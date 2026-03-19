package com.example.verificadordepreciosluz.data.model

import com.google.gson.annotations.SerializedName

data class DolarResponse(
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("fuente") val fuente: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("compra") val compra: Double?,
    @SerializedName("venta") val venta: Double?,
    @SerializedName("promedio") val promedio: Double?,
    @SerializedName("fechaActualizacion") val fechaActualizacion: String?
)

data class CotizacionesResponse(
    @SerializedName("moneda") val moneda: String?,
    @SerializedName("fuente") val fuente: String?,
    @SerializedName("nombre") val nombre: String?,
    @SerializedName("compra") val compra: Double?,
    @SerializedName("venta") val venta: Double?,
    @SerializedName("promedio") val promedio: Double?,
    @SerializedName("fechaActualizacion") val fechaActualizacion: String?
)
