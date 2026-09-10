# ArogyaResQ AI

*From Injury → First Aid → Next Step.*

## Problem Statement
Workers in high‑risk environments (factories, construction, chemical plants, firefighting, etc.) often need immediate guidance right after an injury — what to do now, what not to do, and whether it's serious enough to need emergency care — before help arrives.

## Target Users
Workers in occupational high‑risk environments, and anyone needing quick, structured first‑aid guidance during a workplace injury.

## Solution
**ArogyaResQ AI** is a conversational first‑aid decision‑support assistant. The user selects their work environment and describes what happened in plain language; Gemini returns a structured assessment (not free text) covering risk level, immediate DO/DON'T actions, red flags to watch for, and a clear next step — with critical situations always escalated to "seek emergency help now."

## Features
- Environment‑aware guidance (factory, firefighter, construction, chemical, etc.)
- Structured, validated response for every message: risk level, DO actions, DON'T actions, red flags, next step
- Safety override layer: certain keywords (e.g. "not breathing", "unconscious", "severe bleeding") force a CRITICAL emergency response regardless of what the model returns
- Conversation memory within a session (doesn't re‑ask environment)
- Safe fallback response if the Gemini API is unreachable, so the app is never silently unusable in an emergency

## Technology Stack
- **Backend:** Python, FastAPI, Pydantic, Jinja2
- **AI:** Gemini API (`gemini-3.6-flash`) via the `google-genai` SDK, using `response_schema` to force structured output
- **Frontend:** Plain HTML + CSS, no JavaScript — standard HTML forms and FastAPI routes handle every interaction

## How Gemini API Is Used
Every user message is sent to Gemini along with the conversation history and the user's stated work environment. Gemini is required (via `response_schema` bound to a Pydantic model) to return a structured `FirstAidResponse` — risk level, injury category, immediate actions, DON'T actions, red flags, and a next step — rather than free‑form text. This is what lets the UI reliably render DO/DON'T cards and an emergency banner instead of parsing arbitrary prose. A lightweight keyword‑based safety layer then has final authority to force CRITICAL + emergency escalation, so the LLM's classification is never the last word on a life‑threatening situation.

**Note on scope:** this build focuses on the core chat loop end‑to‑end (environment context → structured Gemini response → DO/DON'T/red‑flag UI → safety override). The fuller architecture — a dedicated RAG knowledge layer with cited sources, incident report generation, demo‑mode presets, and a dashboard — is a natural next step but out of scope for this build.

## How to Run the Project
1. `cd aidwise` (or your project folder name)
2. `python -m venv venv && venv\Scripts\activate` (or `source venv/bin/activate` on macOS/Linux)
3. `pip install -r requirements.txt`
4. `copy .env.example .env` (or `cp` on macOS/Linux) and paste your Gemini API key
5. `uvicorn main:app --reload`
6. Open `http://127.0.0.1:8000`

## Environment Variables
- `GEMINI_API_KEY` — your Gemini API key from Google AI Studio. **Required.** Never commit your real key — only `.env.example` should go in the repo.