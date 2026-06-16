package com.example.verificadordepreciosluz.data.local

import com.example.verificadordepreciosluz.data.network.ProductoResponse
import java.util.LinkedHashMap

data class ScanCacheEntry(
    val timestamp: Long,
    val producto: ProductoResponse
)

class ScanCache(
    private val maxSize: Int = 500,
    private val ttlMs: Long = 15 * 60 * 1000L
) {
    private val cache = object : LinkedHashMap<String, ScanCacheEntry>(16, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, ScanCacheEntry>): Boolean {
            return size > maxSize
        }
    }

    @Synchronized
    fun get(code: String): ProductoResponse? {
        val entry = cache[code] ?: return null
        if (System.currentTimeMillis() - entry.timestamp > ttlMs) {
            cache.remove(code)
            return null
        }
        return entry.producto
    }

    @Synchronized
    fun put(code: String, producto: ProductoResponse) {
        cache[code] = ScanCacheEntry(System.currentTimeMillis(), producto)
    }

    @Synchronized
    fun size(): Int = cache.size

    @Synchronized
    fun clear() {
        cache.clear()
    }
}
