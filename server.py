import os
import uuid
import sqlite3
from flask import Flask, request, jsonify, send_from_directory, abort

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, 'expenses.db')
HTML_FILE = 'expense-tracker.html'

ALLOWED_CATEGORIES = {'Materials', 'Labor', 'Equipment', 'Permits', 'Subcontractors', 'Transport', 'Utilities', 'Misc'}
ALLOWED_STATUSES = {'Paid', 'Pending', 'Unpaid'}
SERVABLE_FILES = {'expense-tracker.html', 'manifest.json', 'sw.js'}

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL DEFAULT 'Materials',
                date TEXT NOT NULL,
                paid_by TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Paid',
                notes TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY CHECK(id=1),
                name TEXT NOT NULL DEFAULT 'My Project'
            )
        """)
        conn.execute("INSERT OR IGNORE INTO project (id,name) VALUES (1,'My Project')")

init_db()

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

# ─── frontend ───
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, HTML_FILE)

@app.route('/<path:p>')
def static_file(p):
    if p not in SERVABLE_FILES:
        abort(404)
    return send_from_directory(BASE_DIR, p)

# ─── project ───
@app.route('/api/project', methods=['GET'])
def project_get():
    with get_db() as conn:
        r = conn.execute("SELECT name FROM project WHERE id=1").fetchone()
    return jsonify({'name': r['name'] if r else 'My Project'})

@app.route('/api/project', methods=['PUT'])
def project_update():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()[:100] or 'My Project'
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO project (id,name) VALUES (1,?)", (name,))
    return jsonify({'name': name})

# ─── expenses ───
@app.route('/api/expenses', methods=['GET'])
def expenses_list():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC, rowid DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/expenses', methods=['POST'])
def expenses_create():
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    eid = uuid.uuid4().hex
    with get_db() as conn:
        conn.execute(
            "INSERT INTO expenses (id,description,amount,category,date,paid_by,status,notes) VALUES (?,?,?,?,?,?,?,?)",
            (eid, fields['description'], fields['amount'], fields['category'], fields['date'],
             fields['paid_by'], fields['status'], fields['notes'])
        )
    return jsonify({'id': eid}), 201

@app.route('/api/expenses/<eid>', methods=['PUT'])
def expenses_update(eid):
    data = request.get_json(force=True)
    fields, err = validated_expense(data)
    if err:
        return jsonify({'error': err[0]}), err[1]

    with get_db() as conn:
        cur = conn.execute(
            "UPDATE expenses SET description=?,amount=?,category=?,date=?,paid_by=?,status=?,notes=? WHERE id=?",
            (fields['description'], fields['amount'], fields['category'], fields['date'],
             fields['paid_by'], fields['status'], fields['notes'], eid)
        )
        if cur.rowcount == 0:
            return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': eid})

@app.route('/api/expenses/<eid>', methods=['DELETE'])
def expenses_delete(eid):
    with get_db() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id=?", (eid,))
        if cur.rowcount == 0:
            return jsonify({'error': 'Not found'}), 404
    return '', 204

@app.route('/api/expenses/clear', methods=['DELETE'])
def expenses_clear():
    with get_db() as conn:
        conn.execute("DELETE FROM expenses")
    return '', 204

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
