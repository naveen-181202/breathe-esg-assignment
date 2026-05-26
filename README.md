# Breathe ESG Tech Intern Assignment

Prototype for ingesting SAP fuel/procurement, utility electricity, and corporate travel data into a normalized analyst review queue.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py runserver
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The API runs at `http://127.0.0.1:8000/api/`. The React app runs at the Vite URL shown in the terminal.

## Demo credentials

This prototype does not require login. The model is tenant-aware, but authentication was deliberately left out for the assignment scope; see `TRADEOFFS.md`.

## What to review

- `MODEL.md`: data model and audit strategy
- `DECISIONS.md`: choices and unresolved PM questions
- `SOURCES.md`: real-world source research and sample file rationale
- `TRADEOFFS.md`: what was intentionally not built
