import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
    )

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-3.6-flash"

app = FastAPI(title="ArogyaResQ AI")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DISCLAIMER = (
    "ArogyaResQ AI gives you structured, workplace‑aware first‑aid guidance — DOs, DON’Ts, and red flags — "
    "so you can act quickly and safely. In a life‑threatening emergency, always call local emergency services "
    "first. This tool supports trained responders; it never replaces them."
)

ENVIRONMENTS = [
    "Factory Worker",
    "Firefighter",
    "Construction Worker",
    "Chemical Worker",
    "Rescue Worker",
    "Warehouse Worker",
    "Other / Not sure",
]

# ── FEATURE 1: Quick‑Action Preset Buttons ────────────────────────────
QUICK_ACTIONS = [
    {"label": "🩹 Minor Cut",       "message": "I have a minor cut that's bleeding a little."},
    {"label": "🦴 Fracture / Sprain","message": "I think I have a fracture or a severe sprain."},
    {"label": "🔥 Burn",            "message": "I got a burn at work."},
    {"label": "🧪 Chemical Spill",  "message": "I got a chemical splash on my skin."},
    {"label": "👁️ Eye Injury",      "message": "Something got into my eye at work."},
    {"label": "🚨 Emergency",       "message": "My coworker is unconscious and not breathing."},
]

CRITICAL_OVERRIDE_KEYWORDS = [
    "not breathing", "can't breathe", "cant breathe", "difficulty breathing",
    "unconscious", "unresponsive", "passed out", "fainted",
    "severe bleeding", "won't stop bleeding", "wont stop bleeding",
    "heavy bleeding", "spurting",
    "chest pain", "crushed", "amputat", "electrocut",
    "seizure", "not moving", "no pulse",
]


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    CRITICAL = "CRITICAL"


class FirstAidResponse(BaseModel):
    is_medical_query: bool
    risk_level: RiskLevel
    injury_category: str
    emergency_required: bool
    immediate_actions: List[str]
    dont_actions: List[str]
    red_flags: List[str]
    next_step: str
    explanation: str


# ── FEATURE 3: Timestamp added to Turn model ──────────────────────────
class Turn(BaseModel):
    role: str  # "user" or "assistant"
    text: str
    structured: Optional[FirstAidResponse] = None
    timestamp: str = ""


class SessionState(BaseModel):
    environment: Optional[str] = None
    history: List[Turn] = []


sessions: Dict[str, SessionState] = {}

FALLBACK_RESPONSE = FirstAidResponse(
    is_medical_query=True,
    risk_level=RiskLevel.CRITICAL,
    injury_category="Unknown (AI unavailable)",
    emergency_required=True,
    immediate_actions=[
        "Move away from danger if it is safe to do so.",
        "Activate your workplace emergency response.",
        "Contact local emergency services.",
        "Alert trained first-aid personnel nearby.",
    ],
    dont_actions=["Do not delay emergency care to keep using this app."],
    red_flags=["AI guidance is currently unavailable — treat this as urgent."],
    next_step="Activate emergency services immediately.",
    explanation=(
        "ArogyaResQ AI couldn't reach the AI service, so a safe default emergency "
        "response is shown instead of no response at all."
    ),
)


def build_system_instruction(environment: Optional[str]) -> str:
    env_line = f"The user works as: {environment}." if environment else (
        "The user's work environment is not specified."
    )
    return (
        "You are ArogyaResQ AI, a first-aid decision-support assistant for workers "
        "in high-risk occupational environments. " + env_line + " "
        "You are NOT a doctor and must never diagnose a condition or claim "
        "certainty when information is incomplete. Always encourage "
        "professional medical evaluation when appropriate, and always treat "
        "any sign of a life-threatening condition (severe bleeding, "
        "breathing difficulty, unconsciousness, chest symptoms, major "
        "trauma, electrical or chemical exposure) as requiring immediate "
        "emergency escalation rather than continued chat. Never tell the "
        "user to delay emergency care to keep talking. Keep advice general, "
        "safe, and consistent with standard first-aid guidance. Ask at most "
        "one short clarifying question if the injury is unclear, otherwise "
        "give your best structured assessment. If the user's message is not "
        "about an injury, illness, symptom, first aid, workplace safety, or "
        "medical emergency, set is_medical_query to false. For a non-medical "
        "query, use a brief explanation that ArogyaResQ AI only handles medical "
        "and first-aid questions, and leave all action lists and risk details "
        "empty or neutral."
    )


