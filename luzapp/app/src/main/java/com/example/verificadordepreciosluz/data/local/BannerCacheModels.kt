package com.example.verificadordepreciosluz.data.local

data class BannerCacheItem(
    val id: Int,
    val titulo: String?,
    val tipo: String,
    val remoteUrl: String,
    val localPath: String,
    val duracionSeg: Int?,
    val prioridad: Int?,
    val fechaInicioMs: Long? = null,
    val fechaFinMs: Long? = null
)

data class BannerCacheMeta(
    val lastSyncAt: Long,
    val items: List<BannerCacheItem>,
)
