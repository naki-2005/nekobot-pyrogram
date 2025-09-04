import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
from pyrogram.types import Message

async def create_quote(client, message: Message):
    """Crea una cita estilo @QuotLyBot a partir de un mensaje respondido"""
    try:
        # Verificar que es una respuesta a otro mensaje
        if not message.reply_to_message:
            await message.reply("❌ Debes responder a un mensaje para citarlo.")
            return

        replied_msg = message.reply_to_message
        
        # Obtener información del usuario
        user = replied_msg.from_user
        if not user:
            await message.reply("❌ No se pudo obtener información del usuario.")
            return
        
        user_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not user_name:
            user_name = user.username or "Usuario"
        
        # Obtener texto del mensaje
        text_content = replied_msg.text or replied_msg.caption or "📷 Media"
        
        # Crear imagen simple de la cita
        try:
            # Configuración básica
            width, height = 600, 300
            image = Image.new("RGB", (width, height), (35, 35, 35))
            draw = ImageDraw.Draw(image)
            
            # Usar fuentes por defecto
            font = ImageFont.load_default()
            
            # Dibujar nombre
            draw.text((20, 20), user_name, fill=(0, 150, 255), font=font)
            
            # Dibujar texto (truncado si es muy largo)
            if len(text_content) > 100:
                text_content = text_content[:100] + "..."
            
            # Dividir texto en líneas
            lines = []
            current_line = ""
            for word in text_content.split():
                test_line = f"{current_line} {word}".strip()
                if len(test_line) * 6 <= width - 40:  # Aproximación simple
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            # Dibujar líneas
            y_pos = 60
            for line in lines[:4]:  # Máximo 4 líneas
                draw.text((20, y_pos), line, fill=(255, 255, 255), font=font)
                y_pos += 30
            
            if len(lines) > 4:
                draw.text((20, y_pos), "...", fill=(255, 255, 255), font=font)
            
            # Guardar imagen
            image_path = f"quote_{message.chat.id}_{message.id}.jpg"
            image.save(image_path)
            
            # Enviar imagen
            await client.send_photo(
                chat_id=message.chat.id,
                photo=image_path,
                reply_to_message_id=replied_msg.id
            )
            
            # Limpiar
            if os.path.exists(image_path):
                os.remove(image_path)
                
        except Exception as e:
            print(f"Error creating image: {e}")
            await message.reply("❌ Error al crear la imagen de la cita.")
            
    except Exception as e:
        print(f"Error in create_quote: {e}")
        await message.reply("❌ Error al procesar el comando.")
