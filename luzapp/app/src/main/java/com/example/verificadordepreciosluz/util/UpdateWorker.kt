package com.example.verificadordepreciosluz.util

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.Constraints
import androidx.work.NetworkType
import java.util.Calendar
import java.util.concurrent.TimeUnit

class UpdateWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {
    
    override suspend fun doWork(): Result {
        return try {
            val context = applicationContext
            // Ignora debounce - siempre verifica
            UpdateChecker.forceCheck(context)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
    
    companion object {
        private const val WORK_NAME = "daily_update_check"
        
        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()
            
            // Calcular tiempo hasta las 7:00 AM (hora Caracas = UTC-4)
            val currentTime = Calendar.getInstance()
            val scheduledTime = Calendar.getInstance().apply {
                set(Calendar.HOUR_OF_DAY, 7)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
                
                // Si ya pasaron las 7 AM, programar para el siguiente día
                if (before(currentTime)) {
                    add(Calendar.DAY_OF_MONTH, 1)
                }
            }
            
            val initialDelay = scheduledTime.timeInMillis - currentTime.timeInMillis
            
            val workRequest = PeriodicWorkRequestBuilder<UpdateWorker>(
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