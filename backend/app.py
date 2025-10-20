#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏配置管理系统 - 后端API
"""

import os
import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, session, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Flask应用初始化
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.secret_key = 'your-secret-key-here'
CORS(app)

# 配置路径
BASE_DIR = Path(__file__).parent.parent
DATABASE_PATH = BASE_DIR / 'config_system.db'
UPLOAD_FOLDER = BASE_DIR / 'uploads'
TEMPLATE_FOLDER = BASE_DIR / 'templates'
DOWNLOAD_FOLDER = BASE_DIR / 'downloads'
GENERATED_FOLDER = BASE_DIR / 'generated'

# 确保目录存在
for folder in [UPLOAD_FOLDER, TEMPLATE_FOLDER, DOWNLOAD_FOLDER, GENERATED_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# 根路由 - 服务前端页面
@app.route('/')
def index():
    """服务前端页面"""
    return app.send_static_file('index.html')

# 数据库初始化
def init_database():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 游戏表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 区服表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            server_id TEXT NOT NULL,
            description TEXT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 配置文件模板表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            game_id INTEGER,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            template_content TEXT,
            config_items TEXT, -- JSON格式存储配置项
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (game_id) REFERENCES games (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 配置文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            template_content TEXT,
            generated_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    ''')
    
    # 创建默认管理员用户
    admin_password = hashlib.sha256('admin'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password_hash, email, role)
        VALUES ('admin', ?, 'admin@example.com', 'admin')
    ''', (admin_password,))
    
    conn.commit()
    conn.close()

# 用户认证装饰器
def login_required(f):
    """登录验证装饰器"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登录'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 路由定义

@app.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute('''
        SELECT id, username, role FROM users 
        WHERE username = ? AND password_hash = ?
    ''', (username, password_hash))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['role'] = user[2]
        return jsonify({
            'message': '登录成功',
            'user': {
                'id': user[0],
                'username': user[1],
                'role': user[2]
            }
        })
    else:
        return jsonify({'error': '用户名或密码错误'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'message': '登出成功'})

# 项目管理API
@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects():
    """获取项目列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, created_at, updated_at
        FROM projects WHERE user_id = ?
        ORDER BY updated_at DESC
    ''', (session['user_id'],))
    
    projects = []
    for row in cursor.fetchall():
        projects.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'created_at': row[3],
            'updated_at': row[4]
        })
    
    conn.close()
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
@login_required
def create_project():
    """创建新项目"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    
    if not name:
        return jsonify({'error': '项目名称不能为空'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO projects (name, description, user_id)
            VALUES (?, ?, ?)
        ''', (name, description, session['user_id']))
        
        project_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'id': project_id,
            'message': '项目创建成功'
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'创建项目失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    """更新项目信息"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 检查项目是否存在且属于当前用户
    cursor.execute('''
        SELECT user_id FROM projects WHERE id = ?
    ''', (project_id,))
    
    project = cursor.fetchone()
    
    if not project or project[0] != session['user_id']:
        conn.close()
        return jsonify({'error': '项目不存在或无权限'}), 404
    
    # 更新项目
    update_fields = []
    update_values = []
    
    if 'name' in data:
        update_fields.append('name = ?')
        update_values.append(data['name'])
    
    if 'description' in data:
        update_fields.append('description = ?')
        update_values.append(data['description'])
    
    update_fields.append('updated_at = CURRENT_TIMESTAMP')
    update_values.append(project_id)
    
    cursor.execute(f'''
        UPDATE projects SET {', '.join(update_fields)}
        WHERE id = ?
    ''', update_values)
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '项目更新成功'})

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """删除项目"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM projects 
        WHERE id = ? AND user_id = ?
    ''', (project_id, session['user_id']))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '项目不存在或无权限'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '项目删除成功'})

