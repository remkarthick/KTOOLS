import os

# ─────────────────────────────────────────
# FILE CONTENTS DICTIONARY
# ─────────────────────────────────────────

files = {}

# ─────────────────────────────────────────
# requirements.txt
# ─────────────────────────────────────────
files['requirements.txt'] = """Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
requests==2.31.0
cryptography==41.0.7
Werkzeug==3.0.1
"""

# ─────────────────────────────────────────
# run.py
# ─────────────────────────────────────────
files['run.py'] = """from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
"""

# ─────────────────────────────────────────
# config.py
# ─────────────────────────────────────────
files['config.py'] = """import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sn-flow-explorer-secret-2024')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENCRYPTION_KEY_FILE = os.path.join(BASE_DIR, 'instance', '.enc_key')
"""

# ─────────────────────────────────────────
# models.py
# ─────────────────────────────────────────
files['models.py'] = """from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class AppConfig(db.Model):
    __tablename__ = 'app_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnFlow(db.Model):
    __tablename__ = 'sn_flows'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    flow_type = db.Column(db.String(50))
    active = db.Column(db.String(10))
    definition = db.Column(db.Text)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnStepInstance(db.Model):
    __tablename__ = 'sn_step_instances'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    flow_sys_id = db.Column(db.String(32))
    inputs = db.Column(db.Text)
    outputs = db.Column(db.Text)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnActionInstance(db.Model):
    __tablename__ = 'sn_action_instances'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    action_type = db.Column(db.String(255))
    inputs = db.Column(db.Text)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnActionType(db.Model):
    __tablename__ = 'sn_action_types'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    definition = db.Column(db.Text)
    active = db.Column(db.String(10))
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnScriptInclude(db.Model):
    __tablename__ = 'sn_script_includes'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    script = db.Column(db.Text)
    active = db.Column(db.String(10))
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class SnScript(db.Model):
    __tablename__ = 'sn_scripts'
    id = db.Column(db.Integer, primary_key=True)
    sys_id = db.Column(db.String(32), unique=True)
    name = db.Column(db.String(255))
    script = db.Column(db.Text)
    active = db.Column(db.String(10))
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class QueryHistory(db.Model):
    __tablename__ = 'query_history'
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)
"""

# ─────────────────────────────────────────
# utils.py
# ─────────────────────────────────────────
files['utils.py'] = """import os
import base64
from cryptography.fernet import Fernet
from config import Config

def get_or_create_key():
    key_file = Config.ENCRYPTION_KEY_FILE
    os.makedirs(os.path.dirname(key_file), exist_ok=True)
    if not os.path.exists(key_file):
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
    with open(key_file, 'rb') as f:
        return f.read()

def encrypt_value(value):
    if not value:
        return value
    f = Fernet(get_or_create_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(value):
    if not value:
        return value
    try:
        f = Fernet(get_or_create_key())
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value

def get_config_value(key):
    from models import AppConfig
    record = AppConfig.query.filter_by(key=key).first()
    if record:
        if key == 'password':
            return decrypt_value(record.value)
        return record.value
    return None

def set_config_value(key, value):
    from models import AppConfig, db
    record = AppConfig.query.filter_by(key=key).first()
    if not record:
        record = AppConfig(key=key)
        db.session.add(record)
    if key == 'password':
        record.value = encrypt_value(value)
    else:
        record.value = value
    db.session.commit()
"""

