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
user_emails = {}
verification_storage = {}
user_limits = {}
user_delays = {}
exceeded_users = []
copy_users = []

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

# Función para generar un código de verificación de 6 números
def generate_verification_code():
    return f"{random.randint(100000, 999999)}"

# Función para establecer el límite de MAIL_MB para un usuario
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
        await message.reply(f"El límite personal del usuario ha sido cambiado a {new_limit} MB.")
    except ValueError:
        await message.reply("Por favor, proporciona un número válido como límite.")

async def set_mail_delay(client, message):
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)
    try:
        raw_input = message.text.split(' ', 1)[1].strip().lower()

        if raw_input == "manual":
            user_delays[user_id] = "manual"
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
        
async def set_mail(client, message):
    email = message.text.split(' ', 1)[1]
    user_id = message.from_user.id
    protect_content = await verify_protect(user_id)
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
    protect_content = await verify_protect(user_id)
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

# Diccionario para almacenar configuraciones de múltiples correos
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
