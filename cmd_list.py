from pyrogram.types import BotCommand
import asyncio

async def lista_cmd(app):
    await app.set_bot_commands([
        BotCommand("start", "Comprobar actividad"),
        BotCommand("help", "Tutorial de comandos"),
        BotCommand("setsize", "Defina el tamaño en Mb para /compress"),
        BotCommand("compress", "Comprimir un archivo en partes"),
        BotCommand("split", "Dividir un archivo en partes"),
        BotCommand("rename", "Cambia el nombre de un archivo"),
        BotCommand("convert", "Convierte un video"),
        BotCommand("calidad", "Ajusta la calidad de /convert"),
        BotCommand("setmail", "Configure su correo para usar /send"),
        BotCommand("setdelay", "Configure el delay del correo"),
        BotCommand("setmb", "Configure el peso de las partes"),
        BotCommand("sendmail", "Envía un archivo dividido en 7z a su correo"),
        BotCommand("sendmailb", "Envía un archivo dividido en bytes a su correo"),
        BotCommand("upfile", "Sube un archivo al servidor"),
        BotCommand("clearfiles", "Borra los archivos en el servidor"),
        BotCommand("verify", "Verifica tu correo con un código"),
        BotCommand("setfile", "Define su preferencia de descarga de Hentai"),
        BotCommand("nh", "Descarga un manga hentai de Nhentai"),
        BotCommand("3h", "Descarga un manga hentai de 3Hentai"),
        BotCommand("covernh", "Obtener info de un manga hentai de Nhentai"),
        BotCommand("cover3h", "Obtener info de un manga hentai de 3Hentai"),
        BotCommand("hito", "Descarga un manga hentai de Hitomila"),
        BotCommand("scan", "Escanea los links dentro de un link indicando"),
        BotCommand("resumecodes", "Extrae codigos Hentai de archivos txt del scan"),
        BotCommand("resumetxtcodes", "Extrae codigos Hentai y los envia en txt"),
        BotCommand("codesplit", "Divide la cantidas de códigos en un txt"),
        BotCommand("imgchest", "Publica una imagen en Imgchest"),
        BotCommand("access", "Obten acceso al bot mediante una contraseña"),
        BotCommand("settings", "(admin) configura el bot"),
        BotCommand("edituser", "(admin) controla el acceso al bot")
    ])