# ─────────────────────────────────────────
# database_manager.py
# ─────────────────────────────────────────
files['database_manager.py'] = """import requests
from models import (db, SnFlow, SnStepInstance, SnActionInstance,
                    SnActionType, SnScriptInclude, SnScript)
from utils import get_config_value
from datetime import datetime

def get_sn_session():
    base_url = get_config_value('base_url')
    username = get_config_value('username')
    password = get_config_value('password')
    if not all([base_url, username, password]):
        raise ValueError('ServiceNow credentials not configured.')
    session = requests.Session()
    session.auth = (username, password)
    session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    return session, base_url.rstrip('/')

def fetch_table(session, base_url, table, fields, limit=1000):
    url = f"{base_url}/api/now/table/{table}"
    params = {
        'sysparm_fields': ','.join(fields),
        'sysparm_limit': limit,
        'sysparm_display_value': 'false'
    }
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get('result', [])

def sync_all(log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)

    try:
        session, base_url = get_sn_session()
        log('✅ Connected to ServiceNow successfully.')

        # Sync Flows
        log('🔄 Syncing sys_hub_flow...')
        flows = fetch_table(session, base_url, 'sys_hub_flow',
                            ['sys_id', 'name', 'type', 'active', 'definition'])
        SnFlow.query.delete()
        for r in flows:
            db.session.add(SnFlow(
                sys_id=r.get('sys_id'),
                name=r.get('name'),
                flow_type=r.get('type'),
                active=str(r.get('active', '')),
                definition=r.get('definition', '')
            ))
        db.session.commit()
        log(f'✅ Synced {len(flows)} flows/subflows.')

        # Sync Step Instances
        log('🔄 Syncing sys_hub_step_instance...')
        try:
            steps = fetch_table(session, base_url, 'sys_hub_step_instance',
                                ['sys_id', 'name', 'flow', 'inputs', 'outputs'])
            SnStepInstance.query.delete()
            for r in steps:
                flow_val = r.get('flow')
                flow_sys_id = flow_val.get('value') if isinstance(flow_val, dict) else flow_val
                db.session.add(SnStepInstance(
                    sys_id=r.get('sys_id'),
                    name=r.get('name'),
                    flow_sys_id=flow_sys_id,
                    inputs=str(r.get('inputs', '')),
                    outputs=str(r.get('outputs', ''))
                ))
            db.session.commit()
            log(f'✅ Synced {len(steps)} step instances.')
        except Exception as e:
            log(f'⚠️ Step instances skipped: {str(e)}')

        # Sync Action Instances
        log('🔄 Syncing sys_hub_action_instance...')
        try:
            actions = fetch_table(session, base_url, 'sys_hub_action_instance',
                                  ['sys_id', 'name', 'action_type', 'inputs'])
            SnActionInstance.query.delete()
            for r in actions:
                at_val = r.get('action_type')
                at = at_val.get('value') if isinstance(at_val, dict) else str(at_val)
                db.session.add(SnActionInstance(
                    sys_id=r.get('sys_id'),
                    name=r.get('name'),
                    action_type=at,
                    inputs=str(r.get('inputs', ''))
                ))
            db.session.commit()
            log(f'✅ Synced {len(actions)} action instances.')
        except Exception as e:
            log(f'⚠️ Action instances skipped: {str(e)}')

        # Sync Action Types
        log('🔄 Syncing sys_hub_action_type_definition...')
        try:
            atypes = fetch_table(session, base_url, 'sys_hub_action_type_definition',
                                 ['sys_id', 'name', 'definition', 'active'])
            SnActionType.query.delete()
            for r in atypes:
                db.session.add(SnActionType(
                    sys_id=r.get('sys_id'),
                    name=r.get('name'),
                    definition=r.get('definition', ''),
                    active=str(r.get('active', ''))
                ))
            db.session.commit()
            log(f'✅ Synced {len(atypes)} action types.')
        except Exception as e:
            log(f'⚠️ Action types skipped: {str(e)}')

        # Sync Script Includes
        log('🔄 Syncing sys_script_include...')
        try:
            includes = fetch_table(session, base_url, 'sys_script_include',
                                   ['sys_id', 'name', 'script', 'active'])
            SnScriptInclude.query.delete()
            for r in includes:
                db.session.add(SnScriptInclude(
                    sys_id=r.get('sys_id'),
                    name=r.get('name'),
                    script=r.get('script', ''),
                    active=str(r.get('active', ''))
                ))
            db.session.commit()
            log(f'✅ Synced {len(includes)} script includes.')
        except Exception as e:
            log(f'⚠️ Script includes skipped: {str(e)}')

        # Sync Scripts
        log('🔄 Syncing sys_script...')
        try:
            scripts = fetch_table(session, base_url, 'sys_script',
                                  ['sys_id', 'name', 'script', 'active'])
            SnScript.query.delete()
            for r in scripts:
                db.session.add(SnScript(
                    sys_id=r.get('sys_id'),
                    name=r.get('name'),
                    script=r.get('script', ''),
                    active=str(r.get('active', ''))
                ))
            db.session.commit()
            log(f'✅ Synced {len(scripts)} scripts.')
        except Exception as e:
            log(f'⚠️ Scripts skipped: {str(e)}')

        log('🎉 Sync completed successfully!')
        return True, 'Sync completed.'

    except Exception as e:
        log(f'❌ Sync failed: {str(e)}')
        return False, str(e)
"""

