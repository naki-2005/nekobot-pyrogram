from pyrogram.types import BotCommand
import asyncio

async def lista_cmd(app):
    await app.set_bot_commands([
        # 🟢 Comandos generales
        BotCommand("start", "Comprobar actividad"),
        BotCommand("help", "Tutorial de comandos"),
        BotCommand("mydata", "Muestra el perfil del usuario"),

        # 📦 Gestión de archivos
        BotCommand("setsize", "Defina el tamaño en Mb para /compress"),
        BotCommand("compress", "Comprimir un archivo en partes"),
        BotCommand("split", "Dividir un archivo en partes"),
        BotCommand("rename", "Cambia el nombre de un archivo"),
        BotCommand("upfile", "Sube un archivo al servidor"),
        BotCommand("listfiles", "Mostrar lista de archivos en el servidor"),
        BotCommand("sendfile", "Subir un archivo almacenado en el servidor"),
        BotCommand("clearfiles", "Borra los archivos en el servidor"),

        # 🎥 Multimedia
        BotCommand("convert", "Convierte un video"),
        BotCommand("calidad", "Ajusta la calidad de /convert"),

        # 📧 Envío por correo
        BotCommand("setmail", "Configure su correo para usar /send"),
        BotCommand("verify", "Verifica tu correo con un código"),
        BotCommand("setdelay", "Configure el delay del correo"),
        BotCommand("setmb", "Configure el peso de las partes"),
        BotCommand("sendmail", "Envía un archivo dividido en 7z a su correo"),
        BotCommand("sendmailb", "Envía un archivo dividido en bytes a su correo"),

        # 🔍 Búsqueda de contenido
        BotCommand("manga", "Busca un manga para descargar"),
        BotCommand("nyaa", "Busca en Nyaa Torrents"),
        BotCommand("nyaa18", "Busca algo en Nyaa Torrents (+18)"),
        BotCommand("magnet", "Descarga un enlace magnet"),
        BotCommand("megadl", "Descarga un enlace de Mega"),

        # 🍥 Contenido hentai
        BotCommand("setfile", "Define su preferencia de descarga de Hentai"),
        BotCommand("searchnh", "Obten hasta 25 resultados de una busqueda en Nhentai"),
        BotCommand("nh", "Descarga un manga hentai de Nhentai"),
        BotCommand("3h", "Descarga un manga hentai de 3Hentai"),
        BotCommand("covernh", "Obtener info de un manga hentai de Nhentai"),
        BotCommand("cover3h", "Obtener info de un manga hentai de 3Hentai"),
        BotCommand("hito", "Descarga un manga hentai de Hitomila"),

        # 🧠 Procesamiento de códigos
        BotCommand("scan", "Escanea los links dentro de un link indicando"),
        BotCommand("resumecodes", "Extrae codigos Hentai de archivos txt del scan"),
        BotCommand("resumetxtcodes", "Extrae codigos Hentai y los envia en txt"),
        BotCommand("codesplit", "Divide la cantidas de códigos en un txt"),

        # 🖼️ Imágenes
        BotCommand("imgchest", "Publica una imagen en Imgchest"),

        # 🔐 Comandos de administración
        BotCommand("settings", "(owner) configura el bot"),
        BotCommand("edituser", "(admin) controla el acceso al bot")
    ])
