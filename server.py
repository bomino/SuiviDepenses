import os
import uuid
from contextlib import contextmanager
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user,
)
import bcrypt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HTML_FILE = 'index.html'

ALLOWED_CATEGORIES = {'Materials', 'Labor', 'Equipment', 'Permits', 'Subcontractors', 'Transport', 'Utilities', 'Misc'}
ALLOWED_STATUSES = {'Paid', 'Pending', 'Unpaid'}
SERVABLE_FILES = {'index.html', 'manifest.json', 'sw.js'}
SERVABLE_ICON_PREFIX = 'icons/'

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if USE_POSTGRES:
        raise RuntimeError("SECRET_KEY environment variable is required in production")
    SECRET_KEY = 'dev-only-do-not-use-in-production'
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if USE_POSTGRES:
    app.config['SESSION_COOKIE_SECURE'] = True

login_manager = LoginManager(app)

if USE_POSTGRES:
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    PH = '%s'
    AMOUNT_TYPE = 'NUMERIC'
    LIST_ORDER = "ORDER BY date DESC, id DESC"

    _pool = ConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=int(os.environ.get('DB_POOL_MAX', '5')),
        kwargs={'row_factory': dict_row},
        open=True,
    )

    def get_conn():
        return _pool.connection()
else:
    import sqlite3

    DB = os.path.join(BASE_DIR, 'expenses.db')
    PH = '?'
    AMOUNT_TYPE = 'REAL'
    LIST_ORDER = "ORDER BY date DESC, rowid DESC"

    @contextmanager
    def get_conn():
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()


def q(sql, params=()):
    """Execute SQL and return (rows, rowcount). Manages connection lifecycle."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall() if cur.description else []
        rc = cur.rowcount
        conn.commit()
        return rows, rc


def _schema_needs_wipe(cur):
    """Return True if any new column from the latest migration is missing.
    Each schema migration appends a probe here so subsequent boots re-detect
    correctly. Idempotent once the new columns exist."""
    try:
        cur.execute("SELECT is_admin FROM users LIMIT 1")
        cur.execute("SELECT user_id FROM expenses LIMIT 1")
        cur.execute("SELECT project_id FROM users LIMIT 1")  # multi-site migration
        cur.execute("SELECT project_id FROM expenses LIMIT 1")
        return False
    except Exception:
        # Postgres aborts the whole transaction when a SELECT references a
        # missing column; the rollback frees the connection so the DROP
        # statements that follow can run. SQLite's rollback() is a no-op here.
        cur.connection.rollback()
        return True


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        if _schema_needs_wipe(cur):
            # First boot of a new schema generation. The user opted in to
            # wipe-and-recreate when this app moved to multi-tenant.
            cur.execute("DROP TABLE IF EXISTS expenses")
            cur.execute("DROP TABLE IF EXISTS project")    # legacy singleton
            cur.execute("DROP TABLE IF EXISTS projects")   # current
            cur.execute("DROP TABLE IF EXISTS users")
            conn.commit()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                project_id TEXT REFERENCES projects(id) ON DELETE SET NULL
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                amount {AMOUNT_TYPE} NOT NULL,
                category TEXT NOT NULL DEFAULT 'Materials',
                date TEXT NOT NULL,
                paid_by TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Paid',
                notes TEXT DEFAULT ''
            )
        """)
        conn.commit()


init_db()


def bootstrap_initial_user():
    """If no users exist, create:
       - a default project (named via INITIAL_PROJECT_NAME, default 'My Project')
       - an admin user (from INITIAL_USERNAME / INITIAL_PASSWORD) assigned to it.
    Idempotent: skips when any user already exists."""
    rows, _ = q("SELECT COUNT(*) AS c FROM users")
    count = rows[0]['c'] if rows else 0
    if count > 0:
        return

    username = (os.environ.get('INITIAL_USERNAME') or '').strip()
    password = (os.environ.get('INITIAL_PASSWORD') or '').strip()
    if not username or not password:
        if USE_POSTGRES:
            print("WARNING: no users in DB and INITIAL_USERNAME/INITIAL_PASSWORD not set. "
                  "Run scripts/add_user.py to create one before the app is usable.")
        return

    project_name = (os.environ.get('INITIAL_PROJECT_NAME') or 'My Project').strip() or 'My Project'

    # Reuse an existing project of the same name if one happens to be there;
    # otherwise create one.
    existing, _ = q(f"SELECT id FROM projects WHERE name = {PH}", (project_name,))
    if existing:
        project_id = existing[0]['id']
    else:
        project_id = uuid.uuid4().hex
        q(f"INSERT INTO projects (id, name) VALUES ({PH}, {PH})", (project_id, project_name))

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    q(f"INSERT INTO users (id, username, password_hash, is_admin, project_id) VALUES ({PH}, {PH}, {PH}, {PH}, {PH})",
      (uuid.uuid4().hex, username, pw_hash, True, project_id))
    print(f"Bootstrapped initial admin user '{username}' on project '{project_name}'")


