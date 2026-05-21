package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.google.gson.stream.JsonWriter
import java.io.File
import java.io.IOException

class BackupRepository(
    private val context: Context,
    private val api: ApiService? = null,
) {
    private val gson = Gson()

    companion object {
        private const val TAG = "BackupRepository"
        private const val FILE_META = "backup_meta.json"
        private const val FILE_PRODUCTOS = "backup_productos.json"
        private const val FILE_PRECIOS = "backup_precios.json"
        private const val FILE_OFERTAS = "backup_ofertas.json"
        private const val FILE_OFERTAS_VIGENCIA = "backup_ofertas_vigencia.json"
        private const val FILE_OFERTAS_SUCURSAL = "backup_ofertas_sucursal.json"
        private const val FILE_OFERTAS_DETALLES = "backup_ofertas_detalles.json"
        private const val FILE_IMPUESTOS = "backup_impuestos.json"
        private const val FILE_TASAS = "backup_tasas.json"
        private const val FILE_BARRAS_ASOCIADAS = "backup_barras_asociadas.json"
    }

    interface BackupProgressListener {
        fun onProgress(section: String, offset: Int, received: Int, total: Int)
        fun onError(section: String, error: Throwable)
    }

    suspend fun downloadAndSaveBackup(progressListener: BackupProgressListener? = null): Result<BackupResponse> {
        return try {
            Log.i("BackupRepository", "Iniciando descarga de backup")
            val service = api ?: return Result.failure(IllegalStateException("ApiService no disponible"))
            val updatedAt = downloadSectionsToDisk(service, progressListener)
            Result.success(BackupResponse(updatedAt = updatedAt))
        } catch (e: Exception) {
            Log.e("BackupRepository", "Error descargando backup", e)
            progressListener?.onError("general", e)
            Result.failure(e)
        }
    }

    private val PACING_MS = 500L

    private suspend fun downloadSectionsToDisk(
        service: ApiService,
        progressListener: BackupProgressListener? = null
    ): String? {
        val sections = listOf(
            "productos", "precios", "ofertas", "ofertas_vigencia", "ofertas_sucursal",
            "ofertas_detalles", "impuestos_producto", "tasas_impuesto", "barras_asociadas"
        )
        val limit = 1000
        var updatedAt: String? = null

        for ((sectionIdx, section) in sections.withIndex()) {
            var offset = 0
            var totalForSection = 0
            val file = File(context.filesDir, "backup_${section}.json")
            val tempFile = File(context.filesDir, "backup_${section}.json.tmp")

            try {
                tempFile.bufferedWriter(bufferSize = 8192).use { writer ->
                    val jsonWriter = JsonWriter(writer)
                    jsonWriter.beginArray()

                    do {
                        val page = service.getBackupSection(section, offset, limit, null)
                        if (updatedAt == null) updatedAt = page.updatedAt

                        val items = getSectionItems(page, section)
                        for (item in items) {
                            gson.toJson(item, item.javaClass, jsonWriter)
                        }

                        totalForSection += items.size
                        progressListener?.onProgress(section, offset, items.size, totalForSection)
                        Log.i("BackupRepository", "backup section=$section offset=$offset received=${items.size}")

                        if (items.size < limit) break
                        offset += limit
                    } while (true)

                    jsonWriter.endArray()
                }

                if (file.exists()) file.delete()
                if (!tempFile.renameTo(file)) {
                    throw IOException("No se pudo renombrar ${tempFile.name} a ${file.name}")
                }

                if (sectionIdx < sections.size - 1) {
                    Thread.sleep(PACING_MS)
                }

            } catch (e: Exception) {
                tempFile.delete()
                progressListener?.onError(section, e)
                throw e
            }
        }

        writeMeta(updatedAt)
        return updatedAt
    }

    private fun getSectionItems(page: BackupResponse, section: String): List<Any> {
        return when (section) {
            "productos" -> page.productos
            "precios" -> page.precios
            "ofertas" -> page.ofertas
            "ofertas_vigencia" -> page.ofertasVigencia
            "ofertas_sucursal" -> page.ofertasSucursal
            "ofertas_detalles" -> page.ofertasDetalles
            "impuestos_producto" -> page.impuestosProducto
            "tasas_impuesto" -> page.tasasImpuesto
            "barras_asociadas" -> page.barrasAsociadas
            else -> emptyList()
        }
    }

    private fun countSectionItems(page: BackupResponse, section: String): Int {
        return when (section) {
            "productos" -> page.productos.size
            "precios" -> page.precios.size
            "ofertas" -> page.ofertas.size
            "ofertas_vigencia" -> page.ofertasVigencia.size
            "ofertas_sucursal" -> page.ofertasSucursal.size
            "ofertas_detalles" -> page.ofertasDetalles.size
            "impuestos_producto" -> page.impuestosProducto.size
            "tasas_impuesto" -> page.tasasImpuesto.size
            "barras_asociadas" -> page.barrasAsociadas.size
            else -> 0
        }
    }

    fun saveBackup(backup: BackupResponse) {
        val delayMs = 4000L  // 4 segundos entre cada sección
        
        writeSection(FILE_PRODUCTOS, backup.productos)
        Thread.sleep(delayMs)
        
        writeSection(FILE_PRECIOS, backup.precios)
        Thread.sleep(delayMs)
        
        writeSection(FILE_OFERTAS, backup.ofertas)
        Thread.sleep(delayMs)
        
        writeSection(FILE_OFERTAS_VIGENCIA, backup.ofertasVigencia)
        Thread.sleep(delayMs)
        
        writeSection(FILE_OFERTAS_SUCURSAL, backup.ofertasSucursal)
        Thread.sleep(delayMs)
        
        writeSection(FILE_OFERTAS_DETALLES, backup.ofertasDetalles)
        Thread.sleep(delayMs)
        
        writeSection(FILE_IMPUESTOS, backup.impuestosProducto)
        Thread.sleep(delayMs)
        
        writeSection(FILE_TASAS, backup.tasasImpuesto)
        Thread.sleep(delayMs)
        
        writeSection(FILE_BARRAS_ASOCIADAS, backup.barrasAsociadas)
        writeMeta(backup.updatedAt)
    }

    fun loadBackup(): BackupResponse? {
        val metaFile = File(context.filesDir, FILE_META)
        if (!metaFile.exists()) return null
        // Fallback: intentar cargar backup_prev si el principal falla
        val tryLoad: (File) -> BackupResponse? = { file ->
            try {
                val updatedAt = readMeta()
                val productos = readSection<BackupProducto>(FILE_PRODUCTOS)
                val precios = readSection<BackupPrecio>(FILE_PRECIOS)
                val ofertas = readSection<BackupOferta>(FILE_OFERTAS)
                // Validación de estructura y campos críticos
                if (productos.isEmpty() || precios.isEmpty()) {
                    Log.e("BackupRepository", "Backup inválido: productos o precios vacíos")
                    null
                } else if (precios.any { it.pvpBase == null || it.pvpBase == 0.0 }) {
                    Log.e("BackupRepository", "Backup inválido: precios nulos o en 0 detectados")
                    null
                } else {
                    BackupResponse(
                        updatedAt = updatedAt,
                        productos = productos,
                        precios = precios,
                        ofertas = ofertas,
                        ofertasVigencia = readSection<BackupOfertaVigencia>(FILE_OFERTAS_VIGENCIA),
                        ofertasSucursal = readSection<BackupOfertaSucursal>(FILE_OFERTAS_SUCURSAL),
                        ofertasDetalles = readSection<BackupOfertaDetalle>(FILE_OFERTAS_DETALLES),
                        impuestosProducto = readSection<BackupImpuestoProducto>(FILE_IMPUESTOS),
                        tasasImpuesto = readSection<BackupTasaImpuesto>(FILE_TASAS),
                        barrasAsociadas = readSection<BackupBarrasAsociadas>(FILE_BARRAS_ASOCIADAS),
                    )
                }
            } catch (e: Exception) {
                Log.e("BackupRepository", "Backup corrupto o incompleto: ${file.name}", e)
                null
            }
        }
        val backup = tryLoad(metaFile)
        if (backup != null) return backup
        // Intentar cargar backup_prev si el principal falla
        val prevFile = File(context.filesDir, "backup_prev.json")
        if (prevFile.exists()) {
            Log.w("BackupRepository", "Intentando cargar backup previo por fallo en el principal")
            return tryLoad(prevFile)
        }
        Log.e("BackupRepository", "No se pudo cargar ningún backup válido")
        return null
    }

    fun getUpdatedAt(): String? {
        return readMeta()
    }

    fun lookupProductoOffline(sku: String): ProductoResponse? {
        val producto = findProductoBySku(sku) ?: return null
        val precio = findBestPrecio(producto.idProducto) ?: return null
        val oferta = findBestOferta(producto.idProducto, precio.idEmpaque)

        val ofertaValida = oferta != null &&
            (oferta.pvpOferta ?: 0.0) > 0.0 &&
            (oferta.pvpBaseOferta ?: 0.0) > 0.0
        // Validar que la oferta seleccionada esté vigente en fechas
        val ofertaVigente = ofertaValida && isOfertaVigenteForOferta(oferta)

        val tasa = findTasaImpuesto(producto.idProducto, precio.indIva)
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

    // Nueva función: valida que la oferta esté vigente en fechas
    private fun isOfertaVigenteForOferta(oferta: BackupOferta?): Boolean {
        if (oferta == null) return false
        var vigente = false
        BackupUtils.streamArray(context, FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            if (item.idOfertaxProducto == oferta.idProductoOfertaxSucursal.toInt()) {
                val now = System.currentTimeMillis()
                val inicio = BackupUtils.parseIsoToMillis(item.fechaInicio)
                val fin = BackupUtils.parseIsoToMillis(item.fechaFin)
                val noExpirada = item.indExpirado != 1
                val cumpleInicio = inicio == null || now >= inicio
                val cumpleFin = fin == null || now <= fin
                if (noExpirada && cumpleInicio && cumpleFin) {
                    vigente = true
                }
            }
        }
        return vigente
    }

    private fun findProductoBySku(sku: String): BackupProducto? {
        var found: BackupProducto? = null
        BackupUtils.streamArray(context, FILE_PRODUCTOS) { item: BackupProducto ->
            if (found == null && item.sku == sku) {
                found = item
            }
        }
        return found
    }

    private fun findBestPrecio(idProducto: Int): BackupPrecio? {
        var best: BackupPrecio? = null
        BackupUtils.streamArray(context, FILE_PRECIOS) { item: BackupPrecio ->
            if (item.idProducto != idProducto) return@streamArray
            if ((item.costoBase ?: 0.0) <= 0.0 || (item.pvpBase ?: 0.0) <= 0.0) return@streamArray
            if (best == null) {
                best = item
                return@streamArray
            }
            val bestHasConversion = (best?.pvpConversion ?: 0.0) > 0.0
            val currentHasConversion = (item.pvpConversion ?: 0.0) > 0.0
            if (currentHasConversion && !bestHasConversion) {
                best = item
                return@streamArray
            }
            if (currentHasConversion == bestHasConversion) {
                val bestBase = best?.pvpBase ?: 0.0
                val currentBase = item.pvpBase ?: 0.0
                if (currentBase > bestBase) {
                    best = item
                }
            }
        }
        return best
    }

    private fun findBestOferta(idProducto: Int, idEmpaque: Int): BackupOferta? {
        var best: BackupOferta? = null
        val idsOfertaxProducto = mutableSetOf<Int>()
        BackupUtils.streamArray(context, FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            idsOfertaxProducto.add(item.idOfertaxProducto)
        }
        if (idsOfertaxProducto.isEmpty()) return null
        BackupUtils.streamArray(context, FILE_OFERTAS) { item: BackupOferta ->
            if (item.idProducto == idProducto && item.idEmpaque == idEmpaque &&
                idsOfertaxProducto.contains(item.idProductoOfertaxSucursal.toInt()) &&
                (item.indActivo == null || item.indActivo == 1)) {
                if (best == null) {
                    best = item
                    return@streamArray
                }
                val bestHasOferta = (best?.pvpOferta ?: 0.0) > 0.0
                val currentHasOferta = (item.pvpOferta ?: 0.0) > 0.0
                if (currentHasOferta && !bestHasOferta) {
                    best = item
                    return@streamArray
                }
                val bestOferta = best?.pvpOferta ?: 0.0
                val currentOferta = item.pvpOferta ?: 0.0
                if (currentOferta > bestOferta) {
                    best = item
                    return@streamArray
                }
                val bestBase = best?.pvpBaseOferta ?: 0.0
                val currentBase = item.pvpBaseOferta ?: 0.0
                if (currentBase > bestBase) {
                    best = item
                }
            }
        }
        return best
    }

    private fun findTasaImpuesto(idProducto: Int, indIva: Boolean?): Double? {
        if (indIva != true) return null
        var idTasa: Int? = null
        BackupUtils.streamArray(context, FILE_IMPUESTOS) { item: BackupImpuestoProducto ->
            if (item.idProducto == idProducto && item.indActivo == 1) {
                idTasa = item.idTasaImpuesto
            }
        }
        if (idTasa == null) return null
        var tasa: Double? = null
        BackupUtils.streamArray(context, FILE_TASAS) { item: BackupTasaImpuesto ->
            if (item.idTasaImpuesto == idTasa) {
                tasa = item.tasa
            }
        }
        return tasa
    }

    private fun isOfertaVigenteForEmpaque(idEmpaque: Int): Boolean {
        val idsSucursal = mutableSetOf<Int>()
        BackupUtils.streamArray(context, FILE_OFERTAS_DETALLES) { item: BackupOfertaDetalle ->
            if (item.idEmpaque == idEmpaque && (item.indActivo == null || item.indActivo == 1)) {
                idsSucursal.add(item.idOfertaxProductoxSucursal)
            }
        }
        if (idsSucursal.isEmpty()) return false

        val idsProducto = mutableSetOf<Int>()
        BackupUtils.streamArray(context, FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            if (idsSucursal.contains(item.idOfertaxProductoxSucursal)) {
                idsProducto.add(item.idOfertaxProducto)
            }
        }
        if (idsProducto.isEmpty()) return false

        val now = System.currentTimeMillis()
        var vigente = false
        BackupUtils.streamArray(context, FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            if (!idsProducto.contains(item.idOfertaxProducto)) return@streamArray
            val inicio = BackupUtils.parseIsoToMillis(item.fechaInicio)
            val fin = BackupUtils.parseIsoToMillis(item.fechaFin)
            val noExpirada = item.indExpirado != 1
            val cumpleInicio = inicio == null || now >= inicio
            val cumpleFin = fin == null || now <= fin
            if (noExpirada && cumpleInicio && cumpleFin) {
                vigente = true
            }
        }
        return vigente
    }

    private inline fun <reified T> readSection(fileName: String): List<T> {
        val file = File(context.filesDir, fileName)
        if (!file.exists()) return emptyList()
        return try {
            file.reader().use { reader ->
                val type = object : TypeToken<List<T>>() {}.type
                gson.fromJson(reader, type)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Sección corrupta $fileName", e)
            file.delete()
            emptyList()
        }
    }

    private fun writeMeta(updatedAt: String?) {
        writeJsonAtomic(FILE_META) { writer ->
            gson.toJson(BackupMeta(updatedAt), writer)
        }
    }

    private fun readMeta(): String? {
        val file = File(context.filesDir, FILE_META)
        if (!file.exists()) return null
        return try {
            file.reader().use { reader ->
                gson.fromJson(reader, BackupMeta::class.java)?.updatedAt
            }
        } catch (e: Exception) {
            Log.e("BackupRepository", "Meta corrupta, eliminando archivo", e)
            file.delete()
            null
        }
    }

    private fun <T> writeSection(fileName: String, data: List<T>) {
        writeJsonAtomic(fileName) { writer ->
            gson.toJson(data, writer)
        }
    }

    private inline fun writeJsonAtomic(fileName: String, writeBlock: (java.io.Writer) -> Unit) {
        val dir = context.filesDir
        val target = File(dir, fileName)
        val temp = File(dir, "$fileName.tmp")
        val maxRetries = 3
        val delayMs = 500L
        
        for (attempt in 1..maxRetries) {
            try {
                temp.writer().use { writer ->
                    writeBlock(writer)
                    writer.flush()
                }
                if (target.exists()) {
                    target.delete()
                }
                if (!temp.renameTo(target)) {
                    if (attempt == maxRetries) {
                        throw IllegalStateException("No se pudo reemplazar $fileName tras $maxRetries intentos")
                    }
                    Log.w("BackupRepository", "Reintento $attempt/$maxRetries para $fileName")
                    Thread.sleep(delayMs)
                    continue
                }
                Log.d("BackupRepository", "Escritura exitosa de $fileName en intento $attempt")
                return
            } catch (e: Exception) {
                Log.w("BackupRepository", "Error intento $attempt para $fileName: ${e.message}")
                try { temp.delete() } catch (_: Exception) {}
                if (attempt == maxRetries) {
                    Log.e("BackupRepository", "Error guardando $fileName de forma atómica tras $maxRetries intentos", e)
                    throw e
                }
                try { Thread.sleep(delayMs) } catch (_: Exception) {}
            }
        }
    }

    private fun deleteAllSections() {
        listOf(
            FILE_META,
            FILE_PRODUCTOS,
            FILE_PRECIOS,
            FILE_OFERTAS,
            FILE_OFERTAS_VIGENCIA,
            FILE_OFERTAS_SUCURSAL,
            FILE_OFERTAS_DETALLES,
            FILE_IMPUESTOS,
            FILE_TASAS,
        ).forEach { name ->
            File(context.filesDir, name).delete()
        }
    }

    private data class BackupMeta(
        val updatedAt: String?,
    )
}
