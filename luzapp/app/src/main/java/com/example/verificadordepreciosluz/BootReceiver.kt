package com.example.verificadordepreciosluz

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.example.verificadordepreciosluz.util.DeviceTypeHelper

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i("BootReceiver", "Dispositivo encendido, iniciando aplicación...")
            
            // Iniciar servicio KioskService solo si es TV (FireTV)
            if (DeviceTypeHelper.detectDeviceType(context) == DeviceTypeHelper.DeviceType.TELEVISOR) {
                Log.i("BootReceiver", "Dispositivo TV detectado, iniciando KioskService...")
                val serviceIntent = Intent(context, KioskService::class.java)
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
            }
            
            // Siempre iniciar MainActivity
            val launchIntent = Intent(context, MainActivity::class.java)
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(launchIntent)
        }
    }
}

