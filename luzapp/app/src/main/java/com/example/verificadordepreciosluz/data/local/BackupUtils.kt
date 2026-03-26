package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteStatement
import android.util.Log
import com.google.gson.Gson
import com.google.gson.stream.JsonReader
import org.threeten.bp.LocalDate
import org.threeten.bp.ZoneId
import org.threeten.bp.ZonedDateTime
import org.threeten.bp.format.DateTimeFormatter
import org.threeten.bp.format.DateTimeParseException
import java.io.File

object BackupUtils {
    const val TAG = "BackupUtils"
    val gson = Gson()

    @JvmStatic
    fun normalizarCodigoBarras(codigo: String): List<String> {
        val codigoLimpio = codigo.trim()
        val variantes = mutableListOf(codigoLimpio)
        
        if (codigoLimpio.all { it.isDigit() } && codigoLimpio.length < 13) {
            val cerosFaltantes = "0".repeat(13 - codigoLimpio.length)
            variantes.add(cerosFaltantes + codigoLimpio)
        }
        
        return variantes
    }

    @JvmStatic
    fun parseIsoToMillis(value: String?): Long? {
        if (value.isNullOrBlank()) return null
        val formatters = listOf(
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSSX"),  // 6 dígitos microsegundos
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSX"),    // 3 dígitos milisegundos
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssX"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd")
        )
        for (formatter in formatters) {
            try {
                val result = when (formatter) {
                    formatters[5] -> {
                        val localDate = LocalDate.parse(value, formatter)
                        localDate.atStartOfDay(ZoneId.of("UTC")).toInstant().toEpochMilli()
                    }
                    else -> {
                        val zonedDateTime = ZonedDateTime.parse(value, formatter.withZone(ZoneId.of("UTC")))
                        zonedDateTime.toInstant().toEpochMilli()
                    }
                }
                return result
            } catch (_: DateTimeParseException) {
            } catch (e: Exception) {
                Log.w(TAG, "Error convirtiendo fecha: $value", e)
            }
        }
        Log.w(TAG, "No se pudo convertir la fecha: $value")
        return null
    }

    @JvmStatic
    inline fun <reified T> streamArray(context: Context, fileName: String, crossinline onItem: (T) -> Unit) {
        val file = File(context.filesDir, fileName)
        if (!file.exists()) return
        file.reader().use { reader ->
            val jsonReader = JsonReader(reader)
            val adapter = gson.getAdapter(T::class.java)
            jsonReader.beginArray()
            while (jsonReader.hasNext()) {
                val item = adapter.read(jsonReader)
                if (item != null) {
                    onItem(item)
                }
            }
            jsonReader.endArray()
        }
    }
}

fun SQLiteStatement.bindOrNull(index: Int, value: Any?) {
    when (value) {
        null -> bindNull(index)
        is Long -> bindLong(index, value)
        is Int -> bindLong(index, value.toLong())
        is Double -> bindDouble(index, value)
        is String -> bindString(index, value)
    }
}

fun Cursor.getDoubleOrNull(index: Int): Double? {
    return if (isNull(index)) null else getDouble(index)
}

fun Cursor.getIntOrNull(index: Int): Int? {
    return if (isNull(index)) null else getInt(index)
}

fun Cursor.getLongOrNull(index: Int): Long? {
    return if (isNull(index)) null else getLong(index)
}