# ─────────────────────────────────────────
# app.py
# ─────────────────────────────────────────
files['app.py'] = """import os
import csv
import io
import json
import sqlite3
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash, Response)
from config import Config
from models import db, AppConfig, QueryHistory
from utils import set_config_value, get_config_value
from database_manager import sync_all, get_sn_session, fetch_table
import requests
import threading

sync_logs = []
sync_running = False

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # ─────────────────────────────────────────
    # DASHBOARD
    # ─────────────────────────────────────────
    @app.route('/')
    def dashboard():
        from models import SnFlow, SnScriptInclude, SnActionType, SnStepInstance
        stats = {
            'flows': SnFlow.query.count(),
            'script_includes': SnScriptInclude.query.count(),
            'action_types': SnActionType.query.count(),
            'step_instances': SnStepInstance.query.count(),
        }
        base_url = get_config_value('base_url') or ''
        username = get_config_value('username') or ''
        return render_template('dashboard.html', stats=stats,
                               base_url=base_url, username=username)

    # ─────────────────────────────────────────
    # CONFIG
    # ─────────────────────────────────────────
    @app.route('/config', methods=['GET', 'POST'])
    def config_page():
        if request.method == 'POST':
            set_config_value('base_url', request.form.get('base_url', '').rstrip('/'))
            set_config_value('username', request.form.get('username', ''))
            set_config_value('password', request.form.get('password', ''))
            flash('Configuration saved successfully!', 'success')
            return redirect(url_for('config_page'))
        return render_template('config.html',
                               base_url=get_config_value('base_url') or '',
                               username=get_config_value('username') or '')

    @app.route('/api/test-connection', methods=['POST'])
    def test_connection():
        try:
            session, base_url = get_sn_session()
            url = f"{base_url}/api/now/table/sys_user"
            resp = session.get(url, params={'sysparm_limit': 1}, timeout=10)
            if resp.status_code == 200:
                return jsonify({'success': True, 'message': 'Connection successful!'})
            else:
                return jsonify({'success': False, 'message': f'HTTP {resp.status_code}: {resp.text[:200]}'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    # ─────────────────────────────────────────
    # SYNC
    # ─────────────────────────────────────────
    @app.route('/api/sync', methods=['POST'])
    def start_sync():
        global sync_logs, sync_running
        if sync_running:
            return jsonify({'success': False, 'message': 'Sync already running.'})
        sync_logs = []
        sync_running = True

        def run_sync():
            global sync_running
            with app.app_context():
                sync_all(log_callback=lambda msg: sync_logs.append(msg))
            sync_running = False

        t = threading.Thread(target=run_sync)
        t.daemon = True
        t.start()
        return jsonify({'success': True, 'message': 'Sync started.'})

    @app.route('/api/sync-logs')
    def get_sync_logs():
        global sync_logs, sync_running
        return jsonify({'logs': sync_logs, 'running': sync_running})

    # ─────────────────────────────────────────
    # ANALYZER
    # ─────────────────────────────────────────
    @app.route('/analyzer')
    def analyzer():
        return render_template('analyzer.html')

    @app.route('/api/analyze', methods=['POST'])
    def analyze():
        from models import SnFlow, SnActionType, SnStepInstance
        data = request.get_json()
        search_term = data.get('search_term', '').strip()
        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400

        results = {'flows': [], 'action_types': [], 'step_instances': []}

        flows = SnFlow.query.filter(
            SnFlow.definition.ilike(f'%{search_term}%')
        ).all()
        for f in flows:
            results['flows'].append({
                'sys_id': f.sys_id,
                'name': f.name,
                'type': f.flow_type or 'Unknown',
                'active': f.active
            })

        atypes = SnActionType.query.filter(
            SnActionType.definition.ilike(f'%{search_term}%')
        ).all()
        for a in atypes:
            results['action_types'].append({
                'sys_id': a.sys_id,
                'name': a.name,
                'active': a.active
            })

        steps = SnStepInstance.query.filter(
            SnStepInstance.inputs.ilike(f'%{search_term}%') |
            SnStepInstance.outputs.ilike(f'%{search_term}%')
        ).all()
        for s in steps:
            results['step_instances'].append({
                'sys_id': s.sys_id,
                'name': s.name,
                'flow_sys_id': s.flow_sys_id
            })

        return jsonify(results)

    # ─────────────────────────────────────────
    # DATABASE CONSOLE
    # ─────────────────────────────────────────
    @app.route('/database-console')
    def database_console():
        return render_template('database_console.html')

    @app.route('/api/db/tables')
    def get_tables():
        conn = sqlite3.connect(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'tables': tables})

    @app.route('/api/db/table/<table_name>')
    def get_table_data(table_name):
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row['name'] for row in cursor.fetchall()]
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 500")
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify({'columns': columns, 'rows': rows})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/db/query', methods=['POST'])
    def execute_query():
        data = request.get_json()
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        success = True
        error_msg = None
        columns = []
        rows = []
        rowcount = 0

        try:
            cursor.execute(query)
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [dict(row) for row in cursor.fetchall()]
            else:
                conn.commit()
                rowcount = cursor.rowcount
        except Exception as e:
            success = False
            error_msg = str(e)
        finally:
            conn.close()

        # Save to history
        try:
            with app.app_context():
                h = QueryHistory(query=query, success=success)
                db.session.add(h)
                db.session.commit()
        except Exception:
            pass

        return jsonify({
            'success': success,
            'columns': columns,
            'rows': rows,
            'rowcount': rowcount,
            'error': error_msg
        })

    @app.route('/api/db/query-history')
    def query_history():
        history = QueryHistory.query.order_by(QueryHistory.executed_at.desc()).limit(10).all()
        return jsonify({'history': [{'query': h.query, 'executed_at': str(h.executed_at), 'success': h.success} for h in history]})

    @app.route('/api/db/delete-row', methods=['POST'])
    def delete_row():
        data = request.get_json()
        table = data.get('table')
        row_id = data.get('id')
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/db/truncate', methods=['POST'])
    def truncate_table():
        data = request.get_json()
        table = data.get('table')
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            conn.execute(f"DELETE FROM {table}")
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/db/vacuum', methods=['POST'])
    def vacuum_db():
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            conn.execute("VACUUM")
            conn.close()
            return jsonify({'success': True, 'message': 'Database vacuumed successfully.'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/db/export/<table_name>')
    def export_csv(table_name):
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(list(row))

            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={table_name}.csv'}
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/db/delete-database', methods=['POST'])
    def delete_database():
        data = request.get_json()
        confirmation = data.get('confirmation', '')
        if confirmation != 'DELETE':
            return jsonify({'success': False, 'error': 'Confirmation text does not match.'})
        try:
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
            conn.close()
            db.create_all()
            return jsonify({'success': True, 'message': 'Database cleared and recreated.'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    return app
"""

# ─────────────────────────────────────────
# templates/base.html
# ─────────────────────────────────────────
files['templates/base.html'] = """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}ServiceNow Flow Explorer{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.7/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
</head>
<body>

<!-- Sidebar -->
<div class="sidebar" id="sidebar">
    <div class="sidebar-brand">
        <i class="bi bi-diagram-3-fill me-2 text-info"></i>
        <span>SN Flow Explorer</span>
    </div>
    <nav class="sidebar-nav">
        <a href="{{ url_for('dashboard') }}" class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}">
            <i class="bi bi-speedometer2"></i> Dashboard
        </a>
        <a href="{{ url_for('analyzer') }}" class="nav-link {% if request.endpoint == 'analyzer' %}active{% endif %}">
            <i class="bi bi-search"></i> Analyzer
        </a>
        <a href="{{ url_for('database_console') }}" class="nav-link {% if request.endpoint == 'database_console' %}active{% endif %}">
            <i class="bi bi-database"></i> DB Console
        </a>
        <a href="{{ url_for('config_page') }}" class="nav-link {% if request.endpoint == 'config_page' %}active{% endif %}">
            <i class="bi bi-gear"></i> Settings
        </a>
    </nav>
    <div class="sidebar-footer">
        <button class="btn btn-sm btn-outline-secondary w-100" onclick="toggleTheme()">
            <i class="bi bi-circle-half" id="theme-icon"></i> Toggle Theme
        </button>
    </div>
</div>

<!-- Main Content -->
<div class="main-content" id="main-content">
    <!-- Top Bar -->
    <div class="topbar d-flex align-items-center justify-content-between px-4 py-2">
        <button class="btn btn-sm btn-outline-secondary" onclick="toggleSidebar()">
            <i class="bi bi-list fs-5"></i>
        </button>
        <div class="d-flex align-items-center gap-3">
            <button class="btn btn-info btn-sm" data-bs-toggle="modal" data-bs-target="#syncModal">
                <i class="bi bi-cloud-download me-1"></i> Preload / Refresh Data
            </button>
            <span class="badge bg-secondary">ServiceNow Flow Explorer</span>
        </div>
    </div>

    <!-- Flash Messages -->
    <div class="px-4 pt-2">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
    </div>

    <!-- Page Content -->
    <div class="content-area px-4 py-3">
        {% block content %}{% endblock %}
    </div>
</div>

<!-- Sync Modal -->
<div class="modal fade" id="syncModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-cloud-download me-2"></i>Preload / Refresh Data</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-muted">This will sync all flows, subflows, actions, and script includes from ServiceNow into the local database.</p>
                <div id="sync-log-container" class="bg-dark rounded p-3 font-monospace small" style="height:300px;overflow-y:auto;display:none;">
                </div>
                <div id="sync-idle-msg" class="text-center py-4">
                    <i class="bi bi-cloud-download fs-1 text-info"></i>
                    <p class="mt-2">Click "Start Sync" to begin.</p>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                <button class="btn btn-info" id="start-sync-btn" onclick="startSync()">
                    <i class="bi bi-play-fill me-1"></i> Start Sync
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Toast Container -->
<div class="toast-container position-fixed bottom-0 end-0 p-3" id="toast-container"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/dataTables.bootstrap5.min.js"></script>
<script src="{{ url_for('static', filename='js/main.js') }}"></script>
{% block scripts %}{% endblock %}
</body>
</html>
"""

