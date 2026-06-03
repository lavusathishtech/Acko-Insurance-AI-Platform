"""
ACKO-Inspired InsurTech Premium Platform
Single-file FastAPI application serving a monolithic Cloud Blue SPA.

Run: uvicorn main:app --reload
"""

from __future__ import annotations

import datetime as dt
from typing import Any, List, Optional

from contextlib import asynccontextmanager
import csv
import io
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from claims_engine import ensure_models, predict_claim
from faq_engine import answer_faq, index_policy_pdfs

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Train/load Module 3 ML models and index policy PDFs for RAG chatbot."""
    ensure_models()
    try:
        count = index_policy_pdfs(force=False)
        print(f"FAQ RAG indexed: {count} chunks from policy PDFs")
    except Exception as exc:
        print(f"FAQ indexing skipped: {exc}")
    yield

app = FastAPI(
    title="ACKO AI InsurTech Platform",
    description="Premium insurance platform with customer portal and management dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

CURRENT_YEAR = dt.date.today().year
NCB_RATE = 0.20
GST_RATE = 0.18


# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------


class PremiumRequest(BaseModel):
    """Payload for premium quote generation."""

    vehicle_type: str = Field(..., description="Car or Bike")
    model_name: str = Field(..., description="Vehicle model name")
    year: int = Field(..., ge=1995, le=CURRENT_YEAR + 1, description="Registration year")
    idv: float = Field(..., gt=0, description="Insured Declared Value in INR")


class PremiumResponse(BaseModel):
    """Structured premium breakdown returned to the client."""

    vehicle_type: str
    model_name: str
    vehicle_age: int
    base_premium: float
    own_damage: float
    ncb_discount: float
    subtotal: float
    gst_18: float
    total_premium: float


class ChatRequest(BaseModel):
    """Chatbot message from the customer."""

    message: str


class ChatResponse(BaseModel):
    """Chatbot reply."""

    reply: str
    source: str = "rule_fallback"


class ClaimsKPI(BaseModel):
    today: int
    this_week: int
    this_month: int


class AvgPayoutKPI(BaseModel):
    car: str
    bike: str


class QuotationsKPI(BaseModel):
    total: int
    avg_premium: str


class KPIBlock(BaseModel):
    total_claims: ClaimsKPI
    avg_payout: AvgPayoutKPI
    approval_rate: str
    quotations: QuotationsKPI


class ChartSeries(BaseModel):
    labels: List[str]
    data: List[int]


class ChartsBlock(BaseModel):
    top_cities: ChartSeries
    historical_trends: ChartSeries


class ChatbotInsight(BaseModel):
    question: str
    hits: int


class EscalationRow(BaseModel):
    id: str
    vehicle: str
    region: str
    payout: str
    fraud_score: str
    justification: str


class TablesBlock(BaseModel):
    chatbot_insights: List[ChatbotInsight]
    escalation_desk: List[EscalationRow]


class DashboardResponse(BaseModel):
    """Full management dashboard payload."""

    kpis: KPIBlock
    charts: ChartsBlock
    tables: TablesBlock


class ClaimAnalysis(BaseModel):
    severity: str
    damage_type: str
    affected_parts: List[str]
    severity_score: int
    parts_count: int
    description: str
    source: str


class ClaimPredictionResponse(BaseModel):
    """Module 3 AI Claims Engine response."""

    claim_id: str
    claim_reference: str
    vehicle_type: str
    model_used: str
    predicted_amount: int
    estimated_amount: int
    approval_probability: float
    approval_percent: float
    fraud_probability: float
    status: str
    analysis: ClaimAnalysis
    vehicle_label: Optional[str] = None
    region: Optional[str] = None


# In-memory claim ledger (demo persistence)
CLAIMS_STORE: list[dict[str, Any]] = []



# ---------------------------------------------------------------------------
# Premium calculation helpers
# ---------------------------------------------------------------------------


def _vehicle_age(year: int) -> int:
    """Compute vehicle age with a floor of zero."""
    return max(0, CURRENT_YEAR - year)


def _age_depreciation_factor(age: int) -> float:
    """Reduce premium as vehicle ages (5% per year, min 55% of base)."""
    return max(0.55, 1.0 - age * 0.05)


def compute_premium(payload: PremiumRequest) -> PremiumResponse:
    """Calculate premium with own-damage, NCB discount, and 18% GST."""
    vtype = payload.vehicle_type.strip().lower()
    base_rate = 0.032 if vtype == "car" else 0.048
    age = _vehicle_age(payload.year)
    age_factor = _age_depreciation_factor(age)

    base_premium = round(payload.idv * base_rate * age_factor, 2)
    own_damage = base_premium
    ncb_discount = round(own_damage * NCB_RATE, 2)
    subtotal = round(own_damage - ncb_discount, 2)
    gst = round(subtotal * GST_RATE, 2)
    total = round(subtotal + gst, 2)

    return PremiumResponse(
        vehicle_type=payload.vehicle_type,
        model_name=payload.model_name,
        vehicle_age=age,
        base_premium=base_premium,
        own_damage=own_damage,
        ncb_discount=ncb_discount,
        subtotal=subtotal,
        gst_18=gst,
        total_premium=total,
    )


def chatbot_reply(message: str) -> tuple[str, str]:
    """PDF RAG + Gemini with rule-based fallback."""
    return answer_faq(message)


def _merge_escalation_rows(base: DashboardResponse) -> list[EscalationRow]:
    """Append live low-approval claims from the session store to escalation desk."""
    rows = list(base.tables.escalation_desk)
    for claim in CLAIMS_STORE:
        if claim.get("approval_percent", 100) < 70 or claim.get("fraud_probability", 0) >= 75:
            rows.insert(
                0,
                EscalationRow(
                    id=claim["claim_id"],
                    vehicle=claim.get("vehicle_label", "Unknown vehicle"),
                    region=claim.get("region", "India"),
                    payout=f"₹ {claim['predicted_amount']:,}",
                    fraud_score=f"{int(claim.get('fraud_probability', 0))}%",
                    justification=claim.get(
                        "justification",
                        "Low approval probability — flagged by Module 3 AI Claims Engine",
                    ),
                ),
            )
    return rows[:12]


def build_dashboard_payload() -> DashboardResponse:
    """Return comprehensive dashboard data for the management center."""
    base = DashboardResponse(
        kpis=KPIBlock(
            total_claims=ClaimsKPI(today=124, this_week=845, this_month=3420),
            avg_payout=AvgPayoutKPI(car="₹ 45,200", bike="₹ 8,400"),
            approval_rate="92.4%",
            quotations=QuotationsKPI(total=15420, avg_premium="₹ 12,500"),
        ),
        charts=ChartsBlock(
            top_cities=ChartSeries(
                labels=["Mumbai", "Bengaluru", "Delhi", "Pune", "Chennai", "Hyderabad"],
                data=[450, 380, 420, 210, 250, 310],
            ),
            historical_trends=ChartSeries(
                labels=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
                data=[1200, 1350, 1100, 1500, 1600, 1450, 1800],
            ),
        ),
        tables=TablesBlock(
            chatbot_insights=[
                ChatbotInsight(question="How to file a claim?", hits=4520),
                ChatbotInsight(question="What is NCB?", hits=3100),
                ChatbotInsight(question="Where is the nearest garage?", hits=2850),
                ChatbotInsight(question="How is IDV calculated?", hits=2400),
                ChatbotInsight(question="What documents are needed for renewal?", hits=1950),
                ChatbotInsight(question="How to renew my car policy?", hits=1820),
                ChatbotInsight(question="Is cashless repair available?", hits=1680),
                ChatbotInsight(question="What is zero depreciation cover?", hits=1540),
                ChatbotInsight(question="How long does claim settlement take?", hits=1410),
                ChatbotInsight(question="Can I transfer NCB to a new vehicle?", hits=1290),
            ],
            escalation_desk=[
                EscalationRow(
                    id="CLM-9823",
                    vehicle="2020 Honda City",
                    region="Delhi",
                    payout="₹ 1,20,000",
                    fraud_score="89%",
                    justification="Suspicious multiple claims in 6 months",
                ),
                EscalationRow(
                    id="CLM-9845",
                    vehicle="2019 Hyundai Creta",
                    region="Mumbai",
                    payout="₹ 85,000",
                    fraud_score="75%",
                    justification="Inconsistent damage report from surveyor",
                ),
                EscalationRow(
                    id="CLM-9867",
                    vehicle="2021 Royal Enfield Classic",
                    region="Bengaluru",
                    payout="₹ 45,000",
                    fraud_score="82%",
                    justification="FIR not filed for theft claim",
                ),
                EscalationRow(
                    id="CLM-9881",
                    vehicle="2018 Maruti Swift",
                    region="Pune",
                    payout="₹ 62,000",
                    fraud_score="91%",
                    justification="Duplicate claim photos detected across policies",
                ),
                EscalationRow(
                    id="CLM-9894",
                    vehicle="2022 Tata Nexon EV",
                    region="Chennai",
                    payout="₹ 1,45,000",
                    fraud_score="68%",
                    justification="Low approval probability — pre-existing damage indicators",
                ),
                EscalationRow(
                    id="CLM-9902",
                    vehicle="2017 Honda Activa",
                    region="Hyderabad",
                    payout="₹ 18,500",
                    fraud_score="77%",
                    justification="Claim filed 48 hours after policy inception",
                ),
                EscalationRow(
                    id="CLM-9915",
                    vehicle="2020 Kia Seltos",
                    region="Kolkata",
                    payout="₹ 95,000",
                    fraud_score="85%",
                    justification="Geolocation mismatch between incident and policy address",
                ),
            ],
        ),
    )
    base.tables.escalation_desk = _merge_escalation_rows(base)
    if CLAIMS_STORE:
        today_extra = min(len(CLAIMS_STORE), 15)
        base.kpis.total_claims.today += today_extra
        base.kpis.total_claims.this_week += today_extra
        base.kpis.total_claims.this_month += len(CLAIMS_STORE)
    return base


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.post("/predict-premium", response_model=PremiumResponse)
async def predict_premium(request: PremiumRequest) -> PremiumResponse:
    """Compute premium breakdown with own-damage, NCB, and GST."""
    return compute_premium(request)


@app.post("/chatbot", response_model=ChatResponse)
async def chatbot(request: ChatRequest) -> ChatResponse:
    """RAG chatbot grounded in ACKO motor, health, and FAQ policy PDFs."""
    reply, source = chatbot_reply(request.message)
    return ChatResponse(reply=reply, source=source)


@app.post("/chatbot/reindex")
async def reindex_chatbot():
    """Force re-index policy PDFs into ChromaDB (admin/dev)."""
    count = index_policy_pdfs(force=True)
    return {"status": "ok", "chunks_indexed": count}


@app.get("/dashboard-data", response_model=DashboardResponse)
async def dashboard_data() -> DashboardResponse:
    """Return KPIs, chart series, and table data for the management dashboard."""
    return build_dashboard_payload()


@app.get("/admin/report")
async def admin_report(type: str = "escalation", format: str = "csv", range: str = "all"):
    """Return a report attachment (escalation, claims, or all data) in CSV or JSON format."""
    payload = build_dashboard_payload()
    
    # Select data based on type
    if type == "recent_claims":
        rows = payload.tables.escalation_desk
        fields = ["id", "vehicle", "region", "payout", "fraud_score", "justification"]
    elif type == "all":
        rows = payload.tables.escalation_desk
        fields = ["id", "vehicle", "region", "payout", "fraud_score", "justification"]
    else:  # escalation (default)
        rows = payload.tables.escalation_desk
        fields = ["id", "vehicle", "region", "payout", "fraud_score", "justification"]

    # Return JSON format
    if format == "json":
        data = [
            {field: getattr(row, field, "") for field in fields}
            for row in rows
        ]
        json_text = json.dumps(data, indent=2)
        headers = {"Content-Disposition": f'attachment; filename="admin_report_{type}.json"'}
        return HTMLResponse(content=json_text, media_type="application/json", headers=headers)
    
    # CSV format (default)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(fields)
    for r in rows:
        writer.writerow([getattr(r, f, "") for f in fields])

    csv_text = stream.getvalue()
    headers = {"Content-Disposition": f'attachment; filename="admin_report_{type}.csv"'}
    return HTMLResponse(content=csv_text, media_type="text/csv", headers=headers)


@app.post("/predict-claim", response_model=ClaimPredictionResponse)
async def predict_claim_endpoint(
    image: UploadFile = File(...),
    vehicle_type: str = Form("Car"),
    model_name: str = Form("Honda City"),
    year: int = Form(2020),
    idv: float = Form(500000),
    incident_date: str = Form(...),
    description: str = Form(""),
    city: str = Form("Bengaluru"),
    policy_type: str = Form("Comprehensive"),
    claim_history: int = Form(0),
    ncb: int = Form(20),
) -> ClaimPredictionResponse:
    """Module 3 pipeline: vision analysis + routed ML amount & approval prediction."""
    image_bytes = await image.read()
    age = max(0, CURRENT_YEAR - year)
    form_data = {
        "vehicle_type": vehicle_type.lower(),
        "idv": idv,
        "vehicle_age_years": age,
        "incident_date": incident_date,
        "policy_type": policy_type,
        "claim_history_count": claim_history,
        "ncb_percent": ncb,
    }
    result = predict_claim(image_bytes, form_data, description)
    vehicle_label = f"{year} {model_name}"
    justification = (
        f"AI severity: {result['analysis']['severity']}; "
        f"approval {result['approval_percent']}%"
    )
    record = {
        **result,
        "vehicle_label": vehicle_label,
        "region": city,
        "justification": justification,
        "created_at": dt.datetime.now().isoformat(),
    }
    CLAIMS_STORE.insert(0, record)

    return ClaimPredictionResponse(
        claim_id=result["claim_id"],
        claim_reference=result["claim_reference"],
        vehicle_type=result["vehicle_type"],
        model_used=result["model_used"],
        predicted_amount=result["predicted_amount"],
        estimated_amount=result["estimated_amount"],
        approval_probability=result["approval_probability"],
        approval_percent=result["approval_percent"],
        fraud_probability=result["fraud_probability"],
        status=result["status"],
        analysis=ClaimAnalysis(**result["analysis"]),
        vehicle_label=vehicle_label,
        region=city,
    )


@app.get("/api/customer/overview")
async def customer_overview() -> dict[str, Any]:
    """Customer dashboard cards, recent claims, and chart series."""
    recent = CLAIMS_STORE[:5]
    statuses = [c.get("status", "Under Review") for c in CLAIMS_STORE]
    approved = sum(1 for s in statuses if s == "Approved")
    total = len(CLAIMS_STORE) or 1
    return {
        "stats": {
            "active_policies": 2,
            "claims_filed": len(CLAIMS_STORE),
            "approval_rate": round((approved / total) * 100, 1) if CLAIMS_STORE else 92.4,
            "avg_payout": int(
                sum(c.get("predicted_amount", 0) for c in CLAIMS_STORE) / max(len(CLAIMS_STORE), 1)
            )
            if CLAIMS_STORE
            else 0,
        },
        "recent_claims": [
            {
                "claim_id": c["claim_id"],
                "vehicle": c.get("vehicle_label", "Vehicle"),
                "amount": c["predicted_amount"],
                "status": c["status"],
                "approval_percent": c["approval_percent"],
            }
            for c in recent
        ],
        "claim_trend": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "data": [2, 4, 3, len(CLAIMS_STORE) + 1, 5, 3, 4],
        },
    }


@app.get("/health")
async def health():
    """Health check for deployment probes."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Monolithic frontend (HTML + Tailwind CDN + Chart.js + vanilla JS)
