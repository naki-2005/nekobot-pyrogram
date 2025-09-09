MAIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Explorador de Archivos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; margin: 0; padding: 0; box-sizing: border-box; background-color: #f8f9fa; }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 1em; 
            text-align: center; 
            position: relative;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-title { 
            font-size: 1.2em; 
            margin-bottom: 10px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        .header a { 
            color: white; 
            text-decoration: none;
            font-weight: bold;
            transition: opacity 0.3s;
        }
        .header a:hover { opacity: 0.8; }
        .nav-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 10px;
        }
        .nav-btn {
            background: rgba(255,255,255,0.2);
            padding: 8px 16px;
            border-radius: 20px;
            color: white;
            text-decoration: none;
            font-size: 0.9em;
            transition: background 0.3s;
            border: 1px solid rgba(255,255,255,0.3);
        }
        .nav-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        .content { 
            padding: 2em; 
            max-width: 1200px;
            margin: 0 auto;
        }
        .section {
            background: white;
            padding: 1.5em;
            border-radius: 10px;
            margin-bottom: 2em;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            margin-top: 0;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5em;
        }
        form { margin-bottom: 1em; display: flex; flex-direction: column; gap: 0.5em; }
        input[type="file"], input[type="text"], select { 
            padding: 0.8em; 
            font-size: 1em; 
            border: 2px solid #ddd;
            border-radius: 6px;
            transition: border-color 0.3s;
        }
        input[type="file"]:focus, input[type="text"]:focus, select:focus {
            border-color: #667eea;
            outline: none;
        }
        button { 
            padding: 0.8em; 
            font-size: 1em; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        ul { list-style-type: none; padding: 0; }
        li { 
            margin: 0.5em 0; 
            word-break: break-word;
            padding: 0.8em;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
        }
        .file-info {
            flex: 1;
            min-width: 200px;
        }
        .file-actions {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        a { text-decoration: none; color: #667eea; font-weight: 500; }
        a:hover { text-decoration: underline; }
        .delete-btn, .rename-btn, .extract-btn, .gallery-btn { 
            color: white; 
            border: none; 
            padding: 0.5em 1em; 
            border-radius: 4px; 
            cursor: pointer;
            font-size: 0.9em;
            text-decoration: none;
            display: inline-block;
        }
        .delete-btn { background-color: #dc3545; }
        .rename-btn { background-color: #ffc107; color: black; }
        .extract-btn { background-color: #28a745; }
        .gallery-btn { background-color: #17a2b8; }
        .compress-toggle { 
            margin-top: 1em;
            background: #28a745;
        }
        .select-all {
            margin-bottom: 10px;
            background: #6c757d;
        }
        
        .file-list {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 1em;
        }
    </style>
    <script>
        function toggleCompress() {
            const section = document.getElementById("compress-section");
            section.style.display = section.style.display === "none" ? "block" : "none";
        }
        
        function toggleRename(id) {
            const input = document.getElementById("rename-" + id);
            const btn = document.getElementById("rename-" + id + "-btn");
            input.style.display = input.style.display === "none" ? "inline" : "none";
            btn.style.display = btn.style.display === "none" ? "inline" : "none";
        }
        
        function selectAllFiles(selectAll) {
            const checkboxes = document.querySelectorAll('input[name="selected"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAll;
            });
        }
    </script>
</head>
<body>
    <div class="header">
        <div class="header-title">
            Servidor Flask de Neko Bot creado por <a href="https://t.me/nakigeplayer" target="_blank">Naki</a>
        </div>
        <div class="nav-buttons">
            <a href="/" class="nav-btn">🏠 Inicio</a>
            <a href="/utils" class="nav-btn">🛠️ Utilidades</a>
            <a href="/downloads" class="nav-btn">📥 Descargas</a>
            {% if has_images %}
            <a href="/gallery?path={{ current_path }}" class="nav-btn">🖼️ Galería</a>
            {% endif %}
        </div>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>📤 Subir archivo</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file">
                <button type="submit">Subir archivo</button>
            </form>
        </div>

        <div class="section">
            <h2>🗜️ Comprimir archivos</h2>
            <button class="compress-toggle" onclick="toggleCompress()">Mostrar opciones de compresión</button>
            <div id="compress-section" style="display:none; margin-top: 1em;">
                <button type="button" class="select-all" onclick="selectAllFiles(true)">Seleccionar todo</button>
                <button type="button" class="select-all" onclick="selectAllFiles(false)">Deseleccionar todo</button>
                <form action="/compress" method="post">
                    <input type="text" name="archive_name" placeholder="Nombre del archivo .7z" required>
                    <div class="file-list">
                        {% for item in items %}
                            <div>
                                <input type="checkbox" name="selected" value="{{ item['full_path'] }}" id="file-{{ loop.index }}">
                                <label for="file-{{ loop.index }}">
                                    {% if item['is_dir'] %}
                                        📂 {{ item['name'] }}/
                                    {% else %}
                                        📄 {{ item['name'] }} — {{ item['size_mb'] }} MB
                                    {% endif %}
                                </label>
                            </div>
                        {% endfor %}
                    </div>
                    <button type="submit">Comprimir seleccionados</button>
                </form>
            </div>
        </div>

        <div class="section">
            <h2>📁 Archivos guardados</h2>
            <ul>
            {% for item in items %}
                <li>
                    <div class="file-info">
                        {% if item['is_dir'] %}
                            📂 <a href="/browse?path={{ item['rel_path'] }}">{{ item['name'] }}/</a>
                        {% else %}
                            📄 <a href="/download?path={{ item['rel_path'] }}">{{ item['name'] }}</a> — {{ item['size_mb'] }} MB
                        {% endif %}
                    </div>
                    <div class="file-actions">
                        <form action="/delete" method="post" style="display:inline;">
                            <input type="hidden" name="path" value="{{ item['full_path'] }}">
                            <button class="delete-btn" onclick="return confirm('¿Eliminar {{ item['name'] }}?')">Eliminar</button>
                        </form>
                        <button class="rename-btn" onclick="toggleRename('{{ loop.index }}')">✏️ Renombrar</button>
                        {% if item['name'].lower().endswith('.7z') or item['name'].lower().endswith('.cbz') or item['name'].lower().endswith('.zip') %}
                        <form action="/extract" method="post" style="display:inline;">
                            <input type="hidden" name="path" value="{{ item['full_path'] }}">
                            <button class="extract-btn" onclick="return confirm('¿Descomprimir {{ item['name'] }}?')">📦 Descomprimir</button>
                        </form>
                        {% endif %}
                        {% if item['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')) %}
                        <a href="/{{ item['rel_path'] }}" class="gallery-btn" target="_blank">🖼️ Ver</a>
                        {% endif %}
                        <form action="/rename" method="post" style="display:inline;">
                            <input type="hidden" name="old_path" value="{{ item['full_path'] }}">
                            <input type="text" name="new_name" id="rename-{{ loop.index }}" style="display:none; width: 200px;" placeholder="Nuevo nombre">
                            <button type="submit" style="display:none;" id="rename-{{ loop.index }}-btn">✅</button>
                        </form>
                    </div>
                </li>
            {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
"""
