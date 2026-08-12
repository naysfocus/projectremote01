package id.remotehp.mobile.util

object UrlNormalizer {
    fun normalize(rawValue: String): String {
        var value = rawValue.trim()
        require(value.isNotEmpty()) { "Alamat server wajib diisi" }
        if (!value.startsWith("http://") && !value.startsWith("https://")) {
            value = "http://$value"
        }
        value = value.trimEnd('/')
        val suffix = "/api/mobile/v1"
        if (value.endsWith(suffix)) {
            value = value.removeSuffix(suffix)
        }
        require(value.startsWith("http://") || value.startsWith("https://")) {
            "Alamat server tidak valid"
        }
        return value
    }

    fun apiBase(serverUrl: String): String = normalize(serverUrl) + "/api/mobile/v1"
}
