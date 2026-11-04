"""
Ledger — Personal Expense Tracker (opens in your web browser)
--------------------------------------------------------------
Run this one file and your browser opens the app automatically.
Uses only the Python standard library — nothing to install.

    python expense_tracker_browser.py

Your expenses are saved to  expenses.csv  next to this file
(columns: date, category, amount, description), so they are still
there next time. Press Ctrl+C in the terminal to stop the server.

Needs an internet connection only for the chart library and fonts.
"""

import csv
import json
import os
import threading
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8000
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")
FIELDS = ["date", "category", "amount", "description"]
CATEGORIES = ["Food", "Travel", "Education", "Shopping", "Entertainment", "Other"]
lock = threading.Lock()


# ---------------------------------------------------------------- storage
def read_expenses():
    """Read expenses.csv, skipping any row that is not a valid expense."""
    if not os.path.exists(CSV_FILE):
        return []
    out = []
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            clean = clean_row(row)
            if clean:
                clean["id"] = f"f{i}"
                out.append(clean)
    return out


def clean_row(row):
    """Return a validated expense dict, or None if the row is invalid."""
    try:
        d = datetime.strptime(str(row.get("date", "")).strip(), "%Y-%m-%d").date()
        amount = float(str(row.get("amount", "")).replace(",", "").strip())
    except ValueError:
        return None
    if d > date.today() or d.year < 1990:
        return None
    if not (0 < amount <= 10_000_000):
        return None
    category = str(row.get("category", "")).strip()
    return {
        "date": d.isoformat(),
        "category": category if category in CATEGORIES else "Other",
        "amount": round(amount, 2),
        "description": str(row.get("description", "")).strip()[:80] or "Imported",
    }


def write_expenses(rows):
    """Replace expenses.csv with the validated rows."""
    good = [r for r in (clean_row(r) for r in rows) if r]
    tmp = CSV_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(good)
    os.replace(tmp, CSV_FILE)          # atomic: never leaves a half-written file
    return len(good)


# ----------------------------------------------------------------- server
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/expenses":
            with lock:
                self._send(200, json.dumps(read_expenses()), "application/json")
        else:
            self._send(404, "Not found", "text/plain")

    def do_POST(self):
        if self.path.split("?")[0] != "/api/expenses":
            return self._send(404, "Not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 20_000_000:
                return self._send(413, "Too large", "text/plain")
            rows = json.loads(self.rfile.read(length) or b"[]")
            if not isinstance(rows, list):
                raise ValueError("expected a list")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, "Bad request", "text/plain")
        with lock:
            saved = write_expenses(rows)
        self._send(200, json.dumps({"saved": saved}), "application/json")

    def log_message(self, *args):       # keep the terminal quiet
        pass


