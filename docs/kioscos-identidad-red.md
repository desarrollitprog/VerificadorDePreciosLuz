# Identidad y red de los kioscos (VMs Hyper-V)

Las VMs de kiosco (`srv-luzcadash-00` … `srv-luzcadash-10`) fueron clonadas y
comparten hostname, `machine-id` y claves SSH. Eso provoca:

- **ESET** marcando la IP del kiosco como *ARP/CachePoisoningAttack* cuando
  Hyper-V le asigna una MAC nueva (bloquea ERP: `Login timeout expired`).
- **Tailscale** con nodos duplicados/“offline” y claves expiradas.
- **SSH** con `REMOTE HOST IDENTIFICATION HAS CHANGED` al reconectar.

## 1. MAC estática en Hyper-V (lo más importante)

En el host Hyper-V, PowerShell como Administrador:

```powershell
# Ver la MAC actual de cada VM
Get-VMNetworkAdapter -VMName "srv-luzcadash-01" | Select-Object VMName, MacAddress

# Fijarla (usar la MAC actual de cada VM, son únicas)
Set-VMNetworkAdapter -VMName "srv-luzcadash-01" -StaticMacAddress "00155D0ADC03"
```

Repetir por cada VM. Con esto la MAC nunca vuelve a cambiar al recrear/restaurar
la VM y ESET deja de interpretar el cambio como suplantación.

> Si se clona una VM nueva: asignar una MAC estática **distinta** antes de
> encenderla.

## 2. Hostname y machine-id únicos

En la consola de la VM (o por SSH):

```bash
cd /home/desarrolloit/VerificadorDePreciosLuz
sudo ./scripts/normalizar_kiosk.sh srv-luzcadash-chacao --reset-machine-id
sudo reboot
```

Luego de reiniciar, revalidar Tailscale:

```bash
sudo tailscale status          # verificar que NO diga "Logged out"
sudo tailscale up              # si pide autenticación
sudo tailscale status | head -3
```

## 3. ESET en el servidor base (ERP)

En ESET Server Security del servidor de la sede:

1. **Solución de problemas de acceso a la red → Dispositivos remotos**:
   seleccionar la IP del kiosco → **Permitir / Agregar a confianza**.
2. **Firewall → Configuración avanzada → Detección de intrusiones**:
   desactivar *“Detección de envenenamiento de caché ARP”* para la red local
   (o marcar `192.168.0.0/24` como red de confianza).

## 4. Verificación

Desde el kiosco:

```bash
ping -c 2 <IP_ERP>
timeout 3 bash -c "echo > /dev/tcp/<IP_ERP>/1433" && echo ERP_OK
curl -s localhost:8000/ping
curl -s localhost:8000/consultar/7591098800281
```

Debe responder un JSON con `pvp_base` distinto de `null`.

## 5. SSH: host key repetida

Si aparece `REMOTE HOST IDENTIFICATION HAS CHANGED`, en el equipo desde el que
te conectas (solo si confías en el cambio, p.ej. tras reinstalar la VM):

```powershell
ssh-keygen -R 192.168.0.221
```

## Notas

- Las VMs comparten la misma host key SSH porque fueron clonadas. Regenerarlas
  (`sudo ssh-keygen -A` + reiniciar `ssh`) es opcional pero recomendable para
  evitar advertencias y facilitar auditorías.
- Documentar en el inventario: sede → VM → MAC estática → IP LAN → IP Tailscale.
