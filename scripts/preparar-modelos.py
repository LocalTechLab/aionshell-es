#!/usr/bin/env python3
# Copyright (c) 2026 Local Tech Lab. Todos los derechos reservados.
# Licencia: LICENSE (uso educativo no comercial).
"""Descarga los recursos durante la instalación, antes del uso sin red."""
from pathlib import Path
import shutil
import sys

from argostranslate import package
from packaging.version import Version
import stanza


def main() -> None:
    archivo = sys.argv[1] if len(sys.argv) > 1 else ''
    if archivo:
        package.install_from_path(Path(archivo).resolve())
    instalados = [p for p in package.get_installed_packages()
                  if p.from_code == 'en' and p.to_code == 'es']
    if not instalados:
        if archivo:
            raise SystemExit('El archivo proporcionado no contiene un modelo en→es.')
        package.update_package_index()
        candidatos = [p for p in package.get_available_packages()
                      if p.from_code == 'en' and p.to_code == 'es']
        if not candidatos:
            raise SystemExit('El índice de Argos no contiene un modelo en→es.')
        modelo = max(candidatos, key=lambda p: Version(p.package_version))
        package.install_from_path(modelo.download())
        instalados = [p for p in package.get_installed_packages()
                      if p.from_code == 'en' and p.to_code == 'es']

    for modelo in instalados:
        # El modelo en_es 1.0 incluye recursos antiguos de Stanza.
        # Prepararlos aquí evita descargas y escrituras al consultar ayuda.
        destino = modelo.package_path / 'stanza'
        destino.mkdir(exist_ok=True)
        recursos = destino / 'resources.json'
        respaldo = destino / 'resources.json.antes-localtechlab'
        if recursos.exists() and not respaldo.exists():
            shutil.copy2(recursos, respaldo)
        try:
            stanza.Pipeline(lang='en', dir=str(destino), processors='tokenize',
                            use_gpu=False, download_method=None, logging_level='ERROR')
        except Exception:
            print('Preparando los recursos de segmentación que faltan o son incompatibles...')
            stanza.Pipeline(lang='en', dir=str(destino), processors='tokenize',
                            use_gpu=False, logging_level='WARNING')
        print(f'Modelo en→es {modelo.package_version}: recursos locales preparados')


if __name__ == '__main__':
    main()