bootstrap_initial_user()


# ─── auth ───
class User(UserMixin):
    def __init__(self, id, username, is_admin=False, project_id=None):
        self.id = id
        self.username = username
        self.is_admin = bool(is_admin)
        self.project_id = project_id


@login_manager.user_loader
def load_user(user_id):
    rows, _ = q(f"SELECT id, username, is_admin, project_id FROM users WHERE id = {PH}", (user_id,))
    if not rows:
        return None
    r = rows[0]
    return User(r['id'], r['username'], r['is_admin'], r['project_id'])


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required'}), 401


def admin_required(f):
    """Gate a route on current_user.is_admin. Combines with login_required."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapper


def _user_payload(uid, username, is_admin, project_id):
    """Common shape returned by /api/login and /api/me. Joins the project name
    so the frontend has everything it needs in one round trip."""
    project_name = None
    if project_id:
        rows, _ = q(f"SELECT name FROM projects WHERE id = {PH}", (project_id,))
        if rows:
            project_name = rows[0]['name']
    return {
        'id': uid,
        'username': username,
        'is_admin': bool(is_admin),
        'project_id': project_id,
        'project_name': project_name,
    }


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    rows, _ = q(f"SELECT id, username, password_hash, is_admin, project_id FROM users WHERE username = {PH}", (username,))
    if not rows:
        return jsonify({'error': 'Invalid credentials'}), 401

    r = rows[0]
    if not bcrypt.checkpw(password.encode('utf-8'), r['password_hash'].encode('utf-8')):
        return jsonify({'error': 'Invalid credentials'}), 401

    login_user(User(r['id'], r['username'], r['is_admin'], r['project_id']), remember=True)
    return jsonify(_user_payload(r['id'], r['username'], r['is_admin'], r['project_id']))


@app.route('/api/logout', methods=['POST'])
def api_logout():
    logout_user()
    return '', 204


@app.route('/api/me', methods=['GET'])
def api_me():
    if current_user.is_authenticated:
        return jsonify(_user_payload(
            current_user.id, current_user.username, current_user.is_admin, current_user.project_id
        ))
    return jsonify({'error': 'Authentication required'}), 401


# ─── user management (admin) ───
@app.route('/api/users', methods=['GET'])
@admin_required
def users_list():
    rows, _ = q("""
        SELECT u.id, u.username, u.is_admin, u.project_id, p.name AS project_name
        FROM users u
        LEFT JOIN projects p ON p.id = u.project_id
        ORDER BY u.username
    """)
    return jsonify([
        {
            'id': r['id'],
            'username': r['username'],
            'is_admin': bool(r['is_admin']),
            'project_id': r['project_id'],
            'project_name': r['project_name'],
        }
        for r in rows
    ])


@app.route('/api/users', methods=['POST'])
@admin_required
def users_create():
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    is_admin = bool(data.get('is_admin'))
    project_id = data.get('project_id') or None
    if not username:
        return jsonify({'error': 'Username required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    existing, _ = q(f"SELECT id FROM users WHERE username = {PH}", (username,))
    if existing:
        return jsonify({'error': 'Username already taken'}), 409

    if project_id:
        proj, _ = q(f"SELECT id FROM projects WHERE id = {PH}", (project_id,))
        if not proj:
            return jsonify({'error': 'Project not found'}), 400

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_id = uuid.uuid4().hex
    q(f"INSERT INTO users (id, username, password_hash, is_admin, project_id) VALUES ({PH}, {PH}, {PH}, {PH}, {PH})",
      (new_id, username, pw_hash, is_admin, project_id))
    return jsonify({
        'id': new_id, 'username': username, 'is_admin': is_admin, 'project_id': project_id
    }), 201


@app.route('/api/users/<uid>/project', methods=['POST'])
@admin_required
def users_set_project(uid):
    data = request.get_json(force=True)
    project_id = data.get('project_id') or None
    if project_id:
        proj, _ = q(f"SELECT id FROM projects WHERE id = {PH}", (project_id,))
        if not proj:
            return jsonify({'error': 'Project not found'}), 400
    _, rc = q(f"UPDATE users SET project_id = {PH} WHERE id = {PH}", (project_id, uid))
    if rc == 0:
        return jsonify({'error': 'User not found'}), 404
    return '', 204


@app.route('/api/users/<uid>', methods=['DELETE'])
@admin_required
def users_delete(uid):
    if uid == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    _, rc = q(f"DELETE FROM users WHERE id = {PH}", (uid,))
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return '', 204


@app.route('/api/users/<uid>/password', methods=['POST'])
@admin_required
def users_reset_password(uid):
    data = request.get_json(force=True)
    password = (data.get('password') or '').strip()
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    _, rc = q(f"UPDATE users SET password_hash = {PH} WHERE id = {PH}", (pw_hash, uid))
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return '', 204


@app.route('/api/users/<uid>/admin', methods=['POST'])
@admin_required
def users_set_admin(uid):
    data = request.get_json(force=True)
    is_admin = bool(data.get('is_admin'))
    if uid == current_user.id and not is_admin:
        return jsonify({'error': 'Cannot remove your own admin role'}), 400
    _, rc = q(f"UPDATE users SET is_admin = {PH} WHERE id = {PH}", (is_admin, uid))
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return '', 204


EXPENSE_INSERT_SQL = (
    f"INSERT INTO expenses (id, user_id, project_id, description, amount, category, date, paid_by, status, notes) "
    f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
)
EXPENSE_UPDATE_SQL = (
    f"UPDATE expenses SET description={PH}, amount={PH}, category={PH}, date={PH}, "
    f"paid_by={PH}, status={PH}, notes={PH} WHERE id={PH}"
)
EXPENSE_DELETE_SQL = f"DELETE FROM expenses WHERE id={PH}"
WORKER_SCOPE = f" AND user_id = {PH} AND project_id = {PH}"


def validated_expense(data):
    desc = (data.get('description') or '').strip()
    amount = data.get('amount')
    if not desc or isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return None, ('Description and a positive amount are required', 400)

    category = data.get('category', 'Materials')
    if category not in ALLOWED_CATEGORIES:
        return None, ('Invalid category', 400)

    status = data.get('status', 'Paid')
    if status not in ALLOWED_STATUSES:
        return None, ('Invalid status', 400)

    return {
        'description': desc[:120],
        'amount': float(amount),
        'category': category,
        'date': (data.get('date') or '')[:10],
        'paid_by': (data.get('paidBy') or '').strip()[:60],
        'status': status,
        'notes': (data.get('notes') or '').strip()[:200],
    }, None


# ─── health ───
@app.route('/health')
def health():
    """Cheap liveness probe. Checks DB reachability so Railway only routes traffic
    to workers whose backend wired up correctly on boot."""
    try:
        q("SELECT 1")
        return jsonify({'ok': True, 'engine': 'postgres' if USE_POSTGRES else 'sqlite'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 503


# ─── frontend ───
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, HTML_FILE)


@app.route('/<path:p>')
def static_file(p):
    if p in SERVABLE_FILES:
        return send_from_directory(BASE_DIR, p)
    if p.startswith(SERVABLE_ICON_PREFIX) and '..' not in p and p.endswith('.png'):
        return send_from_directory(BASE_DIR, p)
    abort(404)


# ─── projects (admin: full CRUD; everyone: read-only list of theirs) ───
@app.route('/api/projects', methods=['GET'])
@login_required
def projects_list():
    """Admins see every project; workers see only the one they're assigned to."""
    if current_user.is_admin:
        rows, _ = q("SELECT id, name FROM projects ORDER BY name")
    elif current_user.project_id:
        rows, _ = q(f"SELECT id, name FROM projects WHERE id = {PH}", (current_user.project_id,))
    else:
        rows = []
    return jsonify([{'id': r['id'], 'name': r['name']} for r in rows])