# ─────────────────────────────────────────
# templates/dashboard.html
# ─────────────────────────────────────────
files['templates/dashboard.html'] = """{% extends 'base.html' %}
{% block title %}Dashboard - SN Flow Explorer{% endblock %}
{% block content %}
<div class="page-header mb-4">
    <h2><i class="bi bi-speedometer2 me-2 text-info"></i>Dashboard</h2>
    <p class="text-muted">Overview of synced ServiceNow data</p>
</div>

{% if base_url %}
<div class="alert alert-info d-flex align-items-center mb-4">
    <i class="bi bi-link-45deg me-2 fs-5"></i>
    <div>Connected to: <strong>{{ base_url }}</strong> as <strong>{{ username }}</strong></div>
</div>
{% else %}
<div class="alert alert-warning d-flex align-items-center mb-4">
    <i class="bi bi-exclamation-triangle me-2 fs-5"></i>
    <div>No ServiceNow instance configured. <a href="{{ url_for('config_page') }}">Configure now →</a></div>
</div>
{% endif %}

<div class="row g-4 mb-4">
    <div class="col-md-3">
        <div class="stat-card card h-100">
            <div class="card-body text-center">
                <i class="bi bi-diagram-3 fs-1 text-info mb-2"></i>
                <h2 class="fw-bold">{{ stats.flows }}</h2>
                <p class="text-muted mb-0">Flows & Subflows</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card card h-100">
            <div class="card-body text-center">
                <i class="bi bi-code-square fs-1 text-success mb-2"></i>
                <h2 class="fw-bold">{{ stats.script_includes }}</h2>
                <p class="text-muted mb-0">Script Includes</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card card h-100">
            <div class="card-body text-center">
                <i class="bi bi-lightning fs-1 text-warning mb-2"></i>
                <h2 class="fw-bold">{{ stats.action_types }}</h2>
                <p class="text-muted mb-0">Action Types</p>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card card h-100">
            <div class="card-body text-center">
                <i class="bi bi-list-task fs-1 text-danger mb-2"></i>
                <h2 class="fw-bold">{{ stats.step_instances }}</h2>
                <p class="text-muted mb-0">Step Instances</p>
            </div>
        </div>
    </div>
</div>

<div class="row g-4">
    <div class="col-md-6">
        <div class="card h-100">
            <div class="card-header"><i class="bi bi-rocket me-2"></i>Quick Actions</div>
            <div class="card-body d-flex flex-column gap-3">
                <button class="btn btn-info" data-bs-toggle="modal" data-bs-target="#syncModal">
                    <i class="bi bi-cloud-download me-2"></i>Preload / Refresh Data from ServiceNow
                </button>
                <a href="{{ url_for('analyzer') }}" class="btn btn-outline-success">
                    <i class="bi bi-search me-2"></i>Open Script Include Analyzer
                </a>
                <a href="{{ url_for('database_console') }}" class="btn btn-outline-warning">
                    <i class="bi bi-database me-2"></i>Open Database Console
                </a>
                <a href="{{ url_for('config_page') }}" class="btn btn-outline-secondary">
                    <i class="bi bi-gear me-2"></i>Configure ServiceNow Connection
                </a>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card h-100">
            <div class="card-header"><i class="bi bi-info-circle me-2"></i>About</div>
            <div class="card-body">
                <p>ServiceNow Flow Explorer helps you:</p>
                <ul>
                    <li>Sync Flows, Subflows, Actions, and Script Includes locally</li>
                    <li>Analyze which Flows reference a specific Script Include</li>
                    <li>Browse and query the local SQLite database</li>
                    <li>Export data to CSV for offline analysis</li>
                </ul>
                <p class="text-muted small mb-0">Data is stored locally in SQLite for fast, offline analysis.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

# ─────────────────────────────────────────
# templates/config.html
# ─────────────────────────────────────────
files['templates/config.html'] = """{% extends 'base.html' %}
{% block title %}Settings - SN Flow Explorer{% endblock %}
{% block content %}
<div class="page-header mb-4">
    <h2><i class="bi bi-gear me-2 text-info"></i>Settings</h2>
    <p class="text-muted">Configure your ServiceNow connection</p>
</div>

<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header"><i class="bi bi-shield-lock me-2"></i>ServiceNow Credentials</div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Instance Base URL</label>
                        <input type="url" name="base_url" class="form-control"
                               placeholder="https://yourinstance.service-now.com"
                               value="{{ base_url }}" required>
                        <div class="form-text">Do not include trailing slash.</div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Username</label>
                        <input type="text" name="username" class="form-control"
                               placeholder="admin" value="{{ username }}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control"
                               placeholder="Leave blank to keep existing password">
                        <div class="form-text">Password is stored encrypted.</div>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-info">
                            <i class="bi bi-save me-1"></i> Save Configuration
                        </button>
                        <button type="button" class="btn btn-outline-success" onclick="testConnection()">
                            <i class="bi bi-wifi me-1"></i> Test Connection
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <div class="card mt-4">
            <div class="card-header"><i class="bi bi-shield-check me-2"></i>Connection Status</div>
            <div class="card-body" id="connection-status">
                <p class="text-muted">Click "Test Connection" to verify your credentials.</p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