# 获取单个项目
@app.route('/api/projects/<int:project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """获取单个项目信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, created_at, updated_at
        FROM projects WHERE id = ? AND user_id = ?
    ''', (project_id, session['user_id']))
    
    project = cursor.fetchone()
    conn.close()
    
    if not project:
        return jsonify({'error': '项目不存在或无权限'}), 404
    
    return jsonify({
        'id': project[0],
        'name': project[1],
        'description': project[2],
        'created_at': project[3],
        'updated_at': project[4]
    })

# 游戏管理API
@app.route('/api/projects/<int:project_id>/games', methods=['GET'])
@login_required
def get_games(project_id):
    """获取项目下的游戏列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, created_at, updated_at
        FROM games 
        WHERE project_id = ? AND user_id = ?
        ORDER BY created_at DESC
    ''', (project_id, session['user_id']))
    
    games = []
    for row in cursor.fetchall():
        games.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'created_at': row[3],
            'updated_at': row[4]
        })
    
    conn.close()
    return jsonify(games)

@app.route('/api/projects/<int:project_id>/games', methods=['POST'])
@login_required
def create_game(project_id):
    """创建游戏"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO games (project_id, name, description, user_id)
        VALUES (?, ?, ?, ?)
    ''', (project_id, data['name'], data.get('description', ''), session['user_id']))
    
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': game_id, 'message': '游戏创建成功'})

# 获取单个游戏
@app.route('/api/games/<int:game_id>', methods=['GET'])
@login_required
def get_game(game_id):
    """获取单个游戏信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, project_id, name, description, created_at, updated_at
        FROM games WHERE id = ? AND user_id = ?
    ''', (game_id, session['user_id']))
    
    game = cursor.fetchone()
    conn.close()
    
    if not game:
        return jsonify({'error': '游戏不存在或无权限'}), 404
    
    return jsonify({
        'id': game[0],
        'project_id': game[1],
        'name': game[2],
        'description': game[3],
        'created_at': game[4],
        'updated_at': game[5]
    })

# 区服管理API
@app.route('/api/games/<int:game_id>/servers', methods=['GET'])
@login_required
def get_servers(game_id):
    """获取游戏下的区服列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, server_id, description, created_at, updated_at
        FROM servers 
        WHERE game_id = ? AND user_id = ?
        ORDER BY created_at DESC
    ''', (game_id, session['user_id']))
    
    servers = []
    for row in cursor.fetchall():
        servers.append({
            'id': row[0],
            'name': row[1],
            'server_id': row[2],
            'description': row[3],
            'created_at': row[4],
            'updated_at': row[5]
        })
    
    conn.close()
    return jsonify(servers)

