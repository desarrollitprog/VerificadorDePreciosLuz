package com.example.verificadordepreciosluz.ui.scanner

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.WindowManager
import android.graphics.Paint
import android.media.ToneGenerator
import android.media.AudioManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.HapticFeedbackConstants
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.example.verificadordepreciosluz.MainActivity
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.example.verificadordepreciosluz.databinding.ActivityScanBinding
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
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlin.math.roundToInt

@OptIn(androidx.camera.core.ExperimentalGetImage::class)
class ScanActivity : AppCompatActivity() {
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

        // Toggle del panel de prueba tocando el título (para emulador)
        binding.tvTituloScanner.setOnClickListener {
            binding.mockPanel.visibility = if (binding.mockPanel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }

        binding.btnMockScan.setOnClickListener {
            val code = binding.etMockCode.text?.toString()?.trim().orEmpty()
            if (code.isNotEmpty()) {
                maybeProcessCode(code)
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

            val analyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(cameraExecutor, ::analyzeImage) }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, analyzer)
            } catch (e: Exception) {
                finishWithMessage("Error iniciando cámara: ${e.localizedMessage}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

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

    private fun sanitizeCode(raw: String): String? {
        // Limpia espacios y filtra códigos demasiado cortos o con ruido.
        val trimmed = raw.trim()
        val digitsOnly = trimmed.filter { it.isDigit() }
        val candidate = when {
            digitsOnly.length >= 8 -> digitsOnly
            trimmed.length >= 8 && trimmed.all { it.isLetterOrDigit() } -> trimmed
            else -> null
        }
        return candidate
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
                    pauseUntil = android.os.SystemClock.elapsedRealtime() + 3000
                }
            } catch (e: Exception) {
                uiHandler.post {
                    val msg = when (e) {
                        is HttpException -> when (e.code()) {
                            404 -> "Producto no encontrado"
                            in 500..599 -> "Error del servidor (${e.code()})"
                            else -> "Error HTTP (${e.code()})"
                        }
                        else -> "Fallo de red o conexión"
                    }
                    Toast.makeText(this@ScanActivity, msg, Toast.LENGTH_SHORT).show()
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

        if (host.isNullOrBlank()) {
            goToConfig("Configura IP/puerto primero")
            return false
        }

        val normalized = ensurePort(sanitizeHost(host), port ?: getString(com.example.verificadordepreciosluz.R.string.default_port))
        api = ApiClient.create(normalized)
        return true
    }

    private fun startPingMonitor() {
        val service = api ?: return
        pingJob?.cancel()
        pingJob = scope.launch {
            while (isActive) {
                try {
                    service.ping()
                } catch (_: Exception) {
                    goToConfig("Conexión perdida. Regresando a configuración")
                    break
                }
                delay(5000)
            }
        }
    }

    private fun goToConfig(reason: String? = null) {
        runOnUiThread {
            reason?.let {
                Toast.makeText(this@ScanActivity, it, Toast.LENGTH_LONG).show()
            }
            startActivity(Intent(this@ScanActivity, MainActivity::class.java))
            finish()
        }
    }

    private fun showResult(producto: ProductoResponse) {
        val regularPrice = producto.precio
        val offerPrice = producto.precioOferta
        val currentPrice = offerPrice ?: regularPrice

        binding.tvPrecioActual.text = getString(com.example.verificadordepreciosluz.R.string.currency_format, currentPrice)

        if (offerPrice != null) {
            binding.tvPrecioAnterior.visibility = View.VISIBLE
            binding.tvPrecioAnterior.text = getString(com.example.verificadordepreciosluz.R.string.currency_format, regularPrice)
            binding.tvPrecioAnterior.paintFlags = binding.tvPrecioAnterior.paintFlags or Paint.STRIKE_THRU_TEXT_FLAG

            val descuento = if (regularPrice > 0) ((regularPrice - offerPrice) / regularPrice * 100).roundToInt() else null
            binding.tvDescuentoBadge.visibility = View.VISIBLE
            binding.tvDescuentoBadge.text = descuento?.let {
                getString(com.example.verificadordepreciosluz.R.string.discount_percent, it)
            } ?: getString(com.example.verificadordepreciosluz.R.string.label_oferta)
        } else {
            binding.tvPrecioAnterior.visibility = View.GONE
            binding.tvDescuentoBadge.visibility = View.GONE
        }

        binding.tvNombre.text = producto.nombre
        binding.tvUbicacion.text = getString(com.example.verificadordepreciosluz.R.string.label_location_placeholder)
        binding.resultOverlay.visibility = View.VISIBLE

        // Ocultar automáticamente tras 10 segundos, limpiando anteriores
        uiHandler.removeCallbacksAndMessages(null)
        uiHandler.postDelayed({ binding.resultOverlay.visibility = View.GONE }, 10_000)
    }

    private fun finishWithMessage(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
        finish()
    }

    private fun ensurePort(ip: String, port: String): String = if (ip.contains(":")) ip else "$ip:$port"
    private fun sanitizeHost(raw: String): String = raw.removePrefix("http://").removePrefix("https://").trimEnd('/')

    private fun feedbackSuccess() {
        // Beep corto
        tone?.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
        // Haptic breve
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vm = getSystemService(VibratorManager::class.java)
                vm.defaultVibrator.vibrate(VibrationEffect.createOneShot(30, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                val vib = getSystemService(VIBRATOR_SERVICE) as Vibrator
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vib.vibrate(VibrationEffect.createOneShot(30, VibrationEffect.DEFAULT_AMPLITUDE))
                } else {
                    @Suppress("DEPRECATION")
                    vib.vibrate(30)
                }
            }
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
}
