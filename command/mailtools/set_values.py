import os
import time
import shutil
import py7zr
import smtplib
from email.message import EmailMessage
import random
from data.vars import admin_users, vip_users, video_limit, PROTECT_CONTENT, correo_manual
import asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from command.db.db import save_user_data_to_db, load_user_config
user_emails = {}
verification_storage = {}
user_limits = {}
user_delays = {}
exceeded_users = []
copy_users = []
def get_access_label(lvl: str) -> str:
    return {
        "0": "Usuario baneado",
        "1": "Usuario público",
        "2": "Usuario",
        "3": "Usuario VIP",
        "4": "MOD",
        "5": "ADMIN",
        "6": "Owner"
    }.get(lvl, "Desconocido")

async def mydata(client, message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name or ""
    name = f"{first_name} {last_name}".strip()
    username = message.from_user.username

    try:
        lvl = load_user_config(user_id, "lvl")
        acceso = get_access_label(lvl)
        email = load_user_config(user_id, "email") or "Sin configurar"
        mail_mb = load_user_config(user_id, "limit")
        mail_delay = load_user_config(user_id, "delay")
    except Exception as e:
        await message.reply(f"⚠️ Error al cargar datos: {e}")
        return

    username_text = f"📎 Usuario: @{username}\n" if username else ""

    text = (
        f"👤 Perfil del usuario {name}\n"
        f"{username_text}"
        f"🆔 : `{user_id}`\n"
        f"🔐 Nivel de acceso: `{acceso}`\n"
        f"📧 Email: `{email}`\n"
        f"📦 Límite: `{mail_mb} MB`\n"
        f"⏱️ Delay: `{mail_delay}`\n"
    )
    await message.reply(text)

    

    
async def copy_manager(user):
    if user not in copy_users:
        copy_users.append(user)
        return f"Usuario '{user}' agregado a la lista."
    else:
        copy_users.remove(user)
        return f"Usuario '{user}' eliminado de la lista."
            
async def verify_protect(user_id):
        protect_content = not (user_id in admin_users or user_id in vip_users or not PROTECT_CONTENT)
        return protect_content 
    
async def set_mail_limit(client, message):
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)

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

        if new_limit > 20 and user_id not in admin_users:
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
        save_user_data_to_db(user_id, "limit", new_limit)
        await message.reply(f"El límite personal del usuario ha sido cambiado a {new_limit} MB.")

    except ValueError:
        await message.reply("Por favor, proporciona un número válido como límite.")
        
def generate_verification_code():
    return f"{random.randint(100000, 999999)}"

async def set_mail_delay(client, message):
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)

    try:
        raw_input = message.text.split(' ', 1)[1].strip().lower()

        if raw_input == "manual":
            user_delays[user_id] = "manual"
            save_user_data_to_db(user_id, "delay", "manual")
            await message.reply("Modo manual activado. El tiempo de espera será definido por otros parámetros.")
            return

        new_limit = int(raw_input)

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
        save_user_data_to_db(user_id, "delay", new_limit)
        time.sleep(4)
        await message.reply(
            f"El tiempo de espera personal del usuario entre el envío de partes ha sido cambiado a {new_limit} segundos."
        )

    except (IndexError, ValueError):
        await message.reply("Por favor, proporciona un número válido como límite o escribe 'manual'.")
        
# Función para obtener el límite de MAIL_MB para un usuario
def get_mail_limit(user_id):
    return user_limits.get(user_id, int(os.getenv('MAIL_MB', 20)))
def get_user_delay(user_id):
    return user_delays.get(user_id, int(os.getenv('MAIL_DELAY', 30)))

def send_ver(destino, asunto, contenido=None, adjunto=False):
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

async def set_mail(client, message, int_lvl):
    try:
        email = message.text.split(' ', 1)[1]
    except IndexError:
        await message.reply("Formato incorrecto. Usa: /setmail tu_correo@example.com")
        return

    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)
    mail_confirmed = os.getenv('MAIL_CONFIRMED')
    if int_lvl >= 4:
        user_emails[user_id] = email
        save_user_data_to_db(user_id, "email", email)
        await message.reply("Correo electrónico registrado automáticamente porque eres parte de la administración del bot.")
        return
    if mail_confirmed:
        confirmed_users = {
            item.split('=')[0]: item.split('=')[1].split(';') 
            for item in mail_confirmed.split(',')
        }
        if str(user_id) in confirmed_users and email in confirmed_users[str(user_id)]:
            user_emails[user_id] = email
            save_user_data_to_db(user_id, "email", email)
            await message.reply("Correo electrónico registrado automáticamente porque el administrador del bot reconoce tu dirección.")
            return
    verification_code = generate_verification_code()
    try:
        contenido = f"""
Tu código de verificación de correo es: {verification_code}
Si no solicitaste este código simplemente ignóralo.
"""
        send_ver(email, 'Código de Verificación', contenido=contenido)
        verification_storage[user_id] = {'email': email, 'code': verification_code}
        await message.reply("Código de verificación enviado a tu correo. Introduce el código usando /verify.")
    except Exception as e:
        await message.reply(f"Error al enviar el correo de verificación: {e}")


async def verify_mail(client, message):
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)

    try:
        code = message.text.split(' ', 1)[1]
    except IndexError:
        await message.reply("Formato incorrecto. Usa: /verify código_de_verificación")
        return

    if user_id not in verification_storage:
        await message.reply("No hay un código de verificación pendiente. Usa /setmail para iniciar el proceso.")
        return

    stored_email = verification_storage[user_id]['email']
    stored_code = verification_storage[user_id]['code']

    if code == stored_code:
        user_emails[user_id] = stored_email
        save_user_data_to_db(user_id, "email", stored_email)
        del verification_storage[user_id]
        await message.reply("✅ Correo electrónico verificado y registrado correctamente.")
    else:
        await message.reply("❌ El código de verificación es incorrecto. Intenta de nuevo.")

multi_user_emails = {}

async def multisetmail(client, message):
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)
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