function testConnection() {
    const statusDiv = document.getElementById('connection-status');
    statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm text-info me-2"></div> Testing connection...';
    fetch('/api/test-connection', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                statusDiv.innerHTML = '<div class="alert alert-success mb-0"><i class="bi bi-check-circle me-2"></i>' + data.message + '</div>';
            } else {
                statusDiv.innerHTML = '<div class="alert alert-danger mb-0"><i class="bi bi-x-circle me-2"></i>' + data.message + '</div>';
            }
        })
        .catch(e => {
            statusDiv.innerHTML = '<div class="alert alert-danger mb-0">Error: ' + e.message + '</div>';
        });
}
</script>
{% endblock %}
"""

# ─────────────────────────────────────────
# templates/analyzer.html
# ─────────────────────────────────────────
files['templates/analyzer.html'] = """{% extends 'base.html' %}
{% block title %}Analyzer - SN Flow Explorer{% endblock %}
{% block content %}
<div class="page-header mb-4">
    <h2><i class="bi bi-search me-2 text-info"></i>Script Include Analyzer</h2>
    <p class="text-muted">Find which Flows, Subflows, and Actions reference a specific Script Include</p>
</div>

<div class="card mb-4">
    <div class="card-body">
        <div class="input-group">
            <span class="input-group-text"><i class="bi bi-search"></i></span>
            <input type="text" id="search-input" class="form-control form-control-lg"
                   placeholder="Enter Script Include name (e.g. MyScriptInclude)">
            <button class="btn btn-info btn-lg" onclick="runAnalysis()">
                <i class="bi bi-play-fill me-1"></i> Analyze
            </button>
        </div>
        <div class="form-text mt-2">Search is case-insensitive and looks for partial matches in flow definitions.</div>
    </div>
</div>

<div id="results-container" style="display:none;">
    <!-- Flows -->
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="bi bi-diagram-3 me-2 text-info"></i>Flows & Subflows</span>
            <span class="badge bg-info" id="flows-count">0</span>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0" id="flows-table">
                    <thead><tr><th>Name</th><th>Type</th><th>Active</th><th>Sys ID</th></tr></thead>
                    <tbody id="flows-body"></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Action Types -->
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="bi bi-lightning me-2 text-warning"></i>Action Types</span>
            <span class="badge bg-warning text-dark" id="actions-count">0</span>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0" id="actions-table">
                    <thead><tr><th>Name</th><th>Active</th><th>Sys ID</th></tr></thead>
                    <tbody id="actions-body"></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Step Instances -->
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="bi bi-list-task me-2 text-danger"></i>Step Instances</span>
            <span class="badge bg-danger" id="steps-count">0</span>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0" id="steps-table">
                    <thead><tr><th>Name</th><th>Flow Sys ID</th><th>Sys ID</th></tr></thead>
                    <tbody id="steps-body"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<div id="no-results" style="display:none;" class="text-center py-5">
    <i class="bi bi-emoji-frown fs-1 text-muted"></i>
    <p class="mt-3 text-muted">No references found. Try a different search term or sync data first.</p>
</div>

<div id="loading" style="display:none;" class="text-center py-5">
    <div class="spinner-border text-info"></div>
    <p class="mt-3">Analyzing...</p>
</div>
{% endblock %}
{% block scripts %}
<script>
document.getElementById('search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') runAnalysis();
});

function runAnalysis() {
    const term = document.getElementById('search-input').value.trim();
    if (!term) { showToast('Please enter a search term.', 'warning'); return; }

    document.getElementById('results-container').style.display = 'none';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('loading').style.display = 'block';

    fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_term: term })
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById('loading').style.display = 'none';
        const total = data.flows.length + data.action_types.length + data.step_instances.length;

        if (total === 0) {
            document.getElementById('no-results').style.display = 'block';
            return;
        }

        document.getElementById('results-container').style.display = 'block';
        document.getElementById('flows-count').textContent = data.flows.length;
        document.getElementById('actions-count').textContent = data.action_types.length;
        document.getElementById('steps-count').textContent = data.step_instances.length;

        const flowsBody = document.getElementById('flows-body');
        flowsBody.innerHTML = data.flows.map(f =>
            `<tr><td>${f.name}</td><td><span class="badge bg-secondary">${f.type}</span></td>
             <td>${f.active === 'true' ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}</td>
             <td><code>${f.sys_id}</code></td></tr>`
        ).join('') || '<tr><td colspan="4" class="text-muted text-center">None found</td></tr>';

        const actionsBody = document.getElementById('actions-body');
        actionsBody.innerHTML = data.action_types.map(a =>
            `<tr><td>${a.name}</td>
             <td>${a.active === 'true' ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}</td>
             <td><code>${a.sys_id}</code></td></tr>`
        ).join('') || '<tr><td colspan="3" class="text-muted text-center">None found</td></tr>';

        const stepsBody = document.getElementById('steps-body');
        stepsBody.innerHTML = data.step_instances.map(s =>
            `<tr><td>${s.name}</td><td><code>${s.flow_sys_id || 'N/A'}</code></td><td><code>${s.sys_id}</code></td></tr>`
        ).join('') || '<tr><td colspan="3" class="text-muted text-center">None found</td></tr>';

        showToast(`Found ${total} reference(s) for "${term}"`, 'success');
    })
    .catch(e => {
        document.getElementById('loading').style.display = 'none';
        showToast('Error: ' + e.message, 'danger');
    });
}
</script>
{% endblock %}
"""

# ─────────────────────────────────────────
# templates/database_console.html
# ─────────────────────────────────────────
files['templates/database_console.html'] = """{% extends 'base.html' %}
{% block title %}Database Console - SN Flow Explorer{% endblock %}
{% block content %}
<div class="page-header mb-4">
    <h2><i class="bi bi-database me-2 text-info"></i>Database Console</h2>
    <p class="text-muted">Browse, query, and manage the local SQLite database</p>
