import os
import subprocess
import datetime
import re

def human_readable_size(size, decimal_places=2):
    for unit in ['KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0

def obtener_duracion_video(original_video_path):
    try:
        total_duration = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", original_video_path]
        )
        return float(total_duration.strip())
    except Exception as e:
        raise RuntimeError(f"Error al obtener la duración del video: {e}")

def comprimir_video(user_id, original_video_path, compressed_video_path, video_settings):
    # Seleccionar la configuración del usuario si existe, de lo contrario usar la configuración por defecto
    settings = video_settings.get(user_id, video_settings.get('default'))
    
    ffmpeg_command = [
        'ffmpeg', '-y', '-i', original_video_path,
        '-s', settings['resolution'],
        '-map', '0',
        '-crf', settings['crf'],
        '-b:a', settings['audio_bitrate'],
        '-r', settings['fps'],
        '-preset', settings['preset'],
        '-c:v', settings['codec'],
        compressed_video_path
    ]
    return subprocess.Popen(ffmpeg_command, stderr=subprocess.PIPE, text=True)

def calcular_progreso(output, total_duration):
    if "size=" in output and "time=" in output:
        match = re.search(r"size=\s*([\d]+).*time=([\d:.]+)", output)
        if match:
            size_kb, current_time_str = match.groups()
            size_kb = int(size_kb)
            readable_size = human_readable_size(size_kb)

            current_time_parts = list(map(float, current_time_str.split(':')))
            current_time = (
                current_time_parts[0] * 3600 +
                current_time_parts[1] * 60 +
                current_time_parts[2]
            )

            percentage = (current_time / total_duration) * 100
            return readable_size, percentage, current_time
    return None, 0, 0
          
