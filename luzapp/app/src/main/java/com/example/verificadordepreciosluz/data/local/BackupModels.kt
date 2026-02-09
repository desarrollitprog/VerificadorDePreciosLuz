package com.example.verificadordepreciosluz.data.local

import com.google.gson.JsonDeserializationContext
import com.google.gson.JsonDeserializer
import com.google.gson.JsonElement
import com.google.gson.annotations.JsonAdapter
import com.google.gson.annotations.SerializedName
import java.lang.reflect.Type

// DTO principal para el respaldo

data class BackupResponse(
    @SerializedName("updated_at") val updatedAt: String?,
    @SerializedName("section") val section: String? = null,
    @SerializedName("offset") val offset: Int? = null,
    @SerializedName("limit") val limit: Int? = null,
    @SerializedName("has_more") val hasMore: Boolean? = null,
    @SerializedName("next_offset") val nextOffset: Int? = null,
    val productos: List<BackupProducto> = emptyList(),
    val precios: List<BackupPrecio> = emptyList(),
    val ofertas: List<BackupOferta> = emptyList(),
    @SerializedName("ofertas_vigencia") val ofertasVigencia: List<BackupOfertaVigencia> = emptyList(),
    @SerializedName("ofertas_sucursal") val ofertasSucursal: List<BackupOfertaSucursal> = emptyList(),
    @SerializedName("ofertas_detalles") val ofertasDetalles: List<BackupOfertaDetalle> = emptyList(),
    @SerializedName("impuestos_producto") val impuestosProducto: List<BackupImpuestoProducto> = emptyList(),
    @SerializedName("tasas_impuesto") val tasasImpuesto: List<BackupTasaImpuesto> = emptyList(),
)

data class BackupProducto(
    @SerializedName("IdProducto") val idProducto: Int,
    @SerializedName("SKU") val sku: String,
    @SerializedName("Nombre") val nombre: String,
)

data class BackupPrecio(
    @SerializedName("IdProductosXEmpaqueXSucursal") val idProductosXEmpaqueXSucursal: Long,
    @SerializedName("IdProducto") val idProducto: Int,
    @SerializedName("IdEmpaque") val idEmpaque: Int,
    @SerializedName("CostoBase") val costoBase: Double?,
    @SerializedName("PVPBase") val pvpBase: Double?,
    @SerializedName("PVPConversion") val pvpConversion: Double?,
    @SerializedName("IndIVA") val indIva: Boolean?,
    @SerializedName("FechaModifica") val fechaModifica: String? // <-- agregado
)

data class BackupOferta(
    @SerializedName("IdProductoOfertaxSucursal") val idProductoOfertaxSucursal: Long,
    @SerializedName("IdProducto") val idProducto: Int,
    @SerializedName("IdEmpaque") val idEmpaque: Int,
    @JsonAdapter(BooleanIntAdapter::class)
    @SerializedName("IndActivo") val indActivo: Int?,
    @SerializedName("PvpOferta") val pvpOferta: Double?,
    @SerializedName("PvpBaseOferta") val pvpBaseOferta: Double?,
)

data class BackupOfertaVigencia(
    @SerializedName("IdOfertaxProducto") val idOfertaxProducto: Int,
    @JsonAdapter(BooleanIntAdapter::class)
    @SerializedName("IndExpirado") val indExpirado: Int?,
    @SerializedName("FechaInicio") val fechaInicio: String?,
    @SerializedName("FechaFin") val fechaFin: String?,
)

data class BackupOfertaSucursal(
    @SerializedName("IdOfertaxProductoxSucursal") val idOfertaxProductoxSucursal: Int,
    @SerializedName("IdOfertaxProducto") val idOfertaxProducto: Int,
)

data class BackupOfertaDetalle(
    @SerializedName("IdOfertaxProductoxSucursalDetalle") val idOfertaxProductoxSucursalDetalle: Int,
    @SerializedName("IdEmpaque") val idEmpaque: Int,
    @SerializedName("IdOfertaxProductoxSucursal") val idOfertaxProductoxSucursal: Int,
    @JsonAdapter(BooleanIntAdapter::class)
    @SerializedName("IndActivo") val indActivo: Int?,
)

data class BackupImpuestoProducto(
    @SerializedName("IdProductoxImpuesto") val idProductoxImpuesto: Long,
    @SerializedName("IdProducto") val idProducto: Int,
    @SerializedName("IdTasaImpuesto") val idTasaImpuesto: Int,
    @JsonAdapter(BooleanIntAdapter::class)
    @SerializedName("IndActivo") val indActivo: Int?,
)

data class BackupTasaImpuesto(
    @SerializedName("IdTasaImpuesto") val idTasaImpuesto: Int,
    @SerializedName("Tasa") val tasa: Double?,
)

class BooleanIntAdapter : JsonDeserializer<Int?> {
    override fun deserialize(
        json: JsonElement,
        typeOfT: Type,
        context: JsonDeserializationContext
    ): Int? {
        if (json.isJsonNull) return null
        return when {
            json.isJsonPrimitive && json.asJsonPrimitive.isBoolean -> if (json.asBoolean) 1 else 0
            json.isJsonPrimitive && json.asJsonPrimitive.isNumber -> json.asInt
            json.isJsonPrimitive && json.asJsonPrimitive.isString -> json.asString.toIntOrNull()
            else -> null
        }
    }
}