@app.route('/api/games/<int:game_id>/servers', methods=['POST'])
@login_required
def create_server(game_id):
    """创建区服"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO servers (game_id, name, server_id, description, user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (game_id, data['name'], data['server_id'], data.get('description', ''), session['user_id']))
    
    server_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': server_id, 'message': '区服创建成功'})

# 模板管理API
@app.route('/api/projects/<int:project_id>/games/<int:game_id>/templates', methods=['GET'])
@login_required
def get_config_templates(project_id, game_id):
    """获取游戏下的配置文件模板"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, file_path, config_items, created_at, updated_at
        FROM config_templates 
        WHERE project_id = ? AND game_id = ? AND user_id = ?
        ORDER BY created_at DESC
    ''', (project_id, game_id, session['user_id']))
    
    templates = []
    for row in cursor.fetchall():
        templates.append({
            'id': row[0],
            'name': row[1],
            'file_path': row[2],
            'config_items': json.loads(row[3]) if row[3] else [],
            'created_at': row[4],
            'updated_at': row[5]
        })
    
    conn.close()
    return jsonify(templates)

@app.route('/api/projects/<int:project_id>/games/<int:game_id>/templates', methods=['POST'])
@login_required
def create_config_template(project_id, game_id):
    """创建配置文件模板"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取项目和游戏信息
    cursor.execute('SELECT name FROM projects WHERE id = ? AND user_id = ?', (project_id, session['user_id']))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在或无权限'}), 404
    
    cursor.execute('SELECT name FROM games WHERE id = ? AND user_id = ?', (game_id, session['user_id']))
    game = cursor.fetchone()
    if not game:
        conn.close()
        return jsonify({'error': '游戏不存在或无权限'}), 404
    
    # 创建模板目录结构（绝对路径，且保留文件相对目录层级）
    project_name = project[0].replace(' ', '_').replace('/', '_')
    game_name = game[0].replace(' ', '_').replace('/', '_')
    file_path = data['file_path']
    file_rel = Path(file_path)
    template_dir = TEMPLATE_FOLDER / project_name / game_name / file_rel.parent
    
    # 确保目录存在
    os.makedirs(template_dir, exist_ok=True)
    
    # 生成模板文件路径
    template_file_path = template_dir / file_rel.name
    
    # 保存模板内容到文件
    try:
        with open(template_file_path, 'w', encoding='utf-8') as f:
            f.write(data.get('template_content', ''))
    except Exception as e:
        conn.close()
        return jsonify({'error': f'创建模板文件失败: {str(e)}'}), 500
    
    # 保存到数据库
    cursor.execute('''
        INSERT INTO config_templates (project_id, game_id, name, file_path, template_content, config_items, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, game_id, data['name'], file_path, 
          data.get('template_content', ''), json.dumps(data.get('config_items', [])), session['user_id']))
    
    template_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': template_id, 
        'message': '配置文件模板创建成功',
        'file_created': str(template_file_path)
    })

# 获取所有游戏（用于前端简化调用）
@app.route('/api/games', methods=['GET'])
@login_required
def get_all_games():
    """获取所有游戏列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT g.id, g.project_id, g.name, g.description, g.created_at, g.updated_at,
               p.name as project_name
        FROM games g
        LEFT JOIN projects p ON g.project_id = p.id
        WHERE g.user_id = ?
        ORDER BY g.created_at DESC
    ''', (session['user_id'],))
    
    games = []
    for row in cursor.fetchall():
        games.append({
            'id': row[0],
            'project_id': row[1],
            'name': row[2],
            'description': row[3],
            'created_at': row[4],
            'updated_at': row[5],
            'project_name': row[6]
        })
    
    conn.close()
    return jsonify(games)

# 获取所有区服（用于前端简化调用）
@app.route('/api/servers', methods=['GET'])
@login_required
def get_all_servers():
    """获取所有区服列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.id, s.game_id, s.name, s.server_id, s.description, s.created_at, s.updated_at,
               g.name as game_name, p.name as project_name
        FROM servers s
        LEFT JOIN games g ON s.game_id = g.id
        LEFT JOIN projects p ON g.project_id = p.id
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC
    ''', (session['user_id'],))
    
    servers = []
    for row in cursor.fetchall():
        servers.append({
            'id': row[0],
            'game_id': row[1],
            'name': row[2],
            'server_id': row[3],
            'description': row[4],
            'created_at': row[5],
            'updated_at': row[6],
            'game_name': row[7],
            'project_name': row[8]
        })
    
    conn.close()
    return jsonify(servers)

# 获取所有模板（用于前端简化调用）
@app.route('/api/templates', methods=['GET'])
@login_required
def get_all_templates():
    """获取所有配置文件模板列表"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.id, t.project_id, t.game_id, t.name, t.file_path, t.config_items, t.created_at, t.updated_at,
               g.name as game_name, p.name as project_name
        FROM config_templates t
        LEFT JOIN games g ON t.game_id = g.id
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC
    ''', (session['user_id'],))
    
    templates = []
    for row in cursor.fetchall():
        templates.append({
            'id': row[0],
            'project_id': row[1],
            'game_id': row[2],
            'name': row[3],
            'file_path': row[4],
            'config_items': json.loads(row[5]) if row[5] else [],
            'created_at': row[6],
            'updated_at': row[7],
            'game_name': row[8],
            'project_name': row[9]
        })
    
    conn.close()
    return jsonify(templates)

