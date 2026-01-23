package com.example.verificadordepreciosluz.data.network

import com.google.gson.annotations.SerializedName
import com.example.verificadordepreciosluz.util.NetworkUtils
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

// DTOs que mapean las respuestas del backend
data class PingResponse(
    val status: String
)

data class ProductoResponse(
    val id: Int,
    @SerializedName("codigo_barras") val codigoBarras: String,
    val nombre: String,
    val precio: Double,
    @SerializedName("precio_oferta") val precioOferta: Double?
)

interface ApiService {
    @GET("ping")
    suspend fun ping(): PingResponse

    @GET("consultar/{codigo}")
    suspend fun consultar(@Path("codigo") codigo: String): ProductoResponse
}

object ApiClient {
    fun create(baseUrl: String, enableLogs: Boolean = false): ApiService {
        val normalized = NetworkUtils.normalizeBase(baseUrl)
        val logging = HttpLoggingInterceptor().apply {
            level = if (enableLogs) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        }
        val client = OkHttpClient.Builder()
            .callTimeout(10, TimeUnit.SECONDS)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(5, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .addInterceptor(logging)
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl(normalized)
            .addConverterFactory(GsonConverterFactory.create())
            .client(client)
            .build()
        return retrofit.create(ApiService::class.java)
    }
}
