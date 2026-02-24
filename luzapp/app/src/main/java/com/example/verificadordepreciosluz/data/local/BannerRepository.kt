package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.BannerResponse
import com.google.gson.Gson
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File

class BannerRepository(
    private val context: Context,
    private val api: ApiService,
    private val baseUrl: String,
) {
    private val gson = Gson()
    private val client = OkHttpClient()

    // Carga metadata local (banners_meta.json)
    fun loadCache(): BannerCacheMeta? {
        val metaFile = File(context.filesDir, FILE_META)
        if (!metaFile.exists()) return null
        return runCatching {
            metaFile.reader().use { reader ->
                gson.fromJson(reader, BannerCacheMeta::class.java)
            }
        }.getOrNull()
    }

    // Determina si el cache está vencido
    fun shouldRefresh(maxAgeMs: Long): Boolean {
        val meta = loadCache() ?: return true
        return System.currentTimeMillis() - meta.lastSyncAt > maxAgeMs
    }

    // Descarga y cachea banners si están vencidos
    suspend fun refreshIfStale(maxAgeMs: Long): BannerCacheMeta? {
        if (!shouldRefresh(maxAgeMs)) return loadCache()
        return runCatching {
            val remote = api.banners().sortedBy { it.prioridad ?: 0 }
            val items = remote.mapNotNull { downloadBanner(it) }
            if (items.isEmpty()) {
                Log.w(TAG, "No se pudo descargar ningún banner, se conserva el cache actual")
                return@runCatching loadCache()
            }
            val meta = BannerCacheMeta(
                lastSyncAt = System.currentTimeMillis(),
                items = items
            )
            saveMeta(meta)
            meta
        }.onFailure {
            Log.e(TAG, "Error actualizando banners", it)
        }.getOrNull()
    }

    // Descarga un banner (imagen/video) y lo guarda en files/banners
    public fun downloadBanner(item: BannerResponse): BannerCacheItem? {
        val absoluteUrl = if (item.url.startsWith("http")) item.url else baseUrl.trimEnd('/') + "/" + item.url.trimStart('/')
        val safeUrl = absoluteUrl.replace(" ", "%20")
        val ext = absoluteUrl.substringAfterLast('.', "")
        val safeExt = if (ext.isBlank()) "bin" else ext
        val fileName = "banner_${item.id}.$safeExt"
        val dir = File(context.filesDir, DIR_BANNERS)
        if (!dir.exists()) dir.mkdirs()
        val outFile = File(dir, fileName)

        val request = Request.Builder().url(safeUrl).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                Log.w(TAG, "Fallo al descargar banner id=${item.id} url=$safeUrl code=${response.code}")
                return null
            }
            val body = response.body ?: return null
            outFile.outputStream().use { output ->
                body.byteStream().copyTo(output)
            }
        }

        return BannerCacheItem(
            id = item.id,
            titulo = item.titulo,
            tipo = item.tipo,
            remoteUrl = item.url,
            localPath = outFile.absolutePath,
            duracionSeg = item.duracionSeg,
            prioridad = item.prioridad,
        )
    }

    // Guarda metadata local de banners
    fun saveMeta(meta: BannerCacheMeta) {
        val metaFile = File(context.filesDir, FILE_META)
        metaFile.writer().use { writer ->
            gson.toJson(meta, writer)
            writer.flush()
        }
    }

    companion object {
        private const val TAG = "BannerRepository"
        private const val FILE_META = "banners_meta.json"
        private const val DIR_BANNERS = "banners"
    }
}
