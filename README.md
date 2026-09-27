# Financial Chatbot

A tiny Flask app that answers basic questions about Apple, Microsoft, and
Tesla's financials (FY2023-2025) from `financial_analysis_output.csv`.

## Files

- `app.py` — the Flask app (web page at `/`, JSON API at `/api/chat`)
- `financial_analysis_output.csv` — the data the chatbot reads
- `requirements.txt` — Python dependencies
- `render.yaml` — optional Render "Blueprint" config for one-click setup

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000

## Deploy on Render

1. Push this folder to a GitHub (or GitLab) repo.
2. In the Render dashboard, click **New +** → **Web Service**, and connect
   that repo. (If the repo includes `render.yaml`, you can instead use
   **New +** → **Blueprint** and Render will read the settings automatically.)
3. If configuring manually, set:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Click **Create Web Service**. Render builds and deploys automatically,
   and gives you a public `https://<your-app>.onrender.com` URL.

Render sets the `PORT` environment variable itself; `app.py` already reads
it, and gunicorn binds to it automatically, so no extra config is needed.

## API

`POST /api/chat` with JSON body `{"query": "What is Tesla's total revenue in 2024?"}`
returns `{"query": ..., "answer": ...}`.
