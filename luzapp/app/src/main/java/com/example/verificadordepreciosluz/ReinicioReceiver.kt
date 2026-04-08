package com.example.verificadordepreciosluz.ui.scanner

import android.app.admin.DevicePolicyManager
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.example.verificadordepreciosluz.ui.scanner.MyDeviceAdminReceiver

class ReinicioReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.i("ReinicioReceiver", "Alarma de reinicio iniciada...")
        
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            val adminComponent = ComponentName(context, MyDeviceAdminReceiver::class.java)
            
            Log.i("ReinicioReceiver", "Intentando ejecutar reinicio...")
            dpm.reboot(adminComponent)
            Log.i("ReinicioReceiver", "Reinicio ejecutado")
        } catch (e: Exception) {
            Log.e("ReinicioReceiver", "Error al ejecutar reinicio: ${e.message}")
        }
        
        // Reprogramar para mañana si es recurrente
        try {
            val prefs = context.getSharedPreferences("reinicio_config", Context.MODE_PRIVATE)
            val horaReinicio = prefs.getString("hora_reinicio", null)
            val esRecurrente = prefs.getBoolean("recurrente", false)
            
            if (horaReinicio != null && esRecurrente) {
                Log.i("ReinicioReceiver", "Reprogramando reinicio recurrente para mañana...")
                val handler = Handler(Looper.getMainLooper())
                handler.postDelayed({
                    try {
                        val scanActivityClass = Class.forName("com.example.verificadordepreciosluz.ui.scanner.ScanActivity")
                        val method = scanActivityClass.getMethod("programarReinicioRecurrente")
                        method.invoke(null)
                    } catch (e: Exception) {
                        Log.e("ReinicioReceiver", "Error al reprogramar: ${e.message}")
                    }
                }, 60000)
            }
        } catch (e: Exception) {
            Log.e("ReinicioReceiver", "Error al verificar recurrente: ${e.message}")
        }
    }
}