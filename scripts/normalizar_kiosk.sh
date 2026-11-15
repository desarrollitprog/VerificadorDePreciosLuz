#!/bin/bash
# Normaliza la identidad de un kiosco (VM clonada de otra).
#
# Problemas que corrige:
#   - Hostname repetido (p.ej. "desarrolloit") entre VMs clonadas.
#   - machine-id duplicado (afecta a systemd, DHCP, algunas apps).
#   - MAC dinámica de Hyper-V (ESET la interpreta como ARP poisoning).
#
# Uso:
#   sudo ./normalizar_kiosk.sh <nuevo-hostname> [--reset-machine-id]
#
# Ejemplo:
#   sudo ./normalizar_kiosk.sh srv-luzcadash-chacao --reset-machine-id
#
# IMPORTANTE: después de cambiar machine-id, la identidad de Tailscale puede
# requerir re-login (sudo tailscale up). Ver docs/kioscos-identidad-red.md.
set -euo pipefail

NUEVO_HOST="${1:-}"
RESET_MACHINE_ID="${2:-}"

if [[ -z "$NUEVO_HOST" ]]; then
    echo "Uso: sudo $0 <nuevo-hostname> [--reset-machine-id]" >&2
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "Este script debe ejecutarse con sudo." >&2
    exit 1
fi

echo "== Identidad actual =="
hostnamectl 2>/dev/null | head -6 || true
echo "machine-id: $(cat /etc/machine-id 2>/dev/null || echo 'N/A')"

echo
echo "== Cambiando hostname a: $NUEVO_HOST =="
hostnamectl set-hostname "$NUEVO_HOST"
# Mantener /etc/hosts coherente (evita "sudo: unable to resolve host")
if grep -qE '^127\.0\.1\.1' /etc/hosts; then
    sed -i -E "s/^127\.0\.1\.1.*/127.0.1.1\t$NUEVO_HOST/" /etc/hosts
else
    echo -e "127.0.1.1\t$NUEVO_HOST" >> /etc/hosts
fi

if [[ "$RESET_MACHINE_ID" == "--reset-machine-id" ]]; then
    echo
    echo "== Regenerando machine-id =="
    cp -a /etc/machine-id "/etc/machine-id.bak.$(date +%Y%m%d%H%M%S)"
    : > /etc/machine-id
    if [[ -f /var/lib/dbus/machine-id ]]; then
        : > /var/lib/dbus/machine-id
        ln -sf /etc/machine-id /var/lib/dbus/machine-id
    fi
    systemd-machine-id-setup
    echo "nuevo machine-id: $(cat /etc/machine-id)"
    echo "NOTA: reinicia el equipo para aplicar la nueva identidad."
fi

echo
echo "== MAC actual de eth0 =="
ip link show eth0 | awk '/link\/ether/ {print $2}'
echo
echo "Siguiente paso (en el host Hyper-V, PowerShell como Administrador):"
echo "  Set-VMNetworkAdapter -VMName '<VM>' -StaticMacAddress '<MAC mostrada arriba>'"
echo "Ver docs/kioscos-identidad-red.md para el procedimiento completo."
