package com.example.verificadordepreciosluz.util

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log

object DeviceTypeHelper {
    private const val TAG = "DeviceTypeHelper"
    
    fun isTv(context: Context): Boolean {
        // 1. Verificar modo UI de televisión
        val uiModeManager = context.getSystemService(Context.UI_MODE_SERVICE) as? android.app.UiModeManager
        val isTvUiMode = uiModeManager?.currentModeType == android.content.res.Configuration.UI_MODE_TYPE_TELEVISION
        
        // 2. Verificar característica LEANBACK (Android TV)
        val packageManager = context.packageManager
        val hasLeanback = packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK)
        
        // 3. Fallback para FireTV (verificar fabricante)
        val isAmazon = Build.MANUFACTURER.equals("amazon", ignoreCase = true)
        
        val isTv = isTvUiMode || hasLeanback || isAmazon
        Log.d(TAG, "isTv: $isTv (uiMode=$isTvUiMode, leanback=$hasLeanback, amazon=$isAmazon)")
        return isTv
    }
}
