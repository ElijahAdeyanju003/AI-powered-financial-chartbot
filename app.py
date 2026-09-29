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

SUGGESTIONS = [
    "What was Microsoft's revenue in 2025?",
    "What was Tesla's net income in 2024?",
    "Compare Apple's revenue in 2024 and 2025.",
    "How did Microsoft's net income change?",
]

WELCOME_MESSAGE = (
    "Hello! I can help you analyze financial information for Microsoft, "
    "Tesla, and Apple. What would you like to know?"
)


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

NUMBER_PATTERN = re.compile(r"(\$[\d,]+(?:\.\d+)?(?: million)?|\(?[+-]?\d+\.\d+%\)?)")


def render_message_text(text):
    """Escape user-facing text, then set figures in a tabular mono face."""
    escaped = html.escape(text)
    return NUMBER_PATTERN.sub(r'<span class="num">\1</span>', escaped)


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GFC Financial Insights</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #0b1e33;
    --ink-soft: #142d4a;
    --paper: #f6f4ee;
    --card: #efeade;
    --border: #ddd5c2;
    --slate: #52606d;
    --gold: #a8752f;
    --good: #2f8f5b;
    font-size: 16px;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    background: var(--paper);
    background-image: repeating-linear-gradient(
      to bottom,
      rgba(11, 30, 51, 0.035) 0px,
      rgba(11, 30, 51, 0.035) 1px,
      transparent 1px,
      transparent 30px
    );
    color: var(--ink);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    display: flex;
    justify-content: center;
    min-height: 100vh;
    padding: 32px 16px 48px;
  }

  .app {
    width: 100%;
    max-width: 640px;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(11, 30, 51, 0.06);
  }

  header {
    background: var(--ink);
    color: #fdfcf9;
    padding: 22px 26px 20px;
    border-bottom: 3px solid var(--gold);
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  header h1 {
    font-family: 'Source Serif 4', Georgia, serif;
    font-weight: 700;
    font-size: 1.5rem;
    margin: 0 0 4px;
    letter-spacing: 0.2px;
  }

  header p {
    margin: 0;
    font-size: 0.85rem;
    color: #c7d0da;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #cfe8d9;
    white-space: nowrap;
    margin-top: 2px;
  }

  .status::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--good);
    box-shadow: 0 0 0 3px rgba(47, 143, 91, 0.25);
  }

  .intro {
    margin: 20px 22px 4px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px 20px;
  }

  .intro h2 {
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.1rem;
    margin: 0 0 6px;
    color: var(--ink);
  }

  .intro p {
    margin: 0 0 14px;
    font-size: 0.88rem;
    color: var(--slate);
    line-height: 1.5;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    font-family: inherit;
    font-size: 0.82rem;
    color: var(--ink);
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 7px 14px;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }

  .chip:hover {
    background: var(--ink);
    color: #fdfcf9;
    border-color: var(--ink);
  }

  .thread {
    padding: 18px 22px 6px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-height: 420px;
    overflow-y: auto;
  }

  .msg { display: flex; flex-direction: column; max-width: 86%; }
  .msg.bot { align-self: flex-start; }
  .msg.user { align-self: flex-end; align-items: flex-end; }

  .msg .label {
    font-size: 0.72rem;
    color: var(--slate);
    margin-bottom: 4px;
    padding: 0 4px;
  }

  .msg .bubble {
    padding: 11px 14px;
    border-radius: 10px;
    font-size: 0.92rem;
    line-height: 1.5;
  }

  .msg.bot .bubble {
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--ink);
    border-top-left-radius: 3px;
  }

  .msg.user .bubble {
    background: var(--ink);
    color: #fdfcf9;
    border-top-right-radius: 3px;
  }

  .num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9em;
  }

  form.composer {
    display: flex;
    gap: 10px;
    padding: 16px 22px 8px;
  }

  .composer input[type=text] {
    flex: 1;
    padding: 11px 14px;
    font-family: inherit;
    font-size: 0.92rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #fffefb;
    color: var(--ink);
  }

  .composer input[type=text]:focus {
    outline: 2px solid var(--gold);
    outline-offset: 1px;
  }

  .composer button {
    font-family: inherit;
    font-weight: 600;
    font-size: 0.92rem;
    padding: 0 22px;
    border: none;
    border-radius: 8px;
    background: var(--ink);
    color: #fdfcf9;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .composer button:hover { background: var(--ink-soft); }

  footer {
    text-align: center;
    font-size: 0.74rem;
    color: var(--slate);
    padding: 4px 22px 20px;
  }

  @media (max-width: 480px) {
    .msg { max-width: 94%; }
  }
</style>
</head>
<body>
  <div class="app">
    <header>
      <div>
        <h1>GFC Financial Insights</h1>
        <p>AI-powered financial performance assistant</p>
      </div>
      <div class="status">Online</div>
    </header>

    <div class="intro">
      <h2>Financial Analysis Assistant</h2>
      <p>Ask questions about the financial performance of Microsoft, Tesla, and Apple from 2023 to 2025.</p>
      <div class="chips">
        {% for s in suggestions %}
        <button type="button" class="chip" data-q="{{ s }}">{{ s }}</button>
        {% endfor %}
      </div>
    </div>

    <div class="thread" id="thread">
      {{ log_html|safe }}
    </div>

    <form class="composer" method="post" action="/">
      <input type="text" name="q" id="q" placeholder="Ask a financial question..." autofocus required autocomplete="off">
      <button type="submit">Send</button>
    </form>

    <footer>Financial data covers 2023&ndash;2025 and is based on SEC 10-K filings. This prototype is for analytical and educational purposes.</footer>
  </div>

  <script>
    document.querySelectorAll('.chip').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var input = document.getElementById('q');
        input.value = btn.getAttribute('data-q');
        btn.closest('.app').querySelector('form.composer').submit();
      });
    });
    var thread = document.getElementById('thread');
    if (thread) { thread.scrollTop = thread.scrollHeight; }
  </script>
</body>
</html>
"""

# In-memory history so the page can show prior turns (per server process, not per visitor).
history = []


def build_thread_html():
    if not history:
        return (
            '<div class="msg bot">'
            '<div class="label">GFC Assistant</div>'
            f'<div class="bubble">{render_message_text(WELCOME_MESSAGE)}</div>'
            "</div>"
        )
    rows = []
    for q, a in history:
        rows.append(
            '<div class="msg user">'
            f'<div class="bubble">{render_message_text(q)}</div>'
            "</div>"
        )
        rows.append(
            '<div class="msg bot">'
            '<div class="label">GFC Assistant</div>'
            f'<div class="bubble">{render_message_text(a)}</div>'
            "</div>"
        )
    return "".join(rows)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        q = request.form.get("q", "").strip()
        if q:
            answer = simple_chatbot(q, df)
            history.append((q, answer))
    return render_template_string(PAGE, log_html=build_thread_html(), suggestions=SUGGESTIONS)


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
