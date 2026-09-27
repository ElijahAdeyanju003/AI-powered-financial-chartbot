import os
import re
import html

import pandas as pd
from flask import Flask, request, jsonify, render_template_string

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "financial_analysis_output.csv")

df = pd.read_csv(CSV_PATH)

DEFAULT_YEAR = 2025


def get_row(df, company, year):
    match = df[(df["Company"].str.lower() == company.lower()) & (df["Fiscal Year"] == year)]
    return match.iloc[0] if not match.empty else None


def detect_company(query, companies):
    q = query.lower()
    for c in companies:
        if c.lower() in q:
            return c
    return None


def detect_year(query, default_year=DEFAULT_YEAR):
    match = re.search(r"20(2[3-5])", query)
    return int("20" + match.group(1)) if match else default_year


def simple_chatbot(user_query, df):
    companies = df["Company"].unique().tolist()
    company = detect_company(user_query, companies)
    year = detect_year(user_query)
    q = user_query.lower()

    if company is None:
        return "Sorry, I can only answer questions about Microsoft, Tesla, or Apple. Please include the company name."

    row = get_row(df, company, year)
    if row is None:
        return f"Sorry, I don't have {company} data for fiscal year {year}. I have data for 2023-2025."

    if "revenue" in q and "grow" not in q and "chang" not in q:
        return f"{company}'s total revenue in FY{year} was ${row['Revenue']:,.0f} million."

    elif "net income" in q and ("chang" in q or "grow" in q or "last year" in q):
        prev_row = get_row(df, company, year - 1)
        if prev_row is None:
            return f"Sorry, I don't have prior-year data to compare {company}'s net income change for FY{year}."
        change = row["NetIncome"] - prev_row["NetIncome"]
        pct = (change / prev_row["NetIncome"]) * 100
        direction = "increased" if change > 0 else "decreased"
        return (
            f"{company}'s net income {direction} by ${abs(change):,.0f} million "
            f"({pct:+.1f}%) from FY{year - 1} to FY{year}."
        )

    elif "net income" in q:
        return f"{company}'s net income in FY{year} was ${row['NetIncome']:,.0f} million."

    elif "total assets" in q or "assets" in q:
        return f"{company}'s total assets in FY{year} were ${row['TotalAssets']:,.0f} million."

    elif "liabilit" in q or "debt" in q:
        return (
            f"{company}'s total liabilities in FY{year} were ${row['TotalLiabilities']:,.0f} million "
            f"(debt-to-assets ratio: {row['DebtToAssets'] * 100:.1f}%)."
        )

    elif "cash flow" in q:
        return f"{company}'s cash flow from operating activities in FY{year} was ${row['OCF']:,.0f} million."

    else:
        return "Sorry, I can only provide information on predefined queries (revenue, net income, total assets, liabilities/debt, or operating cash flow)."


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
  <title>Financial Chatbot</title>
  <style>
    :root {
      --bg:        #0f172a;
      --panel:     #1e293b;
      --panel-2:   #0b1220;
      --border:    #475569;
      --border-hi: #64748b;
      --accent:    #38bdf8;
      --you:       #22d3ee;
      --bot:       #e2e8f0;
      --muted:     #94a3b8;
    }
    * { box-sizing: border-box; }

    body {
      margin: 0; min-height: 100vh;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: radial-gradient(circle at top, #1e293b, #0f172a 60%);
      color: var(--bot);
      display: flex; flex-direction: column; align-items: center;
      padding: 32px 16px;
    }

    /* Outer card */
    .card {
      width: 100%; max-width: 720px;
      background: var(--panel);
      border: 2px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 20px 50px rgba(0,0,0,.5),
                  0 0 0 1px rgba(255,255,255,.03) inset;
      overflow: hidden;
    }

    /* Header */
    header {
      padding: 18px 24px;
      border-bottom: 2px solid var(--border);
      background: linear-gradient(180deg, #1e293b, #172033);
      display: flex; align-items: center; gap: 12px;
    }
    header .dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: var(--accent);
      border: 2px solid #0ea5e9;
      box-shadow: 0 0 12px var(--accent);
    }
    header h1 { font-size: 1.05rem; margin: 0; font-weight: 600; }
    header p  { margin: 0; font-size: .78rem; color: var(--muted); }

    /* Message log */
    #log {
      padding: 20px 24px;
      height: 380px; overflow-y: auto;
      display: flex; flex-direction: column; gap: 12px;
      border-bottom: 2px solid var(--border);
      background: var(--panel-2);
    }
    #log::-webkit-scrollbar { width: 10px; }
    #log::-webkit-scrollbar-track {
      background: #0b1220;
      border-left: 1px solid var(--border);
    }
    #log::-webkit-scrollbar-thumb {
      background: #334155;
      border: 1px solid var(--border);
      border-radius: 6px;
    }
    #log::-webkit-scrollbar-thumb:hover { background: #475569; }

    /* Message bubbles */
    .msg {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 14px;
      line-height: 1.45;
      font-size: .92rem;
      animation: fade .25s ease;
      border: 2px solid var(--border);
    }
    .you {
      align-self: flex-end;
      background: linear-gradient(135deg,#0ea5e9,#22d3ee);
      color: #0f172a;
      border-color: #0891b2;
      border-bottom-right-radius: 4px;
      font-weight: 500;
    }
    .bot {
      align-self: flex-start;
      background: #334155;
      border-color: var(--border-hi);
      border-bottom-left-radius: 4px;
    }
    .bot.empty {
      color: var(--muted);
      font-style: italic;
      background: transparent;
      border-style: dashed;
      border-color: var(--border);
    }
    @keyframes fade {
      from { opacity: 0; transform: translateY(4px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* Typing dots */
    .typing::after {
      content: '…';
      animation: dots 1s steps(3, end) infinite;
    }
    @keyframes dots {
      0%   { content: '.';   }
      33%  { content: '..';  }
      66%  { content: '...'; }
    }

    /* Suggestion chips */
    .chips {
      display: flex; flex-wrap: wrap; gap: 8px;
      padding: 14px 24px;
      border-bottom: 2px solid var(--border);
      background: var(--panel);
    }
    .chip {
      font-size: .78rem;
      padding: 6px 12px;
      border-radius: 999px;
      background: #1e293b;
      border: 2px solid var(--border);
      color: #cbd5e1;
      cursor: pointer;
      transition: border-color .15s, color .15s, background .15s;
    }
    .chip:hover {
      border-color: var(--accent);
      color: var(--accent);
      background: #0b1220;
    }

    /* Input row */
    form {
      display: flex; gap: 10px;
      padding: 16px 24px;
      background: var(--panel-2);
    }
    input[type=text] {
      flex: 1;
      padding: 12px 14px;
      border-radius: 10px;
      border: 2px solid var(--border);
      background: #0f172a;
      color: #e2e8f0;
      font-size: .95rem;
      outline: none;
      transition: border-color .15s, box-shadow .15s;
    }
    input[type=text]:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(56,189,248,.18);
    }

    /* Buttons */
    button {
      padding: 12px 20px;
      border-radius: 10px;
      border: 2px solid #0891b2;
      background: var(--accent);
      color: #0f172a;
      font-weight: 600;
      cursor: pointer;
      transition: transform .1s, filter .15s, border-color .15s;
    }
    button:hover  { filter: brightness(1.08); border-color: #0ea5e9; }
    button:active { transform: scale(.97); }
    button.ghost {
      background: transparent;
      color: var(--muted);
      border-color: var(--border);
    }
    button.ghost:hover { color: var(--accent); border-color: var(--accent); }
  </style>
</head>
<body>
  <h1>Financial Chatbot (Apple &middot; Microsoft &middot; Tesla, FY2023&ndash;2025)</h1>
  <div id="log">{{ log_html|safe }}</div>
  <form method="post" action="/">
    <input type="text" name="q" placeholder="e.g. What is Tesla's total revenue in 2024?"
           autofocus required>
    <button type="submit">Ask</button>
  </form>
  <p class="hint">Try: revenue &middot; net income change &middot; total assets &middot; liabilities &middot; cash flow</p>
</body>
</html>
"""

# In-memory history so the page can show prior turns (per server process, not per visitor).
history = []


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        q = request.form.get("q", "").strip()
        if q:
            answer = simple_chatbot(q, df)
            history.append((q, answer))
    rows = []
    for q, a in history:
        rows.append(f'<div class="you"><b>You:</b> {html.escape(q)}</div>')
        rows.append(f'<div class="bot"><b>Bot:</b> {html.escape(a)}</div>')
    log_html = "".join(rows) or '<div class="bot">Ask a question to begin.</div>'
    return render_template_string(PAGE, log_html=log_html)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    q = data.get("query", "")
    return jsonify({"query": q, "answer": simple_chatbot(q, df)})


@app.route("/reset", methods=["POST"])
def reset():
    history.clear()
    return ("", 204)


if __name__ == "__main__":
    # Render (and most PaaS hosts) inject the port to bind via the PORT env var.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
