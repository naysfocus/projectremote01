package id.remotehp.mobile.ui

import android.app.Activity
import android.app.AlertDialog
import android.app.DatePickerDialog
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.AdapterView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import id.remotehp.mobile.BuildConfig
import id.remotehp.mobile.api.ApiClient
import id.remotehp.mobile.api.ApiException
import id.remotehp.mobile.model.Account
import id.remotehp.mobile.model.SessionState
import id.remotehp.mobile.model.VideoBatch
import id.remotehp.mobile.model.VideoCollection
import id.remotehp.mobile.security.SecureTokenStore
import id.remotehp.mobile.util.AppPreferences
import id.remotehp.mobile.util.UrlNormalizer
import java.time.LocalDate
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var preferences: AppPreferences
    private lateinit var tokenStore: SecureTokenStore
    private lateinit var api: ApiClient
    private val executor = Executors.newSingleThreadExecutor()

    private lateinit var statusChip: TextView
    private lateinit var messageView: TextView
    private lateinit var pairingCard: LinearLayout
    private lateinit var setupCard: LinearLayout
    private lateinit var activeCard: LinearLayout
    private lateinit var serverField: EditText
    private lateinit var codeField: EditText
    private lateinit var nameField: EditText
    private lateinit var pairButton: Button
    private lateinit var accountSpinner: Spinner
    private lateinit var collectionSpinner: Spinner
    private lateinit var batchSpinner: Spinner
    private lateinit var dateField: EditText
    private lateinit var startButton: Button
    private lateinit var deviceLabel: TextView
    private lateinit var activeSummary: TextView
    private lateinit var resumeButton: Button

    private var accounts: List<Account> = emptyList()
    private var collections: List<VideoCollection> = emptyList()
    private var batches: List<VideoBatch> = emptyList()
    private var activeSession: SessionState? = null
    private var ignoreCollectionSelection = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        preferences = AppPreferences(this)
        tokenStore = SecureTokenStore(this)
        api = ApiClient({ preferences.serverUrl }, { tokenStore.read() })
        buildUi()
        handlePairingIntent(intent)
        refreshConnection()
    }


    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            setIntent(intent)
            handlePairingIntent(intent)
        }
    }

    private fun handlePairingIntent(source: Intent?) {
        val uri = source?.data ?: return
        if (uri.scheme != "remotehp" || uri.host != "pair") return
        val server = uri.getQueryParameter("server").orEmpty()
        val code = uri.getQueryParameter("code").orEmpty()
        if (server.isNotBlank()) {
            runCatching { UrlNormalizer.normalize(server) }.getOrNull()?.let { normalized ->
                preferences.serverUrl = normalized
                if (::serverField.isInitialized) serverField.setText(normalized)
            }
        }
        if (code.isNotBlank() && ::codeField.isInitialized) {
            codeField.setText(code.trim().uppercase())
        }
        if (::pairingCard.isInitialized) pairingCard.visibility = View.VISIBLE
        showMessage("QR pairing terbaca. Periksa nama Android lalu tekan PASANGKAN.", false)
    }

    override fun onResume() {
        super.onResume()
        if (::statusChip.isInitialized && tokenStore.read() != null && preferences.serverUrl.isNotBlank()) {
            refreshConnection(silent = true)
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    private fun buildUi() {
        window.statusBarColor = Color.parseColor(UiKit.COLOR_BACKGROUND)
        window.navigationBarColor = Color.parseColor(UiKit.COLOR_SURFACE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        }

        val content = UiKit.vertical(this).apply {
            setPadding(UiKit.dp(this@MainActivity, 20), UiKit.dp(this@MainActivity, 22), UiKit.dp(this@MainActivity, 20), UiKit.dp(this@MainActivity, 32))
            setBackgroundColor(Color.parseColor(UiKit.COLOR_BACKGROUND))
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.CENTER_VERTICAL
        }
        val headerText = UiKit.vertical(this)
        headerText.addView(UiKit.title(this, "Remote HP"))
        headerText.addView(UiKit.body(this, "Android v1.0.0 · Setup & Floating Overlay", 13f))
        header.addView(headerText, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        statusChip = UiKit.statusChip(this)
        UiKit.setStatus(statusChip, "BELUM TERHUBUNG", "neutral")
        header.addView(statusChip)
        content.addView(header, UiKit.fullWidth(header))

        messageView = UiKit.body(this)
        messageView.visibility = View.GONE
        content.addView(messageView, UiKit.fullWidth(messageView, 14))

        pairingCard = buildPairingCard()
        content.addView(pairingCard, UiKit.fullWidth(pairingCard, 18))

        setupCard = buildSetupCard()
        setupCard.visibility = View.GONE
        content.addView(setupCard, UiKit.fullWidth(setupCard, 16))

        activeCard = buildActiveSessionCard()
        activeCard.visibility = View.GONE
        content.addView(activeCard, UiKit.fullWidth(activeCard, 16))

        val footer = UiKit.body(this, "Token disimpan terenkripsi dengan Android Keystore. Server menentukan identitas HP dari token pairing.", 12f)
        content.addView(footer, UiKit.fullWidth(footer, 20))

        setContentView(ScrollView(this).apply { addView(content) })
    }

    private fun buildPairingCard(): LinearLayout = UiKit.card(this).apply {
        addView(UiKit.title(this@MainActivity, "Hubungkan ke PC", 19f))
        addView(UiKit.body(this@MainActivity, "Jalankan jalankan-windows-lan.bat di PC, lalu masukkan alamat dan kode dari menu Android Pairing."), UiKit.fullWidth(this, 6))

        addView(UiKit.label(this@MainActivity, "Alamat server"))
        serverField = UiKit.field(this@MainActivity, "Contoh: 192.168.1.10:5001", InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI)
        serverField.setText(preferences.serverUrl)
        addView(serverField, UiKit.fullWidth(serverField))

        addView(UiKit.label(this@MainActivity, "Kode pairing"))
        codeField = UiKit.field(this@MainActivity, "ABCD-EFGH")
        codeField.setAllCaps(true)
        addView(codeField, UiKit.fullWidth(codeField))

        addView(UiKit.label(this@MainActivity, "Nama Android"))
        nameField = UiKit.field(this@MainActivity, "Nama operator / HP")
        val defaultName = preferences.displayName.ifBlank { "${Build.MANUFACTURER} ${Build.MODEL}".trim() }
        nameField.setText(defaultName)
        addView(nameField, UiKit.fullWidth(nameField))

        pairButton = UiKit.primaryButton(this@MainActivity, "PASANGKAN")
        pairButton.setOnClickListener { pairDevice() }
        addView(pairButton, UiKit.fullWidth(pairButton, 16))
    }

    private fun buildSetupCard(): LinearLayout = UiKit.card(this).apply {
        addView(UiKit.title(this@MainActivity, "Persiapan sesi", 19f))
        deviceLabel = UiKit.body(this@MainActivity)
        addView(deviceLabel, UiKit.fullWidth(deviceLabel, 5))

        addView(UiKit.label(this@MainActivity, "Akun"))
        accountSpinner = Spinner(this@MainActivity)
        addView(accountSpinner, UiKit.fullWidth(accountSpinner))

        addView(UiKit.label(this@MainActivity, "Tanggal batch"))
        dateField = UiKit.field(this@MainActivity, "YYYY-MM-DD")
        dateField.isFocusable = false
        dateField.setText(LocalDate.now().toString())
        dateField.setOnClickListener { openDatePicker() }
        addView(dateField, UiKit.fullWidth(dateField))

        addView(UiKit.label(this@MainActivity, "Sumber video"))
        collectionSpinner = Spinner(this@MainActivity)
        collectionSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (ignoreCollectionSelection || collections.isEmpty() || position !in collections.indices) return
                loadBatches(collections[position].id)
            }
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        addView(collectionSpinner, UiKit.fullWidth(collectionSpinner))

        addView(UiKit.label(this@MainActivity, "Batch"))
        batchSpinner = Spinner(this@MainActivity)
        addView(batchSpinner, UiKit.fullWidth(batchSpinner))

        startButton = UiKit.primaryButton(this@MainActivity, "MULAI SESI")
        startButton.setOnClickListener { createSession() }
        addView(startButton, UiKit.fullWidth(startButton, 18))

        val resetOverlay = UiKit.secondaryButton(this@MainActivity, "Reset posisi panel")
        resetOverlay.setOnClickListener {
            OverlayService.stop(this@MainActivity)
            preferences.resetOverlayPosition()
            Toast.makeText(this@MainActivity, "Posisi, mode, dan transparansi panel direset", Toast.LENGTH_SHORT).show()
        }
        addView(resetOverlay, UiKit.fullWidth(resetOverlay, 10))

        val disconnect = UiKit.secondaryButton(this@MainActivity, "Lepas pairing lokal")
        disconnect.setOnClickListener { confirmLocalDisconnect() }
        addView(disconnect, UiKit.fullWidth(disconnect, 10))
    }

    private fun buildActiveSessionCard(): LinearLayout = UiKit.card(this).apply {
        addView(UiKit.title(this@MainActivity, "Sesi aktif", 19f))
        activeSummary = UiKit.body(this@MainActivity)
        addView(activeSummary, UiKit.fullWidth(activeSummary, 7))
        resumeButton = UiKit.primaryButton(this@MainActivity, "LANJUTKAN SESI")
        resumeButton.setOnClickListener { activeSession?.let { openSession(it.id) } }
        addView(resumeButton, UiKit.fullWidth(resumeButton, 16))
    }

    private fun pairDevice() {
        val normalized = try {
            UrlNormalizer.normalize(serverField.text.toString())
        } catch (exc: IllegalArgumentException) {
            showMessage(exc.message ?: "Alamat server tidak valid", true)
            return
        }
        val code = codeField.text.toString().trim()
        val displayName = nameField.text.toString().trim()
        if (code.length < 8) {
            showMessage("Masukkan kode pairing dari PC", true)
            return
        }
        if (displayName.isBlank()) {
            showMessage("Nama Android wajib diisi", true)
            return
        }

        preferences.serverUrl = normalized
        preferences.displayName = displayName
        UiKit.setLoading(pairButton, true, "PASANGKAN", "MENGHUBUNGKAN…")
        showMessage("Menghubungkan ke server…", false)
        executor.execute {
            try {
                val result = api.pair(code, preferences.appDeviceUuid, displayName, BuildConfig.VERSION_NAME)
                tokenStore.save(result.token)
                runOnUiThread {
                    codeField.setText("")
                    Toast.makeText(this, "Pairing berhasil: ${result.deviceName}", Toast.LENGTH_SHORT).show()
                    refreshConnection()
                }
            } catch (exc: Exception) {
                runOnUiThread {
                    UiKit.setLoading(pairButton, false, "PASANGKAN", "MENGHUBUNGKAN…")
                    showMessage(readableError(exc), true)
                }
            }
        }
    }

    private fun refreshConnection(silent: Boolean = false) {
        if (tokenStore.read() == null || preferences.serverUrl.isBlank()) {
            showDisconnected()
            return
        }
        UiKit.setStatus(statusChip, "MENGHUBUNGKAN", "warning")
        if (!silent) showMessage("Memeriksa server…", false)
        executor.execute {
            try {
                val bootstrap = api.bootstrap()
                val loadedAccounts = api.accounts()
                val loadedCollections = api.collections().filter { it.available }
                runOnUiThread {
                    accounts = loadedAccounts
                    collections = loadedCollections
                    activeSession = bootstrap.activeSession
                    showConnected(bootstrap.deviceName)
                }
            } catch (exc: Exception) {
                runOnUiThread {
                    if (exc is ApiException && exc.statusCode == 401) {
                        tokenStore.clear()
                        showDisconnected()
                        showMessage("Pairing sudah dicabut atau token tidak valid. Pasangkan ulang.", true)
                    } else {
                        UiKit.setStatus(statusChip, "OFFLINE", "error")
                        showMessage(readableError(exc), true)
                    }
                }
            }
        }
    }

    private fun showConnected(deviceName: String) {
        UiKit.setStatus(statusChip, "TERHUBUNG", "success")
        pairingCard.visibility = View.GONE
        setupCard.visibility = View.VISIBLE
        deviceLabel.text = "Terpasang ke $deviceName · ${preferences.serverUrl}"
        UiKit.bindSpinner(accountSpinner, accounts, "Belum ada akun untuk HP ini")
        ignoreCollectionSelection = true
        UiKit.bindSpinner(collectionSpinner, collections, "Belum ada koleksi READY")
        ignoreCollectionSelection = false
        if (collections.isNotEmpty()) loadBatches(collections.first().id) else {
            batches = emptyList()
            UiKit.bindSpinner(batchSpinner, batches, "Belum ada batch READY")
        }
        activeSession?.let { session ->
            activeSummary.text = "${session.accountName} · ${session.collectionName} / ${session.batchName}\nProgres ${session.doneCount}/${session.total} · aksi berikutnya ${session.nextAction.uppercase()}"
            activeCard.visibility = View.VISIBLE
            startButton.isEnabled = false
            startButton.alpha = 0.55f
            startButton.text = "SESI MASIH AKTIF"
        } ?: run {
            activeCard.visibility = View.GONE
            startButton.isEnabled = accounts.isNotEmpty() && collections.isNotEmpty()
            startButton.alpha = if (startButton.isEnabled) 1f else 0.55f
            startButton.text = "MULAI SESI"
        }
        showMessage("Server siap. Pilih akun, tanggal, koleksi, dan batch.", false)
    }

    private fun showDisconnected() {
        UiKit.setStatus(statusChip, "BELUM TERHUBUNG", "neutral")
        pairingCard.visibility = View.VISIBLE
        setupCard.visibility = View.GONE
        activeCard.visibility = View.GONE
        if (::pairButton.isInitialized) {
            UiKit.setLoading(pairButton, false, "PASANGKAN", "MENGHUBUNGKAN…")
        }
    }

    private fun loadBatches(collectionId: Long) {
        UiKit.bindSpinner(batchSpinner, emptyList<VideoBatch>(), "Memuat batch…")
        executor.execute {
            try {
                val loaded = api.batches(collectionId).filter { it.available && it.videoCount == 24 }
                runOnUiThread {
                    batches = loaded
                    UiKit.bindSpinner(batchSpinner, batches, "Tidak ada batch READY 24 video")
                    startButton.isEnabled = activeSession == null && accounts.isNotEmpty() && batches.isNotEmpty()
                    startButton.alpha = if (startButton.isEnabled) 1f else 0.55f
                }
            } catch (exc: Exception) {
                runOnUiThread {
                    batches = emptyList()
                    UiKit.bindSpinner(batchSpinner, batches, "Gagal memuat batch")
                    showMessage(readableError(exc), true)
                }
            }
        }
    }

    private fun createSession() {
        val account = accounts.getOrNull(accountSpinner.selectedItemPosition)
        val collection = collections.getOrNull(collectionSpinner.selectedItemPosition)
        val batch = batches.getOrNull(batchSpinner.selectedItemPosition)
        if (account == null || collection == null || batch == null) {
            showMessage("Pilih akun, koleksi, dan batch READY", true)
            return
        }
        UiKit.setLoading(startButton, true, "MULAI SESI", "MEMBUAT SESI…")
        executor.execute {
            try {
                val session = api.createSession(account.id, collection.id, batch.subfolder, dateField.text.toString())
                runOnUiThread {
                    activeSession = session
                    UiKit.setLoading(startButton, false, "MULAI SESI", "MEMBUAT SESI…")
                    openSession(session.id)
                }
            } catch (exc: Exception) {
                runOnUiThread {
                    UiKit.setLoading(startButton, false, "MULAI SESI", "MEMBUAT SESI…")
                    showMessage(readableError(exc), true)
                }
            }
        }
    }

    private fun openSession(sessionId: Long) {
        startActivity(
            Intent(this, SessionActivity::class.java)
                .putExtra(SessionActivity.EXTRA_SESSION_ID, sessionId)
                .putExtra(SessionActivity.EXTRA_AUTO_START_OVERLAY, true),
        )
    }

    private fun openDatePicker() {
        val current = runCatching { LocalDate.parse(dateField.text.toString()) }.getOrElse { LocalDate.now() }
        DatePickerDialog(this, { _, year, month, day ->
            dateField.setText(LocalDate.of(year, month + 1, day).toString())
        }, current.year, current.monthValue - 1, current.dayOfMonth).show()
    }

    private fun confirmLocalDisconnect() {
        AlertDialog.Builder(this)
            .setTitle("Lepas pairing lokal?")
            .setMessage("Token di Android akan dihapus. Akses server tetap dapat dicabut dari menu Android Pairing di PC.")
            .setNegativeButton("Batal", null)
            .setPositiveButton("Lepas") { _, _ ->
                OverlayService.stop(this)
                tokenStore.clear()
                preferences.overlaySessionId = -1L
                activeSession = null
                showDisconnected()
                showMessage("Pairing lokal sudah dilepas.", false)
            }
            .show()
    }

    private fun showMessage(message: String, error: Boolean) {
        messageView.text = message
        messageView.setTextColor(Color.parseColor(if (error) UiKit.COLOR_ERROR else UiKit.COLOR_MUTED))
        messageView.visibility = View.VISIBLE
    }

    private fun readableError(exc: Exception): String = when (exc) {
        is ApiException -> exc.message ?: "Operasi gagal"
        else -> exc.message ?: "Operasi gagal"
    }
}
