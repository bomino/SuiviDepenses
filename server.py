import os
import uuid
from contextlib import contextmanager
from flask import Flask, request, jsonify, send_from_directory, abort

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
HTML_FILE = 'index.html'

ALLOWED_CATEGORIES = {'Materials', 'Labor', 'Equipment', 'Permits', 'Subcontractors', 'Transport', 'Utilities', 'Misc'}
ALLOWED_STATUSES = {'Paid', 'Pending', 'Unpaid'}
SERVABLE_FILES = {'index.html', 'manifest.json', 'sw.js'}
SERVABLE_ICON_PREFIX = 'icons/'

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

app = Flask(__name__)

if USE_POSTGRES:
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    PH = '%s'
    AMOUNT_TYPE = 'NUMERIC'
    LIST_ORDER = "ORDER BY date DESC, id DESC"
    SEED_PROJECT = "INSERT INTO project (id, name) VALUES (1, 'My Project') ON CONFLICT (id) DO NOTHING"
    UPSERT_PROJECT = f"INSERT INTO project (id, name) VALUES (1, {PH}) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name"

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
    SEED_PROJECT = "INSERT OR IGNORE INTO project (id, name) VALUES (1, 'My Project')"
    UPSERT_PROJECT = f"INSERT OR REPLACE INTO project (id, name) VALUES (1, {PH})"

    @contextmanager
    def get_conn():
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
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


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                amount {AMOUNT_TYPE} NOT NULL,
                category TEXT NOT NULL DEFAULT 'Materials',
                date TEXT NOT NULL,
                paid_by TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Paid',
                notes TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT 'My Project'
            )
        """)
        cur.execute(SEED_PROJECT)
        conn.commit()


init_db()


EXPENSE_INSERT_SQL = (
    f"INSERT INTO expenses (id, description, amount, category, date, paid_by, status, notes) "
    f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
)
EXPENSE_UPDATE_SQL = (
    f"UPDATE expenses SET description={PH}, amount={PH}, category={PH}, date={PH}, "
    f"paid_by={PH}, status={PH}, notes={PH} WHERE id={PH}"
)
EXPENSE_DELETE_SQL = f"DELETE FROM expenses WHERE id={PH}"


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


# ─── project ───
@app.route('/api/project', methods=['GET'])
def project_get():
    rows, _ = q("SELECT name FROM project WHERE id=1")
    return jsonify({'name': rows[0]['name'] if rows else 'My Project'})


@app.route('/api/project', methods=['PUT'])
def project_update():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()[:100] or 'My Project'
    q(UPSERT_PROJECT, (name,))
    return jsonify({'name': name})


# ─── expenses ───
@app.route('/api/expenses', methods=['GET'])
def expenses_list():
    rows, _ = q(f"SELECT * FROM expenses {LIST_ORDER}")
    out = []
    for r in rows:
        d = dict(r)
        if 'amount' in d and d['amount'] is not None:
            d['amount'] = float(d['amount'])
        out.append(d)
    return jsonify(out)


@app.route('/api/expenses', methods=['POST'])
def expenses_create():
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    eid = uuid.uuid4().hex
    q(EXPENSE_INSERT_SQL, (eid, fields['description'], fields['amount'], fields['category'],
                           fields['date'], fields['paid_by'], fields['status'], fields['notes']))
    return jsonify({'id': eid}), 201


@app.route('/api/expenses/<eid>', methods=['PUT'])
def expenses_update(eid):
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    _, rc = q(EXPENSE_UPDATE_SQL, (fields['description'], fields['amount'], fields['category'],
                                    fields['date'], fields['paid_by'], fields['status'], fields['notes'], eid))
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': eid})


@app.route('/api/expenses/<eid>', methods=['DELETE'])
def expenses_delete(eid):
    _, rc = q(EXPENSE_DELETE_SQL, (eid,))
    if rc == 0:
        return jsonify({'error': 'Not found'}), 404
    return '', 204


@app.route('/api/expenses/clear', methods=['DELETE'])
def expenses_clear():
    q("DELETE FROM expenses")
    return '', 204


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
