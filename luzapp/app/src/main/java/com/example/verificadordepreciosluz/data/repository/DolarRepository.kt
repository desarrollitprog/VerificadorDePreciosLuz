package com.example.verificadordepreciosluz.data.repository

import android.util.Log
import com.example.verificadordepreciosluz.data.model.CotizacionesResponse
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.security.cert.X509Certificate
import java.security.SecureRandom
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

class DolarRepository {
    
    companion object {
        private const val TAG = "DolarRepository"
        private const val DOLAR_API_URL = "https://ve.dolarapi.com/v1/cotizaciones"
        private const val MAX_RETRIES = 3
        private const val CONNECT_TIMEOUT = 30000  // 30 segundos
        private const val READ_TIMEOUT = 30000     // 30 segundos
    }
    
    private val gson = Gson()
    
    // OkHttpClient con TrustManager que acepta todos los certificados
    // (necesario para ve.dolarapi.com que tiene problemas de certificado SSL)
    private val unsafeClient: OkHttpClient by lazy {
        val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        })
        
        val sslContext = SSLContext.getInstance("SSL")
        sslContext.init(null, trustAllCerts, SecureRandom())
        
        OkHttpClient.Builder()
            .connectTimeout(CONNECT_TIMEOUT.toLong(), TimeUnit.MILLISECONDS)
            .readTimeout(READ_TIMEOUT.toLong(), TimeUnit.MILLISECONDS)
            .sslSocketFactory(sslContext.socketFactory, trustAllCerts[0] as X509TrustManager)
            .hostnameVerifier { _, _ -> true }
            .build()
    }
    
    suspend fun getCotizaciones(): Map<String, CotizacionesResponse?> = withContext(Dispatchers.IO) {
        Log.d(TAG, ">>> getCotizaciones() iniciando con reintentos...")
        var lastException: Exception? = null
        
        for (attempt in 1..MAX_RETRIES) {
            try {
                Log.d(TAG, ">>> Intento $attempt/$MAX_RETRIES usando OkHttp")
                
                val request = Request.Builder()
                    .url(DOLAR_API_URL)
                    .addHeader("Accept", "application/json")
                    .build()
                
                unsafeClient.newCall(request).execute().use { response ->
                    val responseCode = response.code
                    Log.d(TAG, ">>> Response code: $responseCode")
                    
                    if (responseCode == 200) {
                        val responseBody = response.body?.string()
                        if (responseBody.isNullOrEmpty()) {
                            Log.e(TAG, ">>> Response body vacío en intento $attempt")
                            lastException = Exception("Response body vacío")
                        } else {
                            Log.d(TAG, ">>> Response body length: ${responseBody.length}")
                            
                            val listType = object : TypeToken<List<CotizacionesResponse>>() {}.type
                            val cotizaciones: List<CotizacionesResponse> = gson.fromJson(responseBody, listType)
                            Log.d(TAG, ">>> Parseadas ${cotizaciones.size} cotizaciones")
                            
                            val result = mutableMapOf<String, CotizacionesResponse?>()
                            for (cotizacion in cotizaciones) {
                                val monedaKey = cotizacion.moneda?.trim() ?: ""
                                if (monedaKey.isNotEmpty()) {
                                    result[monedaKey] = cotizacion
                                }
                            }
                            
                            Log.d(TAG, ">>> Éxito en intento $attempt, resultado: $result")
                            return@withContext result
                        }
                    } else {
                        Log.e(TAG, ">>> HTTP Error en intento $attempt: $responseCode")
                        lastException = Exception("HTTP $responseCode")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, ">>> Exception en intento $attempt: ${e.message}")
                lastException = e
            }
            
            // Si no es el último intento, esperar con backoff
            if (attempt < MAX_RETRIES) {
                val backoffMs = attempt * 5000L  // 5s, 10s
                Log.d(TAG, ">>> Esperando ${backoffMs/1000}s antes del siguiente intento...")
                delay(backoffMs)
            }
        }
        
        Log.e(TAG, ">>> Falló después de $MAX_RETRIES intentos. Último error: ${lastException?.message}")
        emptyMap()
    }
}
