import json
import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

st.set_page_config(page_title="Atmosphere AI", page_icon="🎵", layout="wide")

BUSINESS_TYPES = [
    "Restaurant",
    "Coffee Shop",
    "Retail Store",
    "Gym",
    "Salon",
    "Hotel Lobby",
    "Bar",
]

BRAND_VIBES = ["Calm", "Premium", "Energetic", "Cozy", "Trendy", "Luxury", "Focused"]
TARGET_CUSTOMERS = [
    "Families",
    "Professionals",
    "Students",
    "Date Night",
    "Shoppers",
    "Commuters",
]

BUSINESS_GOALS = [
    "Increase dwell time",
    "Faster turnover",
    "Improve mood",
    "Encourage browsing",
    "Premium experience",
    "Increase energy",
]

TIME_OF_DAY = ["Morning", "Lunch", "Afternoon", "Dinner", "Late Night"]
DESIRED_OUTCOMES = [
    "Calm people down",
    "Keep people longer",
    "Move people faster",
    "Make space feel premium",
    "Increase social energy",
    "Improve focus",
]


def init_state() -> None:
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "business_name": "",
            "business_type": "Restaurant",
            "brand_vibe": "Premium",
            "target_customer": "Professionals",
            "default_goal": "Premium experience",
        }
    if "live" not in st.session_state:
        st.session_state.live = {
            "time_of_day": "Dinner",
            "crowd_level": 55,
            "noise_level": 50,
            "current_energy": 45,
            "desired_outcome": "Make space feel premium",
            "atmosphere_text": "",
        }
    if "analytics" not in st.session_state:
        st.session_state.analytics = []


def _map_business_goal_to_outcome(goal: str) -> str:
    mapping = {
        "Increase dwell time": "Keep people longer",
        "Faster turnover": "Move people faster",
        "Improve mood": "Calm people down",
        "Encourage browsing": "Keep people longer",
        "Premium experience": "Make space feel premium",
        "Increase energy": "Increase social energy",
    }
    return mapping.get(goal, "Keep people longer")


def _base_reco_by_context(business_type: str, time_of_day: str, outcome: str) -> dict:
    if business_type == "Restaurant" and time_of_day == "Dinner" and outcome == "Make space feel premium":
        return {
            "recommended_mood": "Refined & relaxed",
            "genres": ["Jazz", "Soul", "Acoustic", "Lounge"],
            "tempo_bpm": "70-95",
            "volume": "Moderate-low",
            "energy": "Low-medium",
            "playlist_concept": "Dinner Glow Session",
            "reasoning": "Slower, elegant tracks support conversation, premium perception, and a relaxed dining pace.",
        }

    by_time = {
        "Morning": ("Fresh and light", ["Acoustic Pop", "Lo-fi", "Soft Indie"], "80-105", "Low", "Low-medium"),
        "Lunch": ("Bright and social", ["Indie Pop", "Neo Soul", "Chill House"], "95-115", "Moderate", "Medium"),
        "Afternoon": ("Steady and focused", ["Lo-fi", "Nu Jazz", "Downtempo"], "85-110", "Moderate-low", "Medium"),
        "Dinner": ("Warm and premium", ["Jazz", "Soul", "Lounge"], "70-95", "Moderate-low", "Low-medium"),
        "Late Night": ("Vibrant and social", ["House", "R&B", "Afrobeat"], "105-125", "Moderate", "Medium-high"),
    }
    mood, genres, bpm, volume, energy = by_time[time_of_day]

    if outcome == "Move people faster":
        mood, genres, bpm, volume, energy = (
            "Fast turnover",
            ["Funk Pop", "Dance Pop", "Upbeat House"],
            "110-130",
            "Moderate",
            "High",
        )
    elif outcome == "Calm people down":
        mood, genres, bpm, volume, energy = (
            "Calm and clear",
            ["Ambient", "Soft Piano", "Chill Acoustic"],
            "60-85",
            "Low",
            "Low",
        )
    elif outcome == "Improve focus":
        mood, genres, bpm, volume, energy = (
            "Focused flow",
            ["Lo-fi", "Instrumental", "Downtempo"],
            "70-100",
            "Low",
            "Low-medium",
        )
    elif outcome == "Increase social energy":
        mood, genres, bpm, volume, energy = (
            "Social lift",
            ["Disco", "Dance Pop", "Afrobeats"],
            "105-128",
            "Moderate",
            "Medium-high",
        )

    return {
        "recommended_mood": mood,
        "genres": genres,
        "tempo_bpm": bpm,
        "volume": volume,
        "energy": energy,
        "playlist_concept": f"{business_type} {time_of_day} Pulse",
        "reasoning": "The recommendation balances your business context, time block, and desired customer behavior.",
    }


def _risk_checks(crowd_level: int, noise_level: int, volume: str) -> list[str]:
    risks: list[str] = []
    if crowd_level >= 75 and noise_level >= 70:
        risks.append("High crowd and high noise detected. Lower volume slightly and use less sonically dense tracks.")
    if noise_level <= 25 and volume in {"Moderate", "High", "Moderate-high"}:
        risks.append("Space is currently quiet. Consider reducing volume to avoid overwhelming guests.")
    if crowd_level <= 20 and volume in {"Moderate", "High", "Moderate-high"}:
        risks.append("Low crowd with elevated volume can feel empty or awkward. Pull volume down and slow tempo a bit.")
    return risks


