import json
from pathlib import Path
from typing import Union
from ..models import EvaluationSummary


class HTMLReporter:
    """Generates a self-contained, interactive HTML evaluation dashboard."""

    def generate(self, summary: EvaluationSummary, output_path: Union[str, Path]) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._render_template(summary)
        with open(target, "w", encoding="utf-8") as f:
            f.write(html_content)

        return target

    def _render_template(self, summary: EvaluationSummary) -> str:
        # Category breakdown cards
        cat_cards = ""
        for cat, stats in summary.results_by_category.items():
            tot = stats["total"]
            passed = stats["passed"]
            rate = (passed / tot * 100) if tot > 0 else 0
            badge_class = "badge-success" if rate >= 80 else ("badge-warning" if rate >= 50 else "badge-danger")
            cat_cards += f"""
            <div class="cat-card">
                <div class="cat-name">{cat.replace('_', ' ').title()}</div>
                <div class="cat-stats">
                    <span>{passed}/{tot} Passed</span>
                    <span class="badge {badge_class}">{rate:.1f}%</span>
                </div>
            </div>
            """

        # Test case detail cards
        tc_cards = ""
        for ev in summary.evaluations:
            tc = ev.test_case
            resp = ev.agent_response
            status_cls = "passed" if ev.overall_passed else "failed"
            badge_status = '<span class="badge badge-success">PASSED</span>' if ev.overall_passed else '<span class="badge badge-danger">FAILED</span>'
            review_badge = '<span class="badge badge-warning">REVIEW REQUIRED</span>' if ev.requires_human_review else ''

            # Checks table rows
            checks_rows = ""
            for ch in ev.checks:
                chk_badge = '<span class="status-pill pill-pass">PASS</span>' if ch.passed else '<span class="status-pill pill-fail">FAIL</span>'
                checks_rows += f"""
                <tr>
                    <td><code>{ch.check_name}</code></td>
                    <td><small>{ch.evaluator_type.value}</small></td>
                    <td>{chk_badge}</td>
                    <td><strong>{ch.score:.2f}</strong></td>
                    <td>{ch.reason}</td>
                </tr>
                """

            # Failures list
            failures_html = ""
            if ev.failure_reasons:
                failures_html = '<div class="failure-box"><h4>Failure Reasons & Diagnostic Evidence</h4><ul>'
                for fr in ev.failure_reasons:
                    failures_html += f"<li>{fr}</li>"
                failures_html += '</ul></div>'

            # Improvements list
            improvements_html = ""
            if ev.suggested_improvements:
                improvements_html = '<div class="improvements-box"><h4>Recommended Improvements</h4><ul>'
                for imp in ev.suggested_improvements:
                    improvements_html += f"<li>{imp}</li>"
                improvements_html += '</ul></div>'

            # Tools invoked
            tools_str = "None"
            if resp.tool_calls:
                tools_str = ", ".join(f"<code>{t.tool_name}({t.args}) -> {t.status}</code>" for t in resp.tool_calls)

            structured_json = json.dumps(resp.structured_output, indent=2)

            tc_cards += f"""
            <div class="test-item {status_cls} {'needs-review' if ev.requires_human_review else ''}" data-status="{status_cls}" data-review="{str(ev.requires_human_review).lower()}">
                <div class="test-header" onclick="toggleDetails('{tc.id}')">
                    <div class="test-title-col">
                        <span class="test-id">{tc.id}</span>
                        <strong>{tc.title}</strong>
                        <span class="test-cat">({tc.category.value})</span>
                    </div>
                    <div class="test-badges">
                        {review_badge}
                        {badge_status}
                        <span class="chevron" id="chevron-{tc.id}">▼</span>
                    </div>
                </div>
                <div class="test-details" id="details-{tc.id}">
                    <div class="detail-grid">
                        <div class="detail-block">
                            <h5>Source Input</h5>
                            <pre class="code-box">{tc.input_text}</pre>
                            <h5>Test Rationale</h5>
                            <p class="text-muted">{tc.rationale}</p>
                        </div>
                        <div class="detail-block">
                            <h5>Agent Response Output</h5>
                            <p><strong>Natural Text:</strong> "{resp.raw_text}"</p>
                            <p><strong>Status:</strong> <code>{resp.status}</code> | <strong>Reported Confidence:</strong> <code>{resp.confidence:.2f}</code></p>
                            <p><strong>Tools Called:</strong> {tools_str}</p>
                            <h5>Structured Output JSON</h5>
                            <pre class="code-box json-box">{structured_json}</pre>
                        </div>
                    </div>

                    {failures_html}
                    {improvements_html}

                    <div class="checks-wrapper">
                        <h5>Evaluation Checks Detail</h5>
                        <table class="checks-table">
                            <thead>
                                <tr>
                                    <th>Check Name</th>
                                    <th>Evaluator Layer</th>
                                    <th>Result</th>
                                    <th>Score</th>
                                    <th>Evaluation Reason</th>
                                </tr>
                            </thead>
                            <tbody>
                                {checks_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Quality & Evaluation Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: var(--font-family);
            line-height: 1.5;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            margin-bottom: 25px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}
        h1 {{ font-size: 2rem; color: var(--primary); }}
        .header-meta {{ color: var(--text-muted); font-size: 0.9rem; margin-top: 5px; }}

        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .kpi-card {{
            background: var(--surface);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .kpi-val {{ font-size: 2rem; font-weight: bold; }}
        .kpi-val.green {{ color: var(--success); }}
        .kpi-val.red {{ color: var(--danger); }}
        .kpi-val.yellow {{ color: var(--warning); }}
        .kpi-val.blue {{ color: var(--primary); }}
        .kpi-label {{ color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; margin-top: 4px; }}

        /* Category Section */
        .cat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 12px;
            margin-bottom: 25px;
        }}
        .cat-card {{
            background: var(--surface);
            padding: 12px 16px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }}
        .cat-name {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; }}
        .cat-stats {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: var(--text-muted); }}

        /* Filter Controls */
        .filters {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .filter-btn:hover, .filter-btn.active {{
            background: var(--primary);
            color: #0f172a;
            border-color: var(--primary);
        }}

        /* Test Case Items */
        .test-item {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
            transition: border-color 0.2s;
        }}
        .test-item.failed {{ border-left: 5px solid var(--danger); }}
        .test-item.passed {{ border-left: 5px solid var(--success); }}
        .test-item.needs-review {{ border-right: 5px solid var(--warning); }}

        .test-header {{
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
        }}
        .test-header:hover {{ background: var(--surface-hover); }}
        .test-id {{ font-family: monospace; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; margin-right: 8px; font-size: 0.85rem; }}
        .test-cat {{ color: var(--text-muted); font-size: 0.85rem; margin-left: 6px; }}
        .test-badges {{ display: flex; gap: 8px; align-items: center; }}
        .chevron {{ font-size: 0.75rem; margin-left: 8px; transition: transform 0.2s; }}
        .chevron.open {{ transform: rotate(180deg); }}

        .test-details {{
            display: none;
            padding: 18px;
            border-top: 1px solid var(--border);
            background: rgba(15, 23, 42, 0.4);
        }}
        .test-details.open {{ display: block; }}

        .detail-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 15px;
        }}
        @media (max-width: 768px) {{
            .detail-grid {{ grid-template-columns: 1fr; }}
        }}

        .code-box {{
            background: #090d16;
            padding: 10px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.85rem;
            margin-top: 4px;
            white-space: pre-wrap;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .json-box {{ max-height: 180px; overflow-y: auto; }}

        .failure-box {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--danger);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .failure-box h4 {{ color: var(--danger); margin-bottom: 6px; }}
        .failure-box li {{ margin-left: 20px; color: #fca5a5; font-size: 0.9rem; }}

        .improvements-box {{
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid var(--success);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .improvements-box h4 {{ color: var(--success); margin-bottom: 6px; }}
        .improvements-box li {{ margin-left: 20px; color: #86efac; font-size: 0.9rem; }}

        .checks-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 8px;
        }}
        .checks-table th, .checks-table td {{
            padding: 8px 10px;
            border: 1px solid var(--border);
            text-align: left;
        }}
        .checks-table th {{ background: rgba(255,255,255,0.05); }}

        /* Badges & Pills */
        .badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }}
        .badge-success {{ background: rgba(34, 197, 94, 0.2); color: var(--success); }}
        .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
        .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}

        .status-pill {{
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7rem;
            font-weight: bold;
        }}
        .pill-pass {{ background: var(--success); color: #0f172a; }}
        .pill-fail {{ background: var(--danger); color: #fff; }}

        /* Limitations Box */
        .limitations-section {{
            margin-top: 40px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
        }}
        .limitations-section h3 {{ color: var(--warning); margin-bottom: 10px; }}
        .limitations-section ul {{ margin-left: 20px; color: var(--text-muted); font-size: 0.9rem; }}
        .limitations-section li {{ margin-bottom: 6px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Agent Quality & Evaluation Assistant</h1>
            <div class="header-meta">
                Evaluation Run: {summary.timestamp} | Mode: <strong>{summary.eval_mode.upper()}</strong> | Engine: <strong>Deterministic-First Multi-Tier</strong>
            </div>
        </header>

        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-val blue">{summary.total_tests}</div>
                <div class="kpi-label">Total Test Cases</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val green">{summary.passed_tests}</div>
                <div class="kpi-label">Passed Tests</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val red">{summary.failed_tests}</div>
                <div class="kpi-label">Failed / Regressions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val yellow">{summary.review_needed}</div>
                <div class="kpi-label">Human Review Flagged</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-val blue">{summary.pass_rate_percentage:.1f}%</div>
                <div class="kpi-label">Overall Pass Rate</div>
            </div>
        </div>

        <!-- Category Breakdown -->
        <h3 style="margin-bottom: 12px;">7 Required Test Categories</h3>
        <div class="cat-grid">
            {cat_cards}
        </div>

        <!-- Filter Controls -->
        <div class="filters">
            <button class="filter-btn active" onclick="filterTests('all')">All Tests ({summary.total_tests})</button>
            <button class="filter-btn" onclick="filterTests('passed')">Passed Only ({summary.passed_tests})</button>
            <button class="filter-btn" onclick="filterTests('failed')">Failed Only ({summary.failed_tests})</button>
            <button class="filter-btn" onclick="filterTests('review')">Review Flagged ({summary.review_needed})</button>
        </div>

        <!-- Test Case List -->
        <div id="tests-container">
            {tc_cards}
        </div>

        <!-- Limitations of Model-Based Evaluation -->
        <div class="limitations-section">
            <h3>Architectural Safeguards & Limitations of Model-Based Evaluation</h3>
            <p style="margin-bottom: 10px; font-size: 0.9rem; color: var(--text-muted);">
                In accordance with core requirements, an AI judge is <strong>never treated as unquestionable truth</strong>. Deterministic checks take absolute precedence:
            </p>
            <ul>
                <li><strong>No Overturn of Deterministic Rules:</strong> An AI judge cannot pass an agent that fails JSON Schema validation, tool selection contracts, or grounding bounds.</li>
                <li><strong>Mitigation of Verbosity Bias:</strong> LLM judges systematically favor longer, verbose responses regardless of actual factual fidelity. Deterministic token ratio bounds enforce conciseness.</li>
                <li><strong>Position & Self-Preference Drift:</strong> Model judges exhibit self-preference towards outputs resembling their own training data. Calibrated confidence thresholds force human escalation when scores fall into uncertainty zones (0.65 - 0.75).</li>
                <li><strong>Grounding over Fluency:</strong> Beautifully phrased hallucinations (such as assigning Mika to cost estimates when she merely asked for info) are caught by deterministic entity-commitment intersection, not left to model subjectivity.</li>
            </ul>
        </div>
    </div>

    <script>
        function toggleDetails(id) {{
            const el = document.getElementById('details-' + id);
            const ch = document.getElementById('chevron-' + id);
            if (el.classList.contains('open')) {{
                el.classList.remove('open');
                ch.classList.remove('open');
            }} else {{
                el.classList.add('open');
                ch.classList.add('open');
            }}
        }}

        function filterTests(type) {{
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            const items = document.querySelectorAll('.test-item');
            items.forEach(item => {{
                if (type === 'all') {{
                    item.style.display = 'block';
                }} else if (type === 'passed') {{
                    item.style.display = item.dataset.status === 'passed' ? 'block' : 'none';
                }} else if (type === 'failed') {{
                    item.style.display = item.dataset.status === 'failed' ? 'block' : 'none';
                }} else if (type === 'review') {{
                    item.style.display = item.dataset.review === 'true' ? 'block' : 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
        return html
