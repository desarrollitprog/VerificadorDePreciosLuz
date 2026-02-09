package com.example.verificadordepreciosluz.util

import android.content.Context

object SyncPrefs {
    private const val KEY_LAST_FECHA_MODIFICA = "last_fecha_modifica_precios"
    private const val PREFS_NAME = "SyncPrefs"

    fun saveFechaModifica(context: Context, fecha: String) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit().putString(KEY_LAST_FECHA_MODIFICA, fecha).apply()
    }

    fun getFechaModifica(context: Context): String? {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(KEY_LAST_FECHA_MODIFICA, null)
    }
}

