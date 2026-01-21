UTILS_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Utilidades</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: #f5f5f5;
            min-height: 100vh;
        }
        
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 1em; 
            text-align: center; 
            position: relative;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header-title { 
            font-size: 1.5em; 
            margin-bottom: 10px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        
        .nav-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        
        .nav-btn {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 20px;
            color: white;
            text-decoration: none;
            font-size: 1em;
            transition: background 0.3s, transform 0.2s;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        .nav-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
            text-decoration: none;
        }
        
        .content { 
            padding: 2em; 
            max-width: 800px;
            margin: 0 auto;
        }
        
        .section {
            background: white;
            padding: 2em;
            border-radius: 15px;
            margin-bottom: 2em;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }
        
        h2 {
            color: #333;
            margin-top: 0;
            border-bottom: 3px solid #667eea;
            padding-bottom: 0.7em;
            margin-bottom: 1.2em;
            font-size: 1.8em;
        }
        
        h3 {
            color: #444;
            margin: 1.5em 0 1em 0;
            font-size: 1.4em;
        }
        
        form { 
            margin-bottom: 2em; 
            display: flex; 
            flex-direction: column; 
            gap: 1.2em; 
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5em;
        }
        
        label {
            font-weight: bold;
            color: #333;
            font-size: 1.1em;
            margin-bottom: 0.3em;
        }
        
        input[type="text"], 
        input[type="url"],
        select { 
            padding: 1em; 
            font-size: 1.1em; 
            border: 2px solid #ddd;
            border-radius: 8px;
            transition: border-color 0.3s, box-shadow 0.3s;
            width: 100%;
        }
        
        input[type="text"]:focus, 
        input[type="url"]:focus,
        select:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 0.8em;
            margin: 1em 0;
        }
        
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .checkbox-label {
            font-size: 1em;
            color: #555;
            cursor: pointer;
        }
        
        button { 
            padding: 1em 2em; 
            font-size: 1.1em; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: bold;
            margin-top: 1em;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .info-text {
            background: #e3f2fd;
            padding: 1em;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
            margin: 1.5em 0;
            font-size: 1em;
            line-height: 1.6;
        }
        
        .info-text strong {
            color: #0d47a1;
        }
        
        .file-input {
            padding: 1em;
            border: 2px dashed #667eea;
            border-radius: 8px;
            background: #f8f9fa;
            cursor: pointer;
            transition: background 0.3s;
            text-align: center;
            color: #555;
        }
        
        .file-input:hover {
            background: #e9ecef;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 1em;
            border-radius: 8px;
            border: 1px solid #f5c6cb;
            margin: 1em 0;
            display: none;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 1em;
            border-radius: 8px;
            border: 1px solid #c3e6cb;
            margin: 1em 0;
            display: none;
        }
        
        .hidden {
            display: none;
        }
        
        @media (max-width: 768px) {
            .content {
                padding: 1em;
            }
            
            .section {
                padding: 1.5em;
            }
            
            .nav-buttons {
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }
            
            .nav-btn {
                width: 90%;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            🛠️ Utilidades - Servidor Flask de Neko Bot
        </div>
        <div class="nav-buttons">
            <a href="/" class="nav-btn">🏠 Inicio</a>
            <a href="/manga" class="nav-btn">📖 Manga</a>
            <a href="/utils" class="nav-btn">🛠️ Utilidades</a>
            <a href="/downloads" class="nav-btn">📥 Descargas</a>
        </div>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>📤 Subir archivos al servidor</h2>
            
            <div class="error-message" id="uploadError"></div>
            <div class="success-message" id="uploadSuccess"></div>
            
            <form id="uploadForm">
                <div class="form-group">
                    <label for="destinationPath">Ruta de destino:</label>
                    <input type="text" 
                           id="destinationPath" 
                           name="destination_path" 
                           placeholder="Ingrese aquí la ruta destino, si se deja vacío quedará en el directorio base vault_files">
                </div>
                
                <div class="checkbox-group">
                    <input type="checkbox" id="useCustomName" name="use_custom_name">
                    <label for="useCustomName" class="checkbox-label">Nombre personalizado</label>
                </div>
                
                <div class="form-group hidden" id="customNameContainer">
                    <label for="customName">Nombre personalizado:</label>
                    <input type="text" 
                           id="customName" 
                           name="custom_name" 
                           placeholder="Ingrese acá el nombre personalizado del archivo">
                </div>
                
                <div class="form-group">
                    <label for="files">Seleccionar archivos:</label>
                    <input type="file" 
                           id="files" 
                           name="files" 
                           class="file-input" 
                           multiple 
                           required>
                </div>
                
                <button type="submit" id="uploadBtn">📤 Subir Archivos</button>
            </form>
            
            <div class="info-text">
                <strong>💡 Información:</strong>
                <ul style="margin-top: 10px; padding-left: 20px;">
                    <li>Puedes seleccionar múltiples archivos a la vez</li>
                    <li>Si no especificas ruta, los archivos se guardarán en <code>vault_files/</code></li>
                    <li>El nombre personalizado solo aplica cuando subes un solo archivo</li>
                    <li>Formatos soportados: cualquier tipo de archivo</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>📥 Descargar archivos al servidor</h2>
            
            <div class="error-message" id="downloadError"></div>
            <div class="success-message" id="downloadSuccess"></div>
            
            <form id="downloadForm">
                <div class="form-group">
                    <label for="downloadUrl">Enlace para descargar:</label>
                    <input type="url" 
                           id="downloadUrl" 
                           name="download_url" 
                           placeholder="https://ejemplo.com/archivo.zip"
                           required>
                </div>
                
                <div class="form-group">
                    <label for="downloadDestinationPath">Ruta de destino (opcional):</label>
                    <input type="text" 
                           id="downloadDestinationPath" 
                           name="destination_path" 
                           placeholder="Ingrese aquí la ruta destino, si se deja vacío quedará en el directorio base vault_files">
                </div>
                
                <div class="form-group">
                    <label for="downloadCustomName">Nombre personalizado (opcional):</label>
                    <input type="text" 
                           id="downloadCustomName" 
                           name="custom_name" 
                           placeholder="Nombre personalizado del archivo">
                </div>
                
                <button type="submit" id="downloadBtn">📥 Descargar Archivo</button>
            </form>
            
            <div class="info-text">
                <strong>💡 Información:</strong>
                <ul style="margin-top: 10px; padding-left: 20px;">
                    <li>Soporta cualquier tipo de archivo accesible por URL</li>
                    <li>Si no especificas nombre, se usará el nombre original del archivo</li>
                    <li>La descarga se realiza directamente al servidor</li>
                    <li>Puedes descargar imágenes, documentos, archivos comprimidos, etc.</li>
                </ul>
            </div>
        </div>

        <div class="section">
            <h2>🔗 Descargar desde Magnet Link</h2>
            <form action="/magnet" method="post">
                <div class="form-group">
                    <input type="text" name="magnet" placeholder="Magnet link o URL .torrent" required>
                </div>
                <button type="submit">🚀 Iniciar descarga Torrent</button>
            </form>
        </div>

        <div class="section">
            <h2>🔞 Descargar Doujin(s)</h2>
            <form action="/crear_cbz" method="post">
                <div class="form-group">
                    <input type="text" name="codigo" placeholder="Código(s) separados por coma (ej: 123,456,789)" required>
                </div>
                <div class="form-group">
                    <select name="tipo" required>
                        <option value="nh">NHentai</option>
                        <option value="h3">3Hentai</option>
                        <option value="hito">Hitomi.la</option>
                    </select>
                </div>
                <button type="submit">📚 Crear CBZ(s)</button>
            </form>
            <div class="info-text">
                💡 Puedes ingresar múltiples códigos separados por comas (ej: 123456,789012,345678).
                La descarga se procesará en segundo plano y podrás ver el progreso en la página de descargas.
            </div>
        </div>

        <div class="section">
            <h2>📥 Descargar desde MEGA</h2>
            <form action="/mega" method="post">
                <div class="form-group">
                    <input type="text" name="mega_link" placeholder="Enlace MEGA (https://mega.nz/...)" required>
                </div>
                <button type="submit">☁️ Iniciar descarga MEGA</button>
            </form>
            <div class="info-text">
                💡 Ingresa un enlace MEGA para descargar archivos. La descarga se procesará en segundo plano.
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const useCustomNameCheckbox = document.getElementById('useCustomName');
            const customNameContainer = document.getElementById('customNameContainer');
            
            useCustomNameCheckbox.addEventListener('change', function() {
                if (this.checked) {
                    customNameContainer.classList.remove('hidden');
                } else {
                    customNameContainer.classList.add('hidden');
                }
            });
            
            const uploadForm = document.getElementById('uploadForm');
            const uploadError = document.getElementById('uploadError');
            const uploadSuccess = document.getElementById('uploadSuccess');
            const uploadBtn = document.getElementById('uploadBtn');
            
            uploadForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const filesInput = document.getElementById('files');
                if (!filesInput.files || filesInput.files.length === 0) {
                    showMessage(uploadError, 'Seleccionar un archivo es obligatorio');
                    return;
                }
                
                uploadBtn.disabled = true;
                uploadBtn.textContent = 'Subiendo...';
                
                const formData = new FormData();
                formData.append('destination_path', document.getElementById('destinationPath').value);
                
                if (useCustomNameCheckbox.checked) {
                    formData.append('custom_name', document.getElementById('customName').value);
                }
                
                for (let i = 0; i < filesInput.files.length; i++) {
                    formData.append('files', filesInput.files[i]);
                }
                
                try {
                    const response = await fetch('/upload_file', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage(uploadSuccess, result.message);
                        uploadForm.reset();
                        customNameContainer.classList.add('hidden');
                        useCustomNameCheckbox.checked = false;
                    } else {
                        showMessage(uploadError, result.message);
                    }
                } catch (error) {
                    showMessage(uploadError, 'Error de conexión: ' + error.message);
                } finally {
                    uploadBtn.disabled = false;
                    uploadBtn.textContent = '📤 Subir Archivos';
                }
            });
            
            const downloadForm = document.getElementById('downloadForm');
            const downloadError = document.getElementById('downloadError');
            const downloadSuccess = document.getElementById('downloadSuccess');
            const downloadBtn = document.getElementById('downloadBtn');
            
            downloadForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const downloadUrl = document.getElementById('downloadUrl').value.trim();
                if (!downloadUrl) {
                    showMessage(downloadError, 'El enlace está vacío');
                    return;
                }
                
                downloadBtn.disabled = true;
                downloadBtn.textContent = 'Descargando...';
                
                const formData = new FormData();
                formData.append('download_url', downloadUrl);
                formData.append('destination_path', document.getElementById('downloadDestinationPath').value);
                formData.append('custom_name', document.getElementById('downloadCustomName').value);
                
                try {
                    const response = await fetch('/download_file', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showMessage(downloadSuccess, result.message);
                        downloadForm.reset();
                    } else {
                        showMessage(downloadError, result.message);
                    }
                } catch (error) {
                    showMessage(downloadError, 'Error de conexión: ' + error.message);
                } finally {
                    downloadBtn.disabled = false;
                    downloadBtn.textContent = '📥 Descargar Archivo';
                }
            });
            
            function showMessage(element, message) {
                element.textContent = message;
                element.style.display = 'block';
                
                setTimeout(() => {
                    element.style.display = 'none';
                }, 5000);
            }
        });
    </script>
</body>
</html>
"""