@app.route('/api/projects', methods=['POST'])
@admin_required
def projects_create():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()[:100]
    if not name:
        return jsonify({'error': 'Project name required'}), 400
    existing, _ = q(f"SELECT id FROM projects WHERE name = {PH}", (name,))
    if existing:
        return jsonify({'error': 'Project name already taken'}), 409
    pid = uuid.uuid4().hex
    q(f"INSERT INTO projects (id, name) VALUES ({PH}, {PH})", (pid, name))
    return jsonify({'id': pid, 'name': name}), 201


@app.route('/api/projects/<pid>', methods=['PUT'])
@admin_required
def projects_rename(pid):
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()[:100]
    if not name:
        return jsonify({'error': 'Project name required'}), 400
    clash, _ = q(f"SELECT id FROM projects WHERE name = {PH} AND id != {PH}", (name, pid))
    if clash:
        return jsonify({'error': 'Project name already taken'}), 409
    _, rc = q(f"UPDATE projects SET name = {PH} WHERE id = {PH}", (name, pid))
    if rc == 0:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify({'id': pid, 'name': name})


@app.route('/api/projects/<pid>', methods=['DELETE'])
@admin_required
def projects_delete(pid):
    """Cascades to expenses; users assigned to it get project_id = NULL."""
    _, rc = q(f"DELETE FROM projects WHERE id = {PH}", (pid,))
    if rc == 0:
        return jsonify({'error': 'Project not found'}), 404
    return '', 204


