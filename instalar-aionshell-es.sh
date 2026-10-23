#!/usr/bin/env bash
# Copyright (c) 2026 Local Tech Lab. Todos los derechos reservados.
# Licencia: LICENSE (uso educativo no comercial).
set -euo pipefail

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  echo 'Uso: sudo bash instalar-aionshell-es.sh [modelo.argosmodel]'
  echo 'Instala AionShell ES de LocalTechLab en /opt/aionshell-es y /usr/local/bin.'
  echo 'Requiere Internet para dependencias y recursos de segmentación.'
  exit 0
fi
if (( $# > 1 )); then
  echo 'Se acepta como máximo un archivo .argosmodel.' >&2
  exit 1
fi
if [[ ${EUID} -ne 0 ]]; then
  echo 'Ejecuta el instalador con sudo; usa aionshell-es sin sudo.' >&2
  exit 1
fi

ORIGEN="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DESTINO=/opt/aionshell-es
MODELO=${1:-}
if [[ -n "$MODELO" && ! -f "$MODELO" ]]; then
  echo "No existe el modelo: $MODELO" >&2
  exit 1
fi
for archivo in aionshell-es.py glosario-tecnico.json requirements.txt scripts/preparar-modelos.py; do
  if [[ ! -f "$ORIGEN/$archivo" ]]; then
    echo "Falta $ORIGEN/$archivo" >&2
    exit 1
  fi
done
python3 - <<'PY'
import platform
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Se requiere Python 3.10 o posterior; probado con Python 3.13.')
if platform.system() != 'Linux' or platform.machine() != 'x86_64':
    raise SystemExit('Este instalador está preparado para Linux x86_64 con CPU.')
PY

mkdir -p "$DESTINO/modelos" /usr/local/bin
python3 -m venv "$DESTINO/venv" || {
  echo 'Instala primero: sudo apt install python3-venv' >&2
  exit 1
}
"$DESTINO/venv/bin/python" -m pip install \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -r "$ORIGEN/requirements.txt"

export ARGOS_PACKAGES_DIR="$DESTINO/modelos"
export ARGOS_DEVICE_TYPE=cpu
export ARGOS_COMPUTE_TYPE=int8
export ARGOS_CHUNK_TYPE=DEFAULT
"$DESTINO/venv/bin/python" "$ORIGEN/scripts/preparar-modelos.py" "$MODELO"

MARCA="$(date +%Y%m%d%H%M%S)-$$"
for archivo in "$DESTINO/aionshell-es.py" "$DESTINO/glosario-tecnico.json" /usr/local/bin/aionshell-es; do
  if [[ -e "$archivo" || -L "$archivo" ]]; then
    cp -a -- "$archivo" "$archivo.respaldo.$MARCA"
    echo "Respaldo: $archivo.respaldo.$MARCA"
  fi
done
install -m 0644 "$ORIGEN/aionshell-es.py" "$DESTINO/aionshell-es.py"
install -m 0644 "$ORIGEN/glosario-tecnico.json" "$DESTINO/glosario-tecnico.json"
LANZADOR="$(mktemp /usr/local/bin/.aionshell-es.XXXXXX)"
trap 'rm -f -- "$LANZADOR"' EXIT
cat > "$LANZADOR" <<'SH'
#!/bin/sh
export ARGOS_PACKAGES_DIR=/opt/aionshell-es/modelos
export ARGOS_DEVICE_TYPE=cpu
export ARGOS_COMPUTE_TYPE=int8
export ARGOS_CHUNK_TYPE=DEFAULT
exec /opt/aionshell-es/venv/bin/python /opt/aionshell-es/aionshell-es.py "$@"
SH
chmod 755 "$LANZADOR"
mv -f -- "$LANZADOR" /usr/local/bin/aionshell-es
chmod -R a+rX "$DESTINO/modelos"
"$DESTINO/venv/bin/python" -m pip check
/usr/local/bin/aionshell-es --diagnostico
printf '\nInstalación finalizada. Como usuario normal: aionshell-es nmap\n'