# 编辑游戏
@app.route('/api/games/<int:game_id>', methods=['PUT'])
@login_required
def update_game(game_id):
    """更新游戏信息"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE games 
        SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (data['name'], data.get('description', ''), game_id, session['user_id']))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '游戏不存在或无权限'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '游戏更新成功'})

# 删除游戏
@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@login_required
def delete_game(game_id):
    """删除游戏"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM games 
        WHERE id = ? AND user_id = ?
    ''', (game_id, session['user_id']))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '游戏不存在或无权限'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '游戏删除成功'})

# 获取单个服务器
@app.route('/api/servers/<int:server_id>', methods=['GET'])
@login_required
def get_server(server_id):
    """获取单个服务器信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, game_id, name, server_id, description, created_at, updated_at
        FROM servers WHERE id = ? AND user_id = ?
    ''', (server_id, session['user_id']))
    
    server = cursor.fetchone()
    conn.close()
    
    if not server:
        return jsonify({'error': '服务器不存在或无权限'}), 404
    
    return jsonify({
        'id': server[0],
        'game_id': server[1],
        'name': server[2],
        'server_id': server[3],
        'description': server[4],
        'created_at': server[5],
        'updated_at': server[6]
    })

# 编辑区服
@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    """更新区服信息"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE servers 
        SET name = ?, server_id = ?, description = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (data['name'], data['server_id'], data.get('description', ''), server_id, session['user_id']))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '区服不存在或无权限'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '区服更新成功'})

# 删除区服
@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    """删除区服"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM servers 
        WHERE id = ? AND user_id = ?
    ''', (server_id, session['user_id']))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': '区服不存在或无权限'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '区服删除成功'})

# 获取单个模板
@app.route('/api/templates/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """获取单个模板信息"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, project_id, game_id, name, file_path, template_content, config_items, created_at, updated_at
        FROM config_templates WHERE id = ? AND user_id = ?
    ''', (template_id, session['user_id']))
    
    template = cursor.fetchone()
    conn.close()
    
    if not template:
        return jsonify({'error': '模板不存在或无权限'}), 404
    
    return jsonify({
        'id': template[0],
        'project_id': template[1],
        'game_id': template[2],
        'name': template[3],
        'file_path': template[4],
        'template_content': template[5],
        'config_items': json.loads(template[6]) if template[6] else [],
        'created_at': template[7],
        'updated_at': template[8]
    })

