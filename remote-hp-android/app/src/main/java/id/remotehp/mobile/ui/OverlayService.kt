package id.remotehp.mobile.ui

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import id.remotehp.mobile.R
import id.remotehp.mobile.api.ApiClient
import id.remotehp.mobile.model.SessionState
import id.remotehp.mobile.security.SecureTokenStore
import id.remotehp.mobile.util.AppPreferences
import kotlin.math.abs

class OverlayService : Service(), SessionWorkflowController.Listener {
    private enum class Mode { BUBBLE, COMPACT, EXPANDED }

    private lateinit var windowManager: WindowManager
    private lateinit var preferences: AppPreferences
    private lateinit var tokenStore: SecureTokenStore
    private lateinit var api: ApiClient
    private var controller: SessionWorkflowController? = null
    private var overlayView: View? = null
    private var layoutParams: WindowManager.LayoutParams? = null
    private var sessionId: Long = -1L
    private var state: SessionState? = null
    private var mode = Mode.COMPACT
    private var busyLabel = ""
    private var errorMessage = ""
    private var transientMessage = ""
    private var confirmingCancel = false

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        preferences = AppPreferences(this)
        tokenStore = SecureTokenStore(this)
        api = ApiClient({ preferences.serverUrl }, { tokenStore.read() })
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopOverlay(clearSession = false)
                return START_NOT_STICKY
            }
            ACTION_OPEN_SETTINGS -> {
                val settingsIntent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(settingsIntent)
                return START_NOT_STICKY
            }
        }

        val requestedId = intent?.getLongExtra(EXTRA_SESSION_ID, -1L) ?: -1L
        sessionId = if (requestedId > 0L) requestedId else preferences.overlaySessionId
        if (sessionId <= 0L) {
            stopSelf()
            return START_NOT_STICKY
        }

        startForeground(NOTIFICATION_ID, buildNotification("Panel mengambang aktif"))
        if (!Settings.canDrawOverlays(this)) {
            updateNotification("Izin tampil di atas aplikasi lain diperlukan")
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }

        preferences.overlaySessionId = sessionId
        mode = runCatching { Mode.valueOf(preferences.overlayMode) }.getOrDefault(Mode.COMPACT)
        attachOverlay()
        startController()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        controller?.close()
        controller = null
        removeOverlay()
        super.onDestroy()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        removeOverlay()
        attachOverlay()
    }

    override fun onBusy(label: String) {
        busyLabel = label
        errorMessage = ""
        transientMessage = ""
        renderOverlay()
        updateNotification(label)
    }

    override fun onState(state: SessionState, message: String) {
        this.state = state
        busyLabel = ""
        errorMessage = ""
        transientMessage = message
        renderOverlay()
        updateNotification(notificationSummary(state))
    }

    override fun onError(message: String) {
        busyLabel = ""
        errorMessage = message
        transientMessage = ""
        renderOverlay()
        updateNotification("Perlu tindakan · buka panel")
    }

    override fun onFinished() {
        Toast.makeText(this, "Sesi 24/24 selesai", Toast.LENGTH_LONG).show()
        stopOverlay(clearSession = true)
    }

    override fun onCancelled(warning: String) {
        Toast.makeText(this, warning.ifBlank { "Sesi dibatalkan" }, Toast.LENGTH_LONG).show()
        stopOverlay(clearSession = true)
    }

    private fun startController() {
        controller?.close()
        controller = SessionWorkflowController(this, sessionId, api, this)
        controller?.start()
    }

    private fun attachOverlay() {
        if (overlayView != null) return
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            val saved = preferences.overlayPosition(isLandscape())
            x = saved.first
            y = saved.second
        }
        layoutParams = params
        renderOverlay()
    }

    private fun renderOverlay() {
        if (!Settings.canDrawOverlays(this)) return
        val old = overlayView
        if (old != null) runCatching { windowManager.removeView(old) }
        val root = when (mode) {
            Mode.BUBBLE -> buildBubble()
            Mode.COMPACT -> buildCompact()
            Mode.EXPANDED -> buildExpanded()
        }
        overlayView = root
        val params = layoutParams ?: return
        params.width = if (mode == Mode.EXPANDED) {
            minOf(dp(320), (resources.displayMetrics.widthPixels * 0.80f).toInt())
        } else {
            WindowManager.LayoutParams.WRAP_CONTENT
        }
        params.height = WindowManager.LayoutParams.WRAP_CONTENT
        runCatching { windowManager.addView(root, params) }
            .onSuccess { root.post { snapToEdge(save = true) } }
            .onFailure {
                errorMessage = "Panel gagal ditampilkan"
                stopSelf()
            }
    }

    private fun buildBubble(): View {
        val progress = TextView(this).apply {
            text = progressLabel()
            textSize = 13f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            minWidth = dp(54)
            minHeight = dp(54)
            setPadding(dp(8), dp(8), dp(8), dp(8))
            background = roundedPanel(Color.parseColor(UiKit.COLOR_PRIMARY), 0.72f, 999f)
            setOnClickListener { setMode(Mode.COMPACT) }
        }
        installDrag(progress, onTap = { setMode(Mode.COMPACT) }, onDoubleTap = null, onLongPress = { setMode(Mode.EXPANDED) })
        return progress
    }

    private fun buildCompact(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(8), dp(6), dp(7), dp(6))
            background = panelBackground(Mode.COMPACT)
            elevation = dp(6).toFloat()
        }
        val drag = TextView(this).apply {
            text = "⋮⋮"
            textSize = 18f
            setTextColor(Color.parseColor(UiKit.COLOR_MUTED))
            gravity = Gravity.CENTER
            minWidth = dp(32)
            minHeight = dp(48)
        }
        installDrag(
            drag,
            onTap = { setMode(Mode.EXPANDED) },
            onDoubleTap = { setMode(Mode.BUBBLE) },
            onLongPress = { setMode(Mode.EXPANDED) },
        )
        root.addView(drag)

        val progress = TextView(this).apply {
            text = progressLabel()
            textSize = 13f
            setTextColor(Color.parseColor(if (errorMessage.isBlank()) UiKit.COLOR_TEXT else UiKit.COLOR_ERROR))
            gravity = Gravity.CENTER
            minWidth = dp(50)
            setPadding(dp(4), 0, dp(7), 0)
            setOnClickListener { setMode(Mode.EXPANDED) }
        }
        root.addView(progress)

        val main = compactPrimaryButton(primaryLabel())
        main.isEnabled = busyLabel.isBlank()
        main.alpha = if (main.isEnabled) 1f else 0.72f
        main.setOnClickListener { controller?.performPrimary() }
        root.addView(main, LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(48)))
        return root
    }

    private fun buildExpanded(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(12), dp(14), dp(14))
            background = panelBackground(Mode.EXPANDED)
            elevation = dp(8).toFloat()
            minimumWidth = dp(286)
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val drag = TextView(this).apply {
            text = "⋮⋮  ${progressLabel()}"
            textSize = 15f
            setTextColor(Color.parseColor(UiKit.COLOR_TEXT))
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            setPadding(dp(4), dp(7), dp(8), dp(7))
        }
        installDrag(
            drag,
            onTap = null,
            onDoubleTap = { setMode(Mode.BUBBLE) },
            onLongPress = null,
        )
        header.addView(drag, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        val compact = miniTextAction("KECILKAN") { setMode(Mode.COMPACT) }
        header.addView(compact)
        root.addView(header)

        val current = state
        val item = current?.currentItem
        root.addView(detailText(
            if (current == null) "Memuat sesi…" else "${current.accountName} · ${current.collectionName} / ${current.batchName}",
            13f,
            UiKit.COLOR_TEXT,
        ))
        if (item != null) {
            root.addView(detailText(item.filename, 15f, UiKit.COLOR_TEXT, bold = true))
            val schedule = listOf(item.scheduledLabel, item.scheduledTime).filter { it.isNotBlank() }.joinToString(" · ")
            if (schedule.isNotBlank()) root.addView(detailText(schedule, 12f, UiKit.COLOR_MUTED))
            if (item.caption.isNotBlank()) {
                root.addView(detailText(item.caption, 12f, UiKit.COLOR_MUTED).apply { maxLines = 4 })
            }
        }
        val feedback = when {
            errorMessage.isNotBlank() -> errorMessage
            busyLabel.isNotBlank() -> busyLabel
            transientMessage.isNotBlank() -> transientMessage
            item?.status == "sent" -> "Upload di TikTok, lalu tekan SELESAI."
            item?.status == "waiting" -> "Siap mengirim video melalui Fast Path."
            else -> "State mengikuti server."
        }
        root.addView(detailText(feedback, 12f, if (errorMessage.isBlank()) UiKit.COLOR_MUTED else UiKit.COLOR_ERROR))

        val main = expandedPrimaryButton(primaryLabel())
        main.isEnabled = busyLabel.isBlank()
        main.alpha = if (main.isEnabled) 1f else 0.72f
        main.setOnClickListener { controller?.performPrimary() }
        root.addView(main, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(50)).apply { topMargin = dp(10) })

        val actions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        actions.addView(miniTextAction("SALIN ULANG") { controller?.copyCaptionAgain() }, LinearLayout.LayoutParams(0, dp(42), 1f))
        actions.addView(miniTextAction("TIKTOK") { openTikTok() }, LinearLayout.LayoutParams(0, dp(42), 1f).apply { marginStart = dp(6) })
        actions.addView(miniTextAction("APLIKASI") { openSessionActivity() }, LinearLayout.LayoutParams(0, dp(42), 1f).apply { marginStart = dp(6) })
        root.addView(actions, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })

        root.addView(detailText("Transparansi panel ${preferences.overlayOpacity}%", 11f, UiKit.COLOR_MUTED).apply { tag = "opacity_label" })
        val opacity = SeekBar(this).apply {
            max = 40
            progress = (preferences.overlayOpacity - 60).coerceIn(0, 40)
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    if (!fromUser) return
                    preferences.overlayOpacity = 60 + progress
                    root.background = panelBackground(Mode.EXPANDED)
                    (root.findViewWithTag<TextView>("opacity_label"))?.text = "Transparansi panel ${preferences.overlayOpacity}%"
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit
                override fun onStopTrackingTouch(seekBar: SeekBar?) = Unit
            })
        }
        root.addView(opacity, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(38)))

        if (confirmingCancel) {
            root.addView(detailText("Batalkan sesi? Batch dapat masuk REVIEW jika video pernah dikirim.", 12f, UiKit.COLOR_ERROR))
            val confirmRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            confirmRow.addView(miniTextAction("JANGAN") {
                confirmingCancel = false
                renderOverlay()
            }, LinearLayout.LayoutParams(0, dp(42), 1f))
            confirmRow.addView(miniTextAction("BATALKAN") {
                confirmingCancel = false
                controller?.cancel()
            }.apply { setTextColor(Color.parseColor(UiKit.COLOR_ERROR)) }, LinearLayout.LayoutParams(0, dp(42), 1f).apply { marginStart = dp(6) })
            root.addView(confirmRow)
        } else {
            val footer = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            footer.addView(miniTextAction("BUBBLE") { setMode(Mode.BUBBLE) }, LinearLayout.LayoutParams(0, dp(40), 1f))
            footer.addView(miniTextAction("BATALKAN SESI") {
                confirmingCancel = true
                renderOverlay()
            }.apply { setTextColor(Color.parseColor(UiKit.COLOR_ERROR)) }, LinearLayout.LayoutParams(0, dp(40), 1f).apply { marginStart = dp(6) })
            footer.addView(miniTextAction("TUTUP PANEL") { stopOverlay(clearSession = false) }, LinearLayout.LayoutParams(0, dp(40), 1f).apply { marginStart = dp(6) })
            root.addView(footer)
        }
        return root
    }

    private fun compactPrimaryButton(label: String): Button = Button(this).apply {
        text = label
        setAllCaps(false)
        textSize = 13f
        setTextColor(Color.WHITE)
        minWidth = dp(74)
        minHeight = dp(48)
        setPadding(dp(12), 0, dp(12), 0)
        background = roundedPanel(Color.parseColor(primaryColor()), 1f, 12f)
    }

    private fun expandedPrimaryButton(label: String): Button = compactPrimaryButton(label).apply {
        textSize = 15f
    }

    private fun miniTextAction(label: String, action: () -> Unit): TextView = TextView(this).apply {
        text = label
        textSize = 10.5f
        setTextColor(Color.parseColor(UiKit.COLOR_TEXT))
        gravity = Gravity.CENTER
        setPadding(dp(5), dp(5), dp(5), dp(5))
        background = roundedPanel(Color.WHITE, 0.96f, 10f, UiKit.COLOR_BORDER)
        setOnClickListener { action() }
    }

    private fun detailText(textValue: String, size: Float, color: String, bold: Boolean = false): TextView = TextView(this).apply {
        text = textValue
        textSize = size
        setTextColor(Color.parseColor(color))
        if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        setPadding(0, dp(5), 0, 0)
    }

    private fun primaryLabel(): String {
        if (busyLabel.isNotBlank()) return busyLabel
        if (errorMessage.isNotBlank()) return "COBA LAGI"
        val item = state?.currentItem ?: return if (state == null) "MUAT ULANG" else "SELESAIKAN SESI"
        return when {
            item.status == "waiting" -> "KIRIM"
            item.status == "sent" && !item.captionReady -> "SALIN CAPTION"
            item.status == "sent" -> "SELESAI"
            else -> "MUAT ULANG"
        }
    }

    private fun primaryColor(): String = when {
        errorMessage.isNotBlank() -> UiKit.COLOR_ERROR
        state?.currentItem?.status == "sent" -> UiKit.COLOR_SUCCESS
        else -> UiKit.COLOR_PRIMARY
    }

    private fun progressLabel(): String {
        val current = state ?: return "—/24"
        val number = current.currentItem?.number ?: current.total
        return "%02d/%02d".format(number, current.total)
    }

    private fun notificationSummary(value: SessionState): String {
        val action = primaryLabel()
        return "${progressLabel()} · $action"
    }

    private fun setMode(next: Mode) {
        mode = next
        confirmingCancel = false
        preferences.overlayMode = next.name
        renderOverlay()
        snapToEdge(save = true)
    }

    private fun installDrag(
        target: View,
        onTap: (() -> Unit)?,
        onDoubleTap: (() -> Unit)?,
        onLongPress: (() -> Unit)?,
    ) {
        var downRawX = 0f
        var downRawY = 0f
        var startX = 0
        var startY = 0
        var moved = false
        var downAt = 0L
        var previousTapAt = 0L
        var pendingSingleTap: Runnable? = null
        val threshold = dp(8)
        target.setOnTouchListener { _, event ->
            val params = layoutParams ?: return@setOnTouchListener false
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downRawX = event.rawX
                    downRawY = event.rawY
                    startX = params.x
                    startY = params.y
                    moved = false
                    downAt = System.currentTimeMillis()
                    target.alpha = 0.88f
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - downRawX).toInt()
                    val dy = (event.rawY - downRawY).toInt()
                    if (abs(dx) > threshold || abs(dy) > threshold) moved = true
                    if (moved) {
                        params.x = (startX + dx).coerceAtLeast(0)
                        params.y = clampY(startY + dy)
                        overlayView?.let { current -> runCatching { windowManager.updateViewLayout(current, params) } }
                    }
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    target.alpha = 1f
                    val now = System.currentTimeMillis()
                    if (moved) {
                        snapToEdge(save = true)
                    } else if (now - downAt >= 550L && onLongPress != null) {
                        onLongPress()
                    } else if (onDoubleTap != null && now - previousTapAt <= 320L) {
                        pendingSingleTap?.let(target::removeCallbacks)
                        pendingSingleTap = null
                        previousTapAt = 0L
                        onDoubleTap()
                    } else if (onDoubleTap != null) {
                        previousTapAt = now
                        val tapTime = now
                        val runnable = Runnable {
                            if (previousTapAt == tapTime) {
                                previousTapAt = 0L
                                onTap?.invoke()
                            }
                        }
                        pendingSingleTap = runnable
                        target.postDelayed(runnable, 330L)
                    } else {
                        onTap?.invoke()
                    }
                    true
                }
                else -> false
            }
        }
    }

    private fun snapToEdge(save: Boolean) {
        val params = layoutParams ?: return
        val root = overlayView ?: return
        val screenWidth = resources.displayMetrics.widthPixels
        val width = root.width.takeIf { it > 0 } ?: dp(if (mode == Mode.BUBBLE) 54 else 180)
        val margin = dp(8)
        params.x = if (params.x + width / 2 < screenWidth / 2) margin else (screenWidth - width - margin).coerceAtLeast(margin)
        params.y = clampY(params.y)
        runCatching { windowManager.updateViewLayout(root, params) }
        if (save) preferences.saveOverlayPosition(isLandscape(), params.x, params.y)
    }

    private fun clampY(value: Int): Int {
        val screenHeight = resources.displayMetrics.heightPixels
        val height = overlayView?.height?.takeIf { it > 0 } ?: dp(60)
        return value.coerceIn(dp(24), (screenHeight - height - dp(32)).coerceAtLeast(dp(24)))
    }

    private fun panelBackground(mode: Mode): GradientDrawable {
        val base = when (mode) {
            Mode.BUBBLE -> 72
            Mode.COMPACT -> preferences.overlayOpacity
            Mode.EXPANDED -> (preferences.overlayOpacity + 6).coerceAtMost(100)
        }
        return roundedPanel(Color.WHITE, base / 100f, if (mode == Mode.EXPANDED) 18f else 16f, UiKit.COLOR_BORDER)
    }

    private fun roundedPanel(color: Int, alpha: Float, radiusDp: Float, stroke: String? = null): GradientDrawable {
        val resolvedAlpha = (255 * alpha.coerceIn(0.6f, 1f)).toInt()
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(Color.argb(resolvedAlpha, Color.red(color), Color.green(color), Color.blue(color)))
            cornerRadius = dp(radiusDp.toInt()).toFloat()
            if (stroke != null) setStroke(dp(1), Color.parseColor(stroke))
        }
    }

    private fun openTikTok() {
        val packages = listOf(
            "com.zhiliaoapp.musically",
            "com.ss.android.ugc.trill",
            "com.ss.android.ugc.tiktok.lite",
        )
        val launch = packages.firstNotNullOfOrNull { packageManager.getLaunchIntentForPackage(it) }
        if (launch == null) {
            Toast.makeText(this, "TikTok tidak ditemukan", Toast.LENGTH_LONG).show()
            return
        }
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(launch)
    }

    private fun openSessionActivity() {
        startActivity(
            Intent(this, SessionActivity::class.java)
                .putExtra(SessionActivity.EXTRA_SESSION_ID, sessionId)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
        )
    }

    private fun removeOverlay() {
        overlayView?.let { view -> runCatching { windowManager.removeView(view) } }
        overlayView = null
    }

    private fun stopOverlay(clearSession: Boolean) {
        if (clearSession) preferences.overlaySessionId = -1L
        controller?.close()
        controller = null
        removeOverlay()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Panel Remote HP", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Menjaga panel workflow tetap aktif di atas TikTok"
                setShowBadge(false)
            },
        )
    }

    private fun buildNotification(text: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            1,
            Intent(this, SessionActivity::class.java)
                .putExtra(SessionActivity.EXTRA_SESSION_ID, sessionId)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            2,
            Intent(this, OverlayService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setSmallIcon(R.drawable.ic_remote_hp)
            .setContentTitle("Remote HP · Panel aktif")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .addAction(Notification.Action.Builder(null, "Tutup panel", stopIntent).build())
            .build()
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun isLandscape(): Boolean = resources.configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        const val ACTION_SHOW = "id.remotehp.mobile.action.SHOW_OVERLAY"
        const val ACTION_STOP = "id.remotehp.mobile.action.STOP_OVERLAY"
        const val ACTION_OPEN_SETTINGS = "id.remotehp.mobile.action.OPEN_OVERLAY_SETTINGS"
        const val EXTRA_SESSION_ID = "session_id"
        private const val CHANNEL_ID = "remote_hp_overlay"
        private const val NOTIFICATION_ID = 14402


        fun start(context: Context, sessionId: Long) {
            val intent = Intent(context, OverlayService::class.java)
                .setAction(ACTION_SHOW)
                .putExtra(EXTRA_SESSION_ID, sessionId)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(Intent(context, OverlayService::class.java).setAction(ACTION_STOP))
        }
    }
}
