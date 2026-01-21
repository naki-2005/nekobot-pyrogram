WEBUSERS_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Gestión de Usuarios Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #667eea; color: white; }
        tr:hover { background: #f9f9f9; }
        .level-6 { background: #ffe6e6; }
        .level-5 { background: #fff0e6; }
        .level-4 { background: #ffffe6; }
        .level-3 { background: #e6ffe6; }
        .level-2 { background: #e6f7ff; }
        .level-1 { background: #f0e6ff; }
        .level-0 { background: #f5f5f5; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-create { background: #28a745; color: white; }
        .btn-delete { background: #dc3545; color: white; }
        .btn-update { background: #ffc107; color: black; }
        .form-group { margin: 10px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 10px; color: #667eea; text-decoration: none; }
        .permission-warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">🏠 Inicio</a>
            <a href="/manga">📖 Manga</a>
            <a href="/utils">🛠️ Utilidades</a>
            <a href="/downloads">📥 Descargas</a>
            <a href="/webusers">👥 Usuarios Web</a>
        </div>
        
        <h1>👥 Gestión de Usuarios Web</h1>
        
        {% if current_user_level >= 4 %}
        <div class="section">
            <h2>➕ Crear Nuevo Usuario</h2>
            <form method="POST">
                <input type="hidden" name="action" value="create">
                <div class="form-group">
                    <label>ID de Usuario (numérico):</label>
                    <input type="text" name="new_id" required pattern="[0-9]+" title="Solo números">
                </div>
                <div class="form-group">
                    <label>Nombre de Usuario:</label>
                    <input type="text" name="new_user" required>
                </div>
                <div class="form-group">
                    <label>Contraseña:</label>
                    <input type="password" name="new_pass" required>
                </div>
                <button type="submit" class="btn btn-create">Crear Usuario</button>
            </form>
        </div>
        {% endif %}
        
        <div class="section">
            <h2>📋 Usuarios Existentes</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Usuario</th>
                        {% if current_user_level >= 3 %}
                        <th>Contraseña</th>
                        {% endif %}
                        <th>Nivel</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {% for uid, user_data in users.items() %}
                    <tr class="level-{{ user_data.level }}">
                        <td>{{ uid }}</td>
                        <td>{{ user_data.user }}</td>
                        {% if current_user_level >= 3 %}
                        <td>{{ user_data.pass if uid == current_user_id else '****' }}</td>
                        {% endif %}
                        <td>
                            {% if user_data.level == 6 %}Owner
                            {% elif user_data.level == 5 %}Admin
                            {% elif user_data.level == 4 %}Mod
                            {% elif user_data.level == 3 %}VIP
                            {% elif user_data.level == 2 %}User
                            {% elif user_data.level == 1 %}Guest
                            {% else %}No Access{% endif %}
                        </td>
                        <td>
                            {% if current_user_level >= 4 and current_user_level > user_data.level %}
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="action" value="update">
                                <input type="hidden" name="user_id_to_update" value="{{ uid }}">
                                <input type="text" name="new_username" placeholder="Nuevo usuario" style="width: 100px;">
                                <input type="password" name="new_password" placeholder="Nueva contraseña" style="width: 100px;">
                                <button type="submit" class="btn btn-update">Actualizar</button>
                            </form>
                            {% if current_user_level >= 5 and current_user_level > user_data.level %}
                            <form method="POST" style="display: inline;">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="user_id_to_delete" value="{{ uid }}">
                                <button type="submit" class="btn btn-delete" onclick="return confirm('¿Borrar usuario {{ uid }}?')">Borrar</button>
                            </form>
                            {% endif %}
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
