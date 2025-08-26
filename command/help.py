from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def handle_help(client, message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Archivos", callback_data="help_1")],
            [InlineKeyboardButton("Correo", callback_data="help_2")],
            [InlineKeyboardButton("Hentai", callback_data="help_3")],
            [InlineKeyboardButton("Videos", callback_data="help_4")],
            [InlineKeyboardButton("Imgchest", callback_data="help_5")]
        ]
    )
    await message.reply_text(
        "Selecciona una opción para obtener más ayuda:",
        reply_markup=keyboard
    )

async def handle_help_callback(client, callback_query):
    data = callback_query.data

    if data == "help_1":
        await callback_query.message.edit_text(
            """
📁 *Archivos*

Responda a un mensaje y escriba los siguientes comandos:

`/compress` — Comprime el archivo en partes 7z  
`/rename: NuevoNombre.ext` — Cambia el nombre del archivo  
`/setsize 10` — Cambia el tamaño en MB de las partes en que `\\compress` dividirá su archivo
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Archivos")

    elif data == "help_2":
        await callback_query.message.edit_text(
            """
📧 *Correo*

Comandos disponibles para enviar archivos desde Telegram a tu correo.  
Los archivos se autocomprimen si son muy grandes:

`/setmail micorreo@ejemplo.com` — Establece tu dirección de correo  
`/access Código` — Verifica tu correo (opcional para usuarios de confianza)  
`/sendmail` — Escribe este comando respondiendo al mensaje que deseas enviar  
`/setmb 20` — Establece el tamaño máximo en MB para la compresión automática (máximo: 20)
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Correo")

    elif data == "help_3":
        await callback_query.message.edit_text(
            """
🔞 *Hentai*

El bot puede recopilar imágenes desde Nhentai y 3Hentai y enviarlas como archivo CBZ:

`/nh Código` — Descarga el contenido de Nhentai  
`/3h Código` — Descarga el contenido de 3Hentai  
`/covernh Código` — Envía la portada del archivo Nhentai  
`/cover3h Código` — Envía la portada del archivo 3Hentai
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Hentai")

    elif data == "help_4":
        await callback_query.message.edit_text(
            """
🎬 *Videos*

Opciones disponibles para manejo de videos:

`/convert` — Convierte el video  
`/calidad` — Edita los valores de conversión (sin argumentos muestra ejemplos)  
`/cancel ID_Tarea` — Cancela una tarea (solo admins o creador)  
`/list` — Muestra la cola de tareas (solo admins y usuarios VIP)
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Videos")

    elif data == "help_5":
        await callback_query.message.edit_text(
            """
🖼️ *Imgchest*

Permite almacenar imágenes en línea usando el servicio Imgchest:

`/imgchest` — Responde a una imagen con este comando para subirla y recibir el enlace
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda Imgchest")

    elif data == "help_6":
        await callback_query.message.edit_text(
            "Texto de Ayuda 6:\nExplicación relacionada con la tercera opción.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda 6.")

    elif data == "help_back":
        await callback_query.message.edit_text(
            "Selecciona una opción para obtener más ayuda:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Archivos", callback_data="help_1")],
                    [InlineKeyboardButton("Correo", callback_data="help_2")],
                    [InlineKeyboardButton("Hentai", callback_data="help_3")],
                    [InlineKeyboardButton("Videos", callback_data="help_4")],
                    [InlineKeyboardButton("Imgchest", callback_data="help_5")]
                ]
            )
        )
        await callback_query.answer("Regresando al menú principal.")
