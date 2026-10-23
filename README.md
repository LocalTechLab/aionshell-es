# AionShell ES · Local Tech Lab

**Documentación de comandos Linux en español, con traducción local y enfoque educativo.**

AionShell ES forma parte de mi trabajo como creador de contenido en
**Local Tech Lab**, donde desarrollo y comparto herramientas educativas para
la comunidad de habla hispana, con especial atención a Linux, administración
de sistemas y ciberseguridad.

**Este trabajo se realizó dentro de Local Tech Lab.** Su objetivo es acercar
la documentación técnica a quienes están aprendiendo y conectar la práctica
con el contenido educativo del laboratorio.

📺 [YouTube · @LocalTechLab-d7e](https://www.youtube.com/@LocalTechLab-d7e)

Repositorio oficial de la organización [Local Tech Lab](https://github.com/LocalTechLab).

## Qué ofrece

- Ayuda de comandos y páginas de manual en español desde la terminal.
- Preferencia por los manuales en español ya instalados en el sistema.
- Traducción automática inglés→español con Argos Translate, un modelo local y CPU.
- Glosario técnico y caché para reutilizar traducciones.
- Consulta del texto original y traducción de archivos de texto locales.

Las consultas funcionan localmente tras instalar las dependencias y los modelos.
No necesitan claves de API ni servicios de traducción en la nube. La instalación
inicial sí necesita Internet.

## Instalación

Probado en Debian 13, Linux x86_64, Python 3.13.5. Descarga e instala desde GitHub:

```bash
sudo apt install git python3-venv man-db manpages-es
git clone https://github.com/LocalTechLab/aionshell-es.git
cd aionshell-es
sudo bash instalar-aionshell-es.sh
aionshell-es --diagnostico
aionshell-es --man git
```

El programa que quieras consultar también debe estar instalado. La instalación
inicial necesita Internet para las dependencias y los modelos; la traducción
posterior funciona localmente, sin APIs de IA.

El instalador crea `/opt/aionshell-es` y `/usr/local/bin/aionshell-es`. Las dependencias
quedan en un entorno virtual. No instala un servicio ni modifica el Python del sistema.
Si ya existe el programa o el lanzador, guarda copias con sufijo `.respaldo.FECHA-PID`.
Los modelos se guardan en `/opt/aionshell-es/modelos`; cada usuario tiene su propia
caché en `~/.cache/aionshell-es` o en la ruta indicada por `XDG_CACHE_HOME`.

Puede proporcionarse un modelo Argos local:

```bash
sudo bash instalar-aionshell-es.sh /ruta/modelo.argosmodel
```

Esta opción sigue necesitando conexión para instalar dependencias y preparar los
recursos compatibles de Stanza. No es un instalador completamente sin conexión.

## Uso

Ejecuta las consultas como usuario normal, sin `sudo`:

| Objetivo | Comando |
| --- | --- |
| Leer la ayuda de Git en español | `aionshell-es git` |
| Consultar su manual | `aionshell-es --man git` |
| Ver el texto original | `aionshell-es --original git` |
| Traducir el manual inglés, aunque exista uno en español | `aionshell-es --man git --automatico` |
| Traducir un archivo local | `aionshell-es --archivo ayuda.txt` |
| Regenerar una traducción automática | `aionshell-es --refresh git` |
| Comprobar el motor local | `aionshell-es --diagnostico` |
| Consultar todas las opciones | `aionshell-es --help` |

También puedes medir la duración o consultar ayuda específica de un programa
instalado, como Nmap:

```bash
aionshell-es nmap --tiempo
aionshell-es nmap -- --script-help http-title
```

### Ayuda de curl

```bash
aionshell-es curl
aionshell-es curl -- --help all
aionshell-es curl -- --help category
aionshell-es curl -- --help http
aionshell-es curl -- --help --request
aionshell-es --original curl -- --help all
```

El glosario incluye las descripciones de las 269 opciones de `curl 8.14.1`,
sus 25 categorías y los fragmentos de la ayuda detallada de `--request` probados
con esa versión. Se conservan los nombres de opciones, categorías, métodos HTTP
y ejemplos. Estas consultas se resuelven sin cargar el modelo cuando todos sus
fragmentos coinciden con el glosario.

Otras versiones, opciones detalladas o disposiciones del texto pueden contener
frases distintas y utilizar el traductor local. La cobertura del glosario no
equivale a una revisión de todo el manual de curl.

El programa consultado debe estar instalado. `--man` necesita el nombre de un comando,
`man-db` y la página correspondiente: `aionshell-es --man nmap`. Si el sistema dispone
de un manual en español, se muestra directamente, sin cargar el modelo. Si no existe,
se traduce el manual inglés y se muestra el avance por stderr. `--automatico` fuerza
esta segunda ruta; `--original` permite consultar el texto inglés. `--refresh` solo
regenera traducciones automáticas, no modifica los manuales del sistema.

## Uso en clase y límites conocidos

La herramienta ejecuta el programa elegido para obtener su ayuda; úsala con
ejecutables y argumentos de confianza. No constituye un entorno aislado.

La salida indica si es un manual del sistema o una traducción automática. Los manuales
localizados pueden ir por detrás de la versión instalada. La traducción automática
puede contener errores y no se garantiza que sea perfecta: compara dudas con
`--original` y revisa el material antes de usarlo en clase.

Se conservan la sintaxis de uso, las opciones y los ejemplos reconocidos. Las
descripciones de opciones separadas por columnas también se traducen. Algunos términos,
valores de opciones y fragmentos de gramática se dejan en inglés deliberadamente.

`glosario-tecnico.json` contiene correcciones explícitas de frases observadas, como
clonar repositorios, enlaces simbólicos o la ausencia de garantía. Solo se aplican
cuando coincide la frase de origen; no representan una traducción universal. El glosario
debe revisarse al preparar el material de clase. Cambiarlo invalida la caché al
reiniciar el comando, mediante su huella SHA-256.

La caché distingue comandos y versiones. Los segmentos repetidos se reutilizan incluso
durante una regeneración. SQLite se escribe al terminar la traducción para evitar
mantener bloqueos durante la inferencia. Los documentos que solo contienen sintaxis
o frases del glosario no cargan el modelo.

## Comprobaciones

Las pruebas rápidas no necesitan Argos ni conexión:

```bash
python3 -m unittest discover -s tests -v
bash -n instalar-aionshell-es.sh
shellcheck instalar-aionshell-es.sh
```

La última comprobación requiere tener instalado ShellCheck.

Después de instalar, comprueba una traducción nueva sin red. En Linux, desde una
cuenta normal con `sudo`, los siguientes comandos crean un espacio de red independiente
y ejecutan las consultas como tu usuario. Este ejemplo requiere tener instalado Nmap:

```bash
sudo unshare --net runuser -u "$(id -un)" -- aionshell-es nmap --refresh --tiempo
sudo unshare --net runuser -u "$(id -un)" -- aionshell-es --man nmap --tiempo
aionshell-es nmap --tiempo
```

No se desconecta la red del resto del equipo. Esta prueba requiere que el sistema
permita crear espacios de nombres de red.

## Revisión y mantenimiento

El proyecto incluye 35 pruebas unitarias y un flujo de GitHub Actions para comprobar
la sintaxis y ejecutar las pruebas. Estas comprobaciones no sustituyen la validación
de una instalación completa en el equipo de destino.

`requirements.txt` fija las dependencias directas; `requirements-lock.txt` registra
las versiones completas del entorno probado en Debian 13 con Python 3.13.
La compatibilidad con otras plataformas no está verificada.

Las revisiones independientes de seguridad siguen pendientes: las pruebas funcionales
y de traducción no constituyen una certificación ni eliminan el riesgo de ejecutar
programas externos para obtener sus mensajes de ayuda.

## Licencia y propiedad intelectual

**Copyright © 2026 Local Tech Lab. Todos los derechos reservados.**
La [Licencia de Uso Educativo Local Tech Lab v1.0](LICENSE) autoriza clonar,
instalar, estudiar y modificar privadamente el código con fines no comerciales.
**No permite vender ni redistribuir versiones del software** sin permiso escrito.
No es una licencia de código abierto aprobada por OSI.

Las licencias de Argos Translate, Stanza, PyTorch, sus modelos y otros contenidos
de terceros son independientes. Este repositorio no incluye sus modelos ni binarios.
Consulta además [NOTICE.md](NOTICE.md) y [SECURITY.md](SECURITY.md).

