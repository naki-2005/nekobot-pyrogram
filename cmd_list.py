from pyrogram.types import BotCommand

async def lista_cmd(app):
    await app.set_bot_commands([
        BotCommand("start", "Comprobar actividad"),
        BotCommand("setsize", "Defina el tamaño en Mb para /compress"),
        BotCommand("compress", "Comprimir un archivo en partes"),
        BotCommand("rename", "Cambia el nombre de un archivo"),
        BotCommand("convert", "Convierte un video"),
        BotCommand("calidad", "Ajusta la calidad de /convert"),
        BotCommand("setmail", "Configure su correo para usar /send"),
        BotCommand("sendmail", "Envía un archivo a su correo"),
        BotCommand("verify", "Verifica tu correo con un código"),
        BotCommand("setfile", "Define su preferencia de descarga de Hentai"),
        BotCommand("nh", "Descarga un manga hentai de Nhentai"),
        BotCommand("3h", "Descarga un manga hentai de 3Hentai"),
        BotCommand("covernh", "Obtener info de un manga hentai de Nhentai"),
        BotCommand("cover3h", "Obtener info de un manga hentai de 3Hentai"),
        BotCommand("scan", "Escanea los links dentro de un link indicando"),
        BotCommand("resumecodes", "Extrae codigos Hentai de archivos txt del scan"),
        BotCommand("imgchest", "Publica una imagen en Imgchest"),
        BotCommand("access", "Obten acceso al bot mediante una contraseña"),
        BotCommand("adduser", "Permite a un usuario usar el bot (admin)"),
        BotCommand("remuser", "Quita el acceso (admin)"),
        BotCommand("addchat", "Permite al chat actual el uso del bot (admin)"),
        BotCommand("remchat", "Quita el acceso (admin)"),
        BotCommand("ban", "Banea a un usuario (admin)"),
        BotCommand("unban", "Desbanea a un usuario (admin)")
    ])
