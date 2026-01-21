NEW_MAIN_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Explorador de Archivos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { font-family: Arial; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 20px; }
        
        .folder { margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
        .folder-header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 15px; 
            cursor: pointer; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            transition: background 0.3s;
        }
        .folder-header:hover { background: linear-gradient(135deg, #5a6fd8 0%, #6a3f8f 100%); }
        .folder-content { padding: 15px; display: none; }
        
        .file-item { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 12px 15px; 
            border-bottom: 1px solid #eee; 
            transition: background 0.2s;
        }
        .file-item:hover { background: #f8f9fa; }
        .file-item:last-child { border-bottom: none; }
        
        .file-info { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            flex: 1; 
            min-width: 0;
        }
        .file-index { 
            background: #667eea; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 12px; 
            font-size: 12px; 
            flex-shrink: 0;
        }
        .file-name { 
            flex: 1; 
            min-width: 0; 
            overflow: hidden; 
            text-overflow: ellipsis; 
            white-space: nowrap;
            font-weight: 500;
        }
        .file-name a {
            color: #333;
            text-decoration: none;
        }
        .file-name a:hover {
            color: #667eea;
            text-decoration: underline;
        }
        .file-size { 
            color: #666; 
            font-size: 12px; 
            flex-shrink: 0;
            margin-left: 10px;
        }
        .file-type { 
            color: #888; 
            font-size: 11px; 
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            margin-left: 5px;
        }
        
        .file-actions { 
            display: flex; 
            gap: 8px; 
            flex-shrink: 0;
        }
        
        .action-btn {
            padding: 6px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 4px;
            min-width: 28px;
            justify-content: center;
        }
        .btn-download { background: #28a745; color: white; }
        .btn-download:hover { background: #218838; }
        .btn-gallery { background: #17a2b8; color: white; }
        .btn-gallery:hover { background: #138496; }
        .btn-create-cbz { background: #9c27b0; color: white; }
        .btn-create-cbz:hover { background: #7b1fa2; }
        .btn-rename { background: #ffc107; color: black; }
        .btn-rename:hover { background: #e0a800; }
        .btn-delete { background: #dc3545; color: white; }
        .btn-delete:hover { background: #c82333; }
        .btn-compress { background: #6f42c1; color: white; }
        .btn-compress:hover { background: #5a369c; }
        .btn-move { background: #20c997; color: white; }
        .btn-move:hover { background: #1ba87e; }
        .btn-telegram { background: #0088cc; color: white; }
        .btn-telegram:hover { background: #0077b3; }
        
        .nav { 
            margin-bottom: 20px; 
            display: flex; 
            gap: 10px; 
            flex-wrap: wrap;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .nav a { 
            color: white;
            text-decoration: none; 
            padding: 8px 16px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px; 
            transition: transform 0.2s;
        }
        .nav a:hover {
            transform: translateY(-2px);
            text-decoration: none;
        }
        
        .total-files { 
            background: #e9ecef; 
            padding: 12px; 
            border-radius: 4px; 
            margin: 10px 0; 
            text-align: center;
            font-weight: 500;
            color: #495057;
        }
        
        .bulk-actions {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
        }
        
        .bulk-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-select-all { background: #6c757d; color: white; }
        .btn-select-all:hover { background: #5a6268; transform: translateY(-2px); }
        .btn-delete-empty { background: #fd7e14; color: white; }
        .btn-delete-empty:hover { background: #e06c10; transform: translateY(-2px); }
        .btn-compress-selected { background: #6f42c1; color: white; }
        .btn-compress-selected:hover { background: #5a369c; transform: translateY(-2px); }
        .btn-merge-cbz { background: #9c27b0; color: white; }
        .btn-merge-cbz:hover { background: #7b1fa2; transform: translateY(-2px); }
        .btn-move-selected { background: #20c997; color: white; }
        .btn-move-selected:hover { background: #1ba87e; transform: translateY(-2px); }
        .btn-delete-selected { background: #dc3545; color: white; }
        .btn-delete-selected:hover { background: #c82333; transform: translateY(-2px); }
        
        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-right: 15px;
        }
        .checkbox-item input[type="checkbox"] {
            width: 16px;
            height: 16px;
            cursor: pointer;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-title {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 20px;
        }
        .modal-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-confirm { background: #28a745; color: white; }
        .btn-cancel { background: #6c757d; color: white; }
        
        select, input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            margin-bottom: 15px;
        }
        select:focus, input[type="text"]:focus {
            border-color: #667eea;
            outline: none;
        }
        
        .folder-selector {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 15px;
        }
        .folder-option {
            padding: 8px;
            cursor: pointer;
            border-radius: 4px;
            margin-bottom: 5px;
            transition: background 0.2s;
        }
        .folder-option:hover {
            background: #f8f9fa;
        }
        .folder-option.selected {
            background: #e3f2fd;
            border-left: 4px solid #667eea;
        }
        
        .cbz-selector {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 15px;
        }
        .cbz-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        .cbz-item:last-child {
            border-bottom: none;
        }
        .cbz-item-handle {
            cursor: move;
            color: #666;
        }
        .cbz-item-name {
            flex: 1;
            font-size: 14px;
        }
        .cbz-item-checkbox input[type="checkbox"] {
            width: 16px;
            height: 16px;
        }
        
        .sortable-ghost {
            opacity: 0.4;
        }
        .sortable-drag {
            background: #f8f9fa;
        }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .file-actions { flex-wrap: wrap; justify-content: flex-end; }
            .action-btn { padding: 5px 8px; font-size: 11px; }
            .nav { flex-direction: column; }
            .nav a { text-align: center; }
            .bulk-actions { flex-direction: column; }
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.14.0/Sortable.min.js"></script>
    <script>
        let selectedItems = new Set();
        let cbzFilesCache = [];
        
        function toggleFolder(folderName) {
            const content = document.getElementById('content-' + folderName);
            const icon = document.getElementById('icon-' + folderName);
            if (content.style.display === 'block') {
                content.style.display = 'none';
                icon.textContent = '▶';
            } else {
                content.style.display = 'block';
                icon.textContent = '▼';
            }
        }
        
        function selectItem(itemPath, checkbox) {
            if (checkbox.checked) {
                selectedItems.add(itemPath);
            } else {
                selectedItems.delete(itemPath);
            }
            updateBulkActions();
        }
        
        function selectAllItems() {
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                if (checkbox.dataset.path) {
                    selectedItems.add(checkbox.dataset.path);
                }
            });
            updateBulkActions();
        }
        
        function updateBulkActions() {
            const count = selectedItems.size;
            document.querySelectorAll('.bulk-btn').forEach(btn => {
                if (btn.classList.contains('btn-select-all')) return;
                btn.disabled = count === 0;
            });
            
            if (count > 0) {
                document.getElementById('selectedCount').textContent = ` (${count} seleccionados)`;
            } else {
                document.getElementById('selectedCount').textContent = '';
            }
        }
        
        function showRenameInput(filePath, currentName) {
            const newName = prompt("Nuevo nombre:", currentName);
            if (newName && newName !== currentName) {
                const form = document.getElementById('rename-form');
                document.getElementById('old_path').value = filePath;
                document.getElementById('new_name').value = newName;
                form.submit();
            }
        }
        
        function showMoveDialog() {
            if (selectedItems.size === 0) return;
            
            fetch('/api/folders')
                .then(response => response.json())
                .then(folders => {
                    const modal = document.getElementById('moveModal');
                    const list = document.getElementById('folderList');
                    list.innerHTML = '';
                    
                    folders.forEach(folder => {
                        const div = document.createElement('div');
                        div.className = 'folder-option';
                        div.textContent = folder;
                        div.onclick = function() {
                            document.querySelectorAll('.folder-option').forEach(el => el.classList.remove('selected'));
                            this.classList.add('selected');
                            document.getElementById('selectedFolder').value = folder;
                        };
                        list.appendChild(div);
                    });
                    
                    modal.style.display = 'flex';
                    document.getElementById('newFolderInput').style.display = 'none';
                });
        }
        
        function showCompressDialog() {
            if (selectedItems.size === 0) return;
            
            const modal = document.getElementById('compressModal');
            modal.style.display = 'flex';
            document.getElementById('archiveName').value = `archivo_${Date.now()}`;
        }

        async function showMergeCbzDialog() {
            const modal = document.getElementById('mergeCbzModal');
            
            if (selectedItems.size === 0) {
                alert('Selecciona al menos un archivo CBZ');
                return;
            }
            
            const cbzFiles = [];
            const selectedPaths = Array.from(selectedItems);
            
            for (const path of selectedPaths) {
                if (path.toLowerCase().endsWith('.cbz')) {
                    const name = path.split('/').pop();
                    cbzFiles.push({
                        path: path,
                        name: name
                    });
                }
            }
            
            if (cbzFiles.length === 0) {
                alert('No hay archivos CBZ seleccionados');
                return;
            }
            
            if (cbzFiles.length < 2) {
                alert('Selecciona al menos 2 archivos CBZ para combinar');
                return;
            }
            
            const list = document.getElementById('cbzList');
            list.innerHTML = '';
            
            cbzFiles.forEach(cbzFile => {
                const div = document.createElement('div');
                div.className = 'cbz-item';
                div.dataset.path = cbzFile.path;
                
                div.innerHTML = `
                    <div class="cbz-item-handle">☰</div>
                    <div class="cbz-item-name">${cbzFile.name}</div>
                    <div class="cbz-item-checkbox">
                        <input type="checkbox" checked onchange="toggleCbzSelection(this)">
                    </div>
                `;
                
                list.appendChild(div);
            });
            
            modal.style.display = 'flex';
            document.getElementById('mergedCbzName').value = `combinado_${Date.now()}.cbz`;
            
            Sortable.create(list, {
                handle: '.cbz-item-handle',
                ghostClass: 'sortable-ghost',
                dragClass: 'sortable-drag',
                animation: 150
            });
        }
        
        function toggleCbzSelection(checkbox) {
            const cbzItem = checkbox.closest('.cbz-item');
            if (checkbox.checked) {
                cbzItem.classList.add('selected');
            } else {
                cbzItem.classList.remove('selected');
            }
        }
        
        function toggleNewFolderInput() {
            const input = document.getElementById('newFolderInput');
            input.style.display = input.style.display === 'none' ? 'block' : 'none';
            if (input.style.display === 'block') {
                document.getElementById('newFolderName').focus();
                document.getElementById('selectedFolder').value = '';
                document.querySelectorAll('.folder-option').forEach(el => el.classList.remove('selected'));
            }
        }
        
        function submitMove() {
            const folder = document.getElementById('selectedFolder').value;
            const newFolder = document.getElementById('newFolderName').value;
            const targetFolder = newFolder || folder;
            
            if (!targetFolder) {
                alert('Selecciona una carpeta o crea una nueva');
                return;
            }
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/move_items';
            
            selectedItems.forEach(itemPath => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'items[]';
                input.value = itemPath;
                form.appendChild(input);
            });
            
            const targetInput = document.createElement('input');
            targetInput.type = 'hidden';
            targetInput.name = 'target_folder';
            targetInput.value = targetFolder;
            form.appendChild(targetInput);
            
            document.body.appendChild(form);
            form.submit();
        }
        
        function submitCompress() {
            const archiveName = document.getElementById('archiveName').value;
            if (!archiveName) {
                alert('Ingresa un nombre para el archivo');
                return;
            }
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/compress_multiple';
            
            selectedItems.forEach(itemPath => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'selected[]';
                input.value = itemPath;
                form.appendChild(input);
            });
            
            const nameInput = document.createElement('input');
            nameInput.type = 'hidden';
            nameInput.name = 'archive_name';
            nameInput.value = archiveName;
            form.appendChild(nameInput);
            
            document.body.appendChild(form);
            form.submit();
        }
        
        function submitMergeCbz() {
            const cbzName = document.getElementById('mergedCbzName').value;
            if (!cbzName || !cbzName.endsWith('.cbz')) {
                alert('Ingresa un nombre válido para el CBZ (debe terminar en .cbz)');
                return;
            }
            
            const selectedCbzItems = Array.from(document.querySelectorAll('#cbzList .cbz-item.selected'));
            if (selectedCbzItems.length < 2) {
                alert('Selecciona al menos 2 CBZs para combinar');
                return;
            }
            
            const cbzPaths = selectedCbzItems.map(item => item.dataset.path);
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/merge_cbz';
            
            cbzPaths.forEach(cbzPath => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cbz_files[]';
                input.value = cbzPath;
                form.appendChild(input);
            });
            
            const nameInput = document.createElement('input');
            nameInput.type = 'hidden';
            nameInput.name = 'output_name';
            nameInput.value = cbzName;
            form.appendChild(nameInput);
            
            document.body.appendChild(form);
            form.submit();
        }
        
        function createCbzFromFolder(folderPath, folderName) {
            if (!confirm(`¿Crear CBZ "${folderName}.cbz" en el directorio superior?`)) {
                return;
            }
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/create_cbz_from_folder';
            
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'folder_path';
            input.value = folderPath;
            form.appendChild(input);
            
            document.body.appendChild(form);
            form.submit();
        }
        
        function deleteSelected() {
            if (selectedItems.size === 0) return;
            
            if (!confirm(`¿Eliminar ${selectedItems.size} elemento(s) seleccionado(s)?`)) {
                return;
            }
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/delete_multiple';
            
            selectedItems.forEach(itemPath => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'items[]';
                input.value = itemPath;
                form.appendChild(input);
            });
            
            document.body.appendChild(form);
            form.submit();
        }
        
        function deleteEmptyFolders() {
            if (!confirm('¿Eliminar todas las carpetas vacías?')) {
                return;
            }
            
            fetch('/delete_empty_folders', { method: 'POST' })
                .then(response => response.text())
                .then(result => {
                    alert(result);
                    location.reload();
                });
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
        
        function checkFolderContent(folderPath) {
            return fetch(`/api/check_folder?path=${encodeURIComponent(folderPath)}`)
                .then(response => response.json())
                .then(data => data.has_content);
        }
        
        function deleteFolder(folderPath, folderName) {
            checkFolderContent(folderPath).then(hasContent => {
                if (hasContent) {
                    if (!confirm(`La carpeta "${folderName}" no está vacía. Si continúa, perderá el contenido. ¿Continuar?`)) {
                        return;
                    }
                }
                
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '/delete_folder';
                
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'path';
                input.value = folderPath;
                form.appendChild(input);
                
                document.body.appendChild(form);
                form.submit();
            });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            updateBulkActions();
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/manga">📖 Manga</a>
            <a href="/utils">🛠️ Utilidades</a>
            <a href="/downloads">📥 Descargas</a>
            {% if user_level >= 3 %}
            <a href="/webusers">👥 Usuarios Web</a>
            {% endif %}
        </div>
        
        <h1>📁 Explorador de Archivos</h1>
        
        <div class="total-files">
            <strong>Total de archivos: {{ total_files }}</strong>
            <span id="selectedCount"></span>
        </div>
        
        <form id="rename-form" action="/rename" method="POST" style="display: none;">
            <input type="hidden" id="old_path" name="old_path">
            <input type="hidden" id="new_name" name="new_name">
        </form>
        
        {% for folder_name, folder_data in folders.items() %}
        <div class="folder">
            <div class="folder-header" onclick="toggleFolder('{{ folder_name }}')">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span>📁 {{ folder_name }} ({{ folder_data["items"]|length }} archivos)</span>
                    {% if user_level >= 4 %}
                    <div class="checkbox-item">
                        <input type="checkbox" 
                               data-path="{{ folder_data['full_path'] }}"
                               onchange="selectItem('{{ folder_data['full_path'] }}', this)">
                    </div>
                    {% endif %}
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    {% if folder_data["has_images"] %}
                    <a href="/gallery?path={{ folder_name }}" class="action-btn btn-gallery" title="Abrir galería">🖼️</a>
                    <a href="/gallery_slideshow?path={{ folder_name }}" class="action-btn btn-gallery" title="Vista deslizante">🎬</a>
                    <button class="action-btn btn-create-cbz" 
                            onclick="createCbzFromFolder('{{ folder_data['full_path'] }}', '{{ folder_name }}'); event.stopPropagation();" 
                            title="Crear CBZ">📚</button>
                    {% endif %}
                    {% if user_level >= 4 %}
                    <button class="action-btn btn-move" 
                            onclick="showMoveDialog(); event.stopPropagation();" 
                            title="Mover">➡️</button>
                    <button class="action-btn btn-compress" 
                            onclick="showCompressDialog(); event.stopPropagation();" 
                            title="Comprimir">📦</button>
                    <button class="action-btn btn-delete" 
                            onclick="deleteFolder('{{ folder_data['full_path'] }}', '{{ folder_name }}'); event.stopPropagation();" 
                            title="Borrar">🗑️</button>
                    {% endif %}
                    <span id="icon-{{ folder_name }}">▶</span>
                </div>
            </div>
            <div class="folder-content" id="content-{{ folder_name }}">
                {% for file in folder_data["items"] %}
                <div class="file-item">
                    <div class="file-info">
                        {% if user_level >= 4 %}
                        <div class="checkbox-item">
                            <input type="checkbox" 
                                   data-path="{{ file.full_path }}"
                                   onchange="selectItem('{{ file.full_path }}', this)">
                        </div>
                        {% endif %}
                        <span class="file-index">{{ file.index }}</span>
                        <span class="file-name">
                            <a href="/{{ file.rel_path }}">{{ file.name }}</a>
                        </span>
                        <span class="file-type">{{ file.ext.upper() }}</span>
                        <span class="file-size">({{ file.size_mb }} MB)</span>
                    </div>
                    <div class="file-actions">
                        <a href="/download?path={{ file.rel_path }}" class="action-btn btn-download" title="Descargar">📥</a>
                        <a href="/send_telegram/{{ file.index }}" class="action-btn btn-telegram" title="Enviar a Telegram">📤</a>
                        {% if user_level >= 4 %}
                        <button class="action-btn btn-rename" 
                                onclick="showRenameInput('{{ file.full_path }}', '{{ file.name }}')" 
                                title="Renombrar">✏️</button>
                        <button class="action-btn btn-move" 
                                onclick="selectItem('{{ file.full_path }}', this.parentElement.parentElement.querySelector('input[type=\"checkbox\"]')); showMoveDialog();" 
                                title="Mover">➡️</button>
                        <button class="action-btn btn-compress" 
                                onclick="selectItem('{{ file.full_path }}', this.parentElement.parentElement.querySelector('input[type=\"checkbox\"]')); showCompressDialog();" 
                                title="Comprimir">📦</button>
                        <form action="/delete" method="POST" style="display: inline;">
                            <input type="hidden" name="path" value="{{ file.full_path }}">
                            <button type="submit" class="action-btn btn-delete" 
                                    onclick="return confirm('¿Eliminar {{ file.name }}?')" 
                                    title="Borrar">🗑️</button>
                        </form>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        {% if user_level >= 4 %}
        <div class="bulk-actions">
            <button class="bulk-btn btn-select-all" onclick="selectAllItems()">
                ☑️ Seleccionar Todos
            </button>
            <button class="bulk-btn btn-delete-empty" onclick="deleteEmptyFolders()">
                🗑️ Borrar Carpetas Vacías
            </button>
            <button class="bulk-btn btn-compress-selected" onclick="showCompressDialog()" disabled>
                📦 Comprimir Seleccionados
            </button>
            <button class="bulk-btn btn-merge-cbz" onclick="showMergeCbzDialog()">
                🔗 Combinar CBZ (seleccionados)
            </button>
            <button class="bulk-btn btn-move-selected" onclick="showMoveDialog()" disabled>
                ➡️ Mover Seleccionados
            </button>
            <button class="bulk-btn btn-delete-selected" onclick="deleteSelected()" disabled>
                🗑️ Borrar Seleccionados
            </button>
        </div>
        {% endif %}
    </div>
    
    <div class="modal" id="moveModal">
        <div class="modal-content">
            <h3 class="modal-title">📂 Mover elementos</h3>
            <p>Selecciona la carpeta destino:</p>
            
            <div class="folder-selector" id="folderList">
            </div>
            
            <button onclick="toggleNewFolderInput()" style="margin-bottom: 15px;">
                📁 Nueva Carpeta
            </button>
            
            <div id="newFolderInput" style="display: none; margin-bottom: 15px;">
                <input type="text" id="newFolderName" placeholder="Nombre de la nueva carpeta">
            </div>
            
            <input type="hidden" id="selectedFolder">
            
            <div class="modal-actions">
                <button class="modal-btn btn-cancel" onclick="closeModal('moveModal')">
                    Cancelar
                </button>
                <button class="modal-btn btn-confirm" onclick="submitMove()">
                    Aceptar
                </button>
            </div>
        </div>
    </div>
    
    <div class="modal" id="compressModal">
        <div class="modal-content">
            <h3 class="modal-title">📦 Comprimir elementos</h3>
            <p>Nombre del archivo comprimido:</p>
            <input type="text" id="archiveName" placeholder="nombre_archivo" required>
            
            <div class="modal-actions">
                <button class="modal-btn btn-cancel" onclick="closeModal('compressModal')">
                    Cancelar
                </button>
                <button class="modal-btn btn-confirm" onclick="submitCompress()">
                    Confirmar
                </button>
            </div>
        </div>
    </div>
    
    <div class="modal" id="mergeCbzModal">
        <div class="modal-content">
            <h3 class="modal-title">🔗 Combinar CBZs</h3>
            <p>Selecciona y ordena los CBZs seleccionados:</p>
            
            <div class="cbz-selector" id="cbzList">
            </div>
            
            <p>Nombre del CBZ combinado:</p>
            <input type="text" id="mergedCbzName" placeholder="manga_combinado.cbz" required>
            
            <div class="modal-actions">
                <button class="modal-btn btn-cancel" onclick="closeModal('mergeCbzModal')">
                    Cancelar
                </button>
                <button class="modal-btn btn-confirm" onclick="submitMergeCbz()">
                    Combinar
                </button>
            </div>
        </div>
    </div>
</body>
</html>
"""
