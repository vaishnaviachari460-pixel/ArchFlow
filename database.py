import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "archflow.db")


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _json_dump(value):
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _json_load(value, default=None):
    if default is None:
        default = []
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        try:
            # Backward compatibility with the old database that stored str(list).
            import ast
            return ast.literal_eval(value)
        except Exception:
            return default


def _columns(table):
    with get_connection() as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _add_column_if_missing(table, name, definition):
    if name not in _columns(table):
        with get_connection() as conn:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            conn.commit()


def init_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                communication TEXT NOT NULL,
                summary TEXT DEFAULT '',
                risks TEXT DEFAULT '[]',
                decisions TEXT DEFAULT '[]',
                actions TEXT DEFAULT '[]',
                deadlines TEXT DEFAULT '[]',
                project_health TEXT DEFAULT 'HEALTHY',
                priority TEXT DEFAULT 'LOW',
                health_reasons TEXT DEFAULT '[]',
                health_explanation TEXT DEFAULT '',
                changes TEXT DEFAULT '[]',
                revisions TEXT DEFAULT '[]',
                materials TEXT DEFAULT '[]',
                material_events TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    # Safe migration for databases created by earlier ArchFlow versions.
    required = {
        "summary": "TEXT DEFAULT ''",
        "risks": "TEXT DEFAULT '[]'",
        "decisions": "TEXT DEFAULT '[]'",
        "actions": "TEXT DEFAULT '[]'",
        "deadlines": "TEXT DEFAULT '[]'",
        "project_health": "TEXT DEFAULT 'HEALTHY'",
        "priority": "TEXT DEFAULT 'LOW'",
        "health_reasons": "TEXT DEFAULT '[]'",
        "health_explanation": "TEXT DEFAULT ''",
        "changes": "TEXT DEFAULT '[]'",
        "revisions": "TEXT DEFAULT '[]'",
        "materials": "TEXT DEFAULT '[]'",
        "material_events": "TEXT DEFAULT '[]'",
        "created_at": "TEXT",
    }
    for name, definition in required.items():
        _add_column_if_missing("analyses", name, definition)


def save_analysis(communication, result):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO analyses (
                communication, summary, risks, decisions, actions,
                deadlines, project_health, priority, health_reasons,
                health_explanation, changes, revisions, materials,
                material_events, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            communication,
            result.get("summary", ""),
            _json_dump(result.get("risks", [])),
            _json_dump(result.get("decisions", [])),
            _json_dump(result.get("actions", [])),
            _json_dump(result.get("deadlines", [])),
            result.get("project_health", "HEALTHY"),
            result.get("priority", "LOW"),
            _json_dump(result.get("health_reasons", [])),
            result.get("health_explanation", ""),
            _json_dump(result.get("changes", [])),
            _json_dump(result.get("revisions", [])),
            _json_dump(result.get("materials", [])),
            _json_dump(result.get("material_events", [])),
            now,
        ))
        conn.commit()
        return cursor.lastrowid


def get_history(limit=20):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, communication, summary, risks, decisions, actions,
                   deadlines, project_health, priority, health_reasons,
                   health_explanation, changes, revisions, materials,
                   material_events, created_at
            FROM analyses
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),)).fetchall()

    return [_analysis_row_to_dict(row, include_communication=True) for row in rows]


def get_previous_communications(limit=1):
    # Compare against the immediately previous analysis by default.
    # This avoids unrelated old test data contaminating project-memory results.
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT communication
            FROM analyses
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),)).fetchall()
    return [row["communication"] for row in rows]


def _analysis_row_to_dict(row, include_communication=True):
    data = {
        "id": row["id"],
        "summary": row["summary"] or "",
        "risks": _json_load(row["risks"]),
        "decisions": _json_load(row["decisions"]),
        "actions": _json_load(row["actions"]),
        "deadlines": _json_load(row["deadlines"]),
        "project_health": row["project_health"] or "HEALTHY",
        "priority": row["priority"] or "LOW",
        "health_reasons": _json_load(row["health_reasons"]),
        "health_explanation": row["health_explanation"] or "",
        "changes": _json_load(row["changes"]),
        "revisions": _json_load(row["revisions"]),
        "materials": _json_load(row["materials"]),
        "material_events": _json_load(row["material_events"]),
        "created_at": row["created_at"],
    }
    if include_communication:
        data["communication"] = row["communication"]
    return data


def get_latest_analysis_id():
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM analyses ORDER BY id DESC LIMIT 1").fetchone()
    return row["id"] if row else None


