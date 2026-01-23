package com.example.verificadordepreciosluz.util

import java.net.IDN

object NetworkUtils {
    private val ipv4Regex = Regex("^(25[0-5]|2[0-4]\\d|1?\\d{1,2})(\\.(25[0-5]|2[0-4]\\d|1?\\d{1,2})){3}$")
    private val hostnameRegex = Regex("^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(\\.([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$")

    fun sanitizeHost(raw: String): String = raw.removePrefix("http://").removePrefix("https://").trim().trimEnd('/')

    fun validateHost(host: String): Boolean {
        if (host.isBlank()) return false
        val ascii = runCatching { IDN.toASCII(host) }.getOrNull() ?: return false
        return ipv4Regex.matches(ascii) || hostnameRegex.matches(ascii)
    }

    fun validatePort(port: String?): Boolean {
        val value = port?.toIntOrNull() ?: return false
        return value in 1..65535
    }

    fun buildBaseUrl(hostInput: String, portInput: String?, defaultPort: String): String {
        val sanitizedHost = sanitizeHost(hostInput)
        val port = if (validatePort(portInput)) portInput else defaultPort
        val withPort = if (sanitizedHost.contains(":")) sanitizedHost else "$sanitizedHost:$port"
        val withScheme = if (withPort.startsWith("http://") || withPort.startsWith("https://")) withPort else "http://$withPort"
        return if (withScheme.endsWith('/')) withScheme else "$withScheme/"
    }

    fun normalizeBase(raw: String): String {
        val sanitized = sanitizeHost(raw)
        val withScheme = if (sanitized.startsWith("http://") || sanitized.startsWith("https://")) sanitized else "http://$sanitized"
        return if (withScheme.endsWith('/')) withScheme else "$withScheme/"
    }
}
