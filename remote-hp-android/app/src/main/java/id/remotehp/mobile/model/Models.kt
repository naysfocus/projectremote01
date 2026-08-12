package id.remotehp.mobile.model

data class Account(
    val id: Long,
    val username: String,
    val appSlot: String,
) {
    override fun toString(): String = when (appSlot) {
        "clone" -> "$username · Kloning"
        else -> "$username · Original"
    }
}

data class VideoCollection(
    val id: Long,
    val name: String,
    val readyCount: Int,
    val available: Boolean,
) {
    override fun toString(): String = "$name · $readyCount batch siap"
}

data class VideoBatch(
    val id: Long,
    val subfolder: String,
    val status: String,
    val videoCount: Int,
    val available: Boolean,
) {
    override fun toString(): String {
        val label = if (subfolder == ".") "Folder utama" else "Batch $subfolder"
        return "$label · ${status.uppercase()} · $videoCount video"
    }
}

data class PairResult(
    val token: String,
    val clientName: String,
    val deviceName: String,
)

data class SessionItem(
    val id: Long,
    val position: Int,
    val number: Int,
    val filename: String,
    val status: String,
    val caption: String,
    val captionReady: Boolean,
    val scheduledLabel: String,
    val scheduledTime: String,
)

data class SessionState(
    val id: Long,
    val status: String,
    val accountName: String,
    val collectionName: String,
    val batchName: String,
    val batchDate: String,
    val doneCount: Int,
    val total: Int,
    val currentPosition: Int?,
    val nextAction: String,
    val currentItem: SessionItem?,
)

data class BootstrapState(
    val deviceName: String,
    val clientName: String,
    val activeSession: SessionState?,
)
