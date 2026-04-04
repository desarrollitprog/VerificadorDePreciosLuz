package com.example.verificadordepreciosluz.util

import android.content.Context
import android.widget.Toast
import com.example.verificadordepreciosluz.data.model.UpdateInfo
import com.example.verificadordepreciosluz.data.network.UpdateService
import com.example.verificadordepreciosluz.ui.update.UpdateDialog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object UpdateChecker {

    fun check(context: Context, onUpdateAvailable: ((UpdateInfo) -> Unit)? = null) {
        CoroutineScope(Dispatchers.IO).launch {
            val result = UpdateService.checkForUpdate()

            result.onSuccess { updateInfo ->
                if (UpdateService.shouldUpdate(updateInfo.version)) {
                    CoroutineScope(Dispatchers.Main).launch {
                        if (UpdateService.requiresForcedUpdate(updateInfo.minVersion)) {
                            showForcedUpdateDialog(context, updateInfo)
                        } else {
                            onUpdateAvailable?.invoke(updateInfo)
                                ?: showUpdateDialog(context, updateInfo)
                        }
                    }
                }
            }

            result.onFailure {
                // Silencioso - no molestar al usuario si no hay conexión
            }
        }
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
