# Casos de Prueba - Replicación Selectiva (Partes 1 y 2)

## Resumen de Implementación

### Parte 1: Replicación Selectiva
- Upload con asignación específica → replica SOLO a servidores con dispositivos seleccionados
- Upload con "todos" → replica a TODOS los servidores
- Edit con "todos" → actualiza TODOS los servidores

### Parte 2: Cleanup
- Edit con "todos" → detecta servidores sin banner → replica archivo + metadatos

---

## Casos de Prueba - Escenarios de Éxito

### ✅ Test 1: Upload con "Asignar a Todos"
```
Entrada:  asignacion_todos=true, sin dispositivos
Acción:   POST /banners/upload
Resultado esperado:
  - replicar_archivo_a_todas_las_apis(dispositivo_ids=None)
  - Todos los servidores reciben el banner
  - Logs: "[DEBUG] Upload: Replicando archivo a TODAS las APIs"
```

### ✅ Test 2: Upload con Dispositivos Específicos
```
Entrada:  asignacion_todos=false, dispositivos=['D1']
Acción:   POST /banners/upload
Servidor A tiene D1, Servidor B no tiene D1
Resultado esperado:
  - Solo Servidor A recibe el banner
  - Servidor B NO recibe nada
  - Log: "[DEBUG] Upload: Replicando SOLO a 1 servidores"
```

### ✅ Test 3: Edit - Cambiar de Específico a Todos (CASO CRÍTICO - PARTE 2)
```
Estado inicial:
  - Banner X был создан с устройствами D1 (только Сервер A)
  - Servidor A tiene Banner X, Servidor B NO tiene Banner X

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=true
Resultado esperado:
  1. verificar_banner_existe_en_api() para cada servidor
     - Servidor A: existe (200)
     - Servidor B: NO existe (404)
  2. replicar_banner_completo_a_servidores() para Servidor B
     - Envía archivo + metadatos
  3. actualizar_banner_en_todas_las_apis() para Servidor A
     - Solo actualiza metadata
  - Logs: "[DEBUG] PART2-CLEANUP: 1 servidores necesitan el banner"
```

### ✅ Test 4: Edit - Cambiar de Todos a Específico
```
Estado inicial:
  - Banner X был "все устройства"
  - Servidor A, B, C tienen Banner X

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=false&dispositivo_ids=['D1']
Servidor A tiene D1, Servidor B y C no tienen D1
Resultado esperado:
  - Solo Servidor A recibe actualización con dispositivo_ids=['D1']
  - Servidor B y C: ¿qué pasa? (ver Caso 5)
  - Log: "[DEBUG] Replicando SOLO a 1 servidores con asignaciones"
```

---

## ⚠️ Casos Críticos - Problemas Potenciales

### ❌ Caso 5: Edit - Remover asignación de servidores que tenían el banner
```
Estado inicial:
  - Banner X был "все устройства" en Servidores A, B, C

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=false&dispositivo_ids=['D1']
Servidor A tiene D1, Servidor B y C no tienen D1

PROBLEMA: Los Servidores B y C tienen el banner pero ahora no deberían.
          El sistema NO elimina el banner de esos servidores.

Estado final:
  - Servidor A: Banner X con filtro D1 ✅
  - Servidor B: Banner X (sin filtro) ❌ - debería estar eliminado
  - Servidor C: Banner X (sin filtro) ❌ - debería estar eliminado
```

**Solución futura necesaria**: Agregar lógica para eliminar banners de servidores que perdieron la asignación.

### ❌ Caso 6: Archivo no encontrado durante cleanup
```
Estado:
  - Banner был удален физически с диска
  - Servidor B не имеет Banner X

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=true
          (desencadenante cleanup)

PROBLEMA: El archivo no existe en disco
          - replicar_banner_completo_a_servidores() fallará
          - Log: "[ERROR] Archivo no encontrado"

Estado final:
  - Servidor B: NO recibe el banner ❌
```

**Mitigación actual**: La función verifica `os.path.isfile(file_path)` antes de replicar.

