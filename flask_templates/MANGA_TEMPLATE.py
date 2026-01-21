MANGA_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Descargar Manga de MangaDex</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin-bottom: 15px;
            font-size: 1.8em;
        }
        
        .nav {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        
        .nav a {
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 20px;
            transition: background 0.3s;
        }
        
        .nav a:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .form-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px dashed #dee2e6;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        
        .url-input {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .url-input:focus {
            border-color: #667eea;
            outline: none;
        }
        
        .url-input::placeholder {
            color: #aaa;
            font-style: italic;
        }
        
        .select-group {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        
        .select-box {
            flex: 1;
            min-width: 250px;
        }
        
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            background: white;
            cursor: pointer;
            transition: border-color 0.3s;
        }
        
        select:focus {
            border-color: #667eea;
            outline: none;
        }
        
        .range-inputs {
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #dee2e6;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }
        
        .range-inputs.active {
            display: flex;
        }
        
        .range-input {
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            width: 120px;
        }
        
        .range-input:focus {
            border-color: #667eea;
            outline: none;
        }
        
        .download-btn {
            display: block;
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 20px;
        }
        
        .download-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.3);
        }
        
        .download-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .info-box {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
            margin-top: 20px;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .result-message {
            display: none;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        @media (max-width: 768px) {
            .select-group {
                flex-direction: column;
                gap: 20px;
            }
            
            .select-box {
                min-width: 100%;
            }
            
            .container {
                padding: 15px;
            }
            
            .header {
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📖 Descargar Manga de MangaDex</h1>
            <div class="nav">
                <a href="/">🏠 Inicio</a>
                <a href="/manga">📖 Manga</a>
                <a href="/utils">🛠️ Utilidades</a>
                <a href="/downloads">📥 Descargas</a>
            </div>
        </div>
        
        <div class="form-section">
            <div class="form-group">
                <label for="mangaUrl">🔗 URL de MangaDex:</label>
                <input type="text" 
                       id="mangaUrl" 
                       class="url-input" 
                       placeholder="https://mangadex.org/title/... o https://mangadex.org/chapter/..."
                       value="">
            </div>
            
            <div class="select-group">
                <div class="select-box">
                    <label for="downloadRange">📊 Rango de Descarga:</label>
                    <select id="downloadRange" onchange="toggleRangeInputs()">
                        <option value="all">Todo el manga</option>
                        <option value="from-chapter">A partir de X Capítulo</option>
                        <option value="from-volume">A partir de X Volumen</option>
                        <option value="chapters-range">De X Capítulo a X Capítulo</option>
                        <option value="chapter-to-volume">De X Capítulo a X Volumen</option>
                        <option value="volumes-range">De X Volumen a X Volumen</option>
                        <option value="volume-to-chapter">De X Volumen a X Capítulo</option>
                        <option value="specific-chapter">Capítulo específico</option>
                        <option value="specific-volume">Volumen específico</option>
                    </select>
                    
                    <div id="rangeInputs" class="range-inputs">
                        <input type="number" id="startValue" class="range-input" placeholder="Inicio" min="1">
                        <span id="rangeText">a</span>
                        <input type="number" id="endValue" class="range-input" placeholder="Fin" min="1">
                    </div>
                </div>
                
                <div class="select-box">
                    <label for="saveFormat">💾 Formato de Guardado:</label>
                    <select id="saveFormat">
                        <option value="cbz-volume">Un Volumen como CBZ</option>
                        <option value="cbz">Cada capítulo como CBZ</option>
                        <option value="cbz-single">Todo en un CBZ</option>
                        <option value="pdf">Cada capítulo como PDF</option>
                        <option value="pdf-volume">Un volumen como PDF</option>
                        <option value="pdf-single">Todo en un PDF</option>
                        <option value="raw">Imágenes sueltas</option>
                        <option value="raw-volume">Imágenes por volumen</option>
                        <option value="raw-single">Todas las imágenes en una carpeta</option>
                        <option value="cb7">Cada capítulo como CB7</option>
                        <option value="cb7-volume">Un volumen como CB7</option>
                        <option value="cb7-single">Todo en un CB7</option>
                        <option value="epub">Cada capítulo como EPUB</option>
                        <option value="epub-volume">Un volumen como EPUB</option>
                        <option value="epub-single">Todo en un EPUB</option>
                    </select>
                </div>
            </div>
            
            <button id="downloadButton" class="download-btn" onclick="startDownload()">
                🚀 Iniciar Descarga
            </button>
            
            <div class="loading" id="loadingIndicator">
                <div class="spinner"></div>
                <p>Procesando descarga...</p>
                <p id="progressText">Esto puede tomar varios minutos</p>
            </div>
            
            <div class="result-message" id="resultMessage"></div>
        </div>
        
        <div class="info-box">
            <strong>💡 Información:</strong>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li>Las descargas se guardan en la carpeta <code>vault_files/Mangas/</code></li>
                <li>Para descargar todo el manga, selecciona "Todo el manga"</li>
                <li>Para un capítulo específico, usa la opción "Capítulo específico"</li>
                <li>Puedes ver el progreso en la página de <a href="/downloads">Descargas</a></li>
                <li>CBZ es un formato comprimido similar a ZIP, ideal para manga</li>
            </ul>
        </div>
    </div>

    <script>
        function toggleRangeInputs() {
            const rangeSelect = document.getElementById('downloadRange');
            const rangeInputs = document.getElementById('rangeInputs');
            const startValue = document.getElementById('startValue');
            const endValue = document.getElementById('endValue');
            const rangeText = document.getElementById('rangeText');
            
            rangeInputs.classList.remove('active');
            endValue.style.display = 'block';
            rangeText.style.display = 'inline';
            
            switch(rangeSelect.value) {
                case 'all':
                    break;
                    
                case 'from-chapter':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'en adelante';
                    endValue.style.display = 'none';
                    rangeText.style.display = 'inline';
                    startValue.placeholder = 'Número de capítulo';
                    break;
                    
                case 'from-volume':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'en adelante';
                    endValue.style.display = 'none';
                    rangeText.style.display = 'inline';
                    startValue.placeholder = 'Número de volumen';
                    break;
                    
                case 'chapters-range':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'a';
                    startValue.placeholder = 'Capítulo inicio';
                    endValue.placeholder = 'Capítulo fin';
                    break;
                    
                case 'chapter-to-volume':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'al volumen';
                    startValue.placeholder = 'Capítulo inicio';
                    endValue.placeholder = 'Volumen fin';
                    break;
                    
                case 'volumes-range':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'a';
                    startValue.placeholder = 'Volumen inicio';
                    endValue.placeholder = 'Volumen fin';
                    break;
                    
                case 'volume-to-chapter':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = 'al capítulo';
                    startValue.placeholder = 'Volumen inicio';
                    endValue.placeholder = 'Capítulo fin';
                    break;
                    
                case 'specific-chapter':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = '(único)';
                    endValue.style.display = 'none';
                    startValue.placeholder = 'Número de capítulo';
                    break;
                    
                case 'specific-volume':
                    rangeInputs.classList.add('active');
                    rangeText.textContent = '(único)';
                    endValue.style.display = 'none';
                    startValue.placeholder = 'Número de volumen';
                    break;
            }
        }
        
        async function startDownload() {
            const url = document.getElementById('mangaUrl').value.trim();
            const rangeSelect = document.getElementById('downloadRange').value;
            const formatSelect = document.getElementById('saveFormat').value;
            const startValue = document.getElementById('startValue').value;
            const endValue = document.getElementById('endValue').value;
            
            if (!url) {
                showResult('Por favor, ingresa una URL de MangaDex', 'error');
                return;
            }
            
            if (!url.includes('mangadex.org')) {
                showResult('La URL debe ser de MangaDex (mangadex.org)', 'error');
                return;
            }
            
            const downloadBtn = document.getElementById('downloadButton');
            const loadingIndicator = document.getElementById('loadingIndicator');
            const progressText = document.getElementById('progressText');
            
            downloadBtn.disabled = true;
            downloadBtn.textContent = 'Procesando...';
            loadingIndicator.style.display = 'block';
            
            const formData = new FormData();
            formData.append('url', url);
            formData.append('range', rangeSelect);
            formData.append('format', formatSelect);
            formData.append('start', startValue);
            formData.append('end', endValue);
            
            try {
                const response = await fetch('/manga/download', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResult(`✅ ${result.message}<br><br>ID de descarga: ${result.download_id}<br><a href="/downloads">Ver progreso aquí</a>`, 'success');
                } else {
                    showResult(`❌ ${result.message}`, 'error');
                }
            } catch (error) {
                showResult(`❌ Error de conexión: ${error.message}`, 'error');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.textContent = '🚀 Iniciar Descarga';
                loadingIndicator.style.display = 'none';
            }
        }
        
        function showResult(message, type) {
            const resultDiv = document.getElementById('resultMessage');
            resultDiv.className = `result-message ${type}`;
            resultDiv.innerHTML = message;
            resultDiv.style.display = 'block';
            
            setTimeout(() => {
                resultDiv.style.display = 'none';
            }, 10000);
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            toggleRangeInputs();
        });
    </script>
</body>
</html>
"""
