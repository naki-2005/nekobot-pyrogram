import os
import time
import shutil
import py7zr
import smtplib
from email.message import EmailMessage
import random
from data.vars import admin_users, vip_users, video_limit, PROTECT_CONTENT
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
part_queue = {}              # Cola de partes por usuario para envío manual
# Diccionarios para almacenar información de los usuarios
user_emails = {}
verification_storage = {}
user_limits = {}
user_delays = {}
exceeded_users = []

async def mail_query(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if user_id not in part_queue:
        await callback_query.answer("No hay partes en cola.", show_alert=True)
        return

    if data == "send_next_part":
        queue = part_queue[user_id]
        parts = queue["parts"]
        email = queue["email"]
        index = queue["index"]
        total = queue["total"]

        if index >= total:
            await callback_query.message.edit_text("Todas las partes fueron enviadas.")
            del part_queue[user_id]
            return

        part = parts[index]
        asunto = f"Parte {os.path.basename(part)} de {total}"
        try:
            send_email(email, asunto, adjunto=part)
            await callback_query.message.reply(f"Parte {os.path.basename(part)} enviada correctamente.")
            os.remove(part)
            queue["index"] += 1
        except Exception as e:
            await callback_query.message.reply(f"Error al enviar la parte {os.path.basename(part)}: {e}")
    
    elif data.startswith("auto_delay_"):
        delay_value = int(data.replace("auto_delay_", ""))
        part_queue[user_id]["delay"] = delay_value
        await callback_query.message.edit_text(f"Envío automático activado con {delay_value} segundos de espera.")
        await start_auto_send(client, user_id)

    elif data == "cancel_send":
        del part_queue[user_id]
        await callback_query.message.edit_text("Envío cancelado por el usuario.")

    elif data == "no_action":
        await callback_query.answer("Este botón es decorativo 😎", show_alert=False)
        
# Función para generar un código de verificación de 6 números
def generate_verification_code():
    return f"{random.randint(100000, 999999)}"

# Función para establecer el límite de MAIL_MB para un usuario
async def set_mail_limit(client, message):
    user_id = message.from_user.id
    try:
        new_limit = int(message.text.split(' ', 1)[1])
        if new_limit < 1:
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIF02fm3-XonvGhnnaVYCwO-y71UhThAAJuOgAC4KOCB77pR2Nyg3apHgQ"
            )
            time.sleep(3)
            await message.reply("¿Qué haces pendejo?")
            return
        if new_limit > 20:
            if user_id in exceeded_users:
                await client.send_sticker(
                    chat_id=message.chat.id,
                    sticker="CAACAgIAAxkBAAIF02fm3-XonvGhnnaVYCwO-y71UhThAAJuOgAC4KOCB77pR2Nyg3apHgQ"
                )
                time.sleep(3)
                await message.reply("¿Qué haces pendejo? 20 es el límite.")
                return
            else:
                exceeded_users.append(user_id)
                new_limit = 20
        user_limits[user_id] = new_limit
        await message.reply(f"El límite personal del usuario ha sido cambiado a {new_limit} MB.")
    except ValueError:
        await message.reply("Por favor, proporciona un número válido como límite.")

async def set_mail_delay(client, message):
    user_id = message.from_user.id
    try:
        new_limit = int(message.text.split(' ', 1)[1])
        if new_limit < 1:
            await client.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAIF02fm3-XonvGhnnaVYCwO-y71UhThAAJuOgAC4KOCB77pR2Nyg3apHgQ"
            )
            time.sleep(3)
            await message.reply("¿Qué haces pendejo?")
            return
        if new_limit > 300:
            if user_id in exceeded_users:
                await client.send_sticker(
                    chat_id=message.chat.id,
                    sticker="CAACAgIAAxkBAAIF02fm3-XonvGhnnaVYCwO-y71UhThAAJuOgAC4KOCB77pR2Nyg3apHgQ"
                )
                time.sleep(3)
                await message.reply("¿Qué haces pendejo? Eso no llegaría nunca.")
                return
            else:
                exceeded_users.append(user_id)
                new_limit = 300
        user_delays[user_id] = new_limit
        time.sleep(4)
        await message.reply(f"El tiempo de espera personal del usuario entre el envio de partes ha sido cambiado a {new_limit} segundos.")
    except ValueError:
        await message.reply("Por favor, proporciona un número válido como límite.")
        
