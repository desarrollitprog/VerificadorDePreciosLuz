@file:Suppress("OPT_IN_ARGUMENT_IS_NOT_MARKER")

package com.example.verificadordepreciosluz.ui.scanner

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import android.media.ToneGenerator
import android.media.AudioManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.HapticFeedbackConstants
import android.view.View
import android.widget.Toast
import android.util.Log
import android.view.inputmethod.EditorInfo
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.core.widget.addTextChangedListener
import com.example.verificadordepreciosluz.MainActivity
import com.example.verificadordepreciosluz.BuildConfig
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.example.verificadordepreciosluz.databinding.ActivityScanBinding
import com.example.verificadordepreciosluz.R
import com.example.verificadordepreciosluz.util.NetworkUtils
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import retrofit2.HttpException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.IOException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.net.SocketTimeoutException

@OptIn(ExperimentalGetImage::class)
class ScanActivity : AppCompatActivity() {
    companion object { private const val TAG = "ScanActivity" }

    private lateinit var binding: ActivityScanBinding
    private lateinit var cameraExecutor: ExecutorService
    private var requestInFlight = false
    private var lastCode: String? = null
    private var lastScanAt: Long = 0L
    private var pauseUntil: Long = 0L
    private var tone: ToneGenerator? = null
    private val uiHandler = Handler(Looper.getMainLooper())
    private val job = Job()
    private val scope = CoroutineScope(Dispatchers.IO + job)
    private var api: ApiService? = null
    private var pingJob: Job? = null
    private var imageAnalysis: ImageAnalysis? = null
    private var analyzerPaused = false
    private var lastErrorKey: String? = null
    private var lastErrorAt = 0L
    private var lastMockSubmitAt = 0L
    private var pendingMockText: String? = null
    private var mockIdleRunnable: Runnable? = null