### ❌ Caso 7: Servidor fuera de línea durante cleanup
```
Estado:
  - Banner X был только на Servidor A
  - Servidor B tiene el banner (404 al verificar)
  - Servidor C está fuera de línea

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=true

PROBLEMA: 
  - verificar_banner_existe_en_api() para Servidor C puede fallar por timeout
  - replicar_banner_completo_a_servidores() para Servidor C fallará

Estado final:
  - Servidor A: actualizado ✅
  - Servidor B: recibe banner ✅
  - Servidor C: estado incierto ❌ (timeout)
```

### ❌ Caso 8: Condición de carrera - Edit concurrente
```
Servidor A inicia: PUT /banners/1/asignaciones (cambiar a todos)
Servidor B inicia: PUT /banners/1/asignaciones (cambiar a específico)

PROBLEMA: El segundo request puede sobrescribir el primero.
          No hay bloqueo a nivel de banner.
```

### ❌ Caso 9: Metadatos desincronizados después de cleanup
```
Estado inicial:
  - Banner X был создан с título "A"
  - Servidor A tiene Banner X (título "A")
  - Servidor B не имеет Banner X

Acción:   Admin cambia título a "B" y asigna a todos

Flujo:
  1. verificar_banner_existe_en_api()
     - Servidor A: existe con título "A"
     - Servidor B: NO existe
  2. replicar_banner_completo_a_servidores() para Servidor B
     - Envía con título "B" ✅
  3. actualizar_banner_en_todas_las_apis() para Servidor A
     - Envía con título "B" ✅

Resultado: Ambos con título "B" ✅

PERO si el paso 3 falla:
  - Servidor A: título "A" ❌
  - Servidor B: título "B" ✅
```

### ❌ Caso 10: Servidor nuevo registrado después del upload inicial
```
Estado:
  - Banner X был создан на Servidor A, B
  - Nuevo Servidor C se registra después

Acción:   PUT /banners/{id}/asignaciones?asignacion_todos=true

PROBLEMA: Si el banner был создан с asignacion_todos=true originally,
          el cleanup no se activa porque todos los servidores
          conocidos en ese momento tenían el banner.

Estado final:
  - Servidor A: tiene Banner X ✅
  - Servidor B: tiene Banner X ✅
  - Servidor C: NO tiene Banner X ❌
```

**Solución**: Para "asignar a todos", siempre verificar TODOS los servidores actuales.

---

## 📋 Matriz de Comportamiento

| Escenario | Upload/Edit | Servidores con banner antes | Acción | ¿Funciona? |
|-----------|-------------|----------------------------|--------|------------|
| 1 | Upload todos | Ninguno | Replicar a todos | ✅ |
| 2 | Upload específico | Ninguno | Replicar a específicos | ✅ |
| 3 | Edit específico→todos | Algunos | Cleanup + replicar faltantes | ✅ |
| 4 | Edit todos→específico | Todos | Actualizar específicos | ⚠️ Ver 5 |
| 5 | Edit específico→ninguno | Algunos | Actualizar vacio | ⚠️ Ver 5 |
| 6 | Edit (archivo faltante) | Algunos | Fallará en cleanup | ⚠️ Ver 6 |
| 7 | Edit (servidor offline) | Algunos | Timeout/error | ⚠️ Ver 7 |

---

## 🔧 Recomendaciones

1. **Agregar logging detallado** para detectar problemas de cleanup
2. **Agregar retry logic** para servidores offline
3. **Implementar eliminación de banners** cuando se quitan asignaciones (Caso 5)
4. **Agregar verificación post-cleanup** para confirmar que todos tienen el banner
5. **Considerar transacciones** para garantizar consistencia

---

## 🧪 Tests Manuales Recomendados

1. Upload con asignación específica → verificar que solo un servidor recibe
2. Edit específico → todos → verificar que todos reciben
3. Edit todos → específico → verificar que solo específicos reciben + verificar que otros tienen banner (problema conocido)
4. Eliminar banner físicamente → intentar editar → verificar manejo de error
5. Apagar un servidor → editar → verificar timeout y logs