def rule_based_recommendation(profile: dict, live: dict) -> dict:
    rec = _base_reco_by_context(
        business_type=profile["business_type"],
        time_of_day=live["time_of_day"],
        outcome=live["desired_outcome"],
    )
    risks = _risk_checks(live["crowd_level"], live["noise_level"], rec["volume"])
    rec["business_goal_alignment"] = (
        f"Aligned with goal: {profile['default_goal']} and desired outcome: {live['desired_outcome']}."
    )
    rec["risks"] = risks
    return rec


def llm_recommendation(profile: dict, live: dict) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None or not live["atmosphere_text"].strip():
        return None

    client = OpenAI(api_key=api_key)
    prompt = {
        "business_profile": profile,
        "live_inputs": live,
        "task": "Return a JSON recommendation for business-safe atmosphere settings. Avoid playback suggestions.",
        "schema": {
            "recommended_mood": "",
            "genres": [],
            "tempo_bpm": "",
            "volume": "",
            "energy": "",
            "playlist_concept": "",
            "reasoning": "",
            "business_goal_alignment": "",
            "risks": [],
        },
    }

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": "You are Atmosphere AI. Return only strict JSON matching the schema.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.4,
        )
        text = response.output_text.strip()
        data = json.loads(text)
        required = {
            "recommended_mood",
            "genres",
            "tempo_bpm",
            "volume",
            "energy",
            "playlist_concept",
            "reasoning",
            "business_goal_alignment",
            "risks",
        }
        if not required.issubset(data.keys()):
            return None
        return data
    except Exception:
        return None


def bpm_midpoint(tempo_text: str) -> int:
    parts = tempo_text.replace(" ", "").split("-")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return (int(parts[0]) + int(parts[1])) // 2
    return 95


def build_schedule(profile: dict) -> pd.DataFrame:
    rows = []
    for block in ["Morning", "Lunch", "Afternoon", "Evening", "Late Night"]:
        mapped_block = "Dinner" if block == "Evening" else block
        live = {
            "time_of_day": mapped_block,
            "crowd_level": 50,
            "noise_level": 45,
            "current_energy": 50,
            "desired_outcome": _map_business_goal_to_outcome(profile["default_goal"]),
        }
        rec = rule_based_recommendation(profile, live)
        rows.append(
            {
                "Time block": block,
                "Goal": profile["default_goal"],
                "Mood": rec["recommended_mood"],
                "BPM": rec["tempo_bpm"],
                "Volume": rec["volume"],
                "Notes": rec["reasoning"],
            }
        )
    return pd.DataFrame(rows)


init_state()

st.title("🎵 Atmosphere AI")
st.caption(
    "AI-powered atmosphere recommendations for business spaces — designed for strategy and testing, not direct playback."
)

st.info(
    "Legal note: This MVP intentionally does not include Spotify playback. Public business playback typically requires licensed business music providers."
)

profile_tab, live_tab, rec_tab, sched_tab, analytics_tab = st.tabs(
    [
        "1) Business Profile",
        "2) Live Atmosphere Control",
        "3) AI Recommendation",
        "4) Schedule Builder",
        "5) Analytics / Experiment Tracker",
    ]
)

with profile_tab:
    st.subheader("Set your business profile")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.profile["business_name"] = st.text_input(
                "Business name", value=st.session_state.profile["business_name"]
            )
            st.session_state.profile["business_type"] = st.selectbox(
                "Business type",
                BUSINESS_TYPES,
                index=BUSINESS_TYPES.index(st.session_state.profile["business_type"]),
            )
            st.session_state.profile["brand_vibe"] = st.selectbox(
                "Brand vibe",
                BRAND_VIBES,
                index=BRAND_VIBES.index(st.session_state.profile["brand_vibe"]),
            )
        with c2:
            st.session_state.profile["target_customer"] = st.selectbox(
                "Target customer",
                TARGET_CUSTOMERS,
                index=TARGET_CUSTOMERS.index(st.session_state.profile["target_customer"]),
            )
            st.session_state.profile["default_goal"] = st.selectbox(
                "Default business goal",
                BUSINESS_GOALS,
                index=BUSINESS_GOALS.index(st.session_state.profile["default_goal"]),
            )

    st.success("Profile saved in this session.")

