package com.example.verificadordepreciosluz.util

import android.Manifest
import android.app.Activity
import android.app.ActivityManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import android.widget.Toast
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.content.FileProvider
import com.example.verificadordepreciosluz.data.model.UpdateInfo
import com.example.verificadordepreciosluz.data.network.UpdateService
import com.example.verificadordepreciosluz.ui.scanner.MyDeviceAdminReceiver
import com.example.verificadordepreciosluz.ui.scanner.ScanActivity
import com.example.verificadordepreciosluz.ui.update.UpdateDialog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

private const val TAG = "UpdateChecker"
private const val CHANNEL_ID = "update_channel"
private const val NOTIFICATION_ID = 1001
private const val PREFS_NAME = "update_prefs"
private const val KEY_LAST_CHECK = "last_check_time"
private const val KEY_VERSION_CHECKED = "version_checked"
private const val DEBOUNCE_MS = 3600000 // 1 hora

object UpdateChecker {

    enum class UpdateMode {
        DIALOG,        // Opción 1: Muestra diálogo (por defecto)
        SILENT,        // Opción 2: Descarga automáticamente, notifica al final
        AUTO          // Opción 3: Descarga e instala sin interacción (Device Owner)
    }

    private var currentMode = UpdateMode.DIALOG

    fun setUpdateMode(mode: UpdateMode) {
        currentMode = mode
    }

    // Para WorkManager - ignora debounce
    fun forceCheck(context: Context) {
        Log.d(TAG, "forceCheck() called - ignoring debounce")
        currentMode = UpdateMode.AUTO
        
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putLong(KEY_LAST_CHECK, 0).apply()
        
        check(context)
    }

    fun check(context: Context, onUpdateAvailable: ((UpdateInfo) -> Unit)? = null) {
        Log.d(TAG, "check() called, mode: $currentMode")
        
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val lastCheck = prefs.getLong(KEY_LAST_CHECK, 0)
        val currentTime = System.currentTimeMillis()
        val lastVersionChecked = prefs.getString(KEY_VERSION_CHECKED, "")
        
        // Debounce: solo verificar cada 1 hora SI ya se verificó antes
        if (lastCheck > 0 && (currentTime - lastCheck) < DEBOUNCE_MS) {
            Log.d(TAG, "Skipping check, debounce active. Last check: ${currentTime - lastCheck}ms ago")
            return
        }
        
        // Guardar tiempo SIEMPRE al verificar
        prefs.edit().putLong(KEY_LAST_CHECK, currentTime).apply()
        
        CoroutineScope(Dispatchers.IO).launch {
            val result = UpdateService.checkForUpdate()

            result.onSuccess { updateInfo ->
                Log.d(TAG, "checkForUpdate success, version: ${updateInfo.version}")
                if (UpdateService.shouldUpdate(updateInfo.version)) {
                    // Marcar como verificada para evitar descarga repetida
                    prefs.edit().putString(KEY_VERSION_CHECKED, updateInfo.version).apply()
                    
                    Log.d(TAG, "shouldUpdate true, mode: $currentMode")
                    CoroutineScope(Dispatchers.Main).launch {
                        when (currentMode) {
                            UpdateMode.DIALOG -> {
                                if (UpdateService.requiresForcedUpdate(updateInfo.minVersion)) {
                                    showForcedUpdateDialog(context, updateInfo)
                                } else {
                                    onUpdateAvailable?.invoke(updateInfo)
                                        ?: showUpdateDialog(context, updateInfo)
                                }
                            }
                            UpdateMode.SILENT -> {
                                downloadSilently(context, updateInfo)
                            }
                            UpdateMode.AUTO -> {
                                downloadAndInstallAuto(context, updateInfo)
                            }
                        }
                    }
                }
            }

            result.onFailure {
                // Silencioso - no molestar al usuario si no hay conexión
            }
        }
    }