# Función para obtener el límite de MAIL_MB para un usuario
def get_mail_limit(user_id):
    return user_limits.get(user_id, int(os.getenv('MAIL_MB', 20)))
def get_user_delay(user_id):
    return user_delays.get(user_id, int(os.getenv('MAIL_DELAY', 30)))


def send_email(destino, asunto, contenido=None, adjunto=False):
    import os
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = f"Neko Bot <{os.getenv('MAILDIR')}>"
    msg['To'] = destino

    if adjunto:
        with open(adjunto, 'rb') as f:
            msg.add_attachment(
                f.read(),
                maintype='application',
                subtype='octet-stream',
                filename=os.path.basename(adjunto)
            )
    else:
        msg.set_content(contenido if contenido else asunto)

    server_details = os.getenv('MAIL_SERVER').split(':')
    smtp_host = server_details[0]
    smtp_port = int(server_details[1])
    security_enabled = len(server_details) > 2 and server_details[2].lower() == 'tls'

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if security_enabled:
            server.starttls()
        server.login(os.getenv('MAILDIR'), os.getenv('MAILPASS'))
        server.send_message(msg)
        
async def set_mail(client, message):
    email = message.text.split(' ', 1)[1]
    user_id = message.from_user.id
    mail_confirmed = os.getenv('MAIL_CONFIRMED')
    if user_id in admin_users:
        user_emails[user_id] = email
        await message.reply("Correo electrónico registrado automáticamente porque eres el administrador de bot")
        return
    if mail_confirmed:
        confirmed_users = {
            item.split('=')[0]: item.split('=')[1].split(';') 
            for item in mail_confirmed.split(',')
        }
        if str(user_id) in confirmed_users and email in confirmed_users[str(user_id)]:
            user_emails[user_id] = email
            await message.reply("Correo electrónico registrado automáticamente porque el administrador de bot reconoce tu dirección.")
            return

    verification_code = generate_verification_code()
    try:
        contenido = f"""
Tu código de verificación de correo es: {verification_code}
Si no solicitaste este código simplemente ignóralo.
"""
        send_email(email, 'Código de Verificación', contenido=contenido)
        verification_storage[user_id] = {'email': email, 'code': verification_code}
        await message.reply("Código de verificación enviado a tu correo. Introduce el código usando /verify.")
    except Exception as e:
        await message.reply(f"Error al enviar el correo de verificación: {e}")
        
# Función para verificar el código y registrar el correo
async def verify_mail(client, message):
    user_id = message.from_user.id
    code = message.text.split(' ', 1)[1]
    if user_id in verification_storage:
        stored_email = verification_storage[user_id]['email']
        stored_code = verification_storage[user_id]['code']
        if code == stored_code:
            user_emails[user_id] = stored_email
            del verification_storage[user_id]
            await message.reply("Correo electrónico verificado y registrado correctamente.")
        else:
            await message.reply("El código de verificación es incorrecto. Intenta de nuevo.")
    else:
        await message.reply("No hay un código de verificación pendiente. Usa /setmail para iniciar el proceso.")

# Función para comprimir y dividir archivos en partes
def compressfile(file_path, part_size):
    parts = []
    part_size *= 1024 * 1024
    archive_path = f"{file_path}.7z"
    with py7zr.SevenZipFile(archive_path, 'w') as archive:
        archive.write(file_path, os.path.basename(file_path))
    with open(archive_path, 'rb') as archive:
        part_num = 1
        while True:
            part_data = archive.read(part_size)
            if not part_data:
                break
            part_file = f"{archive_path}.{part_num:03d}"
            with open(part_file, 'wb') as part:
                part.write(part_data)
            parts.append(part_file)
            part_num += 1
    return parts


