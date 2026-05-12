package com.example.verificadordepreciosluz

import android.os.Bundle
import android.content.Intent
import android.view.View
import android.view.KeyEvent
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


class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private var isUnlocked = false
    private val UNLOCK_CODE = "ADMIN-CODE-125"
    private var scannerBuffer = StringBuilder()
    private val handler = Handler(Looper.getMainLooper())
    private var bufferTimeoutRunnable: Runnable? = null

    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        // Interceptar teclas del escáner HID cuando el config está bloqueado
        if (!isUnlocked && event.action == KeyEvent.ACTION_DOWN) {
            val keyCode = event.keyCode
            val unicodeChar = event.unicodeChar
            
            Log.d("MainActivity", "dispatchKeyEvent: keyCode=$keyCode, unicodeChar=$unicodeChar")
            
            // Ignorar teclas de control (flechas, tab, etc.)
            if (keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_DPAD_CENTER) {
                // Enter del escáner - procesar el buffer acumulado
                val scannedText = scannerBuffer.toString()
                Log.d("MainActivity", "dispatchKeyEvent: ENTER detectado, buffer='$scannedText'")
                if (scannedText.isNotEmpty()) {
                    binding.etUnlockCode.setText(scannedText)
                    Log.d("MainActivity", "dispatchKeyEvent: Texto enviado a etUnlockCode='$scannedText'")
                }
                scannerBuffer.clear()
                return true // Consumir el Enter para que no active el botón
            } else if (unicodeChar != 0) {
                val char = unicodeChar.toChar()
                scannerBuffer.append(char)
                val bufferText = scannerBuffer.toString()
                Log.d("MainActivity", "Carácter agregado: '$char', buffer: '$bufferText', length=${bufferText.length}")

                // PROCESAR AUTOMÁTICAMENTE cuando alcance longitud válida
                if (bufferText.length == 14) {
                    Log.d("MainActivity", "Longitud válida alcanzada: ${bufferText.length}, procesando...")
                    binding.etUnlockCode.setText(bufferText)
                    scannerBuffer.clear()
                    return true
                }

                // Timeout de 2 segundos para limpiar buffer incompleto
                bufferTimeoutRunnable?.let {handler.removeCallbacks(it) }
                bufferTimeoutRunnable = Runnable {
                    if (scannerBuffer.isNotEmpty()) {
                        Log.w("MainActivity", "Timeout: limpiando buffer incompleto: '${scannerBuffer}'")
                        scannerBuffer.clear()
                    }
                }
                handler.postDelayed(bufferTimeoutRunnable!!, 2000L)

                return true
            }
        }
        return super.dispatchKeyEvent(event)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.d("MainActivity", "onCreate: Iniciando MainActivity")
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val sharedPref = getSharedPreferences("ConfigLuz", MODE_PRIVATE)
        val ipGuardada = sharedPref.getString("ip_servidor", "")
        val puertoGuardado = sharedPref.getString("puerto_servidor", getString(com.example.verificadordepreciosluz.R.string.default_port))
        Log.d("MainActivity", "onCreate: ipGuardada='$ipGuardada', puertoGuardado='$puertoGuardado'")
        
        binding.etIpServidor.setText(ipGuardada)
        binding.etPuertoServidor.setText(puertoGuardado)

        val hasNetwork = NetworkUtils.isNetworkAvailable(this)
        Log.d("MainActivity", "onCreate: hasNetwork=$hasNetwork, ipGuardada.isNullOrBlank=${ipGuardada.isNullOrBlank()}")

        // TextWatcher para el campo de desbloqueo
        binding.etUnlockCode.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {
                Log.d("MainActivity", "etUnlockCode.beforeTextChanged: s='$s'")
            }
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                Log.d("MainActivity", "etUnlockCode.onTextChanged: s='$s'")
            }
            override fun afterTextChanged(editable: Editable?) {
                val code = editable?.toString()?.trim() ?: ""
                Log.d("MainActivity", "etUnlockCode.afterTextChanged: code='$code', UNLOCK_CODE='$UNLOCK_CODE', coincidencia=${code == UNLOCK_CODE}")
                if (code == UNLOCK_CODE) {
                    Log.d("MainActivity", "etUnlockCode.afterTextChanged: ¡Código correcto! Desbloqueando")
                    unlockConfig()
                    binding.etUnlockCode.text?.clear()
                }
            }
        })

        // TextWatcher TEMPORAL para debug
        binding.etIpServidor.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {
                Log.d("MainActivity", "etIpServidor.beforeTextChanged: s='$s'")
            }
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                Log.d("MainActivity", "etIpServidor.onTextChanged: s='$s'")
            }
            override fun afterTextChanged(editable: Editable?) {
                val text = editable?.toString() ?: ""
                Log.d("MainActivity", "etIpServidor.afterTextChanged: text='$text'")
            }
        })

        // Verificar foco
        binding.etUnlockCode.setOnFocusChangeListener { _, hasFocus ->
            Log.d("MainActivity", "etUnlockCode focus changed: hasFocus=$hasFocus")
        }
        binding.etIpServidor.setOnFocusChangeListener { _, hasFocus ->
            Log.d("MainActivity", "etIpServidor focus changed: hasFocus=$hasFocus")
        }

        if (!ipGuardada.isNullOrBlank()) {
            Log.d("MainActivity", "onCreate: IP guardada encontrada, bloqueando inputs")
            binding.etIpServidor.isEnabled = false
            binding.etIpServidor.isFocusable = false
            binding.etPuertoServidor.isEnabled = false
            binding.etPuertoServidor.isFocusable = false
            binding.btnValidar.isFocusable = false
            binding.btnValidar.isFocusableInTouchMode = false
            binding.tvLockedIndicator.visibility = View.VISIBLE
            
            // CRÍTICO: Asegurar que el escáner HID escriba en etUnlockCode
            binding.etUnlockCode.isEnabled = true
            binding.etUnlockCode.isFocusable = true
            binding.etUnlockCode.isFocusableInTouchMode = true
            binding.etUnlockCode.requestFocus()
            Log.d("MainActivity", "onCreate: Forzando foco en etUnlockCode, tiene foco=${binding.etUnlockCode.hasFocus()}")
            
            // Verificar de inmediato dónde está el foco
            Handler(Looper.getMainLooper()).postDelayed({
                Log.d("MainActivity", "onCreate: Verificación foco - etUnlockCode=${binding.etUnlockCode.hasFocus()}, etIpServidor=${binding.etIpServidor.hasFocus()}")
            }, 500)

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
            Log.d("MainActivity", "onCreate: No hay IP guardada, mostrando configuración manual")
            isUnlocked = true
            binding.tvLockedIndicator.visibility = View.GONE
            binding.btnValidar.isFocusable = true
            binding.btnValidar.isFocusableInTouchMode = true
            binding.etIpServidor.requestFocus()
        }

        // Solo verificar backup si NO hay IP guardada
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
        Log.d("MainActivity", "unlockConfig: Iniciando desbloqueo")
        isUnlocked = true
        binding.etIpServidor.isEnabled = true
        binding.etIpServidor.isFocusable = true
        binding.etIpServidor.isFocusableInTouchMode = true
        binding.etPuertoServidor.isEnabled = true
        binding.etPuertoServidor.isFocusable = true
        binding.etPuertoServidor.isFocusableInTouchMode = true
        binding.btnValidar.isFocusable = true
        binding.btnValidar.isFocusableInTouchMode = true
        binding.tvLockedIndicator.visibility = View.GONE
        binding.etIpServidor.requestFocus()
        Log.d("MainActivity", "unlockConfig: Configuración desbloqueada")
        Toast.makeText(this, "Configuración desbloqueada", Toast.LENGTH_SHORT).show()
    }

    private fun probarConexion(ip: String, puerto: String, autoLaunch: Boolean, retryCount: Int = 0) {
        val base = NetworkUtils.buildBaseUrl(ip, puerto, getString(com.example.verificadordepreciosluz.R.string.default_port))
        Log.d("MainActivity", "probarConexion: Iniciando con ip='$ip', puerto='$puerto', autoLaunch=$autoLaunch, retryCount=$retryCount")
        val api = ApiClient.create(base, BuildConfig.DEBUG)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown"
        val maxRetries = 5

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                withContext(Dispatchers.Main) {
                    binding.btnValidar.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                Log.d("MainActivity", "probarConexion: Enviando ping a $base")
                val result = api.ping(deviceId)
                Log.d("MainActivity", "probarConexion: Ping exitoso")
                withContext(Dispatchers.Main) {
                    if (!autoLaunch) {
                        Toast.makeText(this@MainActivity, "Resultado de ping: ${result.status}", Toast.LENGTH_LONG).show()
                    }
                    startActivity(Intent(this@MainActivity, com.example.verificadordepreciosluz.ui.scanner.ScanActivity::class.java))
                    finish()
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "probarConexion: Error en intento $retryCount", e)
                withContext(Dispatchers.Main) {
                    if (autoLaunch && retryCount < maxRetries) {
                        val delay = (retryCount + 1) * 2000L
                        Log.d("MainActivity", "probarConexion: Reintentando en ${delay}ms...")
                        kotlinx.coroutines.delay(delay)
                        probarConexion(ip, puerto, autoLaunch, retryCount + 1)
                    } else {
                        val message = when (e) {
                            is HttpException -> "Error HTTP (${e.code()}) al conectar"
                            is IOException -> "Tiempo de Conexión agotado"
                            else -> "No se pudo conectar al servidor"
                        }
                        Log.d("MainActivity", "probarConexion: Resultado final: $message")
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
}