def main():
    server = None
    for port in range(PORT, PORT + 20):          # use the next free port if busy
        try:
            server = HTTPServer((HOST, port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit("Could not find a free port. Close other apps and retry.")

    url = f"http://{HOST}:{server.server_port}/"
    print(f"Ledger is running at {url}")
    print(f"Saving to {CSV_FILE}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


# The web page itself (HTML, CSS and JavaScript), served at "/".
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Ledger — expense tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0A0C0F; --panel:#111419; --line:#242A33; --line-soft:#1A1F26;
  --ink:#ECEFF3; --ink-soft:#828C99; --ink-dim:#5C6571;
  --accent:#C8FF4D; --accent-dim:#9CCF2E; --accent-ink:#0A0C0F;
  --food:#FF7A5C; --travel:#5FC9FF; --education:#C8FF4D; --shopping:#FFC24B; --entertainment:#C79BFF; --other:#828C99;
  --danger:#FF6B6B; --ok:#7CFFB0; --grid:rgba(236,239,243,.06); --chip-ink:#0A0C0F;
  --mono:"JetBrains Mono",ui-monospace,monospace;
  --head:"Space Grotesk",system-ui,sans-serif;
  --body:"Inter",system-ui,sans-serif;
}
:root[data-theme="light"]{
  --bg:#F3F4F1; --panel:#FFFFFF; --line:#DADCD6; --line-soft:#E7E8E3;
  --ink:#12140F; --ink-soft:#5A5F55; --ink-dim:#7C8174;
  --accent:#4F7A00; --accent-dim:#3F6200; --accent-ink:#FFFFFF;
  --food:#C1401D; --travel:#0E7BAE; --education:#5C8A00; --shopping:#9A6B00; --entertainment:#7136B8; --other:#6E7368;
  --danger:#B32424; --ok:#12793F; --grid:rgba(18,20,15,.07); --chip-ink:#FFFFFF;
}
@media (prefers-color-scheme: light){
  :root:not([data-theme="dark"]){
    --bg:#F3F4F1; --panel:#FFFFFF; --line:#DADCD6; --line-soft:#E7E8E3;
    --ink:#12140F; --ink-soft:#5A5F55; --ink-dim:#7C8174;
    --accent:#4F7A00; --accent-dim:#3F6200; --accent-ink:#FFFFFF;
    --food:#C1401D; --travel:#0E7BAE; --education:#5C8A00; --shopping:#9A6B00; --entertainment:#7136B8; --other:#6E7368;
    --danger:#B32424; --ok:#12793F; --grid:rgba(18,20,15,.07); --chip-ink:#FFFFFF;
  }
}
:root{box-sizing:border-box; padding-top:env(safe-area-inset-top,0px); padding-bottom:env(safe-area-inset-bottom,0px)}
html{scroll-padding-top:env(safe-area-inset-top,0px); scroll-behavior:smooth}
*{box-sizing:border-box}
body{margin:0; background:var(--bg); color:var(--ink); font:15.5px/1.55 var(--body)}
h1,h2,h3{font-family:var(--head); letter-spacing:-.01em; margin:0}
::selection{background:var(--accent); color:var(--accent-ink)}
.wrap{max-width:1180px; margin:0 auto; padding:0 24px}
.mono{font-family:var(--mono)}

/* topbar */
.topbar{border-bottom:1px solid var(--line-soft)}
.topbar .wrap{display:flex; align-items:center; justify-content:space-between; padding:16px 24px; gap:16px}
.brand{display:flex; align-items:center; gap:9px; font:600 17px var(--head)}
.brand i{width:8px; height:8px; background:var(--accent); border-radius:50%}
.topnav{display:flex; gap:22px; align-items:center; font-size:14px; color:var(--ink-soft)}
.topnav a{text-decoration:none} .topnav a:hover{color:var(--ink)}
.theme-btn{background:none; border:1px solid var(--line); color:var(--ink-soft); font:12.5px var(--mono);
  padding:6px 12px; cursor:pointer; border-radius:3px}
.theme-btn:hover{border-color:var(--accent); color:var(--ink)}
@media (max-width:640px){.topnav a{display:none}}

/* hero */
.hero{border-bottom:1px solid var(--line-soft); padding:60px 0 54px; position:relative; overflow:hidden}
.hero::before{content:""; position:absolute; inset:0; pointer-events:none;
  background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
  background-size:64px 64px; -webkit-mask-image:radial-gradient(ellipse 70% 60% at 25% 0%,#000,transparent 75%);
  mask-image:radial-gradient(ellipse 70% 60% at 25% 0%,#000,transparent 75%)}
.hero-grid{display:grid; grid-template-columns:1.05fr .95fr; gap:52px; align-items:center; position:relative}
@media (max-width:940px){.hero-grid{grid-template-columns:1fr}}
.pill{display:inline-flex; align-items:center; gap:8px; font:12.5px var(--mono); color:var(--ink-soft);
  border:1px solid var(--line); padding:5px 12px 5px 10px; border-radius:20px; margin-bottom:22px}
.pill i{width:6px; height:6px; background:var(--accent); border-radius:50%}
.hero h1{font-size:clamp(32px,4.6vw,52px); line-height:1.05; max-width:15ch; font-weight:600}
.hero .lede{color:var(--ink-soft); font-size:17px; max-width:45ch; margin:20px 0 28px}
.cta{display:flex; gap:12px; flex-wrap:wrap}
.btn{font:600 14.5px var(--body); padding:12px 20px; border-radius:3px; cursor:pointer; border:1px solid transparent;
  display:inline-flex; align-items:center; text-decoration:none; color:inherit; background:none}
.btn-accent{background:var(--accent); color:var(--accent-ink)}
.btn-accent:hover{background:var(--accent-dim)}
.btn-outline{border-color:var(--line); color:var(--ink)}
.btn-outline:hover{border-color:var(--ink-soft)}
.btn-small{padding:9px 14px; font-size:13.5px}

/* terminal */
.term{background:var(--panel); border:1px solid var(--line); border-radius:6px; overflow:hidden}
.term-bar{display:flex; align-items:center; gap:7px; padding:10px 14px; border-bottom:1px solid var(--line-soft)}
.term-bar b{width:9px; height:9px; border-radius:50%; background:var(--line)}
.term-bar span{margin-left:8px; font:12.5px var(--mono); color:var(--ink-dim)}
.term-body{padding:16px 18px; font:13px/1.8 var(--mono); color:var(--ink-soft); min-height:176px}
.term-body .u{color:var(--ink)} .term-body .g{color:var(--ok)}
.cursor{display:inline-block; width:7px; height:14px; background:var(--accent); vertical-align:-2px; animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
@media (prefers-reduced-motion:reduce){.cursor{animation:none} html{scroll-behavior:auto}}

/* stat strip */
.strip{border-bottom:1px solid var(--line-soft); background:var(--panel)}
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.stat{padding:20px 24px; border-right:1px solid var(--line-soft); min-width:0}
.stat:last-child{border-right:none}
.stat .k{font:12.5px var(--mono); color:var(--ink-dim); margin-bottom:6px}
.stat .v{font:500 21px var(--mono); letter-spacing:-.02em; overflow-wrap:anywhere}
.stat .d{font-size:12.5px; color:var(--ink-soft); margin-top:4px; overflow-wrap:anywhere}

/* sections */
section.block{padding:48px 0 0}
.sec-head{margin-bottom:20px}
.sec-head .tag{display:block; font:12.5px var(--mono); color:var(--accent); margin-bottom:8px}
.sec-head h2{font-size:24px}
.sec-head p{color:var(--ink-soft); font-size:14.5px; margin:8px 0 0; max-width:56ch}
.panel{background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:24px}

/* manual-entry form */
.add-grid{display:grid; grid-template-columns:150px 170px 150px 1fr auto; gap:14px; align-items:end}
@media (max-width:1020px){.add-grid{grid-template-columns:1fr 1fr}.add-grid .desc{grid-column:1/-1}.add-grid .go{grid-column:1/-1}}
@media (max-width:520px){.add-grid{grid-template-columns:1fr}}
label{display:block; font:12.5px var(--mono); color:var(--ink-dim); margin-bottom:6px}
input,select{width:100%; padding:11px 12px; background:var(--bg); border:1px solid var(--line);
  border-radius:3px; color:var(--ink); font:14.5px var(--body); -webkit-appearance:none; appearance:none; color-scheme:dark light}
select{background-image:linear-gradient(45deg,transparent 50%,var(--ink-dim) 50%),linear-gradient(135deg,var(--ink-dim) 50%,transparent 50%);
  background-position:calc(100% - 18px) 55%,calc(100% - 13px) 55%; background-size:5px 5px,5px 5px; background-repeat:no-repeat}
input:focus,select:focus,button:focus-visible,a:focus-visible{outline:2px solid var(--accent); outline-offset:1px}
.msg{font:13px var(--mono); min-height:20px; margin:14px 0 0; overflow-wrap:anywhere}
.msg.err{color:var(--danger)} .msg.ok{color:var(--ok)}
.recent{margin-top:18px; padding-top:16px; border-top:1px solid var(--line-soft)}
.recent h3{font:12.5px var(--mono); color:var(--ink-dim); font-weight:400; margin-bottom:8px}
.recent-row{display:flex; justify-content:space-between; gap:12px; padding:7px 0; font-size:14px; border-bottom:1px solid var(--line-soft)}
.recent-row:last-child{border-bottom:none}
.recent-row span:last-child{font-family:var(--mono); white-space:nowrap}
.recent-empty{color:var(--ink-soft); font-size:14px}

/* data tools */
.tools{display:flex; flex-wrap:wrap; gap:10px; align-items:center}
.tools .grow{flex:1; min-width:240px}
.tools p{margin:0; font-size:13.5px; color:var(--ink-soft)}
.tools h3{font-size:15px; margin-bottom:4px}

/* tabs + tables */
.tabs{display:flex; gap:2px; border-bottom:1px solid var(--line); margin-bottom:18px; overflow-x:auto}
.tab{background:none; border:none; border-bottom:2px solid transparent; padding:10px 16px; cursor:pointer;
  color:var(--ink-soft); white-space:nowrap; font:13.5px var(--mono)}
.tab[aria-selected="true"]{color:var(--ink); border-bottom-color:var(--accent)}
.scroll{overflow-x:auto}
table{width:100%; border-collapse:collapse; font-size:14px}
th{text-align:left; font:500 12px var(--mono); color:var(--ink-dim); padding:10px; border-bottom:1px solid var(--line); cursor:pointer; white-space:nowrap}
th:hover{color:var(--accent)}
td{padding:10px; border-bottom:1px solid var(--line-soft)}
td.amt,th.amt{text-align:right; font-family:var(--mono); white-space:nowrap}
tr.hi td:first-child{box-shadow:inset 3px 0 0 var(--danger)}
tr.lo td:first-child{box-shadow:inset 3px 0 0 var(--ok)}
.chip{display:inline-block; padding:2px 10px; border-radius:20px; font-size:12.5px; color:var(--chip-ink); white-space:nowrap}
.del{background:none; border:none; color:var(--ink-dim); cursor:pointer; padding:4px 8px; border-radius:3px}
.del:hover{color:var(--danger)}
.empty{padding:48px 20px; text-align:center; color:var(--ink-soft)}
.empty strong{display:block; color:var(--ink); font:600 16px var(--head); margin-bottom:6px}
.chart-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:16px}
.chart-box{background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:18px}
.chart-box h3{font-size:14.5px; margin-bottom:3px}
.chart-box p{margin:0 0 12px; font-size:13px; color:var(--ink-soft)}
.canvas-holder{position:relative; height:250px}
.stack{display:grid; gap:16px}
footer{margin-top:64px; border-top:1px solid var(--line-soft); padding:26px 0; font:13px var(--mono); color:var(--ink-dim)}
</style>
</head>
<body>

<header class="topbar"><div class="wrap">
  <div class="brand"><i></i>Ledger</div>
  <nav class="topnav">
    <a href="#add">Add expense</a><a href="#data">Import</a><a href="#analysis">Analysis</a>
    <button class="theme-btn" id="themeBtn" type="button">theme --toggle</button>
  </nav>
</div></header>

<section class="hero"><div class="wrap"><div class="hero-grid">
  <div>
    <span class="pill"><i></i>Served by Python, saved to expenses.csv</span>
    <h1>Expense infrastructure that scales with your spending.</h1>
    <p class="lede">Log what you spend by hand or import a CSV, then see category and monthly breakdowns instantly. No signup, and nothing leaves your computer.</p>
    <div class="cta">
      <a class="btn btn-accent" href="#add">Add an expense</a>
      <button class="btn btn-outline" id="heroImportBtn" type="button">Import CSV</button>
    </div>
  </div>
  <div class="term">
    <div class="term-bar"><b></b><b></b><b></b><span>session.log</span></div>
    <div class="term-body" id="termBody"></div>
  </div>
</div></div></section>

<div class="strip"><div class="wrap"><div class="stats" id="stats"></div></div></div>

<main class="wrap">

  <!-- MANUAL ENTRY -->
  <section class="block" id="add">
    <div class="sec-head">
      <span class="tag">// manual entry</span>
      <h2>Add an expense</h2>
      <p>Enter spending as it happens. Each entry is validated, saved in this browser, and counted in every total below straight away.</p>
    </div>
    <div class="panel">
      <form id="addForm" novalidate>
        <div class="add-grid">
          <div><label for="f-date">date</label><input type="date" id="f-date" required></div>
          <div><label for="f-cat">category</label>
            <select id="f-cat">
              <option>Food</option><option>Travel</option><option>Education</option>
              <option>Shopping</option><option>Entertainment</option><option>Other</option>
            </select></div>
          <div><label for="f-amt">amount (₹)</label>
            <input type="text" id="f-amt" inputmode="decimal" placeholder="250.00" autocomplete="off"></div>
          <div class="desc"><label for="f-desc">description</label>
            <input type="text" id="f-desc" placeholder="Lunch at the canteen" maxlength="80" autocomplete="off"></div>
          <div class="go"><button class="btn btn-accent" type="submit" style="width:100%">Save expense</button></div>
        </div>
        <p class="msg" id="msg" role="status"></p>
      </form>
      <div class="recent">
        <h3>last 5 entries</h3>
        <div id="recent"></div>
      </div>
    </div>
  </section>

  <!-- IMPORT / EXPORT -->
  <section class="block" id="data">
    <div class="sec-head">
      <span class="tag">// files</span>
      <h2>Import and export</h2>
    </div>
    <div class="stack">
      <div class="panel tools">
        <div class="grow">
          <h3>Read CSV &amp; calculate</h3>
          <p>Columns: date, category, amount, description. Replaces what's loaded and recalculates everything.</p>
        </div>
        <button type="button" id="readCalcBtn" class="btn btn-accent">Read CSV &amp; Calculate</button>
        <input type="file" id="readCalcInput" accept=".csv,text/csv" hidden>
      </div>
      <div class="panel tools">
        <div class="grow">
          <h3>Add rows from a file</h3>
          <p>Appends the valid rows to your existing expenses instead of replacing them.</p>
        </div>
        <button type="button" id="importBtn" class="btn btn-outline btn-small">Import CSV</button>
        <button type="button" id="exportBtn" class="btn btn-outline btn-small">Export CSV</button>
        <button type="button" id="sampleBtn" class="btn btn-outline btn-small">Load sample data</button>
        <button type="button" id="clearBtn" class="btn btn-outline btn-small">Clear all</button>
        <input type="file" id="fileInput" accept=".csv,text/csv" hidden>
      </div>
    </div>
    <p class="msg" id="readMsg"></p>
  </section>

  <!-- ANALYSIS -->
  <section class="block" id="analysis">
    <div class="sec-head">
      <span class="tag">// analysis</span>
      <h2>Where it went</h2>
    </div>

    <div class="tabs" role="tablist">
      <button class="tab" role="tab" aria-selected="true" data-tab="ledger">ledger</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="charts">charts</button>
      <button class="tab" role="tab" aria-selected="false" data-tab="breakdown">breakdown</button>
    </div>

    <div id="panel-ledger">
      <div class="panel" style="padding:6px 6px 0">
        <div class="scroll"><table id="tbl">
          <thead><tr>
            <th data-sort="date">date</th><th data-sort="category">category</th>
            <th data-sort="description">description</th><th class="amt" data-sort="amount">amount</th><th></th>
          </tr></thead>
          <tbody id="tbody"></tbody>
        </table></div>
        <div class="empty" id="emptyState" hidden>
          <strong>No expenses yet</strong>
          Add one above, or import a CSV to get started.
        </div>
      </div>
    </div>

    <div id="panel-charts" hidden>
      <div class="chart-grid">
        <div class="chart-box"><h3>Spending by category</h3><p>Where the money actually goes.</p>
          <div class="canvas-holder"><canvas id="barChart"></canvas></div></div>
        <div class="chart-box"><h3>Category share</h3><p>Same totals, as a proportion of everything.</p>
          <div class="canvas-holder"><canvas id="pieChart"></canvas></div></div>
        <div class="chart-box"><h3>Month by month</h3><p>Total spend over time.</p>
          <div class="canvas-holder"><canvas id="lineChart"></canvas></div></div>
        <div class="chart-box"><h3>Size of a typical expense</h3><p>How many expenses fall in each amount range.</p>
          <div class="canvas-holder"><canvas id="histChart"></canvas></div></div>
      </div>
    </div>

    <div id="panel-breakdown" hidden>
      <div class="stack">
        <div class="panel" style="padding:6px 6px 0"><div class="scroll"><table>
          <thead><tr><th>category</th><th class="amt">entries</th><th class="amt">total</th><th class="amt">average</th><th class="amt">share</th></tr></thead>
          <tbody id="catBody"></tbody></table></div></div>
        <div class="panel" style="padding:6px 6px 0"><div class="scroll"><table>
          <thead><tr><th>month</th><th class="amt">entries</th><th class="amt">total</th><th class="amt">average</th></tr></thead>
          <tbody id="monBody"></tbody></table></div></div>
      </div>
    </div>
  </section>
</main>

<footer><div class="wrap">Ledger · served by Python · data saved to expenses.csv</div></footer>

<script>
const KEY = "ledger.expenses.v1";
const CATS = ["Food","Travel","Education","Shopping","Entertainment","Other"];
let rows = [];
let sortKey = "date", sortDir = -1;
const charts = {};
const $ = id => document.getElementById(id);

/* storage (guarded: may be unavailable or empty) */
async function load(){
  try{
    const res = await fetch("/api/expenses");
    if(!res.ok) throw new Error("server " + res.status);
    rows = await res.json();
  } catch(e){
    try{ const raw = localStorage.getItem(KEY); rows = raw ? JSON.parse(raw) : []; } catch(e2){ rows = []; }
  }
  if(!Array.isArray(rows)) rows = [];
}
function save(){
  try{ localStorage.setItem(KEY, JSON.stringify(rows)); } catch(e){}
  fetch("/api/expenses", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(rows)})
    .catch(()=>{ /* server unreachable: browser copy still kept */ });
}

const money = n => "₹" + n.toLocaleString("en-IN",{minimumFractionDigits:2, maximumFractionDigits:2});
const esc = s => String(s).replace(/[<>&]/g, c=>({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]));
const catColor = c => getComputedStyle(document.documentElement)
  .getPropertyValue("--" + (CATS.includes(c) ? c.toLowerCase() : "other")).trim();
const monthKey = d => d.slice(0,7);
const monthName = k => { const [y,m]=k.split("-"); return new Date(y,m-1,1).toLocaleString("en-US",{month:"short"})+" "+y; };
const todayStr = () => { const d=new Date(); return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0"); };
const newId = () => Date.now()+"-"+Math.random().toString(36).slice(2,8);

/* validation */
function validate(date, amtRaw, desc){
  if(!date) return "Pick a date for this expense.";
  const d = new Date(date+"T00:00:00");
  if(isNaN(d.getTime())) return "That date isn't a real calendar date.";
  if(date > todayStr()) return "That date is in the future. Use today or earlier.";
  if(d.getFullYear() < 1990) return "That date is too far back to be an expense.";
  if(!amtRaw.trim()) return "Enter an amount.";
  if(!/^\d+(\.\d{1,2})?$/.test(amtRaw.trim())) return "Amount must be a number like 250 or 250.50, with no letters or symbols.";
  const amt = parseFloat(amtRaw);
  if(amt <= 0) return "Amount must be greater than zero.";
  if(amt > 10000000) return "That amount looks like a typo. Keep it under ₹1,00,00,000.";
  if(!desc.trim()) return "Add a short description so you'll recognise it later.";
  return null;
}
function setMsg(el, text, good){ el.className = "msg " + (good ? "ok" : "err"); el.textContent = text; }

/* manual add */
$("addForm").addEventListener("submit", e => {
  e.preventDefault();
  const date=$("f-date").value, cat=$("f-cat").value, amtR=$("f-amt").value, desc=$("f-desc").value;
  const error = validate(date, amtR, desc);
  if(error){ setMsg($("msg"), error, false); return; }
  rows.push({id:newId(), date, category:cat, amount:parseFloat(amtR), description:desc.trim()});
  save(); render();
  setMsg($("msg"), "Saved "+money(parseFloat(amtR))+" to "+cat+".", true);
  $("f-amt").value=""; $("f-desc").value=""; $("f-amt").focus();
});

$("tbody").addEventListener("click", e => {
  const b = e.target.closest("button[data-id]"); if(!b) return;
  rows = rows.filter(r => r.id !== b.dataset.id); save(); render();
});

document.querySelectorAll("th[data-sort]").forEach(th => th.addEventListener("click", () => {
  const k = th.dataset.sort;
  sortDir = (k===sortKey) ? -sortDir : (k==="amount"||k==="date" ? -1 : 1);
  sortKey = k; render();
}));

/* render pieces */
function stat(k,v,d){ return `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div>${d?`<div class="d">${d}</div>`:""}</div>`; }
function renderStats(){
  const el = $("stats");
  if(!rows.length){ el.innerHTML = stat("total_spent","₹0.00","nothing recorded yet"); return; }
  const total = rows.reduce((s,r)=>s+r.amount,0);
  const months = new Set(rows.map(r=>monthKey(r.date)));
  const thisMonth = todayStr().slice(0,7);
  const tm = rows.filter(r=>monthKey(r.date)===thisMonth).reduce((s,r)=>s+r.amount,0);
  const hi = rows.reduce((a,b)=>b.amount>a.amount?b:a);
  const lo = rows.reduce((a,b)=>b.amount<a.amount?b:a);
  el.innerHTML =
    stat("total_spent", money(total), rows.length+" entries, "+months.size+" month"+(months.size>1?"s":"")) +
    stat("this_month", money(tm), monthName(thisMonth)) +
    stat("avg_per_entry", money(total/rows.length), "monthly avg "+money(total/months.size)) +
    stat("highest", money(hi.amount), esc(hi.description)) +
    stat("lowest", money(lo.amount), esc(lo.description));
}
function sorted(){
  return [...rows].sort((a,b)=>{
    const x=a[sortKey], y=b[sortKey];
    return sortKey==="amount" ? (x-y)*sortDir : String(x).localeCompare(String(y))*sortDir;
  });
}
function renderTable(){
  const tb=$("tbody");
  $("emptyState").hidden = rows.length>0; $("tbl").hidden = rows.length===0;
  if(!rows.length){ tb.innerHTML=""; return; }
  const max=Math.max(...rows.map(r=>r.amount)), min=Math.min(...rows.map(r=>r.amount));
  tb.innerHTML = sorted().map(r=>`
    <tr class="${r.amount===max?'hi':(r.amount===min&&max!==min)?'lo':''}">
      <td class="mono">${r.date}</td>
      <td><span class="chip" style="background:${catColor(r.category)}">${r.category}</span></td>
      <td>${esc(r.description)}</td>
      <td class="amt">${money(r.amount)}</td>
      <td style="text-align:right"><button class="del" data-id="${r.id}" aria-label="Delete expense" title="Delete">✕</button></td>
    </tr>`).join("");
}
function renderRecent(){
  const el=$("recent");
  if(!rows.length){ el.innerHTML='<div class="recent-empty">Nothing yet. Your entries will show up here.</div>'; return; }
  el.innerHTML = [...rows].slice(-5).reverse().map(r=>
    `<div class="recent-row"><span>${esc(r.description)} <span style="color:var(--ink-dim)">· ${r.category}, ${r.date}</span></span><span>${money(r.amount)}</span></div>`).join("");
}
function byCategory(){
  const m={}; rows.forEach(r=>{ m[r.category]=m[r.category]||{n:0,sum:0}; m[r.category].n++; m[r.category].sum+=r.amount; });
  return Object.entries(m).sort((a,b)=>b[1].sum-a[1].sum);
}
function byMonth(){
  const m={}; rows.forEach(r=>{ const k=monthKey(r.date); m[k]=m[k]||{n:0,sum:0}; m[k].n++; m[k].sum+=r.amount; });
  return Object.entries(m).sort((a,b)=>a[0].localeCompare(b[0]));
}
function renderBreakdown(){
  const total = rows.reduce((s,r)=>s+r.amount,0) || 1;
  const none = c => `<tr><td colspan="${c}" style="color:var(--ink-soft);padding:20px">Nothing to break down yet.</td></tr>`;
  $("catBody").innerHTML = byCategory().map(([c,v])=>`
    <tr><td><span class="chip" style="background:${catColor(c)}">${c}</span></td><td class="amt">${v.n}</td>
    <td class="amt">${money(v.sum)}</td><td class="amt">${money(v.sum/v.n)}</td><td class="amt">${(v.sum/total*100).toFixed(1)}%</td></tr>`).join("") || none(5);
  $("monBody").innerHTML = byMonth().map(([k,v])=>`
    <tr><td class="mono">${monthName(k)}</td><td class="amt">${v.n}</td><td class="amt">${money(v.sum)}</td><td class="amt">${money(v.sum/v.n)}</td></tr>`).join("") || none(4);
}

/* charts */
function drawCharts(){
  if(typeof Chart==="undefined") return;
  const css = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();
  const soft=css("--ink-soft"), grid=css("--grid"), monoF={family:"JetBrains Mono",size:11};
  Chart.defaults.font.family='"Inter",system-ui,sans-serif'; Chart.defaults.color=soft;
  Object.values(charts).forEach(c=>c&&c.destroy());
  const cats=byCategory(), mons=byMonth();
  const axes={x:{grid:{display:false},ticks:{color:soft,font:monoF}}, y:{grid:{color:grid},border:{display:false},ticks:{color:soft,font:monoF}}};
  const base={plugins:{legend:{display:false}}, responsive:true, maintainAspectRatio:false};

  charts.bar=new Chart($("barChart"),{type:"bar",
    data:{labels:cats.map(c=>c[0]),datasets:[{data:cats.map(c=>c[1].sum),backgroundColor:cats.map(c=>catColor(c[0])),borderRadius:2}]},
    options:{...base,scales:axes}});
  charts.pie=new Chart($("pieChart"),{type:"doughnut",
    data:{labels:cats.map(c=>c[0]),datasets:[{data:cats.map(c=>c[1].sum),backgroundColor:cats.map(c=>catColor(c[0])),borderColor:css("--panel"),borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:"55%",plugins:{legend:{position:"right",labels:{boxWidth:10,boxHeight:10,usePointStyle:true,font:monoF}}}}});
  charts.line=new Chart($("lineChart"),{type:"line",
    data:{labels:mons.map(m=>monthName(m[0])),datasets:[{data:mons.map(m=>m[1].sum),borderColor:css("--accent"),backgroundColor:css("--accent")+"22",fill:true,tension:.25,pointBackgroundColor:css("--accent"),pointRadius:4}]},
    options:{...base,scales:axes}});

  const amts=rows.map(r=>r.amount); let labels=[], counts=[];
  if(amts.length){
    const lo=Math.min(...amts), hi=Math.max(...amts), bins=8, w=(hi-lo)/bins||1;
    counts=new Array(bins).fill(0);
    amts.forEach(a=>{ let i=Math.floor((a-lo)/w); if(i>=bins)i=bins-1; if(i<0)i=0; counts[i]++; });
    labels=counts.map((_,i)=>"₹"+Math.round(lo+i*w)+"–"+Math.round(lo+(i+1)*w));
  }
  charts.hist=new Chart($("histChart"),{type:"bar",
    data:{labels,datasets:[{data:counts,backgroundColor:css("--travel"),barPercentage:1,categoryPercentage:1,borderColor:css("--panel"),borderWidth:1}]},
    options:{...base,scales:{x:{grid:{display:false},ticks:{color:soft,maxRotation:60,minRotation:45,font:{family:"JetBrains Mono",size:9}}},
      y:{grid:{color:grid},border:{display:false},ticks:{color:soft,precision:0,font:monoF}}}}});
}

document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{
  document.querySelectorAll(".tab").forEach(x=>x.setAttribute("aria-selected", x===t));
  ["ledger","charts","breakdown"].forEach(n=>$("panel-"+n).hidden=(n!==t.dataset.tab));
  if(t.dataset.tab==="charts") drawCharts();
}));

/* CSV */
function csvCell(s){ return /[",\n]/.test(s) ? '"'+String(s).replace(/"/g,'""')+'"' : s; }
function splitCsvLine(l){
  const out=[]; let cur="", q=false;
  for(let i=0;i<l.length;i++){
    const c=l[i];
    if(q){ if(c==='"'){ if(l[i+1]==='"'){cur+='"';i++;} else q=false; } else cur+=c; }
    else if(c==='"') q=true;
    else if(c===","){ out.push(cur); cur=""; }
    else cur+=c;
  }
  out.push(cur); return out;
}
function parseCsv(text){
  const lines=text.replace(/^\uFEFF/,"").split(/\r?\n/).filter(l=>l.trim());
  const parsed=[], errors=[];
  const hasHeader = lines[0] && lines[0].toLowerCase().startsWith("date");
  lines.slice(hasHeader?1:0).forEach((l,i)=>{
    const [date,cat,amtRaw,...rest]=splitCsvLine(l);
    const amt=(amtRaw||"").replace(/,/g,"").trim();
    const desc=(rest.join(",")||"Imported").trim();
    const err=validate((date||"").trim(), amt, desc);
    if(err){ errors.push({line:i+2,reason:err}); return; }
    parsed.push({id:newId(), date:date.trim(), category:CATS.includes((cat||"").trim())?cat.trim():"Other", amount:parseFloat(amt), description:desc});
  });
  return {parsed,errors};
}
$("exportBtn").addEventListener("click",()=>{
  if(!rows.length){ setMsg($("readMsg"),"Nothing to export yet.",false); return; }
  const csv="date,category,amount,description\n"+sorted().map(r=>[r.date,r.category,r.amount.toFixed(2),csvCell(r.description)].join(",")).join("\n");
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));
  const a=document.createElement("a"); a.href=url; a.download="expenses.csv"; a.click(); URL.revokeObjectURL(url);
});
$("importBtn").addEventListener("click",()=>$("fileInput").click());
$("heroImportBtn").addEventListener("click",()=>$("fileInput").click());
$("fileInput").addEventListener("change",e=>{
  const f=e.target.files[0]; if(!f) return;
  const fr=new FileReader();
  fr.onload=()=>{
    const {parsed,errors}=parseCsv(fr.result);
    rows.push(...parsed); save(); render();
    setMsg($("readMsg"), parsed.length+" row"+(parsed.length===1?"":"s")+" added from \""+f.name+"\""+(errors.length?", "+errors.length+" skipped as invalid.":"."), parsed.length>0);
    e.target.value="";
  };
  fr.readAsText(f);
});
$("readCalcBtn").addEventListener("click",()=>{
  if(rows.length && !confirm("This replaces the "+rows.length+" expenses currently loaded with the file you pick. Continue?")) return;
  $("readCalcInput").click();
});
$("readCalcInput").addEventListener("change",e=>{
  const f=e.target.files[0]; if(!f) return;
  const fr=new FileReader();
  fr.onload=()=>{
    const {parsed,errors}=parseCsv(fr.result);
    if(!parsed.length){ setMsg($("readMsg"),"No valid rows found in \""+f.name+"\". Check it has date, category, amount, description columns.",false); e.target.value=""; return; }
    rows=parsed; save(); render();
    const total=rows.reduce((s,r)=>s+r.amount,0), top=byCategory()[0];
    setMsg($("readMsg"), `Read "${f.name}": ${rows.length} expenses, total ${money(total)}, biggest category ${top[0]} at ${money(top[1].sum)}`+(errors.length?`. ${errors.length} skipped as invalid.`:"."), true);
    document.querySelector('.tab[data-tab="charts"]').click();
    $("analysis").scrollIntoView({behavior:"smooth"});
    e.target.value="";
  };
  fr.readAsText(f);
});

/* sample / clear */
$("sampleBtn").addEventListener("click",()=>{
  const now=new Date(), out=[];
  const seed=[["Food","Canteen lunch",60,180],["Food","Groceries",400,1200],["Travel","Metro card top-up",100,300],["Travel","Auto to college",40,120],
    ["Education","Reference book",250,900],["Education","Lab printout",30,90],["Shopping","T-shirt",400,1400],["Entertainment","Movie ticket",180,450],
    ["Entertainment","Concert",600,1800],["Other","Phone recharge",199,599]];
  for(let back=4;back>=0;back--){
    const n=5+Math.floor(Math.random()*5);
    for(let i=0;i<n;i++){
      const s=seed[Math.floor(Math.random()*seed.length)];
      const dt=new Date(now.getFullYear(),now.getMonth()-back,1+Math.floor(Math.random()*27));
      if(dt>now) continue;
      out.push({id:newId(), date:dt.getFullYear()+"-"+String(dt.getMonth()+1).padStart(2,"0")+"-"+String(dt.getDate()).padStart(2,"0"),
        category:s[0], description:s[1], amount:Math.round((s[2]+Math.random()*(s[3]-s[2]))*100)/100});
    }
  }
  rows=out; save(); render(); setMsg($("readMsg"), out.length+" sample expenses loaded.", true);
});
$("clearBtn").addEventListener("click",()=>{
  if(!rows.length) return;
  if(confirm("Delete all "+rows.length+" expenses? This can't be undone.")){ rows=[]; save(); render(); setMsg($("readMsg"),"All expenses deleted.",true); }
});

/* theme */
$("themeBtn").addEventListener("click",()=>{
  const light=matchMedia("(prefers-color-scheme: light)").matches;
  const cur=document.documentElement.getAttribute("data-theme")||(light?"light":"dark");
  document.documentElement.setAttribute("data-theme", cur==="dark"?"light":"dark");
  render();
});

/* hero terminal */
function typeTerminal(){
  const el=$("termBody");
  const L=[["u","$ ledger add --category Food --amount 120"],["g","✓ saved ₹120.00 to Food"],
           ["u","$ ledger import expenses.csv"],["","parsing date, category, amount, description"],
           ["g","✓ valid rows added, invalid rows skipped"],["g","✓ totals and monthly trend recalculated"]];
  if(matchMedia("(prefers-reduced-motion: reduce)").matches){
    el.innerHTML=L.map(l=>`<div class="${l[0]}">${l[1]}</div>`).join(""); return;
  }
  let i=0, html="";
  (function step(){
    if(i>=L.length){ el.innerHTML=html+'<span class="cursor"></span>'; return; }
    html+=`<div class="${L[i][0]}">${L[i][1]}</div>`;
    el.innerHTML=html+'<span class="cursor"></span>';
    i++; setTimeout(step, 520);
  })();
}

function render(){ renderStats(); renderTable(); renderRecent(); renderBreakdown(); if(!$("panel-charts").hidden) drawCharts(); }
$("f-date").value=todayStr(); $("f-date").max=todayStr();
load().then(render); typeTerminal();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