</div>

<div class="row g-3">
    <!-- Left Panel: Tables -->
    <div class="col-md-2">
        <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-table me-1"></i>Tables</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="loadTables()">
                    <i class="bi bi-arrow-clockwise"></i>
                </button>
            </div>
            <div class="list-group list-group-flush" id="tables-list">
                <div class="list-group-item text-muted small">Loading...</div>
            </div>
        </div>
    </div>

    <!-- Main Area -->
    <div class="col-md-10">
        <!-- SQL Console -->
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span><i class="bi bi-terminal me-2"></i>SQL Query Console</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="loadQueryHistory()">
                    <i class="bi bi-clock-history me-1"></i>History
                </button>
            </div>
            <div class="card-body">
                <textarea id="sql-query" class="form-control font-monospace mb-2"
                          rows="4" placeholder="SELECT * FROM sn_flows LIMIT 10;"></textarea>
                <div class="d-flex gap-2">
                    <button class="btn btn-info" onclick="executeQuery()">
                        <i class="bi bi-play-fill me-1"></i>Execute
                    </button>
                    <button class="btn btn-outline-secondary" onclick="document.getElementById('sql-query').value=''">
                        <i class="bi bi-x me-1"></i>Clear
                    </button>
                </div>
            </div>
        </div>

        <!-- Query History -->
        <div class="card mb-3" id="history-panel" style="display:none;">
            <div class="card-header">
                <i class="bi bi-clock-history me-2"></i>Query History (Last 10)
            </div>
            <div class="list-group list-group-flush" id="history-list"></div>
        </div>

        <!-- Query Results -->
        <div class="card mb-3" id="query-results-card" style="display:none;">
            <div class="card-header"><i class="bi bi-table me-2"></i>Query Results</div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0" id="query-results-table">
                        <thead id="query-results-head"></thead>
                        <tbody id="query-results-body"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Table Viewer -->
        <div class="card" id="table-viewer-card" style="display:none;">
            <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
                <span><i class="bi bi-grid me-2"></i>Table: <strong id="current-table-name"></strong></span>
                <div class="d-flex gap-2 flex-wrap">
                    <button class="btn btn-sm btn-outline-success" onclick="exportCSV()">
                        <i class="bi bi-download me-1"></i>Export CSV
                    </button>
                    <button class="btn btn-sm btn-outline-warning" onclick="truncateTable()">
                        <i class="bi bi-trash me-1"></i>Truncate
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="showDeleteDbModal()">
                        <i class="bi bi-database-x me-1"></i>Delete DB
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="vacuumDb()">
                        <i class="bi bi-stars me-1"></i>Vacuum
                    </button>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0 display" id="table-viewer" style="width:100%">
                        <thead id="table-viewer-head"></thead>
                        <tbody id="table-viewer-body"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Row Detail Modal -->
<div class="modal fade" id="rowDetailModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-card-text me-2"></i>Row Detail</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="row-detail-body"></div>
            <div class="modal-footer">
                <button class="btn btn-danger" id="delete-row-btn">
                    <i class="bi bi-trash me-1"></i>Delete Row
                </button>
                <button class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<!-- Delete DB Modal -->
<div class="modal fade" id="deleteDbModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content border-danger">
            <div class="modal-header bg-danger text-white">
                <h5 class="modal-title"><i class="bi bi-exclamation-triangle me-2"></i>Delete Entire Database</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="text-danger fw-bold">⚠️ This will permanently delete ALL data!</p>
                <p>Type <strong>DELETE</strong> to confirm:</p>
                <input type="text" id="delete-confirm-input" class="form-control" placeholder="Type DELETE here">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button class="btn btn-danger" onclick="deleteDatabase()">
                    <i class="bi bi-database-x me-1"></i>Delete Database
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block scripts %}
<script>
let currentTable = null;
let currentRowId = null;
let dtInstance = null;

// Load tables on page load
loadTables();

function loadTables() {
    fetch('/api/db/tables')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('tables-list');
            if (data.tables.length === 0) {
                list.innerHTML = '<div class="list-group-item text-muted small">No tables found</div>';
                return;
            }
            list.innerHTML = data.tables.map(t =>
                `<button class="list-group-item list-group-item-action small py-2" onclick="loadTable('${t}')">${t}</button>`
            ).join('');
        });
}

function loadTable(tableName) {
    currentTable = tableName;
    document.getElementById('current-table-name').textContent = tableName;
    document.getElementById('table-viewer-card').style.display = 'block';

    // Highlight active table
    document.querySelectorAll('#tables-list button').forEach(b => {
        b.classList.toggle('active', b.textContent === tableName);
    });

    fetch(`/api/db/table/${tableName}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showToast(data.error, 'danger'); return; }

            const head = document.getElementById('table-viewer-head');
            const body = document.getElementById('table-viewer-body');

            head.innerHTML = '<tr>' + data.columns.map(c => `<th>${c}</th>`).join('') + '<th>Actions</th></tr>';

            body.innerHTML = data.rows.map(row => {
                const cells = data.columns.map(c => {
                    const val = row[c] !== null && row[c] !== undefined ? String(row[c]) : '';
                    return `<td title="${val.replace(/"/g, '&quot;')}">${val.length > 50 ? val.substring(0, 50) + '...' : val}</td>`;
                }).join('');
                return `<tr>${cells}<td><button class="btn btn-xs btn-outline-info btn-sm py-0 px-1" onclick='showRowDetail(${JSON.stringify(row)})'>
                    <i class="bi bi-eye"></i></button></td></tr>`;
            }).join('');

            if (dtInstance) { dtInstance.destroy(); }
            dtInstance = $('#table-viewer').DataTable({
                pageLength: 25,
                scrollX: true,
                order: []
            });
        });
}

