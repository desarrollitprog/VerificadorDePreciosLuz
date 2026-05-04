package com.example.verificadordepreciosluz

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log

class HdmiScreenReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "HdmiScreenReceiver"
        
        // Constantes de acción (strings directos para evitar dependencias de constantes de Android que pueden faltar en FireOS)
        private const val ACTION_HDMI_PLUG = "android.intent.action.HDMI_AUDIO_PLUG"
        const val ACTION_HDMI_RECONNECTED = "com.example.verificadordepreciosluz.HDMI_RECONNECTED"
        const val ACTION_SCREEN_ON_LOCAL = "com.example.verificadordepreciosluz.SCREEN_ON"
        
        fun createIntentFilter(): IntentFilter {
            val filter = IntentFilter()
            filter.addAction(ACTION_HDMI_PLUG) // HDMI conectado/desconectado
            filter.addAction(Intent.ACTION_SCREEN_ON) // Pantalla encendida
            filter.addAction(Intent.ACTION_SCREEN_OFF) // Pantalla apagada
            return filter
        }
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_HDMI_PLUG -> {
                val state = intent.getIntExtra("state", 0)
                Log.i(TAG, "HDMI_AUDIO_PLUG: state=$state (${if (state == 1) "CONNECTED" else "DISCONNECTED"})")
                if (state == 1) handleHdmiReconnect(context)
            }
            Intent.ACTION_SCREEN_ON -> {
                Log.i(TAG, "SCREEN_ON: Pantalla encendida")
                handleScreenOn(context)
            }
            Intent.ACTION_SCREEN_OFF -> {
                Log.i(TAG, "SCREEN_OFF: Pantalla apagada")
            }
        }
    }
    
    private fun handleHdmiReconnect(context: Context) {
        Log.i(TAG, "HDMI reconectado - Relanzando MainActivity")
        // Broadcast local para notificar a otros componentes si es necesario
        val localIntent = Intent(ACTION_HDMI_RECONNECTED).apply {
            setPackage(context.packageName)
        }
        context.sendBroadcast(localIntent)
        
        // Relanzar la app
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        try {
            context.startActivity(launchIntent)
            Log.i(TAG, "MainActivity relanzada tras reconexión HDMI")
        } catch (e: Exception) {
            Log.e(TAG, "Error relanzando app: ${e.message}")
        }
    }
    
    private fun handleScreenOn(context: Context) {
        Log.i(TAG, "Pantalla encendida - Relanzando MainActivity")
        // Broadcast local
        val localIntent = Intent(ACTION_SCREEN_ON_LOCAL).apply {
            setPackage(context.packageName)
        }
        context.sendBroadcast(localIntent)
        
        // Relanzar la app
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        try {
            context.startActivity(launchIntent)
            Log.i(TAG, "MainActivity relanzada tras encender pantalla")
        } catch (e: Exception) {
            Log.e(TAG, "Error relanzando app: ${e.message}")
        }
    }
}
