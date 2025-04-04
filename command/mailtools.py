import os
import time
import shutil
import py7zr
import smtplib
from email.message import EmailMessage
import random
from data.vars import admin_users, vip_users, video_limit

# Diccionarios para almacenar información de los usuarios
user_emails = {}
verification_storage = {}
user_limits = {}
exceeded_users = []

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

# Función para obtener el límite de MAIL_MB para un usuario
def get_mail_limit(user_id):
    return user_limits.get(user_id, int(os.getenv('MAIL_MB', 20)))

# Modificación de la función set_mail para enviar el código de verificación por correo
async def set_mail(client, message):
    email = message.text.split(' ', 1)[1]
    user_id = message.from_user.id
    mail_confirmed = os.getenv('MAIL_CONFIRMED')
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
        msg = EmailMessage()
        msg['Subject'] = 'Código de Verificación'
        msg['From'] = f"Neko Bot <{os.getenv('MAILDIR')}>"
        msg['To'] = email
        msg.set_content(f"""
        Tu código de verificación de correo es: {verification_code}
        Si no solicitaste este código simplemente ignóralo.
        """)
        mail_server = os.getenv('MAIL_SERVER')
        if not mail_server:
            raise ValueError("La configuración de MAIL_SERVER no está definida. Asegúrate de configurarla correctamente.")
        server_details = mail_server.split(':')
        if len(server_details) < 2:
            raise ValueError("MAIL_SERVER debe estar en el formato 'host:puerto:opcional_tls'.")
        smtp_host = server_details[0]
        smtp_port = int(server_details[1])
        security_enabled = len(server_details) > 2 and server_details[2].lower() == 'tls'
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if security_enabled:
                server.starttls()
            server.login(os.getenv('MAILDIR'), os.getenv('MAILPASS'))
            server.send_message(msg)
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

# Enviar correo al usuario registrado
async def send_mail(client, message):
    user_id = message.from_user.id
    if user_id not in user_emails:
        await message.reply("No has registrado ningún correo, usa /setmail para hacerlo.", protect_content=True)
        return
    email = user_emails[user_id]
    if not message.reply_to_message:
        await message.reply("Por favor, responde a un mensaje.", protect_content=protect_content)
        return
    reply_message = message.reply_to_message
    if user_id in admin_users:
        protect_content= False

    else:
        protect_content= True

    # Restricciones antes de procesar cualquier contenido
    if reply_message.caption and reply_message.caption.startswith("Look Here") and reply_message.from_user.is_self:
        await message.reply("No puedes enviar este contenido debido a restricciones.", protect_content=protect_content)
        return

    # Envío de mensajes de texto
    if reply_message.text:
        try:
            msg = EmailMessage()
            msg['Subject'] = 'Mensaje de texto'
            msg['From'] = f"Neko Bot <{os.getenv('MAILDIR')}>"
            msg['To'] = email
            msg.set_content(reply_message.text)

            mail_server = os.getenv('MAIL_SERVER')
            server_details = mail_server.split(':')
            smtp_host = server_details[0]
            smtp_port = int(server_details[1])
            security_enabled = len(server_details) > 2 and server_details[2].lower() == 'tls'

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if security_enabled:
                    server.starttls()
                server.login(os.getenv('MAILDIR'), os.getenv('MAILPASS'))
                server.send_message(msg)

            await message.reply("Mensaje de texto enviado correctamente.", protect_content=protect_content)
        except Exception as e:
            await message.reply(f"Error al enviar el mensaje: {e}", protect_content=protect_content)
        return

    mail_mb = get_mail_limit(user_id)
    mail_delay = os.getenv('MAIL_DELAY')

    # Envío de archivos multimedia
    if reply_message.document or reply_message.photo or reply_message.video or reply_message.sticker:
        media = await client.download_media(reply_message, file_name='mailtemp/')
        if os.path.getsize(media) <= mail_mb * 1024 * 1024:
            try:
                msg = EmailMessage()
                msg['Subject'] = 'Archivo'
                msg['From'] = f"Neko Bot <{os.getenv('MAILDIR')}>"
                msg['To'] = email
                with open(media, 'rb') as f:
                    msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=os.path.basename(media))
                mail_server = os.getenv('MAIL_SERVER')
                server_details = mail_server.split(':')
                smtp_host = server_details[0]
                smtp_port = int(server_details[1])
                security_enabled = len(server_details) > 2 and server_details[2].lower() == 'tls'
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    if security_enabled:
                        server.starttls()
                    server.login(os.getenv('MAILDIR'), os.getenv('MAILPASS'))
                    server.send_message(msg)
                await message.reply("Archivo enviado correctamente sin compresión.", protect_content=protect_content)
                os.remove(media)
            except Exception as e:
                await message.reply(f"Error al enviar el archivo: {e}", protect_content=protect_content)
        else:
            await message.reply(f"El archivo supera el límite de {mail_mb} MB, se iniciará la autocompresión.", protect_content=protect_content)
            parts = compressfile(media, mail_mb)
            for part in parts:
                try:
                    mail_server = os.getenv('MAIL_SERVER')
                    if not mail_server:
                        raise ValueError("MAIL_SERVER no está definido en las variables de entorno.")

                    server_details = mail_server.split(':')
                    if len(server_details) < 2:
                        raise ValueError("MAIL_SERVER debe estar en el formato 'host:puerto:opcional_tls'.")

                    smtp_host = server_details[0]
                    smtp_port = int(server_details[1])
                    security_enabled = len(server_details) > 2 and server_details[2].lower() == 'tls'

                    msg = EmailMessage()
                    msg['Subject'] = f"Parte {os.path.basename(part)}"
                    msg['From'] = f"Neko Bot <{os.getenv('MAILDIR')}>"
                    msg['To'] = email

                    with open(part, 'rb') as f:
                        msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename=os.path.basename(part))

                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        if security_enabled:
                            server.starttls()
                        server.login(os.getenv('MAILDIR'), os.getenv('MAILPASS'))
                        server.send_message(msg)

                    await message.reply(f"Parte {os.path.basename(part)} enviada correctamente.", protect_content=protect_content)
                    os.remove(part)
                    time.sleep(float(mail_delay) if mail_delay else 0)
                except Exception as e:
                    await message.reply(f"Error al enviar la parte {os.path.basename(part)}: {e}", protect_content=protect_content)
