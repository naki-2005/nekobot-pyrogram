from command.mailtools.send import mail_query
from command.help import handle_help_callback
from command.admintools import send_setting_editor, process_access_callback, guardar_parametro, get_accesscmd_buttons, get_main_buttons
from command.db.db import subir_bot_config
from command.mangatools import handle_manga_callback
from command.torrets_tools import handle_nyaa_callback
from command.torrets_tools import handle_sukebei_callback 

async def process_query(client, callback_query):
    data = callback_query.data

    mail_related = (
        ["send_next_part", "send_5_parts", "send_10_parts", "cancel_send", "no_action"] +
        [f"auto_delay_{x}" for x in [10, 30, 60, 90, 180]]
    )

    help_related = [f"help_{x}" for x in [1, 2, 3, 4, 5]] + ["help_back"]

    manga_related = data.startswith("manga_") or data.startswith("chapter_") or data in ["first_page", "prev_page", "next_page", "last_page", "noop"]

    nyaa_related = data.startswith("nyaa_")
    
    sukebei_related = data.startswith("sukebei_")

    if data in mail_related:
        await mail_query(client, callback_query)

    elif data in help_related:
        await handle_help_callback(client, callback_query)

    elif data.startswith("id_") and "#" in data:
        await process_access_callback(client, callback_query)

    elif data == "config_back":
        bot_info = await client.get_me()
        bot_id = bot_info.id
        texto = f"Editar la configuración del bot {bot_id}"
        await callback_query.message.edit_text(
            texto,
            reply_markup=get_main_buttons()
        )

    elif data.startswith("config_"):
        parametro = data.split("_")[1]
        texto = f"Editar acceso a los comandos de {parametro}"
        await callback_query.message.edit_text(
            texto,
            reply_markup=get_accesscmd_buttons(parametro)
        )

    elif data.startswith("access_"):
        _, parametro, valor = data.split("_")
        guardar_parametro(parametro, valor)
        await callback_query.answer("✅ Configuración guardada", show_alert=True)

    elif data == "save_config":
        bot_info = await client.get_me()
        bot_id = str(bot_info.id)
        subir_bot_config(bot_id)
        await callback_query.answer("📤 Configuración subida al repositorio", show_alert=True)

    elif data == "config_type":
        await send_setting_public(client, callback_query.message)

    elif manga_related:
        await handle_manga_callback(client, callback_query)

    elif nyaa_related:
        await handle_nyaa_callback(client, callback_query)
        
    elif sukebei_related:
        await handle_sukebei_callback(client, callback_query)


    else:
        await callback_query.answer("No se ha encontrado una respuesta Query correcta.", show_alert=True)
