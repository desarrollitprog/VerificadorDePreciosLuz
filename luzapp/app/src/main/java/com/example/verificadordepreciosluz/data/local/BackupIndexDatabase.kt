package com.example.verificadordepreciosluz.data.local

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class BackupIndexDatabase(context: Context) : SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {
    init {
        setWriteAheadLoggingEnabled(true)
    }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.rawQuery("PRAGMA busy_timeout=3000", null).close()
    }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE meta (`key` TEXT PRIMARY KEY, value TEXT)")
        db.execSQL("CREATE TABLE productos (sku TEXT PRIMARY KEY, idProducto INTEGER, nombre TEXT)")
        db.execSQL("CREATE TABLE precios (idProducto INTEGER, idEmpaque INTEGER, costoBase REAL, pvpBase REAL, pvpConversion REAL, indIva INTEGER)")
        // Tabla ofertas con referencia a idOfertaxProducto para join con vigencia
        db.execSQL("CREATE TABLE ofertas (idProducto INTEGER, idEmpaque INTEGER, pvpOferta REAL, pvpBaseOferta REAL, idProductoOfertaxSucursal INTEGER)")
        // Tabla ofertas_vigencia con fechas de vigencia
        db.execSQL("CREATE TABLE ofertas_vigencia (idOfertaxProducto INTEGER, indExpirado INTEGER, fechaInicioMs INTEGER, fechaFinMs INTEGER)")
        db.execSQL("CREATE TABLE ofertas_sucursal (idOfertaxProductoxSucursal INTEGER, idOfertaxProducto INTEGER)")
        db.execSQL("CREATE TABLE ofertas_detalles (idEmpaque INTEGER, idOfertaxProductoxSucursal INTEGER, indActivo INTEGER)")
        db.execSQL("CREATE TABLE impuestos_producto (idProducto INTEGER, idTasaImpuesto INTEGER, indActivo INTEGER)")
        db.execSQL("CREATE TABLE tasas_impuesto (idTasaImpuesto INTEGER PRIMARY KEY, tasa REAL)")

        db.execSQL("CREATE INDEX idx_productos_sku ON productos(sku)")
        db.execSQL("CREATE INDEX idx_precios_producto ON precios(idProducto)")
        db.execSQL("CREATE INDEX idx_ofertas_producto_empaque ON ofertas(idProducto, idEmpaque)")
        db.execSQL("CREATE INDEX idx_ofertas_vigencia_producto ON ofertas_vigencia(idOfertaxProducto)")
        db.execSQL("CREATE INDEX idx_ofertas_sucursal_producto ON ofertas_sucursal(idOfertaxProducto)")
        db.execSQL("CREATE INDEX idx_ofertas_detalles_empaque ON ofertas_detalles(idEmpaque)")
        db.execSQL("CREATE INDEX idx_impuestos_producto ON impuestos_producto(idProducto)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS meta")
        db.execSQL("DROP TABLE IF EXISTS productos")
        db.execSQL("DROP TABLE IF EXISTS precios")
        db.execSQL("DROP TABLE IF EXISTS ofertas")
        db.execSQL("DROP TABLE IF EXISTS ofertas_vigencia")
        db.execSQL("DROP TABLE IF EXISTS ofertas_sucursal")
        db.execSQL("DROP TABLE IF EXISTS ofertas_detalles")
        db.execSQL("DROP TABLE IF EXISTS impuestos_producto")
        db.execSQL("DROP TABLE IF EXISTS tasas_impuesto")
        onCreate(db)
    }

    companion object {
        private const val DB_NAME = "backup_index.db"
        private const val DB_VERSION = 4
    }
}
