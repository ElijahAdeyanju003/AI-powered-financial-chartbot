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
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    h1 { font-size: 1.4rem; }
    #log { border: 1px solid #ccc; border-radius: 8px; padding: 12px;
           height: 320px; overflow-y: auto; background: #fafafa; }
    .you { color: #0b5; margin: 6px 0; }
    .bot { color: #333; margin: 6px 0; }
    form { display: flex; gap: 8px; margin-top: 12px; }
    input[type=text] { flex: 1; padding: 8px; }
    button { padding: 8px 14px; cursor: pointer; }
    .hint { color: #777; font-size: 0.85rem; margin-top: 8px; }
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
