#!/usr/bin/env python3
"""Implementation Understanding Quiz (Plan #296).

Generates quizzes on changed files to verify user comprehension of:
- What the code does
- Tradeoffs made in implementation
- Whether implementation matches intentions

Usage:
    python scripts/implementation_quiz.py [--branch BRANCH] [--base BASE]
    python scripts/implementation_quiz.py --html  # Opens quiz in browser
    python scripts/implementation_quiz.py --file FILE [FILE ...]
"""

import argparse
import html
import json
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def get_config() -> dict[str, Any]:
    """Load quiz configuration from meta-process.yaml."""
    config_path = Path("meta-process.yaml")
    if not config_path.exists():
        return {"quiz": {"integration": "manual", "min_lines_changed": 0}}

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    return config.get("quiz", {"integration": "manual", "min_lines_changed": 0})


def get_changed_files(branch: str = "HEAD", base: str = "main") -> list[dict[str, Any]]:
    """Get list of changed files with stats."""
    # Get list of changed files with line counts
    result = subprocess.run(
        ["git", "diff", "--numstat", f"{base}...{branch}"],
        capture_output=True,
        text=True,
    )

    files = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0] != "-" else 0
            removed = int(parts[1]) if parts[1] != "-" else 0
            filepath = parts[2]
            files.append({
                "path": filepath,
                "added": added,
                "removed": removed,
                "total_changed": added + removed,
            })

    return sorted(files, key=lambda x: x["total_changed"], reverse=True)


