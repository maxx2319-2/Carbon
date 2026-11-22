---
description: Audit and stress-test the code you name, and write a PDF report 
argument-hint: <files, folders, feature or function to review> [extra instructions]
---

Review this target: $ARGUMENTS

If the target above is empty, ask the user what to review and stop.

This is a review, not a fix. Do not use git or GitHub for anything. Review the files as they are on disk right now.

## Rules from CLAUDE.md that always apply

Tell every subagent these rules word for word:

1. Never edit, move or delete any file outside `tests/`. The only other new file allowed is the final PDF report in `audits/`. Every fix goes in the report as a description and a code snippet. Nothing gets applied.
2. Run all code and tests in the project venv (`.venv\Scripts\python.exe`), headless (`QT_QPA_PLATFORM=offscreen`), so nothing opens on the user's desktop. Never start the app with a visible window.
3. Anything that can hang runs in a subprocess with a time limit (start at 20 s, and use up to 60 s only for cases that need it), so a hang is recorded and killed instead of blocking the run.
4. Write throwaway probe scripts in the system temp folder, not in the repo. Tests that are worth keeping go in `tests/`.
5. Do not add comments to any code you write, including tests and the report's code snippets.
6. Write the report in English. Quote UI text and error messages exactly as the app shows them (Danish). When you suggest new UI text or messages, write them in Danish.
7. Keep fixes small: the minimum change that solves the problem, matching the existing style. Do not suggest refactors that a finding doesn't need.
8. Every tool call needs a clear purpose. Don't test the tools or make exploratory calls.

## Steps

Create a todo list first, then follow these steps in order.

### 1. Scope (do this yourself, no subagent)

- Resolve the target to concrete files. If it names a feature or function, find the files that implement it, plus the code that calls it and the UI around it (for example the GUI bridge and the matching `.html` page).
- Read every `CLAUDE.md` that sits in the project root or in a folder above a file in scope.
- Find the existing tests that cover the target and the `xfail` markers in them. Those are known bugs: list them as "known and still open", not as new findings.
- Note the date, the files in scope and their line counts, and the environment (Windows version, Python version from `.venv`, PySide6 version).

### 2. Run the existing tests

Run the tests that cover the target once, headless in the venv, with `-q -rxX`. Run every failure a second time to separate flaky tests from real failures. Sort each failure into one of three groups: the test is out of date (the code changed on purpose), real problem, or flaky. Note: the `SIGALRM` guard in `tests/conftest.py` does not work on Windows, so put a subprocess time limit around anything that might hang.

### 3. Review in parallel

Launch these 5 subagents in parallel. Give each one the target, the file list from step 1, the CLAUDE.md rules above, the known xfails, and the ID prefixes:

`C` crash, freeze or hang · `S` security · `B` bug or wrong result · `R` rendering · `P` performance · `M` missing or incomplete feature · `E` error messages · `Q` code quality · `WIP` unfinished work in progress

- **Agent 1 (opus), wrong results.** Read the code path end to end and find inputs that give wrong answers, silent failures, wrong rounding, unit mistakes or off-by-one errors. Prove each one with a probe that shows the input, the actual output and the correct output.
- **Agent 2 (opus), crashes, hangs and security.** Look for uncaught exceptions, infinite loops, calculations that can't be stopped, thread leaks, bad file input (empty, binary, non-UTF-8, wrong JSON shape), and user text that reaches `eval`, `exec`, `parse_expr`, `innerHTML` or the file system. Run 400-line seeded random fuzz batches through the main entry point and record whether any exception escapes.
- **Agent 3 (sonnet), editor and rendering.** If the target touches the UI or an `.html` page, load it in a headless `QWebEngineView` and drive it through its own JavaScript functions (load, show output, typing, paste, wheel, undo). Look for frozen pages, rows that go missing, broken LaTeX, editable output and wrong line mapping. If the target has no UI, skip the browser part and only check the output formatting code.
- **Agent 4 (sonnet), performance and stress.** Push sizes far past normal use (huge lines, many lines, many variables, deep nesting, big loops, long text) and time each case. Record the size, the time, and a verdict for each case: OK, SLOW (works, but a user would notice), FLAKY (sometimes fails) or FAIL (hang, crash, wrong output or unusable time). Find where the cost grows quadratically or worse.
- **Agent 5 (sonnet), messages and CLAUDE.md.** Check the error messages the user sees: English Python errors that leak through, Danish spelling mistakes, and misleading messages. Check the code in scope against the code rules in CLAUDE.md (UI text in Danish, simplicity, no speculative features) and quote the exact rule for each violation. Flag unused or dead code as `Q`, and note that the user decides whether to remove it.

