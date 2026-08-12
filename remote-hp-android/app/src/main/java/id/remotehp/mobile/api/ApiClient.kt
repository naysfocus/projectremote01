package id.remotehp.mobile.api

import id.remotehp.mobile.model.Account
import id.remotehp.mobile.model.BootstrapState
import id.remotehp.mobile.model.PairResult
import id.remotehp.mobile.model.SessionItem
import id.remotehp.mobile.model.SessionState
import id.remotehp.mobile.model.VideoBatch
import id.remotehp.mobile.model.VideoCollection
import id.remotehp.mobile.util.UrlNormalizer
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL

class ApiException(
    message: String,
    val statusCode: Int = 0,
) : Exception(message)

class ApiClient(
    private val serverUrlProvider: () -> String,
    private val tokenProvider: () -> String?,
) {
    fun pair(
        code: String,
        appDeviceUuid: String,
        displayName: String,
        appVersion: String,
    ): PairResult {
        val body = JSONObject()
            .put("code", code.trim().uppercase())
            .put("app_device_uuid", appDeviceUuid)
            .put("display_name", displayName.trim())
            .put("app_version", appVersion)
        val response = request("POST", "/pair", body, authenticated = false)
        val client = response.getJSONObject("client")
        return PairResult(
            token = response.getString("token"),
            clientName = client.optString("display_name", "Android Remote HP"),
            deviceName = client.optString("device_name", "HP"),
        )
    }

    fun bootstrap(): BootstrapState {
        val response = request("GET", "/bootstrap")
        val client = response.getJSONObject("client")
        val device = response.getJSONObject("device")
        val active = response.optJSONObject("active_session")?.let(::parseSession)
        return BootstrapState(
            deviceName = device.optString("name", "HP"),
            clientName = client.optString("display_name", "Android Remote HP"),
            activeSession = active,
        )
    }

    fun accounts(): List<Account> {
        val response = request("GET", "/accounts")
        return response.getJSONArray("accounts").mapObjects { row ->
            Account(
                id = row.getLong("id"),
                username = row.optString("username", "Akun"),
                appSlot = row.optString("app_slot", "original"),
            )
        }
    }

    fun collections(): List<VideoCollection> {
        val response = request("GET", "/collections")
        return response.getJSONArray("collections").mapObjects { row ->
            VideoCollection(
                id = row.getLong("id"),
                name = row.optString("name", "Koleksi"),
                readyCount = row.optInt("ready_count", 0),
                available = row.optBoolean("available", false),
            )
        }
    }

    fun batches(collectionId: Long): List<VideoBatch> {
        val response = request("GET", "/collections/$collectionId/batches")
        return response.getJSONArray("batches").mapObjects { row ->
            VideoBatch(
                id = row.getLong("id"),
                subfolder = row.optString("subfolder", "."),
                status = row.optString("status", "unknown"),
                videoCount = row.optInt("video_count", 0),
                available = row.optBoolean("available", false),
            )
        }
    }

    fun createSession(
        accountId: Long,
        collectionId: Long,
        subfolder: String,
        batchDate: String,
    ): SessionState {
        val body = JSONObject()
            .put("account_id", accountId)
            .put("collection_id", collectionId)
            .put("subfolder", subfolder)
            .put("batch_date", batchDate)
        return parseSession(request("POST", "/sessions", body))
    }

    fun session(sessionId: Long): SessionState =
        parseSession(request("GET", "/sessions/$sessionId"))

    fun push(sessionId: Long, position: Int): JSONObject {
        return request(
            "POST",
            "/sessions/$sessionId/push",
            JSONObject().put("expected_position", position),
        )
    }

    fun captionReady(sessionId: Long, position: Int): JSONObject {
        return request(
            "POST",
            "/sessions/$sessionId/caption-ready",
            JSONObject()
                .put("expected_position", position)
                .put("method", "copied"),
        )
    }

    fun confirm(sessionId: Long, position: Int): JSONObject {
        return request(
            "POST",
            "/sessions/$sessionId/confirm",
            JSONObject().put("expected_position", position),
        )
    }

    fun finish(sessionId: Long): JSONObject =
        request("POST", "/sessions/$sessionId/finish", JSONObject())

    fun cancel(sessionId: Long): JSONObject =
        request("POST", "/sessions/$sessionId/cancel", JSONObject())

    private fun request(
        method: String,
        path: String,
        body: JSONObject? = null,
        authenticated: Boolean = true,
    ): JSONObject {
        val base = try {
            UrlNormalizer.apiBase(serverUrlProvider())
        } catch (exc: IllegalArgumentException) {
            throw ApiException(exc.message ?: "Alamat server tidak valid")
        }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            useCaches = false
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            if (authenticated) {
                val token = tokenProvider()?.takeIf { it.isNotBlank() }
                    ?: throw ApiException("Aplikasi belum dipasangkan", 401)
                setRequestProperty("Authorization", "Bearer $token")
            }
            if (body != null) {
                doOutput = true
                outputStream.use { stream ->
                    stream.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
        }

        return try {
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.use { input ->
                BufferedReader(InputStreamReader(input, Charsets.UTF_8)).readText()
            }.orEmpty()
            val json = if (text.isBlank()) JSONObject() else JSONObject(text)
            if (status !in 200..299) {
                throw ApiException(json.optString("error", "Server menolak permintaan"), status)
            }
            if (json.has("ok") && !json.optBoolean("ok", true)) {
                throw ApiException(json.optString("error", "Operasi gagal"), status)
            }
            json
        } catch (exc: ApiException) {
            throw exc
        } catch (exc: Exception) {
            throw ApiException(networkMessage(exc))
        } finally {
            connection.disconnect()
        }
    }

    private fun parseSession(root: JSONObject): SessionState {
        val session = root.getJSONObject("session")
        val account = session.optJSONObject("account") ?: JSONObject()
        val collection = session.optJSONObject("collection") ?: JSONObject()
        val current = root.optJSONObject("current_item")
        return SessionState(
            id = session.getLong("id"),
            status = session.optString("status", "active"),
            accountName = account.optString("username", "Akun"),
            collectionName = collection.optString("name", "Koleksi"),
            batchName = session.optString("batch", collection.optString("batch", ".")),
            batchDate = session.optString("batch_date", ""),
            doneCount = session.optInt("done_count", 0),
            total = session.optInt("total", 24),
            currentPosition = session.optNullableInt("current_position"),
            nextAction = session.optString("next_action", root.optJSONObject("overlay")?.optString("next_action", "none") ?: "none"),
            currentItem = current?.let(::parseItem),
        )
    }

    private fun parseItem(row: JSONObject): SessionItem {
        val captionObject = row.optJSONObject("caption")
        val captionText = if (captionObject != null) captionObject.optString("full", "") else row.optString("caption", "")
        return SessionItem(
            id = row.getLong("id"),
            position = row.getInt("position"),
            number = row.optInt("number", row.getInt("position") + 1),
            filename = row.optString("filename", "Video"),
            status = row.optString("status", "waiting"),
            caption = captionText,
            captionReady = row.optBoolean("caption_ready", false) || (!row.isNull("caption_ready_at") && row.optString("caption_ready_at").isNotBlank()),
            scheduledLabel = row.optString("scheduled_label", ""),
            scheduledTime = row.optString("scheduled_time", ""),
        )
    }

    private fun networkMessage(exc: Exception): String {
        val detail = exc.message?.lowercase().orEmpty()
        return when {
            "cleartext" in detail -> "Android menolak koneksi HTTP. Periksa konfigurasi aplikasi."
            "timeout" in detail -> "Server tidak merespons. Pastikan PC dan HP berada di Wi-Fi yang sama."
            "failed to connect" in detail || "connection refused" in detail ->
                "Server tidak dapat dihubungi. Jalankan mode LAN di PC dan periksa alamatnya."
            else -> "Koneksi ke server gagal. Periksa Wi-Fi dan alamat server."
        }
    }

    private fun JSONObject.optNullableInt(key: String): Int? {
        if (!has(key) || isNull(key)) return null
        return optInt(key)
    }

    private fun <T> JSONArray.mapObjects(transform: (JSONObject) -> T): List<T> {
        val result = ArrayList<T>(length())
        for (index in 0 until length()) {
            result += transform(getJSONObject(index))
        }
        return result
    }

    companion object {
        private const val CONNECT_TIMEOUT_MS = 8_000
        private const val READ_TIMEOUT_MS = 120_000
    }
}
