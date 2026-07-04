import json
from html import escape

REPORT_VERSION = "1.0"


def build(target, raw_score, score, verdict, partial, findings, dynamic, mutation, timing_ms):
    return {
        "version": REPORT_VERSION,
        "target": str(target),
        "score": score,
        "raw_score": raw_score,
        "verdict": verdict,
        "partial": partial,
        "layers": {
            "static": {"ran": True, "findings": [f.to_dict() for f in findings]},
            "dynamic": dynamic or {"ran": False, "reason": "disabled"},
            "mutation": mutation or {"ran": False, "reason": "disabled"},
        },
        "timing_ms": timing_ms,
    }


def to_markdown(report: dict) -> str:
    lines = [
        f"## TrustGate: **{report['verdict']}** (score {report['score']}/100)",
        "",
        f"Target: `{report['target']}`" + ("  ·  *partial analysis*" if report["partial"] else ""),
        "",
    ]
    findings = report["layers"]["static"]["findings"]
    if findings:
        lines.append("| line | detector | severity | message | -pts |")
        lines.append("|------|----------|----------|---------|------|")
        top = sorted(findings, key=lambda f: -f["penalty"])[:5]
        for f in top:
            lines.append(f"| {f['line']} | {f['detector']} | {f['severity']} "
                         f"| {f['message']} | {f['penalty']} |")
        if len(findings) > 5:
            lines.append(f"\n…and {len(findings) - 5} more findings.")
    else:
        lines.append("No static findings.")

    dyn = report["layers"]["dynamic"]
    if dyn.get("ran"):
        lines.append(f"\nTests: {dyn['tests_total'] - dyn['tests_failed']}/{dyn['tests_total']} passed"
                     + (", **timeout**" if dyn.get("timeout") else ""))
    mut = report["layers"]["mutation"]
    if mut.get("ran"):
        lines.append(f"Mutation score: {mut['mutation_score']:.2f} "
                     f"({mut['mutants_killed']}/{mut['mutants_total']} killed)")
    return "\n".join(lines)


def _layer_status(layer: dict) -> str:
    if layer.get("ran"):
        return "ran"
    return layer.get("reason", "disabled")


def to_html(report: dict) -> str:
    """Render a self-contained HTML report for demos and portfolio reviews."""
    findings = report["layers"]["static"]["findings"]
    show_file = any("file" in f for f in findings)
    rows = []
    for f in sorted(findings, key=lambda item: (-item["penalty"], item["line"])):
        file_cell = f"<td>{escape(f.get('file', ''))}</td>" if show_file else ""
        rows.append(
            "<tr>"
            f"{file_cell}"
            f"<td>{f['line']}</td>"
            f"<td>{escape(f['detector'])}</td>"
            f"<td><span class='sev sev-{escape(f['severity'])}'>{escape(f['severity'])}</span></td>"
            f"<td>{escape(f['message'])}</td>"
            f"<td class='pts'>{f['penalty']}</td>"
            "</tr>"
        )
    column_count = 6 if show_file else 5
    findings_html = "\n".join(rows) if rows else (
        f"<tr><td colspan='{column_count}' class='empty'>No static findings.</td></tr>"
    )
    file_header = "<th>File</th>" if show_file else ""

    dyn = report["layers"]["dynamic"]
    mut = report["layers"]["mutation"]
    dyn_text = _layer_status(dyn)
    if dyn.get("ran"):
        passed = dyn.get("tests_total", 0) - dyn.get("tests_failed", 0)
        dyn_text = f"{passed}/{dyn.get('tests_total', 0)} tests passed"
        if dyn.get("timeout"):
            dyn_text += ", timeout"
        if dyn.get("build_error"):
            dyn_text += ", build error"

    mut_text = _layer_status(mut)
    if mut.get("ran"):
        mut_text = (
            f"{mut.get('mutation_score', 0.0):.2f} "
            f"({mut.get('mutants_killed', 0)}/{mut.get('mutants_total', 0)} killed)"
        )

    score = int(report["score"])
    verdict = escape(report["verdict"])
    partial = "Partial analysis" if report["partial"] else "Full analysis"
    target = escape(report["target"])
    timing = escape(json.dumps(report.get("timing_ms", {}), ensure_ascii=False))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TrustGate report - {verdict}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #5e6b78;
      --line: #d8dee6;
      --panel: #f7f9fb;
      --pass: #0b7a3b;
      --review: #9a6500;
      --block: #b42318;
    }}
    body {{
      margin: 0;
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #fff;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .meta, .small {{
      color: var(--muted);
    }}
    .score {{
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 16px;
      align-items: center;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      margin: 18px 0;
    }}
    .number {{
      font-size: 44px;
      font-weight: 700;
    }}
    .bar {{
      height: 16px;
      background: #e8edf2;
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid var(--line);
    }}
    .fill {{
      height: 100%;
      width: {score}%;
      background: var(--{report['verdict'].lower()});
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--{report['verdict'].lower()});
      color: white;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fff;
    }}
    .label {{
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: .06em;
    }}
    .value {{
      margin-top: 6px;
      font-weight: 650;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
    }}
    .pts {{
      text-align: right;
      font-weight: 700;
    }}
    .sev {{
      font-weight: 700;
    }}
    .sev-critical {{ color: var(--block); }}
    .sev-major {{ color: var(--review); }}
    .sev-minor {{ color: var(--muted); }}
    .empty {{
      color: var(--muted);
      text-align: center;
    }}
    pre {{
      white-space: pre-wrap;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }}
    @media (max-width: 720px) {{
      .score, .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>TrustGate <span class="pill">{verdict}</span></h1>
    <div class="meta">Target: <code>{target}</code> · {partial}</div>
  </header>
  <section class="score">
    <div>
      <div class="label">Trust score</div>
      <div class="number">{score}/100</div>
    </div>
    <div class="bar" aria-label="Trust score"><div class="fill"></div></div>
  </section>
  <section class="grid">
    <div class="box"><div class="label">Static layer</div><div class="value">{len(findings)} findings</div></div>
    <div class="box"><div class="label">Dynamic layer</div><div class="value">{escape(dyn_text)}</div></div>
    <div class="box"><div class="label">Mutation layer</div><div class="value">{escape(mut_text)}</div></div>
  </section>
  <h2>Findings</h2>
  <table>
    <thead>
      <tr>{file_header}<th>Line</th><th>Detector</th><th>Severity</th><th>Message</th><th>-pts</th></tr>
    </thead>
    <tbody>
      {findings_html}
    </tbody>
  </table>
  <h2>Timing</h2>
  <pre>{timing}</pre>
</main>
</body>
</html>
"""


def dump(report: dict, path) -> None:
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def dump_html(report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_html(report))
