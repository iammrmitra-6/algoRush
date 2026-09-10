# ArogyaResQ AI

*From Injury → First Aid → Next Step.*

## Problem Statement
Workers in high‑risk environments (factories, construction, chemical plants, firefighting, etc.) often need immediate guidance right after an injury — what to do now, what not to do, and whether it's serious enough to need emergency care — before help arrives.

## Target Users
Workers in occupational high‑risk environments, and anyone needing quick, structured first‑aid guidance during a workplace injury.

## Solution
**ArogyaResQ AI** is a conversational first‑aid decision‑support assistant. The user selects their work environment and describes what happened in plain language; Gemini returns a structured assessment (not free text) covering risk level, immediate DO/DON'T actions, red flags to watch for, and a clear next step — with critical situations always escalated to "seek emergency help now."

## Features
- **Environment‑aware guidance** — factory, firefighter, construction, chemical, rescue, warehouse, and more
- **Structured, validated response** for every message: risk level (LOW / MODERATE / CRITICAL), injury category, DO actions, DON'T actions, red flags, and a clear next step
- **Safety override layer** — certain keywords (e.g. "not breathing", "unconscious", "severe bleeding") force a CRITICAL emergency response regardless of what the model returns
- **Quick‑Action presets** — one‑click chips for common injuries (Minor Cut, Fracture, Burn, Chemical Spill, Eye Injury, Emergency) for fast triage during a crisis
- **Conversation memory** within a session — the assistant doesn't re‑ask the environment
- **Timestamped messages** — every user message and AI response shows the time it was sent
- **Clear Conversation** — reset the chat while preserving the selected environment
- **Graceful non‑medical handling** — off‑topic queries (e.g. history, general knowledge) return a clean message with no DO/DON'T cards and no false emergency banner
- **Safe fallback response** if the Gemini API is unreachable, so the app is never silently unusable in an emergency

## Technology Stack
- **Backend:** Python, FastAPI, Pydantic, Jinja2
- **AI:** Gemini API (`gemini-3.6-flash`) via the `google-genai` SDK, using `response_schema` to force structured JSON output
- **Frontend:** Plain HTML + CSS, no JavaScript — standard HTML forms and FastAPI routes handle every interaction
- **Fonts:** Fraunces (display) + Inter (UI) via Google Fonts

## How Gemini API Is Used
Every user message is sent to Gemini along with the conversation history and the user's stated work environment. Gemini is required (via `response_schema` bound to a Pydantic model) to return a structured `FirstAidResponse` — risk level, injury category, immediate actions, DON'T actions, red flags, and a next step — rather than free‑form text. This is what lets the UI reliably render DO/DON'T cards and an emergency banner instead of parsing arbitrary prose.

A lightweight keyword‑based safety layer then has final authority to force CRITICAL + emergency escalation, so the LLM's classification is never the last word on a life‑threatening situation. A parallel pre‑check catches obvious non‑medical queries (history, general knowledge, etc.) before they reach the API, so they return a calm, on‑brand message instead of a false emergency.

**Note on scope:** this build focuses on the core chat loop end‑to‑end (environment context → structured Gemini response → DO/DON'T/red‑flag UI → safety override). The fuller architecture — a dedicated RAG knowledge layer with cited sources, incident report generation, and a dashboard — is a natural next step but out of scope for this build.

## How to Run the Project
1. `cd` into your project folder
2. `python -m venv venv && venv\Scripts\activate` (or `source venv/bin/activate` on macOS/Linux)
3. `pip install -r requirements.txt`
4. `copy .env.example .env` (or `cp` on macOS/Linux) and paste your real Gemini API key
5. `uvicorn main:app --reload`
6. Open `http://127.0.0.1:8000`

## Environment Variables
- `GEMINI_API_KEY` — your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey). **Required.** Never commit your real key — only `.env.example` should go in the repo.

## Project Structure
.
├── main.py # FastAPI app, Gemini integration, safety override
├── requirements.txt # Python dependencies
├── .env.example # Template for environment variables
├── static/
│ └── style.css # Premium dark theme
└── templates/
└── index.html # Jinja2 chat UI

text

## Demo Inputs

| Scenario | Input | Expected |
|----------|-------|----------|
| Minor injury | "I cut my finger on a metal sheet, small cut, minor bleeding." | LOW risk |
| Moderate injury | "I fell off a ladder and can't put weight on my ankle." | MODERATE risk |
| Emergency | "My coworker is unconscious and not breathing." | CRITICAL + red banner |
| Non‑medical | "Tell me about the Battle of Panipat." | Friendly message, no DO/DON'T |