# ─── /api/project (singular) — convenience read/rename of the caller's current project ───
@app.route('/api/project', methods=['GET'])
@login_required
def project_get():
    if not current_user.project_id:
        return jsonify({'name': None, 'id': None})
    rows, _ = q(f"SELECT id, name FROM projects WHERE id = {PH}", (current_user.project_id,))
    if not rows:
        return jsonify({'name': None, 'id': None})
    return jsonify({'id': rows[0]['id'], 'name': rows[0]['name']})


@app.route('/api/project', methods=['PUT'])
@admin_required
def project_update():
    """Renames the admin's currently-assigned project."""
    if not current_user.project_id:
        return jsonify({'error': 'You are not assigned to a project to rename'}), 400
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()[:100]
    if not name:
        return jsonify({'error': 'Project name required'}), 400
    clash, _ = q(f"SELECT id FROM projects WHERE name = {PH} AND id != {PH}", (name, current_user.project_id))
    if clash:
        return jsonify({'error': 'Project name already taken'}), 409
    q(f"UPDATE projects SET name = {PH} WHERE id = {PH}", (name, current_user.project_id))
    return jsonify({'name': name})


# ─── expenses (hybrid scope: admins see all, workers see their own project's rows they created) ───
@app.route('/api/expenses', methods=['GET'])
@login_required
def expenses_list():
    if current_user.is_admin:
        rows, _ = q(f"SELECT * FROM expenses {LIST_ORDER}")
    elif current_user.project_id:
        rows, _ = q(
            f"SELECT * FROM expenses WHERE user_id = {PH} AND project_id = {PH} {LIST_ORDER}",
            (current_user.id, current_user.project_id),
        )
    else:
        rows = []  # unassigned worker -> nothing to show
    out = []
    for r in rows:
        d = dict(r)
        if 'amount' in d and d['amount'] is not None:
            d['amount'] = float(d['amount'])
        out.append(d)
    return jsonify(out)


@app.route('/api/expenses', methods=['POST'])
@login_required
def expenses_create():
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    # Workers always stamp their own project. Admins may target any project,
    # falling back to their own if none specified.
    if current_user.is_admin:
        project_id = data.get('project_id') or current_user.project_id
    else:
        project_id = current_user.project_id

    if not project_id:
        return jsonify({'error': 'You are not assigned to a project. Ask an admin to assign you.'}), 400

    proj, _ = q(f"SELECT id FROM projects WHERE id = {PH}", (project_id,))
    if not proj:
        return jsonify({'error': 'Project not found'}), 400

    eid = uuid.uuid4().hex
    q(EXPENSE_INSERT_SQL, (eid, current_user.id, project_id, fields['description'], fields['amount'],
                           fields['category'], fields['date'], fields['paid_by'],
                           fields['status'], fields['notes']))
    return jsonify({'id': eid, 'project_id': project_id}), 201


@app.route('/api/expenses/<eid>', methods=['PUT'])
@login_required
def expenses_update(eid):
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    base_params = (fields['description'], fields['amount'], fields['category'],
                   fields['date'], fields['paid_by'], fields['status'], fields['notes'])
    if current_user.is_admin:
        sql, params = EXPENSE_UPDATE_SQL, base_params + (eid,)
    else:
        if not current_user.project_id:
            return jsonify({'error': 'Not found'}), 404
        sql = EXPENSE_UPDATE_SQL + WORKER_SCOPE
        params = base_params + (eid, current_user.id, current_user.project_id)
    _, rc = q(sql, params)
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': eid})


@app.route('/api/expenses/<eid>', methods=['DELETE'])
@login_required
def expenses_delete(eid):
    if current_user.is_admin:
        sql, params = EXPENSE_DELETE_SQL, (eid,)
    else:
        if not current_user.project_id:
            return jsonify({'error': 'Not found'}), 404
        sql = EXPENSE_DELETE_SQL + WORKER_SCOPE
        params = (eid, current_user.id, current_user.project_id)
    _, rc = q(sql, params)
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return '', 204


@app.route('/api/expenses/clear', methods=['DELETE'])
@login_required
def expenses_clear():
    if current_user.is_admin:
        q("DELETE FROM expenses")
    elif current_user.project_id:
        q(f"DELETE FROM expenses WHERE user_id = {PH} AND project_id = {PH}",
          (current_user.id, current_user.project_id))
    return '', 204


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
