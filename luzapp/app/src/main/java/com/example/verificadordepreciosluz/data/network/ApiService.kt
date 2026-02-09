package com.example.verificadordepreciosluz.data.network

import com.google.gson.annotations.SerializedName
import com.example.verificadordepreciosluz.data.local.BackupResponse
import com.example.verificadordepreciosluz.util.NetworkUtils
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

// DTOs que mapean las respuestas del backend
data class PingResponse(
    val status: String
)

data class ProductoResponse(
    @SerializedName("id_producto") val idProducto: Int,
    val sku: String,
    val nombre: String,
    @SerializedName("pvp_base") val pvpBase: Double?,
    @SerializedName("pvp_conversion") val pvpConversion: Double?,
    @SerializedName("ind_iva") val indIva: Int?,
    @SerializedName("pvp_oferta") val pvpOferta: Double?,
    @SerializedName("pvp_base_oferta") val pvpBaseOferta: Double?,
    @SerializedName("id_empaque") val idEmpaque: Int?,
    @SerializedName("id_tasa_impuesto") val idTasaImpuesto: Int?,
    @SerializedName("iva_incluido_bs") val ivaIncluidoBs: Double?,
    @SerializedName("precio_final_con_iva") val precioFinalConIva: Double?
)

data class BannerResponse(
    val id: Int,
    val titulo: String?,
    val tipo: String,
    val url: String,
    @SerializedName("duracion_seg") val duracionSeg: Int?,
    val prioridad: Int?,
    @SerializedName("updated_at") val updatedAt: String?
)

interface ApiService {
    @GET("ping")
    suspend fun ping(@Query("device_id") deviceId: String): PingResponse

    @GET("backup")
    suspend fun backup(
        @Query("section") section: String,
        @Query("offset") offset: Int,
        @Query("limit") limit: Int,
    ): BackupResponse

    @GET("consultar/{codigo}")
    suspend fun consultar(@Path("codigo") codigo: String): ProductoResponse

    @GET("banners")
    suspend fun banners(): List<BannerResponse>

    @GET("backup")
    suspend fun getBackupSection(
        @Query("section") section: String,
        @Query("offset") offset: Int,
        @Query("limit") limit: Int,
        @Query("updated_since") updatedSince: String? = null
    ): BackupResponse
}

object ApiClient {
    fun create(baseUrl: String, enableLogs: Boolean = false): ApiService {
        val normalized = NetworkUtils.normalizeBase(baseUrl)
        val logging = HttpLoggingInterceptor().apply {
            level = if (enableLogs) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
        }
        val client = OkHttpClient.Builder()
            .callTimeout(30, TimeUnit.SECONDS)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
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
