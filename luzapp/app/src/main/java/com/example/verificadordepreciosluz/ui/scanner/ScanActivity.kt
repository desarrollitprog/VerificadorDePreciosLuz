@file:Suppress("OPT_IN_ARGUMENT_IS_NOT_MARKER")

package com.example.verificadordepreciosluz.ui.scanner

import android.Manifest
import android.app.admin.DevicePolicyManager
import android.content.ComponentCallbacks2
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
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import android.provider.Settings
import android.media.MediaMetadataRetriever
import com.example.verificadordepreciosluz.MainActivity
import com.example.verificadordepreciosluz.BuildConfig
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.data.network.ApiService
import com.example.verificadordepreciosluz.data.network.PlaybackProgressRequest
import com.example.verificadordepreciosluz.data.network.PlaybackStatusRequest
import com.example.verificadordepreciosluz.data.network.ProductoResponse
import com.example.verificadordepreciosluz.data.local.BackupRepository
import com.example.verificadordepreciosluz.data.local.BackupResponse
import com.example.verificadordepreciosluz.data.local.BackupIndexRepository
import com.example.verificadordepreciosluz.data.local.BackupUtils
import com.example.verificadordepreciosluz.data.local.ScanCache
import com.example.verificadordepreciosluz.data.local.BannerRepository
import com.example.verificadordepreciosluz.data.local.BannerCacheItem
import com.example.verificadordepreciosluz.databinding.ActivityScanBinding
import com.example.verificadordepreciosluz.R
import com.example.verificadordepreciosluz.util.DeviceTypeHelper
import com.example.verificadordepreciosluz.util.PlayerManager
import com.example.verificadordepreciosluz.util.NetworkUtils
import com.example.verificadordepreciosluz.util.UpdateChecker
import com.example.verificadordepreciosluz.util.BackupWorker
import com.example.verificadordepreciosluz.util.UpdateWorker
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
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import android.app.ActivityManager

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
    private val maxRetryBeforeReport = 3
    private var lastMockSubmitAt = 0L
    private var pendingMockText: String? = null
    private var mockIdleRunnable: Runnable? = null
    private var scannerResetRunnable: Runnable? = null
    private var offlineMode = false
    private var isNetworkAvailable = false
    private var networkCallbackRegistered = false
    private var connectivityManager: ConnectivityManager? = null
    private var offlineBackup: BackupResponse? = null
    private var backupReadyNotified = false
    private val backupMaxAgeMs = (24 * 60 * 60 * 1000L)
    private val scanCache = ScanCache()
    private var cameraProvider: ProcessCameraProvider? = null
    private val bannerMaxAgeMs = (12 * 60 * 60 * 1000L)
    private val bannerPollIntervalMs = (60 * 1000L)  // 60 segundos - suficiente para detectar programaciones
    private val bannerPollHandler = Handler(Looper.getMainLooper())
    private var bannerPollRunnable: Runnable? = null
    private var backendBaseUrl: String? = null
    private val standbyIdleMs = 20_000L
    private var standbyItems: MutableList<BannerCacheItem> = mutableListOf()
    private var standbyIndex = 0
    private var forcePlayNow = false
    private var forcePlayNowTimer: Runnable? = null
    private val forcePlayNowTimeoutMs = 60000L // 60 segundos
    private var standbyActive = false
    private var standbyTimerRunnable: Runnable? = null
    private val kioskExitCode = "ADMIN-CODE-125"
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
    private var isPurging = false
    private var reproduccionIdActual: String? = null
    private var progresoRunnable: Runnable? = null
    private var ultimoBannerId: Int? = null
    private var ultimoTitulo: String? = null
    private var ultimoTipoReproduccion: String? = null
    private var ultimoCuartilReportado: Int = 0
    private lateinit var playerManager: PlayerManager
    private val PURGE_INTERVAL_MS = 30L * 24 * 60 * 60 * 1000  // 30 días
    private var purgeTimerRunnable: Runnable? = null
    private var deviceType: DeviceTypeHelper.DeviceType = DeviceTypeHelper.DeviceType.VERIFICADOR
    private var lastAutoResyncAt = 0L
    private val autoResyncCooldownMs = 5 * 60 * 1000L
    private val deviceId: String by lazy {
        Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
    }
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            handleNetworkChange(true)
        }

        override fun onLost(network: Network) {
            Log.w(TAG, "[Network] Conexión perdida")
            // Cerrar WebSocket inmediatamente para evitar zombies
            tabletWebSocket?.close(1001, "Network lost")
            tabletWebSocket = null
            handleNetworkChange(false)
            reconnectTabletWebSocket()
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
    
    // WebSocket reconnection - exponential backoff
    private var wsReconnectAttempts = 0
    private var wsLastReconnectTime = 0L
    private var wsReconnectDelay = 5000L
    private val maxReconnectDelay = 60_000L
    private var isReconnecting = false
    private val reconnectRunnable = Runnable {
        isReconnecting = false
        wsReconnectAttempts++
        startTabletWebSocket()
    }

    // Función para enviar logs de debug al backend
    private fun sendDebugLog(
        message: String,
        today: String? = null,
        cachedDate: String? = null,
        cachedUsd: Float? = null,
        cachedEur: Float? = null,
        apiUsd: Float? = null,
        apiEur: Float? = null,
        cacheActualizado: Boolean? = null
    ) {
        val baseUrl = backendBaseUrl?.trimEnd('/') ?: return
        val debugUrl = "$baseUrl/api/debug-bcv"
        
        try {
            val client = OkHttpClient()
            val params = mutableListOf<String>()
            params.add("log_message=${message}")
            params.add("device_id=$deviceId")
            today?.let { params.add("today=$it") }
            cachedDate?.let { params.add("cached_date=$it") }
            cachedUsd?.let { params.add("cached_usd=$it") }
            cachedEur?.let { params.add("cached_eur=$it") }
            apiUsd?.let { params.add("api_usd=$it") }
            apiEur?.let { params.add("api_eur=$it") }
            cacheActualizado?.let { params.add("cache_actualizado=$it") }
            
            val request = Request.Builder()
                .url("$debugUrl?${params.joinToString("&")}")
                .post(ByteArray(0).toRequestBody(null))
                .build()
            
            client.newCall(request).execute().close()
        } catch (e: Exception) {
            Log.w(TAG, "Error enviando debug log: ${e.message}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (isDownloading) {
                    Toast.makeText(this@ScanActivity, R.string.error_downloading, Toast.LENGTH_SHORT).show()
                    binding.etMockCode.requestFocus()
                    return
                }
                if (!backupReady) {
                    Toast.makeText(this@ScanActivity, R.string.error_backup_not_ready, Toast.LENGTH_SHORT).show()
                    binding.etMockCode.requestFocus()
                    return
                }
                isEnabled = false
                onBackPressedDispatcher.onBackPressed()
            }
        })

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        Thread.setDefaultUncaughtExceptionHandler { _, e ->
            Log.e(TAG, "UncaughtException: ${e.message}", e)
            val intent = packageManager.getLaunchIntentForPackage(packageName)
            intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            android.os.Process.killProcess(android.os.Process.myPid())
        }
        connectivityManager = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        cameraExecutor = Executors.newSingleThreadExecutor()
        tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)

        // Inicializar Device Policy Manager para modo kiosco
        dpm = getSystemService(DEVICE_POLICY_SERVICE) as DevicePolicyManager
        adminComponent = ComponentName(this, MyDeviceAdminReceiver::class.java)
        
        // Programar reinicio recurrente si está configurado
        programarReinicioRecurrente()
        
        // Programar verificación de actualizaciones diarias a las 7:00 AM
        UpdateWorker.schedule(this)
        
        // Programar descarga de backup diaria a las 8:30 AM Caracas
        BackupWorker.schedule(this)
        
        // Verificar actualización inmediatamente al abrir ScanActivity
        UpdateChecker.setUpdateMode(UpdateChecker.UpdateMode.AUTO)
        UpdateChecker.check(this)

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

        deviceType = DeviceTypeHelper.detectDeviceType(this)
        Log.d(TAG, "Tipo de dispositivo detectado: $deviceType")
        Log.d(TAG, "Build: MANUFACTURER=${Build.MANUFACTURER}, MODEL=${Build.MODEL}, PRODUCT=${Build.PRODUCT}, BOARD=${Build.BOARD}")
        if (deviceType == DeviceTypeHelper.DeviceType.TELEVISOR) {
            binding.tvTituloScanner.text = getString(R.string.title_tv_mode)
            Log.d(TAG, "FireTV detectado, título cambiado a 'AUTOMERCADOS LUZ'")
        }
        val esTV = deviceType == DeviceTypeHelper.DeviceType.TELEVISOR
        playerManager = PlayerManager(
            binding.standbyPlayer,
            enableRecoveryTimeout = esTV,
            persistentPlayer = esTV
        )
        Log.d(TAG, "PlayerManager inicializado con ExoPlayer")

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
            schedulePeriodicPurge()
        } else {
            Log.d(TAG, "BCV: onCreate - sin red, no se obtiene tasa BCV")
        }
        if (!hasNetwork) {
            schedulePeriodicPurge()
        }

        scheduleScannerReset()
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
            if (!Build.MANUFACTURER.equals("amazon", ignoreCase = true)) {
                showOutOfService()
                return
            }
            Log.i(TAG, "FireTV sin backup al iniciar - modo offline con publicidad cacheados")
        }
        // Iniciar carrusel de publicidad desde caché local (funciona sin red ni backup)
        uiHandler.postDelayed({
            startStandbyCarousel()
        }, 500)
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
                if (isKioskMode && text == kioskExitCode) {
                    Log.i(TAG, ">>> Código de salida detectado en TextWatcher! Desactivando modo kiosco...")
                    disableKioskMode()
                    isKioskMode = false
                    Toast.makeText(this@ScanActivity, R.string.msg_kiosk_disabled, Toast.LENGTH_SHORT).show()
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
        Log.d(TAG, "maybeProcessCode: code='$code', isKioskMode=$isKioskMode, kioskExitCode='$kioskExitCode', equals=${code == kioskExitCode}")
        
        if (isKioskMode && code == kioskExitCode) {
            Log.i(TAG, ">>> Código de salida detectado! Desactivando modo kiosco...")
            disableKioskMode()
            isKioskMode = false
            Toast.makeText(this, R.string.msg_kiosk_disabled, Toast.LENGTH_SHORT).show()
            // Limpiar el campo y no procesar más
            binding.etMockCode.text?.clear()
            return
        }
        
        val clean = sanitizeCode(code)
        if (clean == null) {
            // Código no válido (longitud incorrecta)
            Toast.makeText(this, R.string.error_invalid_code, Toast.LENGTH_SHORT).show()
            binding.etMockCode.requestFocus()
            return
        }
        
        // Debounce: evita spam si el mismo código se mantiene en cámara.
        val now = android.os.SystemClock.elapsedRealtime()
        if (now < pauseUntil) return
        val cooldown = 1500L // 1.5 s permite re-escaneos razonables
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
        // Limpiar diferido: esperar 250ms para que el HID termine de enviar
        // todos los caracteres del siguiente código antes de limpiar.
        // Previene pérdida del primer carácter por race condition entre
        // clear() y la llegada de teclas HID.
        uiHandler.postDelayed({
            binding.etMockCode.text?.clear()
            binding.etMockCode.requestFocus()
        }, 250)
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
        schedulePeriodicPurge()
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

    // Sincroniza banners en segundo plano - fuerza descarga inmediata cuando se recibe BANNER_INICIADO
    private fun syncBannersOnStart(newBannerId: Int? = null) {
        val service = api ?: return
        val baseUrl = backendBaseUrl ?: return
        scope.launch {
            try {
                val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                // Forzar descarga inmediata (maxAgeMs = 0) cuando se recibe BANNER_INICIADO
                repo.refreshIfStale(0L, deviceId)
                
                // Esperar 500 ms para que termine la descarga antes de priorizar
                delay(500L)
                
                // Recargar el caché local y priorizar el nuevo banner
                uiHandler.post {
                    // Recargar lista desde caché
                    val cache = repo.loadCache()
                    if (cache != null && cache.items.isNotEmpty()) {
                        standbyItems = cache.items.toMutableList()
                        
                        // Si hay un nuevo banner, moverlo al inicio del carrusel
                        if (newBannerId != null) {
                            Log.i(TAG, "[WebSocket] Priorizando banner $newBannerId para reproducción inmediata")
                            // Asegurar que el overlay esté visible
                            binding.standbyOverlay.visibility = View.VISIBLE
                            standbyActive = true
                            // Buscar el banner en standbyItems y moverlo al inicio
                            val index = standbyItems.indexOfFirst { it.id == newBannerId }
                            if (index > 0) {
                                val item = standbyItems.removeAt(index)
                                standbyItems.add(0, item)
                                standbyIndex = 0
                                // Forzar reproducción inmediata
                                playStandbyItem()
                                Log.i(TAG, "[WebSocket] Banner $newBannerId movido al índice 0 para reproducción")
                            } else if (index == 0) {
                                // Ya está al inicio, forzar reproducción
                                standbyIndex = 0
                                playStandbyItem()
                                Log.i(TAG, "[WebSocket] Banner $newBannerId ya en índice 0, reproduciendo")
                            }
                        } else if (!standbyActive) {
                            Log.i(TAG, "[WebSocket] Carrusel detenido, reactivando con ${standbyItems.size} banners")
                            standbyActive = true
                            standbyIndex = 0
                            binding.standbyOverlay.visibility = View.VISIBLE
                            playStandbyItem()
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error al sincronizar banners", e)
            }
        }
    }

    // Elimina el archivo local de un banner específico
    private fun deleteBannerFile(bannerId: Int, url: String) {
        try {
            val ext = url.substringAfterLast('.', "")
            val safeExt = ext.ifBlank { "bin" }
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
    private var lastBannerCheckMs: Long = 0L
    private val notifiedBannersStart = mutableSetOf<Int>()
    private val notifiedBannersEnd = mutableSetOf<Int>()
    // L1.4: Dedup de comandos por command_id (últimos 20 IDs)
    private val processedCommandIds = object : LinkedHashSet<String>() {
        override fun add(element: String): Boolean {
            if (size >= 20) remove(first())
            return super.add(element)
        }
    }
    
    private fun startBannerPolling() {
        val runnable = object : Runnable {
            override fun run() {
                if (isPurging) {
                    Log.d(TAG, "Banner polling: skipping during purge")
                    bannerPollHandler.postDelayed(this, bannerPollIntervalMs)
                    return
                }
                Log.d(TAG, "Banner polling: refreshing banners")
                val service = api
                val baseUrl = backendBaseUrl
                if (service != null && baseUrl != null) {
                    scope.launch {
                        try {
                            val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                            repo.refreshIfStale(bannerMaxAgeMs, deviceId)
                            
                            // Verificar si hay un banner que debe iniciar ahora (fallback cuando WebSocket no está conectado)
                            val now = System.currentTimeMillis()
                            if (lastBannerCheckMs > 0) {
                                val cache = repo.loadCache()
                                cache?.items?.forEach { bannerItem ->
                                    // Si el banner tiene fecha_inicio y debe iniciar entre el último check y ahora
                                    // Y NO fue ya notificado por WebSocket
                                    if (bannerItem.fechaInicioMs != null && bannerItem.fechaInicioMs > lastBannerCheckMs && bannerItem.fechaInicioMs <= now) {
                                        if (!notifiedBannersStart.contains(bannerItem.id)) {
                                            Log.i(TAG, "[Polling] Banner ${bannerItem.id} debe iniciar ahora, priorizando...")
                                            notifiedBannersStart.add(bannerItem.id)
                                            syncBannersOnStart(bannerItem.id)
                                        } else {
                                            Log.d(TAG, "[Polling] Banner ${bannerItem.id} ya notificado por WebSocket, saltando")
                                        }
                                    }
                                }
                            }
                            lastBannerCheckMs = now
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

    // PARTE 3: Limpia el caché si tiene más de 24 horas
    private fun limpiarCacheObsoleto() {
        val cachedDateStr = prefsDolar.getString("fecha", null)
        if (cachedDateStr != null) {
            try {
                val tz = java.util.TimeZone.getTimeZone("America/Caracas")
                val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.US).apply { timeZone = tz }
                val cachedDate = dateFormat.parse(cachedDateStr)
                val ahora = java.util.Date()
                
                if (cachedDate != null) {
                    val diffHoras = (ahora.time - cachedDate.time) / (1000 * 60 * 60)
                    if (diffHoras > 24) {
                        prefsDolar.edit().clear().apply()
                        Log.w(TAG, "BCV: Cache obsoleto limpiado (${diffHoras}h)")
                        sendDebugLog("Cache obsoleto limpiado (${diffHoras}h)", cachedDate = cachedDateStr)
                    }
                }
            } catch (_: Exception) {
                prefsDolar.edit().clear().apply()
                Log.w(TAG, "BCV: Cache corrupto limpiado")
            }
        }
    }

    // Obtiene y muestra las cotizaciones BCV (USD y EUR)
    private fun syncDolarBCV() {
        Log.i(TAG, "BCV: syncDolarBCV() llamado")
        
        // PARTE 3: Limpiar caché obsoleto (más de 24 horas)
        limpiarCacheObsoleto()
        
        // PARTE 1: Usar timezone explícito de Venezuela (America/Caracas)
        val tz = java.util.TimeZone.getTimeZone("America/Caracas")
        val today = SimpleDateFormat("yyyy-MM-dd", Locale.US).apply { 
            timeZone = tz 
        }.format(java.util.Date())
        val cachedDate = prefsDolar.getString("fecha", null)
        val cachedUsd = prefsDolar.getFloat("usd", 0f)
        val cachedEur = prefsDolar.getFloat("eur", 0f)
        Log.d(TAG, "BCV: today=$today (America/Caracas), cachedDate=$cachedDate, cachedUsd=$cachedUsd, cachedEur=$cachedEur")

        // PARTE 2: Primero mostrar caché si existe, luego siempre llamar a la API
        if (cachedDate == today && (cachedUsd > 0f || cachedEur > 0f)) {
            Log.d(TAG, "BCV: mostrando datos cacheados pero verificando con API...")
            uiHandler.post {
                mostrarTasaBCV(cachedUsd, cachedEur)
            }
            // No salir aquí, continuar para verificar con API
        }

        Log.d(TAG, "BCV: llamando a la API para obtener datos frescos...")
        sendDebugLog("syncDolarBCV llamado", today = today, cachedDate = cachedDate, cachedUsd = cachedUsd, cachedEur = cachedEur)
        dolarBcJob?.cancel()
        dolarBcJob = scope.launch {
            try {
                Log.d(TAG, "BCV: ejecutando getCotizaciones()")
                sendDebugLog("Ejecutando getCotizaciones()", today = today, cachedDate = cachedDate, cachedUsd = cachedUsd, cachedEur = cachedEur)
                val cotizaciones = dolarRepository.getCotizaciones()
                Log.d(TAG, "BCV: respuesta cruda: $cotizaciones")
                
                val usd = cotizaciones["USD"]
                val eur = cotizaciones["EUR"]
                Log.d(TAG, "BCV: USD=$usd, EUR=$eur")

                if (usd != null || eur != null) {
                    val usdVal = usd?.promedio ?: 0.0
                    val eurVal = eur?.promedio ?: 0.0
                    val usdFloat = usdVal.toFloat()
                    val eurFloat = eurVal.toFloat()
                    
                    // Comparar con cache - solo actualizar si son diferentes
                    val cacheIgual = (usdFloat == cachedUsd && eurFloat == cachedEur)
                    val cacheActualizado: Boolean
                    
                    if (cacheIgual) {
                        Log.d(TAG, "BCV: API devuelve mismos valores que cache, no actualizando")
                        cacheActualizado = false
                    } else {
                        Log.d(TAG, "BCV: Valores diferentes - Actualizando cache y UI")
                        prefsDolar.edit()
                            .putString("fecha", today)
                            .putFloat("usd", usdFloat)
                            .putFloat("eur", eurFloat)
                            .apply()
                        cacheActualizado = true
                    }
                    
                    sendDebugLog(
                        "API responded - comparing with cache",
                        today = today,
                        cachedDate = cachedDate,
                        cachedUsd = cachedUsd,
                        cachedEur = cachedEur,
                        apiUsd = usdFloat,
                        apiEur = eurFloat,
                        cacheActualizado = cacheActualizado
                    )
                    
                    uiHandler.post {
                        mostrarTasaBCV(usdFloat, eurFloat)
                    }
                    Log.d(TAG, "BCV: cotizaciones mostradas (cache actualizado: $cacheActualizado)")
                } else {
                    Log.w(TAG, "BCV: API devolvio vacio")
                    sendDebugLog("API devolvio vacio", today = today, cachedDate = cachedDate, cachedUsd = cachedUsd, cachedEur = cachedEur)
                    uiHandler.post {
                        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.text = getString(R.string.sin_actualizacion_bcv)
                        findViewById<android.widget.TextView>(R.id.cardDolarBc)?.visibility = View.VISIBLE
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "BCV: Error fetching BCV rate", e)
                uiHandler.post {
                    findViewById<android.widget.TextView>(R.id.cardDolarBc)?.text = getString(R.string.sin_actualizacion_bcv)
                    findViewById<android.widget.TextView>(R.id.cardDolarBc)?.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun mostrarTasaBCV(usd: Float, eur: Float) {
        val symbols = DecimalFormatSymbols(Locale.Builder().setLanguage("es").setRegion("VE").build()).apply {
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

    // Programa limpieza periódica del caché de banners cada 30 días
    private fun schedulePeriodicPurge() {
        val prefs = getSharedPreferences("PurgePrefs", MODE_PRIVATE)
        val lastPurgeAt = prefs.getLong("lastPurgeAt", 0L)
        val delay: Long
        if (lastPurgeAt == 0L) {
            delay = PURGE_INTERVAL_MS  // Primera vez: programar para 30 días
        } else {
            val nextPurgeAt = lastPurgeAt + PURGE_INTERVAL_MS
            delay = maxOf(0L, nextPurgeAt - System.currentTimeMillis())
        }
        purgeTimerRunnable?.let { uiHandler.removeCallbacks(it) }
        purgeTimerRunnable = Runnable {
            if (!isFinishing && !isPurging && api != null && backendBaseUrl != null) {
                isPurging = true
                Log.i(TAG, "[Purge] Iniciando purge periódico programado")
                uiHandler.post {
                    stopStandbyCarousel()
                    binding.standbyOverlay.visibility = View.GONE
                }
                scope.launch {
                    try {
                        ejecutarPurgaTotal(this@ScanActivity, api!!, backendBaseUrl!!, deviceId) {
                            getSharedPreferences("PurgePrefs", MODE_PRIVATE).edit()
                                .putLong("lastPurgeAt", System.currentTimeMillis()).apply()
                            uiHandler.post {
                                Log.i(TAG, "[Purge] Purge periódico completado exitosamente")
                                startStandbyCarousel()
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "[Purge] Error en purge periódico", e)
                    } finally {
                        isPurging = false
                        uiHandler.post { schedulePeriodicPurge() }
                    }
                }
            } else {
                schedulePeriodicPurge()
            }
        }
        if (delay > 0) {
            Log.i(TAG, "[Purge] Próxima limpieza programada en ${delay / (24 * 60 * 60 * 1000)} días")
        }
        uiHandler.postDelayed(purgeTimerRunnable!!, delay)
    }

    // Programa reset periódico del escáner HID cada 30s para prevenir
    // corrupción del InputConnection en Android 7 (rk3128_box)
    private fun scheduleScannerReset() {
        scannerResetRunnable?.let { uiHandler.removeCallbacks(it) }
        scannerResetRunnable = Runnable {
            runOnUiThread {
                lastCode = null
                lastScanAt = 0L
                pauseUntil = 0L
                pendingMockText = null
                binding.etMockCode.text?.clear()
                binding.etMockCode.requestFocus()
                if (analyzerPaused) {
                    pauseAnalyzer(false)
                }
                Log.d(TAG, "[ScannerReset] Reset periódico ejecutado")
            }
            uiHandler.postDelayed(scannerResetRunnable!!, 30_000L)
        }
        uiHandler.postDelayed(scannerResetRunnable!!, 30_000L)
    }

    // Intenta auto-resincronizar banners cuando el queue se vacía en Fire TV
    private fun maybeAutoResync() {
        if (deviceType != DeviceTypeHelper.DeviceType.TELEVISOR) return
        if (isPurging) return
        if (!isNetworkAvailable) return
        if (api == null || backendBaseUrl == null) return
        val now = System.currentTimeMillis()
        if (now - lastAutoResyncAt < autoResyncCooldownMs) return
        lastAutoResyncAt = now
        isPurging = true
        Log.i(TAG, "[AutoResync] Iniciando auto-resync por queue vacío en Fire TV")
        stopStandbyCarousel("auto_resync")
        scope.launch {
            try {
                ejecutarPurgaTotal(this@ScanActivity, api!!, backendBaseUrl!!, deviceId) {
                    uiHandler.post {
                        Log.i(TAG, "[AutoResync] Completado exitosamente")
                        startStandbyCarousel()
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "[AutoResync] Error", e)
            } finally {
                isPurging = false
            }
        }
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
            maybeAutoResync()
            return
        }

        Log.i(TAG, "Standby: cache cargado items=${cache.items.size}")

        standbyItems = cache.items.toMutableList() // <-- Siempre mutable
        standbyIndex = 0
        standbyActive = true
        binding.standbyOverlay.visibility = View.VISIBLE
        
        playerManager.release()
        playStandbyItem()
    }

    // Reproduce un item del carrusel (imagen o video)
    private fun playStandbyItem() {
        Log.d(TAG, "playStandbyItem: INICIO standbyActive=$standbyActive itemsSize=${standbyItems.size}")
        if (!standbyActive || standbyItems.isEmpty()) {
            Log.w(TAG, "playStandbyItem: SALIENDO - standbyActive=$standbyActive o items vacio")
            return
        }
        // Proteger el índice
        if (standbyIndex >= standbyItems.size) standbyIndex = 0
        val item = standbyItems[standbyIndex]
        Log.d(TAG, "playStandbyItem: item=${item.id} tipo=${item.tipo} fechaInicioMs=${item.fechaInicioMs} localPath=${item.localPath}")

        // Guard anti-duplicado: evitar doble inicio del mismo banner
        if (reproduccionIdActual != null && ultimoBannerId == item.id) {
            Log.w(TAG, "playStandbyItem: llamada duplicada para banner ${item.id}, ignorando")
            return
        }
        
        // FASE 7.3: Validar vigencia - skip banners no vigentes
        val now = System.currentTimeMillis()
        Log.d(TAG, "playStandbyItem: validando fecha_inicio forcePlayNow=$forcePlayNow now=$now")
        
        // Validar fecha_inicio (no reproducir antes de tiempo)
        // SOLO para polling. Cuando llega por WebSocket (BANNER_INICIADO), se reproduce inmediatamente
        if (item.fechaInicioMs != null && now < item.fechaInicioMs && !forcePlayNow) {
            Log.d(TAG, "Standby: banner ${item.id} aún no inicia (now=$now, fechaInicioMs=${item.fechaInicioMs}), esperando...")
            uiHandler.postDelayed({
                Log.d(TAG, "Standby: retry ejecutándose, standbyActive=$standbyActive")
                if (standbyActive && standbyItems.isNotEmpty()) {
                    playStandbyItem()
                }
            }, 5000)
            return
        }

        // Validar fecha_fin (skip si ya vencido)
        if (item.fechaFinMs != null && now > item.fechaFinMs) {
            Log.w(TAG, "Standby: banner ${item.id} vencido (fechaFinMs=${item.fechaFinMs}), eliminando...")
            val file = File(item.localPath)
            if (file.exists()) file.delete()
            standbyItems.removeAt(standbyIndex)
            if (standbyItems.isEmpty()) {
                Log.i(TAG, "Standby: todos los banners han vencido. Deteniendo carrusel.")
                stopStandbyCarousel()
                maybeAutoResync()
                return
            }
            if (standbyIndex >= standbyItems.size) standbyIndex = 0
            playStandbyItem()
            return
        }
        
        val itemFile = File(item.localPath)
        val fileExists = itemFile.exists() && itemFile.length() > 512L
        if (itemFile.exists() && !fileExists) {
            Log.w(TAG, "Standby: archivo corrupto (${itemFile.length()} bytes), eliminando: ${item.localPath}")
            itemFile.delete()
        }
        Log.d(TAG, "playStandbyItem: archivo existe=$fileExists path=${item.localPath}")
        if (!fileExists) {
            // Contador de reintentos para evitar spam de notificaciones
            val currentRetry = retryCountMap.getOrDefault(item.localPath, 0)
            val newRetry = currentRetry + 1
            retryCountMap[item.localPath] = newRetry
            
            if (newRetry >= maxRetryBeforeReport) {
                // Solo reportar si falló maxRetryBeforeReport veces consecutivas
                Log.w(TAG, "Standby: archivo no existe tras $newRetry intentos, eliminando de la lista: ${item.localPath}")
                reportPlaybackFailure(
                    localPath = item.localPath,
                    reason = "Archivo no encontrado tras $newRetry intentos"
                )
                retryCountMap.remove(item.localPath)
            } else {
                Log.w(TAG, "Standby: archivo no existe (intento $newRetry/$maxRetryBeforeReport), reintentando: ${item.localPath}")
            }
            
            if (standbyItems.isNotEmpty()) {
                standbyItems.removeAt(standbyIndex)
            }
            if (standbyItems.isEmpty()) {
                Log.e(TAG, "Standby: todos los archivos han sido eliminados. Deteniendo carrusel.")
                stopStandbyCarousel()
                maybeAutoResync()
                return
            }
            if (standbyIndex >= standbyItems.size) standbyIndex = 0
            playStandbyItem()
            return
        }
        
        // Si el archivo existe, resetear el contador de reintentos
        retryCountMap.remove(item.localPath)
        Log.i(TAG, "Standby: item idx=$standbyIndex tipo=${item.tipo} path=${item.localPath} exists=true")
        standbySlideRunnable?.let { uiHandler.removeCallbacks(it) }
        binding.standbyImage.visibility = View.GONE
        binding.standbyPlayer.visibility = View.GONE
        releaseStandbyBitmap()
        
        // Finalizar reproducción anterior si existe
        if (reproduccionIdActual != null && ultimoBannerId != null) {
            val tipoAnterior = ultimoTipoReproduccion ?: "image"
            if (tipoAnterior == "image") {
                sendPlaybackEvent(
                    bannerId = ultimoBannerId!!,
                    titulo = ultimoTitulo,
                    tipoEvento = "COMPLETED",
                    completo = true,
                    cuartil50 = true,
                    cuartil75 = true,
                    cuartil100 = true,
                    motivoFin = "completion"
                )
            } else {
                sendPlaybackEvent(
                    bannerId = ultimoBannerId!!,
                    titulo = ultimoTitulo,
                    tipoEvento = "INTERRUPTED",
                    completo = false,
                    motivoFin = "skip"
                )
            }
            reproduccionIdActual = null
        }

        // Generar ID único para esta reproducción
        val fallbackDur = item.duracionSeg?.toDouble() ?: 10.0
        val durSeg = if (item.tipo == "video") {
            getVideoDurationSeconds(item.localPath) ?: fallbackDur
        } else {
            fallbackDur
        }
        reproduccionIdActual = "${deviceId}_${item.id}_${System.currentTimeMillis()}"
        ultimoBannerId = item.id
        ultimoTitulo = item.titulo
        ultimoTipoReproduccion = item.tipo
        ultimoCuartilReportado = 0
        
        // Reportar inicio de reproducción
        sendPlaybackEvent(
            bannerId = item.id,
            titulo = item.titulo,
            tipoEvento = "START",
            duracionTotalSeg = durSeg
        )
        
        // Notificar al servidor qué contenido se está reproduciendo
        notifyPlayingNow(item)
        
        if (item.tipo == "video") {
            binding.standbyPlayer.visibility = View.VISIBLE
            playVideo(item, durSeg)
        } else {
            binding.standbyImage.visibility = View.VISIBLE
            val reqWidth = if (binding.standbyImage.width > 0) binding.standbyImage.width else resources.displayMetrics.widthPixels
            val reqHeight = if (binding.standbyImage.height > 0) binding.standbyImage.height else resources.displayMetrics.heightPixels
            
            val imageFile = java.io.File(item.localPath)
            if (!imageFile.exists()) {
                Log.w(TAG, "Standby: el archivo de imagen desapareció justo antes de decodificar: ${item.localPath}")
                nextStandbyItem()
                return
            }
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

    private fun playVideo(item: BannerCacheItem, durSeg: Double) {
        val videoUri = android.net.Uri.fromFile(File(item.localPath))

        val onVideoCompletion = {
            sendPlaybackEvent(
                bannerId = item.id,
                titulo = item.titulo,
                tipoEvento = "COMPLETED",
                duracionTotalSeg = durSeg,
                segundosReproducidos = durSeg,
                porcentajeCompletado = 100.0,
                cuartil50 = true,
                cuartil75 = true,
                cuartil100 = true,
                completo = true,
                motivoFin = "completion"
            )
            stopVideoProgressTracker()
            reproduccionIdActual = null
            ultimoTipoReproduccion = null
            playerManager.release()
            nextStandbyItem()
        }

        val onVideoError: (Int, Int) -> Boolean = { what, extra ->
            Log.w(TAG, "Standby: error video what=$what extra=$extra para ${item.localPath}")
            playerManager.release()
            val currentRetry = retryCountMap.getOrDefault(item.localPath, 0)
            val newRetry = currentRetry + 1
            retryCountMap[item.localPath] = newRetry
            if (newRetry >= maxRetryBeforeReport) {
                reportPlaybackFailure(
                    localPath = item.localPath,
                    reason = "ExoPlayer error what=$what extra=$extra tras $newRetry intentos"
                )
                retryCountMap.remove(item.localPath)
            } else {
                Log.w(TAG, "Standby: error video (intento $newRetry/$maxRetryBeforeReport), reintentando...")
            }
            if (standbyItems.size == 1) {
                stopStandbyCarousel()
                maybeAutoResync()
            } else {
                if (standbyItems.isNotEmpty()) {
                    standbyItems.removeAt(standbyIndex)
                }
                if (standbyItems.isEmpty()) {
                    stopStandbyCarousel()
                    maybeAutoResync()
                } else {
                    if (standbyIndex >= standbyItems.size) standbyIndex = 0
                    uiHandler.postDelayed({ playStandbyItem() }, 150)
                }
            }
            true
        }

        playerManager.onCompletion = onVideoCompletion
        playerManager.onError = onVideoError
        playerManager.play(videoUri)
        startVideoProgressTracker(item.id, durSeg)
    }

    // Avanza al siguiente elemento del carrusel
    private fun nextStandbyItem() {
        if (!standbyActive || standbyItems.isEmpty()) return
        standbyIndex = (standbyIndex + 1) % standbyItems.size
        playStandbyItem()
    }

    // Detiene el carrusel y limpia el overlay
    private fun stopStandbyCarousel(motivo: String = "scan") {
        if (!standbyActive) return
        val lastBanner = ultimoBannerId
        stopVideoProgressTracker()
        if (lastBanner != null && reproduccionIdActual != null) {
            val tipoAnterior = ultimoTipoReproduccion ?: "image"
            try {
                if (tipoAnterior == "image") {
                    sendPlaybackEvent(
                        bannerId = lastBanner,
                        titulo = ultimoTitulo,
                        tipoEvento = "COMPLETED",
                        completo = true,
                        cuartil50 = true,
                        cuartil75 = true,
                        cuartil100 = true,
                        motivoFin = motivo
                    )
                } else {
                    val currentPos = playerManager.currentPosition().toDouble()
                    val duration = playerManager.duration().toDouble()
                    val pct = if (duration > 0) (currentPos / duration) * 100.0 else 0.0
                    sendPlaybackEvent(
                        bannerId = lastBanner,
                        titulo = ultimoTitulo,
                        tipoEvento = "INTERRUPTED",
                        segundosReproducidos = currentPos / 1000.0,
                        porcentajeCompletado = pct,
                        cuartil50 = pct >= 50,
                        cuartil75 = pct >= 75,
                        cuartil100 = false,
                        completo = false,
                        motivoFin = motivo
                    )
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error enviando ${if (tipoAnterior == "image") "COMPLETED" else "INTERRUPTED"}: ${e.message}")
            }
        }
        reproduccionIdActual = null
        ultimoTipoReproduccion = null
        standbyActive = false
        standbySlideRunnable?.let { uiHandler.removeCallbacks(it) }
        playerManager.release()
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
            val halfHeight = srcHeight / 2
            val halfWidth = srcWidth / 2
            while ((halfHeight / inSampleSize) >= reqHeight && (halfWidth / inSampleSize) >= reqWidth) {
                inSampleSize *= 2
            }
        }
        return inSampleSize.coerceAtLeast(1)
    }

    // 2.1 Re-sincronizar respaldo local cuando vuelve la conexión
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
                Toast.makeText(this, R.string.msg_backup_ready, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun shouldDownloadBackup(): Boolean {
        if (Build.MANUFACTURER.equals("amazon", ignoreCase = true)) {
            Log.d(TAG, "FireTV detectado, saltando descarga de backup")
            return false
        }
        val repo = BackupRepository(this)
        val updatedAt = repo.getUpdatedAt() ?: return true
        val updatedAtMillis = parseIsoToMillis(updatedAt) ?: return true
        return System.currentTimeMillis() - updatedAtMillis > backupMaxAgeMs
    }

    // 2.2 Actualizar texto de última sincronización del backup
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

    // 2.4 Validar antigüedad del respaldo local (máx. 12 h)
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

        // P8: Caché LRU local — respuesta inmediata sin red ni backup
        val cached = scanCache.get(code)
        if (cached != null) {
            feedbackSuccess()
            showResult(cached)
            pauseUntil = android.os.SystemClock.elapsedRealtime() + 4000
            return
        }

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
                scanCache.put(code, producto) // P8: guardar en caché LRU
                uiHandler.post {
                    feedbackSuccess()
                    showResult(producto)
                    // Pausa el escáner 3 s tras un éxito para evitar lecturas inmediatas repetidas
                    pauseUntil = android.os.SystemClock.elapsedRealtime() + 4000
                }
            } catch (e: Exception) {
                var setOffline = false
                val (key, msg) = when (e) {
                    is HttpException -> when (e.code()) {
                        404 -> "404" to getString(R.string.error_product_not_found)
                        in 500..599 -> "5xx" to getString(R.string.error_server, e.code())
                        else -> "4xx" to getString(R.string.error_http, e.code())
                    }
                    is SocketTimeoutException -> {
                        setOffline = true
                        "timeout" to getString(R.string.error_timeout)
                    }
                    is IOException -> {
                        setOffline = true
                        "network" to getString(R.string.error_network)
                    }
                    else -> "unknown" to getString(R.string.error_unexpected)
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
                // Reprocesar texto acumulado en el campo mock mientras había requestInFlight=true
                uiHandler.post { processPendingMockText() }
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
                    Log.w(TAG, "[OFFLINE] showOutOfService: backup stale (más de 24h)")
                    uiHandler.post { showOutOfService() }
                    return@launch
                }
                offlineBackup = backup
                val indexRepo = BackupIndexRepository(this@ScanActivity)
                val producto = indexRepo.lookupProductoOffline(code)
                    ?: BackupRepository(this@ScanActivity).lookupProductoOffline(code)
                if (producto == null) {
                    uiHandler.post { showThrottledError("offline_not_found", getString(R.string.error_product_not_found)) }
                    return@launch
                }
                scanCache.put(code, producto) // P8: guardar en caché LRU
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
                uiHandler.post { processPendingMockText() }
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
            goToConfig(getString(R.string.error_config_required))
            return false
        }

        val portToUse = port ?: defaultPort
        if (!NetworkUtils.validatePort(portToUse)) {
            goToConfig(getString(R.string.error_invalid_port))
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

    private fun getVideoDurationSeconds(localPath: String): Double? {
        return try {
            val retriever = MediaMetadataRetriever()
            retriever.setDataSource(localPath)
            val durMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            retriever.release()
            durMs?.toDoubleOrNull()?.let { it / 1000.0 }
        } catch (e: Exception) {
            Log.w(TAG, "Error obteniendo duración real del video: ${e.message}")
            null
        }
    }

    private fun sendPlaybackEvent(
        bannerId: Int,
        titulo: String? = null,
        tipoEvento: String,
        duracionTotalSeg: Double? = null,
        segundosReproducidos: Double? = null,
        porcentajeCompletado: Double? = null,
        cuartil50: Boolean? = null,
        cuartil75: Boolean? = null,
        cuartil100: Boolean? = null,
        completo: Boolean? = null,
        motivoFin: String? = null
    ) {
        val service = api ?: return
        val rid = reproduccionIdActual ?: return
        scope.launch {
            try {
                service.reportarProgresoReproduccion(
                    PlaybackProgressRequest(
                        reproduccionId = rid,
                        dispositivoId = deviceId,
                        bannerId = bannerId,
                        titulo = titulo,
                        tipoEvento = tipoEvento,
                        duracionTotalSeg = duracionTotalSeg,
                        segundosReproducidos = segundosReproducidos,
                        porcentajeCompletado = porcentajeCompletado,
                        cuartil50 = cuartil50,
                        cuartil75 = cuartil75,
                        cuartil100 = cuartil100,
                        completo = completo,
                        motivoFin = motivoFin
                    )
                )
                Log.d(TAG, "Playback event $tipoEvento enviado para banner $bannerId")
            } catch (e: Exception) {
                Log.w(TAG, "Error enviando playback event $tipoEvento: ${e.message}")
            }
        }
    }

    private fun startVideoProgressTracker(bannerId: Int, duracionTotalSeg: Double) {
        stopVideoProgressTracker()
        ultimoCuartilReportado = 0
        ultimoBannerId = bannerId
        progresoRunnable = Runnable {
            try {
                val currentPos = playerManager.currentPosition().toDouble()
                val duration = playerManager.duration().toDouble()
                if (duration <= 0) return@Runnable

                val pct = (currentPos / duration) * 100.0
                val cuartil = when {
                    pct >= 100 -> 100
                    pct >= 75 -> 75
                    pct >= 50 -> 50
                    else -> 25
                }

                if (cuartil > ultimoCuartilReportado) {
                    ultimoCuartilReportado = cuartil
                    sendPlaybackEvent(
                        bannerId = bannerId,
                        titulo = ultimoTitulo,
                        tipoEvento = "PROGRESS",
                        duracionTotalSeg = duracionTotalSeg,
                        segundosReproducidos = currentPos / 1000.0,
                        porcentajeCompletado = pct,
                        cuartil50 = cuartil >= 50,
                        cuartil75 = cuartil >= 75,
                        cuartil100 = cuartil >= 100
                    )
                }

                if (standbyActive) {
                    uiHandler.postDelayed(progresoRunnable!!, 1000)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error en videoProgressTracker: ${e.message}")
            }
        }
        uiHandler.postDelayed(progresoRunnable!!, 1000)
    }

    private fun stopVideoProgressTracker() {
        progresoRunnable?.let { uiHandler.removeCallbacks(it) }
        progresoRunnable = null
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
                    if (backup != null && !isBackupStale(backup)) {
                        offlineBackup = backup
                        setOfflineMode(true)
                        uiHandler.post { updateOfflineTimestamp(offlineBackup) }
                        // Reintenta ping cada 60 segundos en modo offline
                        delay(60000)
                        offlineRetry = true
                        continue
                    }
                    // Sin backup válido
                    if (Build.MANUFACTURER.equals("amazon", ignoreCase = true)) {
                        // FireTV: no necesita backup, continúa en offline con banners cacheados
                        Log.i(TAG, "FireTV sin conexión y sin backup - modo offline con publicidad cacheados")
                        setOfflineMode(true)
                        delay(60000)
                        offlineRetry = true
                        continue
                    }
                    goToConfig(reason ?: getString(R.string.error_connection_lost))
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
                    getString(R.string.error_ping_failed, e.code())
                } else {
                    getString(R.string.error_server, e.code())
                }
                if (e.code() in 400..499) break
            } catch (_: SocketTimeoutException) {
                lastReason = getString(R.string.error_timeout)
            } catch (_: IOException) {
                lastReason = getString(R.string.error_ping_no_connection)
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
        val symbols = DecimalFormatSymbols(Locale.Builder().setLanguage("es").setRegion("VE").build()).apply {
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
            val symbols = DecimalFormatSymbols(Locale.Builder().setLanguage("es").setRegion("VE").build()).apply {
                groupingSeparator = '.'
                decimalSeparator = ','
            }
            val formatter = DecimalFormat("#,##0.##", symbols)
            val precioBsFormateado = formatter.format(precioBs)
            binding.tvPrecioBsOferta.text = getString(R.string.precio_bs_formato, precioBsFormateado)
            
            // Reducir tamaño si el texto supera 25 caracteres (usando tamaños del XML)
            val tamanoNombreOferta = resources.getDimension(R.dimen.text_size_nombre_oferta) / resources.displayMetrics.density
            val tamanoNombreReducido = tamanoNombreOferta * 0.8f
            if (producto.nombre.length > 25) {
                binding.tvNombreOferta.textSize = tamanoNombreReducido
            }
            
            val tamanoPrecioOferta = resources.getDimension(R.dimen.text_size_precio_oferta) / resources.displayMetrics.density
            val tamanoPrecioOfertaReducido = tamanoPrecioOferta * 0.8f
            val precioOfertaText = String.format(Locale.US, "$%.2f", producto.pvpOferta)
            if (precioOfertaText.length > 25) {
                binding.tvPrecioOferta.textSize = tamanoPrecioOfertaReducido
            }
            
            val tamanoPrecioBsOferta = resources.getDimension(R.dimen.text_size_precio_bs_oferta) / resources.displayMetrics.density
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
            // Pequeño delay para que el layout termine antes de pedir foco
            binding.etMockCode.post {
                binding.etMockCode.requestFocus()
            }
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

    // Reprocesar texto acumulado en etMockCode mientras había requestInFlight=true
    private fun processPendingMockText() {
        if (requestInFlight) return
        val text = binding.etMockCode.text?.toString().orEmpty()
        if (text.isNotEmpty()) {
            maybeProcessCode(text)
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
        playerManager.dispose()
        super.onDestroy()
        stopBannerPolling()
        cameraProvider?.unbindAll()
        cameraExecutor.shutdown()
        tone?.release()
        tone = null
        job.cancel()
        scope.cancel()
        dolarBcJob?.cancel()
        // Cleanup de reconnect handler para evitar memory leak
        uiHandler.removeCallbacks(reconnectRunnable)
        purgeTimerRunnable?.let { uiHandler.removeCallbacks(it) }
        scannerResetRunnable?.let { uiHandler.removeCallbacks(it) }
        tabletWebSocket?.close(1000, "Activity destroyed")
        tabletWebSocket = null
        wsClient?.dispatcher?.executorService?.shutdown()
        wsClient = null
        
    }

    override fun onPause() {
        super.onPause()
        playerManager.pause()
        cameraProvider?.unbindAll()
        scannerResetRunnable?.let { uiHandler.removeCallbacks(it) }
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
            }, 500) // 500 ms de delay
        }
        
        playerManager.resume()
        resumeCameraIfAvailable()  // Solo reiniciar cámara si está disponible
        binding.etMockCode.requestFocus()
        scheduleScannerReset()
    }

    override fun onUserInteraction() {
        super.onUserInteraction()
    }

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) {
            Log.w(TAG, "onTrimMemory: nivel $level, liberando recursos")
            releaseStandbyBitmap()
            System.gc()
        }
    }

    private fun toggleMockPanel() {
        // En lugar de cambiar alpha del panel, cambiamos visibilidad del rectángulo ocultador
        val isRectanguloVisible = binding.rectanguloOcultador.visibility == View.VISIBLE
        
        if (isRectanguloVisible) {
            // Mostrar toggle: ocultar rectángulo
            binding.rectanguloOcultador.visibility = View.GONE
            binding.etMockCode.requestFocus()
            Log.d(TAG, "Toggle: Mostrando panel (rectángulo oculto)")
        } else {
            // Ocultar toggle: mostrar rectángulo
            binding.rectanguloOcultador.visibility = View.VISIBLE
            binding.etMockCode.requestFocus()
            Log.d(TAG, "Toggle: Ocultando panel (rectángulo visible)")
        }
    }

    // Ocultar progressBar al terminar la descarga
    private fun hideProgress() {
        runOnUiThread {
            findViewById<android.widget.FrameLayout>(R.id.progressContainer).visibility = View.GONE
        }
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
            wsClient = OkHttpClient.Builder()
                .connectTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                .readTimeout(0, java.util.concurrent.TimeUnit.SECONDS)
                .writeTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
                .pingInterval(60, java.util.concurrent.TimeUnit.SECONDS)
                .retryOnConnectionFailure(false)
                .build()
            val request = Request.Builder().url(wsUrl).build()
            val wsListener = object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                    Log.i(TAG, "[WebSocket] Conexión abierta: $wsUrl")
                    // Reset exponential backoff al conectar exitosamente
                    wsReconnectAttempts = 0
                    wsReconnectDelay = 5000L
                    isReconnecting = false
                    try {
                        val identifyMsg = org.json.JSONObject()
                        identifyMsg.put("type", "IDENTIFY")
                        identifyMsg.put("device_id", deviceId)
                        identifyMsg.put("device_type", DeviceTypeHelper.detectDeviceType(this@ScanActivity).name.lowercase(Locale.ROOT))
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
                        
                        // L1.4: Dedup por command_id - ignorar comandos ya procesados
                        val commandId = message.optString("command_id", "")
                        if (commandId.isNotEmpty() && !processedCommandIds.add(commandId)) {
                            Log.w(TAG, "[WebSocket] Comando duplicado ignorado: command=$command command_id=$commandId")
                            return
                        }
                        
                        try {
                            sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                            Log.i(TAG, "[WebSocket] Confirmación enviada para comando: $command")
                        } catch (e: Exception) {
                            Log.e(TAG, "[WebSocket] Error enviando confirmación", e)
                        }
                        when (command) {
                            "WIPE_AND_RESYNC" -> {
                                Log.i(
                                    TAG,
                                    "[WebSocket] Comando WIPE_AND_RESYNC recibido. Pausando carrusel antes de purga..."
                                )

                                // 1. PAUSAR el carrusel INMEDIATAMENTE antes de borrar archivos
                                uiHandler.post {
                                    stopStandbyCarousel()
                                    binding.standbyOverlay.visibility = View.GONE
                                    Log.d(TAG, "[WebSocket] Carrusel detenido y overlay ocultado")
                                }

                                isPurging = true
                                scope.launch {
                                    val apiService = api
                                    if (apiService == null) {
                                        isPurging = false
                                        sendSyncConfirmation(webSocket, command, "FAILED", "ApiService no inicializado", commandId = commandId)
                                        return@launch
                                    }

                                    // 2. Ejecutar purga SIN callback de inicio de carrusel
                                    val purgeResult = ejecutarPurgaTotal(this@ScanActivity, apiService, baseUrl, deviceId) {
                                        // Callback vacío - controlamos el inicio manualmente
                                    }

                                    // 3. Solo iniciar carrusel DESPUÉS de que la purga termine exitosamente
                                    uiHandler.post {
                                        isPurging = false
                                        if (purgeResult.success) {
                                            Log.i(TAG, "[WebSocket] Purga exitosa, iniciando carrusel...")
                                            startStandbyCarousel()
                                        } else {
                                            Log.w(TAG, "[WebSocket] Purga fallida, no se inicia carrusel")
                                            sendSyncConfirmation(
                                                webSocket,
                                                command,
                                                "FAILED",
                                                purgeResult.reason ?: "Purga fallida",
                                                commandId
                                            )
                                        }
                                    }

                                    if (purgeResult.success) {
                                        sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                    } else {
                                        sendSyncConfirmation(
                                            webSocket,
                                            command,
                                            "FAILED",
                                            purgeResult.reason ?: "Purga fallida",
                                            commandId
                                        )
                                    }
                                }
                            }
                            "BANNER_INICIADO" -> {
                                val bannerId = message.optInt("banner_id", 0)
                                val titulo = message.optString("titulo", "")
                                Log.i(TAG, "[WebSocket] BANNER_INICIADO recibido: id=$bannerId, titulo=$titulo")

                                // Marcar como notificado para evitar duplicados con polling
                                notifiedBannersStart.add(bannerId)

                                //Cancelar timer anterior si existe
                                forcePlayNowTimer?.let { uiHandler.removeCallbacks(it) }

                                //Programar Expiracion
                                forcePlayNowTimer = Runnable {forcePlayNow = false}
                                uiHandler.postDelayed(forcePlayNowTimer!!, forcePlayNowTimeoutMs)

                                // Forzar reproducción inmediata (ignorar validación de fecha_inicio)
                                forcePlayNow = true

                                // Recargar banners inmediatamente y priorizar el nuevo banner
                                syncBannersOnStart(bannerId)
                                uiHandler.post {
                                    Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_INICIADO")
                                    // Confirmar al backend que el banner fue recibido
                                    sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                }
                            }
                            "BANNER_LIST" -> {
                                val bannersArray = message.optJSONArray("banners")
                                val count = bannersArray?.length() ?: 0
                                Log.i(TAG, "[WebSocket] BANNER_LIST recibido: $count banners")

                                if (bannersArray != null) {
                                    for (i in 0 until bannersArray.length()) {
                                        val b = bannersArray.getJSONObject(i)
                                        notifiedBannersStart.add(b.optInt("banner_id", 0))
                                    }
                                }

                                forcePlayNowTimer?.let { uiHandler.removeCallbacks(it) }
                                forcePlayNowTimer = Runnable { forcePlayNow = false }
                                uiHandler.postDelayed(forcePlayNowTimer!!, forcePlayNowTimeoutMs)
                                forcePlayNow = true

                                syncBannersOnStart()
                                uiHandler.post {
                                    Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_LIST")
                                    sendSyncConfirmation(webSocket, "BANNER_LIST", "SUCCESS")
                                }
                            }
                            "BANNER_EXPIRED" -> {
                                val bannerId = message.optInt("banner_id", 0)
                                val titulo = message.optString("titulo", "")
                                Log.i(TAG, "[WebSocket] BANNER_EXPIRED recibido: id=$bannerId, titulo=$titulo")

                                uiHandler.post {
                                    val index = standbyItems.indexOfFirst { it.id == bannerId }
                                    if (index >= 0) {
                                        val item = standbyItems.removeAt(index)
                                        val file = File(item.localPath)
                                        if (file.exists()) file.delete()
                                        Log.i(TAG, "[WebSocket] Banner $bannerId eliminado del carrusel por expiración")
                                        if (standbyItems.isEmpty()) {
                                            stopStandbyCarousel()
                                        } else if (standbyIndex >= standbyItems.size) {
                                            standbyIndex = 0
                                        }
                                    }
                                    sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                }

                                scope.launch {
                                    val service = api ?: return@launch
                                    val baseUrl = backendBaseUrl ?: return@launch
                                    val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                                    val cache = repo.loadCache() ?: return@launch
                                    val removed = cache.items.removeAll { it.id == bannerId }
                                    if (removed) {
                                        repo.saveMeta(cache)
                                        Log.i(TAG, "[WebSocket] Banner $bannerId eliminado del cache metadata por expiración")
                                    }
                                }
                            }
                            "REINICIAR" -> {
                                Log.i(TAG, "[WebSocket] ==== REINICIAR COMMAND RECEIVED ====")
                                val scheduledAt = message.optString("scheduled_at", "")
                                val targetHour = message.optString("hour", "") // formato "06:35"
                                val isRecurring = message.optBoolean("recurring", false)
                                Log.i(
                                    TAG,
                                    "[WebSocket] hour=$targetHour, scheduled_at=$scheduledAt, recurring=$isRecurring"
                                )

                                try {
                                    val pkgName = applicationContext.packageName
                                    Log.i(TAG, "[WebSocket] Verificando si es Device Owner: $pkgName")

                                    // Guardar configuración recurrente si aplica
                                    if (dpm.isDeviceOwnerApp(pkgName)) {
                                        val prefs = getSharedPreferences("reinicio_config", MODE_PRIVATE)

                                        if (isRecurring && targetHour.isNotEmpty()) {
                                            Log.i(TAG, "[WebSocket] Guardando configuración de reinicio recurrente")
                                            prefs.edit()
                                                .putString("hora_reinicio", targetHour)
                                                .putBoolean("recurrente", true)
                                                .apply()
                                            Log.i(
                                                TAG,
                                                "[WebSocket] Configuración guardada: hora=$targetHour, recurrente=true"
                                            )
                                        } else if (!isRecurring) {
                                            prefs.edit()
                                                .putBoolean("recurrente", false)
                                                .apply()
                                        }
                                    }

                                    // Sí hay hour, calcular delay en timezone del dispositivo
                                    if (targetHour.isNotEmpty()) {
                                        val delay = calcularProximaReinicio(targetHour)

                                        if (delay > 0) {
                                            Log.i(
                                                TAG,
                                                "[WebSocket] Programando reinicio para dentro de ${delay / 1000 / 60} minutos"
                                            )
                                            sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                            uiHandler.postDelayed({
                                                ejecutarReinicio(dpm, adminComponent, webSocket, command, commandId = commandId)
                                            }, delay)
                                            return
                                        } else {
                                            Log.i(
                                                TAG,
                                                "[WebSocket] La hora programada ya pasó hoy, ejecutando inmediatamente"
                                            )
                                        }
                                    } else if (scheduledAt.isNotEmpty()) {
                                        // Legacy: usar scheduled_at para backward compatibility
                                        try {
                                            val normalizedAt =
                                                scheduledAt.replace("+00:00", "+0000").replace("+00", "+0000")
                                            val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.US)
                                            val targetTime = isoFormat.parse(normalizedAt)

                                            if (targetTime != null) {
                                                val now = System.currentTimeMillis()
                                                val delayLegacy = targetTime.time - now

                                                if (delayLegacy > 0) {
                                                    Log.i(
                                                        TAG,
                                                        "[WebSocket] Programando reinicio legacy para dentro de ${delayLegacy / 1000 / 60} minutos"
                                                    )
                                                    sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                                    uiHandler.postDelayed({
                                                        ejecutarReinicio(dpm, adminComponent, webSocket, command, commandId = commandId)
                                                    }, delayLegacy)
                                                    return
                                                }
                                            }
                                        } catch (e: Exception) {
                                            Log.e(TAG, "[WebSocket] Error parseando scheduled_at: ${e.message}")
                                        }
                                    }

                                    // Reinicio inmediato o sin hour
                                    if (dpm.isDeviceOwnerApp(pkgName)) {
                                        Log.i(TAG, "[WebSocket] ES Device Owner - ejecutando reinicio automático")
                                        sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                        Log.i(TAG, "[WebSocket] Confirmación RECEIVED enviada, ejecutando reinicio...")
                                        uiHandler.postDelayed({
                                            ejecutarReinicio(dpm, adminComponent, webSocket, command, commandId = commandId)
                                        }, 2000)
                                    } else {
                                        // No es Device Owner: mostrar diálogo
                                        Log.i(TAG, "[WebSocket] NO es Device Owner - mostrando diálogo...")
                                        sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                        runOnUiThread {
                                            try {
                                                Log.i(TAG, "[WebSocket] Intentando mostrar diálogo...")
                                                val alertDialog = android.app.AlertDialog.Builder(this@ScanActivity)
                                                    .setTitle("Reinicio solicitado")
                                                    .setMessage("El servidor ha solicitado el reinicio del dispositivo.\n\nPor favor, mantén presionado el botón de Encendido para reiniciar.")
                                                    .setPositiveButton("Aceptar") { _, _ ->
                                                        Log.i(TAG, "[WebSocket] Usuario presionó Aceptar")
                                                        sendSyncConfirmation(webSocket, command, "COMPLETED", commandId = commandId)
                                                    }
                                                    .setCancelable(false)
                                                    .create()
                                                alertDialog.show()
                                                Log.i(TAG, "[WebSocket] Diálogo mostrado correctamente")
                                            } catch (e: Exception) {
                                                Log.e(TAG, "[WebSocket] Error al mostrar diálogo: ${e.message}")
                                                sendSyncConfirmation(webSocket, command, "FAILED", "Error: ${e.message}", commandId = commandId)
                                            }
                                        }
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, "[WebSocket] Error preparando reinicio: ${e.message}")
                                    sendSyncConfirmation(webSocket, command, "FAILED", "Error: ${e.message}", commandId = commandId)
                                }
                            }
                            else -> {
                                Log.i(TAG, "[WebSocket] Comando recibido no reconocido: $command")
                            }
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
                        
                        // L1.4: Dedup por command_id - ignorar comandos ya procesados
                        val commandId = message.optString("command_id", "")
                        if (commandId.isNotEmpty() && !processedCommandIds.add(commandId)) {
                            Log.w(TAG, "[WebSocket] Comando duplicado ignorado (binario): command=$command command_id=$commandId")
                            return
                        }
                        
                        try {
                            sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                            Log.i(TAG, "[WebSocket] Confirmación enviada para comando (binario): $command")
                        } catch (e: Exception) {
                            Log.e(TAG, "[WebSocket] Error enviando confirmación (binario)", e)
                        }
                        when (command) {
                            "WIPE_AND_RESYNC" -> {
                                Log.i(
                                    TAG,
                                    "[WebSocket] Comando WIPE_AND_RESYNC recibido (binario). Pausando carrusel antes de purga..."
                                )

                                // 1. PAUSAR el carrusel INMEDIATAMENTE antes de borrar archivos
                                uiHandler.post {
                                    stopStandbyCarousel()
                                    binding.standbyOverlay.visibility = View.GONE
                                    Log.d(TAG, "[WebSocket] Carrusel detenido y overlay ocultado (binario)")
                                }

                                isPurging = true
                                scope.launch {
                                    val apiService = api
                                    if (apiService == null) {
                                        isPurging = false
                                        sendSyncConfirmation(webSocket, command, "FAILED", "ApiService no inicializado", commandId = commandId)
                                        return@launch
                                    }

                                    // 2. Ejecutar purga SIN callback de inicio de carrusel
                                    val purgeResult = ejecutarPurgaTotal(this@ScanActivity, apiService, baseUrl, deviceId) {
                                        // Callback vacío - controlamos el inicio manualmente
                                    }

                                    // 3. Solo iniciar carrusel DESPUÉS de que la purga termine exitosamente
                                    uiHandler.post {
                                        isPurging = false
                                        if (purgeResult.success) {
                                            Log.i(TAG, "[WebSocket] Purga exitosa (binario), iniciando carrusel...")
                                            startStandbyCarousel()
                                        } else {
                                            Log.w(TAG, "[WebSocket] Purga fallida (binario), no se inicia carrusel")
                                            sendSyncConfirmation(
                                                webSocket,
                                                command,
                                                "FAILED",
                                                purgeResult.reason ?: "Purga fallida",
                                                commandId
                                            )
                                        }
                                    }

                                    if (purgeResult.success) {
                                        sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                    } else {
                                        sendSyncConfirmation(
                                            webSocket,
                                            command,
                                            "FAILED",
                                            purgeResult.reason ?: "Purga fallida",
                                            commandId
                                        )
                                    }
                                }
                            }
                            "BANNER_INICIADO" -> {
                                val bannerId = message.optInt("banner_id", 0)
                                val titulo = message.optString("titulo", "")
                                Log.i(TAG, "[WebSocket] BANNER_INICIADO recibido (binario): id=$bannerId, titulo=$titulo")

                                // Marcar como notificado para evitar duplicados con polling
                                notifiedBannersStart.add(bannerId)

                                //Cancelar timer anterior si existe
                                forcePlayNowTimer?.let {uiHandler.removeCallbacks(it)}

                                //Programar expiracion
                                forcePlayNowTimer = Runnable {forcePlayNow = false}
                                uiHandler.postDelayed(forcePlayNowTimer!!, forcePlayNowTimeoutMs)

                                // Forzar reproducción inmediata (ignorar validación de fecha_inicio)
                                forcePlayNow = true

                                // Recargar banners inmediatamente y priorizar el nuevo banner
                                syncBannersOnStart(bannerId)
                                uiHandler.post {
                                    Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_INICIADO (binario)")
                                    // Confirmar al backend que el banner fue recibido
                                    sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                }
                            }
                            "BANNER_LIST" -> {
                                val bannersArray = message.optJSONArray("banners")
                                val count = bannersArray?.length() ?: 0
                                Log.i(TAG, "[WebSocket] BANNER_LIST recibido (binario): $count banners")

                                if (bannersArray != null) {
                                    for (i in 0 until bannersArray.length()) {
                                        val b = bannersArray.getJSONObject(i)
                                        notifiedBannersStart.add(b.optInt("banner_id", 0))
                                    }
                                }

                                forcePlayNowTimer?.let { uiHandler.removeCallbacks(it) }
                                forcePlayNowTimer = Runnable { forcePlayNow = false }
                                uiHandler.postDelayed(forcePlayNowTimer!!, forcePlayNowTimeoutMs)
                                forcePlayNow = true

                                syncBannersOnStart()
                                uiHandler.post {
                                    Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_LIST (binario)")
                                    sendSyncConfirmation(webSocket, "BANNER_LIST", "SUCCESS")
                                }
                            }
                            "BANNER_FINALIZADO" -> {
                                val bannerId = message.optInt("banner_id", 0)
                                val titulo = message.optString("titulo", "")
                                val bannerUrl = message.optString("url", "")
                                Log.i(TAG, "[WebSocket] BANNER_FINALIZADO recibido (binario): id=$bannerId, titulo=$titulo")

                                // Marcar como notificado para evitar duplicados con polling
                                notifiedBannersEnd.add(bannerId)

                                // Eliminar archivo local del banner que terminó
                                if (bannerId > 0 && bannerUrl.isNotEmpty()) {
                                    deleteBannerFile(bannerId, bannerUrl)
                                }

                                uiHandler.post {
                                    syncBannersOnStart()
                                    Log.i(TAG, "[WebSocket] Banners recargados tras BANNER_FINALIZADO (binario)")
                                    sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                }
                            }
                            "BANNER_EXPIRED" -> {
                                val bannerId = message.optInt("banner_id", 0)
                                val titulo = message.optString("titulo", "")
                                Log.i(TAG, "[WebSocket] BANNER_EXPIRED recibido (binario): id=$bannerId, titulo=$titulo")

                                uiHandler.post {
                                    val index = standbyItems.indexOfFirst { it.id == bannerId }
                                    if (index >= 0) {
                                        val item = standbyItems.removeAt(index)
                                        val file = File(item.localPath)
                                        if (file.exists()) file.delete()
                                        Log.i(TAG, "[WebSocket] Banner $bannerId eliminado del carrusel por expiración (binario)")
                                        if (standbyItems.isEmpty()) {
                                            stopStandbyCarousel()
                                        } else if (standbyIndex >= standbyItems.size) {
                                            standbyIndex = 0
                                        }
                                    }
                                    sendSyncConfirmation(webSocket, command, "SUCCESS", commandId = commandId)
                                }

                                scope.launch {
                                    val service = api ?: return@launch
                                    val baseUrl = backendBaseUrl ?: return@launch
                                    val repo = BannerRepository(this@ScanActivity, service, baseUrl)
                                    val cache = repo.loadCache() ?: return@launch
                                    val removed = cache.items.removeAll { it.id == bannerId }
                                    if (removed) {
                                        repo.saveMeta(cache)
                                        Log.i(TAG, "[WebSocket] Banner $bannerId eliminado del cache metadata por expiración (binario)")
                                    }
                                }
                            }
                            "REINICIAR" -> {
                                Log.i(
                                    TAG,
                                    "[WebSocket] Comando REINICIAR recibido (binario). Ejecutando reinicio del dispositivo..."
                                )
                                try {
                                    val pkgName = applicationContext.packageName
                                    if (dpm.isDeviceOwnerApp(pkgName)) {
                                        Log.i(TAG, "[WebSocket] ES Device Owner (binario) - ejecutando reinicio")
                                        sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                        Log.i(
                                            TAG,
                                            "[WebSocket] Confirmación RECEIVED enviada (binario), ejecutando reinicio..."
                                        )
                                        uiHandler.postDelayed({
                                            try {
                                                dpm.reboot(adminComponent)
                                            } catch (e: Exception) {
                                                Log.e(TAG, "[WebSocket] Error al ejecutar reinicio (binario): ${e.message}")
                                                sendSyncConfirmation(
                                                    webSocket,
                                                    command,
                                                    "FAILED",
                                                    "Error al reiniciar: ${e.message}",
                                                    commandId
                                                )
                                            }
                                        }, 2000)
                                    } else {
                                        Log.i(TAG, "[WebSocket] NO es Device Owner (binario) - mostrando diálogo...")
                                        sendSyncConfirmation(webSocket, command, "RECEIVED", commandId = commandId)
                                        runOnUiThread {
                                            try {
                                                val alertDialog = android.app.AlertDialog.Builder(this@ScanActivity)
                                                    .setTitle("Reinicio solicitado")
                                                    .setMessage("El servidor ha solicitado el reinicio del dispositivo.\n\nPor favor, mantén presionado el botón de Encendido para reiniciar.")
                                                    .setPositiveButton("Aceptar") { _, _ ->
                                                        Log.i(TAG, "[WebSocket] Usuario presionó Aceptar (binario)")
                                                        sendSyncConfirmation(webSocket, command, "COMPLETED", commandId = commandId)
                                                    }
                                                    .setCancelable(false)
                                                    .create()
                                                alertDialog.show()
                                            } catch (e: Exception) {
                                                Log.e(TAG, "[WebSocket] Error al mostrar diálogo (binario): ${e.message}")
                                                sendSyncConfirmation(webSocket, command, "FAILED", "Error: ${e.message}", commandId = commandId)
                                            }
                                        }
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, "[WebSocket] Error preparando reinicio (binario): ${e.message}")
                                    sendSyncConfirmation(webSocket, command, "FAILED", "Error: ${e.message}", commandId = commandId)
                                }
                            }
                            else -> {
                                Log.i(TAG, "[WebSocket] Comando recibido no reconocido (binario): $command")
                            }
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
        val now = System.currentTimeMillis()
        
        // Reset si pasaron más de 5 minutos desde el último intento
        if (now - wsLastReconnectTime > 5 * 60 * 1000) {
            wsReconnectAttempts = 0
            wsReconnectDelay = 5000L
            isReconnecting = false
        }
        wsLastReconnectTime = now
        
        if (isReconnecting) return
        isReconnecting = true
        
        // Exponential backoff con jitter (±20%)
        val baseDelay = minOf(1000L * (1 shl wsReconnectAttempts), maxReconnectDelay)
        val jitter = (baseDelay * 0.2 * Math.random()).toLong()
        val delay = baseDelay + jitter
        
        Log.i(TAG, "[WebSocket] Reconectando en ${delay}ms (intento ${wsReconnectAttempts + 1}, base=${baseDelay}ms)")
        
        uiHandler.removeCallbacks(reconnectRunnable)
        uiHandler.postDelayed(reconnectRunnable, delay)
    }

    private fun sendSyncConfirmation(
        webSocket: WebSocket,
        command: String,
        status: String,
        reason: String? = null,
        commandId: String? = null,
    ) {
        scope.launch {
            sendSyncConfirmationWithRetry(webSocket, command, status, reason, commandId)
        }
    }
    
    private suspend fun sendSyncConfirmationWithRetry(
        webSocket: WebSocket,
        command: String,
        status: String,
        reason: String? = null,
        commandId: String? = null,
        maxRetries: Int = 3
    ): Boolean {
        repeat(maxRetries) { attempt ->
            try {
                val confirmMsg = org.json.JSONObject()
                confirmMsg.put("type", "CONFIRMATION")
                confirmMsg.put("command", command)
                confirmMsg.put("device_id", deviceId)
                confirmMsg.put("status", status)
                if (!reason.isNullOrBlank()) {
                    confirmMsg.put("reason", reason)
                }
                if (!commandId.isNullOrBlank()) {
                    confirmMsg.put("command_id", commandId)
                }
                webSocket.send(confirmMsg.toString())
                Log.i(TAG, "[WebSocket] Confirmación enviada: status=$status command=$command")
                return true
            } catch (e: Exception) {
                Log.e(TAG, "[WebSocket] Confirmación failed (attempt ${attempt + 1}/$maxRetries): ${e.message}")
                if (attempt < maxRetries - 1) {
                    delay(1000L shl attempt)  // Exponential backoff: 1s, 2s, 4s
                }
            }
        }
        Log.e(TAG, "[WebSocket] Confirmación falló después de $maxRetries intentos: status=$status command=$command")
        return false
    }

    private fun notifyPlayingNow(item: BannerCacheItem) {
        try {
            val playingMsg = org.json.JSONObject()
            playingMsg.put("type", "PLAYING_NOW")
            playingMsg.put("device_id", deviceId)
            playingMsg.put("banner_id", item.id)
            
            val content = org.json.JSONObject()
            content.put("titulo", item.titulo ?: File(item.localPath).name)
            content.put("url", item.remoteUrl)
            content.put("tipo", item.tipo)
            item.duracionSeg?.let { content.put("duracion", it) }
            
            playingMsg.put("content", content)
            
            // Enviar via WebSocket si está disponible
            tabletWebSocket?.let { ws ->
                try {
                    ws.send(playingMsg.toString())
                    Log.i(TAG, "[WebSocket] PLAYING_NOW enviado: ${item.tipo} - ${item.titulo ?: item.localPath}")
                } catch (e: Exception) {
                    Log.e(TAG, "[WebSocket] Error enviando PLAYING_NOW: ${e.message}")
                }
            } ?: run {
                Log.w(TAG, "[WebSocket] WebSocket no disponible para PLAYING_NOW")
            }
        } catch (e: Exception) {
            Log.e(TAG, "[WebSocket] Error preparando PLAYING_NOW: ${e.message}")
        }
    }

    private fun showOutOfService() {
        runOnUiThread {
            binding.resultOverlay.visibility = View.VISIBLE
            binding.tvNombre.text = getString(R.string.fuera_de_servicio)
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
            dpm.isDeviceOwnerApp(applicationContext.packageName)
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
                    dpm.setLockTaskPackages(adminComponent, arrayOf(applicationContext.packageName))
                    Log.i(TAG, "Lock task packages configurados")
                } catch (e: Exception) {
                    Log.w(TAG, "No se pudieron configurar lock task packages: ${e.message}")
                }
            }
            
            val isPermitted = dpm.isLockTaskPermitted(applicationContext.packageName)
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

    private fun ejecutarReinicio(
        dpm: DevicePolicyManager,
        adminComponent: ComponentName,
        webSocket: WebSocket?,
        command: String,
        commandId: String? = null,
    ) {
        try {
            dpm.reboot(adminComponent)
            Log.i(TAG, "Reinicio ejecutado correctamente")
        } catch (e: Exception) {
            Log.e(TAG, "Error al ejecutar reinicio: ${e.message}")
            if (webSocket != null) {
                sendSyncConfirmation(webSocket, command, "FAILED", "Error al reiniciar: ${e.message}", commandId)
            }
        }
    }

    private fun programarReinicioRecurrente() {
        try {
            val prefs = getSharedPreferences("reinicio_config", MODE_PRIVATE)
            val horaReinicio = prefs.getString("hora_reinicio", null)
            val esRecurrente = prefs.getBoolean("recurrente", false)
            
            if (horaReinicio == null || !esRecurrente) {
                Log.i(TAG, "[Reinicio] No hay configuración de reinicio recurrente")
                return
            }
            
            Log.i(TAG, "[Reinicio] Programando reinicio recurrente a las $horaReinicio")
            
            val partes = horaReinicio.split(":")
            val hora = partes[0].toInt()
            val minuto = partes[1].toInt()
            
            val calendar = java.util.Calendar.getInstance()
            val nowMillis = calendar.timeInMillis
            
            calendar.set(java.util.Calendar.HOUR_OF_DAY, hora)
            calendar.set(java.util.Calendar.MINUTE, minuto)
            calendar.set(java.util.Calendar.SECOND, 0)
            calendar.set(java.util.Calendar.MILLISECOND, 0)
            
            // Si ya pasó la hora hoy, programar para mañana
            if (calendar.timeInMillis <= nowMillis) {
                calendar.add(java.util.Calendar.DAY_OF_YEAR, 1)
            }
            
            val alarmManager = getSystemService(ALARM_SERVICE) as? android.app.AlarmManager
            if (alarmManager == null) {
                Log.e(TAG, "[Reinicio] AlarmManager no disponible")
                return
            }
            
            val intent = Intent(this, ReinicioReceiver::class.java)
            val pendingIntent = android.app.PendingIntent.getBroadcast(
                this,
                1001,
                intent,
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
            )
            
            // Verificar permiso de alarms exactos (Android 12+)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                if (!alarmManager.canScheduleExactAlarms()) {
                    Log.w(TAG, "[Reinicio] No hay permiso para alarms exactos, intentando de todas formas")
                }
            }
            
            // Usar setExactAndAllowWhileIdle para Android 6+
            try {
                alarmManager.setExactAndAllowWhileIdle(
                    android.app.AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
            } catch (_: SecurityException) {
                Log.w(TAG, "[Reinicio] SecurityException: usando set() como fallback")
                alarmManager.set(
                    android.app.AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
            }
            
            Log.i(TAG, "[Reinicio] Alarm programado para ${calendar.time}")
        } catch (e: Exception) {
            Log.e(TAG, "[Reinicio] Error al programar reinicio recurrente: ${e.message}")
        }
    }

    private fun calcularProximaReinicio(horaTarget: String): Long {
        // Formato horaTarget: "06:35"
        val partes = horaTarget.split(":")
        if (partes.size != 2) return 0
        
        val hora = partes[0].toIntOrNull() ?: return 0
        val minuto = partes[1].toIntOrNull() ?: return 0
        
        val calendar = java.util.Calendar.getInstance()
        val ahora = System.currentTimeMillis()
        
        val targetCalendar = java.util.Calendar.getInstance().apply {
            set(java.util.Calendar.HOUR_OF_DAY, hora)
            set(java.util.Calendar.MINUTE, minuto)
            set(java.util.Calendar.SECOND, 0)
            set(java.util.Calendar.MILLISECOND, 0)
        }
        
        // Si ya pasó la hora hoy, programar para mañana
        if (targetCalendar.timeInMillis <= ahora) {
            targetCalendar.add(java.util.Calendar.DAY_OF_YEAR, 1)
        }
        
        return targetCalendar.timeInMillis - ahora
    }
}