    private fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Actualización",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notificación de actualización de la app"
                setShowBadge(false)
            }
            val notificationManager = context.getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun showNotification(context: Context, title: String, message: String, progress: Int = -1) {
        createNotificationChannel(context)
        
        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(title)
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
        
        if (progress >= 0) {
            builder.setProgress(100, progress, progress == 0)
        }
        
        val notificationManager = context.getSystemService(NotificationManager::class.java)
        try {
            notificationManager.notify(NOTIFICATION_ID, builder.build())
        } catch (e: SecurityException) {
            Log.w(TAG, "Permission denied for notification")
        }
    }

    private fun hideNotification(context: Context) {
        val notificationManager = context.getSystemService(NotificationManager::class.java)
        notificationManager.cancel(NOTIFICATION_ID)
    }

    private fun updateProgressToast(context: Context, message: String) {
        Handler(Looper.getMainLooper()).post {
            Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
        }
    }

    private fun downloadSilently(context: Context, updateInfo: UpdateInfo) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                withContext(Dispatchers.Main) {
                    showNotification(context, "Descargando actualización", "Iniciando...", 0)
                    updateProgressToast(context, "Descargando actualización...")
                }
                
                val downloadUrl = UpdateService.getUpdateUrl(updateInfo)
                val targetFile = File(context.cacheDir, "update_${updateInfo.version}.apk")

                downloadFile(context, downloadUrl, targetFile)

                withContext(Dispatchers.Main) {
                    showNotification(context, "Actualización lista", "Instalando...", 100)
                    Toast.makeText(context, "Actualización descargada. Instalando...", Toast.LENGTH_SHORT).show()
                    installSilentlyMethod(context, targetFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    hideNotification(context)
                    Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun downloadAndInstallAuto(context: Context, updateInfo: UpdateInfo) {
        Log.d(TAG, "downloadAndInstallAuto() called, url: ${UpdateService.getUpdateUrl(updateInfo)}")
        CoroutineScope(Dispatchers.IO).launch {
            try {
                withContext(Dispatchers.Main) {
                    showNotification(context, "Descargando actualización", "Descargando... 0%", 0)
                    updateProgressToast(context, "Descargando actualización v${updateInfo.version}...")
                }
                
                val downloadUrl = UpdateService.getUpdateUrl(updateInfo)
                val targetFile = File(context.cacheDir, "update_${updateInfo.version}.apk")
                Log.d(TAG, "Downloading APK...")

                downloadFile(context, downloadUrl, targetFile)
                Log.d(TAG, "APK downloaded, size: ${targetFile.length()} bytes")

                withContext(Dispatchers.Main) {
                    showNotification(context, "Actualizando app", "Instalando... 0%", 0)
                    updateProgressToast(context, "Instalando actualización...")
                    installSilentlyMethod(context, targetFile)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error: ${e.message}")
                withContext(Dispatchers.Main) {
                    hideNotification(context)
                    updateProgressToast(context, "Error: ${e.message}")
                    installFallbackWithNormal(context, e.message)
                }
            }
        }
    }

    private fun installFallbackWithNormal(context: Context, errorMessage: String? = null) {
        updateProgressToast(context, "Abriendo instalador...")
        Toast.makeText(context, "Error: $errorMessage. Instale manualmente.", Toast.LENGTH_LONG).show()
    }

    private suspend fun downloadFile(context: Context, url: String, target: File) {
        Log.d(TAG, "downloadFile() from: $url")
        
        val notificationManager = context.getSystemService(NotificationManager::class.java)
        
        val client = okhttp3.OkHttpClient().newBuilder()
            .connectTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            .build()
        val request = okhttp3.Request.Builder().url(url).build()
        val response = client.newCall(request).execute()
        
        Log.d(TAG, "Response code: ${response.code}")

        if (!response.isSuccessful) throw Exception("Descarga fallida: ${response.code}")

        val body = response.body ?: throw Exception("Respuesta vacía")
        val totalBytes = body.contentLength()
        Log.d(TAG, "Total bytes to download: $totalBytes")
        
        var downloadedBytes = 0L
        body.byteStream().use { input ->
            target.outputStream().use { output ->
                val buffer = ByteArray(8192)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    output.write(buffer, 0, bytesRead)
                    downloadedBytes += bytesRead
                    if (totalBytes > 0) {
                        val progress = ((downloadedBytes * 100) / totalBytes).toInt()
                        if (progress % 25 == 0) {
                            Log.d(TAG, "Download progress: $progress%")
                            withContext(Dispatchers.Main) {
                                showNotification(context, "Descargando actualización", "Descargando... $progress%", progress)
                            }
                        }
                    }
                }
            }
        }
        Log.d(TAG, "downloadFile() complete, saved: ${target.length()} bytes")
    }

    private fun installSilentlyMethod(context: Context, apkFile: File) {
        Log.d(TAG, "installSilently() called")
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            val adminComponent = ComponentName(context, MyDeviceAdminReceiver::class.java)
            Log.d(TAG, "isAdminActive: ${dpm.isAdminActive(adminComponent)}")

            if (dpm.isAdminActive(adminComponent)) {
                Log.d(TAG, "Device Owner active, starting silent install")
                val packageInstaller = context.packageManager.packageInstaller
                val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
                
                val sessionId = packageInstaller.createSession(params)
                val session = packageInstaller.openSession(sessionId)
                
                apkFile.inputStream().use { input ->
                    session.openWrite("base.apk", 0, apkFile.length()).use { output ->
                        input.copyTo(output)
                    }
                }
                
                val pendingIntent = PendingIntent.getBroadcast(
                    context, 0, Intent(context, MyDeviceAdminReceiver::class.java), PendingIntent.FLAG_IMMUTABLE
                )
                session.commit(pendingIntent.intentSender)

                Handler(Looper.getMainLooper()).post {
                    showNotification(context, "Actualización", "Instalación programada", 100)
                    Toast.makeText(context, "Actualización programada", Toast.LENGTH_SHORT).show()
                    scheduleRestart(context)
                }
            } else {
                Log.d(TAG, "Device Owner NOT active, using fallback")
                installWithNormal(context, apkFile)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error installing: ${e.message}")
            installWithNormal(context, apkFile)
        }
    }

    private fun installWithNormal(context: Context, apkFile: File) {
        try {
            showNotification(context, "Instalando app", "Abriendo instalador...", 0)
            updateProgressToast(context, "Abriendo instalador...")
            
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                apkFile
            )
            
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TASK)
                addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP)
            }
            
            hideNotification(context)
            context.startActivity(Intent.createChooser(intent, "Instalar actualización"))
            
            scheduleRestart(context)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error: ${e.message}")
            hideNotification(context)
            Toast.makeText(context, "Error al instalar. Instale manualmente.", Toast.LENGTH_LONG).show()
        }
    }

    private fun scheduleRestart(context: Context) {
        Handler(Looper.getMainLooper()).postDelayed({
            try {
                showNotification(context, "Actualización", "Reiniciando app...", 0)
                Toast.makeText(context, "Reiniciando app...", Toast.LENGTH_SHORT).show()

                val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)
                intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)

                hideNotification(context)
            } catch (e: Exception) {
                Log.e(TAG, "Error restarting: ${e.message}")
                hideNotification(context)
            }
        }, 3000)
    }

    private fun showUpdateDialog(context: Context, updateInfo: UpdateInfo) {
        UpdateDialog(context, updateInfo) {}.show()
    }

    private fun showForcedUpdateDialog(context: Context, updateInfo: UpdateInfo) {
        android.app.AlertDialog.Builder(context)
            .setTitle("Actualización obligatoria")
            .setMessage("Debes actualizar a la versión ${updateInfo.version} para continuar usando la app.\n\n${updateInfo.changelog ?: ""}")
            .setCancelable(false)
            .setPositiveButton("Actualizar") { _, _ ->
                UpdateDialog(context, updateInfo) {}.show()
            }
            .show()
    }
}
