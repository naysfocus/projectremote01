package id.remotehp.mobile.ui

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import id.remotehp.mobile.api.ApiClient
import id.remotehp.mobile.model.SessionState
import id.remotehp.mobile.security.SecureTokenStore
import id.remotehp.mobile.util.AppPreferences

class SessionActivity : Activity(), SessionWorkflowController.Listener {
    private lateinit var preferences: AppPreferences
    private lateinit var tokenStore: SecureTokenStore
    private lateinit var api: ApiClient
    private lateinit var controller: SessionWorkflowController
    private var sessionId: Long = -1L
    private var session: SessionState? = null
    private var busy = false
    private var awaitingOverlayPermission = false
    private var resumedOnce = false
    private var autoStartOverlay = false
    private var autoStartConsumed = false

    private lateinit var connectionChip: TextView
    private lateinit var progressText: TextView
    private lateinit var contextText: TextView
    private lateinit var filenameText: TextView
    private lateinit var scheduleText: TextView
    private lateinit var stateText: TextView
    private lateinit var captionText: TextView
    private lateinit var primaryButton: Button
    private lateinit var overlayButton: Button
    private lateinit var tiktokButton: Button
    private lateinit var messageText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sessionId = intent.getLongExtra(EXTRA_SESSION_ID, -1L)
        if (sessionId <= 0L) {
            finish()
            return
        }
        autoStartOverlay = intent.getBooleanExtra(EXTRA_AUTO_START_OVERLAY, false)
        preferences = AppPreferences(this)
        tokenStore = SecureTokenStore(this)
        api = ApiClient({ preferences.serverUrl }, { tokenStore.read() })
        controller = SessionWorkflowController(this, sessionId, api, this)
        buildUi()
        controller.start()
    }

    override fun onResume() {
        super.onResume()
        if (awaitingOverlayPermission && Settings.canDrawOverlays(this)) {
            awaitingOverlayPermission = false
            startOverlayAndTikTok()
            return
        }
        if (resumedOnce && ::controller.isInitialized && !controller.isBusy()) {
            controller.refresh("Menyinkronkan sesi…")
        }
        resumedOnce = true
    }

    override fun onDestroy() {
        if (::controller.isInitialized) controller.close()
        super.onDestroy()
    }

    private fun buildUi() {
        window.statusBarColor = Color.parseColor(UiKit.COLOR_BACKGROUND)
        val content = UiKit.vertical(this).apply {
            setPadding(UiKit.dp(this@SessionActivity, 20), UiKit.dp(this@SessionActivity, 22), UiKit.dp(this@SessionActivity, 20), UiKit.dp(this@SessionActivity, 32))
            setBackgroundColor(Color.parseColor(UiKit.COLOR_BACKGROUND))
        }

        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val back = UiKit.secondaryButton(this, "‹ Setup")
        back.setOnClickListener { finish() }
        top.addView(back)
        val title = UiKit.title(this, "Sesi Upload", 22f)
        top.addView(title, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = UiKit.dp(this@SessionActivity, 12)
        })
        connectionChip = UiKit.statusChip(this)
        UiKit.setStatus(connectionChip, "MEMUAT", "warning")
        top.addView(connectionChip)
        content.addView(top, UiKit.fullWidth(top))

        val sessionCard = UiKit.card(this)
        progressText = UiKit.title(this, "—/24", 32f)
        sessionCard.addView(progressText)
        contextText = UiKit.body(this)
        sessionCard.addView(contextText, UiKit.fullWidth(contextText, 5))
        content.addView(sessionCard, UiKit.fullWidth(sessionCard, 18))

        val itemCard = UiKit.card(this)
        stateText = UiKit.body(this, "Menunggu state server", 12f)
        itemCard.addView(stateText)
        filenameText = UiKit.title(this, "Memuat video…", 19f)
        itemCard.addView(filenameText, UiKit.fullWidth(filenameText, 8))
        scheduleText = UiKit.body(this)
        itemCard.addView(scheduleText, UiKit.fullWidth(scheduleText, 5))
        captionText = UiKit.body(this)
        captionText.maxLines = 5
        itemCard.addView(captionText, UiKit.fullWidth(captionText, 12))
        content.addView(itemCard, UiKit.fullWidth(itemCard, 14))

        messageText = UiKit.body(this)
        messageText.visibility = View.GONE
        content.addView(messageText, UiKit.fullWidth(messageText, 14))

        overlayButton = UiKit.primaryButton(this, "BUKA PANEL MENGAMBANG")
        overlayButton.setOnClickListener { requestOverlayAndStart() }
        content.addView(overlayButton, UiKit.fullWidth(overlayButton, 18))

        primaryButton = UiKit.secondaryButton(this, "MEMUAT…")
        primaryButton.isEnabled = false
        primaryButton.setOnClickListener { controller.performPrimary() }
        content.addView(primaryButton, UiKit.fullWidth(primaryButton, 10))

        tiktokButton = UiKit.secondaryButton(this, "BUKA TIKTOK TANPA PANEL")
        tiktokButton.setOnClickListener { openTikTok() }
        content.addView(tiktokButton, UiKit.fullWidth(tiktokButton, 10))

        val cancel = UiKit.secondaryButton(this, "Batalkan sesi")
        cancel.setTextColor(Color.parseColor(UiKit.COLOR_ERROR))
        cancel.setOnClickListener { confirmCancel() }
        content.addView(cancel, UiKit.fullWidth(cancel, 10))

        val note = UiKit.body(
            this,
            "Mode utama v1.0.0 adalah panel mengambang satu tombol di atas TikTok. Layar penuh ini tetap tersedia sebagai fallback dan halaman recovery.",
            12f,
        )
        content.addView(note, UiKit.fullWidth(note, 18))

        setContentView(ScrollView(this).apply { addView(content) })
    }

    override fun onBusy(label: String) {
        busy = true
        primaryButton.isEnabled = false
        primaryButton.text = label
        overlayButton.isEnabled = false
        showMessage(label, false)
    }

    override fun onState(state: SessionState, message: String) {
        session = state
        busy = false
        render(state)
        if (message.isNotBlank()) Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        if (autoStartOverlay && !autoStartConsumed) {
            autoStartConsumed = true
            requestOverlayAndStart()
        }
    }

    override fun onError(message: String) {
        busy = false
        UiKit.setStatus(connectionChip, "PERLU DICOBA", "warning")
        showMessage(message, true)
        primaryButton.text = "COBA LAGI"
        primaryButton.isEnabled = true
        overlayButton.isEnabled = true
    }

    override fun onFinished() {
        busy = false
        OverlayService.stop(this)
        AlertDialog.Builder(this)
            .setTitle("Sesi selesai")
            .setMessage("Seluruh 24 video selesai dan sesi telah ditutup di server.")
            .setCancelable(false)
            .setPositiveButton("Kembali") { _, _ -> finish() }
            .show()
    }

    override fun onCancelled(warning: String) {
        busy = false
        OverlayService.stop(this)
        Toast.makeText(this, warning.ifBlank { "Sesi dibatalkan" }, Toast.LENGTH_LONG).show()
        finish()
    }

    private fun render(value: SessionState) {
        UiKit.setStatus(connectionChip, "TERHUBUNG", "success")
        progressText.text = "${value.doneCount}/${value.total}"
        contextText.text = "${value.accountName} · ${value.collectionName} / ${value.batchName}\nTanggal ${value.batchDate}"
        overlayButton.isEnabled = true
        overlayButton.text = if (Settings.canDrawOverlays(this)) "BUKA PANEL & TIKTOK" else "AKTIFKAN PANEL MENGAMBANG"

        val item = value.currentItem
        if (item == null) {
            filenameText.text = "Semua video selesai"
            scheduleText.text = "Selesaikan sesi untuk menutup workflow."
            captionText.text = ""
            stateText.text = "24/24 SIAP DISELESAIKAN"
            primaryButton.text = "SELESAIKAN SESI"
            primaryButton.isEnabled = !busy
            tiktokButton.visibility = View.GONE
            return
        }

        filenameText.text = item.filename
        scheduleText.text = listOf(item.scheduledLabel, item.scheduledTime).filter { it.isNotBlank() }.joinToString(" · ")
        captionText.text = if (item.caption.isBlank()) "Caption kosong" else item.caption
        stateText.text = "VIDEO ${item.number}/${value.total} · ${item.status.uppercase()}"
        tiktokButton.visibility = if (item.status == "sent") View.VISIBLE else View.GONE
        primaryButton.text = primaryLabel(value)
        primaryButton.isEnabled = !busy
        showMessage(
            when {
                item.status == "waiting" -> "Buka panel mengambang agar workflow berjalan di atas TikTok."
                item.status == "sent" && !item.captionReady -> "Caption belum ditandai siap."
                item.status == "sent" -> "Upload di TikTok, lalu tekan SELESAI di panel."
                else -> "State disinkronkan dari server."
            },
            false,
        )
    }

    private fun primaryLabel(value: SessionState): String {
        val item = value.currentItem ?: return "SELESAIKAN SESI"
        return when {
            item.status == "waiting" -> "KIRIM (FALLBACK LAYAR PENUH)"
            item.status == "sent" && !item.captionReady -> "SALIN CAPTION"
            item.status == "sent" -> "SELESAI (FALLBACK LAYAR PENUH)"
            else -> "MUAT ULANG"
        }
    }

    private fun requestOverlayAndStart() {
        if (Settings.canDrawOverlays(this)) {
            startOverlayAndTikTok()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Izinkan panel mengambang")
            .setMessage("Remote HP membutuhkan izin Tampil di atas aplikasi lain agar satu tombol tetap terlihat saat TikTok dibuka. Izin ini tidak digunakan untuk auto-click atau membaca layar TikTok.")
            .setNegativeButton("Nanti", null)
            .setPositiveButton("Buka pengaturan") { _, _ ->
                awaitingOverlayPermission = true
                startActivity(
                    Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")),
                )
            }
            .show()
    }

    private fun startOverlayAndTikTok() {
        requestNotificationPermissionIfNeeded()
        OverlayService.start(this, sessionId)
        Toast.makeText(this, "Panel aktif · geser dari pegangan ⋮⋮", Toast.LENGTH_SHORT).show()
        openTikTok()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQUEST_NOTIFICATIONS)
        }
    }

    private fun confirmCancel() {
        AlertDialog.Builder(this)
            .setTitle("Batalkan sesi?")
            .setMessage("Jika video sudah pernah dikirim, batch dapat masuk status REVIEW dan perlu diperiksa di PC.")
            .setNegativeButton("Jangan", null)
            .setPositiveButton("Batalkan") { _, _ -> controller.cancel() }
            .show()
    }

    private fun openTikTok() {
        val packages = listOf(
            "com.zhiliaoapp.musically",
            "com.ss.android.ugc.trill",
            "com.ss.android.ugc.tiktok.lite",
        )
        val launch = packages.firstNotNullOfOrNull { packageManager.getLaunchIntentForPackage(it) }
        if (launch == null) {
            Toast.makeText(this, "TikTok tidak ditemukan di HP ini", Toast.LENGTH_LONG).show()
            return
        }
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(launch)
    }

    private fun showMessage(message: String, error: Boolean) {
        messageText.text = message
        messageText.setTextColor(Color.parseColor(if (error) UiKit.COLOR_ERROR else UiKit.COLOR_MUTED))
        messageText.visibility = View.VISIBLE
    }

    companion object {
        const val EXTRA_SESSION_ID = "session_id"
        const val EXTRA_AUTO_START_OVERLAY = "auto_start_overlay"
        private const val REQUEST_NOTIFICATIONS = 1442
    }
}
