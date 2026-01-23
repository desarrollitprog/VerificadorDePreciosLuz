package com.example.verificadordepreciosluz

import android.os.Bundle
import android.content.Intent
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.edit
import androidx.lifecycle.lifecycleScope
import com.example.verificadordepreciosluz.data.network.ApiClient
import com.example.verificadordepreciosluz.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

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
            probarConexion(ipGuardada, puertoGuardado.orEmpty(), autoLaunch = true)
        }

        // 3. Acción al hacer clic en el botón
        binding.btnValidar.setOnClickListener {
            val ip = binding.etIpServidor.text.toString().trim()
            val puerto = binding.etPuertoServidor.text.toString().trim()

            if (ip.isNotEmpty()) {
                // Función de extensión KTX: guarda y aplica automáticamente
                sharedPref.edit(commit = false) {
                    putString("ip_servidor", ip)
                    putString("puerto_servidor", puerto)
                }

                Toast.makeText(this, "IP Guardada: $ip:$puerto", Toast.LENGTH_SHORT).show()

                // Probar conexión llamando /ping en el backend
                probarConexion(ip, puerto, autoLaunch = false)
            } else {
                // Error si el campo está vacío
                Toast.makeText(this, "Por favor, ingresa la IP del servidor", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun probarConexion(ip: String, puerto: String, autoLaunch: Boolean) {
        val base = ensurePort(sanitizeHost(ip), puerto)
        val api = ApiClient.create(base)

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
                    Toast.makeText(
                        this@MainActivity,
                        "No se pudo conectar al servidor: ${e.localizedMessage}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } finally {
                withContext(Dispatchers.Main) {
                    binding.btnValidar.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                }
            }
        }
    }

    private fun ensurePort(ip: String, port: String): String {
        val p = port.ifBlank { getString(com.example.verificadordepreciosluz.R.string.default_port) }
        return if (ip.contains(":")) ip else "$ip:$p"
    }

    private fun sanitizeHost(raw: String): String {
        return raw.removePrefix("http://").removePrefix("https://").trimEnd('/')
    }
}