def get_file_diff(filepath: str, branch: str = "HEAD", base: str = "main") -> str:
    """Get the diff for a specific file."""
    result = subprocess.run(
        ["git", "diff", f"{base}...{branch}", "--", filepath],
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_file_content(filepath: str, branch: str = "HEAD") -> str:
    """Get file content at a specific branch."""
    result = subprocess.run(
        ["git", "show", f"{branch}:{filepath}"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def render_changes_chart(files: list[dict[str, Any]]) -> str:
    """Render ASCII chart of changes by file."""
    if not files:
        return "No files changed."

    max_lines = max(f["total_changed"] for f in files)
    max_path_len = min(40, max(len(f["path"]) for f in files))
    chart_width = 40

    lines = [
        "┌" + "─" * (max_path_len + 2) + "┬" + "─" * (chart_width + 2) + "┬" + "─" * 8 + "┐",
        "│ " + "File".ljust(max_path_len) + " │ " + "Changes".center(chart_width) + " │ " + "Lines".center(6) + " │",
        "├" + "─" * (max_path_len + 2) + "┼" + "─" * (chart_width + 2) + "┼" + "─" * 8 + "┤",
    ]

    for f in files[:15]:  # Limit to top 15 files
        path = f["path"]
        if len(path) > max_path_len:
            path = "..." + path[-(max_path_len - 3):]

        bar_len = int((f["total_changed"] / max_lines) * chart_width) if max_lines > 0 else 0
        bar_len = max(1, bar_len)  # At least 1 char

        # Green for added, red for removed
        added_ratio = f["added"] / f["total_changed"] if f["total_changed"] > 0 else 0.5
        green_len = int(bar_len * added_ratio)
        red_len = bar_len - green_len

        bar = "+" * green_len + "-" * red_len
        bar = bar.ljust(chart_width)

        lines.append(f"│ {path.ljust(max_path_len)} │ {bar} │ {str(f['total_changed']).center(6)} │")

    if len(files) > 15:
        lines.append(f"│ {'... and ' + str(len(files) - 15) + ' more files'.ljust(max_path_len)} │ {' ' * chart_width} │ {''.center(6)} │")

    lines.append("└" + "─" * (max_path_len + 2) + "┴" + "─" * (chart_width + 2) + "┴" + "─" * 8 + "┘")

    return "\n".join(lines)


def render_file_structure_chart(files: list[dict[str, Any]]) -> str:
    """Render ASCII tree of changed files by directory."""
    from collections import defaultdict

    # Group by directory
    by_dir: dict[str, list[str]] = defaultdict(list)
    for f in files:
        path = Path(f["path"])
        dir_path = str(path.parent) if path.parent != Path(".") else "(root)"
        by_dir[dir_path].append(path.name)

    lines = ["Changed file structure:", ""]

    dirs = sorted(by_dir.keys())
    for i, dir_path in enumerate(dirs):
        is_last_dir = i == len(dirs) - 1
        prefix = "└── " if is_last_dir else "├── "
        lines.append(f"{prefix}{dir_path}/")

        filenames = sorted(by_dir[dir_path])
        for j, filename in enumerate(filenames):
            is_last_file = j == len(filenames) - 1
            dir_prefix = "    " if is_last_dir else "│   "
            file_prefix = "└── " if is_last_file else "├── "
            lines.append(f"{dir_prefix}{file_prefix}{filename}")

    return "\n".join(lines)


def generate_quiz_prompt(filepath: str, diff: str, content: str) -> str:
    """Generate the prompt for quiz generation."""
    return f"""Analyze this code change and generate a comprehension quiz.

FILE: {filepath}

DIFF:
```
{diff[:3000]}  # Truncate long diffs
```

CURRENT CONTENT (after change):
```
{content[:5000]}  # Truncate long files
```

Generate a quiz with 3-5 questions that verify the user:
1. Understands what this code DOES (comprehension)
2. Understands WHY it was done this way (tradeoffs)
3. Confirms this matches their INTENTION (alignment)

For each question:
- Use multiple choice (A/B/C/D) where possible
- Include an "explain" option for open-ended understanding
- Note the correct answer

Use ASCII diagrams where helpful to illustrate:
- Data flow
- State transitions
- Architecture relationships
- Before/after comparisons

Format as YAML:
```yaml
file: {filepath}
summary: |
  Brief description of what changed
diagram: |
  ASCII diagram if helpful (optional)
questions:
  - type: multiple_choice
    category: comprehension|tradeoff|alignment
    question: "What does X do?"
    options:
      a: "Option A"
      b: "Option B"
      c: "Option C"
      d: "Option D"
    correct: "b"
    explanation: "Why B is correct"
  - type: open_ended
    category: comprehension|tradeoff|alignment
    question: "Explain why..."
    key_points:
      - "Point 1"
      - "Point 2"
```
"""


def print_quiz_header(files: list[dict[str, Any]]) -> None:
    """Print quiz header with overview."""
    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)

    print("\n" + "=" * 70)
    print("  IMPLEMENTATION UNDERSTANDING QUIZ")
    print("=" * 70)
    print()
    print(f"  Files changed: {len(files)}")
    print(f"  Lines added:   +{total_added}")
    print(f"  Lines removed: -{total_removed}")
    print()
    print(render_changes_chart(files))
    print()
    print(render_file_structure_chart(files))
    print()
    print("-" * 70)
    print("  This quiz verifies your understanding of the changes.")
    print("  Answer honestly - misalignment is valuable feedback!")
    print("-" * 70)
    print()


def run_interactive_quiz(files: list[dict[str, Any]], branch: str, base: str) -> dict[str, Any]:
    """Run interactive quiz on changed files."""
    print_quiz_header(files)

    results: dict[str, Any] = {
        "files_quizzed": [],
        "total_questions": 0,
        "understood": 0,
        "misaligned": 0,
        "needs_discussion": [],
    }

    for f in files:
        filepath = f["path"]

        # Skip non-code files
        if not any(filepath.endswith(ext) for ext in [".py", ".yaml", ".yml", ".md", ".json"]):
            continue

        print(f"\n{'=' * 70}")
        print(f"  FILE: {filepath}")
        print(f"  Changes: +{f['added']} / -{f['removed']}")
        print("=" * 70)

        diff = get_file_diff(filepath, branch, base)

        # Show diff summary
        print("\nDiff preview:")
        print("-" * 40)
        diff_lines = diff.split("\n")[:30]
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"  \033[32m{line}\033[0m")  # Green
            elif line.startswith("-") and not line.startswith("---"):
                print(f"  \033[31m{line}\033[0m")  # Red
            else:
                print(f"  {line}")
        if len(diff.split("\n")) > 30:
            print(f"  ... ({len(diff.split(chr(10))) - 30} more lines)")
        print("-" * 40)

        # Ask comprehension questions
        print("\n  COMPREHENSION CHECK:")
        print()

        q1 = input("  1. In your own words, what does this change DO?\n     > ")
        results["total_questions"] += 1

        q2 = input("\n  2. What TRADEOFF or design decision was made here?\n     > ")
        results["total_questions"] += 1

        q3 = input("\n  3. Does this match your INTENTION? (yes/no/partially)\n     > ").lower().strip()
        results["total_questions"] += 1

        if q3 in ["yes", "y"]:
            results["understood"] += 1
        elif q3 in ["no", "n"]:
            results["misaligned"] += 1
            results["needs_discussion"].append({
                "file": filepath,
                "reason": input("     What's different from your intention?\n     > "),
            })
        else:
            concern = input("     What aspect is unclear or partially misaligned?\n     > ")
            if concern:
                results["needs_discussion"].append({
                    "file": filepath,
                    "reason": concern,
                })

        results["files_quizzed"].append(filepath)

        print()
        continue_quiz = input("  Continue to next file? (yes/no) [yes]: ").lower().strip()
        if continue_quiz in ["no", "n"]:
            break

    return results


def print_quiz_results(results: dict[str, Any]) -> None:
    """Print quiz results summary."""
    print("\n" + "=" * 70)
    print("  QUIZ RESULTS")
    print("=" * 70)

    files_count = len(results["files_quizzed"])

    # ASCII result chart
    if files_count > 0:
        understood_pct = (results["understood"] / files_count) * 100
        misaligned_pct = (results["misaligned"] / files_count) * 100
        partial_pct = 100 - understood_pct - misaligned_pct

        bar_width = 40
        understood_bar = int(understood_pct / 100 * bar_width)
        misaligned_bar = int(misaligned_pct / 100 * bar_width)
        partial_bar = bar_width - understood_bar - misaligned_bar

        print()
        print("  Alignment:")
        print(f"  [{'█' * understood_bar}{'░' * partial_bar}{'▒' * misaligned_bar}]")
        print(f"   █ Aligned: {results['understood']}/{files_count} ({understood_pct:.0f}%)")
        print(f"   ░ Partial: {files_count - results['understood'] - results['misaligned']}/{files_count}")
        print(f"   ▒ Misaligned: {results['misaligned']}/{files_count} ({misaligned_pct:.0f}%)")

    print()
    print(f"  Files quizzed: {files_count}")
    print(f"  Total questions: {results['total_questions']}")

    if results["needs_discussion"]:
        print()
        print("  ⚠ NEEDS DISCUSSION:")
        print("  " + "-" * 40)
        for item in results["needs_discussion"]:
            print(f"  • {item['file']}")
            print(f"    {item['reason']}")
        print("  " + "-" * 40)

    print()
    if results["misaligned"] > 0:
        print("  RECOMMENDATION: Review misaligned files before merge.")
    elif results["needs_discussion"]:
        print("  RECOMMENDATION: Discuss partial alignments before merge.")
    else:
        print("  ✓ All changes appear to match your intentions.")

    print("=" * 70)


def generate_html_quiz(files: list[dict[str, Any]], branch: str, base: str) -> str:
    """Generate HTML quiz page."""
    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)

    # Build file cards with diffs
    file_cards = []
    for i, f in enumerate(files):
        filepath = f["path"]
        # Skip non-code files
        if not any(filepath.endswith(ext) for ext in [".py", ".yaml", ".yml", ".md", ".json", ".js", ".ts", ".tsx"]):
            continue

        diff = get_file_diff(filepath, branch, base)
        diff_html = html.escape(diff[:5000])  # Truncate long diffs

        # Color the diff lines
        diff_lines = []
        for line in diff_html.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                diff_lines.append(f'<span class="diff-add">{line}</span>')
            elif line.startswith("-") and not line.startswith("---"):
                diff_lines.append(f'<span class="diff-remove">{line}</span>')
            elif line.startswith("@@"):
                diff_lines.append(f'<span class="diff-info">{line}</span>')
            else:
                diff_lines.append(line)

        colored_diff = "\n".join(diff_lines)

        file_cards.append(f'''
        <div class="file-card" id="file-{i}">
            <div class="file-header">
                <span class="file-path">{html.escape(filepath)}</span>
                <span class="file-stats">
                    <span class="added">+{f["added"]}</span>
                    <span class="removed">-{f["removed"]}</span>
                </span>
            </div>
            <details class="diff-section">
                <summary>View Diff</summary>
                <pre class="diff">{colored_diff}</pre>
            </details>
            <div class="questions">
                <div class="question">
                    <label>1. In your own words, what does this change DO?</label>
                    <textarea name="comprehension-{i}" rows="3" placeholder="Describe what this code does..."></textarea>
                </div>
                <div class="question">
                    <label>2. What TRADEOFF or design decision was made here?</label>
                    <textarea name="tradeoff-{i}" rows="3" placeholder="Identify any tradeoffs or alternatives considered..."></textarea>
                </div>
                <div class="question">
                    <label>3. Does this match your INTENTION?</label>
                    <div class="alignment-options">
                        <label><input type="radio" name="alignment-{i}" value="yes"> Yes, exactly what I wanted</label>
                        <label><input type="radio" name="alignment-{i}" value="partial"> Partially - some concerns</label>
                        <label><input type="radio" name="alignment-{i}" value="no"> No - this differs from my intention</label>
                    </div>
                    <textarea name="alignment-note-{i}" rows="2" placeholder="If partial or no, explain what's different..."></textarea>
                </div>
            </div>
        </div>
        ''')

    # Calculate bar widths for chart
    max_lines = max(f["total_changed"] for f in files) if files else 1
    file_bars = []
    for f in files[:10]:
        width = int((f["total_changed"] / max_lines) * 100)
        added_pct = int((f["added"] / f["total_changed"]) * 100) if f["total_changed"] > 0 else 50
        file_bars.append(f'''
            <div class="bar-row">
                <span class="bar-label" title="{html.escape(f["path"])}">{html.escape(Path(f["path"]).name)}</span>
                <div class="bar-container">
                    <div class="bar" style="width: {width}%">
                        <div class="bar-added" style="width: {added_pct}%"></div>
                        <div class="bar-removed" style="width: {100-added_pct}%"></div>
                    </div>
                </div>
                <span class="bar-value">{f["total_changed"]}</span>
            </div>
        ''')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Implementation Understanding Quiz</title>
    <style>
        :root {{
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --accent: #0f3460;
            --text: #e6e6e6;
            --text-dim: #888;
            --green: #4ade80;
            --red: #f87171;
            --yellow: #fbbf24;
            --blue: #60a5fa;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 20px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: var(--text-dim); }}
        .stat-card.files .stat-value {{ color: var(--blue); }}
        .stat-card.added .stat-value {{ color: var(--green); }}
        .stat-card.removed .stat-value {{ color: var(--red); }}

        .chart {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .chart h2 {{ margin-top: 0; font-size: 1.2em; }}
        .bar-row {{
            display: flex;
            align-items: center;
            margin: 8px 0;
        }}
        .bar-label {{
            width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 0.9em;
            color: var(--text-dim);
        }}
        .bar-container {{
            flex: 1;
            height: 20px;
            background: var(--accent);
            border-radius: 4px;
            overflow: hidden;
            margin: 0 10px;
        }}
        .bar {{
            height: 100%;
            display: flex;
        }}
        .bar-added {{ background: var(--green); }}
        .bar-removed {{ background: var(--red); }}
        .bar-value {{
            width: 50px;
            text-align: right;
            font-size: 0.9em;
        }}

        .file-card {{
            background: var(--card-bg);
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .file-header {{
            background: var(--accent);
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .file-path {{ font-family: monospace; }}
        .file-stats .added {{ color: var(--green); margin-right: 10px; }}
        .file-stats .removed {{ color: var(--red); }}

        .diff-section {{ padding: 0 20px; }}
        .diff-section summary {{
            cursor: pointer;
            padding: 10px 0;
            color: var(--blue);
        }}
        .diff {{
            background: #0d1117;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.85em;
            line-height: 1.4;
        }}
        .diff-add {{ color: var(--green); }}
        .diff-remove {{ color: var(--red); }}
        .diff-info {{ color: var(--blue); }}

        .questions {{ padding: 20px; }}
        .question {{
            margin-bottom: 20px;
        }}
        .question label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .question textarea {{
            width: 100%;
            background: var(--accent);
            border: 1px solid #333;
            border-radius: 4px;
            color: var(--text);
            padding: 10px;
            font-family: inherit;
            resize: vertical;
        }}
        .alignment-options {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin: 10px 0;
        }}
        .alignment-options label {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: normal;
            cursor: pointer;
        }}

        .submit-section {{
            text-align: center;
            padding: 30px;
            background: var(--card-bg);
            border-radius: 8px;
        }}
        .submit-btn {{
            background: var(--green);
            color: #000;
            border: none;
            padding: 15px 40px;
            font-size: 1.1em;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
        }}
        .submit-btn:hover {{ opacity: 0.9; }}

        .results {{
            display: none;
            background: var(--card-bg);
            padding: 30px;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .results.show {{ display: block; }}
        .results h2 {{ margin-top: 0; }}
        .result-bar {{
            height: 30px;
            background: var(--accent);
            border-radius: 4px;
            overflow: hidden;
            display: flex;
            margin: 20px 0;
        }}
        .result-aligned {{ background: var(--green); }}
        .result-partial {{ background: var(--yellow); }}
        .result-misaligned {{ background: var(--red); }}

        .concerns {{
            background: rgba(251, 191, 36, 0.1);
            border-left: 4px solid var(--yellow);
            padding: 15px;
            margin-top: 20px;
        }}
        .concerns h3 {{ margin-top: 0; color: var(--yellow); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Implementation Understanding Quiz</h1>

        <div class="summary">
            <div class="stat-card files">
                <div class="stat-value">{len(files)}</div>
                <div class="stat-label">Files Changed</div>
            </div>
            <div class="stat-card added">
                <div class="stat-value">+{total_added}</div>
                <div class="stat-label">Lines Added</div>
            </div>
            <div class="stat-card removed">
                <div class="stat-value">-{total_removed}</div>
                <div class="stat-label">Lines Removed</div>
            </div>
        </div>

        <div class="chart">
            <h2>📊 Changes by File</h2>
            {"".join(file_bars)}
        </div>

        <form id="quiz-form">
            <p style="color: var(--text-dim); text-align: center;">
                Answer these questions to verify your understanding of each change.<br>
                Honest answers help identify misalignment early!
            </p>

            {"".join(file_cards)}

            <div class="submit-section">
                <button type="submit" class="submit-btn">Submit Quiz</button>
            </div>
        </form>

        <div class="results" id="results">
            <h2>📋 Quiz Results</h2>
            <div id="result-content"></div>
        </div>
    </div>

    <script>
        document.getElementById('quiz-form').addEventListener('submit', function(e) {{
            e.preventDefault();

            const formData = new FormData(this);
            const results = {{
                timestamp: new Date().toISOString(),
                branch: "{branch}",
                base: "{base}",
                files: [],
                summary: {{ aligned: 0, partial: 0, misaligned: 0 }}
            }};

            // Collect answers for each file
            let fileIndex = 0;
            document.querySelectorAll('.file-card').forEach((card, i) => {{
                const filepath = card.querySelector('.file-path').textContent;
                const alignment = formData.get('alignment-' + i);

                results.files.push({{
                    path: filepath,
                    comprehension: formData.get('comprehension-' + i) || '',
                    tradeoff: formData.get('tradeoff-' + i) || '',
                    alignment: alignment || 'unanswered',
                    alignmentNote: formData.get('alignment-note-' + i) || ''
                }});

                if (alignment === 'yes') results.summary.aligned++;
                else if (alignment === 'partial') results.summary.partial++;
                else if (alignment === 'no') results.summary.misaligned++;
            }});

            // Calculate percentages
            const total = results.files.length;
            const alignedPct = (results.summary.aligned / total * 100) || 0;
            const partialPct = (results.summary.partial / total * 100) || 0;
            const misalignedPct = (results.summary.misaligned / total * 100) || 0;

            // Build results HTML
            let html = `
                <div class="result-bar">
                    <div class="result-aligned" style="width: ${{alignedPct}}%"></div>
                    <div class="result-partial" style="width: ${{partialPct}}%"></div>
                    <div class="result-misaligned" style="width: ${{misalignedPct}}%"></div>
                </div>
                <p>
                    <span style="color: var(--green)">■</span> Aligned: ${{results.summary.aligned}}/${{total}} (${{alignedPct.toFixed(0)}}%)<br>
                    <span style="color: var(--yellow)">■</span> Partial: ${{results.summary.partial}}/${{total}} (${{partialPct.toFixed(0)}}%)<br>
                    <span style="color: var(--red)">■</span> Misaligned: ${{results.summary.misaligned}}/${{total}} (${{misalignedPct.toFixed(0)}}%)
                </p>
            `;

            // Show concerns
            const concerns = results.files.filter(f => f.alignment !== 'yes' && f.alignmentNote);
            if (concerns.length > 0) {{
                html += '<div class="concerns"><h3>⚠️ Needs Discussion</h3>';
                concerns.forEach(f => {{
                    html += `<p><strong>${{f.path}}</strong><br>${{f.alignmentNote}}</p>`;
                }});
                html += '</div>';
            }}

            // Recommendation
            if (results.summary.misaligned > 0) {{
                html += '<p style="color: var(--red); font-weight: bold; margin-top: 20px;">⛔ Review misaligned files before merge.</p>';
            }} else if (results.summary.partial > 0) {{
                html += '<p style="color: var(--yellow); font-weight: bold; margin-top: 20px;">⚠️ Discuss partial alignments before merge.</p>';
            }} else {{
                html += '<p style="color: var(--green); font-weight: bold; margin-top: 20px;">✅ All changes match your intentions!</p>';
            }}

            // Save results button
            html += `
                <button onclick="saveResults()" style="margin-top: 20px; padding: 10px 20px; cursor: pointer;">
                    📥 Download Results JSON
                </button>
            `;

            document.getElementById('result-content').innerHTML = html;
            document.getElementById('results').classList.add('show');
            document.getElementById('results').scrollIntoView({{ behavior: 'smooth' }});

            // Store results for download
            window.quizResults = results;
        }});

        function saveResults() {{
            const blob = new Blob([JSON.stringify(window.quizResults, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'quiz-results-' + new Date().toISOString().split('T')[0] + '.json';
            a.click();
        }}
    </script>
</body>
</html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Implementation Understanding Quiz")
    parser.add_argument("--branch", default="HEAD", help="Branch to quiz")
    parser.add_argument("--base", default="main", help="Base branch to compare against")
    parser.add_argument("--file", nargs="+", help="Specific files to quiz")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be quizzed")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    parser.add_argument("--html", action="store_true", help="Open quiz in browser (HTML mode)")
    args = parser.parse_args()

    config = get_config()

    if args.config:
        print("Quiz configuration:")
        print(yaml.dump(config, default_flow_style=False))
        return 0

    # Get changed files
    if args.file:
        files = [{"path": f, "added": 0, "removed": 0, "total_changed": 0} for f in args.file]
    else:
        files = get_changed_files(args.branch, args.base)

    # Filter by min_lines_changed
    min_lines = config.get("min_lines_changed", 0)
    if min_lines > 0:
        files = [f for f in files if f["total_changed"] >= min_lines]

    if not files:
        print("No files to quiz.")
        return 0

    if args.dry_run:
        print("Would quiz the following files:")
        print(render_changes_chart(files))
        return 0

    # HTML mode - generate and open in browser
    if args.html:
        html_content = generate_html_quiz(files, args.branch, args.base)

        # Write to temp file and open
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html_content)
            temp_path = f.name

        print(f"Opening quiz in browser: {temp_path}")
        webbrowser.open(f"file://{temp_path}")
        return 0

    # Run interactive terminal quiz
    results = run_interactive_quiz(files, args.branch, args.base)
    print_quiz_results(results)

    # Return non-zero if misaligned (for CI integration)
    if results["misaligned"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