async def send_mail(client, message):
    user_id = message.from_user.id

    if user_id not in user_emails:
        await message.reply("No has registrado ningún correo, usa /setmail para hacerlo.", protect_content=True)
        return

    email = user_emails[user_id]

    if not message.reply_to_message:
        await message.reply("Por favor, responde a un mensaje.", protect_content=True)
        return

    reply_message = message.reply_to_message

    protect_content = not (
        user_id in admin_users or
        user_id in vip_users or
        not PROTECT_CONTENT
    )

    if reply_message.caption and reply_message.caption.startswith("Look Here") and reply_message.from_user.is_self:
        await message.reply("No puedes enviar este contenido debido a restricciones.", protect_content=protect_content)
        return

    mail_mb = get_mail_limit(user_id)
    mail_delay = get_user_delay(user_id)

    # Envío de texto directo
    if reply_message.text:
        try:
            send_email(email, 'Mensaje de texto', contenido=reply_message.text)
            await message.reply("Mensaje de texto enviado correctamente.", protect_content=protect_content)
        except Exception as e:
            await message.reply(f"Error al enviar el mensaje: {e}", protect_content=protect_content)
        return

    # Archivos multimedia
    if reply_message.document or reply_message.photo or reply_message.video or reply_message.sticker:
        media = await client.download_media(reply_message, file_name='mailtemp/')
        if os.path.getsize(media) <= mail_mb * 1024 * 1024:
            try:
                send_email(email, 'Archivo', adjunto=media)
                await message.reply("Archivo enviado correctamente sin compresión.", protect_content=protect_content)
                os.remove(media)
            except Exception as e:
                await message.reply(f"Error al enviar el archivo: {e}", protect_content=protect_content)
        else:
            await message.reply(f"El archivo supera el límite de {mail_mb} MB, se iniciará la autocompresión.", protect_content=protect_content)
            parts = compressfile(media, mail_mb)
            cantidad_de_parts = len(parts)

            if mail_delay == "manual":
                part_queue[user_id] = {
                    "parts": parts,
                    "email": email,
                    "index": 0,
                    "total": cantidad_de_parts,
                    "message_id": message.message_id
                }
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Enviar siguiente parte", callback_data="send_next_part")],
                    [InlineKeyboardButton("Enviar automáticamente", callback_data="no_action")],
                    [
                        InlineKeyboardButton("10 seg", callback_data="auto_delay_10"),
                        InlineKeyboardButton("30 seg", callback_data="auto_delay_30"),
                        InlineKeyboardButton("60 seg", callback_data="auto_delay_60")
                    ],
                    [
                        InlineKeyboardButton("90 seg", callback_data="auto_delay_90"),
                        InlineKeyboardButton("180 seg", callback_data="auto_delay_180")
                    ],
                    [InlineKeyboardButton("Cancelar envío", callback_data="cancel_send")]
                ])

                await message.reply(
                    f"Tienes {cantidad_de_parts} partes listas para enviar.",
                    reply_markup=keyboard,
                    protect_content=protect_content
                )
            else:
                for part in parts:
                    try:
                        asunto = f"Parte {os.path.basename(part)} de {cantidad_de_parts}"
                        send_email(email, asunto, adjunto=part)
                        await message.reply(f"Parte {os.path.basename(part)} de {cantidad_de_parts} enviada correctamente.", protect_content=protect_content)
                        os.remove(part)
                        time.sleep(float(mail_delay) if mail_delay else 0)
                    except Exception as e:
                        await message.reply(f"Error al enviar la parte {os.path.basename(part)}: {e}", protect_content=protect_content)

# Diccionario para almacenar configuraciones de múltiples correos
multi_user_emails = {}

async def multisetmail(client, message):
    user_id = message.from_user.id
    if user_id not in admin_users:
        await message.reply("Esta función es solo para administradores.", protect_content=True); return
    try:
        emails_data = message.text.split(' ', 1)[1]
        email_entries = [entry.strip() for entry in emails_data.split(',') if entry.strip()]
        email_config = {}
        for entry in email_entries:
            if ':' not in entry:
                await message.reply(f"Formato incorrecto en: {entry}. Debe ser correo:limite_mb*limite_mensajes"); return
            email, limits = entry.rsplit(':', 1)
            if '*' not in limits:
                await message.reply(f"Formato incorrecto en: {entry}. Debe incluir límite de mensajes (ej: 20*4)"); return
            limit_mb, limit_msgs = limits.split('*')
            try:
                limit_mb = int(limit_mb); limit_msgs = int(limit_msgs)
                if limit_mb < 1 or limit_mb > 100:
                    await message.reply(f"Límite de tamaño inválido para {email}. Debe ser entre 1 y 100 MB."); return
                if limit_msgs < 1 or limit_msgs > 100:
                    await message.reply(f"Límite de mensajes inválido para {email}. Debe ser entre 1 y 100."); return
                email_config[email] = {'size_limit': limit_mb, 'msg_limit': limit_msgs}
            except ValueError:
                await message.reply(f"Límites inválidos para {email}. Deben ser números."); return
        multi_user_emails[user_id] = email_config
        response = "✅ Configuración de múltiples correos actualizada:\n" + "\n".join([
            f"{email}: {config['size_limit']}MB*{config['msg_limit']} mensajes" for email, config in email_config.items()
        ])
        await message.reply(response)
    except Exception as e:
        await message.reply(f"❌ Error al procesar la configuración: {str(e)}")
        

