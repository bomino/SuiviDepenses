"""Add (or replace) a user in the expense tracker.

Usage:
    python scripts/add_user.py <username> <password>

Connects to the same database the server uses:
- DATABASE_URL env var set  -> Postgres (production)
- DATABASE_URL not set      -> local expenses.db (SQLite)

On Railway, run via:
    railway run python scripts/add_user.py supervisor mySafePass
"""
import os
import sys
import uuid

# Allow running from project root or scripts/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
import server


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip())
        sys.exit(1)

    username = sys.argv[1].strip()
    password = sys.argv[2]

    if not username:
        print("ERROR: username cannot be empty")
        sys.exit(1)
    if len(password) < 6:
        print("ERROR: password must be at least 6 characters")
        sys.exit(1)

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    rows, _ = server.q(
        f"SELECT id FROM users WHERE username = {server.PH}",
        (username,),
    )
    if rows:
        existing_id = rows[0]['id']
        server.q(
            f"UPDATE users SET password_hash = {server.PH} WHERE id = {server.PH}",
            (pw_hash, existing_id),
        )
        print(f"Updated password for existing user '{username}'")
    else:
        server.q(
            f"INSERT INTO users (id, username, password_hash) VALUES ({server.PH}, {server.PH}, {server.PH})",
            (uuid.uuid4().hex, username, pw_hash),
        )
        print(f"Created user '{username}'")


if __name__ == '__main__':
    main()
