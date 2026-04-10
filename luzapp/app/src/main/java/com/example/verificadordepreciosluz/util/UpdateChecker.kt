package com.example.verificadordepreciosluz.util

import android.app.PendingIntent
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.widget.Toast
import android.os.Handler
import android.os.Looper
import com.example.verificadordepreciosluz.data.model.UpdateInfo
import com.example.verificadordepreciosluz.data.network.UpdateService
import com.example.verificadordepreciosluz.ui.scanner.MyDeviceAdminReceiver
import com.example.verificadordepreciosluz.ui.update.UpdateDialog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

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

    fun check(context: Context, onUpdateAvailable: ((UpdateInfo) -> Unit)? = null) {
        CoroutineScope(Dispatchers.IO).launch {
            val result = UpdateService.checkForUpdate()

            result.onSuccess { updateInfo ->
                if (UpdateService.shouldUpdate(updateInfo.version)) {
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

    private fun downloadSilently(context: Context, updateInfo: UpdateInfo) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val downloadUrl = UpdateService.getUpdateUrl(updateInfo)
                val targetFile = File(context.cacheDir, "update_${updateInfo.version}.apk")

                downloadFile(downloadUrl, targetFile)

                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Actualización descargada. Se instalará al reiniciar.", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Error descargando: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun downloadAndInstallAuto(context: Context, updateInfo: UpdateInfo) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val downloadUrl = UpdateService.getUpdateUrl(updateInfo)
                val targetFile = File(context.cacheDir, "update_${updateInfo.version}.apk")

                downloadFile(downloadUrl, targetFile)

                withContext(Dispatchers.Main) {
                    installSilently(context, targetFile)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private suspend fun downloadFile(url: String, target: File) {
        val client = okhttp3.OkHttpClient()
        val request = okhttp3.Request.Builder().url(url).build()
        val response = client.newCall(request).execute()

        if (!response.isSuccessful) throw Exception("Descarga fallida: ${response.code}")

        response.body?.byteStream()?.use { input ->
            target.outputStream().use { output ->
                input.copyTo(output)
            }
        }
    }

    private fun installSilently(context: Context, apkFile: File) {
        try {
            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
            val adminComponent = ComponentName(context, MyDeviceAdminReceiver::class.java)

            if (dpm.isAdminActive(adminComponent)) {
                // Device Owner: instalación silenciosa con PackageInstaller
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
                    Toast.makeText(context, "Actualización programada", Toast.LENGTH_SHORT).show()
                }
            } else {
                installNormal(context, apkFile)
            }
        } catch (e: Exception) {
            // Fallback: instalación normal
            installNormal(context, apkFile)
        }
    }

    private fun installNormal(context: Context, apkFile: File) {
        val intent = android.content.Intent(android.content.Intent.ACTION_VIEW).apply {
            setDataAndType(android.net.Uri.fromFile(apkFile), "application/vnd.android.package-archive")
            addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(intent)
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