# ---------------------------------------------------------------------------

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACKO AI — India's Smart Insurance Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['"Plus Jakarta Sans"', 'sans-serif'] },
                    colors: {
                        cloud: { light: '#bae6fd', DEFAULT: '#0077ff', dark: '#0099ff' }
                    }
                }
            }
        };
    </script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            background:
                radial-gradient(ellipse at 20% 0%, rgba(0, 153, 255, 0.12) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(6, 182, 212, 0.10) 0%, transparent 45%),
                linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #bae6fd 100%);
            background-attachment: fixed;
            min-height: 100vh;
            color: #1e293b;
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
            border-radius: 20px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .glass-card:hover { transform: translateY(-2px); box-shadow: 0 16px 40px rgba(0, 119, 255, 0.08); }
        .glass-input {
            background: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.8);
            transition: all 0.3s ease;
        }
        .glass-input:focus {
            background: rgba(255, 255, 255, 0.9);
            border-color: #0077ff;
            box-shadow: 0 0 0 3px rgba(0, 119, 255, 0.2);
            outline: none;
        }
        .glass-input:focus-visible { outline: 2px solid #0077ff; outline-offset: 2px; }
        .btn-primary {
            background: linear-gradient(135deg, #0077ff 0%, #0099ff 50%, #06b6d4 100%);
            color: white;
            transition: all 0.3s ease;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0, 119, 255, 0.3); }
        .btn-primary:focus-visible { outline: 2px solid #0077ff; outline-offset: 3px; }
        .hidden { display: none !important; }
        #chat-history::-webkit-scrollbar { width: 6px; }
        #chat-history::-webkit-scrollbar-thumb { background: rgba(0, 119, 255, 0.3); border-radius: 10px; }
        .fade-in { animation: fadeIn 0.45s ease forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .approval-ring {
            width: 7rem; height: 7rem; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: white;
            position: relative;
        }
        .approval-ring::before {
            content: '';
            position: absolute; inset: -4px; border-radius: 50%;
            background: conic-gradient(#22c55e var(--pct, 0%), #e2e8f0 0);
            z-index: 0;
        }
        .approval-ring-inner {
            width: calc(100% - 12px); height: calc(100% - 12px);
            border-radius: 50%; background: rgba(255,255,255,0.9);
            display: flex; align-items: center; justify-content: center;
            position: relative; z-index: 1;
        }
        .typing-dots span {
            display: inline-block; width: 6px; height: 6px; margin: 0 2px;
            background: rgba(255,255,255,0.8); border-radius: 50%;
            animation: bounce 1.2s infinite;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 80%, 100% { transform: translateY(0); } 40% { transform: translateY(-6px); } }
        .product-card { cursor: pointer; }
        .product-card:hover { border-color: rgba(0, 119, 255, 0.4); }
        .login-hub { background: rgba(255,255,255,0.35); backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.65); border-radius: 28px; padding: 2rem; box-shadow: 0 24px 80px rgba(0,119,255,0.12); }
        .hero-visual { border-radius: 24px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,119,255,0.15); }
        .hero-visual img { width: 100%; height: 280px; object-fit: cover; }
        .tab-btn { padding: 0.65rem 1.25rem; border-radius: 12px; font-weight: 600; font-size: 0.875rem; color: #64748b; transition: all 0.25s ease; }
        .tab-btn.active { background: linear-gradient(135deg, #0077ff, #06b6d4); color: white; box-shadow: 0 8px 20px rgba(0,119,255,0.25); }
        .tab-panel { display: none; animation: fadeIn 0.4s ease; }
        .tab-panel.active { display: block; }
        .stat-card { background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(255,255,255,0.4)); border: 1px solid rgba(255,255,255,0.8); border-radius: 16px; padding: 1.25rem; }
        .upload-zone { border: 2px dashed rgba(0,119,255,0.35); border-radius: 16px; padding: 2rem; text-align: center; transition: all 0.3s; cursor: pointer; background: rgba(255,255,255,0.3); }
        .upload-zone:hover { border-color: #0077ff; background: rgba(0,119,255,0.05); }
        .claim-preview-img { max-height: 220px; border-radius: 12px; object-fit: cover; width: 100%; }
        .tracker-step { flex: 1; text-align: center; position: relative; }
        .tracker-step .dot { width: 2rem; height: 2rem; border-radius: 50%; background: #e2e8f0; margin: 0 auto 0.5rem; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; transition: all 0.4s; }
        .tracker-step.done .dot { background: linear-gradient(135deg, #22c55e, #16a34a); color: white; }
        .tracker-step.active .dot { background: linear-gradient(135deg, #0077ff, #06b6d4); color: white; box-shadow: 0 0 0 4px rgba(0,119,255,0.2); animation: pulse 1.5s infinite; }
        .tracker-step::after { content: ''; position: absolute; top: 1rem; left: 55%; width: 90%; height: 2px; background: #e2e8f0; z-index: -1; }
        .tracker-step:last-child::after { display: none; }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
        .float-badge { animation: float 4s ease-in-out infinite; }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        .shimmer { background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
    </style>
</head>
<body class="antialiased font-sans">

<div id="app" class="container mx-auto px-4 py-6 max-w-7xl">
    <!-- Global header -->
    <header class="flex justify-between items-center mb-8 glass-card px-6 py-4 fade-in">
        <div class="text-2xl font-bold text-cloud flex items-center gap-2 cursor-pointer" onclick="goHome()">
            <i class="fa-solid fa-shield-halved"></i> ACKO<span class="text-slate-800">AI</span>
        </div>
        <nav id="header-nav" class="hidden lg:flex items-center gap-6 text-sm font-semibold text-slate-600">
            <a href="#products" class="hover:text-cloud transition-colors">Products</a>
            <a href="#products" class="hover:text-cloud transition-colors">Claims</a>
            <a href="#login-section" class="hover:text-cloud transition-colors">Renew</a>
            <a href="#login-section" class="hover:text-cloud transition-colors px-4 py-2 rounded-full border border-cloud/30 text-cloud">Login</a>
        </nav>
        <button id="logout-btn" class="hidden text-sm font-semibold text-cloud hover:text-cloud-dark transition-colors px-4 py-2 rounded-xl border border-cloud/30" onclick="logout()">
            <i class="fa-solid fa-right-from-bracket mr-1"></i> Logout
        </button>
    </header>

    <!-- ========== AUTH / LANDING VIEW ========== -->
    <div id="auth-view">

        <!-- ACKO-inspired hero with visual -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center mb-16 fade-in">
            <div class="text-center lg:text-left">
            <div class="inline-flex items-center gap-2 bg-white/50 backdrop-blur px-4 py-2 rounded-full text-sm font-semibold text-cloud mb-6 border border-white/60">
                <i class="fa-solid fa-award"></i> India's #1 insurance app · Best direct insurer 2025
            </div>
            <h1 class="text-4xl md:text-5xl font-extrabold text-slate-900 mb-4 leading-tight">
                Have an award-winning insurer<br><span class="text-cloud">by your side</span>
            </h1>
            <p class="text-lg text-slate-500 max-w-2xl mx-auto mb-8">
                Simple prices. Super fast claims. AI-powered quotes and policy assistance — no brokers, no hidden fees.
            </p>
            <div class="flex flex-wrap justify-center gap-6 md:gap-12 mb-10">
                <div class="text-center"><div class="text-2xl font-bold text-cloud">7 mins</div><div class="text-sm text-slate-500">Fastest claim settlement</div></div>
                <div class="text-center"><div class="text-2xl font-bold text-cloud">98.8%</div><div class="text-sm text-slate-500">Claims settled in 1 week</div></div>
                <div class="text-center"><div class="text-2xl font-bold text-cloud">24×7</div><div class="text-sm text-slate-500">Instant claims support</div></div>
            </div>
            <button type="button" onclick="scrollToLogin()" class="btn-primary px-8 py-3 rounded-xl font-semibold text-lg">
                Get started <i class="fa-solid fa-arrow-down ml-2"></i>
            </button>
            </div>
            <div class="hero-visual relative">
                <img src="https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=900&q=80" alt="Modern insurance protection" loading="lazy">
                <div class="absolute bottom-4 left-4 glass-card px-4 py-3 float-badge text-left">
                    <div class="text-xs text-slate-500">AI Claims Engine</div>
                    <div class="font-bold text-cloud">60 sec triage</div>
                </div>
            </div>
        </section>

        <!-- Product rail -->
        <section id="products" class="mb-16 fade-in">
            <h2 class="text-2xl font-bold text-center mb-8">Select your protection</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                <div class="glass-card product-card p-5" onclick="scrollToLogin()">
                    <i class="fa-solid fa-car text-2xl text-cloud mb-3"></i>
                    <h3 class="font-bold mb-1">Car insurance</h3>
                    <p class="text-xs text-slate-500 mb-3">Simple prices. Fast claims.</p>
                    <span class="text-xs font-semibold text-cloud">From ₹2,094*</span>
                </div>
                <div class="glass-card product-card p-5" onclick="scrollToLogin()">
                    <i class="fa-solid fa-motorcycle text-2xl text-cloud mb-3"></i>
                    <h3 class="font-bold mb-1">Bike insurance</h3>
                    <p class="text-xs text-slate-500 mb-3">Insure in just 1 minute.</p>
                    <span class="text-xs font-semibold text-cloud">Quick quote</span>
                </div>
                <div class="glass-card product-card p-5" onclick="scrollToLogin()">
                    <i class="fa-solid fa-heart-pulse text-2xl text-cloud mb-3"></i>
                    <h3 class="font-bold mb-1">Health insurance</h3>
                    <p class="text-xs text-slate-500 mb-3">100% hospital bill payments.</p>
                    <span class="text-xs font-semibold text-cloud">From ₹600/mo</span>
                </div>
                <div class="glass-card product-card p-5" onclick="scrollToLogin()">
                    <i class="fa-solid fa-user-shield text-2xl text-cloud mb-3"></i>
                    <h3 class="font-bold mb-1">Life insurance</h3>
                    <p class="text-xs text-slate-500 mb-3">100% pure term cover.</p>
                    <span class="text-xs font-semibold text-cloud">₹25L – ₹100Cr</span>
                </div>
                <div class="glass-card product-card p-5" onclick="scrollToLogin()">
                    <i class="fa-solid fa-plane text-2xl text-cloud mb-3"></i>
                    <h3 class="font-bold mb-1">Travel insurance</h3>
                    <p class="text-xs text-slate-500 mb-3">150+ countries covered.</p>
                    <span class="text-xs font-semibold text-cloud">Schengen ready</span>
                </div>
            </div>
        </section>

        <!-- Testimonials -->
        <section class="mb-16 fade-in">
            <h2 class="text-2xl font-bold text-center mb-2">Promises made. Promises kept.</h2>
            <p class="text-center text-slate-500 mb-8">Stories that speak for ACKO</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="glass-card p-6">
                    <div class="text-amber-400 mb-3"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                    <p class="text-sm text-slate-600 mb-4">"Got my car quote and completed payment within 2 minutes. The UI is clean and does not push hidden add-ons."</p>
                    <strong class="text-sm">Rohan Deshmukh</strong><span class="text-xs text-slate-400 block">ACKO customer, Mumbai</span>
                </div>
                <div class="glass-card p-6">
                    <div class="text-amber-400 mb-3"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                    <p class="text-sm text-slate-600 mb-4">"Submitted a bumper scrape photo at 11 AM. The AI evaluated damage instantly. Zero hassles."</p>
                    <strong class="text-sm">Ananya Sen</strong><span class="text-xs text-slate-400 block">ACKO car insurance, Bengaluru</span>
                </div>
                <div class="glass-card p-6">
                    <div class="text-amber-400 mb-3"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                    <p class="text-sm text-slate-600 mb-4">"Asked about NCB balance. Got policy clause details instantly. Fantastic experience."</p>
                    <strong class="text-sm">Harish Kumar</strong><span class="text-xs text-slate-400 block">ACKO health insurance, Chennai</span>
                </div>
            </div>
        </section>

        <!-- Unified login hub -->
        <section id="login-section" class="login-hub mb-16 fade-in max-w-4xl mx-auto">
            <div class="text-center mb-8">
                <h2 class="text-2xl font-bold">Sign in to your workspace</h2>
                <p class="text-slate-500 mt-2">Choose Customer Portal or Management Control Center</p>
            </div>
            <div class="flex flex-col md:flex-row gap-8 justify-center items-stretch">
            <div class="glass-card p-8 flex-1 w-full relative overflow-hidden">
                <div class="absolute -left-10 -top-10 w-32 h-32 bg-cyan-400/20 rounded-full blur-2xl"></div>
                <h2 class="text-2xl font-bold mb-2">Customer Portal</h2>
                <p class="text-slate-500 mb-6">Manage policies, get quotes, and chat with AI assistance.</p>
                <form onsubmit="login(event, 'customer')">
                    <input type="email" id="c-email" value="customer@ackoai.com" class="glass-input w-full px-4 py-3 rounded-xl mb-4" required placeholder="customer@ackoai.com">
                    <input type="password" id="c-pass" value="customer123" class="glass-input w-full px-4 py-3 rounded-xl mb-6" required placeholder="customer123">
                    <button type="submit" class="btn-primary w-full py-3 rounded-xl font-semibold">Login as Customer</button>
                </form>
            </div>
            <div class="glass-card p-8 flex-1 w-full relative overflow-hidden">
                <div class="absolute -right-10 -top-10 w-32 h-32 bg-cloud/20 rounded-full blur-2xl"></div>
                <h2 class="text-2xl font-bold mb-2">Management Control Center</h2>
                <p class="text-slate-500 mb-6">Real-time KPIs, charts, and risk escalation desk.</p>
                <form onsubmit="login(event, 'admin')">
                    <input type="email" id="a-email" value="admin@ackoai.com" class="glass-input w-full px-4 py-3 rounded-xl mb-4" required placeholder="admin@ackoai.com">
                    <input type="password" id="a-pass" value="admin123" class="glass-input w-full px-4 py-3 rounded-xl mb-6" required placeholder="admin123">
                    <button type="submit" class="btn-primary w-full py-3 rounded-xl font-semibold">Login as Manager</button>
                </form>
            </div>
            </div>
        </section>

        <!-- Footer -->
        <footer id="landing-footer" class="glass-card p-8 mb-8 fade-in">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
                <div>
                    <h6 class="font-bold uppercase text-xs mb-3 text-slate-400">Products</h6>
                    <ul class="space-y-2 text-slate-600">
                        <li><a href="#products" class="hover:text-cloud">Car insurance</a></li>
                        <li><a href="#products" class="hover:text-cloud">Bike insurance</a></li>
                        <li><a href="#products" class="hover:text-cloud">Health insurance</a></li>
                    </ul>
                </div>
                <div>
                    <h6 class="font-bold uppercase text-xs mb-3 text-slate-400">Company</h6>
                    <ul class="space-y-2 text-slate-600">
                        <li><a href="#" class="hover:text-cloud">About us</a></li>
                        <li><a href="#" class="hover:text-cloud">Careers</a></li>
                        <li><a href="#" class="hover:text-cloud">Contact</a></li>
                    </ul>
                </div>
                <div>
                    <h6 class="font-bold uppercase text-xs mb-3 text-slate-400">Support</h6>
                    <ul class="space-y-2 text-slate-600">
                        <li><a href="#" class="hover:text-cloud">File a claim</a></li>
                        <li><a href="#" class="hover:text-cloud">Track a claim</a></li>
                        <li><a href="#" class="hover:text-cloud">Renew policy</a></li>
                    </ul>
                </div>
                <div>
                    <h6 class="font-bold uppercase text-xs mb-3 text-slate-400">Legal</h6>
                    <ul class="space-y-2 text-slate-600">
                        <li><a href="#" class="hover:text-cloud">Privacy policy</a></li>
                        <li><a href="#" class="hover:text-cloud">Terms & conditions</a></li>
                    </ul>
                </div>
            </div>
            <p class="text-xs text-slate-400 mt-8 pt-6 border-t border-white/50">© 2026 ACKO AI Platform. CIN: U74110KA2016PTC120161</p>
        </footer>
    </div>

    <!-- ========== CUSTOMER MODULE ========== -->
    <div id="customer-view" class="hidden space-y-6">
        <div class="glass-card p-4 flex flex-wrap gap-2" id="customer-tabs">
            <button type="button" class="tab-btn active" data-tab="overview" onclick="switchCustomerTab('overview')"><i class="fa-solid fa-grid-2 mr-1"></i> Overview</button>
            <button type="button" class="tab-btn" data-tab="premium" onclick="switchCustomerTab('premium')"><i class="fa-solid fa-calculator mr-1"></i> Premium Predictor</button>
            <button type="button" class="tab-btn" data-tab="chatbot" onclick="switchCustomerTab('chatbot')"><i class="fa-solid fa-robot mr-1"></i> AI Chatbot</button>
            <button type="button" class="tab-btn" data-tab="claims" onclick="switchCustomerTab('claims')"><i class="fa-solid fa-camera mr-1"></i> AI Claims Engine</button>
        </div>

        <!-- Overview tab -->
        <div id="tab-overview" class="tab-panel active space-y-6">
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="stat-card"><div class="text-xs text-slate-500 uppercase font-semibold">Active Policies</div><div class="text-2xl font-bold text-cloud mt-1" id="st-policies">2</div></div>
                <div class="stat-card"><div class="text-xs text-slate-500 uppercase font-semibold">Claims Filed</div><div class="text-2xl font-bold text-cloud mt-1" id="st-claims">0</div></div>
                <div class="stat-card"><div class="text-xs text-slate-500 uppercase font-semibold">Approval Rate</div><div class="text-2xl font-bold text-green-600 mt-1" id="st-approval">92%</div></div>
                <div class="stat-card"><div class="text-xs text-slate-500 uppercase font-semibold">Avg Payout</div><div class="text-2xl font-bold mt-1" id="st-payout">₹ 0</div></div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="glass-card p-6">
                    <h3 class="font-bold mb-4">Claim activity</h3>
                    <div class="h-48"><canvas id="customerChart"></canvas></div>
                </div>
                <div class="glass-card p-6">
                    <h3 class="font-bold mb-4">Recent claims</h3>
                    <div id="recent-claims-list" class="space-y-3 text-sm text-slate-500">No claims yet. Use AI Claims Engine to file one.</div>
                </div>
            </div>
            <div class="glass-card p-6">
                <h3 class="font-bold mb-6">Claim status tracker</h3>
                <div class="flex gap-2" id="claim-tracker">
                    <div class="tracker-step done"><div class="dot"><i class="fa-solid fa-check text-xs"></i></div><span class="text-xs font-medium">Submitted</span></div>
                    <div class="tracker-step active"><div class="dot">2</div><span class="text-xs font-medium">AI Analysis</span></div>
                    <div class="tracker-step"><div class="dot">3</div><span class="text-xs font-medium">Review</span></div>
                    <div class="tracker-step"><div class="dot">4</div><span class="text-xs font-medium">Settlement</span></div>
                </div>
            </div>
        </div>

        <!-- Premium tab -->
        <div id="tab-premium" class="tab-panel">
        <div class="glass-card p-8 max-w-2xl mx-auto">
            <h3 class="text-xl font-bold mb-2 flex items-center gap-2"><i class="fa-solid fa-calculator text-cloud"></i> Premium Calculator</h3>
            <p class="text-sm text-slate-500 mb-6">Instant AI-powered quotes for car and bike policies.</p>
            <form id="premium-form" onsubmit="calculatePremium(event)">
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Vehicle Type</label>
                    <select id="v-type" class="glass-input w-full px-4 py-3 rounded-xl">
                        <option value="Car">Car</option>
                        <option value="Bike">Bike</option>
                    </select>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Model Name</label>
                    <input type="text" id="v-model" class="glass-input w-full px-4 py-3 rounded-xl" placeholder="e.g. Honda City" required>
                </div>
                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div>
                        <label class="block text-sm font-medium mb-1">Registration Year</label>
                        <input type="number" id="v-year" class="glass-input w-full px-4 py-3 rounded-xl" min="1995" max="2026" value="2020" required>
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">IDV (₹)</label>
                        <input type="number" id="v-idv" class="glass-input w-full px-4 py-3 rounded-xl" value="500000" required>
                    </div>
                </div>
                <button type="submit" class="btn-primary w-full py-3 rounded-xl font-semibold flex justify-center items-center gap-2">
                    <span id="calc-text">Generate Quote</span>
                    <i id="calc-spinner" class="fa-solid fa-spinner fa-spin hidden"></i>
                </button>
            </form>
            <div id="quote-result" class="hidden mt-8 p-6 bg-white/50 rounded-xl border border-white fade-in">
                <div class="flex justify-between items-start mb-4 border-b border-slate-200 pb-3">
                    <div>
                        <h4 class="font-bold text-lg">Premium Quote Invoice</h4>
                        <p id="q-header" class="text-sm text-slate-500 mt-1"></p>
                    </div>
                    <span class="text-xs bg-cloud/10 text-cloud px-2 py-1 rounded-lg font-semibold">ACKO AI</span>
                </div>
                <div class="flex justify-between mb-2 text-sm"><span class="text-slate-500">Base Premium</span><span id="q-base" class="font-medium"></span></div>
                <div class="flex justify-between mb-2 text-sm"><span class="text-slate-500">Own Damage</span><span id="q-od" class="font-medium"></span></div>
                <div class="flex justify-between mb-2 text-sm"><span class="text-slate-500">NCB Discount (20%)</span><span id="q-ncb" class="text-green-600 font-medium"></span></div>
                <div class="flex justify-between mb-2 text-sm"><span class="text-slate-500">Subtotal</span><span id="q-sub" class="font-medium"></span></div>
                <div class="flex justify-between mb-4 text-sm"><span class="text-slate-500">GST (18%)</span><span id="q-gst" class="font-medium"></span></div>
                <div class="flex justify-between items-center pt-4 border-t border-slate-200">
                    <span class="font-bold">Total Premium</span>
                    <span id="q-total" class="text-2xl font-bold text-cloud"></span>
                </div>
            </div>
        </div>
        </div>

        <!-- Chatbot tab -->
        <div id="tab-chatbot" class="tab-panel">
        <div class="glass-card p-0 flex flex-col h-[620px] overflow-hidden max-w-3xl mx-auto">
            <div class="p-6 border-b border-white/60 bg-white/30">
                <h3 class="text-xl font-bold flex items-center gap-2"><i class="fa-solid fa-robot text-cloud"></i> AI Virtual Policy Chatbot</h3>
                <p class="text-sm text-slate-500">Motor · Health · FAQ policy PDFs · Powered by Gemini RAG</p>
            </div>
            <div id="chat-history" class="flex-1 p-6 overflow-y-auto flex flex-col gap-3"></div>
                <div class="p-4 border-t border-white/60 bg-white/30">
                    <div class="flex flex-wrap gap-2 mb-3 px-1">
                        <button type="button" class="text-xs px-3 py-1 rounded-full bg-white/60 hover:bg-cloud/10 border border-white" onclick="askPrompt('What is NCB in motor insurance?')">NCB</button>
                        <button type="button" class="text-xs px-3 py-1 rounded-full bg-white/60 hover:bg-cloud/10 border border-white" onclick="askPrompt('What is waiting period in health insurance?')">Health waiting period</button>
                        <button type="button" class="text-xs px-3 py-1 rounded-full bg-white/60 hover:bg-cloud/10 border border-white" onclick="askPrompt('How do I file a motor insurance claim?')">File claim</button>
                        <button type="button" class="text-xs px-3 py-1 rounded-full bg-white/60 hover:bg-cloud/10 border border-white" onclick="askPrompt('What is IDV?')">IDV</button>
                    </div>
                    <form onsubmit="sendMessage(event)" class="flex gap-2">
                    <input type="text" id="chat-input" class="glass-input flex-1 px-4 py-3 rounded-xl" placeholder="Type your insurance question..." required>
                    <button type="submit" class="btn-primary w-12 h-12 rounded-xl flex items-center justify-center" aria-label="Send"><i class="fa-solid fa-paper-plane"></i></button>
                </form>
            </div>
        </div>
        </div>

        <!-- AI Claims Engine tab (Module 3) -->
        <div id="tab-claims" class="tab-panel">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="glass-card p-8">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs font-bold uppercase tracking-wide text-cloud bg-cloud/10 px-2 py-1 rounded">Module 3</span>
                        <h3 class="text-xl font-bold">AI Claims Engine</h3>
                    </div>
                    <p class="text-sm text-slate-500 mb-6">Powered by Module 3: Gradient Boosting regressors &amp; classifiers trained on synthetic claim data, with optional Gemini Vision for photo triage.</p>
                    <form id="claim-form" onsubmit="submitClaim(event)">
                        <label class="upload-zone block mb-4" for="claim-image">
                            <input type="file" id="claim-image" name="image" accept="image/*" class="hidden" required onchange="previewClaimImage(event)">
                            <i class="fa-solid fa-cloud-arrow-up text-3xl text-cloud mb-2"></i>
                            <p class="font-semibold">Upload vehicle damage photo</p>
                            <p class="text-xs text-slate-500 mt-1">JPG, PNG or WEBP</p>
                        </label>
                        <img id="claim-preview" class="claim-preview-img hidden mb-4" alt="Damage preview">
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <div><label class="text-sm font-medium">Vehicle Type</label>
                                <select id="c-vtype" class="glass-input w-full px-3 py-2 rounded-xl mt-1"><option>Car</option><option>Bike</option></select></div>
                            <div><label class="text-sm font-medium">Model</label>
                                <input type="text" id="c-model" class="glass-input w-full px-3 py-2 rounded-xl mt-1" value="Honda City" required></div>
                            <div><label class="text-sm font-medium">Year</label>
                                <input type="number" id="c-year" class="glass-input w-full px-3 py-2 rounded-xl mt-1" value="2020" min="1995" max="2026"></div>
                            <div><label class="text-sm font-medium">IDV (₹)</label>
                                <input type="number" id="c-idv" class="glass-input w-full px-3 py-2 rounded-xl mt-1" value="500000"></div>
                            <div><label class="text-sm font-medium">Incident Date</label>
                                <input type="date" id="c-incident" class="glass-input w-full px-3 py-2 rounded-xl mt-1" required></div>
                            <div><label class="text-sm font-medium">City</label>
                                <input type="text" id="c-city" class="glass-input w-full px-3 py-2 rounded-xl mt-1" value="Bengaluru"></div>
                        </div>
                        <div class="mb-4"><label class="text-sm font-medium">Damage description</label>
                            <textarea id="c-desc" rows="3" class="glass-input w-full px-3 py-2 rounded-xl mt-1" placeholder="e.g. Front bumper dent and cracked headlight after parking impact."></textarea></div>
                        <button type="submit" class="btn-primary w-full py-3 rounded-xl font-semibold flex justify-center gap-2">
                            <span id="claim-btn-text">Analyse & Predict Claim</span>
                            <i id="claim-spinner" class="fa-solid fa-spinner fa-spin hidden"></i>
                        </button>
                    </form>
                </div>
                <div class="space-y-6">
                    <div id="claim-result" class="glass-card p-6 hidden fade-in">
                        <h4 class="font-bold text-lg mb-4 flex items-center gap-2"><i class="fa-solid fa-file-invoice text-cloud"></i> AI Claim Decision</h4>
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <div class="stat-card text-center"><div class="text-xs text-slate-500">Estimated Payout</div><div class="text-xl font-bold text-cloud" id="cr-amount">-</div></div>
                            <div class="stat-card text-center"><div class="text-xs text-slate-500">Approval Probability</div><div class="text-xl font-bold text-green-600" id="cr-approval">-</div></div>
                        </div>
                        <div class="mb-3 flex justify-between text-sm"><span>Claim ID</span><strong id="cr-id">-</strong></div>
                        <div class="mb-3 flex justify-between text-sm"><span>Status</span><span id="cr-status" class="font-semibold px-2 py-1 rounded-lg bg-green-100 text-green-700">-</span></div>
                        <div class="mb-3 flex justify-between text-sm"><span>ML Models</span><span id="cr-model" class="text-slate-600 text-xs">-</span></div>
                        <div class="mb-3 flex justify-between text-sm"><span>Fraud Risk</span><span id="cr-fraud" class="font-bold">-</span></div>
                        <div class="p-4 bg-white/50 rounded-xl text-sm">
                            <div class="font-semibold mb-2">Damage analysis</div>
                            <p id="cr-analysis" class="text-slate-600"></p>
                            <p class="text-xs text-slate-400 mt-2" id="cr-parts"></p>
                        </div>
                    </div>
                    <div class="glass-card p-6">
                        <img src="https://images.unsplash.com/photo-1625047509248-ec889c63d437?w=600&q=80" alt="Vehicle insurance" class="rounded-xl w-full h-40 object-cover mb-3">
                        <p class="text-sm text-slate-600"><strong>Powered by Module 3:</strong> Gradient Boosting regressors & classifiers trained on synthetic claim data, with optional Gemini Vision for photo triage.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ========== ADMIN / MANAGEMENT MODULE ========== -->
    <div id="admin-view" class="hidden space-y-8">
        <div class="glass-card px-6 py-4">
            <h2 class="text-xl font-bold">Management Command Dashboard</h2>
            <p class="text-sm text-slate-500">Live KPIs, analytics, and human risk escalation desk</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="glass-card p-6 relative overflow-hidden">
                <div class="text-sm font-medium text-slate-500 mb-1">Total Claims Submitted</div>
                <div class="text-3xl font-bold mb-4 text-slate-800" id="kpi-claims-total">-</div>
                <div class="flex flex-wrap gap-2 text-xs">
                    <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded-md">Today: <span id="kpi-claims-today" class="font-bold">-</span></span>
                    <span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded-md">Week: <span id="kpi-claims-week" class="font-bold">-</span></span>
                    <span class="bg-violet-100 text-violet-800 px-2 py-1 rounded-md">Month: <span id="kpi-claims-month" class="font-bold">-</span></span>
                </div>
                <i class="fa-solid fa-file-invoice absolute right-4 bottom-4 text-4xl text-slate-200"></i>
            </div>
            <div class="glass-card p-6">
                <div class="text-sm font-medium text-slate-500 mb-2">Avg Predicted Claim Payout</div>
                <div class="flex flex-col gap-3 mt-4">
                    <div class="flex justify-between items-center bg-white/40 px-3 py-2 rounded-lg">
                        <span class="text-sm flex items-center gap-2"><i class="fa-solid fa-car text-cloud"></i> Cars</span>
                        <span class="font-bold" id="kpi-payout-car">-</span>
                    </div>
                    <div class="flex justify-between items-center bg-white/40 px-3 py-2 rounded-lg">
                        <span class="text-sm flex items-center gap-2"><i class="fa-solid fa-motorcycle text-cloud"></i> Bikes</span>
                        <span class="font-bold" id="kpi-payout-bike">-</span>
                    </div>
                </div>
            </div>
            <div class="glass-card p-6 flex flex-col items-center justify-center">
                <div class="text-sm font-medium text-slate-500 mb-4 w-full text-center">Claim Approval Rate</div>
                <div class="approval-ring" id="approval-ring">
                    <div class="approval-ring-inner">
                        <span class="text-xl font-bold text-green-600" id="kpi-approval">-</span>
                    </div>
                </div>
            </div>
            <div class="glass-card p-6">
                <div class="text-sm font-medium text-slate-500 mb-1">Quotations Analytics</div>
                <div class="text-4xl font-bold mb-3 text-cloud" id="kpi-quotes-total">-</div>
                <div class="text-sm text-slate-500 bg-white/40 p-2 rounded-lg">
                    Avg Premium Quoted: <span class="font-bold text-slate-800 float-right" id="kpi-quotes-avg">-</span>
                </div>
            </div>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="glass-card p-6">
                <h3 class="font-bold mb-4">Top Cities by Claim Volume</h3>
                <div class="w-full h-64"><canvas id="barChart"></canvas></div>
            </div>
            <div class="glass-card p-6">
                <h3 class="font-bold mb-4">Claim Ingestion Trends</h3>
                <div class="w-full h-64"><canvas id="lineChart"></canvas></div>
            </div>
        </div>
        <div class="grid grid-cols-1 gap-6">
            <div class="glass-card p-6">
                <h3 class="font-bold mb-4">Claims 4D Overview</h3>
                <p class="text-xs text-slate-400 mb-3">Bubble: X = Payout, Y = Approval %, Size = Severity, Color = Fraud Risk</p>
                <div class="w-full h-80"><canvas id="bubbleChart"></canvas></div>
            </div>
        </div>
        <div class="grid grid-cols-1 gap-6">
            <div class="glass-card p-6">
                <h3 class="font-bold mb-4 text-blue-300"><i class="fa-solid fa-file-export"></i> Generate & Download Report</h3>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                        <label class="text-xs font-bold text-slate-400 block mb-2">Report Type</label>
                        <select id="report-type-select" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm">
                            <option value="escalation">Escalation Desk (Fraud Risk)</option>
                            <option value="recent_claims">Recent Claims</option>
                            <option value="all">All Data</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs font-bold text-slate-400 block mb-2">Format</label>
                        <select id="report-format-select" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm">
                            <option value="csv">CSV (Excel)</option>
                            <option value="json">JSON (Data)</option>
                        </select>
                    </div>
                    <div>
                        <label class="text-xs font-bold text-slate-400 block mb-2">Date Range</label>
                        <select id="report-date-select" class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm">
                            <option value="today">Today</option>
                            <option value="week">This Week</option>
                            <option value="month">This Month</option>
                            <option value="all">All Time</option>
                        </select>
                    </div>
                    <div class="flex items-end">
                        <button onclick="downloadReport();" class="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold text-sm transition">
                            <i class="fa-solid fa-download"></i> Download
                        </button>
                    </div>
                </div>
                <p class="text-xs text-slate-400 mt-3"><i class="fa-solid fa-info-circle"></i> Select report type, format, and date range. Click Download to generate your report.</p>
            </div>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="glass-card p-6 col-span-1 max-h-[520px] overflow-y-auto">
                <h3 class="font-bold mb-6 text-cloud"><i class="fa-solid fa-comment-dots"></i> Conversational Insights</h3>
                <p class="text-xs text-slate-500 mb-4">Top 10 chatbot questions this week</p>
                <div class="space-y-4" id="table-chatbot"></div>
            </div>
            <div class="glass-card p-6 col-span-1 lg:col-span-2 overflow-x-auto">
                <h3 class="font-bold mb-4 text-red-500"><i class="fa-solid fa-triangle-exclamation"></i> Human Risk Mitigation Escalation Desk</h3>
                <table class="w-full text-left border-collapse min-w-[640px]">
                    <thead>
                        <tr class="text-sm text-slate-500 border-b border-white/60">
                            <th class="pb-3 font-medium">Claim ID</th>
                            <th class="pb-3 font-medium">Vehicle Details</th>
                            <th class="pb-3 font-medium">Market Region</th>
                            <th class="pb-3 font-medium">Predicted Payout</th>
                            <th class="pb-3 font-medium text-center">Fraud Score</th>
                            <th class="pb-3 font-medium">Trigger Justification</th>
                        </tr>
                    </thead>
                    <tbody id="table-escalation" class="text-sm"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
/* ========== Role routing & state engine ========== */
const AppState = {
    role: null,
    views: ['auth-view', 'customer-view', 'admin-view'],
    barChart: null,
    lineChart: null,
    bubbleChart: null,
    customerChart: null,
    customerTab: 'overview',
};

const CREDENTIALS = {
    customer: { email: 'customer@ackoai.com', password: 'customer123', view: 'customer-view' },
    admin: { email: 'admin@ackoai.com', password: 'admin123', view: 'admin-view' },
};

const FRAUD_BADGE = {
    high: 'px-2.5 py-1 bg-red-100 text-red-700 rounded-lg font-bold text-xs',
    medium: 'px-2.5 py-1 bg-orange-100 text-orange-700 rounded-lg font-bold text-xs',
    low: 'px-2.5 py-1 bg-amber-100 text-amber-700 rounded-lg font-bold text-xs',
};

function scrollToLogin() {
    document.getElementById('login-section')?.scrollIntoView({ behavior: 'smooth' });
}

function goHome() {
    if (AppState.role) logout();
    else window.scrollTo({ top: 0, behavior: 'smooth' });
}

function login(e, roleKey) {
    e.preventDefault();
    const prefix = roleKey === 'customer' ? 'c' : 'a';
    const email = document.getElementById(prefix + '-email').value.trim();
    const pass = document.getElementById(prefix + '-pass').value;
    const cred = CREDENTIALS[roleKey];

    if (email === cred.email && pass === cred.password) {
        AppState.role = roleKey;
        switchView(cred.view);
        if (roleKey === 'customer') {
            resetChatbot();
            loadCustomerOverview();
            const inc = document.getElementById('c-incident');
            if (inc) inc.value = new Date().toISOString().slice(0, 10);
        }
        if (roleKey === 'admin') loadDashboardData();
    } else {
        alert('Invalid credentials. Use the demo accounts shown in the login form.');
    }
}

function logout() {
    AppState.role = null;
    if (AppState.barChart) { AppState.barChart.destroy(); AppState.barChart = null; }
    if (AppState.lineChart) { AppState.lineChart.destroy(); AppState.lineChart = null; }
    switchView('auth-view');
}

function switchView(viewId) {
    AppState.views.forEach(id => {
        const el = document.getElementById(id);
        el.classList.add('hidden');
        el.classList.remove('fade-in');
    });
    const target = document.getElementById(viewId);
    target.classList.remove('hidden');
    void target.offsetWidth;
    target.classList.add('fade-in');

    const isAuth = viewId === 'auth-view';
    document.getElementById('logout-btn').classList.toggle('hidden', isAuth);
    document.getElementById('header-nav').classList.toggle('hidden', !isAuth);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ========== Customer: Tab navigation ========== */
function switchCustomerTab(tab) {
    AppState.customerTab = tab;
    document.querySelectorAll('#customer-tabs .tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('[id^="tab-"]').forEach(panel => {
        if (panel.id.startsWith('tab-')) {
            panel.classList.toggle('active', panel.id === 'tab-' + tab);
        }
    });
    if (tab === 'overview') loadCustomerOverview();
}

/* ========== Customer: Overview dashboard ========== */
async function loadCustomerOverview() {
    try {
        const res = await fetch('/api/customer/overview');
        const data = await res.json();
        document.getElementById('st-policies').textContent = data.stats.active_policies;
        document.getElementById('st-claims').textContent = data.stats.claims_filed;
        document.getElementById('st-approval').textContent = data.stats.approval_rate + '%';
        document.getElementById('st-payout').textContent = data.stats.avg_payout
            ? fmt(data.stats.avg_payout) : '₹ 0';

        const list = document.getElementById('recent-claims-list');
        if (!data.recent_claims.length) {
            list.innerHTML = '<p class="text-slate-500">No claims yet. Use AI Claims Engine to file one.</p>';
        } else {
            list.innerHTML = data.recent_claims.map(c => `
                <div class="flex justify-between items-center p-3 bg-white/40 rounded-xl">
                    <div><strong>${escapeHtml(c.claim_id)}</strong><br><span class="text-xs text-slate-500">${escapeHtml(c.vehicle)}</span></div>
                    <div class="text-right"><div class="font-bold">${fmt(c.amount)}</div>
                    <span class="text-xs px-2 py-0.5 rounded-full ${c.status === 'Approved' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}">${escapeHtml(c.status)}</span></div>
                </div>`).join('');
        }

        if (AppState.customerChart) AppState.customerChart.destroy();
        const ctx = document.getElementById('customerChart')?.getContext('2d');
        if (ctx) {
            AppState.customerChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.claim_trend.labels,
                    datasets: [{
                        label: 'Claims',
                        data: data.claim_trend.data,
                        borderColor: '#0077ff',
                        backgroundColor: 'rgba(0,119,255,0.1)',
                        fill: true,
                        tension: 0.4,
                    }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
            });
        }
    } catch (e) { console.error(e); }
}

function animateClaimTracker(status) {
    const steps = document.querySelectorAll('#claim-tracker .tracker-step');
    steps.forEach((s, i) => {
        s.classList.remove('done', 'active');
        if (status === 'Approved' && i < 4) s.classList.add('done');
        else if (status === 'Under Review' && i < 2) s.classList.add(i === 1 ? 'active' : 'done');
        else if (status === 'Escalated' && i === 2) s.classList.add('active');
        else if (i === 0) s.classList.add('done');
    });
}

/* ========== Customer: AI Claims Engine (Module 3) ========== */
function previewClaimImage(e) {
    const file = e.target.files?.[0];
    const img = document.getElementById('claim-preview');
    if (!file) return;
    img.src = URL.createObjectURL(file);
    img.classList.remove('hidden');
}

async function submitClaim(e) {
    e.preventDefault();
    const fileInput = document.getElementById('claim-image');
    if (!fileInput.files?.[0]) { alert('Please upload a damage photo.'); return; }

    const btn = document.getElementById('claim-btn-text');
    const spin = document.getElementById('claim-spinner');
    btn.textContent = 'Analysing with AI...';
    spin.classList.remove('hidden');

    const fd = new FormData();
    fd.append('image', fileInput.files[0]);
    fd.append('vehicle_type', document.getElementById('c-vtype').value);
    fd.append('model_name', document.getElementById('c-model').value);
    fd.append('year', document.getElementById('c-year').value);
    fd.append('idv', document.getElementById('c-idv').value);
    fd.append('incident_date', document.getElementById('c-incident').value);
    fd.append('description', document.getElementById('c-desc').value);
    fd.append('city', document.getElementById('c-city').value);
    fd.append('policy_type', 'Comprehensive');
    fd.append('claim_history', '0');
    fd.append('ncb', '20');

    try {
        const res = await fetch('/predict-claim', { method: 'POST', body: fd });
        if (!res.ok) throw new Error('Claim prediction failed');
        const data = await res.json();

        document.getElementById('cr-amount').textContent = fmt(data.predicted_amount);
        document.getElementById('cr-approval').textContent = data.approval_percent + '%';
        document.getElementById('cr-id').textContent = data.claim_id;
        const st = document.getElementById('cr-status');
        st.textContent = data.status;
        st.className = 'font-semibold px-2 py-1 rounded-lg text-sm ' + (
            data.status === 'Approved' ? 'bg-green-100 text-green-700' :
            data.status === 'Escalated' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700');
        document.getElementById('cr-model').textContent = data.model_used;
        document.getElementById('cr-fraud').textContent = data.fraud_probability + '%';
        document.getElementById('cr-analysis').textContent = data.analysis.description || data.analysis.severity + ' ' + data.analysis.damage_type;
        document.getElementById('cr-parts').textContent = 'Parts: ' + (data.analysis.affected_parts || []).join(', ') + ' · Source: ' + data.analysis.source;

        const box = document.getElementById('claim-result');
        box.classList.remove('hidden');
        box.classList.add('fade-in');
        animateClaimTracker(data.status);
        loadCustomerOverview();
    } catch (err) {
        alert('Could not process claim. Ensure the server is running.');
    } finally {
        btn.textContent = 'Analyse & Predict Claim';
        spin.classList.add('hidden');
    }
}

/* ========== Customer: Premium calculator ========== */
async function calculatePremium(e) {
    e.preventDefault();
    const type = document.getElementById('v-type').value;
    const model = document.getElementById('v-model').value;
    const year = parseInt(document.getElementById('v-year').value, 10);
    const idv = parseFloat(document.getElementById('v-idv').value);
    const btnText = document.getElementById('calc-text');
    const spinner = document.getElementById('calc-spinner');

    btnText.textContent = 'Calculating...';
    spinner.classList.remove('hidden');

    try {
        const res = await fetch('/predict-premium', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vehicle_type: type, model_name: model, year, idv }),
        });
        if (!res.ok) throw new Error('Premium request failed');
        const data = await res.json();

        document.getElementById('q-header').textContent =
            `${data.model_name} · ${data.vehicle_type} · ${data.vehicle_age} yrs old`;
        document.getElementById('q-base').textContent = fmt(data.base_premium);
        document.getElementById('q-od').textContent = fmt(data.own_damage);
        document.getElementById('q-ncb').textContent = '- ' + fmt(data.ncb_discount);
        document.getElementById('q-sub').textContent = fmt(data.subtotal);
        document.getElementById('q-gst').textContent = fmt(data.gst_18);
        document.getElementById('q-total').textContent = fmt(data.total_premium);

        const box = document.getElementById('quote-result');
        box.classList.remove('hidden');
        box.classList.add('fade-in');
    } catch (err) {
        alert('Could not calculate premium. Ensure the server is running.');
    } finally {
        btnText.textContent = 'Generate Quote';
        spinner.classList.add('hidden');
    }
}

function fmt(n) {
    return '₹ ' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

/* ========== Customer: Chatbot ========== */
function resetChatbot() {
    const history = document.getElementById('chat-history');
    history.innerHTML = '';
    appendMessage(
        "Hi! I'm your AI policy assistant. Ask about claims, IDV, NCB, garages, renewals, or documents.",
        'bot'
    );
}

function appendMessage(text, sender) {
    const history = document.getElementById('chat-history');
    const wrap = document.createElement('div');
    wrap.className = 'flex flex-col max-w-[85%] fade-in ' + (sender === 'user' ? 'self-end items-end' : 'self-start items-start');

    const bubble = document.createElement('div');
    bubble.className = sender === 'user'
        ? 'px-4 py-3 rounded-2xl rounded-tr-sm bg-white text-slate-800 border border-white/60 shadow-sm'
        : 'px-4 py-3 rounded-2xl rounded-tl-sm bg-cloud text-white shadow-md';
    bubble.textContent = text;

    const time = document.createElement('span');
    time.className = 'text-[10px] text-slate-400 mt-1 px-1';
    time.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    wrap.appendChild(bubble);
    wrap.appendChild(time);
    history.appendChild(wrap);
    history.scrollTop = history.scrollHeight;
    return wrap;
}

function showTypingIndicator() {
    const history = document.getElementById('chat-history');
    const wrap = document.createElement('div');
    wrap.id = 'typing-indicator';
    wrap.className = 'self-start fade-in';
    wrap.innerHTML = '<div class="px-4 py-3 rounded-2xl rounded-tl-sm bg-cloud text-white shadow-md typing-dots"><span></span><span></span><span></span></div>';
    history.appendChild(wrap);
    history.scrollTop = history.scrollHeight;
}

function hideTypingIndicator() {
    document.getElementById('typing-indicator')?.remove();
}

function askPrompt(text) {
    switchCustomerTab('chatbot');
    document.getElementById('chat-input').value = text;
    sendMessage(new Event('submit'));
}

async function sendMessage(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendMessage(msg, 'user');
    input.value = '';
    showTypingIndicator();

    try {
        const res = await fetch('/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg }),
        });
        if (!res.ok) throw new Error('Chat failed');
        const data = await res.json();
        hideTypingIndicator();
        setTimeout(() => {
            appendMessage(data.reply, 'bot');
            if (data.source && data.source.startsWith('rag')) {
                const history = document.getElementById('chat-history');
                const tag = document.createElement('div');
                tag.className = 'self-start text-[10px] text-cloud/80 px-2 -mt-1 mb-1';
                tag.textContent = '📄 Answer from ACKO policy documents';
                history.appendChild(tag);
            }
        }, 300);
    } catch (err) {
        hideTypingIndicator();
        appendMessage("Sorry, I couldn't reach the server. Please try again.", 'bot');
    }
}

/* ========== Admin: Dashboard ========== */
async function loadDashboardData() {
    try {
        const res = await fetch('/dashboard-data');
        if (!res.ok) throw new Error('Dashboard fetch failed');
        const data = await res.json();

        document.getElementById('kpi-claims-total').textContent =
            data.kpis.total_claims.this_month.toLocaleString('en-IN');
        document.getElementById('kpi-claims-today').textContent = data.kpis.total_claims.today;
        document.getElementById('kpi-claims-week').textContent = data.kpis.total_claims.this_week;
        document.getElementById('kpi-claims-month').textContent = data.kpis.total_claims.this_month;

        document.getElementById('kpi-payout-car').textContent = data.kpis.avg_payout.car;
        document.getElementById('kpi-payout-bike').textContent = data.kpis.avg_payout.bike;

        const rateStr = data.kpis.approval_rate;
        document.getElementById('kpi-approval').textContent = rateStr;
        const pct = parseFloat(rateStr) || 0;
        document.getElementById('approval-ring').style.setProperty('--pct', pct + '%');

        document.getElementById('kpi-quotes-total').textContent =
            data.kpis.quotations.total.toLocaleString('en-IN');
        document.getElementById('kpi-quotes-avg').textContent = data.kpis.quotations.avg_premium;

        renderCharts(data.charts);
        renderChatbotTable(data.tables.chatbot_insights);
        renderEscalationTable(data.tables.escalation_desk);
        render4DBubbleChart(data.tables.escalation_desk);
    } catch (err) {
        console.error('Dashboard error:', err);
        alert('Could not load dashboard data.');
    }
}

function renderCharts(charts) {
    Chart.defaults.font.family = '"Plus Jakarta Sans", sans-serif';
    Chart.defaults.color = '#64748b';

    if (AppState.barChart) AppState.barChart.destroy();
    const ctxBar = document.getElementById('barChart').getContext('2d');
    AppState.barChart = new Chart(ctxBar, {
        type: 'bar',
        data: {
            labels: charts.top_cities.labels,
            datasets: [{
                label: 'Claims',
                data: charts.top_cities.data,
                backgroundColor: '#0077ff',
                borderRadius: 6,
                barPercentage: 0.6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, border: { display: false } },
                x: { grid: { display: false }, border: { display: false } },
            },
        },
    });

    if (AppState.lineChart) AppState.lineChart.destroy();
    const ctxLine = document.getElementById('lineChart').getContext('2d');
    const gradient = ctxLine.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
    gradient.addColorStop(1, 'rgba(6, 182, 212, 0)');

    AppState.lineChart = new Chart(ctxLine, {
        type: 'line',
        data: {
            labels: charts.historical_trends.labels,
            datasets: [{
                label: 'Volume',
                data: charts.historical_trends.data,
                borderColor: '#06b6d4',
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#06b6d4',
                pointBorderWidth: 2,
                pointRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, border: { display: false } },
                x: { grid: { display: false }, border: { display: false } },
            },
        },
    });
}

function render4DBubbleChart(escalationDesk) {
    const bubbleCtx = document.getElementById('bubbleChart');
    if (!bubbleCtx) return;
    
    const bubblePoints = escalationDesk.map(row => {
        const payout = Number(String(row.payout).replace(/[^0-9.-]/g, '')) || 0;
        const fraudScore = Number(String(row.fraud_score).replace(/[^0-9.-]/g, '')) || 50;
        const r = Math.min(24, Math.max(6, fraudScore / 5));
        const color = fraudScore >= 80 ? '#ef4444' : fraudScore >= 70 ? '#f59e0b' : '#10b981';
        return { x: payout, y: fraudScore, r: r, backgroundColor: color, label: row.vehicle };
    }).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));

    if (AppState.bubbleChart) AppState.bubbleChart.destroy();
    AppState.bubbleChart = new Chart(bubbleCtx, {
        type: 'bubble',
        data: { datasets: [{ label: '4D Claims', data: bubblePoints, borderColor: '#fff', borderWidth: 0.5 }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#64748b' } },
                tooltip: {
                    backgroundColor: 'rgba(15,23,42,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    callbacks: {
                        label: function(ctx) {
                            const d = ctx.raw;
                            return [`Payout: ₹${d.x}`, `Fraud: ${d.y}%`, `Severity: ${d.r}`];
                        }
                    }
                }
            },
            scales: {
                x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(0,0,0,0.05)' }, title: { display: true, text: 'Payout (INR)', color: '#64748b' } },
                y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(0,0,0,0.05)' }, title: { display: true, text: 'Fraud Score (%)', color: '#64748b' } }
            }
        }
    });
}

function downloadReport() {
    const type = document.getElementById('report-type-select')?.value || 'escalation';
    const format = document.getElementById('report-format-select')?.value || 'csv';
    const range = document.getElementById('report-date-select')?.value || 'all';
    const url = `/admin/report?type=${type}&format=${format}&range=${range}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `admin_report_${new Date().toISOString().split('T')[0]}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function renderChatbotTable(insights) {
    const container = document.getElementById('table-chatbot');
    container.innerHTML = '';
    const maxHits = Math.max(...insights.map(i => i.hits), 1);
    insights.forEach((item, i) => {
        const width = Math.max((item.hits / maxHits) * 100, 5);
        const row = document.createElement('div');
        row.innerHTML = `
            <div class="flex justify-between text-sm mb-1">
                <span class="truncate pr-3 text-slate-700">${i + 1}. ${escapeHtml(item.question)}</span>
                <span class="font-bold shrink-0">${item.hits.toLocaleString('en-IN')}</span>
            </div>
            <div class="w-full bg-white/60 rounded-full h-2">
                <div class="bg-cloud h-2 rounded-full transition-all duration-500" style="width:${width}%"></div>
            </div>`;
        container.appendChild(row);
    });
}

function fraudBadgeClass(scoreStr) {
    const n = parseInt(scoreStr, 10);
    if (n >= 85) return FRAUD_BADGE.high;
    if (n >= 70) return FRAUD_BADGE.medium;
    return FRAUD_BADGE.low;
}

function renderEscalationTable(desk) {
    const tbody = document.getElementById('table-escalation');
    tbody.innerHTML = '';
    desk.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-white/40 hover:bg-white/60 transition-colors';
        tr.innerHTML = `
            <td class="py-4 font-bold text-slate-800">${escapeHtml(item.id)}</td>
            <td class="py-4">${escapeHtml(item.vehicle)}</td>
            <td class="py-4">${escapeHtml(item.region)}</td>
            <td class="py-4 font-bold">${escapeHtml(item.payout)}</td>
            <td class="py-4 text-center"><span class="${fraudBadgeClass(item.fraud_score)}">${escapeHtml(item.fraud_score)}</span></td>
            <td class="py-4 text-slate-600 text-xs max-w-xs">${escapeHtml(item.justification)}</td>`;
        tbody.appendChild(tr);
    });
}

function escapeHtml(str) {
    return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/* Init */
switchView('auth-view');
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend() -> HTMLResponse:
    """Serve the monolithic premium platform SPA."""
    return HTMLResponse(content=HTML_CONTENT)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