function showRowDetail(row) {
    currentRowId = row.id;
    const body = document.getElementById('row-detail-body');
    body.innerHTML = '<div class="table-responsive"><table class="table table-sm">' +
        Object.entries(row).map(([k, v]) =>
            `<tr><th class="w-25">${k}</th><td><pre class="mb-0 small" style="white-space:pre-wrap;word-break:break-all;">${v !== null ? v : '<em class="text-muted">null</em>'}</pre></td></tr>`
        ).join('') + '</table></div>';

    document.getElementById('delete-row-btn').onclick = function() {
        if (confirm('Delete this row?')) deleteRow(currentRowId);
    };

    new bootstrap.Modal(document.getElementById('rowDetailModal')).show();
}

function deleteRow(id) {
    fetch('/api/db/delete-row', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: currentTable, id: id })
    })
    .then(r => r.json())
    .then(data => {
        bootstrap.Modal.getInstance(document.getElementById('rowDetailModal')).hide();
        if (data.success) {
            showToast('Row deleted.', 'success');
            loadTable(currentTable);
        } else {
            showToast(data.error, 'danger');
        }
    });
}

function executeQuery() {
    const query = document.getElementById('sql-query').value.trim();
    if (!query) { showToast('Please enter a query.', 'warning'); return; }

    fetch('/api/db/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
    })
    .then(r => r.json())
    .then(data => {
        const card = document.getElementById('query-results-card');
        card.style.display = 'block';

        if (!data.success) {
            document.getElementById('query-results-head').innerHTML = '';
            document.getElementById('query-results-body').innerHTML =
                `<tr><td class="text-danger"><i class="bi bi-x-circle me-2"></i>${data.error}</td></tr>`;
            showToast('Query failed: ' + data.error, 'danger');
            return;
        }

        if (data.columns.length > 0) {
            document.getElementById('query-results-head').innerHTML =
                '<tr>' + data.columns.map(c => `<th>${c}</th>`).join('') + '</tr>';
            document.getElementById('query-results-body').innerHTML =
                data.rows.map(row =>
                    '<tr>' + data.columns.map(c => `<td>${row[c] !== null ? row[c] : ''}</td>`).join('') + '</tr>'
                ).join('') || '<tr><td colspan="' + data.columns.length + '" class="text-muted text-center">No rows returned</td></tr>';
            showToast(`Query returned ${data.rows.length} row(s).`, 'success');
        } else {
            document.getElementById('query-results-head').innerHTML = '';
            document.getElementById('query-results-body').innerHTML =
                `<tr><td class="text-success"><i class="bi bi-check-circle me-2"></i>Query executed. Rows affected: ${data.rowcount}</td></tr>`;
            showToast(`Query executed. Rows affected: ${data.rowcount}`, 'success');
        }
    });
}

function loadQueryHistory() {
    const panel = document.getElementById('history-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'none') return;

    fetch('/api/db/query-history')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('history-list');
            list.innerHTML = data.history.map(h =>
                `<button class="list-group-item list-group-item-action small py-2 ${h.success ? '' : 'list-group-item-danger'}"
                 onclick="document.getElementById('sql-query').value='${h.query.replace(/'/g, "\\'")}'; document.getElementById('history-panel').style.display='none';">
                 <code>${h.query.substring(0, 80)}${h.query.length > 80 ? '...' : ''}</code>
                 <small class="text-muted d-block">${h.executed_at}</small></button>`
            ).join('') || '<div class="list-group-item text-muted">No history yet.</div>';
        });
}

function exportCSV() {
    if (!currentTable) { showToast('Select a table first.', 'warning'); return; }
    window.location.href = `/api/db/export/${currentTable}`;
}

function truncateTable() {
    if (!currentTable) { showToast('Select a table first.', 'warning'); return; }
    if (!confirm(`Truncate table "${currentTable}"? All data will be deleted.`)) return;
    fetch('/api/db/truncate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: currentTable })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) { showToast('Table truncated.', 'success'); loadTable(currentTable); }
        else showToast(data.error, 'danger');
    });
}

function vacuumDb() {
    fetch('/api/db/vacuum', { method: 'POST' })
        .then(r => r.json())
        .then(data => showToast(data.success ? data.message : data.error, data.success ? 'success' : 'danger'));
}

function showDeleteDbModal() {
    document.getElementById('delete-confirm-input').value = '';
    new bootstrap.Modal(document.getElementById('deleteDbModal')).show();
}

function deleteDatabase() {
    const confirmation = document.getElementById('delete-confirm-input').value;
    fetch('/api/db/delete-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation: confirmation })
    })
    .then(r => r.json())
    .then(data => {
        bootstrap.Modal.getInstance(document.getElementById('deleteDbModal')).hide();
        if (data.success) {
            showToast(data.message, 'success');
            loadTables();
            document.getElementById('table-viewer-card').style.display = 'none';
        } else {
            showToast(data.error, 'danger');
        }
    });
}
</script>
{% endblock %}
"""

# ─────────────────────────────────────────
# static/css/style.css
# ─────────────────────────────────────────
files['static/css/style.css'] = """
:root {
    --sidebar-width: 240px;
    --topbar-height: 56px;
    --accent: #0dcaf0;
}

body { margin: 0; font-family: 'Segoe UI', sans-serif; }

/* Sidebar */
.sidebar {
    position: fixed;
    top: 0; left: 0;
    width: var(--sidebar-width);
    height: 100vh;
    background: #0f1117;
    border-right: 1px solid #1e2130;
    display: flex;
    flex-direction: column;
    z-index: 1000;
    transition: transform 0.3s ease;
}

