package com.example.verificadordepreciosluz.data.network

import com.example.verificadordepreciosluz.BuildConfig
import com.example.verificadordepreciosluz.data.model.UpdateInfo
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Url
import java.util.concurrent.TimeUnit

interface UpdateApiService {
    @GET
    suspend fun checkUpdate(@Url url: String): UpdateInfo

    @GET
    suspend fun downloadUpdate(@Url url: String): okhttp3.ResponseBody
}

object UpdateService {
    private const val BASE_URL = "https://tavorl25.github.io/VerificadorDePreciosLuz"
    private const val UPDATE_PATH = "/version.json"

    private val client: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        OkHttpClient.Builder()
            .callTimeout(30, TimeUnit.SECONDS)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl("$BASE_URL/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    private val api: UpdateApiService by lazy {
        retrofit.create(UpdateApiService::class.java)
    }

    fun getCurrentVersion(): String {
        return BuildConfig.VERSION_NAME
    }

    suspend fun checkForUpdate(): Result<UpdateInfo> {
        return try {
            val response = api.checkUpdate("$BASE_URL$UPDATE_PATH")
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun shouldUpdate(remoteVersion: String): Boolean {
        return compareVersions(remoteVersion, getCurrentVersion()) > 0
    }

    fun requiresForcedUpdate(remoteMinVersion: String?): Boolean {
        if (remoteMinVersion.isNullOrEmpty()) return false
        return compareVersions(getCurrentVersion(), remoteMinVersion) < 0
    }

    private fun compareVersions(v1: String, v2: String): Int {
        // Soporta versiones tipo "1.0.0" y fechas "20260410"
        val parts1 = parseVersionParts(v1)
        val parts2 = parseVersionParts(v2)
        val maxLen = maxOf(parts1.size, parts2.size)

        for (i in 0 until maxLen) {
            val p1 = parts1.getOrElse(i) { 0 }
            val p2 = parts2.getOrElse(i) { 0 }
            if (p1 != p2) return p1 - p2
        }
        return 0
    }
    
    private fun parseVersionParts(version: String): List<Int> {
        // Si es fecha (8 dígitos), convertir a formato comparable
        val cleaned = version.replace(".", "")
        if (cleaned.length == 8 && cleaned.all { it.isDigit() }) {
            // "20260410" -> [2026, 04, 10]
            return listOf(
                cleaned.substring(0, 4).toIntOrNull() ?: 0,
                cleaned.substring(4, 6).toIntOrNull() ?: 0,
                cleaned.substring(6, 8).toIntOrNull() ?: 0
            )
        }
        // Versión normal "1.0.0"
        return version.split(".").mapNotNull { it.toIntOrNull() }
    }

    fun getUpdateUrl(updateInfo: UpdateInfo): String {
        return updateInfo.downloadUrl.ifEmpty { "$BASE_URL/luzapp.apk" }
    }

    fun getChecksum(updateInfo: UpdateInfo): String {
        return updateInfo.checksum.replace(" ", "").replace("\n", "").lowercase()
    }
}
