package com.example.verificadordepreciosluz.data.local

import android.content.ContentValues
import android.content.Context
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class BackupIndexRepository(private val context: Context) {
    private val gson = Gson()
    private val dbHelper = BackupIndexDatabase(context)
    private val dbLock = Any()

    private data class VigenciaInfo(
        val idOfertaxProducto: Int,
        val fechaInicioMs: Long?,
        val fechaFinMs: Long?,
        val indExpirado: Int?
    )

    private data class DetalleInfo(
        val idOfertaxProductoxSucursal: Int,
        val idOfertaxProducto: Int,
        val idEmpaque: Int
    )

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
                    if (!cursor.moveToFirst()) {
                        Log.d(TAG, "[INDEX] No hay meta, índice no está actualizado")
                        return false
                    }
                    val storedUpdatedAt = cursor.getString(0)
                    val result = storedUpdatedAt == updatedAt
                    Log.d(TAG, "[INDEX] updatedAt almacenado: $storedUpdatedAt, actualizado: $updatedAt, esActualizado: $result")
                    return result
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
                // Log de conteos de tablas
                val tableCounts = mutableMapOf<String, Int>()
                listOf("productos", "precios", "ofertas", "ofertas_vigencia", "ofertas_sucursal", "ofertas_detalles").forEach { table ->
                    db.rawQuery("SELECT COUNT(*) FROM $table", null).use { cursor ->
                        if (cursor.moveToFirst()) {
                            tableCounts[table] = cursor.getInt(0)
                        }
                    }
                }
                Log.d(TAG, "[OFFLINE] Conteo de tablas: $tableCounts")

                val producto = queryProducto(db, sku) ?: run {
                    Log.d(TAG, "[OFFLINE] Producto no encontrado para sku: $sku")
                    return null
                }
                Log.d(TAG, "[OFFLINE] Producto encontrado: id=${producto.idProducto}, nombre=${producto.nombre}")

                val precio = queryBestPrecio(db, producto.idProducto) ?: run {
                    Log.d(TAG, "[OFFLINE] Precio no encontrado para idProducto: ${producto.idProducto}")
                    return null
                }
                Log.d(TAG, "[OFFLINE] Precio encontrado: idEmpaque=${precio.idEmpaque}, pvpBase=${precio.pvpBase}")

                val oferta = queryBestOferta(db, producto.idProducto, precio.idEmpaque)
                Log.d(TAG, "[OFFLINE] Oferta encontrada: $oferta")

                val now = System.currentTimeMillis()
                Log.d(TAG, "[OFFLINE] Hora actual (ms): $now, fecha: ${java.util.Date(now)}")

                var fechaInicioMs: Long? = null
                var fechaFinMs: Long? = null

                if (oferta != null) {
                    val idProducto = producto.idProducto
                    val idEmpaque = precio.idEmpaque
                    Log.d(TAG, "[OFFLINE] Buscando vigencia para idProducto=$idProducto, idEmpaque=$idEmpaque, now=$now")
                    
                    // Paso 1: Buscar TODAS las ofertas vigentes en ofertas_vigencia
                    val vigentesSql = """
                        SELECT idOfertaxProducto, fechaInicioMs, fechaFinMs, indExpirado
                        FROM ofertas_vigencia
                        WHERE (indExpirado IS NULL OR indExpirado != 1)
                          AND (fechaInicioMs IS NULL OR fechaInicioMs <= ?)
                          AND (fechaFinMs IS NULL OR fechaFinMs >= ?)
                    """.trimIndent()
                    
                    val idsVigente = mutableListOf<VigenciaInfo>()
                    db.rawQuery(vigentesSql, arrayOf(now.toString(), now.toString())).use { cursor ->
                        while (cursor.moveToNext()) {
                            val idOp = cursor.getInt(0)
                            val inicio = cursor.getLongOrNull(1)
                            val fin = cursor.getLongOrNull(2)
                            val exp = cursor.getIntOrNull(3)
                            idsVigente.add(VigenciaInfo(idOp, inicio, fin, exp))
                        }
                    }
                    Log.d(TAG, "[OFFLINE] Paso 1: ${idsVigente.size} ofertas vigentes encontradas")
                    
                    if (idsVigente.isNotEmpty()) {
                        // Paso 2: Buscar en ofertas_sucursal - obtener IdOfertaxProductoxSucursal
                        val placeholders2 = idsVigente.joinToString(",") { _ -> "?" }
                        val idsArray2 = idsVigente.map { v -> v.idOfertaxProducto.toString() }.toTypedArray()
                        
                        val sucursalesSql = """
                            SELECT idOfertaxProductoxSucursal, idOfertaxProducto
                            FROM ofertas_sucursal
                            WHERE idOfertaxProducto IN ($placeholders2)
                        """.trimIndent()
                        
                        val idsSucursal = mutableListOf<Pair<Int, Int>>() // (idOfertaxProductoxSucursal, idOfertaxProducto)
                        db.rawQuery(sucursalesSql, idsArray2).use { cursor ->
                            while (cursor.moveToNext()) {
                                val idOps = cursor.getInt(0)
                                val idOp = cursor.getInt(1)
                                idsSucursal.add(Pair(idOps, idOp))
                            }
                        }
                        Log.d(TAG, "[OFFLINE] Paso 2: ${idsSucursal.size} registros en ofertas_sucursal")
                        
                        if (idsSucursal.isNotEmpty()) {
                            // Paso 3: Buscar en ofertas_detalles - obtener idEmpaque disponibles
                            val placeholders3 = idsSucursal.joinToString(",") { _ -> "?" }
                            val idsArray3 = idsSucursal.map { it.first.toString() }.toTypedArray()
                            
                            val detallesSql = """
                                SELECT idOfertaxProductoxSucursal, idEmpaque, indActivo
                                FROM ofertas_detalles
                                WHERE idOfertaxProductoxSucursal IN ($placeholders3)
                                  AND (indActivo IS NULL OR indActivo = 1)
                            """.trimIndent()
                            
                            val detallesEncontrados = mutableListOf<DetalleInfo>() // (idOfertaxProductoxSucursal, idOfertaxProducto, idEmpaque)
                            db.rawQuery(detallesSql, idsArray3).use { cursor ->
                                while (cursor.moveToNext()) {
                                    val idOpsDet = cursor.getInt(0)
                                    val idEmpDet = cursor.getInt(1)
                                    val indAct = cursor.getIntOrNull(2)
                                    // Buscar el idOfertaxProducto correspondiente
                                    val match = idsSucursal.find { it.first == idOpsDet }
                                    if (match != null && (indAct == null || indAct == 1)) {
                                        detallesEncontrados.add(DetalleInfo(idOpsDet, match.second, idEmpDet))
                                    }
                                }
                            }
                            Log.d(TAG, "[OFFLINE] Paso 3: ${detallesEncontrados.size} detalles encontrados")
                            
                            // Paso 4: Verificar si el idEmpaque del producto coincide con alguno de los detalles
                            val detalleMatch = detallesEncontrados.find { it.idEmpaque == idEmpaque }
                            if (detalleMatch != null) {
                                Log.d(TAG, "[OFFLINE] Paso 4: Coincidencia! idEmpaque=$idEmpaque, idOfertaxProducto=${detalleMatch.idOfertaxProducto}")
                                
                                // Buscar la vigencia correspondiente
                                val vigenciaMatch = idsVigente.find { v -> v.idOfertaxProducto == detalleMatch.idOfertaxProducto }
                                if (vigenciaMatch != null) {
                                    fechaInicioMs = vigenciaMatch.fechaInicioMs
                                    fechaFinMs = vigenciaMatch.fechaFinMs
                                    Log.d(TAG, "[OFFLINE] Vigencia encontrada! fechaInicioMs=$fechaInicioMs, fechaFinMs=$fechaFinMs")
                                }
                            } else {
                                Log.w(TAG, "[OFFLINE] Paso 4: No hay coincidencia de idEmpaque")
                            }
                        }
                    }
                    
                    if (fechaInicioMs == null && fechaFinMs == null) {
                        Log.w(TAG, "[OFFLINE] No se encontró vigencia después de los 4 pasos")
                    }
                } else {
                    Log.d(TAG, "[OFFLINE] No hay oferta para este producto")
                }

                val ofertaValida = oferta != null &&
                    (oferta.pvpOferta ?: 0.0) > 0.0 &&
                    (oferta.pvpBaseOferta ?: 0.0) > 0.0
                Log.d(TAG, "[OFFLINE] ofertaValida: $ofertaValida")

                val fechasValidas = fechaInicioMs != null || fechaFinMs != null
                Log.d(TAG, "[OFFLINE] fechasValidas: $fechasValidas (fechaInicioMs=$fechaInicioMs, fechaFinMs=$fechaFinMs)")

                val ofertaVigente = ofertaValida && fechasValidas && isWithinVigencia(now, fechaInicioMs, fechaFinMs)
                Log.d(TAG, "[OFFLINE] ofertaVigente: $ofertaVigente")

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

    private fun isWithinVigencia(now: Long, fechaInicioMs: Long?, fechaFinMs: Long?): Boolean {
        val nowDate = java.util.Calendar.getInstance().apply { timeInMillis = now }.let {
            java.util.Calendar.getInstance().apply {
                set(it.get(java.util.Calendar.YEAR), it.get(java.util.Calendar.MONTH), it.get(java.util.Calendar.DAY_OF_MONTH), 0, 0, 0)
                set(java.util.Calendar.MILLISECOND, 0)
            }
        }.timeInMillis
        
        return when {
            fechaInicioMs == null && fechaFinMs != null -> {
                val fechaFinDate = java.util.Calendar.getInstance().apply { timeInMillis = fechaFinMs }.let {
                    java.util.Calendar.getInstance().apply {
                        set(it.get(java.util.Calendar.YEAR), it.get(java.util.Calendar.MONTH), it.get(java.util.Calendar.DAY_OF_MONTH), 23, 59, 59)
                        set(java.util.Calendar.MILLISECOND, 999)
                    }
                }.timeInMillis
                nowDate <= fechaFinDate
            }
            fechaInicioMs != null && fechaFinMs == null -> now >= fechaInicioMs
            fechaInicioMs != null && fechaFinMs != null -> {
                val fechaInicioDate = java.util.Calendar.getInstance().apply { timeInMillis = fechaInicioMs }.let {
                    java.util.Calendar.getInstance().apply {
                        set(it.get(java.util.Calendar.YEAR), it.get(java.util.Calendar.MONTH), it.get(java.util.Calendar.DAY_OF_MONTH), 0, 0, 0)
                        set(java.util.Calendar.MILLISECOND, 0)
                    }
                }.timeInMillis
                val fechaFinDate = java.util.Calendar.getInstance().apply { timeInMillis = fechaFinMs }.let {
                    java.util.Calendar.getInstance().apply {
                        set(it.get(java.util.Calendar.YEAR), it.get(java.util.Calendar.MONTH), it.get(java.util.Calendar.DAY_OF_MONTH), 23, 59, 59)
                        set(java.util.Calendar.MILLISECOND, 999)
                    }
                }.timeInMillis
                nowDate >= fechaInicioDate && nowDate <= fechaFinDate
            }
            else -> false
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
        BackupUtils.streamArray(context, FILE_PRODUCTOS) { item: BackupProducto ->
            stmt.bindString(1, item.sku)
            stmt.bindLong(2, item.idProducto.toLong())
            stmt.bindString(3, item.nombre)
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertPrecios(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO precios (idProducto, idEmpaque, costoBase, pvpBase, pvpConversion, indIva) VALUES (?, ?, ?, ?, ?, ?)")
        BackupUtils.streamArray(context, FILE_PRECIOS) { item: BackupPrecio ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idEmpaque.toLong())
            stmt.bindOrNull(3, item.costoBase)
            stmt.bindOrNull(4, item.pvpBase)
            stmt.bindOrNull(5, item.pvpConversion)
            stmt.bindOrNull(6, item.indIva?.let { if (it) 1 else 0 })
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertOfertas(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas (idProducto, idEmpaque, pvpOferta, pvpBaseOferta, idProductoOfertaxSucursal) VALUES (?, ?, ?, ?, ?)")
        BackupUtils.streamArray(context, FILE_OFERTAS) { item: BackupOferta ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idEmpaque.toLong())
            stmt.bindOrNull(3, item.pvpOferta)
            stmt.bindOrNull(4, item.pvpBaseOferta)
            stmt.bindOrNull(5, item.idProductoOfertaxSucursal)
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertOfertasVigencia(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_vigencia (idOfertaxProducto, indExpirado, fechaInicioMs, fechaFinMs) VALUES (?, ?, ?, ?)")
        BackupUtils.streamArray(context, FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            val fechaInicioMs = BackupUtils.parseIsoToMillis(item.fechaInicio)
            val fechaFinMs = BackupUtils.parseIsoToMillis(item.fechaFin)
            Log.d(TAG, "[INSERT] ofertas_vigencia idOfertaxProducto=${item.idOfertaxProducto}, fechaInicio=${item.fechaInicio} -> $fechaInicioMs, fechaFin=${item.fechaFin} -> $fechaFinMs")
            
            stmt.bindLong(1, item.idOfertaxProducto.toLong())
            stmt.bindOrNull(2, item.indExpirado)
            stmt.bindOrNull(3, fechaInicioMs)
            stmt.bindOrNull(4, fechaFinMs)
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertOfertasSucursal(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_sucursal (idOfertaxProductoxSucursal, idOfertaxProducto) VALUES (?, ?)")
        BackupUtils.streamArray(context, FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            stmt.bindLong(1, item.idOfertaxProductoxSucursal.toLong())
            stmt.bindLong(2, item.idOfertaxProducto.toLong())
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertOfertasDetalles(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO ofertas_detalles (idEmpaque, idOfertaxProductoxSucursal, indActivo) VALUES (?, ?, ?)")
        BackupUtils.streamArray(context, FILE_OFERTAS_DETALLES) { item: BackupOfertaDetalle ->
            stmt.bindLong(1, item.idEmpaque.toLong())
            stmt.bindLong(2, item.idOfertaxProductoxSucursal.toLong())
            stmt.bindOrNull(3, item.indActivo)
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertImpuestosProducto(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT INTO impuestos_producto (idProducto, idTasaImpuesto, indActivo) VALUES (?, ?, ?)")
        BackupUtils.streamArray(context, FILE_IMPUESTOS) { item: BackupImpuestoProducto ->
            stmt.bindLong(1, item.idProducto.toLong())
            stmt.bindLong(2, item.idTasaImpuesto.toLong())
            stmt.bindOrNull(3, item.indActivo)
            stmt.executeInsert()
            stmt.clearBindings()
        }
    }

    private fun insertTasasImpuesto(db: android.database.sqlite.SQLiteDatabase) {
        val stmt = db.compileStatement("INSERT OR REPLACE INTO tasas_impuesto (idTasaImpuesto, tasa) VALUES (?, ?)")
        BackupUtils.streamArray(context, FILE_TASAS) { item: BackupTasaImpuesto ->
            stmt.bindLong(1, item.idTasaImpuesto.toLong())
            stmt.bindOrNull(2, item.tasa)
            stmt.executeInsert()
            stmt.clearBindings()
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
            if (!cursor.moveToFirst()) {
                Log.d(TAG, "[OFFLINE] No hay ofertas para idProducto=$idProducto, idEmpaque=$idEmpaque")
                return null
            }
            val row = OfertaRow(
                pvpOferta = cursor.getDoubleOrNull(0),
                pvpBaseOferta = cursor.getDoubleOrNull(1)
            )
            Log.d(TAG, "[OFFLINE] Oferta cruda: pvpOferta=${row.pvpOferta}, pvpBaseOferta=${row.pvpBaseOferta}")
            return row
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
