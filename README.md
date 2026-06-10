# ACKO Insurance AI Platform (InsureX UI)

Premium insurance platform with **InsureX** React frontend (Acko-inspired purple UI), FastAPI backend, AI premium/claim/chatbot services, and management analytics dashboard.

## Quick start

### Backend (modular API — use with React app)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health  
Dashboard data: http://127.0.0.1:8000/dashboard-data

### InsureX React frontend

Requires [Node.js](https://nodejs.org/) (npm included).

```bash
cd client-app
npm install
npm run dev
```

Open http://localhost:5173 (proxies `/api` and `/dashboard-data` to port 8000).

### Production (single server)

```bash
cd client-app && npm install && npm run build
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Default UI:** Previous ACKO blue website in `frontend/` at http://127.0.0.1:8000/

```powershell
.\start-website.ps1
```

**Optional InsureX React UI** (purple, multi-page): build `client-app` then:

```powershell
.\start-insurex.ps1
# or: $env:SERVE_REACT_UI="true"; uvicorn app.main:app --reload
```

### Legacy monolith (optional)

```bash
uvicorn main:app --reload
```

Serves the embedded HTML SPA at http://127.0.0.1:8000/ (cloud-blue theme, separate from InsureX).

## InsureX routes

| Route | Description |
|-------|-------------|
| `/` | Marketing home — hero, product cards |
| `/products/:type` | Product detail (`car`, `bike`, `health`, `travel`) |
| `/about` | About us |
| `/contact` | Get quote form |
| `/login` | Dual-role login (Customer / Management) |
| `/home` | Customer portal (protected) |
| `/dashboard` | Management dashboard with charts (protected) |

**Brand colors:** Primary `#6B4EFF`, surface `#F5F5F5`, white backgrounds.

## Demo logins (InsureX + API)

| Role | Email | Password |
|------|-------|----------|
| Customer | `customer@acko.demo` or `customer@ackoai.com` | `customer123` |
| Admin | `admin@acko.demo` or `admin@ackoai.com` | `admin123` |

- Customer login → `/home`
- Management login → `/dashboard`

## Features

- **Marketing site:** responsive pages, Unsplash imagery, Lucide icons, fade-in animations
- **Customer:** JWT login, policy overview, claims snippet (`GET /api/customer/overview`)
- **Management:** KPI cards, bar/pie/line charts (Recharts), recent claims table (`GET /dashboard-data`)
- **AI:** scikit-learn premium/claims, Gemini FAQ RAG (`faq_engine.py`), chatbot API

## Database

```bash
python create_tables.py
```

## Docker

```bash
docker compose up --build
```
