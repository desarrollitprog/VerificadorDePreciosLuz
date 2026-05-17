package com.example.verificadordepreciosluz.util

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.Constraints
import androidx.work.NetworkType
import com.example.verificadordepreciosluz.data.local.BackupIndexRepository
import com.example.verificadordepreciosluz.data.local.BackupRepository
import com.example.verificadordepreciosluz.data.local.BackupUtils
import com.example.verificadordepreciosluz.data.network.ApiClient
import java.util.Calendar
import java.util.TimeZone
import java.util.concurrent.TimeUnit

class BackupWorker(context: Context, workerParams: WorkerParameters) :
    CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            val ctx = applicationContext
            val prefs = ctx.getSharedPreferences("ConfigLuz", Context.MODE_PRIVATE)
            val host = prefs.getString("ip_servidor", null) ?: return Result.failure()
            val port = prefs.getString("puerto_servidor", "8000")
            val baseUrl = NetworkUtils.buildBaseUrl(host, port, "8000")
            val api = ApiClient.create(baseUrl)

            val existing = BackupRepository(ctx).getUpdatedAt()
            if (existing != null) {
                val millis = BackupUtils.parseIsoToMillis(existing)
                if (millis != null && (System.currentTimeMillis() - millis) < 12 * 60 * 60 * 1000L) {
                    Log.i(TAG, "Backup vigente (<12h), saltando descarga programada")
                    return Result.success()
                }
            }

            val repo = BackupRepository(ctx, api)
            val result = repo.downloadAndSaveBackup()

            if (result.isSuccess) {
                BackupIndexRepository(ctx).ensureIndex(repo.getUpdatedAt())
            }

            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Error en backup programado: ${e.message}")
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "BackupWorker"
        private const val WORK_NAME = "daily_backup_sync"

        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()

            val caracasTz = TimeZone.getTimeZone("America/Caracas")
            val now = Calendar.getInstance(caracasTz)
            val target = Calendar.getInstance(caracasTz).apply {
                set(Calendar.HOUR_OF_DAY, 8)
                set(Calendar.MINUTE, 30)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
                if (before(now)) {
                    add(Calendar.DAY_OF_MONTH, 1)
                }
            }

            val initialDelay = target.timeInMillis - now.timeInMillis

            val workRequest = PeriodicWorkRequestBuilder<BackupWorker>(
                24, TimeUnit.HOURS
            )
                .setConstraints(constraints)
                .setInitialDelay(initialDelay, TimeUnit.MILLISECONDS)
                .build()

            androidx.work.WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    workRequest
                )
        }
    }
}
