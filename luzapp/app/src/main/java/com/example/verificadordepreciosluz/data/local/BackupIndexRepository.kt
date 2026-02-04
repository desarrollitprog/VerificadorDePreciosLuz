package com.example.verificadordepreciosluz.data.local

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.google.gson.Gson
import com.google.gson.stream.JsonReader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class BackupIndexRepository(private val context: Context) {
    private val gson = Gson()
    private val dbHelper = BackupIndexDatabase(context)
    private val dbLock = Any()

    suspend fun ensureIndex(updatedAt: String?) {
        if (updatedAt.isNullOrBlank()) return
        if (isIndexUpToDate(updatedAt)) return
        rebuildIndex(updatedAt)
    }

    fun isIndexUpToDate(updatedAt: String?): Boolean {
        if (updatedAt.isNullOrBlank()) return false
        synchronized(dbLock) {
            dbHelper.readableDatabase.use { db ->
                db.rawQuery("SELECT value FROM meta WHERE `key`='updatedAt' LIMIT 1", null).use { cursor ->
                    if (!cursor.moveToFirst()) return false
                    return cursor.getString(0) == updatedAt
                }
            }
        }
    }

    suspend fun rebuildIndex(updatedAt: String?) = withContext(Dispatchers.IO) {
        if (updatedAt.isNullOrBlank()) return@withContext
        synchronized(dbLock) {
            dbHelper.writableDatabase.use { db ->
                db.beginTransaction()
                try {
                    clearTables(db)
                    insertProductos(db)
                    insertPrecios(db)
                    insertOfertas(db)
                    insertOfertasVigencia(db)
                    insertOfertasSucursal(db)
                    insertOfertasDetalles(db)
                    insertImpuestosProducto(db)
                    insertTasasImpuesto(db)
                    saveMeta(db, updatedAt)
                    db.setTransactionSuccessful()
                    Log.i(TAG, "Índice local actualizado")
                } catch (e: Exception) {
                    Log.e(TAG, "Error reconstruyendo índice local", e)
                } finally {
                    db.endTransaction()
                }
            }
        }
    }

    fun lookupProductoOffline(sku: String): ProductoResponse? {
        synchronized(dbLock) {
            dbHelper.readableDatabase.use { db ->
                val producto = queryProducto(db, sku) ?: return null
                val precio = queryBestPrecio(db, producto.idProducto) ?: return null
                val oferta = queryBestOferta(db, producto.idProducto, precio.idEmpaque)
                val ofertaVigente = oferta != null && isOfertaVigente(db, precio.idEmpaque)
                val tasa = queryTasaImpuesto(db, producto.idProducto, precio.indIva)
                val factor = if (tasa != null) 1 + (tasa / 100.0) else 1.0

                val pvpBase = precio.pvpBase?.times(factor)
                val rawConversion = precio.pvpConversion?.times(factor)
                val pvpConversion = if (rawConversion != null && rawConversion > 0.0) rawConversion else pvpBase
                val pvpOferta = oferta?.pvpOferta?.times(factor)
                val pvpBaseOferta = oferta?.pvpBaseOferta?.times(factor)

                return ProductoResponse(
                    idProducto = producto.idProducto,
                    sku = producto.sku,
                    nombre = producto.nombre,
                    pvpBase = if (ofertaVigente) null else pvpBase,
                    pvpConversion = if (ofertaVigente) null else pvpConversion,
                    indIva = if (precio.indIva == true) 1 else 0,
                    pvpOferta = if (ofertaVigente) pvpOferta else null,
                    pvpBaseOferta = if (ofertaVigente) pvpBaseOferta else null,
                    idEmpaque = precio.idEmpaque,
                    idTasaImpuesto = null,
                    ivaIncluidoBs = null,
                    precioFinalConIva = null,
                )
            }
        }
    }

    private fun clearTables(db: android.database.sqlite.SQLiteDatabase) {
        db.execSQL("DELETE FROM meta")
        db.execSQL("DELETE FROM productos")
        db.execSQL("DELETE FROM precios")
        db.execSQL("DELETE FROM ofertas")
        db.execSQL("DELETE FROM ofertas_vigencia")
        db.execSQL("DELETE FROM ofertas_sucursal")
        db.execSQL("DELETE FROM ofertas_detalles")
        db.execSQL("DELETE FROM impuestos_producto")
        db.execSQL("DELETE FROM tasas_impuesto")
    }

    private fun insertProductos(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT OR REPLACE INTO productos (sku, idProducto, nombre) VALUES (?, ?, ?)")
        streamArray(FILE_PRODUCTOS) { item: BackupProducto ->
            stmt.bindString(1, item.sku)
            stmt.bindLong(2, item.idProducto.toLong())
            stmt.bindString(3, item.nombre)
            stmt.executeInsert()
        }
    }

    private fun insertPrecios(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO precios (idProducto, idEmpaque, costoBase, pvpBase, pvpConversion, indIva) VALUES (?, ?, ?, ?, ?, ?)")
        streamArray(FILE_PRECIOS) { item: BackupPrecio ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idEmpaque.toLong())
            bindDoubleOrNull(stmt, 3, item.costoBase)
            bindDoubleOrNull(stmt, 4, item.pvpBase)
            bindDoubleOrNull(stmt, 5, item.pvpConversion)
            bindIntOrNull(stmt, 6, item.indIva?.let { if (it) 1 else 0 })
            stmt.executeInsert()
        }
    }

    private fun insertOfertas(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas (idProducto, idEmpaque, pvpOferta, pvpBaseOferta) VALUES (?, ?, ?, ?)")
        streamArray(FILE_OFERTAS) { item: BackupOferta ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idEmpaque.toLong())
            bindDoubleOrNull(stmt, 3, item.pvpOferta)
            bindDoubleOrNull(stmt, 4, item.pvpBaseOferta)
            stmt.executeInsert()
        }
    }

    private fun insertOfertasVigencia(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_vigencia (idOfertaxProducto, indExpirado, fechaInicioMs, fechaFinMs) VALUES (?, ?, ?, ?)")
        streamArray(FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            stmt.bindLong(1, item.idOfertaxProducto.toLong())
            bindIntOrNull(stmt, 2, item.indExpirado)
            bindLongOrNull(stmt, 3, parseIsoToMillis(item.fechaInicio))
            bindLongOrNull(stmt, 4, parseIsoToMillis(item.fechaFin))
            stmt.executeInsert()
        }
    }

    private fun insertOfertasSucursal(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_sucursal (idOfertaxProductoxSucursal, idOfertaxProducto) VALUES (?, ?)")
        streamArray(FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            stmt.bindLong(1, item.idOfertaxProductoxSucursal.toLong())
            stmt.bindLong(2, item.idOfertaxProducto.toLong())
            stmt.executeInsert()
        }
    }

    private fun insertOfertasDetalles(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_detalles (idEmpaque, idOfertaxProductoxSucursal, indActivo) VALUES (?, ?, ?)")
        streamArray(FILE_OFERTAS_DETALLES) { item: BackupOfertaDetalle ->
            stmt.bindLong(1, item.idEmpaque.toLong())
            stmt.bindLong(2, item.idOfertaxProductoxSucursal.toLong())
            bindIntOrNull(stmt, 3, item.indActivo)
            stmt.executeInsert()
        }
    }

    private fun insertImpuestosProducto(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO impuestos_producto (idProducto, idTasaImpuesto, indActivo) VALUES (?, ?, ?)")
        streamArray(FILE_IMPUESTOS) { item: BackupImpuestoProducto ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idTasaImpuesto.toLong())
            bindIntOrNull(stmt, 3, item.indActivo)
            stmt.executeInsert()
        }
    }

    private fun insertTasasImpuesto(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT OR REPLACE INTO tasas_impuesto (idTasaImpuesto, tasa) VALUES (?, ?)")
        streamArray(FILE_TASAS) { item: BackupTasaImpuesto ->
            stmt.bindLong(1, item.idTasaImpuesto.toLong())
            bindDoubleOrNull(stmt, 2, item.tasa)
            stmt.executeInsert()
        }
    }

    private fun saveMeta(db: android.database.sqlite.SQLiteDatabase, updatedAt: String) {
        val values = ContentValues().apply {
            put("key", "updatedAt")
            put("value", updatedAt)
        }
        db.insertWithOnConflict("meta", null, values, android.database.sqlite.SQLiteDatabase.CONFLICT_REPLACE)
    }

    private fun queryProducto(db: android.database.sqlite.SQLiteDatabase, sku: String): ProductoRow? {
        db.rawQuery("SELECT idProducto, sku, nombre FROM productos WHERE sku = ? LIMIT 1", arrayOf(sku)).use { cursor ->
            if (!cursor.moveToFirst()) return null
            return ProductoRow(
                idProducto = cursor.getInt(0),
                sku = cursor.getString(1),
                nombre = cursor.getString(2)
            )
        }
    }

    private fun queryBestPrecio(db: android.database.sqlite.SQLiteDatabase, idProducto: Int): PrecioRow? {
        val sql = """
            SELECT idEmpaque, costoBase, pvpBase, pvpConversion, indIva
            FROM precios
            WHERE idProducto = ?
              AND (costoBase IS NULL OR costoBase > 0)
              AND (pvpBase IS NULL OR pvpBase > 0)
            ORDER BY (CASE WHEN pvpConversion > 0 THEN 1 ELSE 0 END) DESC,
                     pvpBase DESC
            LIMIT 1
        """.trimIndent()
        db.rawQuery(sql, arrayOf(idProducto.toString())).use { cursor ->
            if (!cursor.moveToFirst()) return null
            return PrecioRow(
                idEmpaque = cursor.getInt(0),
                costoBase = cursor.getDoubleOrNull(1),
                pvpBase = cursor.getDoubleOrNull(2),
                pvpConversion = cursor.getDoubleOrNull(3),
                indIva = cursor.getIntOrNull(4)?.let { it == 1 }
            )
        }
    }

    private fun queryBestOferta(db: android.database.sqlite.SQLiteDatabase, idProducto: Int, idEmpaque: Int): OfertaRow? {
        val sql = """
            SELECT pvpOferta, pvpBaseOferta
            FROM ofertas
            WHERE idProducto = ? AND idEmpaque = ?
            ORDER BY (CASE WHEN pvpOferta > 0 THEN 1 ELSE 0 END) DESC,
                     pvpOferta DESC,
                     pvpBaseOferta DESC
            LIMIT 1
        """.trimIndent()
        db.rawQuery(sql, arrayOf(idProducto.toString(), idEmpaque.toString())).use { cursor ->
            if (!cursor.moveToFirst()) return null
            return OfertaRow(
                pvpOferta = cursor.getDoubleOrNull(0),
                pvpBaseOferta = cursor.getDoubleOrNull(1)
            )
        }
    }

    private fun isOfertaVigente(db: android.database.sqlite.SQLiteDatabase, idEmpaque: Int): Boolean {
        val now = System.currentTimeMillis()
        val sql = """
            SELECT 1
            FROM ofertas_vigencia v
            JOIN ofertas_sucursal s ON v.idOfertaxProducto = s.idOfertaxProducto
            JOIN ofertas_detalles d ON s.idOfertaxProductoxSucursal = d.idOfertaxProductoxSucursal
            WHERE d.idEmpaque = ?
              AND (v.indExpirado IS NULL OR v.indExpirado != 1)
              AND (v.fechaInicioMs IS NULL OR v.fechaInicioMs <= ?)
              AND (v.fechaFinMs IS NULL OR v.fechaFinMs >= ?)
            LIMIT 1
        """.trimIndent()
        db.rawQuery(sql, arrayOf(idEmpaque.toString(), now.toString(), now.toString())).use { cursor ->
            return cursor.moveToFirst()
        }
    }

    private fun queryTasaImpuesto(db: android.database.sqlite.SQLiteDatabase, idProducto: Int, indIva: Boolean?): Double? {
        if (indIva != true) return null
        val sql = """
            SELECT t.tasa
            FROM impuestos_producto i
            JOIN tasas_impuesto t ON i.idTasaImpuesto = t.idTasaImpuesto
            WHERE i.idProducto = ? AND (i.indActivo IS NULL OR i.indActivo = 1)
            LIMIT 1
        """.trimIndent()
        db.rawQuery(sql, arrayOf(idProducto.toString())).use { cursor ->
            if (!cursor.moveToFirst()) return null
            return cursor.getDoubleOrNull(0)
        }
    }

    private fun parseIsoToMillis(value: String?): Long? {
        if (value.isNullOrBlank()) return null
        val clean = value.replace("Z", "").substringBefore(".")
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
            sdf.timeZone = TimeZone.getTimeZone("UTC")
            sdf.parse(clean)?.time
        } catch (_: Exception) {
            null
        }
    }

    private inline fun <reified T> streamArray(fileName: String, crossinline onItem: (T) -> Unit) {
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

    private fun bindDoubleOrNull(stmt: android.database.sqlite.SQLiteStatement, index: Int, value: Double?) {
        if (value == null) stmt.bindNull(index) else stmt.bindDouble(index, value)
    }

    private fun bindLongOrNull(stmt: android.database.sqlite.SQLiteStatement, index: Int, value: Long?) {
        if (value == null) stmt.bindNull(index) else stmt.bindLong(index, value)
    }

    private fun bindIntOrNull(stmt: android.database.sqlite.SQLiteStatement, index: Int, value: Int?) {
        if (value == null) stmt.bindNull(index) else stmt.bindLong(index, value.toLong())
    }

    private data class ProductoRow(val idProducto: Int, val sku: String, val nombre: String)
    private data class PrecioRow(
        val idEmpaque: Int,
        val costoBase: Double?,
        val pvpBase: Double?,
        val pvpConversion: Double?,
        val indIva: Boolean?,
    )
    private data class OfertaRow(val pvpOferta: Double?, val pvpBaseOferta: Double?)

    companion object {
        private const val TAG = "BackupIndexRepository"
        private const val FILE_PRODUCTOS = "backup_productos.json"
        private const val FILE_PRECIOS = "backup_precios.json"
        private const val FILE_OFERTAS = "backup_ofertas.json"
        private const val FILE_OFERTAS_VIGENCIA = "backup_ofertas_vigencia.json"
        private const val FILE_OFERTAS_SUCURSAL = "backup_ofertas_sucursal.json"
        private const val FILE_OFERTAS_DETALLES = "backup_ofertas_detalles.json"
        private const val FILE_IMPUESTOS = "backup_impuestos.json"
        private const val FILE_TASAS = "backup_tasas.json"
    }
}

private fun Cursor.getDoubleOrNull(index: Int): Double? {
    return if (isNull(index)) null else getDouble(index)
}

private fun Cursor.getIntOrNull(index: Int): Int? {
    return if (isNull(index)) null else getInt(index)
}
