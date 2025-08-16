from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def handle_help(client, message):
    # Crear el teclado InlineKeyboardMarkup
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
    # Procesar las acciones de los botones
    data = callback_query.data

    if data == "help_1":
        await callback_query.message.edit_text(
            """
            Archivos:\n
**Responda a in mensaje y escriba los siguientes comandos**\n
`/compress`: Para comprimir su archivo en archivos 7z
`/rename: Nuevo Nombre.ext` Cambie el nombre del archivo
`/setsize 10`: Cambie el tamaño en MB de las partes en que `\compress` dividira su archivo.
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Archivos")

    elif data == "help_2":
        await callback_query.message.edit_text(
            """
            Correo:\n
**He aqui los comandos que usted puede usar relacionados al correo electrónico, usted puede enviar archivos desde Telegram a su correo, los archivos se autocomprimen a partes de menor tamaño si son muy grandes.**\n
`/setmail micorreo@ejemplo.con`: Establece su dirección para recibir archivos, un codigo sera generado y enviado a su correo para verificar su identidad
`/access Código`: Veifique su correo electrónico, si es un usuario de confianza este paso no es necesario
`/sendmail`: Esctiba este comando respondiendo sl mensaje que quiere enviar.
`/setmb 20`: Establece el tamaño de los archivos al auto comprimir (20 es el valor maximo)
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Correo")

    elif data == "help_3":
        await callback_query.message.edit_text(
            """Hentai:\n
**El bot es capaz de recopilar fotos de las web Nhentai y 3Hentai e enviarlas al chat como un archivo CBZ**\n
`/nh Code`: Descarga el código introducido
`/3h Code`: Descarga el código introducido
`/covernh Code`: Envia la primera foto del archivo al chat
`/cover3h Code`: Envia la primera foto del archivo al chat
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Hentai")

    elif data == "help_4":
        await callback_query.message.edit_text(
            """Videos\n
**En el bot estas son las opciones para los videos**\n
`/convert`: Convierte el video
`/calidad`: Edita los valores de la conversación, escriba el comando sin argumento para obtener ejemplo del uso.
`/cancel ID Tarea`: Cancela una Tarea en ejecución o futura de convertir, solo disponible para el creador de la tarea y admins
`/list`: Muestra la cola de tareas, solo disponible para admins y usuarios vip            
            """,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver", callback_data="help_back")]]
            )
        )
        await callback_query.answer("Mostrando Ayuda de Videos")

    elif data == "help_5":
        await callback_query.message.edit_text(
            """Imgchest:\n
**Con el bot usted podra almacenar fotos online en el servicio de Imgchest**\n
`/imgchest`: Escriba el comando en respuesta a una foto y el bot almacenará la imagen y le dara un link
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
        # Volver al menú principal de ayuda
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