# 编辑模板
@app.route('/api/templates/<int:template_id>', methods=['PUT'])
@login_required
def update_template(template_id):
    """更新配置文件模板"""
    data = request.get_json()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取模板信息
    cursor.execute('''
        SELECT project_id, game_id, file_path FROM config_templates 
        WHERE id = ? AND user_id = ?
    ''', (template_id, session['user_id']))
    
    template_info = cursor.fetchone()
    if not template_info:
        conn.close()
        return jsonify({'error': '模板不存在或无权限'}), 404
    
    project_id, game_id, old_file_path = template_info
    
    # 获取项目和游戏信息
    cursor.execute('SELECT name FROM projects WHERE id = ? AND user_id = ?', (project_id, session['user_id']))
    project = cursor.fetchone()
    cursor.execute('SELECT name FROM games WHERE id = ? AND user_id = ?', (game_id, session['user_id']))
    game = cursor.fetchone()
    
    if not project or not game:
        conn.close()
        return jsonify({'error': '项目或游戏不存在'}), 404
    
    # 创建模板目录结构（绝对路径，且保留文件相对目录层级）
    project_name = project[0].replace(' ', '_').replace('/', '_')
    game_name = game[0].replace(' ', '_').replace('/', '_')
    new_file_path = data['file_path']
    new_rel = Path(new_file_path)
    template_dir = TEMPLATE_FOLDER / project_name / game_name / new_rel.parent
    
    # 确保目录存在
    os.makedirs(template_dir, exist_ok=True)
    
    # 生成新的模板文件路径
    template_file_path = template_dir / new_rel.name
    
    # 如果文件路径改变，删除旧文件
    if old_file_path != new_file_path:
        old_rel = Path(old_file_path)
        old_template_file_path = TEMPLATE_FOLDER / project_name / game_name / old_rel
        if os.path.exists(old_template_file_path):
            try:
                os.remove(old_template_file_path)
            except Exception as e:
                print(f"删除旧模板文件失败: {e}")
    
    # 保存模板内容到文件
    try:
        with open(template_file_path, 'w', encoding='utf-8') as f:
            f.write(data.get('template_content', ''))
    except Exception as e:
        conn.close()
        return jsonify({'error': f'更新模板文件失败: {str(e)}'}), 500
    
    # 解析模板内容中的配置项
    config_items = get_template_config_items(data.get('template_content', ''))
    
    # 更新数据库
    cursor.execute('''
        UPDATE config_templates 
        SET name = ?, file_path = ?, template_content = ?, config_items = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (data['name'], new_file_path, data.get('template_content', ''), 
          json.dumps(config_items), template_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '模板更新成功',
        'file_updated': str(template_file_path)
    })

# 删除模板
@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """删除配置文件模板"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取模板信息
    cursor.execute('''
        SELECT project_id, game_id, file_path FROM config_templates 
        WHERE id = ? AND user_id = ?
    ''', (template_id, session['user_id']))
    
    template_info = cursor.fetchone()
    if not template_info:
        conn.close()
        return jsonify({'error': '模板不存在或无权限'}), 404
    
    project_id, game_id, file_path = template_info
    
    # 获取项目和游戏信息
    cursor.execute('SELECT name FROM projects WHERE id = ? AND user_id = ?', (project_id, session['user_id']))
    project = cursor.fetchone()
    cursor.execute('SELECT name FROM games WHERE id = ? AND user_id = ?', (game_id, session['user_id']))
    game = cursor.fetchone()
    
    if project and game:
        # 计算模板绝对路径
        project_name = project[0].replace(' ', '_').replace('/', '_')
        game_name = game[0].replace(' ', '_').replace('/', '_')
        template_file_path = TEMPLATE_FOLDER / project_name / game_name / Path(file_path)
        if os.path.exists(template_file_path):
            try:
                os.remove(template_file_path)
            except Exception as e:
                print(f"删除模板文件失败: {e}")
    
    # 从数据库删除
    cursor.execute('''
        DELETE FROM config_templates 
        WHERE id = ? AND user_id = ?
    ''', (template_id, session['user_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': '模板删除成功'})

# 生成配置文件
@app.route('/api/generate-config', methods=['POST'])
@login_required
def generate_config():
    """生成配置文件"""
    data = request.get_json()
    server_id = data.get('server_id')
    template_id = data.get('template_id')
    config_data = data.get('config_data', {})
    
    print(f"DEBUG: 收到生成请求 - server_id: {server_id}, template_id: {template_id}")
    print(f"DEBUG: 配置数据: {config_data}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取模板信息
    cursor.execute('''
        SELECT template_content, file_path FROM config_templates 
        WHERE id = ? AND user_id = ?
    ''', (template_id, session['user_id']))
    
    template = cursor.fetchone()
    if not template:
        print(f"DEBUG: 模板不存在 - template_id: {template_id}, user_id: {session['user_id']}")
        conn.close()
        return jsonify({'error': '模板不存在或无权限'}), 404
    
    template_content = template[0]
    file_path = template[1]
    print(f"DEBUG: 模板内容长度: {len(template_content)}, 文件路径: {file_path}")
    
    # 替换模板中的变量
    generated_content = template_content
    for key, value in config_data.items():
        placeholder = f'{{{{ {key} }}}}'  # 使用两个大括号格式
        generated_content = generated_content.replace(placeholder, str(value))
    print(f"DEBUG: 变量替换完成，生成内容长度: {len(generated_content)}")
    print(f"DEBUG: 替换后的内容预览: {generated_content[:200]}...")
    
    # 计算生成文件的实际落盘路径：generated/{项目}/{游戏}/{区服名或ID}/{file_path}
    cursor.execute('''
        SELECT s.name as server_name, s.server_id, g.name as game_name, p.name as project_name
        FROM servers s
        JOIN games g ON s.game_id = g.id
        JOIN projects p ON g.project_id = p.id
        WHERE s.id = ? AND s.user_id = ?
    ''', (server_id, session['user_id']))
    sgp = cursor.fetchone()
    if not sgp:
        print(f"DEBUG: 区服不存在 - server_id: {server_id}, user_id: {session['user_id']}")
        conn.close()
        return jsonify({'error': '区服不存在或无权限'}), 404
    server_name, server_sid, game_name, project_name = sgp
    print(f"DEBUG: 区服信息 - 项目: {project_name}, 游戏: {game_name}, 区服: {server_name}/{server_sid}")
    
    project_safe = project_name.replace(' ', '_').replace('/', '_')
    game_safe = game_name.replace(' ', '_').replace('/', '_')
    server_dir_name = server_name or server_sid
    rel_path = Path(file_path)
    output_dir = GENERATED_FOLDER / project_safe / game_safe / server_dir_name / rel_path.parent
    
    print(f"DEBUG: 创建目录: {output_dir}")
    print(f"DEBUG: GENERATED_FOLDER: {GENERATED_FOLDER}")
    print(f"DEBUG: GENERATED_FOLDER 存在: {GENERATED_FOLDER.exists()}")
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"DEBUG: 目录创建成功: {output_dir}")
        print(f"DEBUG: 目录存在: {output_dir.exists()}")
    except Exception as e:
        print(f"DEBUG: 目录创建失败: {str(e)}")
        conn.close()
        return jsonify({'error': f'创建目录失败: {str(e)}'}), 500
    
    output_file_path = output_dir / rel_path.name
    print(f"DEBUG: 写入文件: {output_file_path}")
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(generated_content)
        print(f"DEBUG: 文件写入成功: {output_file_path}")
        print(f"DEBUG: 文件存在: {output_file_path.exists()}")
        print(f"DEBUG: 文件大小: {output_file_path.stat().st_size if output_file_path.exists() else 'N/A'}")
    except Exception as e:
        print(f"DEBUG: 文件写入失败: {str(e)}")
        conn.close()
        return jsonify({'error': f'写入生成文件失败: {str(e)}'}), 500

    # 保存生成记录到数据库（仍保存模板相对路径便于查询）
    cursor.execute('''
        INSERT INTO config_files (server_id, file_name, file_path, template_content, generated_content)
        VALUES (?, ?, ?, ?, ?)
    ''', (server_id, rel_path.name, file_path, template_content, generated_content))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '配置文件生成成功',
        'generated_content': generated_content,
        'file_path': file_path,
        'output_file': str(output_file_path)
    })

# 获取生成目录路径
@app.route('/api/get-generated-path', methods=['POST'])
@login_required
def get_generated_path():
    """获取生成目录的绝对路径"""
    data = request.get_json()
    project_name = data.get('project_name')
    game_name = data.get('game_name')
    server_name = data.get('server_name')
    
    if not all([project_name, game_name, server_name]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 构建生成目录路径
    project_safe = project_name.replace(' ', '_').replace('/', '_')
    game_safe = game_name.replace(' ', '_').replace('/', '_')
    server_dir_name = server_name.replace(' ', '_').replace('/', '_')
    
    generated_path = GENERATED_FOLDER / project_safe / game_safe / server_dir_name
    
    return jsonify({
        'path': str(generated_path),
        'exists': generated_path.exists()
    })

# 打开文件夹（Windows）
@app.route('/api/open-folder', methods=['POST'])
@login_required
def open_folder():
    """打开指定文件夹"""
    data = request.get_json()
    folder_path = data.get('path')
    
    if not folder_path:
        return jsonify({'error': '缺少文件夹路径'}), 400
    
    try:
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            subprocess.run(['explorer', folder_path], check=True)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', folder_path], check=True)
        elif platform.system() == 'Linux':
            subprocess.run(['xdg-open', folder_path], check=True)
        
        return jsonify({'message': '文件夹已打开'})
    except Exception as e:
        return jsonify({'error': f'打开文件夹失败: {str(e)}'}), 500

# 下载生成文件的ZIP包
@app.route('/api/download-generated-zip', methods=['POST'])
@login_required
def download_generated_zip():
    """下载生成文件的ZIP包"""
    data = request.get_json()
    project_name = data.get('project_name')
    game_name = data.get('game_name')
    server_name = data.get('server_name')
    
    if not all([project_name, game_name, server_name]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        import zipfile
        import tempfile
        
        # 构建生成目录路径
        project_safe = project_name.replace(' ', '_').replace('/', '_')
        game_safe = game_name.replace(' ', '_').replace('/', '_')
        server_dir_name = server_name.replace(' ', '_').replace('/', '_')
        
        generated_path = GENERATED_FOLDER / project_safe / game_safe / server_dir_name
        
        print(f"DEBUG: 查找生成目录: {generated_path}")
        if not generated_path.exists():
            print(f"DEBUG: 生成目录不存在，尝试创建: {generated_path}")
            try:
                os.makedirs(generated_path, exist_ok=True)
                print(f"DEBUG: 目录创建成功: {generated_path}")
            except Exception as e:
                print(f"DEBUG: 目录创建失败: {str(e)}")
                return jsonify({'error': f'生成目录不存在且无法创建: {str(e)}'}), 404
        
        # 检查目录中是否有文件
        files_in_dir = list(generated_path.rglob('*'))
        files_only = [f for f in files_in_dir if f.is_file()]
        
        if not files_only:
            return jsonify({'error': '生成目录中没有配置文件，请先生成配置文件'}), 404
        
        print(f"DEBUG: 找到 {len(files_only)} 个文件，开始创建ZIP包")
        
        # 创建临时ZIP文件
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_only:
                # 保持相对路径结构
                arcname = file_path.relative_to(generated_path)
                zipf.write(file_path, arcname)
                print(f"DEBUG: 添加文件到ZIP: {arcname}")
        
        print(f"DEBUG: ZIP包创建成功: {temp_zip.name}")
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f'{project_name}_{game_name}_{server_name}_configs.zip',
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'error': f'创建ZIP包失败: {str(e)}'}), 500

# 修改用户密码
@app.route('/api/user/password', methods=['PUT'])
@login_required
def change_password():
    """修改用户密码"""
    print(f"DEBUG: 收到密码修改请求")
    print(f"DEBUG: session: {session}")
    print(f"DEBUG: user_id in session: {'user_id' in session}")
    
    data = request.get_json()
    print(f"DEBUG: 请求数据: {data}")
    
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    if not current_password or not new_password:
        print(f"DEBUG: 缺少必要参数")
        return jsonify({'error': '缺少必要参数'}), 400
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 验证当前密码
    cursor.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    print(f"DEBUG: 查询到的用户: {user}")
    
    if not user:
        print(f"DEBUG: 用户不存在")
        conn.close()
        return jsonify({'error': '用户不存在'}), 404
    
    # 验证当前密码（简单比较，实际应用中应该使用哈希）
    if user[0] != current_password:
        print(f"DEBUG: 当前密码错误")
        conn.close()
        return jsonify({'error': '当前密码错误'}), 400
    
    # 更新密码
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, session['user_id']))
    conn.commit()
    conn.close()
    
    print(f"DEBUG: 密码修改成功")
    return jsonify({'message': '密码修改成功'})

# 调试API - 查看数据库状态
@app.route('/api/debug/status', methods=['GET'])
@login_required
def debug_status():
    """调试API - 查看数据库状态"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 获取各种数据统计
    cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (session['user_id'],))
    project_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM games WHERE user_id = ?', (session['user_id'],))
    game_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM servers WHERE user_id = ?', (session['user_id'],))
    server_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM config_templates WHERE user_id = ?', (session['user_id'],))
    template_count = cursor.fetchone()[0]
    
    # 获取最新的模板信息
    cursor.execute('''
        SELECT ct.id, ct.name, ct.file_path, ct.config_items, 
               p.name as project_name, g.name as game_name
        FROM config_templates ct
        LEFT JOIN projects p ON ct.project_id = p.id
        LEFT JOIN games g ON ct.game_id = g.id
        WHERE ct.user_id = ?
        ORDER BY ct.created_at DESC
        LIMIT 5
    ''', (session['user_id'],))
    recent_templates = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'user_id': session['user_id'],
        'counts': {
            'projects': project_count,
            'games': game_count,
            'servers': server_count,
            'templates': template_count
        },
        'recent_templates': [
            {
                'id': t[0],
                'name': t[1],
                'file_path': t[2],
                'config_items': json.loads(t[3]) if t[3] else [],
                'project_name': t[4],
                'game_name': t[5]
            } for t in recent_templates
        ]
    })

# 辅助函数
def get_template_config_items(template_content):
    """解析模板内容中的配置项"""
    import re
    variables = re.findall(r'\{\{([^}]+)\}\}', template_content)
    
    config_items = []
    seen = set()
    
    for var in variables:
        var = var.strip()
        if var not in seen:
            seen.add(var)
            config_items.append({
                'key': var,
                'label': generate_friendly_label(var),
                'type': 'text',
                'default_value': get_default_value(var)
            })
    
    return config_items

def generate_friendly_label(var_name):
    """根据变量名生成友好的标签"""
    label_map = {
        'server_id': '区服ID',
        'server_name': '区服名称',
        'server_port': '游戏端口',
        'server_host': '服务器地址',
        'game_port': '游戏端口',
        'game_host': '游戏服务器地址',
        'max_players': '最大玩家数',
        'db_host': '数据库地址',
        'db_port': '数据库端口',
        'db_name': '数据库名称',
        'db_user': '数据库用户名',
        'db_password': '数据库密码',
        'redis_host': 'Redis地址',
        'redis_port': 'Redis端口',
        'redis_password': 'Redis密码',
        'app_name': '应用名称',
        'app_version': '应用版本',
        'debug': '调试模式',
        'log_level': '日志级别',
        'http_port': 'HTTP端口',
        'timezone': '时区',
        'language': '语言',
        'api_key': 'API密钥',
        'secret_key': '密钥'
    }
    
    return label_map.get(var_name, var_name.replace('_', ' ').title())

def get_default_value(var_name):
    """根据变量名获取默认值"""
    default_map = {
        'server_id': 'server_001',
        'server_name': '测试区服',
        'server_port': '8080',
        'server_host': 'localhost',
        'game_port': '8080',
        'game_host': 'localhost',
        'max_players': '1000',
        'db_host': 'localhost',
        'db_port': '3306',
        'db_name': 'game_db',
        'db_user': 'root',
        'db_password': 'password',
        'redis_host': 'localhost',
        'redis_port': '6379',
        'redis_password': '',
        'app_name': '游戏服务器',
        'app_version': '1.0.0',
        'debug': 'false',
        'log_level': 'info',
        'http_port': '80',
        'timezone': 'Asia/Shanghai',
        'language': 'zh-CN'
    }
    
    return default_map.get(var_name, '')

if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