async def multisendmail(client, message):
    user_id = message.from_user.id
    if user_id not in admin_users:
        await message.reply("Esta función es solo para administradores.", protect_content=True); return
    if user_id not in multi_user_emails or not multi_user_emails[user_id]:
        await message.reply("Primero configura los correos con /multisetmail correo1:limite*msgs,correo2:limite*msgs,..."); return
    if not message.reply_to_message:
        await message.reply("Por favor, responde al mensaje que contiene el archivo a enviar."); return
    reply_message = message.reply_to_message
    original_filename = ""; file_size = 0
    if reply_message.document:
        file_size = reply_message.document.file_size; original_filename = reply_message.document.file_name
    elif reply_message.video:
        file_size = reply_message.video.file_size; original_filename = f"video_{reply_message.video.file_unique_id}.mp4"
    elif reply_message.photo:
        file_size = reply_message.photo.sizes[-1].file_size; original_filename = f"photo_{reply_message.photo.file_unique_id}.jpg"
    else:
        await message.reply("Solo se pueden enviar archivos (documentos, fotos o videos) con este comando."); return
    if not original_filename: original_filename = f"archivo_{int(time.time())}.bin"
    total_size_mb = file_size / (1024 * 1024)
    email_config = multi_user_emails[user_id]
    total_capacity = sum(conf['size_limit'] * conf['msg_limit'] for conf in email_config.values())
    if total_size_mb > total_capacity:
        await message.reply("❌ Todos los correos registrados no pueden recibir este fichero"); return
    processing_msg = await message.reply(f"📁 Procesando: {original_filename} ({total_size_mb:.2f} MB)...")
    try:
        media = await client.download_media(reply_message, file_name='mailtemp/')
        archive_path = f"mailtemp/{original_filename}.7z"
        with py7zr.SevenZipFile(archive_path, 'w') as archive: archive.write(media, original_filename)
        with open(archive_path, 'rb') as f: compressed_data = f.read()
        os.remove(archive_path); os.remove(media)
        current_position = 0; part_num = 1; total_parts = 0
        for email, config in email_config.items():
            size_limit = config['size_limit'] * 1024 * 1024; msg_limit = config['msg_limit']
            total_parts += min((len(compressed_data) - current_position + size_limit - 1) // size_limit, msg_limit)
        current_position = 0; part_num = 1
        for email, config in email_config.items():
            if current_position >= len(compressed_data): break
            size_limit = config['size_limit'] * 1024 * 1024; remaining_msgs = config['msg_limit']
            while current_position < len(compressed_data) and remaining_msgs > 0:
                chunk_size = min(size_limit, len(compressed_data) - current_position)
                part_data = compressed_data[current_position:current_position + chunk_size]
                current_position += chunk_size; remaining_msgs -= 1
                attachment_filename = f"{original_filename}.7z"
                part_file = f"mailtemp/{attachment_filename}.part{part_num}"
                with open(part_file, 'wb') as f: f.write(part_data)
                try:
                    asunto = f"{original_filename} [{part_num}/{total_parts}]"
                    send_email(email, asunto, adjunto=part_file)
                    await processing_msg.edit_text(
                        f"📤 Enviando {original_filename} [{part_num}/{total_parts}] a {email}\n"
                        f"📦 Tamaño: {chunk_size/(1024*1024):.2f}MB\n"
                        f"✉️ Mensajes restantes en este correo: {remaining_msgs}/{config['msg_limit']}"
                    )
                    os.remove(part_file); part_num += 1
                    await asyncio.sleep(2)
                except Exception as e:
                    await processing_msg.edit_text(f"❌ Error al enviar parte {part_num}: {str(e)}")
                    if os.path.exists(part_file): os.remove(part_file); return
        await processing_msg.edit_text(f"✅ {original_filename} enviado completamente!")
    except Exception as e:
        if 'media' in locals() and os.path.exists(media): os.remove(media)
        if 'archive_path' in locals() and os.path.exists(archive_path): os.remove(archive_path)
        await processing_msg.edit_text(f"❌ Error procesando {original_filename}: {str(e)}")
