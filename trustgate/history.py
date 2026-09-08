"""SQLite storage for project scans, findings and quality history."""
import html
import json
import sqlite3
import time
from pathlib import Path


def _connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            mode TEXT NOT NULL,
            verdict TEXT NOT NULL,
            score INTEGER NOT NULL,
            raw_score INTEGER,
            findings INTEGER NOT NULL,
            syntax_errors INTEGER NOT NULL,
            report_json TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS scan_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            file TEXT NOT NULL,
            line INTEGER NOT NULL,
            detector TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            penalty INTEGER NOT NULL,
            FOREIGN KEY(scan_id) REFERENCES scan_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_scan_runs_project_id ON scan_runs(project_id);
        CREATE INDEX IF NOT EXISTS idx_scan_findings_scan_id ON scan_findings(scan_id);
        """
    )


def _project_id(con: sqlite3.Connection, target: str) -> int:
    now = int(time.time())
    name = Path(target).name or target
    con.execute(
        """
        INSERT INTO projects(target, name, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(target) DO NOTHING
        """,
        (target, name, now),
    )
    row = con.execute("SELECT id FROM projects WHERE target = ?", (target,)).fetchone()
    return int(row["id"])


def save_scan(scan_report: dict, db_path) -> int:
    with _connect(db_path) as con:
        _ensure_schema(con)
        project_id = _project_id(con, scan_report["target"])
        cur = con.execute(
            """
            INSERT INTO scan_runs (
                project_id, created_at, mode, verdict, score, raw_score,
                findings, syntax_errors, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                int(time.time()),
                scan_report["mode"],
                scan_report["verdict"],
                int(scan_report["score"]),
                int(scan_report.get("raw_score", scan_report["score"])),
                int(scan_report["summary"]["findings"]),
                int(scan_report["summary"]["syntax_errors"]),
                json.dumps(scan_report, ensure_ascii=False),
            ),
        )
        scan_id = int(cur.lastrowid)
        con.executemany(
            """
            INSERT INTO scan_findings (
                scan_id, file, line, detector, severity, message, penalty
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    scan_id,
                    item["file"],
                    int(item["line"]),
                    item["detector"],
                    item["severity"],
                    item["message"],
                    int(item["penalty"]),
                )
                for item in scan_report.get("findings", [])
            ],
        )
        return scan_id


def list_scans(db_path, limit: int = 10) -> list[dict]:
    path = Path(db_path)
    if not path.is_file():
        return []
    with _connect(path) as con:
        _ensure_schema(con)
        rows = con.execute(
            """
            SELECT
                scan_runs.id, scan_runs.created_at, projects.target,
                projects.name AS project, scan_runs.mode, scan_runs.verdict,
                scan_runs.score, scan_runs.findings, scan_runs.syntax_errors
            FROM scan_runs
            JOIN projects ON projects.id = scan_runs.project_id
            ORDER BY scan_runs.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def detector_trends(db_path, limit: int = 10) -> list[dict]:
    path = Path(db_path)
    if not path.is_file():
        return []
    with _connect(path) as con:
        _ensure_schema(con)
        rows = con.execute(
            """
            SELECT detector, severity, COUNT(*) AS count, SUM(penalty) AS penalty
            FROM scan_findings
            GROUP BY detector, severity
            ORDER BY count DESC, penalty DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_scan(db_path, scan_id: int) -> dict | None:
    path = Path(db_path)
    if not path.is_file():
        return None
    with _connect(path) as con:
        _ensure_schema(con)
        row = con.execute(
            "SELECT report_json FROM scan_runs WHERE id = ?",
            (scan_id,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row["report_json"])


def render_dashboard(db_path, title: str = "TrustGate dashboard") -> str:
    rows = list_scans(db_path, limit=50)
    trends = detector_trends(db_path, limit=12)
    latest = rows[0] if rows else None
    verdict_class = (latest or {}).get("verdict", "PASS").lower()

    scan_rows = "\n".join(
        "<tr>"
        f"<td>{row['id']}</td>"
        f"<td>{time.strftime('%Y-%m-%d %H:%M', time.localtime(row['created_at']))}</td>"
        f"<td>{html.escape(row['project'])}</td>"
        f"<td><span class='badge {row['verdict'].lower()}'>{row['verdict']}</span></td>"
        f"<td>{row['score']}</td>"
        f"<td>{row['findings']}</td>"
        f"<td>{row['syntax_errors']}</td>"
        "</tr>"
        for row in rows
    )
    trend_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(row['detector'])}</td>"
        f"<td>{html.escape(row['severity'])}</td>"
        f"<td>{row['count']}</td>"
        f"<td>{row['penalty'] or 0}</td>"
        "</tr>"
        for row in trends
    )
    empty_scans = "<tr><td colspan='7'>No scans recorded yet.</td></tr>"
    empty_trends = "<tr><td colspan='4'>No findings stored yet.</td></tr>"

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f7f4; color: #181818; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px 18px 48px; }}
    h1 {{ font-size: 32px; margin: 0 0 18px; }}
    h2 {{ font-size: 20px; margin: 28px 0 12px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .metric {{ border: 1px solid #d8d6cf; border-radius: 8px; padding: 14px; background: white; }}
    .label {{ color: #666; font-size: 13px; }}
    .value {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8d6cf; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #ece9e1; text-align: left; font-size: 14px; }}
    th {{ background: #efeee8; }}
    .badge {{ border-radius: 999px; padding: 3px 8px; font-weight: 700; font-size: 12px; }}
    .pass {{ background: #d8f3dc; color: #1b5e20; }}
    .review {{ background: #fff3bf; color: #805b00; }}
    .block {{ background: #ffd6d6; color: #8b1a1a; }}
    @media (max-width: 760px) {{ .summary {{ grid-template-columns: 1fr 1fr; }} th, td {{ font-size: 12px; padding: 8px; }} }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(title)}</h1>
  <section class="summary">
    <div class="metric"><div class="label">Latest verdict</div><div class="value {verdict_class}">{html.escape((latest or {}).get("verdict", "-"))}</div></div>
    <div class="metric"><div class="label">Latest score</div><div class="value">{html.escape(str((latest or {}).get("score", "-")))}</div></div>
    <div class="metric"><div class="label">Total scans</div><div class="value">{len(rows)}</div></div>
    <div class="metric"><div class="label">Findings in latest scan</div><div class="value">{html.escape(str((latest or {}).get("findings", "-")))}</div></div>
  </section>

  <h2>Scan history</h2>
  <table>
    <thead><tr><th>ID</th><th>Time</th><th>Project</th><th>Verdict</th><th>Score</th><th>Findings</th><th>Syntax</th></tr></thead>
    <tbody>{scan_rows or empty_scans}</tbody>
  </table>

  <h2>Quality trends by detector</h2>
  <table>
    <thead><tr><th>Detector</th><th>Severity</th><th>Count</th><th>Penalty</th></tr></thead>
    <tbody>{trend_rows or empty_trends}</tbody>
  </table>
</main>
</body>
</html>
"""