    private val requestPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) startCamera() else finishWithMessage("Permiso de cámara denegado")
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        cameraExecutor = Executors.newSingleThreadExecutor()
        tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)

        if (!configureBackend()) return

        startPingMonitor()

        ensurePermissionAndStart()

        // Toggle del panel de prueba tocando el título (para emulador/técnico)
        binding.tvTituloScanner.setOnClickListener {
            toggleMockPanel()
        }

        setupMockInput()
    }

    private fun setupMockInput() {
        binding.btnMockScan.setOnClickListener {
            val code = binding.etMockCode.text?.toString()?.trim().orEmpty()
            submitMockIfValid(code)
        }

        binding.etMockCode.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                val code = binding.etMockCode.text?.toString()?.trim().orEmpty()
                submitMockIfValid(code)
                true
            } else {
                false
            }
        }

        binding.etMockCode.addTextChangedListener { editable ->
            val text = editable?.toString()?.trim().orEmpty()
            mockIdleRunnable?.let { uiHandler.removeCallbacks(it) }

            // Solo programa disparo si tiene longitud válida
            pendingMockText = if (text.length == 8 || text.length == 12 || text.length == 13) text else null

            pendingMockText?.let { candidate ->
                mockIdleRunnable = Runnable {
                    submitMockIfValid(candidate)
                }
                uiHandler.postDelayed(mockIdleRunnable!!, 120)
            }
        }
    }

    private fun ensurePermissionAndStart() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            requestPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(cameraExecutor, ::analyzeImage) }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis)
            } catch (e: Exception) {
                finishWithMessage("Error iniciando cámara: ${e.localizedMessage}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun analyzeImage(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image
        if (mediaImage == null) {
            imageProxy.close()
            return
        }

        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        val scanner = BarcodeScanning.getClient()

        scanner.process(image)
            .addOnSuccessListener { barcodes ->
                val raw = barcodes.firstOrNull()?.rawValue
                if (!raw.isNullOrBlank()) {
                    maybeProcessCode(raw)
                }
            }
            .addOnFailureListener { /* ignore: keep scanning */ }
            .addOnCompleteListener { imageProxy.close() }
    }

    private fun maybeProcessCode(code: String) {
        val clean = sanitizeCode(code) ?: return
        // Debounce: evita spam si el mismo código se mantiene en cámara.
        val now = android.os.SystemClock.elapsedRealtime()
        if (now < pauseUntil) return
        val cooldown = 1500L // 1.5s permite re-escaneos razonables
        if (requestInFlight) return
        if (clean == lastCode && (now - lastScanAt) < cooldown) return
        lastCode = clean
        lastScanAt = now
        onBarcodeDetected(clean)
    }

    private fun submitMockIfValid(raw: String) {
        val code = raw.trim()
        if (code.isEmpty()) return
        val now = android.os.SystemClock.elapsedRealtime()
        // Evita disparos duplicados en milisegundos
        if (now - lastMockSubmitAt < 250) return
        lastMockSubmitAt = now
        mockIdleRunnable?.let { uiHandler.removeCallbacks(it) }
        pendingMockText = null
        maybeProcessCode(code)
        binding.etMockCode.text?.clear()
    }

    private fun sanitizeCode(raw: String): String? {
        // Acepta solo dígitos para EAN-13, EAN-8 o UPC-E/UPC-A (12)
        val digits = raw.filter { it.isDigit() }
        return when (digits.length) {
            8, 12, 13 -> digits
            else -> null
        }
    }

    private fun onBarcodeDetected(code: String) {
        val api = api ?: run {
            goToConfig("Configura IP/puerto primero")
            return
        }

        scope.launch {
            requestInFlight = true
            try {
                val producto = api.consultar(code)
                uiHandler.post {
                    feedbackSuccess()
                    showResult(producto)
                    // Pausa el escáner 3s tras un éxito para evitar lecturas inmediatas repetidas
                    pauseUntil = android.os.SystemClock.elapsedRealtime() + 4000
                }
            } catch (e: Exception) {
                uiHandler.post {
                    val (key, msg) = when (e) {
                        is HttpException -> when (e.code()) {
                            404 -> "404" to "Producto no encontrado"
                            in 500..599 -> "5xx" to "Error del servidor (${e.code()})"
                            else -> "4xx" to "Error HTTP (${e.code()})"
                        }
                        is SocketTimeoutException -> "timeout" to "Tiempo de Conexion agotado"
                        is IOException -> "network" to "Fallo de red o conexión"
                        else -> "unknown" to "Error inesperado"
                    }
                    showThrottledError(key, msg)
                }
            } finally {
                // Permitir reintentar incluso con el mismo código después de un error
                if (lastCode == code) {
                    lastCode = null
                }
                requestInFlight = false
            }
        }
    }

    private fun configureBackend(): Boolean {
        val prefs = getSharedPreferences("ConfigLuz", MODE_PRIVATE)
        val host = prefs.getString("ip_servidor", null)
        val port = prefs.getString("puerto_servidor", getString(com.example.verificadordepreciosluz.R.string.default_port))

        val sanitized = host?.let { NetworkUtils.sanitizeHost(it) }
        val defaultPort = getString (com.example.verificadordepreciosluz.R.string.default_port)

        if (sanitized.isNullOrBlank() || !NetworkUtils.validateHost(sanitized)) {
            goToConfig("Configura IP/puerto primero")
            return false
        }

        val portToUse = port ?: defaultPort
        if (!NetworkUtils.validatePort(portToUse)) {
            goToConfig("Puerto inválido. Regresando a configuración")
            return false
        }

        val normalized = NetworkUtils.buildBaseUrl(sanitized, portToUse, defaultPort)
        api = ApiClient.create(normalized, BuildConfig.DEBUG)
        return true
    }

    private fun startPingMonitor() {
        val service = api ?: return
        pingJob?.cancel()
        pingJob = scope.launch {
            while (isActive) {
                val (ok, reason) = pingWithRetries(service)
                if (!ok) {
                    goToConfig(reason ?: "Conexión perdida. Regresando a configuración")
                    return@launch
                }
                delay(5000)
            }
        }
    }

    private suspend fun pingWithRetries(service: ApiService): Pair<Boolean, String?> {
        val delays = listOf(0L, 1500L, 3000L)
        var lastReason: String? = null
        for (waitMs in delays) {
            if (waitMs > 0) delay(waitMs)
            try {
                service.ping()
                return true to null
            } catch (e: HttpException) {
                lastReason = if (e.code() in 400..499) {
                    "Ping falló (${e.code()}). Revisa la configuración"
                } else {
                    "Servidor responde con error (${e.code()})"
                }
                if (e.code() in 400..499) break
            } catch (_: SocketTimeoutException) {
                lastReason = "Tiempo de Conexion agotado"
            } catch (_: IOException) {
                lastReason = "Ping sin conexión"
            }
        }
        return false to lastReason
    }

    private fun goToConfig(reason: String? = null) {
        runOnUiThread {
            pingJob?.cancel()
            reason?.let {
                Toast.makeText(this@ScanActivity, it, Toast.LENGTH_LONG).show()
            }
            startActivity(Intent(this@ScanActivity, MainActivity::class.java))
            finish()
        }
    }

    private fun showResult(producto: ProductoResponse) {

        // Mostrar nombre
        binding.tvNombre.text = producto.nombre

        // Mostrar precio en Bs
        val precioBs = producto.pvpBaseOferta ?: producto.pvpBase ?: 0.0
        binding.tvPrecioActual.text = getString(R.string.currency_format, precioBs)

        // Mostrar mensaje informativo de IVA
        binding.tvIva.text = getString(R.string.price_with_iva_format)

        // Mostrar precio en $ en txtprecio
        val precioUsd = producto.pvpOferta ?: producto.pvpConversion ?: 0.0
        binding.tvPrecioDolar.text = getString(R.string.price_usd_format, precioUsd)

        // Cambiar color de fondo si está en oferta
        if (producto.pvpOferta != null) {
            binding.tvPrecioDolar.setBackgroundResource(R.color.vinotinto_oferta)
        } else {
            binding.tvPrecioDolar.setBackgroundResource(R.color.verde_luz)
        }


        // Ocultar ubicación
        binding.tvUbicacion.visibility = View.GONE

        binding.resultOverlay.visibility = View.VISIBLE
        pauseAnalyzer(true)

        // Ocultar automáticamente tras 3 segundos, limpiando anteriores
        uiHandler.removeCallbacksAndMessages(null)
        uiHandler.postDelayed({
            binding.resultOverlay.visibility = View.GONE
            pauseAnalyzer(false)
            binding.etMockCode.requestFocus()
        }, 4_000)
    }

    private fun finishWithMessage(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
        finish()
    }

    private fun pauseAnalyzer(paused: Boolean) {
        if (analyzerPaused == paused) return
        analyzerPaused = paused
        imageAnalysis?.let { analysis ->
            if (paused) {
                analysis.clearAnalyzer()
            } else {
                analysis.setAnalyzer(cameraExecutor, ::analyzeImage)
            }
        }
    }

    private fun showThrottledError(key: String, message: String, minIntervalMs: Long = 2000) {
        val now = android.os.SystemClock.elapsedRealtime()
        if (key == lastErrorKey && (now - lastErrorAt) < minIntervalMs) return
        lastErrorKey = key
        lastErrorAt = now

        val overlayVisible = binding.resultOverlay.visibility == View.VISIBLE
        Log.w(TAG, "scan_error key=$key overlay=$overlayVisible msg=$message")
        if (!overlayVisible) {
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }

    private fun feedbackSuccess() {
        // Beep corto
        tone?.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
        // Haptic breve
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager
                vibratorManager.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                getSystemService(VIBRATOR_SERVICE) as Vibrator
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(30, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(30)
            }
        } catch (_: Exception) {
            // fallback: haptic en la vista si vibración falla
        } catch (_: Exception) {
            // fallback: haptic en la vista si vibración falla
            binding.previewView.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        tone?.release()
        tone = null
        pingJob?.cancel()
        job.cancel()
        scope.cancel()
    }

    override fun onPause() {
        super.onPause()
        // Pausa el monitor de ping cuando la actividad no está en primer plano
        pingJob?.cancel()
    }

    override fun onResume() {
        super.onResume()
        // Reanuda el monitor de ping al volver al primer plano
        if (api == null) {
            // Si se perdió la instancia por cualquier motivo, intenta reconfigurar
            if (!configureBackend()) return
        }
        binding.etMockCode.requestFocus()
        startPingMonitor()
    }

    private fun toggleMockPanel() {
        val isHidden = binding.mockPanel.alpha == 0f
        if (isHidden) {
            binding.mockPanel.alpha = 1f
            binding.etMockCode.alpha = 1f
            binding.etMockCode.requestFocus()
        } else {
            binding.mockPanel.alpha = 0f
            binding.etMockCode.alpha = 0f
            // Mantener view visible para que siga existiendo; foco opcional si se usa lector
            binding.etMockCode.requestFocus()
        }
    }
}
