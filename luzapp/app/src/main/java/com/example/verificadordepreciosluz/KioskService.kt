package com.example.verificadordepreciosluz

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import android.util.Log
import com.example.verificadordepreciosluz.util.DeviceTypeHelper

class KioskService : Service() {
    companion object {
        private const val TAG = "KioskService"
        private const val CHANNEL_ID = "kiosk_service_channel"
        private const val NOTIFICATION_ID = 1
    }

    private var hdmiReceiver: HdmiScreenReceiver? = null

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "KioskService onCreate")

        if (DeviceTypeHelper.detectDeviceType(this) != DeviceTypeHelper.DeviceType.TELEVISOR) {
            Log.d(TAG, "No es TV, deteniendo servicio")
            stopSelf()
            return
        }

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        registerHdmiReceiver()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "KioskService onStartCommand")
        return START_STICKY
    }

    override fun onDestroy() {
        Log.i(TAG, "KioskService onDestroy")
        unregisterHdmiReceiver()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun registerHdmiReceiver() {
        hdmiReceiver = HdmiScreenReceiver()
        val filter = HdmiScreenReceiver.createIntentFilter()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            registerReceiver(hdmiReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            registerReceiver(hdmiReceiver, filter)
        }
        Log.i(TAG, "HdmiScreenReceiver registrado")
    }

    private fun unregisterHdmiReceiver() {
        hdmiReceiver?.let {
            try {
                unregisterReceiver(it)
                Log.i(TAG, "HdmiScreenReceiver desregistrado")
            } catch (e: Exception) {
                Log.e(TAG, "Error al desregistrar receptor: ${e.message}")
            }
        }
        hdmiReceiver = null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Servicio Kiosco",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Mantiene el servicio de kiosco activo"
                setShowBadge(false)
            }
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("LuzApp")
                .setContentText("Servicio activo")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setFlag(Notification.FLAG_ONGOING_EVENT, true)
                .build()
        } else {
            Notification.Builder(this)
                .setContentTitle("LuzApp")
                .setContentText("Servicio activo")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setFlag(Notification.FLAG_ONGOING_EVENT, true)
                .build()
        }
    }
}
