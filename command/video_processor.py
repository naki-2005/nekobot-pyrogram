from command.get_files.video_file import obtener_duracion_video, comprimir_video, calcular_progreso, human_readable_size
import os
import re
import datetime

async def procesar_video(client, message, original_video_path, task_id, tareas_en_ejecucion, user_specific_settings):
    chat_id = message.chat.id
    compressed_video_path = f"{os.path.splitext(original_video_path)[0]}_compressed.mkv"

    progress_message = await client.send_message(chat_id=chat_id, text="🚀 **Iniciando proceso de compresión...**")

    try:
        total_duration = obtener_duracion_video(original_video_path)
        start_time = datetime.datetime.now()
        process = comprimir_video(original_video_path, compressed_video_path, user_specific_settings)

        last_update_time = datetime.datetime.now()

        while True:
            if tareas_en_ejecucion[task_id]["cancel"]:
                process.terminate()
                await progress_message.edit_text(f"❌ Proceso cancelado para `{task_id}`.")
                if os.path.exists(compressed_video_path):
                    os.remove(compressed_video_path)
                    os.remove(original_video_path)
                return

            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break

            readable_size, percentage, current_time = calcular_progreso(output, total_duration)
            if (datetime.datetime.now() - last_update_time).seconds >= 10:
                elapsed_time = datetime.datetime.now() - start_time
                estimated_total_time = (elapsed_time.total_seconds() / (percentage / 100)) if percentage > 0 else 0
                remaining_time = str(datetime.timedelta(seconds=int(estimated_total_time - elapsed_time.total_seconds())))

                await progress_message.edit_text(
                    text=(
                        f"🚀 **Progreso:**\n"
                        f"📊 Tamaño procesado: `{readable_size}`\n"
                        f"📈 Porcentaje completado: `{percentage:.2f}%`\n"
                        f"⏳ Tiempo total transcurrido: `{str(elapsed_time).split('.')[0]}`\n"
                        f"⌛ Tiempo estimado restante: `{remaining_time}`\n"
                    )
                )
                last_update_time = datetime.datetime.now()

        await progress_message.edit_text("✅ **Proceso completado. Preparando resultados...**")

        compressed_size = os.path.getsize(compressed_video_path)
        original_size = os.path.getsize(original_video_path)
        description = (
            f"✅ **Archivo procesado correctamente ☑️**\n"
            f"📂 **Tamaño original:** {human_readable_size(original_size // 1024)}\n"
            f"📁 **Tamaño procesado:** {human_readable_size(compressed_size // 1024)}\n"
            f"⌛ **Tiempo de procesamiento:** {str(datetime.datetime.now() - start_time).split('.')[0]}\n"
            f"🎥 **Duración del video:** {str(datetime.timedelta(seconds=total_duration))}\n"
            f"🎉 **¡Gracias por usar el bot!**"
        )

        nombre = os.path.splitext(os.path.basename(compressed_video_path))[0]
        return nombre, description, chat_id, compressed_video_path, original_video_path
    except Exception as e:
        await client.send_message(chat_id=chat_id, text=f"❌ **Ocurrió un error al procesar el video:**\n{e}")
        os.remove(original_video_path)
        os.remove(compressed_video_path)
