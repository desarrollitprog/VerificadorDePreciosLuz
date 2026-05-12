package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.BannerResponse
import com.google.gson.Gson
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

class BannerRepository(
    private val context: Context,
    private val api: ApiService,
    private val baseUrl: String,
) {
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

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
    suspend fun refreshIfStale(maxAgeMs: Long, deviceId: String? = null): BannerCacheMeta? {
        if (!shouldRefresh(maxAgeMs)) return loadCache()
        return runCatching {
            val remote = api.banners(deviceId).sortedBy { it.prioridad ?: 0 }
            val items = remote.mapNotNull { downloadBanner(it) }.toMutableList()
            if (items.isEmpty()) {
                Log.w(TAG, "No se pudo descargar ningún banner, se conserva el cache actual")
                context.getString(com.example.verificadordepreciosluz.R.string.msg_no_banners).let { Log.w(TAG, it) }
                return@runCatching loadCache()
            }
            val meta = BannerCacheMeta(
                lastSyncAt = System.currentTimeMillis(),
                items = items
            )
            cleanupExpiredBanners(meta)
            saveMeta(meta)
            meta
        }.onFailure {
            Log.e(TAG, "Error actualizando banners", it)
        }.getOrNull()
    }

    fun cleanupExpiredBanners(meta: BannerCacheMeta? = null) {
        val target = meta ?: loadCache() ?: return
        val before = target.items.size
        target.items.removeAll {
            it.fechaFinMs != null && System.currentTimeMillis() > it.fechaFinMs
        }
        if (target.items.size < before) {
            Log.i(TAG, "cleanupExpiredBanners: eliminados ${before - target.items.size} banners vencidos")
            if (meta == null) saveMeta(target)
        }
    }

    // Descarga un banner (imagen/video) y lo guarda en files/banners
    public fun downloadBanner(item: BannerResponse): BannerCacheItem? {
        val absoluteUrl = if (item.url.startsWith("http")) item.url else baseUrl.trimEnd('/') + "/" + item.url.trimStart('/')
        val safeUrl = absoluteUrl.replace(" ", "%20")
        val ext = absoluteUrl.substringAfterLast('.', "")
        val safeExt = ext.ifBlank { "bin" }
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

        // Verificación robusta tras descarga
        if (!outFile.exists()) {
            Log.w(TAG, "Archivo descargado no existe: ${outFile.absolutePath} (id=${item.id})")
            return null
        }
        val fileSize = outFile.length()
        if (fileSize == 0L) {
            Log.w(TAG, "Archivo descargado tiene tamaño 0: ${outFile.absolutePath} (id=${item.id}) - Eliminando archivo")
            outFile.delete()
            return null
        }
        if (!outFile.canRead()) {
            Log.w(TAG, "Archivo descargado no es legible: ${outFile.absolutePath} (id=${item.id}) - Eliminando archivo")
            outFile.delete()
            return null
        }
        // Verificación de tamaño mínimo para videos (al menos 10KB)
        if (item.tipo == "video" && fileSize < 10000) {
            Log.w(TAG, "Video demasiado pequeño (${fileSize} bytes), probablemente incompleto: ${outFile.absolutePath} (id=${item.id}) - Eliminando archivo")
            outFile.delete()
            return null
        }
        // Verificación adicional con MediaMetadataRetriever para videos
        if (item.tipo == "video") {
            try {
                val retriever = android.media.MediaMetadataRetriever()
                retriever.setDataSource(outFile.absolutePath)
                val duration = retriever.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION)
                retriever.release()
                if (duration == null) {
                    Log.w(TAG, "Video sin duración válida, probablemente corrupto: ${outFile.absolutePath} (id=${item.id}) - Eliminando archivo")
                    outFile.delete()
                    return null
                }
                Log.d(TAG, "Video verificado OK: ${outFile.absolutePath} (id=${item.id}) duration=${duration}ms")
            } catch (e: Exception) {
                Log.w(TAG, "No se pudo leer metadata del video: ${e.message} - ${outFile.absolutePath} (id=${item.id}) - Eliminando archivo")
                outFile.delete()
                return null
            }
        }
        Log.d(TAG, "Banner descargado OK: ${outFile.absolutePath} (id=${item.id}) size=${fileSize}")

        return BannerCacheItem(
            id = item.id,
            titulo = item.titulo,
            tipo = item.tipo,
            remoteUrl = item.url,
            localPath = outFile.absolutePath,
            duracionSeg = item.duracionSeg,
            prioridad = item.prioridad,
            fechaInicioMs = item.fechaInicioMs,
            fechaFinMs = item.fechaFinMs
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
