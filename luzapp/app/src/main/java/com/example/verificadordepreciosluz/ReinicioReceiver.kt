package com.example.verificadordepreciosluz.ui.scanner

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
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
                reprogramarReinicio(context, horaReinicio)
            }
        } catch (e: Exception) {
            Log.e("ReinicioReceiver", "Error al verificar recurrente: ${e.message}")
        }
    }
    
    private fun reprogramarReinicio(context: Context, horaReinicio: String) {
        try {
            val partes = horaReinicio.split(":")
            if (partes.size != 2) return
            
            val hora = partes[0].toInt()
            val minuto = partes[1].toInt()
            
            val calendar = java.util.Calendar.getInstance()
            calendar.add(java.util.Calendar.DAY_OF_YEAR, 1)
            calendar.set(java.util.Calendar.HOUR_OF_DAY, hora)
            calendar.set(java.util.Calendar.MINUTE, minuto)
            calendar.set(java.util.Calendar.SECOND, 0)
            calendar.set(java.util.Calendar.MILLISECOND, 0)
            
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, ReinicioReceiver::class.java)
            val pendingIntent = PendingIntent.getBroadcast(
                context,
                1001,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            
            try {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
                Log.i("ReinicioReceiver", "Alarm reprogramado para mañana a las $horaReinicio")
            } catch (e: SecurityException) {
                alarmManager.set(
                    AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
            }
        } catch (e: Exception) {
            Log.e("ReinicioReceiver", "Error al reprogramar: ${e.message}")
        }
    }
}