# Plan de Mejoras

## 1. Análisis: ¿Por qué un verificador "deja de escribir" el serial en el input?

**Realidad:** El escáner HID (USB) **siempre escribe** en `etMockCode` porque es un teclado y el input tiene foco constante (`requestFocus()` en 10+ lugares). El problema real es que el serial **se escribe pero se ignora** en estas barreras:

| Barrera | Archivo:Línea | Silencioso | Impacto |
|---------|--------------|------------|---------|
| `pauseUntil` (4s post-éxito) | ScanActivity.kt:547 | Sin log | Ignora TODO scan durante 4s |
| `requestInFlight == true` | ScanActivity.kt:549 | Sin log | Ignora TODO scan mientras la API no responda |
| Cooldown mismo código (1.5s) | ScanActivity.kt:550 | Sin log | Ignora scans repetidos |
| `sanitizeCode` falla (no 8/12/13 dígitos) | ScanActivity.kt:537-543 | Toast | Serial visible en input pero no procesado |
| Kiosk exit code | ScanActivity.kt:527-534 | Log | Limpia input, no procesa |
| `code.isEmpty()` en mock | ScanActivity.kt:557 | Sin log | Submit ignorado |
| Debounce 250ms mock | ScanActivity.kt:560 | Sin log | Multi-enter ignorado |
| Cámara ML Kit | ScanActivity.kt:490-521 | Ignora | Nunca escribe en ningún input |

### Problemas de diseño detectados

- Las 3 barreras principales (`pauseUntil`, `requestInFlight`, cooldown) no emiten **ningún log** — imposible diagnosticar en producción por qué un scan no se procesó
- `pauseUntil` (4s) y `requestInFlight` son bloqueos **globales**: afectan a todos los escáneres (cámara + USB HID) indiscriminadamente
- La cámara nunca escribe en el `EditText`, bypassa completamente el input

---

## 2. Script de pruebas de estrés vía ADB

### Objetivo

Probar la app Android en el kiosko real bajo carga: inyectar seriales consecutivos vía ADB y medir cuántos llegan a procesarse vs cuántos se pierden en cada barrera.

### Requisitos

- Python 3.10+ en PC (Windows)
- ADB en PATH
- Kiosko conectado por USB/WiFi con depuración USB habilitada
- `adb devices` reconoce el dispositivo

### Pipeline del script

```
stress_test.py

1. Carga seriales (desde /backup API o archivo CSV local)

2. Conecta ADB al kiosko
   ├── adb shell input keyevent KEYCODE_WAKE
   └── adb shell am start -n ...ScanActivity (si no está abierta)

3. Inicia logcat en background:
   ├── adb logcat -c
   └── adb logcat -s ScanActivity -v time > log_YYMMDD_HHMM.txt

4. Bucle principal:
   Por cada serial en skus.csv:
   ├── adb shell input text <codigo>
   ├── adb shell input keyevent KEYCODE_ENTER
   ├── Espera N ms (configurable: 3000, 5000, 7000, etc.)
   ├── Registra: enviado, timestamp
   └── Verifica logcat en busca de:
       ├── "maybeProcessCode" → llegó a procesamiento
       ├── "scan_ignored"     → bloqueado por barrera (requiere mejora #3)
       ├── "Código inválido"  → sanitize falló
       └── sin marca          → PERDIDO (por barrera sin log)

5. Fases de prueba:
   ├── Fase 1: 1 scan / 7s (ritmo normal) [20 scans]
   ├── Fase 2: 1 scan / 5s (hora pico) [30 scans]
   ├── Fase 3: 1 scan / 3s (hora pico intensa) [40 scans]
   ├── Fase 4: 1 scan / 2s (sobrecarga) [30 scans]
   └── Fase 5: 10 scans en 1s (ráfaga) [3 rondas]

6. Post-procesamiento del logcat:
   ├── Extraer timestamp de cada "maybeProcessCode"
   ├── Extraer timestamp de cada "scan_ignored"
   ├── Extraer timestamp de cada "scan_error"
   ├── Extraer timestamp de cada "Codigo inválido"
   ├── Extraer excepciones, ANR, crashes
   └── Calcular diferencia entre enviado y procesado

7. Reporte final:
   ├── Seriales enviados vs procesados por fase
   ├── Pérdidas estimadas por barrera (pauseUntil / requestInFlight / cooldown)
   ├── Latencia entre input y maybeProcessCode
   ├── Errores (timeout, 404, 5xx, excepciones)
   └── Crashes/ANR detectados
```

