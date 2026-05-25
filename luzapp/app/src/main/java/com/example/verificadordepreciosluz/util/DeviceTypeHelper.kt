package com.example.verificadordepreciosluz.util

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log

object DeviceTypeHelper {
    private const val TAG = "DeviceTypeHelper"

    enum class DeviceType { TELEVISOR, VERIFICADOR }

    fun detectDeviceType(context: Context): DeviceType {
        val uiModeManager = context.getSystemService(Context.UI_MODE_SERVICE) as? android.app.UiModeManager
        val isTvUiMode = uiModeManager?.currentModeType == android.content.res.Configuration.UI_MODE_TYPE_TELEVISION

        val packageManager = context.packageManager
        val hasLeanback = packageManager.hasSystemFeature(PackageManager.FEATURE_LEANBACK)

        val isAmazon = Build.MANUFACTURER.equals("amazon", ignoreCase = true)

        val isTv = isTvUiMode || hasLeanback || isAmazon
        val type = if (isTv) DeviceType.TELEVISOR else DeviceType.VERIFICADOR
        Log.d(TAG, "detectDeviceType: $type (uiMode=$isTvUiMode, leanback=$hasLeanback, amazon=$isAmazon)")
        Log.d(TAG, "Build: MANUFACTURER=${Build.MANUFACTURER}, MODEL=${Build.MODEL}, PRODUCT=${Build.PRODUCT}, BOARD=${Build.BOARD}")
        return type
    }
}
