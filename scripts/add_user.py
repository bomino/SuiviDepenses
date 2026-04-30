"""Add (or replace) a user in the expense tracker.

Usage:
    python scripts/add_user.py <username> <password> [--admin]

The optional --admin flag promotes the user (or, when updating an existing
user, overrides their admin status). Without --admin, an existing user's
admin flag is left unchanged; new users are created as non-admins.

Connects to the same database the server uses:
- DATABASE_URL env var set  -> Postgres (production)
- DATABASE_URL not set      -> local expenses.db (SQLite)

On Railway, run via:
    railway run python scripts/add_user.py supervisor mySafePass --admin
"""
import os
import sys
import uuid

# Allow running from project root or scripts/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
import server


def main():
    args = [a for a in sys.argv[1:] if a != '--admin']
    make_admin = '--admin' in sys.argv[1:]

    if len(args) != 2:
        print(__doc__.strip())
        sys.exit(1)

    username = args[0].strip()
    password = args[1]

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
        if make_admin:
            server.q(
                f"UPDATE users SET password_hash = {server.PH}, is_admin = {server.PH} WHERE id = {server.PH}",
                (pw_hash, True, existing_id),
            )
            print(f"Updated password and promoted to admin: '{username}'")
        else:
            server.q(
                f"UPDATE users SET password_hash = {server.PH} WHERE id = {server.PH}",
                (pw_hash, existing_id),
            )
            print(f"Updated password for existing user '{username}'")
    else:
        server.q(
            f"INSERT INTO users (id, username, password_hash, is_admin) VALUES ({server.PH}, {server.PH}, {server.PH}, {server.PH})",
            (uuid.uuid4().hex, username, pw_hash, make_admin),
        )
        role = "admin" if make_admin else "user"
        print(f"Created {role} '{username}'")


if __name__ == '__main__':
    main()