Each agent returns a list of findings. Every finding contains:
- ID prefix and a short title written as an outcome ("Zooming into a plot freezes the sheet for good")
- Where: `file:line` (one or more), with the function name in parentheses
- What happens: the exact input, and the measured output or time
- Why: the root cause, if it isn't obvious
- Fix: a concrete, minimal fix, with a short code snippet when it helps
- A suggested severity, and the probe used to reproduce it

Do not report:
- Style or formatting opinions
- Problems the agent could not reproduce or confirm in the code
- Pedantic nitpicks a senior engineer would not raise
- Code outside the target, unless the target directly calls it and the bug shows up through the target

### 4. Validate

For every finding, launch a validation subagent in parallel (opus for C, S and B findings, sonnet for the rest). The validator re-runs the reproduction from scratch, confirms the line numbers, and checks that the fix would actually solve the problem. It returns CONFIRMED (with its own measured output) or REJECTED (with the reason).

Drop every REJECTED finding. Merge duplicates. Then number the findings within each prefix (C-01, C-02, B-01 and so on) and set the final severity:

| Severity | Meaning |
|---|---|
| Critical | Crash, permanent freeze, security hole, or wrong answers in everyday use |
| High | Silent failures, data loss risk, wrong answers in specific cases, severe slowdowns |
| Medium | Broken feature with a workaround, misleading output, noticeable slowness |
| Low | Rare edge cases, cosmetics, clean-up |
| Info | Notes on unfinished work |

### 5. Write regression tests

Write `tests/test_review_<target>.py` (`<target>` in snake_case), following the conventions of the existing tests:
- One test per confirmed finding, with the ID in the test name (`test_b03_variables_pasted_as_text`).
- A bug that still exists gets `@pytest.mark.xfail(strict=True, reason="<ID> <short title>")`. Once the bug is fixed, the test XPASSes and fails, which tells the user to remove the marker.
- Anything that can hang runs in a subprocess with a time limit.
- Add the stress cases from agent 4 as tests too.
- No comments.

Run the new file headless in the venv until it reports 0 failed, and note the result (passed, xfailed, time).

### 6. Write the PDF report

Build the report as one self-contained HTML file in the system temp folder, then render it to `audits/<Target>_Audit_Report.pdf` in the project root (for example `audits/Interpreter_Audit_Report.pdf`). Create the `audits` folder if it doesn't exist. If the PDF already exists, add the date to the new file's name instead of overwriting the old one.

