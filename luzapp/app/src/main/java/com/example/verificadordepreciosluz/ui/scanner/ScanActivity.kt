@file:Suppress("OPT_IN_ARGUMENT_IS_NOT_MARKER")

package com.example.verificadordepreciosluz.ui.scanner

import android.Manifest
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
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
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.view.HapticFeedbackConstants
import android.view.View
import android.widget.Toast
import android.util.Log
import android.view.inputmethod.EditorInfo
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.inputmethod.InputMethodManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Rect
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import android.provider.Settings
import com.example.verificadordepreciosluz.MainActivity
import com.example.verificadordepreciosluz.BuildConfig
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.PlaybackStatusRequest
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.example.verificadordepreciosluz.data.local.BackupRepository
import com.example.verificadordepreciosluz.data.local.BackupResponse
import com.example.verificadordepreciosluz.data.local.BackupIndexRepository
import com.example.verificadordepreciosluz.data.local.BackupUtils
import com.example.verificadordepreciosluz.data.local.BannerRepository
import com.example.verificadordepreciosluz.data.local.BannerCacheItem
import com.example.verificadordepreciosluz.databinding.ActivityScanBinding
import com.example.verificadordepreciosluz.R
import com.example.verificadordepreciosluz.util.NetworkUtils
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
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
import androidx.core.view.WindowCompat
import androidx.core.view.isVisible
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import com.example.verificadordepreciosluz.data.local.ejecutarPurgaTotal
import com.example.verificadordepreciosluz.data.repository.DolarRepository
import java.io.File
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject

@OptIn(ExperimentalGetImage::class)
class ScanActivity : AppCompatActivity(), BackupRepository.BackupProgressListener {
    // Variables globales y binding
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
    private var lastPlaybackReportKey: String? = null
    private var lastPlaybackReportAt = 0L
    private val retryCountMap = mutableMapOf<String, Int>()
    private val MAX_RETRY_BEFORE_REPORT = 3
    private var lastMockSubmitAt = 0L
    private var pendingMockText: String? = null
    private var mockIdleRunnable: Runnable? = null
    private var offlineMode = false
    private var isNetworkAvailable = false
    private var networkCallbackRegistered = false
    private var connectivityManager: ConnectivityManager? = null
    private var offlineBackup: BackupResponse? = null
    private var backupReadyNotified = false
    private val backupMaxAgeMs = (12 * 60 * 60 * 1000L).toLong()
    private var cameraProvider: ProcessCameraProvider? = null
    private val bannerMaxAgeMs = (12 * 60 * 60 * 1000L).toLong()
    private val bannerPollIntervalMs = (25 * 60 * 1000L).toLong()
    private val bannerPollHandler = Handler(Looper.getMainLooper())
    private var bannerPollRunnable: Runnable? = null
    private var backendBaseUrl: String? = null
    private val standbyIdleMs = 20_000L
    private var standbyItems: MutableList<BannerCacheItem> = mutableListOf()
    private var standbyIndex = 0
    private var standbyActive = false
    private var standbyTimerRunnable: Runnable? = null
    private val KIOSK_EXIT_CODE = "ADMIN-CODE-125"
    private var isKioskMode = false
    private var isDownloading = false  // Para bloquear salida durante descarga
    private var dolarBcJob: Job? = null
    private val dolarRepository = DolarRepository()
    private val prefsDolar by lazy { getSharedPreferences("DolarBCV", MODE_PRIVATE) }
    private lateinit var dpm: DevicePolicyManager
    private lateinit var adminComponent: ComponentName
    private var standbySlideRunnable: Runnable? = null
    private var resultHideRunnable: Runnable? = null
    private var currentStandbyBitmap: Bitmap? = null
    private val deviceId: String by lazy {
        Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
    }
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            handleNetworkChange(true)
        }

        override fun onLost(network: Network) {
            handleNetworkChange(false)
        }

        override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
            val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            handleNetworkChange(hasInternet)
        }
    }

    // Cámara opcional: se inicia solo si el permiso ya está concedido
    // Si no hay permiso, se usa solo el escánero externo (USB HID)
    companion object { private const val TAG = "ScanActivity" }

    // Declarar backupReady como propiedad de la clase, antes de cualquier uso
    private var backupReady: Boolean = false

    private var tabletWebSocket: WebSocket? = null
    private var wsClient: OkHttpClient? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (isDownloading) {
                    Toast.makeText(this@ScanActivity, "Descarga en progreso, espera...", Toast.LENGTH_SHORT).show()
                    binding.etMockCode.requestFocus()
                    return
                }
                if (!backupReady) {
                    Toast.makeText(this@ScanActivity, "Respaldo no está listo. Espera la sincronización", Toast.LENGTH_SHORT).show()
                    binding.etMockCode.requestFocus()
                    return
                }
                isEnabled = false
                onBackPressedDispatcher.onBackPressed()
            }
        })

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        connectivityManager = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        cameraExecutor = Executors.newSingleThreadExecutor()
        tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)

        // Inicializar Device Policy Manager para modo kiosco
        dpm = getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        adminComponent = ComponentName(this, com.example.verificadordepreciosluz.ui.scanner.MyDeviceAdminReceiver::class.java)

        val forceOffline = intent.getBooleanExtra("force_offline_mode", false)
        val hasNetwork = NetworkUtils.isNetworkAvailable(this)
        isNetworkAvailable = hasNetwork
        setBackupReady(BackupRepository(this).getUpdatedAt() != null)

        if (forceOffline) {
            configureBackend()
            startOfflineModeOnLaunch()
        } else if (hasNetwork) {
            if (!configureBackend()) return
            startPingMonitor()
            syncBackupOnStart()
            syncBannersOnStart()
            startBannerPolling()
        } else {
            configureBackend()
            startOfflineModeOnLaunch()
        }

        ensurePermissionAndStart()

        // Toggle del panel de prueba tocando el título (para emulador/técnico)
        binding.tvTituloScanner.setOnClickListener {
            toggleMockPanel()
        }

        setupMockInput()
        resetStandbyTimer()
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN)
        applyImmersiveMode()
        hideKeyboard()
        excludeSystemGestures()

        if (hasNetwork && backendBaseUrl != null && api != null) {
            startTabletWebSocket()
        }

        // Obtener tasa BCV al inicio y programar actualizaciones
        if (hasNetwork) {
            Log.d(TAG, "BCV: onCreate - tiene red, invocando syncDolarBCV()")
            syncDolarBCV()
            scheduleDolarBCVRefresh()
        } else {
            Log.d(TAG, "BCV: onCreate - sin red, no se obtiene tasa BCV")
        }
    }

    // Implementación de métodos de la interfaz BackupProgressListener
    override fun onProgress(section: String, offset: Int, received: Int, total: Int) {
        runOnUiThread {
            val progressContainer = findViewById<android.widget.FrameLayout>(R.id.progressContainer)
            val progressBar = findViewById<android.widget.ProgressBar>(R.id.progressBar)
            val progressText = findViewById<android.widget.TextView>(R.id.progressText)
            val percent = if (total > 0) (received * 100 / total) else 0
            progressBar.max = total
            progressBar.progress = received
            progressText.text = getString(R.string.progress_section_percent, section, percent)
            progressContainer.visibility = View.VISIBLE
        }
    }
    override fun onError(section: String, error: Throwable) {
        runOnUiThread {
            findViewById<android.widget.FrameLayout>(R.id.progressContainer).visibility = View.GONE
            Toast.makeText(this, "Error en $section: ${error.localizedMessage}", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) {
            applyImmersiveMode()
            hideKeyboard()
            excludeSystemGestures()
        }
    }

    private fun startOfflineModeOnLaunch() {
        setOfflineMode(true)
        offlineBackup = loadOfflineBackup()
        setBackupReady(offlineBackup != null)
        updateOfflineTimestamp(offlineBackup)
        scope.launch {
            BackupIndexRepository(this@ScanActivity).ensureIndex(offlineBackup?.updatedAt)
        }
        if (offlineBackup == null) {
            showOutOfService()
            return
        }
    }

    // Reemplazar en setupMockInput el addTextChangedListener por un TextWatcher explícito
    private fun setupMockInput() {
        binding.btnMockScan.setOnClickListener {
            val code = binding.etMockCode.text?.toString()?.trim().orEmpty()
            submitMockIfValid(code)
        }
        binding.etMockCode.showSoftInputOnFocus = false
        binding.etMockCode.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                val code = binding.etMockCode.text?.toString()?.trim().orEmpty()
                submitMockIfValid(code)
                true
            } else {
                false
            }
        }
        binding.etMockCode.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(editable: android.text.Editable?) {
                val text = editable?.toString()?.trim().orEmpty()
                
                // Verificar si es el código de salida del modo kiosco
                if (isKioskMode && text == KIOSK_EXIT_CODE) {
                    Log.i(TAG, ">>> Código de salida detectado en TextWatcher! Desactivando modo kiosco...")
                    disableKioskMode()
                    isKioskMode = false
                    Toast.makeText(this@ScanActivity, "Modo kiosco desactivado", Toast.LENGTH_SHORT).show()
                    editable?.clear()
                    binding.etMockCode.requestFocus()
                    return
                }
                
                mockIdleRunnable?.let { uiHandler.removeCallbacks(it) }
                pendingMockText = if (text.length >= 8) text else null
                pendingMockText?.let { candidate ->
                    mockIdleRunnable = Runnable {
                        submitMockIfValid(candidate)
                    }
                    uiHandler.postDelayed(mockIdleRunnable!!, 120)
                }
            }
        })
    }

    private var cameraAvailable: Boolean = false  // Flag para saber si la cámara está activa

    private fun ensurePermissionAndStart() {
        // Cámara es opcional: solo se inicia si el permiso ya está concedido
        // Si no hay permiso, simplemente no se inicia (el escánero USB externo sigue funcionando)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            Log.d(TAG, "Cámara: permiso concedido, iniciando cámara...")
            cameraAvailable = true
            startCamera()
        } else {
            Log.d(TAG, "Cámara: sin permiso, modo solo escánero externo")
            cameraAvailable = false
            // No solicitar permiso - el escánero USB externo funciona sin cámara
        }
    }

    private fun resumeCameraIfAvailable() {
        // Solo reiniciar la cámara si está disponible (permiso concedido)
        if (cameraAvailable && ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        }
    }

    private fun applyImmersiveMode() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowCompat.setDecorFitsSystemWindows(window, false)
            window.insetsController?.let { controller ->
                controller.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                controller.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                    View.SYSTEM_UI_FLAG_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                )
        }
    }

    private fun hideKeyboard() {
        val imm = getSystemService(INPUT_METHOD_SERVICE) as? InputMethodManager ?: return
        imm.hideSoftInputFromWindow(binding.root.windowToken, 0)
    }

    private fun excludeSystemGestures() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            binding.root.post {
                val rect = Rect(0, 0, binding.root.width, binding.root.height)
                binding.root.systemGestureExclusionRects = listOf(rect)
            }
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            cameraProvider = cameraProviderFuture.get()
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
                // Filtrar solo códigos de barras válidos (EAN, UPC)
                val validFormats = listOf(
                    Barcode.FORMAT_EAN_13,
                    Barcode.FORMAT_EAN_8,
                    Barcode.FORMAT_UPC_A,
                    Barcode.FORMAT_UPC_E
                )
                val validBarcode = barcodes.firstOrNull { barcode ->
                    barcode.format in validFormats
                }
                validBarcode?.rawValue?.let { raw ->
                    if (raw.isNotBlank()) {
                        maybeProcessCode(raw)
                    }
                }
            }
            .addOnFailureListener { /* ignore: keep scanning */ }
            .addOnCompleteListener { imageProxy.close() }
    }

    private fun maybeProcessCode(code: String) {
        // Verificar si es el código de salida del modo kiosco
        Log.d(TAG, "maybeProcessCode: code='$code', isKioskMode=$isKioskMode, KIOSK_EXIT_CODE='$KIOSK_EXIT_CODE', equals=${code == KIOSK_EXIT_CODE}")
        
        if (isKioskMode && code == KIOSK_EXIT_CODE) {
            Log.i(TAG, ">>> Código de salida detectado! Desactivando modo kiosco...")
            disableKioskMode()
            isKioskMode = false
            Toast.makeText(this, "Modo kiosco desactivado", Toast.LENGTH_SHORT).show()
            // Limpiar el campo y no procesar más
            binding.etMockCode.text?.clear()
            return
        }
        
        val clean = sanitizeCode(code)
        if (clean == null) {
            // Código no válido (longitud incorrecta)
            Toast.makeText(this, "Código no válido. Use serial del producto.", Toast.LENGTH_SHORT).show()
            binding.etMockCode.requestFocus()
            return
        }
        
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
        resetStandbyTimer() // Reinicia el timer de publicidad también en mock
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

    // ===== MODO OFFLINE: helpers modulares =====

    // 1) Activar o desactivar indicador visual de modo offline
    private fun setOfflineMode(enabled: Boolean) {
        // Guarda el estado lógico, independiente del hilo.
        offlineMode = enabled
        // Ejecuta la actualización visual SIEMPRE en el hilo principal.
        if (Looper.getMainLooper().isCurrentThread) {
            // Actualiza el indicador principal de modo offline.
            binding.tvOfflineIndicator.visibility = if (enabled) View.VISIBLE else View.GONE
            // Actualiza la etiqueta de última sincronización del backup.
            binding.tvOfflineUpdated.visibility = if (enabled) View.VISIBLE else View.GONE
        } else {
            // Si estamos en un hilo de fondo, re-enviamos la UI al main thread.
            runOnUiThread {
                // Actualiza el indicador principal de modo offline.
                binding.tvOfflineIndicator.visibility = if (enabled) View.VISIBLE else View.GONE
                // Actualiza la etiqueta de última sincronización del backup.
                binding.tvOfflineUpdated.visibility = if (enabled) View.VISIBLE else View.GONE
            }
        }
    }

    private fun handleNetworkChange(available: Boolean) {
        Log.d(TAG, "BCV: handleNetworkChange - available=$available, isNetworkAvailable=$isNetworkAvailable")
        if (available == isNetworkAvailable) return
        isNetworkAvailable = available

        if (!available) {
            pingJob?.cancel()
            setOfflineMode(true)
            if (offlineBackup == null) {
                offlineBackup = loadOfflineBackup()
            }
            updateOfflineTimestamp(offlineBackup)
            return
        }

        if (api == null) {
            configureBackend()
        }
        setOfflineMode(false)
        api?.let { service ->
            startPingMonitor()
            resyncBackupIfOnline(service)
            syncBannersOnStart()
        }
        // Refrescar tasa BCV cuando vuelve la conexion
        Log.d(TAG, "BCV: handleNetworkChange - red disponible, invocando syncDolarBCV()")
        syncDolarBCV()
        scheduleDolarBCVRefresh()
    }

    // 2) Cargar respaldo local desde almacenamiento interno
    private fun loadOfflineBackup(): BackupResponse? {
        val repo = BackupRepository(this)
        val updatedAt = repo.getUpdatedAt() ?: return null
        return BackupResponse(updatedAt = updatedAt)
    }

    // 2.5) Descarga inicial del backup al entrar en ScanActivity
    private fun syncBackupOnStart() {
        val service = api ?: return
        scope.launch {
            try {
                Log.i(TAG, "Iniciando sincronización de backup (ScanActivity)")
                if (!shouldDownloadBackup()) {
                    Log.i(TAG, "Backup vigente, no se descarga")
                    offlineBackup = loadOfflineBackup()
                    uiHandler.post { updateOfflineTimestamp(offlineBackup) }
                    return@launch
                }
                isDownloading = true  // Bloquear salida durante descarga
                
                // Pausar carrusel antes de descargar backup
                uiHandler.post {
                    stopStandbyCarousel()
                    binding.standbyOverlay.visibility = View.GONE
                    Log.d(TAG, "Backup: carrusel pausado antes de descarga")
                }
                
                val repo = BackupRepository(this@ScanActivity, service)
                val result = repo.downloadAndSaveBackup(this@ScanActivity)
                Log.i(TAG, "Resultado backup en ScanActivity: ${result.isSuccess}")
                offlineBackup = loadOfflineBackup()
                setBackupReady(offlineBackup != null)
                isDownloading = false  // Permitir salida después de descarga
                
                // Reiniciar carrusel solo si el backup fue exitoso
                if (result.isSuccess) {
                    uiHandler.post {
                        startStandbyCarousel()
                        Log.d(TAG, "Backup: carrusel iniciado tras descarga exitosa")
                    }
                }
                
                scope.launch {
                    BackupIndexRepository(this@ScanActivity).ensureIndex(offlineBackup?.updatedAt)
                }
                uiHandler.post { updateOfflineTimestamp(offlineBackup) }
            } catch (e: Exception) {
                Log.e(TAG, "Error al sincronizar backup", e)
                isDownloading = false  // Permitir salida en caso de error
                // Reiniciar carrusel aunque haya error
                uiHandler.post { startStandbyCarousel() }
            } finally {
                hideProgress()
                isDownloading = false
            }
        }
    }

    // Sincroniza banners en segundo plano - fuer descarga inmediata cuando se recibe BANNER_INICIADO
    private fun syncBannersOnStart() {
        val service = api ?: return
        val baseUrl = backendBaseUrl ?: return
        scope.launch {
            try {
                val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                // Forzar descarga inmediata (maxAgeMs = 0) cuando se recibe BANNER_INICIADO
                repo.refreshIfStale(0L, deviceId)
            } catch (e: Exception) {
                Log.e(TAG, "Error al sincronizar banners", e)
            }
        }
    }

    // Elimina el archivo local de un banner específico
    private fun deleteBannerFile(bannerId: Int, url: String) {
        try {
            val ext = url.substringAfterLast('.', "")
            val safeExt = if (ext.isBlank()) "bin" else ext
            val fileName = "banner_$bannerId.$safeExt"
            val bannersDir = File(filesDir, "banners")
            val file = File(bannersDir, fileName)
            if (file.exists()) {
                if (file.delete()) {
                    Log.i(TAG, "[BannerCleanup] Archivo eliminado: $fileName")
                } else {
                    Log.w(TAG, "[BannerCleanup] No se pudo eliminar: $fileName")
                }
            } else {
                Log.d(TAG, "[BannerCleanup] Archivo no existe: $fileName")
            }
        } catch (e: Exception) {
            Log.e(TAG, "[BannerCleanup] Error al eliminar archivo del banner $bannerId", e)
        }
    }

    // Inicia polling de banners cada 25 minutos
    private fun startBannerPolling() {
        val runnable = object : Runnable {
            override fun run() {
                Log.d(TAG, "Banner polling: refreshing banners")
                val service = api
                val baseUrl = backendBaseUrl
                if (service != null && baseUrl != null) {
                    scope.launch {
                        try {
                            val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                            repo.refreshIfStale(bannerMaxAgeMs, deviceId)
                            Log.d(TAG, "Banner polling: refresh completed")
                        } catch (e: Exception) {
                            Log.e(TAG, "Banner polling: error", e)
                        }
                    }
                }
                bannerPollHandler.postDelayed(this, bannerPollIntervalMs)
            }
        }
        bannerPollRunnable = runnable
        bannerPollHandler.postDelayed(runnable, bannerPollIntervalMs)
    }

    // Detiene el polling de banners
    private fun stopBannerPolling() {
        bannerPollRunnable?.let { bannerPollHandler.removeCallbacks(it) }
        bannerPollRunnable = null
    }

    // Obtiene y muestra las cotizaciones BCV (USD y EUR)
    private fun syncDolarBCV() {
        Log.i(TAG, "BCV: syncDolarBCV() llamado")
        
        val today = java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US).format(java.util.Date())
        val cachedDate = prefsDolar.getString("fecha", null)
        val cachedUsd = prefsDolar.getFloat("usd", 0f)
        val cachedEur = prefsDolar.getFloat("eur", 0f)
        Log.d(TAG, "BCV: today=$today, cachedDate=$cachedDate, cachedUsd=$cachedUsd, cachedEur=$cachedEur")

        // Si ya tenemos del día de hoy, mostrar cache y salir
        if (cachedDate == today && (cachedUsd > 0f || cachedEur > 0f)) {
            Log.d(TAG, "BCV: mostrando datos cacheados")
            uiHandler.post {
                mostrarTasaBCV(cachedUsd, cachedEur)
            }
            return
        }

        Log.d(TAG, "BCV: sin cache o fecha diferente, llamando API...")
        dolarBcJob?.cancel()
        dolarBcJob = scope.launch {
            try {
                Log.d(TAG, "BCV: ejecutando getCotizaciones()")
                val cotizaciones = dolarRepository.getCotizaciones()
                Log.d(TAG, "BCV: respuesta cruda: $cotizaciones")
                
                val usd = cotizaciones["USD"]
                val eur = cotizaciones["EUR"]
                Log.d(TAG, "BCV: USD=$usd, EUR=$eur")

                if (usd != null || eur != null) {
                    val usdVal = usd?.promedio ?: 0.0
                    val eurVal = eur?.promedio ?: 0.0
                    
                    // Guardar fecha y valores
                    prefsDolar.edit()
                        .putString("fecha", today)
                        .putFloat("usd", usdVal.toFloat())
                        .putFloat("eur", eurVal.toFloat())
                        .apply()

                    uiHandler.post {
                        mostrarTasaBCV(usdVal.toFloat(), eurVal.toFloat())
                    }
                    Log.d(TAG, "BCV: cotizaciones actualizadas")
                } else {
                    Log.w(TAG, "BCV: API devolvio vacio")
                    uiHandler.post {
                        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.text = "Sin Actualizacion del BCV"
                        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.visibility = View.VISIBLE
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "BCV: Error fetching BCV rate", e)
                uiHandler.post {
                    findViewById<android.widget.TextView>(R.id.cardDolarBc)?.text = "Sin Actualizacion del BCV"
                    findViewById<android.widget.TextView>(R.id.cardDolarBc)?.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun mostrarTasaBCV(usd: Float, eur: Float) {
        val symbols = DecimalFormatSymbols(Locale("es", "VE")).apply {
            groupingSeparator = '.'
            decimalSeparator = ','
        }
        val formatter = DecimalFormat("#,##0.0000", symbols)

        val parts = mutableListOf<String>()
        if (usd > 0f) parts.add("USD: Bs ${formatter.format(usd)}")
        if (eur > 0f) parts.add("EUR: Bs ${formatter.format(eur)}")
        val textoFinal = parts.joinToString(" | ")

        Log.d(TAG, "BCV: mostrando - $textoFinal")
        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.text = textoFinal
        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.visibility = View.VISIBLE
        
        // También actualizar tvBcvOferta para la sección de ofertas
        findViewById<android.widget.TextView>(R.id.tvBcvOferta)?.text = textoFinal
        findViewById<android.widget.TextView>(R.id.tvBcvOferta)?.visibility = View.VISIBLE
    }

    // Programa actualización de la tasa BCV al iniciar día siguiente
    private fun scheduleDolarBCVRefresh() {
        val now = java.util.Calendar.getInstance()
        val midnight = java.util.Calendar.getInstance().apply {
            add(java.util.Calendar.DAY_OF_MONTH, 1)
            set(java.util.Calendar.HOUR_OF_DAY, 0)
            set(java.util.Calendar.MINUTE, 1)
            set(java.util.Calendar.SECOND, 0)
        }
        val msUntilMidnight = midnight.timeInMillis - now.timeInMillis

        uiHandler.postDelayed({
            if (isNetworkAvailable && !isFinishing) {
                syncDolarBCV()
            }
            scheduleDolarBCVRefresh()
        }, msUntilMidnight)
    }

    // Reinicia el temporizador de inactividad
    private fun resetStandbyTimer() {
        standbyTimerRunnable?.let { uiHandler.removeCallbacks(it) }
        standbyTimerRunnable = Runnable { startStandbyCarousel() }
        uiHandler.postDelayed(standbyTimerRunnable!!, standbyIdleMs)
        Log.d(TAG, "Standby timer programado en ${standbyIdleMs}ms")
    }

    // Inicia el carrusel leyendo el cache local
    private fun startStandbyCarousel() {
        if (standbyActive) return
        val baseUrl = backendBaseUrl ?: return
        val repo = api?.let { BannerRepository(this, it, baseUrl) } ?: return
        val cache = repo.loadCache() ?: return
        if (cache.items.isEmpty()) {
            Log.w(TAG, "Standby: cache vacío, no inicia carrusel")
            return
        }

        Log.i(TAG, "Standby: cache cargado items=${cache.items.size}")

        standbyItems = cache.items.toMutableList() // <-- Siempre mutable
        standbyIndex = 0
        standbyActive = true
        binding.standbyOverlay.visibility = View.VISIBLE
        playStandbyItem()
    }

    // Reproduce un item del carrusel (imagen o video)
    private fun playStandbyItem() {
        if (!standbyActive || standbyItems.isEmpty()) return
        // Proteger el índice
        if (standbyIndex >= standbyItems.size) standbyIndex = 0
        val item = standbyItems[standbyIndex]
        val fileExists = java.io.File(item.localPath).exists()
        if (!fileExists) {
            // Contador de reintentos para evitar spam de notificaciones
            val currentRetry = retryCountMap.getOrDefault(item.localPath, 0)
            val newRetry = currentRetry + 1
            retryCountMap[item.localPath] = newRetry
            
            if (newRetry >= MAX_RETRY_BEFORE_REPORT) {
                // Solo reportar si falló MAX_RETRY_BEFORE_REPORT veces consecutivas
                Log.w(TAG, "Standby: archivo no existe tras $newRetry intentos, eliminando de la lista: ${item.localPath}")
                reportPlaybackFailure(
                    localPath = item.localPath,
                    reason = "Archivo no encontrado tras $newRetry intentos"
                )
                retryCountMap.remove(item.localPath)
            } else {
                Log.w(TAG, "Standby: archivo no existe (intento $newRetry/$MAX_RETRY_BEFORE_REPORT), reintentando: ${item.localPath}")
            }
            
            if (standbyItems.isNotEmpty()) {
                standbyItems.removeAt(standbyIndex)
            }
            if (standbyItems.isEmpty()) {
                Log.e(TAG, "Standby: todos los archivos han sido eliminados. Deteniendo carrusel.")
                stopStandbyCarousel()
                return
            }
            if (standbyIndex >= standbyItems.size) standbyIndex = 0
            playStandbyItem()
            return
        }
        
        // Si el archivo existe, resetear el contador de reintentos
        retryCountMap.remove(item.localPath)
        Log.i(TAG, "Standby: item idx=$standbyIndex tipo=${item.tipo} path=${item.localPath} exists=$fileExists")
        standbySlideRunnable?.let { uiHandler.removeCallbacks(it) }
        binding.standbyImage.visibility = View.GONE
        binding.standbyVideo.visibility = View.GONE
        releaseStandbyBitmap()
        if (item.tipo == "video") {
            binding.standbyVideo.visibility = View.VISIBLE
            binding.standbyVideo.setOnCompletionListener {
                nextStandbyItem()
            }
            binding.standbyVideo.setOnPreparedListener { mp ->
                mp.setVideoScalingMode(android.media.MediaPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT)
            }
            binding.standbyVideo.setOnErrorListener { _, what, extra ->
                Log.w(TAG, "Standby: error video what=$what extra=$extra para ${item.localPath}")
                
                // Contador de reintentos para errores de video
                val currentRetry = retryCountMap.getOrDefault(item.localPath, 0)
                val newRetry = currentRetry + 1
                retryCountMap[item.localPath] = newRetry
                
                // Solo reportar si falló MAX_RETRY_BEFORE_REPORT veces consecutivas
                if (newRetry >= MAX_RETRY_BEFORE_REPORT) {
                    reportPlaybackFailure(
                        localPath = item.localPath,
                        reason = "VideoView error what=$what extra=$extra tras $newRetry intentos"
                    )
                    retryCountMap.remove(item.localPath)
                } else {
                    Log.w(TAG, "Standby: error video (intento $newRetry/$MAX_RETRY_BEFORE_REPORT), reintentando...")
                }
                
                if (standbyItems.size == 1) {
                    stopStandbyCarousel()
                } else {
                    if (standbyItems.isNotEmpty()) {
                        standbyItems.removeAt(standbyIndex)
                    }
                    if (standbyItems.isEmpty()) {
                        stopStandbyCarousel()
                    } else {
                        if (standbyIndex >= standbyItems.size) standbyIndex = 0
                        playStandbyItem()
                    }
                }
                true
            }
            val videoFile = java.io.File(item.localPath)
            val videoUri = android.net.Uri.fromFile(videoFile)
            binding.standbyVideo.setVideoURI(videoUri)
            binding.standbyVideo.start()
        } else {
            binding.standbyImage.visibility = View.VISIBLE
            val reqWidth = if (binding.standbyImage.width > 0) binding.standbyImage.width else resources.displayMetrics.widthPixels
            val reqHeight = if (binding.standbyImage.height > 0) binding.standbyImage.height else resources.displayMetrics.heightPixels
            val bitmap = decodeSampledBitmap(item.localPath, reqWidth, reqHeight)
            if (bitmap == null) {
                Log.w(TAG, "Standby: bitmap nulo para ${item.localPath}")
                nextStandbyItem()
                return
            }
            currentStandbyBitmap = bitmap
            binding.standbyImage.setImageBitmap(bitmap)
            val durationMs = ((item.duracionSeg ?: 10) * 1000L)
            standbySlideRunnable = Runnable { nextStandbyItem() }
            uiHandler.postDelayed(standbySlideRunnable!!, durationMs)
        }
    }

    // Avanza al siguiente elemento del carrusel
    private fun nextStandbyItem() {
        if (!standbyActive || standbyItems.isEmpty()) return
        standbyIndex = (standbyIndex + 1) % standbyItems.size
        playStandbyItem()
    }

    // Detiene el carrusel y limpia el overlay
    private fun stopStandbyCarousel() {
        if (!standbyActive) return
        standbyActive = false
        standbySlideRunnable?.let { uiHandler.removeCallbacks(it) }
        binding.standbyVideo.stopPlayback()
        binding.standbyOverlay.visibility = View.GONE
        releaseStandbyBitmap()
        Log.d(TAG, "Standby: detenido")
    }

    private fun releaseStandbyBitmap() {
        binding.standbyImage.setImageDrawable(null)
        currentStandbyBitmap?.let {
            if (!it.isRecycled) it.recycle()
        }
        currentStandbyBitmap = null
    }

    private fun decodeSampledBitmap(path: String, reqWidth: Int, reqHeight: Int): Bitmap? {
        return try {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(path, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

            val decodeOptions = BitmapFactory.Options().apply {
                inPreferredConfig = Bitmap.Config.RGB_565
                inDither = true
                inScaled = false
                inSampleSize = calculateInSampleSize(bounds.outWidth, bounds.outHeight, reqWidth, reqHeight)
            }
            BitmapFactory.decodeFile(path, decodeOptions)
        } catch (oom: OutOfMemoryError) {
            Log.e(TAG, "Standby: OOM decodificando imagen $path", oom)
            null
        } catch (e: Exception) {
            Log.e(TAG, "Standby: error decodificando imagen $path", e)
            null
        }
    }

    private fun calculateInSampleSize(srcWidth: Int, srcHeight: Int, reqWidth: Int, reqHeight: Int): Int {
        var inSampleSize = 1
        if (srcHeight > reqHeight || srcWidth > reqWidth) {
            var halfHeight = srcHeight / 2
            var halfWidth = srcWidth / 2
            while ((halfHeight / inSampleSize) >= reqHeight && (halfWidth / inSampleSize) >= reqWidth) {
                inSampleSize *= 2
            }
        }
        return inSampleSize.coerceAtLeast(1)
    }

    // 2.1) Re-sincronizar respaldo local cuando vuelve la conexión
    private fun resyncBackupIfOnline(service: ApiService) {
        scope.launch {
            try {
                if (!shouldDownloadBackup()) {
                    offlineBackup = loadOfflineBackup()
                    uiHandler.post { updateOfflineTimestamp(offlineBackup) }
                    return@launch
                }
                isDownloading = true  // Bloquear salida durante descarga
                
                // Pausar carrusel antes de descargar backup
                uiHandler.post {
                    stopStandbyCarousel()
                    binding.standbyOverlay.visibility = View.GONE
                    Log.d(TAG, "Backup: carrusel pausado antes de resincronización")
                }
                
                val repo = BackupRepository(this@ScanActivity, service)
                val result = repo.downloadAndSaveBackup(this@ScanActivity)
                offlineBackup = loadOfflineBackup()
                setBackupReady(offlineBackup != null)
                isDownloading = false  // Permitir salida después de descarga
                
                // Reiniciar carrusel solo si el backup fue exitoso
                if (result.isSuccess) {
                    uiHandler.post {
                        startStandbyCarousel()
                        Log.d(TAG, "Backup: carrusel iniciado tras resincronización exitosa")
                    }
                }
                
                scope.launch {
                    BackupIndexRepository(this@ScanActivity).ensureIndex(offlineBackup?.updatedAt)
                }
                uiHandler.post { updateOfflineTimestamp(offlineBackup) }
            } catch (_: Exception) {
                // En caso de fallo, mantener el respaldo existente
                isDownloading = false
                // Reiniciar carrusel aunque haya error
                uiHandler.post { startStandbyCarousel() }
            } finally {
                hideProgress()
                isDownloading = false
            }
        }
    }

    private fun setBackupReady(ready: Boolean) {
        backupReady = ready
        if (ready && !backupReadyNotified) {
            backupReadyNotified = true
            uiHandler.post {
                Toast.makeText(this, "Respaldo listo. Puedes salir", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun shouldDownloadBackup(): Boolean {
        val repo = BackupRepository(this)
        val updatedAt = repo.getUpdatedAt() ?: return true
        val updatedAtMillis = parseIsoToMillis(updatedAt) ?: return true
        return System.currentTimeMillis() - updatedAtMillis > backupMaxAgeMs
    }

    // 2.2) Actualizar texto de última sincronización del backup
    private fun updateOfflineTimestamp(backup: BackupResponse?) {
        val updatedAt = backup?.updatedAt
        val formatted = formatIsoToReadable(updatedAt) ?: "-"
        runOnUiThread {
            binding.tvOfflineUpdated.text = getString(
                R.string.offline_last_update_format,
                formatted
            )
        }
    }

    // 2.4) Validar antigüedad del respaldo local (máx 12h)
    private fun isBackupStale(backup: BackupResponse?): Boolean {
        val updatedAtMillis = BackupUtils.parseIsoToMillis(backup?.updatedAt) ?: return true
        return System.currentTimeMillis() - updatedAtMillis > backupMaxAgeMs
    }

    // 2.3) Formatear fecha ISO a formato legible local (dd/MM/yyyy HH:mm)
    private fun formatIsoToReadable(value: String?): String? {
        val millis = BackupUtils.parseIsoToMillis(value) ?: return null
        return try {
            val out = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault())
            out.format(java.util.Date(millis))
        } catch (_: Exception) {
            null
        }
    }

    // 3) Parsear fechas ISO a milisegundos (usa BackupUtils que maneja múltiples formatos)
    private fun parseIsoToMillis(value: String?): Long? {
        return BackupUtils.parseIsoToMillis(value)
    }

    private fun onBarcodeDetected(code: String) {
        stopStandbyCarousel()
        resetStandbyTimer() // Reinicia el timer de publicidad cada vez que se escanea
        if (!isNetworkAvailable) {
            if (!offlineMode) {
                setOfflineMode(true)
            }
            handleOfflineLookup(code)
            return
        }
        // 7) Consulta offline si el modo offline está activo
        if (offlineMode) {
            handleOfflineLookup(code)
            return
        }

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
                var setOffline = false
                val (key, msg) = when (e) {
                    is HttpException -> when (e.code()) {
                        404 -> "404" to "Producto no encontrado"
                        in 500..599 -> "5xx" to "Error del servidor (${e.code()})"
                        else -> "4xx" to "Error HTTP (${e.code()})"
                    }
                    is SocketTimeoutException -> {
                        setOffline = true
                        "timeout" to "Tiempo de Conexion agotado"
                    }
                    is IOException -> {
                        setOffline = true
                        "network" to "Fallo de red o conexión"
                    }
                    else -> "unknown" to "Error inesperado"
                }
                if (setOffline && !offlineMode) {
                    setOfflineMode(true)
                }
                uiHandler.post {
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

    // 8) Resolver consulta con respaldo local
    private fun handleOfflineLookup(code: String) {
        scope.launch {
            requestInFlight = true
            try {
                val backup = offlineBackup ?: loadOfflineBackup()
                if (backup == null) {
                    Log.w(TAG, "[OFFLINE] showOutOfService: backup == null")
                    uiHandler.post { showOutOfService() }
                    return@launch
                }
                val isStale = isBackupStale(backup)
                Log.d(TAG, "[OFFLINE] Backup updatedAt: ${backup.updatedAt}, isStale: $isStale")
                if (isStale) {
                    Log.w(TAG, "[OFFLINE] showOutOfService: backup stale (más de 12h)")
                    uiHandler.post { showOutOfService() }
                    return@launch
                }
                offlineBackup = backup
                val indexRepo = BackupIndexRepository(this@ScanActivity)
                val producto = indexRepo.lookupProductoOffline(code)
                    ?: BackupRepository(this@ScanActivity).lookupProductoOffline(code)
                if (producto == null) {
                    uiHandler.post { showThrottledError("offline_not_found", "Producto no encontrado") }
                    return@launch
                }
                uiHandler.post {
                    feedbackSuccess()
                    showResult(producto)
                    pauseUntil = android.os.SystemClock.elapsedRealtime() + 4000
                }
            } finally {
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
        val port = prefs.getString("puerto_servidor", getString(R.string.default_port))

        val sanitized = host?.let { NetworkUtils.sanitizeHost(it) }
        val defaultPort = getString(R.string.default_port)

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
        backendBaseUrl = normalized
        api = ApiClient.create(normalized, BuildConfig.DEBUG)
        return true
    }

    private fun reportPlaybackFailure(localPath: String, reason: String) {
        val service = api ?: return
        val fileName = runCatching { File(localPath).name }.getOrDefault(localPath)
        val reportKey = "playback_failed:$fileName:$reason"
        val now = android.os.SystemClock.elapsedRealtime()
        if (reportKey == lastPlaybackReportKey && (now - lastPlaybackReportAt) < 15_000) {
            return
        }
        lastPlaybackReportKey = reportKey
        lastPlaybackReportAt = now

        scope.launch {
            try {
                service.reportPlaybackStatus(
                    PlaybackStatusRequest(
                        deviceId = deviceId,
                        videoName = fileName,
                        reason = reason,
                    )
                )
                Log.i(TAG, "Playback error report enviado: $fileName")
            } catch (e: Exception) {
                Log.w(TAG, "No se pudo reportar playback error al backend-api: ${e.message}")
            }
        }
    }

    private fun startPingMonitor() {
        val service = api ?: return
        pingJob?.cancel()
        pingJob = scope.launch {
            var offlineRetry = false
            while (isActive) {
                val (ok, reason) = pingWithRetries(service)
                if (!ok) {
                    val backup = offlineBackup ?: loadOfflineBackup()
                    if (backup != null) {
                        if (isBackupStale(backup)) {
                            uiHandler.post {
                                showThrottledError("offline_stale", "Respaldo vencido (24h). Conéctate al servidor")
                            }
                            goToConfig("Respaldo vencido. Regresando a configuración")
                            return@launch
                        }
                        offlineBackup = backup
                        setOfflineMode(true)
                        uiHandler.post { updateOfflineTimestamp(offlineBackup) }
                        // Reintenta ping cada 60 segundos en modo offline
                        delay(60000)
                        offlineRetry = true
                        continue
                    }
                    goToConfig(reason ?: "Conexión perdida. Regresando a configuración")
                    return@launch
                }
                if (offlineMode || offlineRetry) {
                    setOfflineMode(false)
                    resyncBackupIfOnline(service)
                    offlineRetry = false
                }
                // Ping cada 180 segundos (3 minutos) en modo online
                delay(180000)
            }
        }
    }

    private suspend fun pingWithRetries(service: ApiService): Pair<Boolean, String?> {
        val delays = listOf(0L, 1500L)
        var lastReason: String? = null
        for (waitMs in delays) {
            if (waitMs > 0) delay(waitMs)
            try {
                service.ping(deviceId)
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

        // Obtener dimensiones según el tamaño de pantalla
        val config = resources.configuration
        val screenWidthDp = config.smallestScreenWidthDp
        val esTabletPequena = screenWidthDp < 600
        
        // Si el nombre supera 25 caracteres, reducir tamaño
        val tamanoNormal = if (esTabletPequena) 35f else 45f
        val tamanoReducido = if (esTabletPequena) 28f else 35f
        
        if (producto.nombre.length > 25) {
            binding.tvNombre.textSize = tamanoReducido
        } else {
            binding.tvNombre.textSize = tamanoNormal
        }

        // Mostrar precio en Bs con separador de miles y decimales
        val precioBs = producto.pvpBaseOferta ?: producto.pvpBase ?: 0.0
        val symbols = DecimalFormatSymbols(Locale("es", "VE")).apply {
            groupingSeparator = '.'
            decimalSeparator = ','
        }
        val formatter = DecimalFormat("#,##0.##", symbols)
        val precioBsFormateado = formatter.format(precioBs)
        val precioBsText = "Bs $precioBsFormateado"
        binding.tvPrecioActual.text = precioBsText
        
        // Si el texto supera 25 caracteres, achicar el tamaño
        val tamanoPrecioNormal = if (esTabletPequena) 30f else 40f
        val tamanoPrecioReducido = if (esTabletPequena) 24f else 30f
        
        if (precioBsText.length > 25) {
            binding.tvPrecioActual.textSize = tamanoPrecioReducido
        } else {
            binding.tvPrecioActual.textSize = tamanoPrecioNormal
        }

        // Mostrar mensaje informativo de IVA
        binding.tvIva.text = getString(R.string.price_with_iva_format)

        // Mostrar precio en $ en txtprecio
        val precioUsd = producto.pvpOferta ?: producto.pvpConversion ?: 0.0
        binding.tvPrecioDolar.text = getString(R.string.price_usd_format, precioUsd)

        if (producto.pvpOferta != null && producto.pvpOferta > 0) {
            // Mostrar diseño de oferta
            binding.resultCard.setCardBackgroundColor(getColor(R.color.oferta_yellow))
            binding.ofertaGroup.visibility = View.VISIBLE
            binding.infoGroup.visibility = View.GONE
            // Setear datos de oferta
            binding.tvNombreOferta.text = producto.nombre
            binding.tvPrecioOferta.text = String.format(Locale.US, "$%.2f", producto.pvpOferta)
            // Mostrar precio en bolívares en la oferta
            val precioBs = producto.pvpBaseOferta ?: producto.pvpBase ?: 0.0
            val symbols = DecimalFormatSymbols(Locale("es", "VE")).apply {
                groupingSeparator = '.'
                decimalSeparator = ','
            }
            val formatter = DecimalFormat("#,##0.##", symbols)
            val precioBsFormateado = formatter.format(precioBs)
            binding.tvPrecioBsOferta.text = "Bs $precioBsFormateado"
            
            // Reducir tamaño si el texto supera 25 caracteres (usando tamaños del XML)
            val tamanoNombreOferta = resources.getDimension(R.dimen.text_size_nombre_oferta) / resources.displayMetrics.scaledDensity
            val tamanoNombreReducido = tamanoNombreOferta * 0.8f
            if (producto.nombre.length > 25) {
                binding.tvNombreOferta.textSize = tamanoNombreReducido
            }
            
            val tamanoPrecioOferta = resources.getDimension(R.dimen.text_size_precio_oferta) / resources.displayMetrics.scaledDensity
            val tamanoPrecioOfertaReducido = tamanoPrecioOferta * 0.8f
            val precioOfertaText = String.format(Locale.US, "$%.2f", producto.pvpOferta)
            if (precioOfertaText.length > 25) {
                binding.tvPrecioOferta.textSize = tamanoPrecioOfertaReducido
            }
            
            val tamanoPrecioBsOferta = resources.getDimension(R.dimen.text_size_precio_bs_oferta) / resources.displayMetrics.scaledDensity
            val tamanoPrecioBsOfertaReducido = tamanoPrecioBsOferta * 0.8f
            val precioBsOfertaText = "Bs $precioBsFormateado"
            if (precioBsOfertaText.length > 25) {
                binding.tvPrecioBsOferta.textSize = tamanoPrecioBsOfertaReducido
            }
            
            // Puedes agregar aquí lógica para IVA, total ref, etc.
        } else {
            // Mostrar diseño normal
            binding.resultCard.setCardBackgroundColor(getColor(R.color.cardview_default_background))
            binding.ofertaGroup.visibility = View.GONE
            binding.infoGroup.visibility = View.VISIBLE
        }

        binding.resultOverlay.visibility = View.VISIBLE
        pauseAnalyzer(true)

        // Ocultar automáticamente tras 3 segundos, limpiando anteriores
        resultHideRunnable?.let { uiHandler.removeCallbacks(it) }
        resultHideRunnable = Runnable {
            binding.resultOverlay.visibility = View.GONE
            pauseAnalyzer(false)
            binding.etMockCode.requestFocus()
            resetStandbyTimer()
        }
        uiHandler.postDelayed(resultHideRunnable!!, 4_000)
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
        resetScanStateAfterError()
        binding.etMockCode.requestFocus()
        val now = android.os.SystemClock.elapsedRealtime()
        if (key == lastErrorKey && (now - lastErrorAt) < minIntervalMs) return
        lastErrorKey = key
        lastErrorAt = now

        val overlayVisible = binding.resultOverlay.isVisible
        Log.w(TAG, "scan_error key=$key overlay=$overlayVisible msg=$message")
        if (!overlayVisible) {
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
        }
    }

    private fun resetScanStateAfterError() {
        pauseUntil = 0L
        lastScanAt = 0L
        requestInFlight = false
        lastCode = null
        pauseAnalyzer(false)
        resetStandbyTimer() // Reinicia el temporizador de standby para que vuelva la publicidad
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

    override fun onStart() {
        super.onStart()
        val cm = connectivityManager ?: return
        if (!networkCallbackRegistered) {
            val request = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()
            runCatching {
                cm.registerNetworkCallback(request, networkCallback)
                networkCallbackRegistered = true
            }
        }
        val networkAvailable = NetworkUtils.isNetworkAvailable(this)
        Log.d(TAG, "BCV: onStart - NetworkUtils.isNetworkAvailable=$networkAvailable")
        handleNetworkChange(networkAvailable)
    }

    override fun onStop() {
        super.onStop()
        val cm = connectivityManager ?: return
        if (networkCallbackRegistered) {
            runCatching {
                cm.unregisterNetworkCallback(networkCallback)
                networkCallbackRegistered = false
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopBannerPolling()
        cameraProvider?.unbindAll()
        cameraExecutor.shutdown()
        tone?.release()
        tone = null
        job.cancel()
        scope.cancel()
        dolarBcJob?.cancel()
        tabletWebSocket?.close(1000, "Activity destroyed")
        wsClient?.dispatcher?.executorService?.shutdown()
    }

    override fun onPause() {
        super.onPause()
        cameraProvider?.unbindAll()
    }

    override fun onResume() {
        super.onResume()
        
        // Activar modo kiosco si es Device Owner (con pequeño delay para que la vista esté lista)
        if (isDeviceOwner() && !isKioskMode) {
            uiHandler.postDelayed({
                if (!isKioskMode) {
                    enableKioskMode()
                    isKioskMode = true
                    Log.i(TAG, "Modo kiosco activado en onResume (delayed)")
                }
            }, 500) // 500ms de delay
        }
        
        resumeCameraIfAvailable()  // Solo reiniciar cámara si está disponible
        binding.etMockCode.requestFocus()
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

    // Ocultar progressBar al terminar la descarga
    private fun hideProgress() {
        runOnUiThread {
            findViewById<android.widget.FrameLayout>(R.id.progressContainer).visibility = View.GONE
        }
    }

    // Método para manejar mensajes de WebSocket
    private fun handleWebSocketMessage(message: String) {
        // Ejemplo de parseo simple, ajustar según formato real
        if (message == "WIPE_AND_RESYNC") {
            val apiService = api ?: return
            val baseUrl = backendBaseUrl ?: return
            scope.launch {
                ejecutarPurgaTotal(this@ScanActivity, apiService, baseUrl, deviceId)
            }
        }
        // ...otros comandos...
    }

    private fun startTabletWebSocket() {
        Log.i(TAG, "[WebSocket] startTabletWebSocket() llamado")
        val baseUrl = backendBaseUrl ?: run {
            Log.e(TAG, "[WebSocket] backendBaseUrl es null, no se puede conectar")
            return
        }
        val cleanBaseUrl = baseUrl.trimEnd('/')
        val wsUrl = cleanBaseUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws/tablet"
        Log.i(TAG, "[WebSocket] Intentando conectar a: $wsUrl")
        try {
            wsClient = OkHttpClient()
            val request = Request.Builder().url(wsUrl).build()
            val wsListener = object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                    Log.i(TAG, "[WebSocket] Conexión abierta: $wsUrl")
                    try {
                        val identifyMsg = org.json.JSONObject()
                        identifyMsg.put("type", "IDENTIFY")
                        identifyMsg.put("device_id", deviceId)
                        webSocket.send(identifyMsg.toString())
                        Log.i(TAG, "[WebSocket] Identificación enviada: device_id=$deviceId")
                    } catch (e: Exception) {
                        Log.e(TAG, "[WebSocket] Error enviando identificación", e)
                    }
                }
                override fun onMessage(webSocket: WebSocket, text: String) {
                    Log.i(TAG, "[WebSocket] Mensaje recibido (texto): $text")
                    try {
                        val message = org.json.JSONObject(text)
                        val type = message.optString("type")
                        
                        if (type == "ping") {
                            Log.d(TAG, "[WebSocket] Ping recibido, enviando pong...")
                            val pongMsg = org.json.JSONObject()
                            pongMsg.put("type", "pong")
                            pongMsg.put("timestamp", message.optLong("timestamp", System.currentTimeMillis() / 1000))
                            webSocket.send(pongMsg.toString())
                            Log.d(TAG, "[WebSocket] Pong enviado")
                            return
                        }
                        
                        val command = message.optString("command")
                        if (command.isEmpty()) {
                            return
                        }
                        
                        try {
                            sendSyncConfirmation(webSocket, command, "RECEIVED")
                            Log.i(TAG, "[WebSocket] Confirmación enviada para comando: $command")
                        } catch (e: Exception) {
                            Log.e(TAG, "[WebSocket] Error enviando confirmación", e)
                        }
                        if (command == "WIPE_AND_RESYNC") {
                            Log.i(TAG, "[WebSocket] Comando WIPE_AND_RESYNC recibido. Pausando carrusel antes de purga...")
                            
                            // 1. PAUSAR el carrusel INMEDIATAMENTE antes de borrar archivos
                            uiHandler.post {
                                stopStandbyCarousel()
                                binding.standbyOverlay.visibility = View.GONE
                                Log.d(TAG, "[WebSocket] Carrusel detenido y overlay ocultado")
                            }
                            
                            scope.launch {
                                val apiService = api
                                if (apiService == null) {
                                    sendSyncConfirmation(webSocket, command, "FAILED", "ApiService no inicializado")
                                    return@launch
                                }

                                // 2. Ejecutar purga SIN callback de inicio de carrusel
                                val purgeResult = ejecutarPurgaTotal(this@ScanActivity, apiService, baseUrl, deviceId) {
                                    // Callback vacío - controlamos el inicio manualmente
                                }

                                // 3. Solo iniciar carrusel DESPUÉS de que la purga termine exitosamente
                                uiHandler.post {
                                    if (purgeResult.success) {
                                        Log.i(TAG, "[WebSocket] Purga exitosa, iniciando carrusel...")
                                        startStandbyCarousel()
                                    } else {
                                        Log.w(TAG, "[WebSocket] Purga fallida, no se inicia carrusel")
                                        sendSyncConfirmation(webSocket, command, "FAILED", purgeResult.reason ?: "Purga fallida")
                                    }
                                }

                                if (purgeResult.success) {
                                    sendSyncConfirmation(webSocket, command, "SUCCESS")
                                } else {
                                    sendSyncConfirmation(webSocket, command, "FAILED", purgeResult.reason ?: "Purga fallida")
                                }
                            }
                        } else if (command == "BANNER_INICIADO") {
                            val bannerId = message.optInt("banner_id", 0)
                            val titulo = message.optString("titulo", "")
                            Log.i(TAG, "[WebSocket] BANNER_INICIADO recibido: id=$bannerId, titulo=$titulo")
                            
                            // Recargar banners inmediatamente cuando un banner comienza
                            uiHandler.post {
                                syncBannersOnStart()
                                Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_INICIADO")
                                // Confirmar al backend que el banner fue recibido
                                sendSyncConfirmation(webSocket, command, "SUCCESS")
                            }
                        } else if (command == "BANNER_FINALIZADO") {
                            val bannerId = message.optInt("banner_id", 0)
                            val titulo = message.optString("titulo", "")
                            val bannerUrl = message.optString("url", "")
                            Log.i(TAG, "[WebSocket] BANNER_FINALIZADO recibido: id=$bannerId, titulo=$titulo")
                            
                            // Eliminar archivo local del banner que terminó
                            if (bannerId > 0 && bannerUrl.isNotEmpty()) {
                                deleteBannerFile(bannerId, bannerUrl)
                            }
                            
                            // Recargar banners inmediatamente cuando un banner termina
                            uiHandler.post {
                                syncBannersOnStart()
                                Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_FINALIZADO")
                                // Confirmar al backend que el banner fue recibido
                                sendSyncConfirmation(webSocket, command, "SUCCESS")
                            }
                        } else {
                            Log.i(TAG, "[WebSocket] Comando recibido no reconocido: $command")
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "[WebSocket] Error procesando mensaje WebSocket (texto)", e)
                    }
                }
                override fun onMessage(webSocket: WebSocket, bytes: okio.ByteString) {
                    Log.w(TAG, "[WebSocket] Mensaje recibido (binario): ${bytes.hex()}")
                    try {
                        val text = bytes.utf8()
                        Log.w(TAG, "[WebSocket] Binario decodificado como texto: $text")
                        val message = org.json.JSONObject(text)
                        val type = message.optString("type")
                        
                        if (type == "ping") {
                            Log.d(TAG, "[WebSocket] Ping recibido (binario), enviando pong...")
                            val pongMsg = org.json.JSONObject()
                            pongMsg.put("type", "pong")
                            pongMsg.put("timestamp", message.optLong("timestamp", System.currentTimeMillis() / 1000))
                            webSocket.send(pongMsg.toString())
                            Log.d(TAG, "[WebSocket] Pong enviado (binario)")
                            return
                        }
                        
                        val command = message.optString("command")
                        if (command.isEmpty()) {
                            return
                        }
                        
                        try {
                            sendSyncConfirmation(webSocket, command, "RECEIVED")
                            Log.i(TAG, "[WebSocket] Confirmación enviada para comando (binario): $command")
                        } catch (e: Exception) {
                            Log.e(TAG, "[WebSocket] Error enviando confirmación (binario)", e)
                        }
                        if (command == "WIPE_AND_RESYNC") {
                            Log.i(TAG, "[WebSocket] Comando WIPE_AND_RESYNC recibido (binario). Ejecutando purga total...")
                            scope.launch {
                                val apiService = api
                                if (apiService == null) {
                                    sendSyncConfirmation(webSocket, command, "FAILED", "ApiService no inicializado")
                                    return@launch
                                }

                                val purgeResult = ejecutarPurgaTotal(this@ScanActivity, apiService, baseUrl, deviceId) {
                                    uiHandler.post {
                                        stopStandbyCarousel()
                                        startStandbyCarousel()
                                    }
                                }

                                if (purgeResult.success) {
                                    sendSyncConfirmation(webSocket, command, "SUCCESS")
                                } else {
                                    sendSyncConfirmation(webSocket, command, "FAILED", purgeResult.reason ?: "Purga fallida")
                                }
                            }
                        } else if (command == "BANNER_INICIADO") {
                            val bannerId = message.optInt("banner_id", 0)
                            val titulo = message.optString("titulo", "")
                            Log.i(TAG, "[WebSocket] BANNER_INICIADO recibido (binario): id=$bannerId, titulo=$titulo")
                            
                            uiHandler.post {
                                syncBannersOnStart()
                                Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_INICIADO (binario)")
                                // Confirmar al backend que el banner fue recibido
                                sendSyncConfirmation(webSocket, command, "SUCCESS")
                            }
                        } else if (command == "BANNER_FINALIZADO") {
                            val bannerId = message.optInt("banner_id", 0)
                            val titulo = message.optString("titulo", "")
                            val bannerUrl = message.optString("url", "")
                            Log.i(TAG, "[WebSocket] BANNER_FINALIZADO recibido (binario): id=$bannerId, titulo=$titulo")
                            
                            // Eliminar archivo local del banner que terminó
                            if (bannerId > 0 && bannerUrl.isNotEmpty()) {
                                deleteBannerFile(bannerId, bannerUrl)
                            }
                            
                            uiHandler.post {
                                syncBannersOnStart()
                                Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_FINALIZADO (binario)")
                                // Confirmar al backend que el banner fue recibido
                                sendSyncConfirmation(webSocket, command, "SUCCESS")
                            }

                        } else {
                            Log.i(TAG, "[WebSocket] Comando recibido no reconocido (binario): $command")
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "[WebSocket] Error procesando mensaje WebSocket (binario)", e)
                    }
                }
                override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
                    Log.e(TAG, "[WebSocket] Error de conexión: ${t.message}", t)
                    reconnectTabletWebSocket()
                }
                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    Log.w(TAG, "[WebSocket] Conexión cerrada: $reason")
                    reconnectTabletWebSocket()
                }
            }
            tabletWebSocket = wsClient!!.newWebSocket(request, wsListener)
        } catch (e: Exception) {
            Log.e(TAG, "[WebSocket] Excepción al crear WebSocket: ${e.message}", e)
        }
    }

    private fun reconnectTabletWebSocket() {
        // Espera 5 segundos y reconecta
        uiHandler.postDelayed({ startTabletWebSocket() }, 5000)
    }

    private fun sendSyncConfirmation(
        webSocket: WebSocket,
        command: String,
        status: String,
        reason: String? = null,
    ) {
        try {
            val confirmMsg = org.json.JSONObject()
            confirmMsg.put("type", "CONFIRMATION")
            confirmMsg.put("command", command)
            confirmMsg.put("device_id", deviceId)
            confirmMsg.put("status", status)
            if (!reason.isNullOrBlank()) {
                confirmMsg.put("reason", reason)
            }
            webSocket.send(confirmMsg.toString())
            Log.i(TAG, "[WebSocket] Confirmación enviada: status=$status command=$command")
        } catch (e: Exception) {
            Log.e(TAG, "[WebSocket] Error enviando confirmación status=$status command=$command", e)
        }
    }

    private fun showOutOfService() {
        runOnUiThread {
            binding.resultOverlay.visibility = View.VISIBLE
            binding.tvNombre.text = "Fuera de Servicio"
            binding.tvPrecioActual.text = ""
            binding.tvPrecioDolar.text = ""
            binding.tvIva.text = ""
            binding.tvOferta.visibility = View.GONE
            binding.resultCard.setCardBackgroundColor(getColor(R.color.cardview_default_background))
            binding.tvOfflineIndicator.visibility = View.VISIBLE
            binding.tvOfflineUpdated.visibility = View.VISIBLE
            binding.etMockCode.isEnabled = true
            binding.etMockCode.requestFocus()
            binding.btnMockScan.isEnabled = true
        }
    }

    // ========================
    // Modo Kiosco (Lock Task)
    // ========================

    private fun isDeviceOwner(): Boolean {
        return try {
            dpm.isDeviceOwnerApp(packageName)
        } catch (e: Exception) {
            Log.e(TAG, "Error checking device owner", e)
            false
        }
    }

    private fun enableKioskMode() {
        Log.i(TAG, "Intentando activar modo kiosco...")
        Log.i(TAG, "isDeviceOwner: ${isDeviceOwner()}")
        
        try {
            // Intentar agregar la app a lock task packages si es device owner
            if (isDeviceOwner()) {
                try {
                    dpm.setLockTaskPackages(adminComponent, arrayOf(packageName))
                    Log.i(TAG, "Lock task packages configurados")
                } catch (e: Exception) {
                    Log.w(TAG, "No se pudieron configurar lock task packages: ${e.message}")
                }
            }
            
            val isPermitted = dpm.isLockTaskPermitted(packageName)
            Log.i(TAG, "isLockTaskPermitted: $isPermitted")
            
            if (isPermitted) {
                startLockTask()
                Log.i(TAG, "Kiosk mode enabled - EXITO")
            } else {
                Log.w(TAG, "Lock task NO permitido - intentando forzar...")
                // Intentar directamente por si acaso
                try {
                    startLockTask()
                    Log.i(TAG, "Kiosk mode enabled - forzado")
                } catch (e2: Exception) {
                    Log.e(TAG, "Error forzado: ${e2.message}")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error enabling kiosk mode: ${e.message}", e)
        }
    }

    private fun disableKioskMode() {
        try {
            stopLockTask()
            Log.i(TAG, "Kiosk mode disabled")
        } catch (e: Exception) {
            Log.e(TAG, "Error disabling kiosk mode", e)
        }
    }
}
