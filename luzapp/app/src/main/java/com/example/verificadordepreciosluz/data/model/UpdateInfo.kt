package com.example.verificadordepreciosluz.data.model

import com.google.gson.annotations.SerializedName

data class UpdateInfo(
    @SerializedName("version") val version: String,
    @SerializedName("min_version") val minVersion: String?,
    @SerializedName("download_url") val downloadUrl: String,
    @SerializedName("checksum") val checksum: String,
    @SerializedName("changelog") val changelog: String?
)

data class UpdateCheckResponse(
    @SerializedName("has_update") val hasUpdate: Boolean,
    @SerializedName("update_info") val updateInfo: UpdateInfo?
)
