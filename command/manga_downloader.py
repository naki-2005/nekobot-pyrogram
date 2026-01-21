import os
import subprocess
import uuid
import json
from datetime import datetime
import re
import glob
import time

class MangaDexDownloader:
    def __init__(self, base_path="vault_files/Mangas"):
        self.base_path = base_path
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
        
        self.downloads = {}
        self.downloads_file = os.path.join(base_path, "downloads.json")
        self.load_downloads()
    
    def load_downloads(self):
        if os.path.exists(self.downloads_file):
            try:
                with open(self.downloads_file, 'r', encoding='utf-8') as f:
                    self.downloads = json.load(f)
            except:
                self.downloads = {}
    
    def save_downloads(self):
        with open(self.downloads_file, 'w', encoding='utf-8') as f:
            json.dump(self.downloads, f, indent=2)
    
    def get_download_progress(self, download_id):
        return self.downloads.get(download_id, {})
    
    def detectar_formato_volumen(self, format_type):
        formatos_volumen = ["cbz-volume", "pdf-volume", "raw-volume", "cb7-volume", "epub-volume"]
        formatos_capitulo = ["cbz-single", "pdf-single", "raw-single", "cb7-single", "epub-single"]
        
        if format_type in formatos_volumen:
            return "volumen"
        elif format_type in formatos_capitulo:
            return "capitulo"
        else:
            return "simple"
    
    def limpiar_archivos_incompletos(self, base_directory):
        archivos_problema = []
        formatos = ['.cbz', '.cb7', '.zip', '.pdf', '.epub']
        
        for root, dirs, files in os.walk(base_directory):
            for file in files:
                if any(file.endswith(fmt) for fmt in formatos):
                    filepath = os.path.join(root, file)
                    file_size = os.path.getsize(filepath)
                    
                    if file_size < 10240:
                        try:
                            os.remove(filepath)
                            archivos_problema.append(file)
                        except:
                            pass
        
        return archivos_problema
    
    def build_command(self, url, download_range, format_type, start_value=None, end_value=None, reintento=False):
        cmd = ["mangadex-dl"]
        
        cmd.extend(["--path", self.base_path])
        
        if reintento:
            cmd.extend(["--force", "true"])
        
        format_map = {
            "cbz": ["--save-as", "cbz"],
            "cbz-volume": ["--save-as", "cbz-volume"],
            "cbz-single": ["--save-as", "cbz-single"],
            "pdf": ["--save-as", "pdf"],
            "pdf-volume": ["--save-as", "pdf-volume"],
            "pdf-single": ["--save-as", "pdf-single"],
            "raw": ["--save-as", "raw"],
            "raw-volume": ["--save-as", "raw-volume"],
            "raw-single": ["--save-as", "raw-single"],
            "cb7": ["--save-as", "cb7"],
            "cb7-volume": ["--save-as", "cb7-volume"],
            "cb7-single": ["--save-as", "cb7-single"],
            "epub": ["--save-as", "epub"],
            "epub-volume": ["--save-as", "epub-volume"],
            "epub-single": ["--save-as", "epub-single"],
        }
        
        if format_type in format_map:
            cmd.extend(format_map[format_type])
        
        if download_range == "all":
            pass
        elif download_range == "from-chapter" and start_value:
            cmd.extend(["--start-chapter", start_value])
        elif download_range == "from-volume" and start_value:
            cmd.extend(["--start-volume", start_value])
        elif download_range == "chapters-range" and start_value and end_value:
            cmd.extend(["--start-chapter", start_value, "--end-chapter", end_value])
        elif download_range == "chapter-to-volume" and start_value and end_value:
            cmd.extend(["--start-chapter", start_value, "--end-volume", end_value])
        elif download_range == "volumes-range" and start_value and end_value:
            cmd.extend(["--start-volume", start_value, "--end-volume", end_value])
        elif download_range == "volume-to-chapter" and start_value and end_value:
            cmd.extend(["--start-volume", start_value, "--end-chapter", end_value])
        elif download_range == "specific-chapter" and start_value:
            cmd.extend(["--start-chapter", start_value, "--end-chapter", start_value])
        elif download_range == "specific-volume" and start_value:
            cmd.extend(["--start-volume", start_value, "--end-volume", start_value])
        
        cmd.append(url)
        
        return cmd
    
    def cleanup_temp_files(self, directory):
        temp_patterns = ['*.temp', '*.tmp', '*.*.part', '*.download']
        archivos_eliminados = []
        
        for patron in temp_patterns:
            for ruta_archivo in glob.glob(os.path.join(directory, '**', patron), recursive=True):
                try:
                    os.remove(ruta_archivo)
                    archivos_eliminados.append(os.path.basename(ruta_archivo))
                except OSError as e:
                    pass
        
        return archivos_eliminados
    
    def start_download(self, url, download_range="all", format_type="cbz-volume", 
                      start_value=None, end_value=None, max_reintentos=2):
        download_id = str(uuid.uuid4())
        
        self.downloads[download_id] = {
            "id": download_id,
            "url": url,
            "range": download_range,
            "format": format_type,
            "start": start_value,
            "end": end_value,
            "state": "processing",
            "progress": 0,
            "message": "Iniciando descarga...",
            "start_time": datetime.now().isoformat(),
            "output": "",
            "error": "",
            "reintentos": 0,
            "fallo_volumen": False
        }
        self.save_downloads()
        
        def run_download():
            ultimo_error = None
            es_formato_volumen = self.detectar_formato_volumen(format_type) == "volumen"
            
            for intento in range(max_reintentos + 1):
                try:
                    self.downloads[download_id]["message"] = f"Intentando descarga (intento {intento + 1})..."
                    self.downloads[download_id]["reintentos"] = intento
                    self.save_downloads()
                    
                    es_reintento = intento > 0
                    
                    if es_reintento and es_formato_volumen:
                        self.downloads[download_id]["fallo_volumen"] = True
                        self.downloads[download_id]["message"] = "⚠️  Formato por volumen detectado. Limpiando archivos incompletos..."
                        self.save_downloads()
                        
                        archivos_eliminados = self.limpiar_archivos_incompletos(self.base_path)
                        self.cleanup_temp_files(self.base_path)
                        
                        if archivos_eliminados:
                            self.downloads[download_id]["message"] = f"⚠️  Eliminados {len(archivos_eliminados)} archivos incompletos"
                            self.save_downloads()
                    
                    cmd = self.build_command(url, download_range, format_type, start_value, end_value, es_reintento)
                    
                    self.downloads[download_id]["command"] = " ".join(cmd)
                    self.save_downloads()
                    
                    proceso = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    lineas_stdout = []
                    lineas_stderr = []
                    capitulo_actual = None
                    
                    while True:
                        salida = proceso.stdout.readline()
                        if salida:
                            lineas_stdout.append(salida)
                            self.downloads[download_id]["output"] += salida
                            
                            if "Downloading chapter" in salida:
                                match = re.search(r'chapter\s+([\d\.]+)', salida, re.IGNORECASE)
                                if match:
                                    capitulo_actual = match.group(1)
                                    self.downloads[download_id]["message"] = f"Descargando capítulo {capitulo_actual}"
                            
                            elif "Volume" in salida and "chapter" in salida.lower():
                                match = re.search(r'Volume\s+([\d\.]+).*?chapter\s+([\d\.]+)', salida, re.IGNORECASE)
                                if match:
                                    volumen = match.group(1)
                                    capitulo = match.group(2)
                                    self.downloads[download_id]["message"] = f"Volumen {volumen} - Capítulo {capitulo}"
                            
                            elif "Progreso" in salida or "Progress" in salida:
                                self.downloads[download_id]["message"] = salida.strip()
                            
                            if "100%" in salida:
                                coincidencia = re.search(r'(\d+)%', salida)
                                if coincidencia:
                                    self.downloads[download_id]["progress"] = int(coincidencia.group(1))
                            
                            self.save_downloads()
                        
                        error = proceso.stderr.readline()
                        if error:
                            lineas_stderr.append(error)
                            self.downloads[download_id]["error"] += error
                            self.save_downloads()
                        
                        if salida == '' and error == '' and proceso.poll() is not None:
                            break
                    
                    codigo_retorno = proceso.wait()
                    
                    if codigo_retorno == 0:
                        self.downloads[download_id]["state"] = "completed"
                        self.downloads[download_id]["message"] = "✅ Descarga completada"
                        self.downloads[download_id]["progress"] = 100
                        self.downloads[download_id]["end_time"] = datetime.now().isoformat()
                        self.save_downloads()
                        return
                    
                    else:
                        ultimo_error = f"Proceso falló con código: {codigo_retorno}"
                        
                        if es_formato_volumen:
                            self.downloads[download_id]["message"] = f"❌ Error en formato volumen. Se reiniciará completamente..."
                        else:
                            self.downloads[download_id]["message"] = f"❌ Falló, preparando reintento... ({ultimo_error})"
                        
                        self.save_downloads()
                
                except Exception as e:
                    ultimo_error = str(e)
                    self.downloads[download_id]["message"] = f"❌ Excepción, preparando reintento... ({ultimo_error})"
                    self.save_downloads()
                
                if intento < max_reintentos:
                    tiempo_espera = (intento + 1) * 20
                    self.downloads[download_id]["message"] = f"⏸️  Esperando {tiempo_espera} segundos antes de reintentar..."
                    self.save_downloads()
                    time.sleep(tiempo_espera)
                    
                    if es_formato_volumen:
                        self.cleanup_temp_files(self.base_path)
            
            self.downloads[download_id]["state"] = "error"
            self.downloads[download_id]["message"] = f"❌ Descarga falló después de {max_reintentos} reintentos. Último error: {ultimo_error}"
            self.downloads[download_id]["end_time"] = datetime.now().isoformat()
            self.save_downloads()
        
        import threading
        thread = threading.Thread(target=run_download)
        thread.daemon = True
        thread.start()
        
        return download_id
    
    def verificar_descargas_interrumpidas(self, horas=1):
        tiempo_actual = datetime.now()
        descargas_a_reintentar = []
        
        for download_id, download_info in self.downloads.items():
            if download_info.get("state") == "processing":
                if "start_time" in download_info:
                    tiempo_inicio = datetime.fromisoformat(download_info["start_time"])
                    if (tiempo_actual - tiempo_inicio).total_seconds() > horas * 3600:
                        descargas_a_reintentar.append(download_id)
        
        for download_id in descargas_a_reintentar:
            info = self.downloads[download_id]
            
            if self.detectar_formato_volumen(info["format"]) == "volumen":
                self.downloads[download_id]["message"] = "🔄 Reiniciando descarga de volumen (formato detectado)"
                self.save_downloads()
            
            self.start_download(
                url=info["url"],
                download_range=info["range"],
                format_type=info["format"],
                start_value=info["start"],
                end_value=info["end"],
                max_reintentos=5
            )
        
        return len(descargas_a_reintentar)
    
    def cleanup_old_downloads(self, hours=24):
        current_time = datetime.now()
        to_delete = []
        
        for download_id, download_info in self.downloads.items():
            if "end_time" in download_info:
                end_time = datetime.fromisoformat(download_info["end_time"])
                if (current_time - end_time).total_seconds() > hours * 3600:
                    to_delete.append(download_id)
        
        for download_id in to_delete:
            del self.downloads[download_id]
        
        self.save_downloads()
    
    def get_all_downloads(self):
        self.cleanup_old_downloads()
        return self.downloads
