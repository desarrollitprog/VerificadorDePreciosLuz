package com.example.verificadordepreciosluz

import android.os.Bundle
import android.content.Intent
import android.view.View
import android.widget.Toast
import android.provider.Settings
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.edit
import androidx.lifecycle.lifecycleScope
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.BuildConfig
import com.example.verificadordepreciosluz.databinding.ActivityMainBinding
import com.example.verificadordepreciosluz.util.NetworkUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.example.verificadordepreciosluz.data.local.BackupRepository
import retrofit2.HttpException
import java.io.IOException
import android.text.Editable
import android.text.TextWatcher
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var cameraExecutor: ExecutorService
    private var isUnlocked = false
    private val UNLOCK_CODE = "ADMIN-CODE-125"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()

        val sharedPref = getSharedPreferences("ConfigLuz", MODE_PRIVATE)
        val ipGuardada = sharedPref.getString("ip_servidor", "")
        binding.etIpServidor.setText(ipGuardada)
        val puertoGuardado = sharedPref.getString("puerto_servidor", getString(com.example.verificadordepreciosluz.R.string.default_port))
        binding.etPuertoServidor.setText(puertoGuardado)

        val hasNetwork = NetworkUtils.isNetworkAvailable(this)

        if (!ipGuardada.isNullOrBlank()) {
            binding.etIpServidor.isEnabled = false
            binding.etIpServidor.isFocusable = false
            binding.etPuertoServidor.isEnabled = false
            binding.etPuertoServidor.isFocusable = false
            binding.tvLockedIndicator.visibility = View.VISIBLE
            startCameraScanner()
            binding.etUnlockCode.requestFocus()

            if (hasNetwork) {
                probarConexion(ipGuardada, puertoGuardado.orEmpty(), autoLaunch = true)
            } else {
                val backup = BackupRepository(this@MainActivity).loadBackup()
                if (backup != null) {
                    Toast.makeText(this, "Sin conexión: modo offline", Toast.LENGTH_LONG).show()
                    startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                    finish()
                }
            }
        } else {
            binding.tvLockedIndicator.visibility = View.GONE
            // Installation NEW - NO check automatic, wait for manual
        }

        binding.etUnlockCode.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(editable: Editable?) {
                val code = editable?.toString()?.trim() ?: ""
                if (code == UNLOCK_CODE) {
                    unlockConfig()
                    binding.etUnlockCode.text?.clear()
                }
            }
        })

        // Solo verificar backup si NO hay IP guardada (si la hay, ya se manejó arriba)
        if (ipGuardada.isNullOrBlank() && !hasNetwork) {
            val backup = BackupRepository(this@MainActivity).loadBackup()
            if (backup != null) {
                startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                finish()
                return
            } else {
                Toast.makeText(this, "Sin conexión y sin respaldo local", Toast.LENGTH_LONG).show()
            }
        }

        binding.btnValidar.setOnClickListener {
            val ip = binding.etIpServidor.text.toString().trim()
            val puerto = binding.etPuertoServidor.text.toString().trim()

            val validation = validateConfig(ip, puerto)
            if (!validation.isValid) {
                Toast.makeText(this, validation.message, Toast.LENGTH_LONG).show()
                return@setOnClickListener
            }

            val sanitizedHost = validation.sanitizedHost.orEmpty()
            val normalizedPort = validation.portToUse.orEmpty()

            sharedPref.edit(commit = false) {
                putString("ip_servidor", sanitizedHost)
                putString("puerto_servidor", normalizedPort)
            }

            Toast.makeText(this, "IP Guardada: $sanitizedHost:$normalizedPort", Toast.LENGTH_SHORT).show()

            if (NetworkUtils.isNetworkAvailable(this)) {
                probarConexion(sanitizedHost, normalizedPort, autoLaunch = false)
            } else {
                val backup = BackupRepository(this@MainActivity).loadBackup()
                if (backup != null) {
                    Toast.makeText(this, "Sin conexión: iniciando modo offline", Toast.LENGTH_LONG).show()
                    startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                    finish()
                } else {
                    Toast.makeText(this, "Sin conexión y sin respaldo local", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun unlockConfig() {
        isUnlocked = true
        binding.etIpServidor.isEnabled = true
        binding.etIpServidor.isFocusable = true
        binding.etIpServidor.isFocusableInTouchMode = true
        binding.etPuertoServidor.isEnabled = true
        binding.etPuertoServidor.isFocusable = true
        binding.etPuertoServidor.isFocusableInTouchMode = true
        binding.tvLockedIndicator.visibility = View.GONE
        binding.etIpServidor.requestFocus()
        Toast.makeText(this, "Configuración desbloqueada", Toast.LENGTH_SHORT).show()
    }

    private fun startCameraScanner() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewViewLogin.surfaceProvider)
            }
            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also {
                    it.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalyzer)
            } catch (e: Exception) {
                Log.e("MainActivity", "Camera binding failed", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.camera.core.ExperimentalGetImage
    private fun processImage(imageProxy: androidx.camera.core.ImageProxy) {
        val mediaImage = imageProxy.image
        if (mediaImage != null) {
            val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
            val scanner = BarcodeScanning.getClient()
            scanner.process(image)
                .addOnSuccessListener { barcodes ->
                    for (barcode in barcodes) {
                        barcode.rawValue?.let { code ->
                            runOnUiThread {
                                binding.etUnlockCode.setText(code)
                            }
                        }
                    }
                }
                .addOnCompleteListener {
                    imageProxy.close()
                }
        } else {
            imageProxy.close()
        }
    }

    private fun probarConexion(ip: String, puerto: String, autoLaunch: Boolean, retryCount: Int = 0) {
        val base = NetworkUtils.buildBaseUrl(ip, puerto, getString(com.example.verificadordepreciosluz.R.string.default_port))
        val api = ApiClient.create(base, BuildConfig.DEBUG)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
        val maxRetries = 5

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                withContext(Dispatchers.Main) {
                    binding.btnValidar.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                val result = api.ping(deviceId)
                withContext(Dispatchers.Main) {
                    if (!autoLaunch) {
                        Toast.makeText(
                            this@MainActivity,
                            "Resultado de ping: ${result.status}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                    startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                    finish()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    if (autoLaunch && retryCount < maxRetries) {
                        val delay = (retryCount + 1) * 2000L
                        Log.d("MainActivity", "Intento ${retryCount + 1}/$maxRetries falló. Reintentando en ${delay}ms...")
                        Handler(Looper.getMainLooper()).postDelayed({
                            probarConexion(ip, puerto, autoLaunch, retryCount + 1)
                        }, delay)
                    } else {
                        val message = when (e) {
                            is HttpException -> "Error HTTP (${e.code()}) al conectar"
                            is IOException -> "Tiempo de Conexion agotado"
                            else -> "No se pudo conectar al servidor"
                        }
                        if (!autoLaunch) {
                            Toast.makeText(this@MainActivity, message, Toast.LENGTH_LONG).show()
                        } else {
                            Toast.makeText(this@MainActivity, "Sin conexión: modo offline", Toast.LENGTH_LONG).show()
                            val backup = BackupRepository(this@MainActivity).loadBackup()
                            if (backup != null) {
                                startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                                finish()
                            }
                        }
                    }
                }
            } finally {
                withContext(Dispatchers.Main) {
                    if (retryCount >= maxRetries || !autoLaunch) {
                        binding.btnValidar.isEnabled = true
                        binding.progressBar.visibility = View.GONE
                    }
                }
            }
        }
    }

    private fun validateConfig(hostInput: String, portInput: String): ValidationResult {
        val defaultPort = getString(com.example.verificadordepreciosluz.R.string.default_port)
        val sanitizedHost = NetworkUtils.sanitizeHost(hostInput)

        if (!NetworkUtils.validateHost(sanitizedHost)) {
            return ValidationResult(false, "Host inválido. Usa IP o dominio válidos")
        }

        val portToUse = portInput.ifBlank { defaultPort }
        if (!NetworkUtils.validatePort(portToUse)) {
            return ValidationResult(false, "Puerto inválido (1-65535)")
        }

        return ValidationResult(true, null, sanitizedHost, portToUse)
    }

    private data class ValidationResult(
        val isValid: Boolean,
        val message: String?,
        val sanitizedHost: String? = null,
        val portToUse: String? = null
    )

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}