
# NewsChecker

## News Bias & Fact-Check Platform

NewsChecker is a web application designed to help users explore news articles and, eventually, analyze potential bias and verify claims.

Currently, the platform supports searching for news articles by topic. Machine-learning-based bias analysis and automated fact-checking are planned features.

## Tech Stack

### Frontend
- React
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- Pydantic
- Requests
- Beautiful Soup

### External Services
- NewsAPI for searching related news articles

## Project Structure

```text
NewsChecker/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   └── analysis.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── ml/
│   │   ├── services/
│   │   │   ├── article_fetcher.py
│   │   │   ├── news_search.py
│   │   │   └── text_preprocessor.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── models/
│   ├── tests/
│   ├── .env
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ArticleCard.jsx
│   │   │   └── SearchForm.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   └── package.json
├── .gitignore
└── README.md
```

## Prerequisites

- Python installed
- Node.js and npm installed
- A NewsAPI API key

## Backend Setup

Open a terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` and add your API key:

```text
NEWS_API_KEY=your_api_key_here
```

Start the backend:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Backend API documentation:

http://127.0.0.1:8000/docs

## Frontend Setup

Open a second terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the frontend URL printed by Vite, usually:

http://localhost:5173

## Current API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API welcome message |
| GET | `/health` | Health check |
| POST | `/analyze` | Submit text, URL, or topic for processing |

## Environment Variables and Security

- Never commit `.env` files or real API keys.
- Keep `.env.example` limited to placeholder values.
- Do not commit virtual environments or `node_modules`.

## Planned Features

- News article bias analysis using a trained ML model
- Claim extraction and evidence-based fact-checking
- Article selection and detailed analysis results
- Improved relevance filtering
- Automated tests
