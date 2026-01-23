package com.example.verificadordepreciosluz

import android.os.Bundle
import android.content.Intent
import android.view.View
import android.widget.Toast
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
import retrofit2.HttpException
import java.io.IOException

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 2. Cargamos la IP si ya fue guardada anteriormente (Persistencia)
        val sharedPref = getSharedPreferences("ConfigLuz", MODE_PRIVATE)
        val ipGuardada = sharedPref.getString("ip_servidor", "")
        binding.etIpServidor.setText(ipGuardada)
        val puertoGuardado = sharedPref.getString("puerto_servidor", getString(com.example.verificadordepreciosluz.R.string.default_port))
        binding.etPuertoServidor.setText(puertoGuardado)

        // Si hay config guardada, probar ping antes de saltar al escáner (pero no cortamos la inicialización de la pantalla)
        if (!ipGuardada.isNullOrBlank()) {
            val validation = validateConfig(ipGuardada, puertoGuardado.orEmpty())
            if (validation.isValid) {
                probarConexion(validation.sanitizedHost.orEmpty(), validation.portToUse.orEmpty(), autoLaunch = true)
            }
        }

        // 3. Acción al hacer clic en el botón
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

            // Probar conexión llamando /ping en el backend
            probarConexion(sanitizedHost, normalizedPort, autoLaunch = false)
        }
    }

    private fun probarConexion(ip: String, puerto: String, autoLaunch: Boolean) {
        val base = NetworkUtils.buildBaseUrl(ip, puerto, getString(com.example.verificadordepreciosluz.R.string.default_port))
        val api = ApiClient.create(base, BuildConfig.DEBUG)

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                withContext(Dispatchers.Main) {
                    binding.btnValidar.isEnabled = false
                    binding.progressBar.visibility = View.VISIBLE
                }
                val result = api.ping()
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
                    val message = when (e) {
                        is HttpException -> "Error HTTP (${e.code()}) al conectar"
                        is IOException -> "Tiempo de Conexion agotado"
                        else -> "No se pudo conectar al servidor"
                    }
                    Toast.makeText(this@MainActivity, message, Toast.LENGTH_LONG).show()
                }
            } finally {
                withContext(Dispatchers.Main) {
                    binding.btnValidar.isEnabled = true
                    binding.progressBar.visibility = View.GONE
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