### Estructura de archivos

```
raíz-del-proyecto/
├── stress_test.py              # Script principal
├── skus.csv                    # Seriales a inyectar (descargados de /backup)
├── requirements.txt            # Dependencias Python
└── resultados/                 # Output de cada ejecución
    ├── log_YYYYMMDD_HHMM.txt   # Logcat crudo
    ├── reporte_YYYYMMDD_HHMM.json  # Métricas estructuradas
    └── resumen_YYYYMMDD_HHMM.txt   # Reporte legible
```

### Comandos ADB clave

```powershell
# Inyectar código de barras (escribe en etMockCode que tiene foco)
adb shell input text "7591234567890"

# Enter para confirmar
adb shell input keyevent KEYCODE_ENTER

# Limpiar logcat
adb shell logcat -c

# Filtrar logcat por ScanActivity
adb shell logcat -s ScanActivity -v time

# Verificar que la app está en primer plano
adb shell dumpsys window windows | findstr "mCurrentFocus"
```

### Logcat patterns a capturar

| Patrón | Significado | Nivel |
|--------|-------------|-------|
| `maybeProcessCode: code='...'` | Serial llegó a procesamiento | Exito |
| `scan_ignored:` (nuevo) | Bloqueado por barrera | Bloqueo |
| `Codigo invalido` | `sanitizeCode` fallo | Bloqueo |
| `Codigo de salida detectado` | Kiosk exit code | Bloqueo |
| `onBarcodeDetected` (nuevo) | Pasó todas las barreras | Exito |
| `ANR` en logcat | Application Not Responding | Crash |
| `FATAL EXCEPTION` | Crash total | Crash |
| Scan NO logueado | Perdido en barrera sin log | Perdida |

### Dependencias Python

```txt
# requirements.txt
# Opcional: httpx para descargar seriales desde /backup
```

### Como ejecutar

```powershell
# 1. Conectar kiosko
adb devices

# 2. Opcional: descargar seriales desde /backup
python stress_test.py --download-skus http://ip-servidor:8000

# 3. O usar archivo local
python stress_test.py --skus skus.csv --rate 5000

# 4. Parametros
--rate       # ms entre scans (3000=3s, 5000=5s, 7000=7s)
--phases     # ejecutar todas las fases
--duration   # tiempo total en segundos
--output     # directorio de salida
```

---

## 3. Mejora: logging en las barreras silenciosas

Agregar logs en las 3 barreras silenciosas de `maybeProcessCode` para poder medir con precisión:

```kotlin
// ScanActivity.kt ~line 547
if (now < pauseUntil) {
    Log.d(TAG, "scan_ignored: pauseUntil activo (${pauseUntil - now}ms restantes)")
    return
}
// ~line 549
if (requestInFlight) {
    Log.d(TAG, "scan_ignored: requestInFlight activo")
    return
}
// ~line 550
if (clean == lastCode && (now - lastScanAt) < cooldown) {
    Log.d(TAG, "scan_ignored: cooldown mismo codigo (${now - lastScanAt}ms)")
    return
}
```

Y en `onBarcodeDetected` (~line 1351):
```kotlin
Log.d(TAG, "onBarcodeDetected: code='$code'")
```

---

## 4. Orden de implementacion

1. Crear `stress_test.py` en la raiz
2. Crear `requirements.txt`
3. Agregar los 3 logs faltantes en `ScanActivity.kt` (lineas 547, 549, 550)
4. Agregar log en `onBarcodeDetected` (linea 1351)
5. Crear `resultados/` directorio
6. Probar en un kiosko real o emulador
7. Analizar resultados y documentar hallazgos
