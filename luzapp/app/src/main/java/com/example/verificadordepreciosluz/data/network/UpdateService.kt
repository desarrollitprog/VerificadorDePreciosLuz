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
    private const val BASE_URL = "http://luzcadash.ddns.net"
    private const val UPDATE_PATH = "/updates/version.json"

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
        val parts1 = v1.split(".").mapNotNull { it.toIntOrNull() }
        val parts2 = v2.split(".").mapNotNull { it.toIntOrNull() }
        val maxLen = maxOf(parts1.size, parts2.size)

        for (i in 0 until maxLen) {
            val p1 = parts1.getOrElse(i) { 0 }
            val p2 = parts2.getOrElse(i) { 0 }
            if (p1 != p2) return p1 - p2
        }
        return 0
    }

    fun getUpdateUrl(updateInfo: UpdateInfo): String {
        return updateInfo.downloadUrl.ifEmpty { "$BASE_URL/updates/app-release.apk" }
    }

    fun getChecksum(updateInfo: UpdateInfo): String {
        return updateInfo.checksum.replace(" ", "").replace("\n", "").lowercase()
    }
}
