package id.remotehp.mobile.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Handler
import android.os.Looper
import id.remotehp.mobile.api.ApiClient
import id.remotehp.mobile.api.ApiException
import id.remotehp.mobile.model.SessionState
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Satu controller workflow untuk layar penuh dan floating overlay.
 * State server selalu menjadi sumber kebenaran; tidak ada tebakan state lokal.
 */
class SessionWorkflowController(
    context: Context,
    private val sessionId: Long,
    private val api: ApiClient,
    private val listener: Listener,
) {
    interface Listener {
        fun onBusy(label: String)
        fun onState(state: SessionState, message: String = "")
        fun onError(message: String)
        fun onFinished()
        fun onCancelled(warning: String)
    }

    private val appContext = context.applicationContext
    private val mainHandler = Handler(Looper.getMainLooper())
    private val executor = Executors.newSingleThreadExecutor()
    private val busy = AtomicBoolean(false)

    @Volatile
    private var state: SessionState? = null

    fun start() = refresh("Memuat sesi…")

    fun refresh(label: String = "Memuat ulang…") {
        runOperation(label) {
            val loaded = api.session(sessionId)
            publishState(loaded)
        }
    }

    fun performPrimary() {
        if (busy.get()) return
        val current = state
        val item = current?.currentItem
        when {
            current == null -> refresh()
            item == null -> finishSession()
            item.status == "waiting" -> push(item.position)
            item.status == "sent" && !item.captionReady -> copyCaption(item.position, item.caption)
            item.status == "sent" -> confirm(item.position)
            else -> refresh("Menyinkronkan state…")
        }
    }

    fun copyCaptionAgain() {
        if (busy.get()) return
        val item = state?.currentItem
        if (item == null || item.status != "sent") {
            refresh("Menyinkronkan state…")
            return
        }
        copyCaption(item.position, item.caption)
    }

    fun cancel() {
        runOperation("Membatalkan sesi…") {
            val result = api.cancel(sessionId)
            val warning = result.optString("warning", "")
            mainHandler.post { listener.onCancelled(warning) }
        }
    }

    fun currentState(): SessionState? = state

    fun isBusy(): Boolean = busy.get()

    fun close() {
        executor.shutdownNow()
    }

    private fun push(position: Int) {
        runOperation("MENGIRIM…") {
            val result = api.push(sessionId, position)
            val caption = result.optJSONObject("caption")?.optString("full", "")
                ?: state?.currentItem?.caption.orEmpty()
            copyToClipboard(caption)
            api.captionReady(sessionId, position)
            val loaded = api.session(sessionId)
            publishState(loaded, "Video terkirim · caption tersalin")
        }
    }

    private fun copyCaption(position: Int, caption: String) {
        runOperation("MENYALIN…") {
            copyToClipboard(caption)
            api.captionReady(sessionId, position)
            val loaded = api.session(sessionId)
            publishState(loaded, "Caption tersalin")
        }
    }

    private fun confirm(position: Int) {
        runOperation("MENYELESAIKAN…") {
            api.confirm(sessionId, position)
            val loaded = api.session(sessionId)
            publishState(loaded)
        }
    }

    private fun finishSession() {
        runOperation("MENUTUP SESI…") {
            api.finish(sessionId)
            mainHandler.post { listener.onFinished() }
        }
    }

    private fun runOperation(label: String, operation: () -> Unit) {
        if (!busy.compareAndSet(false, true)) return
        mainHandler.post { listener.onBusy(label) }
        executor.execute {
            try {
                operation()
            } catch (exc: Exception) {
                mainHandler.post { listener.onError(readableError(exc)) }
            } finally {
                busy.set(false)
            }
        }
    }

    private fun publishState(loaded: SessionState, message: String = "") {
        state = loaded
        mainHandler.post { listener.onState(loaded, message) }
    }

    private fun copyToClipboard(value: String) {
        val clipboard = appContext.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Caption Remote HP", value))
    }

    private fun readableError(exc: Exception): String = when (exc) {
        is ApiException -> exc.message ?: "Operasi gagal"
        else -> exc.message ?: "Operasi gagal"
    }
}
