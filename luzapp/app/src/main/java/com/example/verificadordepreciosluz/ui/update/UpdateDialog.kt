package com.example.verificadordepreciosluz.ui.update

import android.app.Dialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.WindowManager
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.core.content.FileProvider
import com.example.verificadordepreciosluz.R
import com.example.verificadordepreciosluz.data.model.UpdateInfo
import com.example.verificadordepreciosluz.data.network.UpdateService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest

class UpdateDialog(
    context: Context,
    private val updateInfo: UpdateInfo,
    private val onDismiss: () -> Unit
) : Dialog(context, R.style.Theme_VerificadorDePreciosLuz_Dialog) {

    private var progressBar: ProgressBar? = null
    private var tvStatus: TextView? = null
    private var tvProgress: TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.dialog_update)
        setCancelable(false)
        window?.setLayout(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT
        )

        progressBar = findViewById(R.id.progressUpdate)
        tvStatus = findViewById(R.id.tvUpdateStatus)
        tvProgress = findViewById(R.id.tvUpdateProgress)

        findViewById<TextView>(R.id.tvUpdateVersion).text = "Versión: ${updateInfo.version}"
        findViewById<TextView>(R.id.tvUpdateChangelog).text = updateInfo.changelog ?: "Sin cambios"

        findViewById<TextView>(R.id.btnUpdateNow).setOnClickListener { downloadUpdate() }
        findViewById<TextView>(R.id.btnUpdateLater).setOnClickListener { dismiss() }
    }

    private fun downloadUpdate() {
        tvStatus?.text = "Descargando..."
        findViewById<TextView>(R.id.btnUpdateNow).isEnabled = false

        val downloadUrl = UpdateService.getUpdateUrl(updateInfo)
        val targetFile = File(context.cacheDir, "update_${updateInfo.version}.apk")

        CoroutineScope(Dispatchers.IO).launch {
            try {
                downloadFile(downloadUrl, targetFile)
                
                withContext(Dispatchers.Main) {
                    if (verifyChecksum(targetFile)) {
                        installApk(targetFile)
                    } else {
                        showError("Error de verificación")
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    showError("Error: ${e.message}")
                }
            }
        }
    }

    private suspend fun downloadFile(url: String, target: File) {
        val client = OkHttpClient()
        val request = Request.Builder().url(url).build()
        val response = client.newCall(request).execute()

        if (!response.isSuccessful) throw Exception("Descarga fallida: ${response.code}")

        val body = response.body ?: throw Exception("Respuesta vacía")
        val totalBytes = body.contentLength()
        var downloadedBytes = 0L

        FileOutputStream(target).use { fos ->
            body.byteStream().use { input ->
                val buffer = ByteArray(8192)
                var bytesRead: Int
                while (input.read(buffer).also { bytesRead = it } != -1) {
                    fos.write(buffer, 0, bytesRead)
                    downloadedBytes += bytesRead

                    if (totalBytes > 0) {
                        val progress = ((downloadedBytes * 100) / totalBytes).toInt()
                        withContext(Dispatchers.Main) {
                            updateProgress(progress)
                        }
                    }
                }
            }
        }
    }

    private fun updateProgress(progress: Int) {
        Handler(Looper.getMainLooper()).post {
            progressBar?.progress = progress
            tvProgress?.text = "$progress%"
        }
    }

    private fun verifyChecksum(file: File): Boolean {
        val expectedChecksum = UpdateService.getChecksum(updateInfo)
        if (expectedChecksum.isEmpty()) return true

        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(file.readBytes())
        val actualChecksum = digest.joinToString("") { "%02x".format(it) }

        return actualChecksum == expectedChecksum
    }

    private fun installApk(file: File) {
        try {
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                file
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            context.startActivity(intent)
            dismiss()
        } catch (e: Exception) {
            showError("No se pudo iniciar la instalación")
        }
    }

    private fun showError(message: String) {
        tvStatus?.text = message
        findViewById<TextView>(R.id.btnUpdateNow).apply {
            isEnabled = true
            text = "Reintentar"
        }
    }
}