.sidebar-brand {
    padding: 1.2rem 1rem;
    font-size: 1.1rem;
    font-weight: 700;
    color: #fff;
    border-bottom: 1px solid #1e2130;
    display: flex;
    align-items: center;
}

.sidebar-nav {
    flex: 1;
    padding: 1rem 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.sidebar-nav .nav-link {
    color: #adb5bd;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.95rem;
    transition: all 0.2s;
    text-decoration: none;
}

.sidebar-nav .nav-link:hover,
.sidebar-nav .nav-link.active {
    background: #1e2130;
    color: var(--accent);
}

.sidebar-footer {
    padding: 1rem;
    border-top: 1px solid #1e2130;
}

/* Main Content */
.main-content {
    margin-left: var(--sidebar-width);
    min-height: 100vh;
    transition: margin-left 0.3s ease;
}

.topbar {
    height: var(--topbar-height);
    background: #0f1117;
    border-bottom: 1px solid #1e2130;
    position: sticky;
    top: 0;
    z-index: 999;
}

.content-area { min-height: calc(100vh - var(--topbar-height)); }

/* Stat Cards */
.stat-card {
    border: 1px solid #1e2130;
    background: #0f1117;
    transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(13, 202, 240, 0.15);
}

/* Cards */
.card {
    border: 1px solid #1e2130;
    background: #0f1117;
}

.card-header {
    background: #1e2130;
    border-bottom: 1px solid #2a2f45;
    font-weight: 600;
}

/* Page Header */
.page-header h2 { font-weight: 700; }

/* Sidebar collapsed */
.sidebar.collapsed { transform: translateX(-100%); }
.main-content.expanded { margin-left: 0; }

/* Light mode overrides */
[data-bs-theme="light"] .sidebar { background: #f8f9fa; border-right: 1px solid #dee2e6; }
[data-bs-theme="light"] .sidebar-brand { color: #212529; }
[data-bs-theme="light"] .sidebar-nav .nav-link { color: #495057; }
[data-bs-theme="light"] .sidebar-nav .nav-link:hover,
[data-bs-theme="light"] .sidebar-nav .nav-link.active { background: #e9ecef; color: #0dcaf0; }
[data-bs-theme="light"] .topbar { background: #f8f9fa; border-bottom: 1px solid #dee2e6; }
[data-bs-theme="light"] .card { background: #fff; border-color: #dee2e6; }
[data-bs-theme="light"] .card-header { background: #f8f9fa; border-bottom-color: #dee2e6; }
[data-bs-theme="light"] .stat-card { background: #fff; }

/* Responsive */
@media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); }
    .sidebar.open { transform: translateX(0); }
    .main-content { margin-left: 0; }
}
"""

# ─────────────────────────────────────────
# static/js/main.js
# ─────────────────────────────────────────
files['static/js/main.js'] = """
// ─────────────────────────────────────────
// Theme Toggle
// ─────────────────────────────────────────
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-bs-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', next);
    localStorage.setItem('theme', next);
}

// Apply saved theme
(function() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', saved);
})();

// ─────────────────────────────────────────
// Sidebar Toggle
// ─────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const main = document.getElementById('main-content');
    sidebar.classList.toggle('collapsed');
    main.classList.toggle('expanded');
}

// ─────────────────────────────────────────
// Toast Notifications
// ─────────────────────────────────────────
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const id = 'toast-' + Date.now();
    const icons = { success: 'check-circle-fill', danger: 'x-circle-fill', warning: 'exclamation-triangle-fill', info: 'info-circle-fill' };
    const icon = icons[type] || 'info-circle-fill';

    const html = `
        <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${icon} me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`;

    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// ─────────────────────────────────────────
// Sync Logic
// ─────────────────────────────────────────
let syncInterval = null;

function startSync() {
    const btn = document.getElementById('start-sync-btn');
    const logContainer = document.getElementById('sync-log-container');
    const idleMsg = document.getElementById('sync-idle-msg');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Syncing...';
    logContainer.style.display = 'block';
    idleMsg.style.display = 'none';
    logContainer.innerHTML = '';

    fetch('/api/sync', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                showToast(data.message, 'danger');
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-fill me-1"></i> Start Sync';
                return;
            }
            syncInterval = setInterval(pollSyncLogs, 1000);
        });
}

function pollSyncLogs() {
    fetch('/api/sync-logs')
        .then(r => r.json())
        .then(data => {
            const logContainer = document.getElementById('sync-log-container');
            logContainer.innerHTML = data.logs.map(l => {
                let cls = 'text-light';
                if (l.startsWith('✅') || l.startsWith('🎉')) cls = 'text-success';
                else if (l.startsWith('❌')) cls = 'text-danger';
                else if (l.startsWith('⚠️')) cls = 'text-warning';
                else if (l.startsWith('🔄')) cls = 'text-info';
                return `<div class="${cls}">${l}</div>`;
            }).join('');
            logContainer.scrollTop = logContainer.scrollHeight;

            if (!data.running) {
                clearInterval(syncInterval);
                const btn = document.getElementById('start-sync-btn');
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-fill me-1"></i> Start Sync';
                showToast('Sync completed!', 'success');
            }
        });
}
"""

# ─────────────────────────────────────────
# FILE WRITER
# ─────────────────────────────────────────
def create_files(): 
    for filepath, content in files.items(): 
        dirpath = os.path.dirname(filepath) 
        if dirpath: 
            os.makedirs(dirpath, exist_ok=True) 
        with open(filepath, 'w', encoding='utf-8') as f: 
            f.write(content) 
            print(f'✅ Created: {filepath}')


# Create required directories
for d in ['instance', 'static/css', 'static/js', 'templates']:
    os.makedirs(d, exist_ok=True)

print()
print('🎉 Project generated successfully!')
print()
print('Next steps:')
print('  1. python -m venv venv')
print('  2. venv\\Scripts\\activate     # On Windows')
print('  3. pip install -r requirements.txt')
print('  4. python run.py')
print('  5. Open http://localhost:5000')


if __name__ == '__main__': 
    create_files()