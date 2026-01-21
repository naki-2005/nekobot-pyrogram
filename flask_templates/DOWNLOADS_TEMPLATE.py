DOWNLOADS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Descargas Activas</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5em;
            text-align: center;
            border-radius: 10px 10px 0 0;
            margin: -25px -25px 25px -25px;
            position: relative;
        }
        
        h1 { 
            color: white; 
            text-align: center; 
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            font-size: 2.2em;
        }
        
        .nav { 
            margin-bottom: 25px; 
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        
        .nav a { 
            margin: 0 15px; 
            text-decoration: none; 
            color: white;
            font-weight: bold;
            padding: 12px 25px;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.2);
            transition: background 0.3s, transform 0.2s;
            display: inline-block;
            font-size: 1.1em;
        }
        
        .nav a:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            text-decoration: none;
        }
        
        .download-section {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px dashed #dee2e6;
        }
        
        .download-section h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            font-size: 1.8em;
        }
        
        .download-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .download-card { 
            border: 2px solid #e0e0e0; 
            padding: 25px; 
            border-radius: 12px; 
            background: white;
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
        }
        
        .download-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }
        
        .download-card.completed { 
            border-color: #28a745;
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        }
        
        .download-card.error { 
            border-color: #dc3545;
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        }
        
        .download-card.processing { 
            border-color: #007bff;
            background: linear-gradient(135deg, #cce7ff 0%, #b3d9ff 100%);
        }
        
        .download-card h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.5em;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.3s;
        }
        
        .delete-btn:hover {
            background: #c82333;
        }
        
        .progress-bar { 
            background: #e0e0e0; 
            height: 25px; 
            border-radius: 12px; 
            overflow: hidden; 
            margin: 20px 0; 
            position: relative;
        }
        
        .progress-fill { 
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            height: 100%; 
            transition: width 0.5s ease-out; 
            position: relative;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            font-size: 0.9em;
        }
        
        .stats { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
            gap: 15px; 
            margin: 20px 0;
        }
        
        .stat-item { 
            padding: 12px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 8px;
            border-left: 4px solid #667eea;
            text-align: center;
        }
        
        .stat-item strong {
            display: block;
            color: #333;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        
        .stat-item span {
            color: #666;
            font-size: 1.1em;
            font-weight: 600;
        }
        
        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 30px 0;
            padding: 20px;
            background: #e9ecef;
            border-radius: 10px;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .refresh-btn { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            padding: 12px 30px; 
            border-radius: 8px; 
            cursor: pointer;
            transition: transform 0.2s;
            font-size: 1.1em;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
        }
        
        .bulk-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .bulk-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.2s;
        }
        
        .bulk-btn.delete-all {
            background: #dc3545;
            color: white;
        }
        
        .bulk-btn.delete-all:hover {
            background: #c82333;
            transform: translateY(-2px);
        }
        
        .bulk-btn.delete-completed {
            background: #ffc107;
            color: black;
        }
        
        .bulk-btn.delete-completed:hover {
            background: #e0a800;
            transform: translateY(-2px);
        }
        
        .auto-refresh { 
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .auto-refresh input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        
        .auto-refresh label {
            color: #333;
            font-weight: 500;
            cursor: pointer;
        }
        
        .message-box {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 0.95em;
            line-height: 1.5;
        }
        
        .error-box {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .info-box {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .current-item {
            font-style: italic;
            color: #6c757d;
            margin: 10px 0;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.7);
            border-radius: 6px;
            border-left: 3px solid #17a2b8;
        }
        
        .no-downloads {
            text-align: center;
            padding: 60px 40px;
            color: #6c757d;
            font-size: 1.2em;
        }
        
        .no-downloads h3 {
            margin-bottom: 20px;
            font-size: 1.8em;
            color: #495057;
        }
        
        .no-downloads p {
            max-width: 600px;
            margin: 0 auto 30px auto;
            line-height: 1.6;
        }
        
        .manga-progress {
            font-size: 1.2em;
            font-weight: bold;
            margin: 15px 0;
            color: #495057;
            padding: 10px;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 6px;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
                margin: 10px;
            }
            
            .download-cards {
                grid-template-columns: 1fr;
            }
            
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .bulk-actions {
                justify-content: center;
            }
            
            .nav a {
                margin: 5px;
                display: block;
                width: calc(100% - 10px);
                box-sizing: border-box;
            }
            
            .stats {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📥 Descargas Activas</h1>
        </div>
        
        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/manga">📖 Manga</a>
            <a href="/utils">🛠️ Utilidades</a>
            <a href="/downloads">📥 Descargas</a>
        </div>

        <div class="controls">
            <button class="refresh-btn" onclick="location.reload()">
                🔄 Actualizar
            </button>
            
            <div class="bulk-actions">
                <button class="bulk-btn delete-completed" onclick="deleteAllCompleted()">
                    🗑️ Eliminar Completadas
                </button>
                <button class="bulk-btn delete-all" onclick="deleteAllDownloads()">
                    🗑️ Eliminar Todas
                </button>
            </div>
            
            <div class="auto-refresh">
                <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
                <label for="autoRefresh">Actualizar automáticamente cada 5 segundos</label>
            </div>
        </div>
        
        {% if manga_downloads %}
        <div class="download-section">
            <h2>📖 Descargas de Manga</h2>
            <div class="download-cards">
                {% for id, download in manga_downloads.items() %}
                <div class="download-card {{ download.state }}">
                    <h3>
                        📖 Manga Download
                        {% if download.state in ["completed", "error"] %}
                        <button class="delete-btn" onclick="deleteDownload('{{ id }}', 'manga')">×</button>
                        {% endif %}
                    </h3>
                    
                    <p><strong>URL:</strong> {{ download.url[:50] }}...</p>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ download.progress }}%">
                            <div class="progress-text">{{ download.progress }}%</div>
                        </div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <strong>Estado:</strong>
                            <span style="color: 
                                {% if download.state == 'completed' %}#28a745
                                {% elif download.state == 'error' %}#dc3545
                                {% else %}#007bff{% endif %};">
                                {{ download.state }}
                            </span>
                        </div>
                        <div class="stat-item">
                            <strong>Formato:</strong>
                            <span>{{ download.format }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Rango:</strong>
                            <span>{{ download.range }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Iniciado:</strong>
                            <span>{{ download.start_time[:19] }}</span>
                        </div>
                        {% if download.end_time %}
                        <div class="stat-item">
                            <strong>Finalizado:</strong>
                            <span>{{ download.end_time[:19] }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if download.message %}
                    <div class="current-item">{{ download.message }}</div>
                    {% endif %}
                    
                    {% if download.error %}
                    <div class="message-box error-box">
                        <strong>❌ Error:</strong> {{ download.error }}
                    </div>
                    {% endif %}
                    
                    {% if download.output %}
                    <div class="message-box info-box">
                        <strong>📋 Salida:</strong><br>
                        <small>{{ download.output[-200:] if download.output|length > 200 else download.output }}</small>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if mega_downloads %}
        <div class="download-section">
            <h2>📦 Descargas MEGA</h2>
            <div class="download-cards">
                {% for id, download in mega_downloads.items() %}
                <div class="download-card {{ download.state }}">
                    <h3>
                        📥 Descarga MEGA
                        {% if download.state in ["completed", "error"] %}
                        <button class="delete-btn" onclick="deleteDownload('{{ id }}', 'mega')">×</button>
                        {% endif %}
                    </h3>
                    
                    <p><strong>Enlace:</strong> {{ download.link[:50] }}...</p>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ download.progress }}%">
                            <div class="progress-text">{{ download.progress }}%</div>
                        </div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <strong>Estado:</strong>
                            <span>{{ download.state }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Progreso:</strong>
                            <span>{{ download.progress }}%</span>
                        </div>
                        <div class="stat-item">
                            <strong>Iniciado:</strong>
                            <span>{{ download.start_time[:19] }}</span>
                        </div>
                        {% if download.end_time %}
                        <div class="stat-item">
                            <strong>Finalizado:</strong>
                            <span>{{ download.end_time[:19] }}</span>
                        </div>
                        {% endif %}
                        {% if download.output_dir %}
                        <div class="stat-item">
                            <strong>Directorio:</strong>
                            <span>{{ download.output_dir|basename }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if download.message %}
                    <div class="current-item">{{ download.message }}</div>
                    {% endif %}
                    
                    {% if download.error %}
                    <div class="message-box error-box">
                        <strong>❌ Error:</strong> {{ download.error }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if doujin_downloads %}
        <div class="download-section">
            <h2>📚 Descargas de Doujins</h2>
            <div class="download-cards">
                {% for id, download in doujin_downloads.items() %}
                <div class="download-card {{ download.state }}">
                    <h3>
                        📖 CBZ{{ 's' if download.total > 1 else '' }} ({{ download.tipo|upper }})
                        {% if download.state in ["completed", "error"] %}
                        <button class="delete-btn" onclick="deleteDownload('{{ id }}', 'doujin')">×</button>
                        {% endif %}
                    </h3>
                    
                    <div class="manga-progress">
                        Progreso: {{ download.progress }} de {{ download.total }} CBZ{{ 's' if download.total > 1 else '' }}
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ (download.progress / download.total * 100) | round(1) }}%">
                            <div class="progress-text">{{ (download.progress / download.total * 100) | round(1) }}%</div>
                        </div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <strong>✅ Completados:</strong>
                            <span>{{ download.completados }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>❌ Errores:</strong>
                            <span>{{ download.errores }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>📊 Total:</strong>
                            <span>{{ download.total }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Iniciado:</strong>
                            <span>{{ download.start_time[:19] }}</span>
                        </div>
                        {% if download.end_time %}
                        <div class="stat-item">
                            <strong>Finalizado:</strong>
                            <span>{{ download.end_time[:19] }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if download.state == 'processing' %}
                    <div class="current-item">{{ download.current_item }}</div>
                    {% endif %}
                    
                    {% if download.state == 'completed' and download.resultados %}
                    <div class="message-box info-box">
                        <strong>📋 Resultados:</strong><br>
                        {% for resultado in download.resultados[:3] %}
                        <small>{{ resultado.codigo }}: 
                            <span style="color: {% if resultado.estado == 'completado' %}#28a745{% else %}#dc3545{% endif %};">
                                {{ resultado.estado }}
                            </span>
                            {% if resultado.error %} - {{ resultado.error }}{% endif %}
                        </small><br>
                        {% endfor %}
                        {% if download.resultados|length > 3 %}
                        <small>... y {{ download.resultados|length - 3 }} más</small>
                        {% endif %}
                    </div>
                    {% endif %}
                    
                    {% if download.error %}
                    <div class="message-box error-box">
                        <strong>❌ Error:</strong> {{ download.error }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        {% if downloads %}
        <div class="download-section">
            <h2>📦 Descargas Torrent</h2>
            <div class="download-cards">
                {% for id, download in downloads.items() %}
                <div class="download-card {{ download.state }}">
                    <h3>
                        {{ download.filename }}
                        {% if download.state in ["completed", "error"] %}
                        <button class="delete-btn" onclick="deleteDownload('{{ id }}', 'torrent')">×</button>
                        {% endif %}
                    </h3>
                    
                    <p><strong>Enlace:</strong> {{ download.link[:50] }}...</p>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ download.percent }}%">
                            <div class="progress-text">{{ download.percent }}%</div>
                        </div>
                    </div>
                    
                    <div class="stats">
                        <div class="stat-item">
                            <strong>Estado:</strong>
                            <span>{{ download.state }}</span>
                        </div>
                        <div class="stat-item">
                            <strong>Descargado:</strong>
                            <span>{{ (download.downloaded / (1024*1024)) | round(2) }} MB</span>
                        </div>
                        <div class="stat-item">
                            <strong>Total:</strong>
                            <span>{{ (download.total_size / (1024*1024)) | round(2) if download.total_size > 0 else 'Calculando...' }} MB</span>
                        </div>
                        <div class="stat-item">
                            <strong>Velocidad:</strong>
                            <span>{{ (download.speed / (1024*1024)) | round(2) }} MB/s</span>
                        </div>
                        <div class="stat-item">
                            <strong>Iniciado:</strong>
                            <span>{{ download.start_time[:19] }}</span>
                        </div>
                        {% if download.end_time %}
                        <div class="stat-item">
                            <strong>Completado:</strong>
                            <span>{{ download.end_time[:19] }}</span>
                        </div>
                        {% endif %}
                    </div>
                    
                    {% if download.error %}
                    <div class="message-box error-box">
                        <strong>❌ Error:</strong> {{ download.error }}
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if not downloads and not doujin_downloads and not mega_downloads and not manga_downloads %}
        <div class="no-downloads">
            <h3>📭 No hay descargas activas</h3>
            <p>Inicia una nueva descarga desde la página de Utilidades</p>
            <p>Las descargas de manga, torrents, MEGA y doujins aparecerán aquí</p>
            <a href="/utils" class="refresh-btn" style="display: inline-block; margin-top: 20px;">
                🛠️ Ir a Utilidades
            </a>
        </div>
        {% endif %}
    </div>

    <script>
        let autoRefreshInterval;
        
        function toggleAutoRefresh() {
            if (document.getElementById('autoRefresh').checked) {
                autoRefreshInterval = setInterval(() => {
                    location.reload();
                }, 5000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }
        
        async function deleteDownload(downloadId, downloadType) {
            if (!confirm('¿Eliminar esta descarga?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/downloads/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        download_id: downloadId,
                        type: downloadType
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(result.message);
                    location.reload();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error de conexión: ' + error.message);
            }
        }
        
        async function deleteAllCompleted() {
            if (!confirm('¿Eliminar todas las descargas completadas?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/downloads/delete-all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: 'all'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(result.message);
                    location.reload();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error de conexión: ' + error.message);
            }
        }
        
        async function deleteAllDownloads() {
            if (!confirm('¿Eliminar TODAS las descargas (incluyendo las activas)?')) {
                return;
            }
            
            try {
                const response = await fetch('/api/downloads/delete-all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        type: 'all'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(result.message);
                    location.reload();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error de conexión: ' + error.message);
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.download-card');
            cards.forEach(card => {
                const progressBar = card.querySelector('.progress-bar');
                if (progressBar) {
                    const progressFill = progressBar.querySelector('.progress-fill');
                    const progressText = progressBar.querySelector('.progress-text');
                    if (progressFill && progressText) {
                        const width = progressFill.style.width;
                        progressText.textContent = width;
                    }
                }
            });
        });
    </script>
</body>
</html>
"""
