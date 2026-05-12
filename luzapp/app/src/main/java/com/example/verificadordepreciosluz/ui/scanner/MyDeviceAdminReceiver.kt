package com.example.verificadordepreciosluz.ui.scanner

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.util.Log

class MyDeviceAdminReceiver : DeviceAdminReceiver() {

    companion object {
        private const val TAG = "MyDeviceAdminReceiver"
    }

    override fun onEnabled(context: Context, intent: Intent) {
        super.onEnabled(context, intent)
        Log.i(TAG, "Device Owner habilitado")
    }

    override fun onDisabled(context: Context, intent: Intent) {
        super.onDisabled(context, intent)
        Log.i(TAG, "Device Owner deshabilitado")
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        Log.w(TAG, "Solicitud de deshabilitación de Device Owner")
        return "Al deshabilitar el Device Owner, el modo kiosco déjará de funcionar."
    }

    override fun onReceive(context: Context, intent: Intent) {
        val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -1)
        if (status != -1) {
            val packageName = intent.getStringExtra(PackageInstaller.EXTRA_PACKAGE_NAME)
            when (status) {
                PackageInstaller.STATUS_SUCCESS -> {
                    Log.i(TAG, "Instalación completada exitosamente: $packageName")
                    val launchIntent = context.packageManager.getLaunchIntentForPackage(context.packageName)
                    if (launchIntent != null) {
                        launchIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                        context.startActivity(launchIntent)
                    }
                }
                PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                    Log.w(TAG, "Instalación requiere acción del usuario: $packageName")
                    val confirmIntent = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                    if (confirmIntent != null) {
                        confirmIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        context.startActivity(confirmIntent)
                    }
                }
                else -> {
                    val message = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)
                    Log.e(TAG, "Instalación fallida: status=$status message=$message package=$packageName")
                }
            }
            return
        }
        super.onReceive(context, intent)
    }
}
