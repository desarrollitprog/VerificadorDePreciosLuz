async def verificar_banner_existe_en_api_con_retry(api_url: str, banner_id: int, timeout: int = 15) -> dict:
    """
    Verifica si un banner existe en un backend-api específico CON RETRY.
    """
    try:
        response = await retry_with_backoff(
            _verificar_banner_check_internal,
            api_url, banner_id, timeout
        )
        return {"exists": response.status_code == 200, "status_code": response.status_code}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"exists": False, "status_code": 404}
        return {"exists": False, "status_code": e.response.status_code, "error": str(e)}
    except Exception as e:
        return {"exists": False, "status_code": 0, "error": str(e)}


# ============================================================
# FASE 6: Cambio de Asignación con Cleanup
# ============================================================

async def limpiar_banner_de_servidor(
    api_url: str,
    banner_id: int,
    timeout: int = 30
) -> dict:
    """
    Envía un PUT para limpiar las asignaciones de un banner en un servidor específico.
    Esto establece dispositivo_ids="" (vacío), lo que significa "todos" en backend-api.
    Para ELIMINAR un banner de un servidor específico, usar después de verificar.
    
    Args:
        api_url: URL del backend-api
        banner_id: ID del banner
        timeout: Timeout para la petición
        
    Returns:
        {"success": True/False, "api_url": ..., "error": ...}
    """
    update_url = f"{api_url.rstrip('/')}/banners/{banner_id}"
    data = {"dispositivo_ids": ""}  # Vacío = limpiar asignaciones específicas
    
    log.info("limpiando_banner_de_servidor", api_url=api_url, banner_id=banner_id, data=data)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.put(update_url, data=data)
            log.info("limpiando_banner_respuesta", api_url=api_url, banner_id=banner_id, status_code=response.status_code)
            response.raise_for_status()
            return {"success": True, "api_url": api_url, "response": response.json()}
    except Exception as e:
        log.error("limpiando_banner_error", api_url=api_url, banner_id=banner_id, error=str(e))
        return {"success": False, "api_url": api_url, "error": str(e)}


async def obtener_servidores_con_banner(
    banner_id: int,
    servidores: list,
    timeout: int = 35
) -> list:
    """
    Obtiene la lista de servidores que SÍ tienen un banner específico (PARALELO).
    
    Args:
        banner_id: ID del banner
        servidores: Lista de servidores a verificar
        timeout: Timeout para cada verificación
        
    Returns:
        Lista de servidores que tienen el banner
    """
    async def _verificar_servidor(servidor: dict) -> dict:
        api_url = servidor.get("api_url")
        if not api_url:
            ip = servidor.get("ip")
            if ip:
                api_url = f"http://{ip}:8000"
        
        if not api_url:
            log.warning("servidor_sin_api_url", servidor_id=servidor.get("id"), nombre=servidor.get("nombre"))
            return {"servidor": servidor, "tiene_banner": None}
        
        result = await verificar_banner_existe_en_api(api_url, banner_id, timeout)
        tiene = result.get("exists", False)
        
        log.info("verificacion_servidor", servidor_id=servidor.get("id"), nombre=servidor.get("nombre"),
                api_url=api_url, tiene_banner=tiene, status_code=result.get("status_code"))
        
        return {"servidor": servidor, "tiene_banner": tiene, "api_url": api_url}
    
    if not servidores:
        log.warning("sin_servidores_para_verificar", banner_id=banner_id)
        return []
    
    log.info("iniciando_verificacion_paralela", banner_id=banner_id, total_servidores=len(servidores), timeout=timeout)
    
    results = await asyncio.gather(
        *[_verificar_servidor(srv) for srv in servidores],
        return_exceptions=True
    )
    
    servidores_con_banner = []
    errores = []
    for result in results:
        if isinstance(result, Exception):
            log.error("error_en_verificacion", error=str(result))
            errores.append({"error": str(result)})
            continue
            
        if result.get("tiene_banner"):
            servidores_con_banner.append(result["servidor"])
            log.info("servidor_tiene_banner", servidor_id=result["servidor"].get("id"),
                    nombre=result["servidor"].get("nombre"))
    
    log.info("verificacion_completa", banner_id=banner_id,
            total_verificados=len(servidores),
            srv_tienen_banner=len(servidores_con_banner),
            errores=len(errores))
    
    return servidores_con_banner