def get_latest_analysis():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, communication, summary, risks, decisions, actions,
                   deadlines, project_health, priority, health_reasons,
                   health_explanation, changes, revisions, materials,
                   material_events, created_at
            FROM analyses ORDER BY id DESC LIMIT 1
        """).fetchone()
    return _analysis_row_to_dict(row) if row else None


def init_action_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                action TEXT NOT NULL,
                owner TEXT DEFAULT 'Project Team',
                deadline TEXT DEFAULT 'Not specified',
                status TEXT DEFAULT 'PENDING',
                priority TEXT DEFAULT 'MEDIUM',
                source TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    required = {
        "analysis_id": "INTEGER",
        "owner": "TEXT DEFAULT 'Project Team'",
        "deadline": "TEXT DEFAULT 'Not specified'",
        "status": "TEXT DEFAULT 'PENDING'",
        "priority": "TEXT DEFAULT 'MEDIUM'",
        "source": "TEXT DEFAULT ''",
        "created_at": "TEXT",
    }
    for name, definition in required.items():
        _add_column_if_missing("actions", name, definition)

    with get_connection() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_analysis ON actions(analysis_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at)")
        conn.commit()


def normalize_text(text):
    return " ".join(str(text or "").strip().lower().split())


def _normalize_status(status):
    return str(status or "").strip().upper().replace("_", " ")


def save_actions(actions, analysis_id):
    saved = []
    if not actions:
        return saved

    with get_connection() as conn:
        for item in actions:
            if isinstance(item, str):
                action_text = item
                owner = "Project Team"
                deadline = "Not specified"
                priority = "MEDIUM"
                source = ""
            else:
                action_text = item.get("action", item.get("description", item.get("title", "")))
                owner = item.get("owner") or "Project Team"
                deadline = item.get("deadline") or "Not specified"
                priority = item.get("priority") or "MEDIUM"
                source = item.get("source") or ""

            action_text = str(action_text or "").strip()
            owner = str(owner or "Project Team").strip()
            deadline = str(deadline or "Not specified").strip()
            priority = str(priority or "MEDIUM").upper().strip()
            source = str(source or "").strip()
            if not action_text:
                continue

            existing = conn.execute("""
                SELECT * FROM actions
                WHERE analysis_id = ? AND lower(trim(action)) = lower(trim(?))
                  AND lower(trim(owner)) = lower(trim(?))
                LIMIT 1
            """, (analysis_id, action_text, owner)).fetchone()

            if existing:
                if deadline.lower() != "not specified":
                    conn.execute("UPDATE actions SET deadline=?, priority=?, source=? WHERE id=?", (deadline, priority, source, existing["id"]))
                row = conn.execute("SELECT * FROM actions WHERE id=?", (existing["id"],)).fetchone()
            else:
                cursor = conn.execute("""
                    INSERT INTO actions (analysis_id, action, owner, deadline, status, priority, source)
                    VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
                """, (analysis_id, action_text, owner, deadline, priority, source))
                row = conn.execute("SELECT * FROM actions WHERE id=?", (cursor.lastrowid,)).fetchone()

            saved.append(_action_row_to_dict(row))
        conn.commit()
    return saved


def _action_row_to_dict(row):
    return {
        "id": row["id"],
        "analysis_id": row["analysis_id"],
        "action": row["action"],
        "owner": row["owner"] or "Project Team",
        "deadline": row["deadline"] or "Not specified",
        "status": row["status"] or "PENDING",
        "priority": row["priority"] or "MEDIUM",
        "source": row["source"] or "",
        "created_at": row["created_at"],
    }


def get_actions(analysis_id=None):
    query = "SELECT * FROM actions"
    params = ()
    if analysis_id is not None:
        query += " WHERE analysis_id = ?"
        params = (analysis_id,)
    query += " ORDER BY id ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_action_row_to_dict(row) for row in rows]


def update_action_status(action_id, status):
    status = _normalize_status(status)
    allowed = {"PENDING", "IN PROGRESS", "COMPLETED"}
    if status not in allowed:
        raise ValueError("Invalid action status.")
    try:
        action_id = int(action_id)
    except (TypeError, ValueError):
        return False
    with get_connection() as conn:
        cursor = conn.execute("UPDATE actions SET status=? WHERE id=?", (status, action_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_actions_for_analysis(analysis_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM actions WHERE analysis_id=?", (analysis_id,))
        conn.commit()


def clear_actions():
    with get_connection() as conn:
        conn.execute("DELETE FROM actions")
        conn.commit()


init_database()
init_action_table()
