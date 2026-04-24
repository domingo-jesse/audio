# Atmosphere AI (MVP)

Atmosphere AI is a Streamlit prototype for **AI-powered music atmosphere recommendations** in business spaces.

> This MVP recommends settings and strategies only. It does **not** stream music.

## What the app does

The app helps owners and managers choose the right music atmosphere using business context and live conditions:

1. **Business Profile**
   - Capture business name, type, brand vibe, target customer, and default goal.
2. **Live Atmosphere Control**
   - Set time of day, crowd level, noise level, current energy, and desired outcome.
3. **AI Recommendation**
   - Generate recommendations for mood, genre, BPM range, volume, energy, playlist concept, and risk flags.
   - Uses rule-based logic by default.
   - If `OPENAI_API_KEY` is available and optional atmosphere text is provided, a more customized JSON recommendation is generated via OpenAI.
   - Includes an **AI Adjustment Copilot** checklist that translates recommendations into live, step-by-step adjustment actions.
4. **Schedule Builder**
   - Create a sample daily schedule across morning/lunch/afternoon/evening/late night.
5. **Analytics / Experiment Tracker**
   - Log test rows manually and view charts for dwell time, sales estimate, and tips estimate by music mood.

All data persists in `st.session_state` for the duration of the session (no database required).

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in terminal (typically `http://localhost:8501`).

## Why Spotify playback is not included

This app intentionally excludes Spotify playback because Spotify is generally for personal/non-commercial listening and is not designed as a licensed public performance solution for most business venues.

Atmosphere AI is designed so future versions can integrate with **licensed business music providers**.

## Future integrations

- Licensed business music APIs/platforms (e.g., Soundtrack Your Brand, Soundtrack API, Sonos Pro, Mood Media, or similar)
- POS data integration
- Foot traffic sensors
- Microphone-based ambient noise detection
- Customer feedback collection
- Automatic A/B testing workflows