async def procesar_cambio_asignacion(
    banner_id: int,
    servidores_disponibles: list,
    servidores_asignados_nuevos: list,
    banner_data: dict,
    timeout: int = 35
) -> dict:
    """
    Procesa el cambio de asignación de un banner manejando Cleanup.
    
    1. Verifica qué servidores tienen el banner actualmente
    2. Calcula diferencias (agregar, eliminar, actualizar)
    3. Ejecuta las acciones correspondientes
    
    Args:
        banner_id: ID del banner
        servidores_disponibles: Lista de todos los servidores disponibles
        servidores_asignados_nuevos: Lista de servidores objetivo (donde debe estar)
        banner_data: Datos del banner {file_path, titulo, tipo, activo, prioridad, ...}
        timeout: Timeout para operaciones paralelo
        
    Returns:
        {
            "exito": True/False,
            "agregados": [...],
            "eliminados": [...],
            "actualizados": [...],
            "errores": [...]
        }
    """
    log.info("iniciando_proceso_cambio_asignacion", banner_id=banner_id,
            total_srv_disponibles=len(servidores_disponibles),
            srv_asignados_nuevos=len(servidores_asignados_nuevos))
    
    # Determinar IDs de servidores nuevos
    nuevos_ids = set(s.get("id") for s in servidores_asignados_nuevos)
    
    # 1. Verificar servidores actuales (paralelo)
    log.info("verificando_servidores_actuales", banner_id=banner_id, timeout=timeout)
    srv_con_banner = await obtener_servidores_con_banner(banner_id, servidores_disponibles, timeout)
    
    # Obtener IDs de servidores que tienen el banner
    anteriores_ids = set(s.get("id") for s in srv_con_banner)
    
    log.info("resultado_verificacion", banner_id=banner_id,
            srv_tienen_banner=len(anteriores_ids),
            srv_tienen_ids=list(anteriores_ids))
    
    # 2. Calcular diferencias
    srv_a_agregar_ids = nuevos_ids - anteriores_ids  # Nuevos que no tienen el banner
    srv_a_eliminar_ids = anteriores_ids - nuevos_ids  # Antiguos que deben perder
    srv_a_actualizar_ids = nuevos_ids & anteriores_ids  # En ambos = actualizar
    
    log.info("calculo_diferencias", banner_id=banner_id,
            agregar=len(srv_a_agregar_ids),
            eliminar=len(srv_a_eliminar_ids),
            actualizar=len(srv_a_actualizar_ids))
    
    # 3. Preparar listas de servidores
    servidores_a_agregar = [s for s in servidores_asignados_nuevos if s.get("id") in srv_a_agregar_ids]
    servidores_a_eliminar = [s for s in srv_con_banner if s.get("id") in srv_a_eliminar_ids]
    servidores_a_actualizar = [s for s in servidores_asignados_nuevos if s.get("id") in srv_a_actualizar_ids]
    
    agregados = []
    eliminados = []
    actualizados = []
    errores = []
    
    # 4. Ejecutar acciones
    
    # A) AGREGAR: Replicar banner a servidores nuevos
    if servidores_a_agregar:
        log.info("iniciando_replicacion", banner_id=banner_id, cantidad=len(servidores_a_agregar))
        
        replication_results = await replicar_banner_completo_a_servidores(
            banner_data=banner_data,
            servidores=servidores_a_agregar,
            timeout=timeout
        )
        
        for res in replication_results:
            if res.get("success"):
                agregados.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url")
                })
            else:
                errores.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url"),
                    "error": res.get("error"),
                    "tipo": "agregar"
                })
        
        if errores:
            log.error("errores_en_agregar", banner_id=banner_id, cantidad=len(errores))
            return {"exito": False, "errores": errores}
    
    # B) ELIMINAR: Limpiar asignaciones de servidores que deben perder
    if servidores_a_eliminar:
        log.info("iniciando_limpieza", banner_id=banner_id, cantidad=len(servidores_a_eliminar))
        
        async def _limpiar_un_servidor(servidor: dict) -> dict:
            api_url = servidor.get("api_url")
            if not api_url:
                ip = servidor.get("ip")
                if ip:
                    api_url = f"http://{ip}:8000"
            
            result = await limpiar_banner_de_servidor(api_url, banner_id, timeout)
            return {
                "servidor_id": servidor.get("id"),
                "servidor_nombre": servidor.get("nombre"),
                "api_url": api_url,
                "success": result.get("success", False),
                "error": result.get("error")
            }
        
        cleanup_results = await asyncio.gather(
            *[_limpiar_un_servidor(srv) for srv in servidores_a_eliminar],
            return_exceptions=True
        )
        
        for res in cleanup_results:
            if isinstance(res, Exception):
                errores.append({"error": str(res), "tipo": "eliminar"})
                continue
                
            if res.get("success"):
                eliminados.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url")
                })
            else:
                errores.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url"),
                    "error": res.get("error"),
                    "tipo": "eliminar"
                })
        
        if errores:
            log.error("errores_en_eliminar", banner_id=banner_id, cantidad=len(errores))
            return {"exito": False, "errores": errores}
    
    # C) ACTUALIZAR: Actualizar datos en servidores que mantienen
    if servidores_a_actualizar:
        log.info("iniciando_actualizacion", banner_id=banner_id, cantidad=len(servidores_a_actualizar))
        
        # Extraer dispositivo_ids nuevos si existen
        device_ids_nuevos = banner_data.get("dispositivo_ids")
        
        update_results = await actualizar_banner_en_asignaciones(
            banner_id=banner_id,
            servidores=servidores_a_actualizar,
            titulo=banner_data.get("titulo"),
            tipo=banner_data.get("tipo"),
            activo=banner_data.get("activo"),
            prioridad=banner_data.get("prioridad"),
            fecha_inicio=banner_data.get("fecha_inicio"),
            fecha_fin=banner_data.get("fecha_fin"),
            duracion_seg=banner_data.get("duracion_seg"),
            dispositivo_ids=device_ids_nuevos,
            timeout=timeout
        )
        
        for res in update_results:
            if res.get("success"):
                actualizados.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url")
                })
            else:
                errores.append({
                    "servidor_id": res.get("servidor_id"),
                    "servidor_nombre": res.get("servidor_nombre"),
                    "api_url": res.get("api_url"),
                    "error": res.get("error"),
                    "tipo": "actualizar"
                })
        
        if errores:
            log.error("errores_en_actualizar", banner_id=banner_id, cantidad=len(errores))
            return {"exito": False, "errores": errores}
    
    # Resultado final
    resultado = {
        "exito": len(errores) == 0,
        "agregados": agregados,
        "eliminados": eliminados,
        "actualizados": actualizados,
        "errores": errores
    }
    
    log.info("proceso_cambio_asignacion_completo", banner_id=banner_id,
            exito=resultado["exito"],
            agregados=len(agregados),
            eliminados=len(eliminados),
            actualizados=len(actualizados),
            errores=len(errores))
    
    return resultado