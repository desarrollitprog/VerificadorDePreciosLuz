package com.example.verificadordepreciosluz.data.local

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.BannerResponse
import com.example.verificadordepreciosluz.data.local.BannerRepository

suspend fun ejecutarPurgaTotal(context: android.content.Context, api: ApiService, baseUrl: String) {
    withContext(Dispatchers.IO) {
        // Paso 1: Borrado de archivos locales
        val bannersDir = File(context.filesDir, "banners")
        if (bannersDir.exists() && bannersDir.isDirectory) {
            bannersDir.listFiles()?.forEach { it.delete() }
        }
        // Si tienes carpeta de videos, repite el proceso:
        val videosDir = File(context.filesDir, "videos")
        if (videosDir.exists() && videosDir.isDirectory) {
            videosDir.listFiles()?.forEach { it.delete() }
        }

        // Paso 2: Solicitar manifiesto actualizado al backend secundario
        val banners = api.banners() // Debe ser suspend fun banners(): List<BannerResponse>
        // Si tienes endpoint para videos, obtén la lista aquí

        // Paso 3: Descargar todos los archivos del manifiesto
        val repo = BannerRepository(context, api, baseUrl)
        banners.forEach { banner ->
            repo.downloadBanner(banner)
        }
        // Si tienes videos, descarga cada uno aquí
    }
}
