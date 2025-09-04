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
        user = replied_msg.from_user
        
        # Obtener nombre de usuario
        user_name = user.first_name or ""
        if user.last_name:
            user_name += f" {user.last_name}"
        if not user_name.strip():
            user_name = user.username or "Usuario"
        
        # Obtener texto del mensaje
        text_content = replied_msg.text or replied_msg.caption or "📷 Media"
        
        # Crear imagen de la cita
        image_path = await generate_quote_image(user_name, text_content)
        
        if image_path:
            # Enviar la imagen
            await client.send_photo(
                chat_id=message.chat.id,
                photo=image_path,
                reply_to_message_id=replied_msg.id
            )
            
            # Eliminar archivo temporal
            os.remove(image_path)
        else:
            await message.reply("❌ Error al crear la cita.")
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def generate_quote_image(user_name: str, text: str):
    """Genera una imagen con la cita estilo WhatsApp"""
    try:
        # Configuración
        width, height = 800, 400
        bg_color = (35, 35, 35)  # Fondo oscuro
        text_color = (255, 255, 255)  # Texto blanco
        accent_color = (0, 150, 255)  # Azul para el nombre
        
        # Crear imagen
        image = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Cargar fuentes (ajusta según tu sistema)
        try:
            name_font = ImageFont.truetype("arialbd.ttf", 30)
            text_font = ImageFont.truetype("arial.ttf", 28)
        except:
            # Fuentes por defecto
            name_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Dibujar nombre
        draw.text((50, 50), user_name, fill=accent_color, font=name_font)
        
        # Dibujar texto (con ajuste de líneas)
        max_width = width - 100
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=text_font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Dibujar líneas de texto
        y_position = 100
        for line in lines[:5]:  # Máximo 5 líneas
            draw.text((50, y_position), line, fill=text_color, font=text_font)
            y_position += 40
        
        if len(lines) > 5:
            draw.text((50, y_position), "...", fill=text_color, font=text_font)
        
        # Guardar imagen temporal
        image_path = f"quote_{message.chat.id}_{message.id}.jpg"
        image.save(image_path)
        
        return image_path
        
    except Exception as e:
        print(f"Error generating quote image: {e}")
        return None
