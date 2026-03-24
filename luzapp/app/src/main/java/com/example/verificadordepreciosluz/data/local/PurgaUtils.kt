package com.example.verificadordepreciosluz.data.local

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.BannerResponse
import com.example.verificadordepreciosluz.data.local.BannerRepository
import android.util.Log

data class PurgaResult(
    val success: Boolean,
    val reason: String? = null,
)

suspend fun ejecutarPurgaTotal(context: android.content.Context, api: ApiService, baseUrl: String, deviceId: String? = null, onPurgeComplete: (() -> Unit)? = null): PurgaResult {
    return withContext(Dispatchers.IO) {
        try {
            Log.d("PurgaTotal", "Iniciando purga total con deviceId: $deviceId")
            // Paso 1: Borrado de archivos locales
            val bannersDir = File(context.filesDir, "banners")
            Log.d("PurgaTotal", "Borrando archivos en: ${bannersDir.absolutePath}")
            if (bannersDir.exists() && bannersDir.isDirectory) {
                bannersDir.listFiles()?.forEach { it.delete() }
            }
            val videosDir = File(context.filesDir, "videos")
            Log.d("PurgaTotal", "Borrando archivos en: ${videosDir.absolutePath}")
            if (videosDir.exists() && videosDir.isDirectory) {
                videosDir.listFiles()?.forEach { it.delete() }
            }

            // Paso 2: Solicitar manifiesto actualizado al backend secundario
            Log.d("PurgaTotal", "Solicitando manifiesto de banners al backend con deviceId: $deviceId...")
            val banners = api.banners(deviceId)
            Log.d("PurgaTotal", "Manifiesto recibido: ${banners.size} items")
            if (banners.isEmpty()) {
                Log.w("PurgaTotal", "Manifiesto vacío. Nada que descargar.")
            }
            if (banners.size > 100) {
                Log.e("PurgaTotal", "Demasiados banners en el manifiesto (${banners.size}), abortando por seguridad.")
                return@withContext PurgaResult(
                    success = false,
                    reason = "Demasiados banners en manifiesto (${banners.size})",
                )
            }

            // Paso 3: Descargar todos los archivos del manifiesto
            val repo = BannerRepository(context, api, baseUrl)
            val items = mutableListOf<BannerCacheItem>()
            for ((i, banner) in banners.withIndex()) {
                try {
                    Log.d("PurgaTotal", "Descargando banner ${i+1}/${banners.size} id=${banner.id} url=${banner.url}")
                    val item = repo.downloadBanner(banner)
                    if (item != null) {
                        val file = File(item.localPath)
                        if (file.exists()) {
                            items.add(item)
                        } else {
                            Log.w("PurgaTotal", "Archivo descargado no existe: ${item.localPath} (id=${banner.id}) - No se agrega al cache")
                        }
                    }
                } catch (e: Exception) {
                    Log.e("PurgaTotal", "Error descargando banner id=${banner.id}: ${e.message}")
                }
            }
            Log.d("PurgaTotal", "Descargados ${items.size} de ${banners.size} banners tras purga via WebSocket")
            Log.d("PurgaTotal", "Ruta de guardado de banners: ${bannersDir.absolutePath}")
            Log.d("PurgaTotal", "Ruta de guardado de videos: ${videosDir.absolutePath}")
            // Actualizar el cache local con los nuevos items descargados
            val meta = BannerCacheMeta(
                lastSyncAt = System.currentTimeMillis(),
                items = items
            )
            repo.saveMeta(meta)
            Log.d("PurgaTotal", "Cache actualizado con ${items.size} items")
            // Notificar al hilo principal que la purga terminó (para reiniciar el carrusel)
            onPurgeComplete?.let {
                withContext(Dispatchers.Main) { it() }
            }
            Log.d("PurgaTotal", "Purga total finalizada")
            return@withContext PurgaResult(success = true)
        } catch (e: Exception) {
            Log.e("PurgaTotal", "Error fatal en purga: ${e.message}", e)
            return@withContext PurgaResult(
                success = false,
                reason = e.message ?: "Error fatal en purga",
            )
        }
    }
}
