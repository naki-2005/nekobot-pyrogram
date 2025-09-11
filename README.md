```markdown
# 🐾 Neko Bot

Bot de Telegram multifuncional con herramientas para:

- 📦 Gestión de archivos
- 📧 Envío por correo
- 🎥 Conversión de video
- 🔍 Búsqueda de contenido
- 🍥 Descarga de manga hentai
- 🧲 Descarga de enlaces Torrent/Magnet
- 🖼️ Publicación de imágenes

No requiere configuración manual en BotFather: los comandos se registran automáticamente al iniciar.

---

## 🚀 Instalación rápida

```bash
git clone https://github.com/nakigeplayer/nekobot-pyrogram
cd nekobot-pyrogram
pip install -r requirements.txt
```

---

## ⚙️ Cómo iniciar el bot

### Opción 1: Ejecutar directamente `neko.py`

```bash
python3 neko.py -a API_ID -H API_HASH -b GIT_API -r GIT_REPO -t TOKEN
```

#### Argumentos disponibles:
- `-a` → API ID de Telegram (obtenido en [my.telegram.org](https://my.telegram.org))
- `-H` → API HASH asociado
- `-b` → API del repositorio de comandos (puede ser tu GitHub API)
- `-r` → URL del repositorio con los comandos
- `-t` → Token del bot (si usas sesión de bot)
- `-ss` → SESSION_STRING (si usas sesión de usuario)
- `-id` → USER_ID (requerido si usas SESSION_STRING)
- `-owner` → *(opcional pero recomendado)* ID del propietario del bot
- `-w` → *(opcional)* Enlace web del bot

---

### Opción 2: Usar `start.sh`

Este script lanza un servidor HTTP y ejecuta el bot automáticamente con las variables de entorno definidas.

```bash
./start.sh
```

#### Variables necesarias:
```env
API_ID=...           # API ID de Telegram
API_HASH=...         # API HASH de Telegram
TOKEN=...            # Token del bot (o SESSION_STRING + USER_ID)
SESSION_STRING=...   # (opcional) sesión de usuario
USER_ID=...          # (requerido si usas SESSION_STRING)
GIT_API=...          # API para acceder al repositorio
GIT_REPO=...         # URL del repositorio con comandos
```

#### Variables opcionales:
```env
OWNER=...            # ID del propietario del bot
WEB_LINK=...         # Enlace web del bot
```

---

## 🔐 Uso del argumento `-owner` y el comando `/settings`

Aunque `-owner` es opcional, **se recomienda usarlo en la primera ejecución** para habilitar el acceso al comando `/settings`, exclusivo para el propietario del bot.

Este comando permite configurar el comportamiento del bot directamente desde Telegram:

- `/settings` → Abre el panel de configuración si eres el owner
- `/settings public` → Activa o desactiva el modo público del bot
- `/settings protect` → Activa o desactiva la protección de contenido (bloquea reenvío)
- `/settings web <usuario> <contraseña>` → Guarda credenciales para acceso web
- `/settings web reload` → Recarga configuración web desde GitHub
- `/settings copy <bot_id>` → Copia configuración de otro bot
- `/settings mail <correo> <contraseña> <servidor>` → Configura el correo del bot
- `/settings imgapi <clave>` → Guarda la API de Imgchest

Este sistema permite restringir funciones a ciertos usuarios o abrir el bot a todos, según tus necesidades.

---

## 📦 Comandos del bot

### 🟢 Generales
- `/start` — Comprobar actividad  
- `/help` — Tutorial de comandos  
- `/mydata` — Muestra el perfil del usuario  

### 📦 Gestión de archivos
- `/setsize` — Defina el tamaño en Mb para /compress  
- `/compress` — Comprimir un archivo en partes  
- `/split` — Dividir un archivo en partes  
- `/rename` — Cambia el nombre de un archivo  
- `/upfile` — Sube un archivo al servidor  
- `/listfiles` — Mostrar lista de archivos en el servidor  
- `/sendfile` — Subir un archivo almacenado en el servidor  
- `/clearfiles` — Borra los archivos en el servidor  

### 🎥 Multimedia
- `/convert` — Convierte un video  
- `/calidad` — Ajusta la calidad de /convert  

### 📧 Envío por correo
- `/setmail` — Configure su correo para usar /send  
- `/verify` — Verifica tu correo con un código  
- `/setdelay` — Configure el delay del correo  
- `/setmb` — Configure el peso de las partes  
- `/sendmail` — Envía un archivo dividido en 7z a su correo  
- `/sendmailb` — Envía un archivo dividido en bytes a su correo  

### 🔍 Búsqueda de contenido
- `/manga` — Busca un manga para descargar  
- `/nyaa` — Busca en Nyaa Torrents  
- `/nyaa18` — Busca algo en Nyaa Torrents (+18)  
- `/magnet` — Descarga un enlace magnet  
- `/megadl` — Descarga un enlace de Mega  

### 🍥 Contenido hentai
- `/setfile` — Define su preferencia de descarga de Hentai  
- `/nh` — Descarga un manga hentai de Nhentai  
- `/3h` — Descarga un manga hentai de 3Hentai  
- `/covernh` — Obtener info de un manga hentai de Nhentai  
- `/cover3h` — Obtener info de un manga hentai de 3Hentai  
- `/hito` — Descarga un manga hentai de Hitomi.la  

### 🧠 Procesamiento de códigos
- `/scan` — Escanea los links dentro de un link indicado  
- `/resumecodes` — Extrae códigos Hentai de archivos txt del scan  
- `/resumetxtcodes` — Extrae códigos Hentai y los envía en txt  
- `/codesplit` — Divide la cantidad de códigos en un txt  

### 🖼️ Imágenes
- `/imgchest` — Publica una imagen en Imgchest  

### 🔐 Administración
- `/settings` — *(owner)* configura el bot  
- `/edituser` — *(admin)* controla el acceso al bot  

---

## ☁️ Deploy en Render

Puedes desplegar el bot fácilmente en Render con solo un clic:

[![Deploy en Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/blueprint/new?repo=https%3A%2F%2Fgithub.com%2Fnakigeplayer%2Fnekobot-pyrogram)
```
