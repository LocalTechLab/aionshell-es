"""Comprobaciones sin descargar ni cargar modelos de traducción."""
import importlib.util
import contextlib
import io
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'ayuda_es', Path(__file__).resolve().parents[1] / 'aionshell-es.py')
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class MotorFalso:
    def __init__(self):
        self.entradas = []

    def translate(self, texto):
        self.entradas.append(texto)
        return 'texto traducido'


class PruebasAyuda(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE segmentos (origen TEXT PRIMARY KEY, salida TEXT)')
        self.motor = MotorFalso()

    def test_opcion_con_dos_puntos_internos(self):
        entrada = '  -b <host[:probeport]>: Use this host\n'
        salida = app.traducir_linea(entrada.rstrip('\n'), 'nmap', self.motor, self.db, False)
        self.assertEqual(salida, '  -b <host[:probeport]>: texto traducido')
        self.assertEqual(self.motor.entradas, ['Use this host'])

    def test_tokens_fuera_del_traductor(self):
        entrada = 'Connect with --help at https://example.org using <PORT> or IPv6'
        salida = app.traducir_descripcion(entrada, self.motor, self.db, False, 'nmap')
        for token in ['--help', 'https://example.org', '<PORT>', 'IPv6']:
            self.assertIn(token, salida)
            self.assertNotIn(token, ' '.join(self.motor.entradas))

    def test_ejemplo_y_uso_conservan_sintaxis(self):
        ejemplo = '  nmap -sV -p 443 127.0.0.1'
        self.assertEqual(app.traducir_linea(ejemplo, 'nmap', self.motor, self.db, False), ejemplo)
        self.assertEqual(app.traducir_linea('Usage: nmap [options] <target>', 'nmap',
                                          self.motor, self.db, False),
                         'Uso: nmap [options] <target>')
        self.assertEqual(self.motor.entradas, [])

    def test_rechaza_argumentos_que_no_solicitan_ayuda(self):
        with patch.object(app, 'ayuda_comando') as ejecutar:
            with self.assertRaises(RuntimeError):
                app.obtener_documentacion('nmap', False, ['-sS', '127.0.0.1'])
            ejecutar.assert_not_called()

    def test_cache_completa_no_carga_motor(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(app, 'CACHE_HOME', Path(tmp)), patch.object(app, 'obtener_motor') as motor:
                app.guardar_cache('Source text', 'Texto guardado', 'nmap')
                self.assertEqual(app.traducir_ayuda('Source text', 'nmap', False), 'Texto guardado')
                motor.assert_not_called()

    def test_error_del_motor_no_se_guarda_en_cache(self):
        with patch.object(self.motor, 'translate', side_effect=OSError('modelo ausente')):
            with self.assertRaises(RuntimeError):
                app.traducir_fragmento('Some text', self.motor, self.db, False)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM segmentos').fetchone()[0], 0)

    def test_opciones_en_columnas_se_traducen(self):
        entrada = '  -a, --all                  do not ignore hidden files'
        salida = app.traducir_linea(entrada, 'ls', self.motor, self.db, False)
        self.assertEqual(salida, '  -a, --all                  texto traducido')
        self.assertEqual(self.motor.entradas, ['do not ignore hidden files'])

    def test_columna_tiene_prioridad_sobre_dos_puntos_en_descripcion(self):
        entrada = '  --file=FILE   read file: then continue'
        salida = app.traducir_linea(entrada, 'tool', self.motor, self.db, False)
        self.assertEqual(salida, '  --file=FILE   texto traducido')

    def test_subcomando_no_se_traduce(self):
        entrada = '   clone     Clone a repository into a new directory'
        self.assertEqual(app.traducir_linea(entrada, 'git', self.motor, self.db, False),
                         '   clone     Clona un repositorio en un directorio nuevo')
        self.assertEqual(self.motor.entradas, [])

    def test_titulos_sin_dos_puntos(self):
        self.assertEqual(app.traducir_linea('SYNOPSIS', 'true', self.motor, self.db, False), 'SINOPSIS')
        self.assertEqual(self.motor.entradas, [])

    def test_shell_y_comando_info_se_conservan(self):
        entrada = "Your shell supports info '(coreutils) true invocation'"
        salida = app.traducir_descripcion(entrada, self.motor, self.db, False, 'true')
        self.assertIn('shell', salida)
        self.assertIn("info '(coreutils) true invocation'", salida)
        self.assertNotIn('shell', ' '.join(self.motor.entradas))

    def test_man_sin_comando_da_error_util(self):
        error = io.StringIO()
        with patch.object(sys, 'argv', ['aionshell-es', '--man']), contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as salida:
                app.main()
        self.assertEqual(salida.exception.code, 2)
        self.assertIn('aionshell-es --man nmap', error.getvalue())

    def test_manual_ingles_no_se_etiqueta_como_espanol(self):
        english = subprocess.CompletedProcess([], 0, '/usr/share/man/man1/git.1.gz\n', '')
        with patch.object(app.shutil, 'which', return_value='/usr/bin/man'):
            with patch.object(app.subprocess, 'run', return_value=english) as ejecutar:
                self.assertIsNone(app.obtener_manual_es('git'))
                self.assertEqual(ejecutar.call_count, 1)

    def test_manual_espanol_se_lee_sin_motor(self):
        ruta = subprocess.CompletedProcess([], 0, '/usr/share/man/es/man1/nmap.1.gz\n', '')
        pagina = subprocess.CompletedProcess([], 0, 'NOMBRE\nHerramienta de redes\n', '')
        salida = io.StringIO()
        with patch.object(sys, 'argv', ['aionshell-es', '--man', 'nmap']):
            with patch.object(app.shutil, 'which', return_value='/usr/bin/man'):
                with patch.object(app.subprocess, 'run', side_effect=[ruta, pagina]):
                    with patch.object(app, 'obtener_motor') as motor, contextlib.redirect_stdout(salida):
                        self.assertEqual(app.main(), 0)
                        motor.assert_not_called()
        self.assertIn('Manual local en español', salida.getvalue())
        self.assertIn('Herramienta de redes', salida.getvalue())

    def test_argumentos_incompatibles_no_se_ignoran(self):
        for argv in [['--man', 'nmap', '--archivo', 'texto.txt'],
                     ['--archivo', 'texto.txt', '--', '--help'],
                     ['--automatico', 'nmap']]:
            with self.subTest(argv=argv), patch.object(sys, 'argv', ['aionshell-es', *argv]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    app.main()
                self.assertEqual(error.exception.code, 2)

    def test_cache_separa_el_contexto_de_comandos(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'CACHE_HOME', Path(tmp)):
            app.guardar_cache('same source', 'resultado uno', 'uno')
            self.assertEqual(app.leer_cache('same source', 'uno'), 'resultado uno')
            self.assertIsNone(app.leer_cache('same source', 'dos'))

    def test_refresh_reutiliza_segmentos_dentro_de_la_misma_consulta(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'CACHE_HOME', Path(tmp)):
            with patch.object(app, 'obtener_motor', return_value=self.motor):
                salida = app.traducir_ayuda('Repeated text\nRepeated text\n', 'demo', True)
        self.assertEqual(self.motor.entradas, ['Repeated text'])
        self.assertEqual(salida, 'texto traducido\ntexto traducido\n')

    def test_no_bloquea_sqlite_mientras_traduce(self):
        pendientes = {}
        app.traducir_fragmento('First fragment', self.motor, self.db, True, pendientes)
        app.traducir_fragmento('Second fragment', self.motor, self.db, True, pendientes)
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(len(pendientes), 2)

    def test_sintaxis_de_uso_multilinea_no_se_traduce(self):
        texto = ('Usage: ip [ OPTIONS ] OBJECT\n'
                 'where OBJECT := { address | route | link }\n'
                 '       OPTIONS := { -4 | -6 }\n\nDescription text\n')
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'CACHE_HOME', Path(tmp)):
            with patch.object(app, 'obtener_motor', return_value=self.motor):
                salida = app.traducir_ayuda(texto, 'ip', True)
        self.assertIn('where OBJECT := { address | route | link }', salida)
        self.assertIn('       OPTIONS := { -4 | -6 }', salida)
        self.assertEqual(self.motor.entradas, ['Description text'])

    def test_documento_de_sintaxis_no_carga_argos(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'CACHE_HOME', Path(tmp)):
            with patch.object(app, 'obtener_motor') as cargar:
                app.traducir_ayuda('Usage: ip [ OPTIONS ]\n       -4 | -6\n', 'ip', True)
                cargar.assert_not_called()

    def test_correcciones_tecnicas_de_sentido(self):
        casos = [
            ('git', 'Clone a repository into a new directory', 'Clona un repositorio en un directorio nuevo'),
            ('grep', 'likewise, but follow all symlinks', 'Hace lo mismo, pero sigue todos los enlaces simbólicos'),
            ('grep', 'PATTERNS are strings', 'PATTERNS son cadenas de texto'),
            ('true', 'There is NO WARRANTY, to the extent permitted by law.',
             'NO SE OFRECE NINGUNA GARANTÍA, en la medida permitida por la ley.'),
            ('nmap', 'Ping Scan - disable port scan',
             'Descubrimiento de equipos mediante ping: desactiva el sondeo de puertos'),
        ]
        for cmd, origen, esperado in casos:
            with self.subTest(cmd=cmd):
                self.assertEqual(app.traducir_descripcion(origen, self.motor, self.db, False, cmd), esperado)
        self.assertEqual(self.motor.entradas, [])

    def test_glosario_preserva_opciones_y_metavariables(self):
        datos, _ = app.cargar_glosario()
        for comando, frases in datos.items():
            for origen, destino in frases.items():
                with self.subTest(comando=comando, origen=origen):
                    for token in app.TOKENS.findall(origen):
                        if token in ('e.g', 'i.e'):
                            continue  # Abreviaturas de prosa, no sintaxis técnica.
                        self.assertIn(token, destino)


if __name__ == '__main__':
    unittest.main()
