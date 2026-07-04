"""SQLite storage for project scan history."""
import json
import sqlite3
import time
from pathlib import Path


def save_scan(scan_report: dict, db_path) -> int:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                target TEXT NOT NULL,
                mode TEXT NOT NULL,
                verdict TEXT NOT NULL,
                score INTEGER NOT NULL,
                findings INTEGER NOT NULL,
                syntax_errors INTEGER NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        cur = con.execute(
            """
            INSERT INTO scans (
                created_at, target, mode, verdict, score, findings,
                syntax_errors, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(time.time()),
                scan_report["target"],
                scan_report["mode"],
                scan_report["verdict"],
                int(scan_report["score"]),
                int(scan_report["summary"]["findings"]),
                int(scan_report["summary"]["syntax_errors"]),
                json.dumps(scan_report, ensure_ascii=False),
            ),
        )
        return int(cur.lastrowid)


def list_scans(db_path, limit: int = 10) -> list[dict]:
    path = Path(db_path)
    if not path.is_file():
        return []
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT id, created_at, target, mode, verdict, score, findings, syntax_errors
            FROM scans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
