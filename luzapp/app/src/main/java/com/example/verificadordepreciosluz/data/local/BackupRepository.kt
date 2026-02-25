package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.util.Log
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.example.verificadordepreciosluz.util.SyncPrefs
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.google.gson.stream.JsonReader
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

class BackupRepository(
    private val context: Context,
    private val api: ApiService? = null,
) {
    private val gson = Gson()

    interface BackupProgressListener {
        fun onProgress(section: String, offset: Int, received: Int, total: Int)
        fun onError(section: String, error: Throwable)
    }

    suspend fun downloadAndSaveBackup(progressListener: BackupProgressListener? = null): Result<BackupResponse> {
        return try {
            Log.i("BackupRepository", "Iniciando descarga de backup")
            val service = api ?: return Result.failure(IllegalStateException("ApiService no disponible"))
            val backup = downloadPagedBackup(service, progressListener)
            saveBackup(backup)
            Result.success(backup)
        } catch (e: Exception) {
            Log.e("BackupRepository", "Error descargando backup", e)
            progressListener?.onError("general", e)
            Result.failure(e)
        }
    }

    private suspend fun downloadPagedBackup(
        service: ApiService,
        progressListener: BackupProgressListener? = null
    ): BackupResponse {
        val productosMap = mutableMapOf<String, BackupProducto>()
        val preciosMap = mutableMapOf<String, BackupPrecio>()
        val ofertas = mutableListOf<BackupOferta>()
        val ofertasVigencia = mutableListOf<BackupOfertaVigencia>()
        val ofertasSucursal = mutableListOf<BackupOfertaSucursal>()
        val ofertasDetalles = mutableListOf<BackupOfertaDetalle>()
        val impuestosProducto = mutableListOf<BackupImpuestoProducto>()
        val tasasImpuesto = mutableListOf<BackupTasaImpuesto>()
        var updatedAt: String? = null
        val sections = listOf(
            "productos", "precios", "ofertas", "ofertas_vigencia", "ofertas_sucursal",
            "ofertas_detalles", "impuestos_producto", "tasas_impuesto"
        )
        val limit = 1000
        var maxFechaModifica: String? = null
        for (section in sections) {
            var totalItems = 0
            var offset = 0
            do {
                try {
                    val updatedSince = if (section == "precios") SyncPrefs.getFechaModifica(context) else null
                    val page = if (section == "precios") {
                        service.getBackupSection(section, offset, limit, updatedSince)
                    } else {
                        service.getBackupSection(section, offset, limit, null)
                    }
                    if (updatedAt == null) updatedAt = page.updatedAt
                    when (section) {
                        "productos" -> {
                            page.productos.forEach { item -> productosMap.putIfAbsent(item.sku, item) }
                            totalItems += page.productos.size
                        }
                        "precios" -> {
                            page.precios.forEach { item ->
                                val hasCosto = (item.costoBase ?: 0.0) > 0.0
                                val hasPvpBase = (item.pvpBase ?: 0.0) > 0.0
                                val hasPvpConversion = (item.pvpConversion ?: 0.0) > 0.0
                                if (!hasCosto || (!hasPvpBase && !hasPvpConversion)) return@forEach
                                val key = "${item.idProducto}:${item.idEmpaque}"
                                val existing = preciosMap[key]
                                if (existing == null) {
                                    preciosMap[key] = item
                                } else {
                                    val existingHasConversion = (existing.pvpConversion ?: 0.0) > 0.0
                                    val shouldReplace = when {
                                        hasPvpConversion && !existingHasConversion -> true
                                        hasPvpConversion == existingHasConversion ->
                                            (item.pvpBase ?: 0.0) > (existing.pvpBase ?: 0.0)
                                        else -> false
                                    }
                                    if (shouldReplace) {
                                        preciosMap[key] = item
                                    }
                                }
                                // Actualizar maxFechaModifica
                                if (!item.fechaModifica.isNullOrBlank()) {
                                    if (maxFechaModifica == null || item.fechaModifica > maxFechaModifica) {
                                        maxFechaModifica = item.fechaModifica
                                    }
                                }
                            }
                            totalItems += page.precios.size
                        }
                        "ofertas" -> { ofertas.addAll(page.ofertas); totalItems += page.ofertas.size }
                        "ofertas_vigencia" -> { ofertasVigencia.addAll(page.ofertasVigencia); totalItems += page.ofertasVigencia.size }
                        "ofertas_sucursal" -> { ofertasSucursal.addAll(page.ofertasSucursal); totalItems += page.ofertasSucursal.size }
                        "ofertas_detalles" -> { ofertasDetalles.addAll(page.ofertasDetalles); totalItems += page.ofertasDetalles.size }
                        "impuestos_producto" -> { impuestosProducto.addAll(page.impuestosProducto); totalItems += page.impuestosProducto.size }
                        "tasas_impuesto" -> { tasasImpuesto.addAll(page.tasasImpuesto); totalItems += page.tasasImpuesto.size }
                    }
                    val received = countSectionItems(page, section)
                    progressListener?.onProgress(section, offset, received, totalItems)
                    Log.i("BackupRepository", "backup section=$section offset=$offset received=$received")
                    if (received < limit) break
                    offset += limit
                } catch (e: Exception) {
                    progressListener?.onError(section, e)
                    throw e
                }
            } while (true)
        }
        // Guardar el máximo FechaModifica de precios si se descargó la sección
        if (maxFechaModifica != null) {
            SyncPrefs.saveFechaModifica(context, maxFechaModifica)
            Log.i("BackupRepository", "[downloadPagedBackup] Guardada maxFechaModifica precios: $maxFechaModifica")
        }
        return BackupResponse(
            updatedAt = updatedAt,
            productos = productosMap.values.toList(),
            precios = preciosMap.values.toList(),
            ofertas = ofertas,
            ofertasVigencia = ofertasVigencia,
            ofertasSucursal = ofertasSucursal,
            ofertasDetalles = ofertasDetalles,
            impuestosProducto = impuestosProducto,
            tasasImpuesto = tasasImpuesto,
        )
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
            else -> 0
        }
    }

    fun saveBackup(backup: BackupResponse) {
        writeMeta(backup.updatedAt)
        writeSection(FILE_PRODUCTOS, backup.productos)
        writeSection(FILE_PRECIOS, backup.precios)
        writeSection(FILE_OFERTAS, backup.ofertas)
        writeSection(FILE_OFERTAS_VIGENCIA, backup.ofertasVigencia)
        writeSection(FILE_OFERTAS_SUCURSAL, backup.ofertasSucursal)
        writeSection(FILE_OFERTAS_DETALLES, backup.ofertasDetalles)
        writeSection(FILE_IMPUESTOS, backup.impuestosProducto)
        writeSection(FILE_TASAS, backup.tasasImpuesto)
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
        // Buscar la vigencia de la oferta específica
        var vigente = false
        streamArray(FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            if (item.idOfertaxProducto == oferta.idProductoOfertaxSucursal.toInt()) {
                val now = System.currentTimeMillis()
                val inicio = parseIsoToMillis(item.fechaInicio)
                val fin = parseIsoToMillis(item.fechaFin)
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
        streamArray(FILE_PRODUCTOS) { item: BackupProducto ->
            if (found == null && item.sku == sku) {
                found = item
            }
        }
        return found
    }

    private fun findBestPrecio(idProducto: Int): BackupPrecio? {
        var best: BackupPrecio? = null
        streamArray(FILE_PRECIOS) { item: BackupPrecio ->
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
        // Obtener los ids de ofertas por sucursal para este producto y empaque
        val idsOfertaxProducto = mutableSetOf<Int>()
        streamArray(FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            // Relacionar por idProducto y idEmpaque si están presentes en el modelo
            idsOfertaxProducto.add(item.idOfertaxProducto)
        }
        if (idsOfertaxProducto.isEmpty()) return null
        streamArray(FILE_OFERTAS) { item: BackupOferta ->
            // Filtrar por idProducto, idEmpaque, idOfertaxProducto y solo ofertas activas
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
        streamArray(FILE_IMPUESTOS) { item: BackupImpuestoProducto ->
            if (item.idProducto == idProducto && item.indActivo == 1) {
                idTasa = item.idTasaImpuesto
            }
        }
        if (idTasa == null) return null
        var tasa: Double? = null
        streamArray(FILE_TASAS) { item: BackupTasaImpuesto ->
            if (item.idTasaImpuesto == idTasa) {
                tasa = item.tasa
            }
        }
        return tasa
    }

    private fun isOfertaVigenteForEmpaque(idEmpaque: Int): Boolean {
        val idsSucursal = mutableSetOf<Int>()
        streamArray(FILE_OFERTAS_DETALLES) { item: BackupOfertaDetalle ->
            // Filtrar solo detalles activos (IndActivo == 1 o nulo)
            if (item.idEmpaque == idEmpaque && (item.indActivo == null || item.indActivo == 1)) {
                idsSucursal.add(item.idOfertaxProductoxSucursal)
            }
        }
        if (idsSucursal.isEmpty()) return false

        val idsProducto = mutableSetOf<Int>()
        streamArray(FILE_OFERTAS_SUCURSAL) { item: BackupOfertaSucursal ->
            if (idsSucursal.contains(item.idOfertaxProductoxSucursal)) {
                idsProducto.add(item.idOfertaxProducto)
            }
        }
        if (idsProducto.isEmpty()) return false

        val now = System.currentTimeMillis()
        var vigente = false
        streamArray(FILE_OFERTAS_VIGENCIA) { item: BackupOfertaVigencia ->
            if (!idsProducto.contains(item.idOfertaxProducto)) return@streamArray
            val inicio = parseIsoToMillis(item.fechaInicio)
            val fin = parseIsoToMillis(item.fechaFin)
            val noExpirada = item.indExpirado != 1
            val cumpleInicio = inicio == null || now >= inicio
            val cumpleFin = fin == null || now <= fin
            if (noExpirada && cumpleInicio && cumpleFin) {
                vigente = true
            }
        }
        return vigente
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
        try {
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
        } catch (e: Exception) {
            Log.e("BackupRepository", "Sección corrupta $fileName, eliminando archivo", e)
            file.delete()
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

    private inline fun <reified T> readSection(fileName: String): List<T> {
        val file = File(context.filesDir, fileName)
        if (!file.exists()) return emptyList()
        return try {
            file.reader().use { reader ->
                val type = object : TypeToken<List<T>>() {}.type
                gson.fromJson(reader, type)
            }
        } catch (e: Exception) {
            Log.e("BackupRepository", "Sección corrupta $fileName, eliminando archivo", e)
            file.delete()
            emptyList()
        }
    }

    private inline fun writeJsonAtomic(fileName: String, writeBlock: (java.io.Writer) -> Unit) {
        val dir = context.filesDir
        val target = File(dir, fileName)
        val temp = File(dir, "$fileName.tmp")
        try {
            temp.writer().use { writer ->
                writeBlock(writer)
                writer.flush()
            }
            if (target.exists()) {
                target.delete()
            }
            if (!temp.renameTo(target)) {
                throw IllegalStateException("No se pudo reemplazar $fileName")
            }
        } catch (e: Exception) {
            Log.e("BackupRepository", "Error guardando $fileName de forma atómica", e)
            temp.delete()
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

    companion object {
        private const val FILE_META = "backup_meta.json"
        private const val FILE_PRODUCTOS = "backup_productos.json"
        private const val FILE_PRECIOS = "backup_precios.json"
        private const val FILE_OFERTAS = "backup_ofertas.json"
        private const val FILE_OFERTAS_VIGENCIA = "backup_ofertas_vigencia.json"
        private const val FILE_OFERTAS_SUCURSAL = "backup_ofertas_sucursal.json"
        private const val FILE_OFERTAS_DETALLES = "backup_ofertas_detalles.json"
        private const val FILE_IMPUESTOS = "backup_impuestos.json"
        private const val FILE_TASAS = "backup_tasas.json"
    }

    private data class BackupMeta(
        val updatedAt: String?,
    )
}