with live_tab:
    st.subheader("Tune your live atmosphere")
    with st.container(border=True):
        l1, l2 = st.columns(2)
        with l1:
            st.session_state.live["time_of_day"] = st.selectbox(
                "Time of day",
                TIME_OF_DAY,
                index=TIME_OF_DAY.index(st.session_state.live["time_of_day"]),
            )
            st.session_state.live["crowd_level"] = st.slider(
                "Crowd level", 0, 100, value=st.session_state.live["crowd_level"]
            )
            st.session_state.live["noise_level"] = st.slider(
                "Noise level", 0, 100, value=st.session_state.live["noise_level"]
            )
        with l2:
            st.session_state.live["current_energy"] = st.slider(
                "Current energy level", 0, 100, value=st.session_state.live["current_energy"]
            )
            st.session_state.live["desired_outcome"] = st.selectbox(
                "Desired outcome",
                DESIRED_OUTCOMES,
                index=DESIRED_OUTCOMES.index(st.session_state.live["desired_outcome"]),
            )
            st.session_state.live["atmosphere_text"] = st.text_area(
                "AI Mode (optional): Describe the current atmosphere",
                value=st.session_state.live["atmosphere_text"],
                placeholder="Example: Busy dining room, conversations are loud, guests are waiting for tables...",
            )

with rec_tab:
    st.subheader("Recommendation engine")
    base_rec = rule_based_recommendation(st.session_state.profile, st.session_state.live)
    llm_rec = llm_recommendation(st.session_state.profile, st.session_state.live)

    rec = llm_rec if llm_rec else base_rec
    mode = "OpenAI-customized" if llm_rec else "Rule-based"
    st.caption(f"Mode: **{mode}**")

    card1, card2 = st.columns([1.3, 1])
    with card1:
        with st.container(border=True):
            st.markdown(f"### {rec['recommended_mood']}")
            st.write(f"**Genres:** {', '.join(rec['genres'])}")
            st.write(f"**Tempo:** {rec['tempo_bpm']} BPM")
            st.write(f"**Playlist concept:** {rec['playlist_concept']}")
            st.write(f"**Why this fits:** {rec['reasoning']}")
            st.write(f"**Goal alignment:** {rec['business_goal_alignment']}")

            if rec.get("risks"):
                st.warning("Risk flags")
                for r in rec["risks"]:
                    st.write(f"- {r}")
            else:
                st.success("No obvious risk mismatch detected for current volume/crowd/noise.")

    with card2:
        with st.container(border=True):
            bpm_mid = bpm_midpoint(rec["tempo_bpm"])
            volume_level = rec["volume"].lower()
            volume_map = {"low": 30, "moderate-low": 40, "moderate": 55, "moderate-high": 65, "high": 75}
            energy_map = {"low": 30, "low-medium": 45, "medium": 55, "medium-high": 70, "high": 82}
            st.metric("BPM target (midpoint)", f"{bpm_mid}")
            st.metric("Recommended volume index", f"{volume_map.get(volume_level, 50)}/100")
            st.metric("Recommended energy index", f"{energy_map.get(rec['energy'].lower(), 50)}/100")

with sched_tab:
    st.subheader("Daily schedule builder")
    with st.container(border=True):
        if st.button("Generate sample daily schedule", type="primary"):
            st.session_state.generated_schedule = build_schedule(st.session_state.profile)

        schedule_df = st.session_state.get("generated_schedule", build_schedule(st.session_state.profile))
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)

with analytics_tab:
    st.subheader("Experiment tracker")
    with st.container(border=True):
        with st.form("analytics_form", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            with a1:
                entry_date = st.date_input("Date", value=date.today())
                time_block = st.selectbox("Time block", ["Morning", "Lunch", "Afternoon", "Evening", "Late Night"])
                music_mood = st.text_input("Music mood used", value=base_rec["recommended_mood"])
            with a2:
                dwell = st.number_input("Average dwell time (minutes)", min_value=0.0, value=45.0, step=1.0)
                sales = st.number_input("Sales estimate ($)", min_value=0.0, value=1200.0, step=50.0)
                tips = st.number_input("Tips estimate ($)", min_value=0.0, value=140.0, step=10.0)
            with a3:
                customer_notes = st.text_area("Customer mood notes", value="")
                staff_notes = st.text_area("Staff notes", value="")

            submitted = st.form_submit_button("Add experiment row")
            if submitted:
                st.session_state.analytics.append(
                    {
                        "Date": str(entry_date),
                        "Time block": time_block,
                        "Music mood used": music_mood,
                        "Average dwell time": dwell,
                        "Sales estimate": sales,
                        "Tips estimate": tips,
                        "Customer mood notes": customer_notes,
                        "Staff notes": staff_notes,
                    }
                )
                st.success("Experiment row added.")

    analytics_df = pd.DataFrame(st.session_state.analytics)
    if analytics_df.empty:
        st.info("No experiment data yet. Add a few rows to unlock charts.")
    else:
        st.dataframe(analytics_df, use_container_width=True, hide_index=True)

        mood_group = analytics_df.groupby("Music mood used", as_index=False).agg(
            {
                "Average dwell time": "mean",
                "Sales estimate": "mean",
                "Tips estimate": "mean",
            }
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            fig1 = px.bar(mood_group, x="Music mood used", y="Average dwell time", title="Dwell time by music mood")
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.bar(mood_group, x="Music mood used", y="Sales estimate", title="Sales estimate by music mood")
            st.plotly_chart(fig2, use_container_width=True)
        with c3:
            fig3 = px.bar(mood_group, x="Music mood used", y="Tips estimate", title="Tips estimate by music mood")
            st.plotly_chart(fig3, use_container_width=True)
