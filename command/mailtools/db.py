import os
import json
import requests
import base64

async def save_mail(client, message):
    user_id_int = int(message.from_user.id)
    admin_users = list(map(int, os.getenv('ADMINS', '').split(','))) if os.getenv('ADMINS') else []
    if user_id_int not in admin_users:
        await message.reply("⛔ No tienes permisos para ejecutar este comando.")
        return

    try:
        # Esperado: user_id,email,delay,limit_mb
        payload = message.text.split(',', 3)
        if len(payload) != 4:
            await message.reply("⚠️ Formato inválido. Usa: user_id,email,delay,limit_mb")
            return

        target_id = payload[0].strip()

        user_data = {
            "email": payload[1].strip(),
            "delay": int(payload[2].strip()),
            "limit_mb": int(payload[3].strip())
        }

        GIT_REPO = os.getenv("GIT_REPO")
        GIT_API = os.getenv("GIT_API")
        FILE_PATH = "config.json"

        url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GIT_API}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            content = response.json()
            sha = content['sha']
            existing_data = json.loads(
                requests.get(content['download_url'], headers=headers).text
            )
        else:
            existing_data = {}
            sha = None
            
        existing_data[target_id] = user_data
        updated_content = json.dumps(existing_data, indent=4)
        
        commit_data = {
            "message": f"Update config for user {target_id}",
            "content": base64.b64encode(updated_content.encode("utf-8")).decode("utf-8"),
            "branch": "main"
        }
        if sha:
            commit_data["sha"] = sha
        put_response = requests.put(url, headers=headers, json=commit_data)

        if put_response.status_code in [200, 201]:
            await message.reply("✅ Configuración guardada exitosamente en GitHub.")
        else:
            await message.reply(f"❌ Error al guardar: {put_response.status_code}")
    except Exception as e:
        await message.reply(f"🚨 Error inesperado: {str(e)}")

def load_mail():
    try:
        GIT_REPO = os.getenv("GIT_REPO")
        GIT_API = os.getenv("GIT_API")
        FILE_PATH = "config.json"

        url = f"https://api.github.com/repos/{GIT_REPO}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GIT_API}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            config = json.loads(
                requests.get(content['download_url'], headers=headers).text
            )

            emails, delays, limits = {}, {}, {}

            for uid, data in config.items():
                uid = int(uid)
                emails[uid] = data['email']
                delays[uid] = data['delay']
                limits[uid] = data['limit_mb']

            return emails, delays, limits

        else:
            print("No se encontró configuración previa.")
            return {}, {}, {}

    except Exception as e:
        print(f"Error al cargar configuración: {str(e)}")
        return {}, {}, {}
