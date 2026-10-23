#!/usr/bin/env python3
# Copyright (c) 2026 Local Tech Lab. Todos los derechos reservados.
# Licencia: LICENSE (uso educativo no comercial).
"""AionShell ES de LocalTechLab: documentación traducida localmente con Argos.

No usa servicios de red durante la ejecución. El modelo en->es debe estar
instalado de antemano. Conserva las opciones, metavariables y ejemplos.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time

VERSION_CACHE = 'aionshell-es-2'
CACHE_HOME = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'aionshell-es'
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
BACKSPACE = re.compile(r'[^\n]\x08')
PROSA_TRAS_IDENTIFICADOR = re.compile(
    r'(?:is|are|was|were|has|have|does|can|may|will|passes|supports|uses|'
    r'reads|writes|provides|allows|requires|returns|transfers)\b')
# Son literales de sintaxis técnica. Nunca deben pasar por el modelo.
TOKENS = re.compile(
    r'`[^`\n]*`|'
    r'"--?[^"\n]+"|'
    r"\binfo\s+'[^'\n]+'|"
    r'\bgit help (?:[a-z][a-z-]*|<[^>\n]+>)|'
    r"(?<!\w)'[^'\n]+'(?!\w)|"
    r'\(-[A-Za-z0-9][A-Za-z0-9-]*\)|'
    r'(?<!\w)[*/=><@|]{2,}(?!\w)|'
    r'[A-Za-z][A-Za-z0-9+.-]*://[^\s<>]+|'
    r'<[^<>\n]{1,120}>|'
    r'\[[A-Za-z][A-Za-z0-9_-]*\]|'
    r'(?<![\w])--[A-Za-z][\w.-]*(?:=(?:<[^<>\n]{1,120}>|[^\s,;]+))?|'
    r'(?<![\w])-[A-Za-z0-9:#?][A-Za-z0-9-]*|'
    r'(?<!\w)(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?|'
    r'(?<!\w)[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+|'
    r'(?<!\w)/[A-Za-z0-9_./+-]+|'
    r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|'
    r'\b(?:User-Agent|IPv4|IPv6|TCP|UDP|SCTP|ICMP|DNS|HTTP|HTTPS|FTP|SOCKS4|XML|'
    r'GET|POST|PUT|DELETE|PATCH|OPTIONS|CONNECT|LIST|RETR|HELP|VRFY|'
    r'PROPFIND|COPY|MOVE|USER|PROTOCOLS|PROTOCOL|FORMAT|RANGE|RATE|HASHES|'
    r'URL|SSH|TLS|SSL|IMAP|POP3|SMTP|SFTP|SCP|TFTP|LDAP|'
    r'NSE|MAC|MTU|IDS|IP|shell|Shell|Bash|bash|'
    r'FILE|FILEs|FILES|PATTERN|PATTERNS|SIZE|WORD|WHEN|TYPE|ACTION|NUM|GLOB|SEP|LABEL|HEAD)\b'
)
TITULOS = {
    'USAGE': 'USO',
    'TARGET SPECIFICATION': 'ESPECIFICACIÓN DEL OBJETIVO',
    'HOST DISCOVERY': 'DESCUBRIMIENTO DE HOSTS',
    'SCAN TECHNIQUES': 'TÉCNICAS DE ESCANEO',
    'PORT SPECIFICATION AND SCAN ORDER': 'PUERTOS Y ORDEN DE ESCANEO',
    'SERVICE/VERSION DETECTION': 'DETECCIÓN DE SERVICIOS Y VERSIONES',
    'SCRIPT SCAN': 'ESCANEO DE SCRIPTS',
    'OS DETECTION': 'DETECCIÓN DEL SISTEMA OPERATIVO',
    'TIMING AND PERFORMANCE': 'TIEMPOS Y RENDIMIENTO',
    'FIREWALL/IDS EVASION AND SPOOFING': 'EVASIÓN Y SUPLANTACIÓN DE FIREWALL/IDS',
    'OUTPUT': 'SALIDA',
    'MISC': 'OTROS',
    'EXAMPLES': 'EJEMPLOS',
    'OPTIONS': 'OPCIONES',
    'COMMANDS': 'COMANDOS',
    'DESCRIPTION': 'DESCRIPCIÓN',
    'NAME': 'NOMBRE',
    'SYNOPSIS': 'SINOPSIS',
    'AUTHOR': 'AUTOR',
    'AUTHORS': 'AUTORES',
    'REPORTING BUGS': 'INFORMAR DE ERRORES',
    'SEE ALSO': 'VÉASE TAMBIÉN',
    'COPYRIGHT': 'DERECHOS DE AUTOR',
    'BUGS': 'ERRORES',
    'NOTES': 'NOTAS',
    'FILES': 'ARCHIVOS',
    'EXIT STATUS': 'ESTADO DE SALIDA',
    'ENVIRONMENT': 'ENTORNO',
}


def ayuda_comando(comando: str, opciones: list[str], segundos: int = 8) -> tuple[str, int]:
    ruta = shutil.which(comando)
    if not ruta:
        raise RuntimeError(f'No existe el ejecutable «{comando}» en PATH.')
    env = os.environ.copy()
    env.update({'LANG': 'C', 'LC_ALL': 'C', 'PAGER': 'cat', 'MANWIDTH': '100'})
    try:
        p = subprocess.run([ruta, *opciones], capture_output=True, text=True,
                           errors='replace', timeout=segundos, env=env)
    except subprocess.TimeoutExpired:
        return '', 124
    except OSError as e:
        raise RuntimeError(f'No se pudo ejecutar «{ruta}»: {e}') from e
    # Algunos programas escriben --help en stderr o terminan con código != 0.
    contenido = p.stdout if p.stdout.strip() else p.stderr
    return limpiar(contenido), p.returncode


def limpiar(texto: str) -> str:
    texto = ANSI.sub('', texto)
    while '\b' in texto and BACKSPACE.search(texto):
        texto = BACKSPACE.sub('', texto)
    return texto.replace('\r\n', '\n').replace('\r', '\n')


def obtener_manual_es(comando: str) -> str | None:
    """Lee el manual distribuido en español; nunca confunde el fallback inglés."""
    if not shutil.which('man'):
        raise RuntimeError('No está instalado man-db.')
    env = os.environ.copy()
    env.update({'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'LANGUAGE': 'es',
                'MANWIDTH': '100', 'GROFF_NO_SGR': '1', 'PAGER': 'cat',
                'MANPAGER': 'cat', 'MANOPT': ''})
    try:
        ubicacion = subprocess.run(['man', '-L', 'es', '-w', '--', comando],
                                   capture_output=True, text=True, errors='replace',
                                   timeout=15, env=env)
        rutas = ubicacion.stdout.strip().splitlines()
        if ubicacion.returncode or not rutas:
            return None
        # man -L es también puede resolver una página inglesa. Comprobar
        # el directorio de idioma antes de presentarla como español.
        if not any(re.fullmatch(r'es(?:_[A-Z]{2})?(?:\.[\w-]+)?', parte)
                   for parte in Path(rutas[0]).parts):
            return None
        pagina = subprocess.run(['man', '-L', 'es', '-P', 'cat', '--', comando],
                                capture_output=True, text=True, errors='replace',
                                timeout=15, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'No fue posible abrir el manual en español: {exc}') from exc
    if pagina.returncode or not pagina.stdout.strip():
        return None
    return limpiar(pagina.stdout)


def obtener_documentacion(comando: str, usar_man: bool, argumentos: list[str] | None = None) -> str:
    if usar_man and argumentos:
        raise RuntimeError('No se puede combinar --man con argumentos adicionales.')
    if argumentos:
        # Ejecutar SOLAMENTE formas explícitas de solicitud de ayuda, nunca escaneos.
        primero = argumentos[0]
        if not (primero in ('help', '-h', '--help', '-?', '--usage')
                or primero.startswith('--') and 'help' in primero):
            raise RuntimeError('Se aceptan únicamente argumentos de ayuda '                                '(p. ej. --script-help http-title).')
        contenido, codigo = ayuda_comando(comando, argumentos, 15)
        if contenido.strip() and (codigo == 0 or len(contenido) > 80):
            return contenido
        raise RuntimeError('Los argumentos indicados no produjeron documentación de ayuda.')
    if usar_man:
        if not shutil.which('man'):
            raise RuntimeError('No está instalado man-db.')
        env = os.environ.copy()
        env.update({'LANG': 'C', 'LC_ALL': 'C', 'LANGUAGE': 'C', 'MANWIDTH': '100',
                    'GROFF_NO_SGR': '1', 'PAGER': 'cat', 'MANPAGER': 'cat', 'MANOPT': ''})
        try:
            p = subprocess.run(['man', '-L', 'C', '-P', 'cat', '--', comando], capture_output=True,
                               text=True, errors='replace', timeout=15, env=env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f'No fue posible abrir man: {exc}') from exc
        if p.returncode != 0 or not p.stdout.strip():
            raise RuntimeError(f'No se encontró la página man de «{comando}».')
        return limpiar(p.stdout)
    for opt in ('--help', '-h'):
        contenido, codigo = ayuda_comando(comando, [opt])
        if len(contenido.strip()) > 80 or (contenido.strip() and codigo == 0):
            return contenido
    raise RuntimeError(f'No hay ayuda de «{comando}» en --help/-h. Prueba --man.')


def clave(texto: str, comando: str = '') -> str:
    huella = cargar_glosario()[1]
    return hashlib.sha256((VERSION_CACHE + '\0' + huella + '\0' + comando + '\0' + texto).encode('utf-8')).hexdigest()


def leer_cache(texto: str, comando: str = '') -> str | None:
    archivo = CACHE_HOME / (clave(texto, comando) + '.txt')
    try:
        return archivo.read_text(encoding='utf-8')
    except FileNotFoundError:
        return None


def guardar_cache(texto: str, salida: str, comando: str = '') -> None:
    CACHE_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    nombre = clave(texto, comando)
    final = CACHE_HOME / (nombre + '.txt')
    temporal = CACHE_HOME / (nombre + f'.{os.getpid()}.tmp')
    temporal.write_text(salida, encoding='utf-8')
    temporal.replace(final)


def obtener_motor():
    try:
        from argostranslate import translate
    except ImportError as exc:
        raise RuntimeError('Argos Translate no está instalado en este Python. '
                           'Ejecuta el instalador proporcionado.') from exc
    # Argos 1.11 no expone download_method de Stanza. El adaptador se
    # limita a este proceso; no modifica archivos de las dependencias.
    from argostranslate.sbd import StanzaSentencizer
    import stanza

    class StanzaLocal(StanzaSentencizer):
        def lazy_pipeline(self):
            if self.stanza_pipeline is None:
                self.stanza_pipeline = stanza.Pipeline(
                    lang=self.stanza_lang_code,
                    dir=str(self.pkg.package_path / 'stanza'),
                    processors='tokenize',
                    use_gpu=False,
                    download_method=None,
                    logging_level='ERROR',
                )
            return self.stanza_pipeline

    translate.StanzaSentencizer = StanzaLocal
    try:
        motor = translate.get_translation_from_codes('en', 'es')
    except Exception as exc:
        raise RuntimeError('No hay modelo inglés→español instalado en Argos Translate. '
                           'Instálalo una sola vez antes de usar el programa.') from exc
    if motor is None:
        raise RuntimeError('Argos Translate no tiene instalado el modelo en→es.')
    return motor


class MotorPerezoso:
    """No carga Argos si todo el documento es sintaxis o está en el glosario."""
    def __init__(self):
        self.motor = None

    def translate(self, texto: str) -> str:
        if self.motor is None:
            self.motor = obtener_motor()
        return self.motor.translate(texto)


@lru_cache(maxsize=128)
def glosario(comando: str) -> dict[str, str]:
    datos, _ = cargar_glosario()
    return {**datos.get('*', {}), **datos.get(Path(comando).name, {})}


@lru_cache(maxsize=1)
def cargar_glosario() -> tuple[dict, str]:
    contenido = Path(__file__).with_name('glosario-tecnico.json').read_bytes()
    try:
        datos = json.loads(contenido)
        if not isinstance(datos, dict) or any(
            not isinstance(nombre, str) or not isinstance(frases, dict) or any(
                not isinstance(origen, str) or not isinstance(destino, str) or
                not destino.strip() or '\n' in destino or '\r' in destino
                for origen, destino in frases.items())
            for nombre, frases in datos.items()
        ):
            raise ValueError('Se requieren diccionarios de frases de una sola línea.')
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f'El glosario técnico no es válido: {exc}') from exc
    return datos, hashlib.sha256(contenido).hexdigest()


def partir_por_dos_puntos_fuera_de_sintaxis(cadena: str) -> int:
    """Localiza los dos puntos que separan opción y explicación.

    Ignora los dos puntos de <host[:probeport]> y [argumento:opción].
    """
    stack = []
    cierre = {'<': '>', '[': ']', '{': '}', '(': ')'}
    for i, char in enumerate(cadena):
        if char in cierre:
            stack.append(cierre[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif char == ':' and not stack and (i + 1 == len(cadena) or cadena[i + 1].isspace()):
            return i
    return -1


def es_ejemplo(linea: str, comando: str) -> bool:
    t = linea.strip()
    # Ejemplos completos: nunca enviar al traductor.
    if re.match(r'(?i)^(ex:|e\.g\.:|examples?:|ejemplos?:)\s*\S+', t):
        return True
    if comando and re.match(r'^' + re.escape(Path(comando).name) + r'(?=\s|$)', t):
        resto = t[len(Path(comando).name):].lstrip()
        # El nombre del programa también puede iniciar una explicación,
        # como "curl passes on the verbatim string...".
        return not PROSA_TRAS_IDENTIFICADOR.match(resto)
    # No tocar ni URLs ni líneas con prompts de shell.
    if re.match(r'^(?:\$|#|>>>|\./)\s*\S+', t):
        return True
    return False


def traducir_fragmento(fragmento: str, motor, db: sqlite3.Connection,
                       renovar: bool, pendientes: dict[str, str] | None = None) -> str:
    if not re.search(r'[A-Za-z]{2}', fragmento):
        return fragmento
    # Conservar todos los espacios iniciales y finales, y no alterar los saltos de línea.
    antes = fragmento[:len(fragmento) - len(fragmento.lstrip())]
    despues = fragmento[len(fragmento.rstrip()):]
    texto = fragmento.strip()
    if not texto:
        return fragmento
    if pendientes is not None and texto in pendientes:
        return antes + pendientes[texto] + despues
    if not renovar:
        registro = db.execute('SELECT salida FROM segmentos WHERE origen=?', (texto,)).fetchone()
        if registro:
            return antes + registro[0] + despues
    try:
        traducido = motor.translate(texto)
    except Exception as exc:
        raise RuntimeError(f'Falló la traducción local de {texto[:70]!r}: {exc}') from exc
    if (not isinstance(traducido, str) or not traducido.strip()
            or '\n' in traducido or '\r' in traducido):
        raise RuntimeError(f'El motor devolvió una traducción inválida para {texto[:70]!r}.')
    traducido = traducido.strip()
    if pendientes is not None:
        pendientes[texto] = traducido
    else:
        db.execute('INSERT OR REPLACE INTO segmentos(origen,salida) VALUES (?,?)',
                   (texto, traducido))
    return antes + traducido + despues


@lru_cache(maxsize=128)
def patron_tokens(comando: str) -> re.Pattern:
    if not comando:
        return TOKENS
    nombre = Path(comando).name
    return re.compile(TOKENS.pattern + r'|(?<![\w-])' + re.escape(nombre) + r'(?![\w-])')


def traducir_descripcion(texto: str, motor, db: sqlite3.Connection,
                          renovar: bool, comando: str,
                          pendientes: dict[str, str] | None = None) -> str:
    # Los tokens sintácticos se separan: jamás se entregan al traductor.
    corregido = glosario(comando).get(' '.join(texto.split()))
    if corregido is not None:
        antes = texto[:len(texto) - len(texto.lstrip())]
        despues = texto[len(texto.rstrip()):]
        return antes + corregido + despues
    pat = patron_tokens(comando)
    salidas = []
    pos = 0
    for m in pat.finditer(texto):
        salidas.append(traducir_fragmento(texto[pos:m.start()], motor, db, renovar, pendientes))
        salidas.append(m.group())
        pos = m.end()
    salidas.append(traducir_fragmento(texto[pos:], motor, db, renovar, pendientes))
    return ''.join(salidas)


def traducir_linea(linea: str, comando: str, motor, db: sqlite3.Connection,
                    renovar: bool, pendientes: dict[str, str] | None = None) -> str:
    if not linea.strip():
        return linea
    # A diferencia de la traducción automática de bloques, aquí mantenemos
    # exactamente el número de líneas y la sintaxis técnica de cada opción.
    indent = linea[:len(linea) - len(linea.lstrip())]
    cuerpo = linea[len(indent):]
    columna = re.match(r'([a-z][a-z0-9_-]*\s{2,})(\S.*)', cuerpo)
    # Una categoría puede llamarse igual que el programa ("curl  The ...").
    # Una columna descriptiva no es un ejemplo de ejecución.
    if (columna and 0 < len(indent) <= 6
            and (columna[1].strip() != Path(comando).name
                 or ' '.join(columna[2].split()) in glosario(comando))):
        return indent + columna[1] + traducir_descripcion(
            columna[2], motor, db, renovar, comando, pendientes)
    if es_ejemplo(linea, comando):
        return linea
    if cuerpo.upper() in TITULOS:
        return indent + TITULOS[cuerpo.upper()]
    if re.match(r'(?i)^' + re.escape(Path(comando).name) + r'\s+\d', cuerpo):
        return linea  # ej.: Nmap 7.98 (https://nmap.org)
    if cuerpo.endswith(':'):
        ingles = cuerpo[:-1]
        if ingles.upper() in TITULOS:
            return indent + TITULOS[ingles.upper()] + ':'
    if cuerpo.upper() == 'MISC:':
        return indent + 'OTROS:'
    # Uso/Usage contiene gramática del CLI: no traducir el lado derecho.
    if re.match(r'(?i)^usage\s*:', cuerpo):
        return indent + re.sub(r'(?i)^usage\s*:', 'Uso:', cuerpo, count=1)
    if cuerpo.startswith('-'):
        prosa = re.match(r'^(?:--[\w.-]+|-[A-Za-z0-9:#?])\s+(.*)', cuerpo)
        if prosa and PROSA_TRAS_IDENTIFICADOR.match(prosa[1]):
            return indent + traducir_descripcion(cuerpo, motor, db, renovar, comando, pendientes)
        i = partir_por_dos_puntos_fuera_de_sintaxis(cuerpo)
        espacio = re.search(r'\s{2,}(?=\S)', cuerpo)
        if espacio is not None and (i < 0 or espacio.start() < i):
            # GNU y otras herramientas separan opción y descripción con
            # columnas, sin usar dos puntos. Conservar la columna de sintaxis.
            corte = espacio.end()
        elif i >= 0:
            corte = i + 1
        else:
            return linea
        return indent + cuerpo[:corte] + traducir_descripcion(
            cuerpo[corte:], motor, db, renovar, comando, pendientes)
    return indent + traducir_descripcion(cuerpo, motor, db, renovar, comando, pendientes)


def es_continuacion_uso(linea: str, comando: str) -> bool:
    """Distingue la gramática de uso de las opciones y la prosa que la siguen."""
    cuerpo = linea.lstrip()
    if not cuerpo:
        return False
    if re.match(r'^where\s+[A-Z]', cuerpo):
        return True
    if not linea[:1].isspace():
        return False
    if cuerpo.startswith('-'):
        # Una opción con descripción termina el bloque Usage, incluso
        # cuando curl no introduce una línea en blanco entre ambos.
        return (re.search(r'\s{2,}(?=\S)', cuerpo) is None
                and partir_por_dos_puntos_fuera_de_sintaxis(cuerpo) < 0)
    return bool(re.match(r'^(?:[\[<{(|]|[A-Z][A-Z0-9_]*\s*[:=]|or:\s)', cuerpo)
                or comando and re.match(
                    re.escape(Path(comando).name) + r'(?=\s|$)', cuerpo))


def actualizar_delimitadores_uso(linea: str, pendientes: list[str]) -> None:
    """Mantiene los grupos de una gramática Usage que continúan en otra línea."""
    cierre = {'[': ']', '{': '}', '(': ')', '<': '>'}
    for char in linea:
        if char in cierre:
            pendientes.append(cierre[char])
        elif pendientes and char == pendientes[-1]:
            pendientes.pop()


def traducir_ayuda(original: str, comando: str, refrescar: bool,
                  progreso: bool = False) -> str:
    if not refrescar:
        desde_cache = leer_cache(original, comando)
        if desde_cache is not None:
            return desde_cache
    # Importación perezosa: la cache completa NO carga el modelo (muy rápida).
    if progreso:
        print('Preparando traducción automática local; los manuales largos pueden tardar.',
              file=sys.stderr, flush=True)
    motor = MotorPerezoso()
    CACHE_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    huella = cargar_glosario()[1][:12]
    db = sqlite3.connect(CACHE_HOME / f'segmentos-{VERSION_CACHE}-{huella}.sqlite3', timeout=15)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS segmentos('
                   'origen TEXT PRIMARY KEY, salida TEXT NOT NULL)')
        partes = original.splitlines(keepends=True)
        salida = []
        pendientes: dict[str, str] = {}
        bloque_uso = False
        delimitadores_uso: list[str] = []
        ultimo_aviso = time.monotonic()
        for numero, linea in enumerate(partes, 1):
            sin_fin = linea.rstrip('\r\n')
            terminador = linea[len(sin_fin):]
            if re.match(r'(?i)^\s*usage\s*:', sin_fin):
                bloque_uso = True
                delimitadores_uso.clear()
                actualizar_delimitadores_uso(sin_fin, delimitadores_uso)
            elif bloque_uso:
                if sin_fin.strip() and (delimitadores_uso or es_continuacion_uso(sin_fin, comando)):
                    actualizar_delimitadores_uso(sin_fin, delimitadores_uso)
                    salida.append(linea)
                    continue
                bloque_uso = False
                delimitadores_uso.clear()
            salida.append(traducir_linea(sin_fin, comando, motor, db, refrescar, pendientes)
                          + terminador)
            if progreso and time.monotonic() - ultimo_aviso >= 2:
                print(f'Traduciendo: {numero}/{len(partes)} líneas',
                      file=sys.stderr, flush=True)
                ultimo_aviso = time.monotonic()
        resultado = ''.join(salida)
        # No mantener un bloqueo de escritura durante la inferencia del
        # modelo. Guardar todos los segmentos en una transacción breve.
        db.executemany('INSERT OR REPLACE INTO segmentos(origen,salida) VALUES (?,?)',
                       pendientes.items())
        db.commit()
        guardar_cache(original, resultado, comando)
        return resultado
    finally:
        db.close()


def main() -> int:
    p = argparse.ArgumentParser(prog='aionshell-es', description=(
        'Consulta manuales en español o traduce documentación EN→ES con un modelo local.'))
    p.add_argument('comando', nargs='?', help='Ejemplo: nmap, git, ip, grep')
    p.add_argument('--man', action='store_true', help='Leer el manual; preferir su versión en español')
    p.add_argument('--automatico', action='store_true',
                   help='Traducir el manual inglés aunque exista uno en español')
    p.add_argument('--archivo', type=Path, help='Traducir un archivo de texto local')
    p.add_argument('--original', action='store_true', help='Mostrar el texto fuente sin traducción')
    p.add_argument('--refresh', action='store_true', help='Regenerar traducción y caché')
    p.add_argument('--diagnostico', action='store_true', help='Verificar motor local y caché')
    p.add_argument('--tiempo', action='store_true', help='Mostrar duración de ejecución')
    # Los parámetros después de -- pertenecen al comando consultado.
    argv = sys.argv[1:]
    if '--' in argv:
        separador = argv.index('--')
        argumentos = argv[separador + 1:]
        args = p.parse_args(argv[:separador])
    else:
        argumentos = []
        args = p.parse_args(argv)
    if args.man and not args.comando:
        p.error('--man necesita un comando; ejemplo: aionshell-es --man nmap')
    if args.man and argumentos:
        p.error('No se puede combinar --man con argumentos adicionales.')
    if args.archivo and (args.man or argumentos):
        p.error('--archivo no se puede combinar con --man ni argumentos adicionales.')
    if args.automatico and not args.man:
        p.error('--automatico requiere --man.')
    if args.automatico and args.original:
        p.error('--automatico y --original son opciones incompatibles.')
    if args.diagnostico:
        print('Backend: Argos Translate local; llamadas HTTP del script: ninguna')
        print(f'Caché: {CACHE_HOME}')
        try:
            from argostranslate import package, settings
            print(f'Directorio de modelos: {settings.package_data_dir}')
            print(f'Tipo de fragmentación: {os.environ.get("ARGOS_CHUNK_TYPE", "DEFAULT")}')
            instalados = [(pkg.from_code, pkg.to_code)
                          for pkg in package.get_installed_packages()]
            print(f'Paquetes detectados: {instalados}')
            if os.environ.get('ARGOS_CHUNK_TYPE', '').upper() == 'NONE':
                print('AVISO: ARGOS_CHUNK_TYPE=NONE puede impedir cargar traducciones; '
                      'usa DEFAULT.', file=sys.stderr)
            try:
                muestra = obtener_motor().translate('This is a local translation test.')
                if not muestra.strip():
                    raise RuntimeError('El motor devolvió una traducción vacía.')
            except Exception as exc:
                raise RuntimeError(f'No se pudo completar la traducción de prueba: {exc}') from exc
            print('Modelo inglés→español: instalado y disponible')
            print(f'Prueba de traducción: {muestra}')
            return 0
        except (RuntimeError, ImportError, OSError) as e:
            print(f'Modelo: NO disponible ({e})', file=sys.stderr)
            return 1
    if not args.comando and not args.archivo:
        p.print_help()
        return 0
    if args.comando and args.archivo:
        p.error('Usa un comando O --archivo, no ambos.')
    t0 = time.monotonic()
    try:
        if args.man and not args.original and not args.automatico:
            manual = obtener_manual_es(args.comando)
            if manual is not None:
                print(f'--- Manual local en español: {args.comando} ---\n')
                print(manual, end='' if manual.endswith('\n') else '\n')
                if args.tiempo:
                    print(f'\nTiempo: {time.monotonic() - t0:.3f} s', file=sys.stderr)
                return 0
            print('No hay un manual local en español; se traducirá el manual inglés.',
                  file=sys.stderr, flush=True)
        if args.archivo:
            fuente = args.archivo.read_text(encoding='utf-8')
            etiqueta = args.archivo.name
        else:
            fuente = obtener_documentacion(args.comando, args.man, argumentos)
            etiqueta = args.comando + ((' ' + ' '.join(argumentos)) if argumentos else '')
        if args.original:
            print(fuente, end='' if fuente.endswith('\n') else '\n')
            return 0
        resultado = traducir_ayuda(fuente, args.comando or '', args.refresh, progreso=True)
        print(f'--- Traducción automática local al español: {etiqueta} ---\n')
        print(resultado, end='' if resultado.endswith('\n') else '\n')
        if args.tiempo:
            print(f'\nTiempo: {time.monotonic() - t0:.3f} s', file=sys.stderr)
        return 0
    except (RuntimeError, OSError, UnicodeError, sqlite3.Error) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