def apply_safety_override(user_text: str, result: FirstAidResponse) -> FirstAidResponse:
    lowered = user_text.lower()
    if any(kw in lowered for kw in CRITICAL_OVERRIDE_KEYWORDS):
        result.is_medical_query = True
        result.risk_level = RiskLevel.CRITICAL
        result.emergency_required = True
        if not result.next_step or "emergency" not in result.next_step.lower():
            result.next_step = "Activate emergency services immediately."
    return result


def call_gemini(session: SessionState, user_text: str) -> FirstAidResponse:
    # Pre‑check: obvious non‑medical queries → no API call
    non_medical_keywords = [
        "battle", "panipat", "history", "who is", "what is",
        "explain", "tell me about", "define", "meaning of"
    ]
    lowered = user_text.lower()
    if any(kw in lowered for kw in non_medical_keywords):
        return FirstAidResponse(
            is_medical_query=False,
            risk_level=RiskLevel.LOW,
            injury_category="Non-Medical Query",
            emergency_required=False,
            immediate_actions=[],
            dont_actions=[],
            red_flags=[],
            next_step="",
            explanation="I am ArogyaResQ AI, a first-aid decision-support assistant for high-risk occupational environments. I can only provide guidance on workplace injuries and medical emergencies. If you or a coworker have suffered an injury, please describe the situation so I can provide first-aid advice."
        )

    contents = []
    for turn in session.history:
        role = "user" if turn.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn.text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=build_system_instruction(session.environment),
                response_mime_type="application/json",
                response_schema=FirstAidResponse,
            ),
        )
        result = FirstAidResponse.model_validate_json(response.text)
    except Exception as e:
        print("API call failed:", e)
        emergency_keywords = ["unconscious", "not breathing", "severe bleeding",
                              "chest pain", "seizure", "electrocut"]
        if any(kw in lowered for kw in emergency_keywords):
            return FALLBACK_RESPONSE
        return FirstAidResponse(
            is_medical_query=False,
            risk_level=RiskLevel.LOW,
            injury_category="Service Unavailable",
            emergency_required=False,
            immediate_actions=[],
            dont_actions=[],
            red_flags=[],
            next_step="Please try again later.",
            explanation="ArogyaResQ AI is temporarily unavailable. Please check your internet connection and try again. If this is an emergency, call local emergency services immediately."
        )

    return apply_safety_override(user_text, result)


def get_session(session_id: Optional[str]) -> tuple[str, SessionState]:
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    new_id = str(uuid.uuid4())
    sessions[new_id] = SessionState()
    return new_id, sessions[new_id]


def now() -> str:
    """FEATURE 3: return current time as a nice string."""
    return datetime.now().strftime("%I:%M %p")


def render_index(request: Request, session_id: str, session: SessionState):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "session_id": session_id,
            "environments": ENVIRONMENTS,
            "session": session,
            "disclaimer": DISCLAIMER,
            "quick_actions": QUICK_ACTIONS,   # FEATURE 1
        },
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    session_id, session = get_session(None)
    return render_index(request, session_id, session)


@app.post("/chat", response_class=HTMLResponse)
def chat(
    request: Request,
    session_id: str = Form(...),
    environment: str = Form(""),
    message: str = Form(""),
):
    session_id, session = get_session(session_id)

    if environment:
        session.environment = environment

    message = message.strip()
    if message:
        # FEATURE 3: add timestamp when appending turns
        session.history.append(Turn(role="user", text=message, timestamp=now()))
        result = call_gemini(session, message)
        session.history.append(
            Turn(role="assistant", text=result.explanation,
                 structured=result, timestamp=now())
        )

    return render_index(request, session_id, session)


# ── FEATURE 3 (cont.): Clear Conversation endpoint ────────────────────
@app.post("/reset")
def reset(session_id: str = Form(...)):
    if session_id in sessions:
        # Preserve environment, wipe history
        sessions[session_id].history = []
    return RedirectResponse(url="/", status_code=303)