Follow `Interpreter_Audit_Report.pdf` (in `audits/`, or in the project root if it hasn't been moved) for structure, tone and look:

**Header:** small grey line "Carbon · <area>", the title "<Target> audit and stress test", a grey one-sentence subtitle, then a two-column table: Date, Code reviewed (the files, plus a note if there are uncommitted changes), Scope, Environment (with "Nothing was opened on your desktop."), and Source changes ("None. Only new files in tests/.").

**Summary:** "I found **N issues**: x critical, y high ...", plus one paragraph on what is solid and what the serious problems are, then one tsundere sentence. After that, the severity table (Severity, Count, Meaning), then a "Fix these first" table (ID, What to do) with up to ten entries that give the most benefit for the least work.

**1 Scope and method:** bullets for Reading, Probing, Editor (only if used), Stress, Fuzzing and Your test suite, each with real numbers (cases run, lines fuzzed).

**2 Findings:** a line explaining the ID prefixes, then one group per severity ("Critical (7)"). Each finding is a card with a coloured tag, the ID and title in bold, then rows labelled Where / What happens / Why / Fix, and an optional code block.

**3 Stress-test results:** tables with the columns Case, Size, Time, Verdict, Note. Colour the verdicts (OK green, SLOW amber, FLAKY amber, FAIL red) and point the Note at a finding ID.

**4 State of the existing test suite:** totals from step 2, plus a table of groups (Group, Tests, Verdict). Leave this section out if no existing tests cover the target.

**5 The new tests:** a table (File, What it covers), the final run result, and the PowerShell command to run the tests headless:
```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python.exe -m pytest -q -rxX tests\test_review_<target>.py
```

**6 What already works well:** honest bullets with numbers.

**7 Suggested order of work:** First (small changes, big effect), then the architecture fixes, correctness, the editor, and finally messages and clean-up, with finding IDs in each step.

End the report with one short tsundere sign-off line.

Use this CSS and card markup. Fill in the footer text:

```html
<style>
:root{--ink:#1f2328;--muted:#6b7280;--line:#d9dde3;--head:#e6e9f0;--crit:#b91c1c;--high:#dc4a12;--med:#b07d00;--low:#3f6787;--info:#6b7280;--ok:#15803d}
@page{@bottom-left{content:"Carbon · <Target> audit · <date>";font:8pt Arial,sans-serif;color:#6b7280}@bottom-right{content:"Page " counter(page);font:8pt Arial,sans-serif;color:#6b7280}}
body{font:9.5pt/1.45 Arial,Helvetica,sans-serif;color:var(--ink);margin:0}
.eyebrow{color:var(--muted);font-size:9pt}
h1{font-size:26pt;margin:2px 0 4px}
.sub{color:var(--muted);font-size:13pt;margin:0 0 14px}
h2{font-size:18pt;margin:22px 0 8px;break-after:avoid}
h3{font-size:12pt;margin:16px 0 6px;break-after:avoid}
h3.critical{color:var(--crit)}h3.high{color:var(--high)}h3.medium{color:var(--med)}h3.low{color:var(--low)}h3.info{color:var(--info)}
code{font-family:Consolas,monospace;font-size:8.5pt}
pre{font:8pt/1.35 Consolas,monospace;margin:6px 0;white-space:pre-wrap}
table{width:100%;border-collapse:collapse;margin:6px 0 12px}
th{background:var(--head);text-align:left;padding:5px 8px;border-bottom:1.5px solid #555}
td{padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
table.meta th{background:none;border:0;border-bottom:1px solid var(--line);width:120px}
tr{break-inside:avoid}
.card{border-bottom:1px solid var(--line);padding:8px 0;break-inside:avoid}
.card .head{display:flex;gap:8px;align-items:center;font-weight:bold;font-size:11.5pt;margin-bottom:4px}
.tag{color:#fff;font-size:7.5pt;font-weight:bold;padding:3px 6px;min-width:76px}
.tag.critical{background:var(--crit)}.tag.high{background:var(--high)}.tag.medium{background:var(--med)}.tag.low{background:var(--low)}.tag.info{background:var(--info)}
.row{display:grid;grid-template-columns:100px 1fr;gap:8px;margin-top:3px}
.row b{color:var(--muted)}
.ok{color:var(--ok);font-weight:bold}.slow,.flaky{color:var(--med);font-weight:bold}.fail{color:var(--crit);font-weight:bold}
.sev-critical{color:var(--crit);font-weight:bold}.sev-high{color:var(--high);font-weight:bold}.sev-medium{color:var(--med);font-weight:bold}.sev-low{color:var(--low);font-weight:bold}.sev-info{color:var(--info);font-weight:bold}
</style>

<div class="card">
  <div class="head"><span class="tag critical">CRITICAL</span>C-01 Title</div>
  <div class="row"><b>Where</b><span><code>src/file.py:123</code> (function)</span></div>
  <div class="row"><b>What happens</b><span>Input, measured output</span></div>
  <div class="row"><b>Why</b><span>Root cause</span></div>
  <div class="row"><b>Fix</b><span>Minimal fix</span></div>
  <pre>optional snippet</pre>
</div>
```

Render the PDF with this script. Save it in the system temp folder and run it headless in the venv, with a 120 s time limit:

```python
import sys
from pathlib import Path
from PySide6.QtCore import QUrl, QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage

app = QApplication(sys.argv)
src, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
page = QWebEnginePage()
layout = QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(16, 16, 16, 18), QPageLayout.Millimeter)
page.pdfPrintingFinished.connect(lambda path, ok: app.exit(0 if ok else 1))
page.loadFinished.connect(lambda ok: page.printToPdf(str(out), layout))
page.load(QUrl.fromLocalFile(str(src)))
sys.exit(app.exec())
```

Open the finished PDF with the Read tool and check that tables don't overflow, cards don't break across pages, and the footer shows on every page. Fix the HTML and render again if needed.

### 7. Terminal summary

Report back in the terminal:
- The path to the PDF and to the new test file
- The issue count by severity
- The "Fix these first" list (ID plus one line each)
- The result of the new test run

If nothing survived validation, say: "No issues found. Checked for bugs, crashes, security, rendering, performance and CLAUDE.md compliance." Still write a short PDF with the scope, the stress-test results and what works well.

Do not offer to apply any fix. The user will ask if they want one.
