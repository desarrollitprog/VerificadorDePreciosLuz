package com.example.verificadordepreciosluz.data.repository

import android.util.Log
import com.example.verificadordepreciosluz.data.model.CotizacionesResponse
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

class DolarRepository {
    
    companion object {
        private const val TAG = "DolarRepository"
        private const val DOLAR_API_URL = "https://ve.dolarapi.com/v1/cotizaciones"
    }
    
    private val gson = Gson()
    
    suspend fun getCotizaciones(): Map<String, CotizacionesResponse?> = withContext(Dispatchers.IO) {
        Log.d(TAG, ">>> getCotizaciones() iniciando...")
        try {
            val url = URL(DOLAR_API_URL)
            Log.d(TAG, ">>> URL: $DOLAR_API_URL")
            
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 10000
            connection.setRequestProperty("Accept", "application/json")
            
            val responseCode = connection.responseCode
            Log.d(TAG, ">>> Response code: $responseCode")
            
            if (responseCode == HttpURLConnection.HTTP_OK) {
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                Log.d(TAG, ">>> Response body length: ${response.length}")
                Log.d(TAG, ">>> Response body: $response")
                
                val listType = object : TypeToken<List<CotizacionesResponse>>() {}.type
                val cotizaciones: List<CotizacionesResponse> = gson.fromJson(response, listType)
                Log.d(TAG, ">>> Parseadas ${cotizaciones.size} cotizaciones")
                
                val result = mutableMapOf<String, CotizacionesResponse?>()
                for (cotizacion in cotizaciones) {
                    val monedaKey = cotizacion.moneda?.trim() ?: ""
                    Log.d(TAG, ">>> Moneda: '$monedaKey', promedio: ${cotizacion.promedio}")
                    if (monedaKey.isNotEmpty()) {
                        result[monedaKey] = cotizacion
                    }
                }
                
                Log.d(TAG, ">>> Map resultado: $result")
                result
            } else {
                Log.e(TAG, ">>> HTTP Error: $responseCode")
                val errorStream = connection.errorStream?.bufferedReader()?.use { it.readText() }
                Log.e(TAG, ">>> Error body: $errorStream")
                emptyMap()
            }
        } catch (e: Exception) {
            Log.e(TAG, ">>> Exception en getCotizaciones", e)
            e.printStackTrace()
            emptyMap()
        }
    }
}
