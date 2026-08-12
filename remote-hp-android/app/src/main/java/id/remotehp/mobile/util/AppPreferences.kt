package id.remotehp.mobile.util

import android.content.Context
import java.util.UUID

class AppPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("remote_hp_prefs", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER_URL, "") ?: ""
        set(value) = prefs.edit().putString(KEY_SERVER_URL, value).apply()

    var displayName: String
        get() = prefs.getString(KEY_DISPLAY_NAME, "") ?: ""
        set(value) = prefs.edit().putString(KEY_DISPLAY_NAME, value).apply()

    var overlaySessionId: Long
        get() = prefs.getLong(KEY_OVERLAY_SESSION_ID, -1L)
        set(value) = prefs.edit().putLong(KEY_OVERLAY_SESSION_ID, value).apply()

    var overlayMode: String
        get() = prefs.getString(KEY_OVERLAY_MODE, "COMPACT") ?: "COMPACT"
        set(value) = prefs.edit().putString(KEY_OVERLAY_MODE, value).apply()

    var overlayOpacity: Int
        get() = prefs.getInt(KEY_OVERLAY_OPACITY, 88).coerceIn(60, 100)
        set(value) = prefs.edit().putInt(KEY_OVERLAY_OPACITY, value.coerceIn(60, 100)).apply()

    val appDeviceUuid: String
        get() {
            val existing = prefs.getString(KEY_APP_UUID, null)
            if (!existing.isNullOrBlank()) return existing
            val created = UUID.randomUUID().toString()
            prefs.edit().putString(KEY_APP_UUID, created).apply()
            return created
        }

    fun overlayPosition(landscape: Boolean): Pair<Int, Int> {
        val prefix = if (landscape) "landscape" else "portrait"
        return prefs.getInt("overlay_${prefix}_x", 24) to prefs.getInt("overlay_${prefix}_y", 180)
    }

    fun saveOverlayPosition(landscape: Boolean, x: Int, y: Int) {
        val prefix = if (landscape) "landscape" else "portrait"
        prefs.edit()
            .putInt("overlay_${prefix}_x", x.coerceAtLeast(0))
            .putInt("overlay_${prefix}_y", y.coerceAtLeast(0))
            .apply()
    }

    fun resetOverlayPosition() {
        prefs.edit()
            .remove("overlay_portrait_x")
            .remove("overlay_portrait_y")
            .remove("overlay_landscape_x")
            .remove("overlay_landscape_y")
            .putString(KEY_OVERLAY_MODE, "COMPACT")
            .putInt(KEY_OVERLAY_OPACITY, 88)
            .apply()
    }

    fun clearConnectionMetadata() {
        prefs.edit()
            .remove(KEY_SERVER_URL)
            .remove(KEY_OVERLAY_SESSION_ID)
            .apply()
    }

    companion object {
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_DISPLAY_NAME = "display_name"
        private const val KEY_APP_UUID = "app_device_uuid"
        private const val KEY_OVERLAY_SESSION_ID = "overlay_session_id"
        private const val KEY_OVERLAY_MODE = "overlay_mode"
        private const val KEY_OVERLAY_OPACITY = "overlay_opacity"
    }
}
