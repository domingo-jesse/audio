import json
import os
import re
from datetime import date, datetime
import time
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

st.set_page_config(page_title="Whisper", page_icon="🎵", layout="wide")

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
LIBRARY_MOODS = ["Calm", "Cozy", "Premium", "Energetic", "Focused", "Social", "Romantic", "Luxury", "Upbeat"]
TIME_OF_DAY_OPTIONS = ["Morning", "Lunch", "Afternoon", "Dinner", "Late Night", "Any"]
BUSINESS_TYPE_OPTIONS = BUSINESS_TYPES + ["Any"]
LICENSE_OPTIONS = ["Royalty-free", "Commercially licensed", "Unknown"]
AI_SETTINGS = ["study", "restaurant", "retail", "gym", "gaming", "sleep", "work"]
AI_ENERGY_OPTIONS = ["low", "medium", "high"]
AI_VOCALS_OPTIONS = ["instrumental preferred", "vocals ok", "no preference"]
MAX_QUEUE_SIZE = 5
QUEUE_REFILL_THRESHOLD = 2
MAX_SONG_DURATION_SECONDS = 300
MAX_YOUTUBE_SEARCHES_PER_DAY = 25
FALLBACK_SONGS_PATH = "songs_fallback.csv"


class YouTubeQuotaExceededError(Exception):
    """Raised when YouTube Data API quota has been exhausted."""


def sample_tracks() -> list[dict]:
    return [
        {
            "title": "Morning Focus Acoustic",
            "artist": "Atlas Lane",
            "file_path": "",
            "bpm": 78,
            "mood_tags": ["Cozy", "Focused"],
            "genre": "Acoustic",
            "energy": 35,
            "best_time_of_day": "Morning",
            "best_business_type": "Coffee Shop",
            "license_status": "Royalty-free",
        },
        {
            "title": "Premium Dinner Jazz",
            "artist": "Velvet Room Trio",
            "file_path": "",
            "bpm": 82,
            "mood_tags": ["Premium", "Luxury"],
            "genre": "Jazz",
            "energy": 40,
            "best_time_of_day": "Dinner",
            "best_business_type": "Restaurant",
            "license_status": "Commercially licensed",
        },
        {
            "title": "Retail Energy Pop",
            "artist": "Neon Avenue",
            "file_path": "",
            "bpm": 118,
            "mood_tags": ["Upbeat", "Energetic"],
            "genre": "Pop",
            "energy": 78,
            "best_time_of_day": "Afternoon",
            "best_business_type": "Retail Store",
            "license_status": "Royalty-free",
        },
        {
            "title": "Calm Lobby Ambient",
            "artist": "Cloud District",
            "file_path": "",
            "bpm": 65,
            "mood_tags": ["Calm", "Luxury"],
            "genre": "Ambient",
            "energy": 22,
            "best_time_of_day": "Any",
            "best_business_type": "Hotel Lobby",
            "license_status": "Commercially licensed",
        },
        {
            "title": "Coffee Shop Warmth",
            "artist": "Harbor & Pine",
            "file_path": "",
            "bpm": 88,
            "mood_tags": ["Cozy", "Social"],
            "genre": "Indie Soul",
            "energy": 48,
            "best_time_of_day": "Lunch",
            "best_business_type": "Coffee Shop",
            "license_status": "Royalty-free",
        },
        {
            "title": "Gym Push Beat",
            "artist": "Pulse Engine",
            "file_path": "",
            "bpm": 130,
            "mood_tags": ["Energetic", "Upbeat"],
            "genre": "Electronic",
            "energy": 90,
            "best_time_of_day": "Any",
            "best_business_type": "Gym",
            "license_status": "Commercially licensed",
        },
        {
            "title": "Late Night Lounge",
            "artist": "Noir Skyline",
            "file_path": "",
            "bpm": 72,
            "mood_tags": ["Romantic", "Premium"],
            "genre": "Lounge",
            "energy": 30,
            "best_time_of_day": "Late Night",
            "best_business_type": "Bar",
            "license_status": "Royalty-free",
        },
        {
            "title": "Afternoon Browse Groove",
            "artist": "Market Circuit",
            "file_path": "",
            "bpm": 102,
            "mood_tags": ["Social", "Upbeat"],
            "genre": "Nu Disco",
            "energy": 62,
            "best_time_of_day": "Afternoon",
            "best_business_type": "Retail Store",
            "license_status": "Commercially licensed",
        },
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
            "autopilot_enabled": False,
            "time_of_day": "Dinner",
            "crowd_level": 55,
            "noise_level": 50,
            "current_energy": 45,
            "desired_outcome": "Make space feel premium",
            "atmosphere_text": "",
        }
    if "analytics" not in st.session_state:
        st.session_state.analytics = []
    if "music_library" not in st.session_state:
        st.session_state.music_library = sample_tracks()
    if "music_filters" not in st.session_state:
        st.session_state.music_filters = {"min_bpm": 70, "max_bpm": 120, "desired_moods": []}
    if "ai_music_interpretation" not in st.session_state:
        st.session_state.ai_music_interpretation = None
    if "ai_selected_song" not in st.session_state:
        st.session_state.ai_selected_song = None
    if "song_queue" not in st.session_state:
        st.session_state.song_queue = []
    if "current_song" not in st.session_state:
        st.session_state.current_song = None
    if "song_start_time" not in st.session_state:
        st.session_state.song_start_time = 0.0
    if "last_ai_search_time" not in st.session_state:
        st.session_state.last_ai_search_time = 0.0
    if "auto_dj_enabled" not in st.session_state:
        st.session_state.auto_dj_enabled = True
    if "youtube_searches_today" not in st.session_state:
        st.session_state.youtube_searches_today = 0
    if "youtube_search_day_key" not in st.session_state:
        st.session_state.youtube_search_day_key = ""
    if "youtube_quota_blocked" not in st.session_state:
        st.session_state.youtube_quota_blocked = False
    if "is_playing" not in st.session_state:
        st.session_state.is_playing = False
    if "auto_dj_mode" not in st.session_state:
        st.session_state.auto_dj_mode = True
    if "active_video_id" not in st.session_state:
        st.session_state.active_video_id = None
    if "player_rendered_video_id" not in st.session_state:
        st.session_state.player_rendered_video_id = None
    if "player_component_html" not in st.session_state:
        st.session_state.player_component_html = None
    if "initial_queue_bootstrap_done" not in st.session_state:
        st.session_state.initial_queue_bootstrap_done = False


def read_secret(key: str) -> str | None:
    env_value = os.getenv(key)
    if env_value:
        return env_value
    try:
        secret_value = st.secrets.get(key)
        return secret_value if secret_value else None
    except Exception:
        return None


def parse_iso8601_duration(duration: str) -> int:
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration or "")
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def get_today_key() -> str:
    return date.today().isoformat()


def _reset_daily_youtube_budget_if_needed() -> None:
    today_key = get_today_key()
    if st.session_state.get("youtube_search_day_key") != today_key:
        st.session_state.youtube_search_day_key = today_key
        st.session_state.youtube_searches_today = 0
        st.session_state.youtube_quota_blocked = False


def can_search_youtube() -> bool:
    _reset_daily_youtube_budget_if_needed()
    if st.session_state.get("youtube_quota_blocked"):
        return False
    if not read_secret("YOUTUBE_API_KEY"):
        return False
    return int(st.session_state.get("youtube_searches_today") or 0) < MAX_YOUTUBE_SEARCHES_PER_DAY


def _clean_music_analysis(data: dict) -> dict:
    mood = str(data.get("mood", "focused")).strip() or "focused"
    energy = str(data.get("energy", "medium")).strip().lower()
    energy = energy if energy in AI_ENERGY_OPTIONS else "medium"
    bpm_min = int(data.get("bpm_min", 70))
    bpm_max = int(data.get("bpm_max", 110))
    bpm_min = max(40, min(200, bpm_min))
    bpm_max = max(40, min(220, bpm_max))
    if bpm_min > bpm_max:
        bpm_min, bpm_max = bpm_max, bpm_min
    time_of_day = str(data.get("time_of_day", "any")).strip().lower() or "any"
    search_query = str(data.get("search_query", "")).strip()
    reason = str(data.get("reason", "")).strip()
    if not search_query:
        search_query = f"{mood} {energy} background music"
    if not reason:
        reason = "This recommendation was generated from your mood, energy, and context request."
    return {
        "mood": mood,
        "energy": energy,
        "bpm_min": bpm_min,
        "bpm_max": bpm_max,
        "time_of_day": time_of_day,
        "search_query": search_query,
        "reason": reason,
    }


def analyze_music_prompt(prompt: str, setting: str | None = None, energy: str | None = None, vocals: str | None = None) -> dict:
    api_key = read_secret("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to Streamlit secrets to use AI Music Finder.")
    if OpenAI is None:
        raise ValueError("OpenAI SDK is not installed in this environment.")

    client = OpenAI(api_key=api_key)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mood", "energy", "bpm_min", "bpm_max", "time_of_day", "search_query", "reason"],
        "properties": {
            "mood": {"type": "string"},
            "energy": {"type": "string", "enum": ["low", "medium", "high"]},
            "bpm_min": {"type": "integer"},
            "bpm_max": {"type": "integer"},
            "time_of_day": {"type": "string"},
            "search_query": {"type": "string"},
            "reason": {"type": "string"},
        },
    }

    user_payload = {
        "prompt": prompt,
        "setting": setting,
        "energy": energy,
        "vocals": vocals,
    }
    instructions = (
        "You are a music query parser. Return only JSON and no markdown. "
        "Infer mood, energy, bpm range, time_of_day, and a practical YouTube search query for background listening."
    )

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            text={"format": {"type": "json_schema", "name": "music_analysis", "schema": schema, "strict": True}},
            temperature=0.3,
        )
        raw_text = response.output_text.strip()
    except Exception:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.3,
        )
        raw_text = response.output_text.strip()

    parsed = json.loads(raw_text)
    return _clean_music_analysis(parsed)


def fallback_search_query(prompt: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(prompt)}"


def format_duration(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def generate_ai_song_ideas(prompt: str, setting: str | None = None, energy: str | None = None, vocals: str | None = None) -> list[str]:
    api_key = read_secret("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to Streamlit secrets to enable AI queue generation.")
    if OpenAI is None:
        raise ValueError("OpenAI SDK is not installed in this environment.")

    client = OpenAI(api_key=api_key)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["queries"],
        "properties": {
            "queries": {
                "type": "array",
                "minItems": 6,
                "maxItems": 10,
                "items": {"type": "string"},
            }
        },
    }
    payload = {"prompt": prompt, "setting": setting, "energy": energy, "vocals": vocals}
    instructions = (
        "You are a music curator for short tracks. Return concise YouTube search queries in the format "
        "'song title artist official audio'. Prioritize songs under 5 minutes and avoid duplicates."
    )
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(payload)},
            ],
            text={"format": {"type": "json_schema", "name": "song_queries", "schema": schema, "strict": True}},
            temperature=0.5,
        )
        parsed = json.loads(response.output_text.strip())
        queries = [q.strip() for q in parsed.get("queries", []) if str(q).strip()]
        return queries[:10]
    except Exception:
        fallback = [
            f"{prompt} official audio",
            f"{prompt} lyric video",
            f"{prompt} music video",
            f"{prompt} radio edit",
            f"{prompt} short version",
            f"{prompt} live session",
        ]
        return [q.strip() for q in fallback if q.strip()]


def build_autodj_bootstrap_inputs(live: dict) -> tuple[str, str | None, str | None, str | None]:
    time_of_day = (live.get("time_of_day") or "Any").lower()
    outcome = (live.get("desired_outcome") or "").lower()

    mood_hint = "balanced"
    setting = "work"
    energy = "medium"

    if "calm" in outcome:
        mood_hint = "calm relaxing"
        setting = "sleep"
        energy = "low"
    elif "social" in outcome or "energy" in outcome:
        mood_hint = "upbeat social"
        setting = "restaurant"
        energy = "high"
    elif "premium" in outcome:
        mood_hint = "premium lounge"
        setting = "restaurant"
        energy = "medium"
    elif "focus" in outcome:
        mood_hint = "focused instrumental"
        setting = "study"
        energy = "low"

    prompt = f"{mood_hint} background music for {time_of_day}"
    return prompt, setting, energy, "instrumental preferred"


@st.cache_data(ttl=86400)
def search_youtube_cached(query: str) -> list:
    youtube_api_key = read_secret("YOUTUBE_API_KEY")
    if not youtube_api_key:
        return []

    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoEmbeddable": "true",
        "videoCategoryId": "10",
        "maxResults": 10,
        "safeSearch": "moderate",
        "key": youtube_api_key,
    }
    response = requests.get("https://www.googleapis.com/youtube/v3/search", params=search_params, timeout=12)
    if response.status_code == 403 and "quotaExceeded" in response.text:
        raise YouTubeQuotaExceededError("YouTube search quota exceeded.")
    response.raise_for_status()
    return response.json().get("items", [])


def get_video_details_batch(video_ids: list[str]) -> dict[str, dict]:
    youtube_api_key = read_secret("YOUTUBE_API_KEY")
    if not youtube_api_key or not video_ids:
        return {}

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "contentDetails,snippet",
            "id": ",".join(video_ids),
            "key": youtube_api_key,
        },
        timeout=12,
    )
    if response.status_code == 403 and "quotaExceeded" in response.text:
        raise YouTubeQuotaExceededError("YouTube videos quota exceeded.")
    response.raise_for_status()
    return {item["id"]: item for item in response.json().get("items", [])}


def get_all_queued_video_ids() -> set[str]:
    queued = {song.get("video_id") for song in st.session_state.get("song_queue", []) if song.get("video_id")}
    current = st.session_state.get("current_song")
    if current and current.get("video_id"):
        queued.add(current["video_id"])
    return queued


def is_duplicate_song(video_id: str) -> bool:
    current = st.session_state.get("current_song")
    if current and current.get("video_id") == video_id:
        return True
    return any(song.get("video_id") == video_id for song in st.session_state.get("song_queue", []))


def maybe_finish_current_song() -> None:
    current = st.session_state.get("current_song")
    if not current:
        return

    duration = int(current.get("duration_seconds", 0))
    started = float(st.session_state.get("song_start_time", 0))
    if duration > 0 and time.time() - started >= duration:
        st.session_state.current_song = None
        st.session_state.song_start_time = 0
        st.session_state.active_video_id = None


def maybe_start_next_song() -> None:
    if st.session_state.get("current_song"):
        return

    queue = st.session_state.get("song_queue", [])
    if queue:
        st.session_state.current_song = queue.pop(0)
        st.session_state.song_start_time = time.time()
        st.session_state.active_video_id = st.session_state.current_song.get("video_id")


def add_songs_to_queue(candidate_songs: list[dict]) -> None:
    for song in candidate_songs:
        if len(st.session_state.song_queue) >= MAX_QUEUE_SIZE:
            break

        video_id = song.get("video_id")
        duration = int(song.get("duration_seconds", 0))
        if not video_id:
            continue
        if duration <= 0 or duration > MAX_SONG_DURATION_SECONDS:
            continue
        if is_duplicate_song(video_id):
            continue

        st.session_state.song_queue.append(song)


def get_ai_youtube_song_candidates(max_needed: int = 5) -> list[dict]:
    youtube_api_key = read_secret("YOUTUBE_API_KEY")
    if not youtube_api_key:
        st.warning("YOUTUBE_API_KEY is missing. Add it to Streamlit secrets to enable Auto-DJ queueing.")
        return []

    prompt = (st.session_state.get("ai_music_prompt") or "").strip()
    if not prompt:
        prompt, default_setting, default_energy, default_vocals = build_autodj_bootstrap_inputs(st.session_state.live)
    else:
        default_setting = st.session_state.get("ai_music_setting") or None
        default_energy = st.session_state.get("ai_music_energy") or None
        default_vocals = st.session_state.get("ai_music_vocals") or None

    try:
        queries = generate_ai_song_ideas(
            prompt=prompt,
            setting=default_setting,
            energy=default_energy,
            vocals=default_vocals,
        )
    except Exception:
        return []

    results: list[dict] = []
    for query in queries:
        if len(results) >= max_needed:
            break
        try:
            items = search_youtube_cached(query)
            st.session_state.youtube_searches_today = int(st.session_state.get("youtube_searches_today") or 0) + 1
        except Exception:
            continue

        video_ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
        if not video_ids:
            continue

        try:
            details_map = get_video_details_batch(video_ids)
        except Exception:
            continue

        for item in items:
            if len(results) >= max_needed:
                break
            video_id = item.get("id", {}).get("videoId")
            if not video_id or is_duplicate_song(video_id) or any(song.get("video_id") == video_id for song in results):
                continue

            details = details_map.get(video_id, {})
            duration_seconds = parse_iso8601_duration(details.get("contentDetails", {}).get("duration", ""))
            if duration_seconds <= 0 or duration_seconds > MAX_SONG_DURATION_SECONDS:
                continue

            snippet = details.get("snippet") or item.get("snippet", {})
            results.append(
                {
                    "title": snippet.get("title", "Unknown title"),
                    "channel": snippet.get("channelTitle", "Unknown channel"),
                    "video_id": video_id,
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                    "duration_seconds": duration_seconds,
                }
            )
            break

    return results


def maybe_refill_queue() -> None:
    if not st.session_state.get("auto_dj_enabled", True):
        return
    if len(st.session_state.song_queue) >= MAX_QUEUE_SIZE:
        return

    now = time.time()
    last_search = float(st.session_state.get("last_ai_search_time", 0))
    if now - last_search < 180:
        return

    candidate_songs = get_ai_youtube_song_candidates(max_needed=MAX_QUEUE_SIZE - len(st.session_state.song_queue))
    add_songs_to_queue(candidate_songs)
    st.session_state.last_ai_search_time = now


def fill_queue_from_fallback(mood: str) -> int:
    try:
        songs = pd.read_csv(FALLBACK_SONGS_PATH).fillna("")
    except Exception:
        return 0

    if songs.empty:
        return 0

    normalized_mood = str(mood or "").strip().lower()
    if normalized_mood:
        mood_matches = songs[songs["mood"].astype(str).str.lower() == normalized_mood]
        if not mood_matches.empty:
            songs = mood_matches

    songs = songs[songs["duration_seconds"].astype(int) <= MAX_SONG_DURATION_SECONDS]
    if songs.empty:
        return 0

    excluded_ids = get_all_queued_video_ids()
    queue = st.session_state.song_queue
    needed = max(0, MAX_QUEUE_SIZE - len(queue))
    if needed <= 0:
        return 0

    added = 0
    for _, row in songs.iterrows():
        video_id = str(row.get("video_id", "")).strip()
        if not video_id or video_id in excluded_ids:
            continue
        queue.append(
            {
                "video_id": video_id,
                "title": str(row.get("title", "Unknown title")).strip() or "Unknown title",
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": str(row.get("artist", "Unknown artist")).strip() or "Unknown artist",
                "duration_seconds": int(row.get("duration_seconds", 0) or 0),
                "search_query": f"fallback:{normalized_mood or 'any'}",
            }
        )
        excluded_ids.add(video_id)
        added += 1
        if added >= needed or len(queue) >= MAX_QUEUE_SIZE:
            break
    return added


def fill_queue_if_needed(prompt: str, mood: str) -> tuple[int, str | None]:
    queue = st.session_state.song_queue
    queue_len = len(queue)
    if queue_len >= MAX_QUEUE_SIZE:
        return 0, None
    if queue_len > QUEUE_REFILL_THRESHOLD:
        return 0, None

    needed = MAX_QUEUE_SIZE - queue_len
    if needed <= 0:
        return 0, None

    if not can_search_youtube():
        added = fill_queue_from_fallback(mood=mood)
        searches_today = int(st.session_state.get("youtube_searches_today") or 0)
        if searches_today >= MAX_YOUTUBE_SEARCHES_PER_DAY:
            return added, "Daily YouTube search budget reached. Using saved/fallback songs for now."
        if added == 0 and not read_secret("YOUTUBE_API_KEY"):
            return 0, "YOUTUBE_API_KEY is missing. Using fallback songs when available."
        return added, None

    broad_query = (prompt or f"{mood} background music under 5 minutes clean").strip()
    try:
        search_items = search_youtube_cached(broad_query)
    except YouTubeQuotaExceededError:
        st.session_state.youtube_quota_blocked = True
        return fill_queue_from_fallback(mood=mood), "YouTube quota exceeded. Using saved/fallback songs for now."
    except Exception as exc:
        return 0, f"YouTube search failed: {exc}"

    st.session_state.youtube_searches_today = int(st.session_state.get("youtube_searches_today") or 0) + 1
    excluded_ids = get_all_queued_video_ids()
    video_ids = [
        item.get("id", {}).get("videoId")
        for item in search_items
        if item.get("id", {}).get("videoId") and item.get("id", {}).get("videoId") not in excluded_ids
    ]
    if not video_ids:
        return fill_queue_from_fallback(mood=mood), None

    try:
        details_map = get_video_details_batch(video_ids)
    except YouTubeQuotaExceededError:
        st.session_state.youtube_quota_blocked = True
        return fill_queue_from_fallback(mood=mood), "YouTube quota exceeded. Using saved/fallback songs for now."
    except Exception as exc:
        return 0, f"YouTube video lookup failed: {exc}"

    added = 0
    for item in search_items:
        if len(queue) >= MAX_QUEUE_SIZE or added >= needed:
            break
        video_id = item.get("id", {}).get("videoId")
        if not video_id or video_id in excluded_ids:
            continue
        details = details_map.get(video_id, {})
        duration_seconds = parse_iso8601_duration(details.get("contentDetails", {}).get("duration", ""))
        if duration_seconds <= 0 or duration_seconds > MAX_SONG_DURATION_SECONDS:
            continue
        snippet = details.get("snippet") or item.get("snippet", {})
        title = snippet.get("title", "Unknown title")
        haystack = f"{title} {snippet.get('description', '')}".lower()
        if "#shorts" in haystack or "shorts" in haystack:
            continue

        queue.append(
            {
                "video_id": video_id,
                "title": title,
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": snippet.get("channelTitle", "Unknown channel"),
                "duration_seconds": duration_seconds,
                "search_query": broad_query,
            }
        )
        excluded_ids.add(video_id)
        added += 1

    if added < needed:
        added += fill_queue_from_fallback(mood=mood)
    return added, None


def advance_queue_if_needed() -> bool:
    changed = False
    now = time.time()
    current_song = st.session_state.get("current_song")

    if current_song:
        started_at = float(current_song.get("started_at") or now)
        duration_seconds = int(current_song.get("duration_seconds") or 0)
        if duration_seconds and now >= started_at + duration_seconds:
            st.session_state.current_song = None
            st.session_state.active_video_id = None
            st.session_state.player_rendered_video_id = None
            st.session_state.player_component_html = None
            st.session_state.is_playing = False
            changed = True

    if not st.session_state.get("current_song") and st.session_state.get("song_queue"):
        next_song = st.session_state.song_queue.pop(0)
        next_song["started_at"] = now
        st.session_state.current_song = next_song
        st.session_state.active_video_id = next_song.get("video_id")
        st.session_state.is_playing = True
        changed = True

    if not st.session_state.get("current_song") and not st.session_state.get("song_queue"):
        st.session_state.active_video_id = None
        st.session_state.player_rendered_video_id = None
        st.session_state.player_component_html = None
        st.session_state.is_playing = False

    return changed

def search_youtube_music(search_query: str) -> dict | None:
    youtube_api_key = read_secret("YOUTUBE_API_KEY")
    if not youtube_api_key:
        return None

    search_params = {
        "part": "snippet",
        "q": search_query,
        "type": "video",
        "videoEmbeddable": "true",
        "maxResults": 5,
        "safeSearch": "moderate",
        "key": youtube_api_key,
    }
    search_response = requests.get(
        "https://www.googleapis.com/youtube/v3/search", params=search_params, timeout=12
    )
    search_response.raise_for_status()
    items = search_response.json().get("items", [])
    if not items:
        return None

    video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
    if not video_ids:
        return None

    details_response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "contentDetails,snippet", "id": ",".join(video_ids), "key": youtube_api_key},
        timeout=12,
    )
    details_response.raise_for_status()
    details_map = {v["id"]: v for v in details_response.json().get("items", [])}

    wants_background = any(
        token in search_query.lower() for token in ["background", "study", "focus", "work", "sleep", "cafe", "coffee"]
    )
    ranking_keywords = {"music", "study", "ambient", "lofi", "focus", "background", "instrumental", "playlist"}

    scored: list[tuple[int, dict]] = []
    for item in items:
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        haystack = f"{title} {description}".lower()
        if "shorts" in haystack or "#shorts" in haystack:
            continue

        details = details_map.get(video_id, {})
        duration_seconds = parse_iso8601_duration(details.get("contentDetails", {}).get("duration", ""))
        if duration_seconds < 120:
            continue

        score = sum(2 for k in ranking_keywords if k in haystack)
        if wants_background:
            if duration_seconds >= 1800:
                score += 8
            elif duration_seconds >= 900:
                score += 5
            elif duration_seconds >= 300:
                score += 2
        else:
            if duration_seconds >= 180:
                score += 2
        scored.append(
            (
                score,
                {
                    "title": title,
                    "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel": snippet.get("channelTitle", "Unknown channel"),
                    "description": description,
                },
            )
        )

    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def render_ai_music_finder() -> None:
    st.subheader("AI Music Finder")
    st.caption("Auto-DJ can keep a rolling queue of short YouTube songs (<=5 minutes).")

    if "ai_music_prompt" not in st.session_state:
        default_prompt, _, _, _ = build_autodj_bootstrap_inputs(st.session_state.live)
        st.session_state.ai_music_prompt = default_prompt

    with st.container(border=True):
        prompt = st.text_area(
            "Describe the music you want",
            key="ai_music_prompt",
            placeholder="I want calm Genshin-style music for studying at night",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            setting = st.selectbox("setting", [""] + AI_SETTINGS, key="ai_music_setting")
        with c2:
            energy = st.selectbox("energy", [""] + AI_ENERGY_OPTIONS, key="ai_music_energy")
        with c3:
            vocals = st.selectbox("vocals", [""] + AI_VOCALS_OPTIONS, key="ai_music_vocals")

        st.toggle("Auto-DJ", key="auto_dj_enabled")

        b1, b2, b3 = st.columns([1, 1, 1])
        with b1:
            skip_clicked = st.button("Skip Song", use_container_width=True)
        with b2:
            refresh_clicked = st.button("Refresh Queue", use_container_width=True)
        with b3:
            search_add_clicked = st.button("Search & Add", use_container_width=True)

    if prompt.strip():
        try:
            interpretation = analyze_music_prompt(
                prompt=prompt.strip(),
                setting=setting or None,
                energy=energy or None,
                vocals=vocals or None,
            )
            st.session_state.ai_music_interpretation = interpretation
        except Exception as exc:
            st.warning(f"Could not update AI interpretation: {exc}")

    if search_add_clicked:
        if len(st.session_state.song_queue) >= MAX_QUEUE_SIZE:
            st.warning("Queue is full (max 5 songs).")
        else:
            needed = MAX_QUEUE_SIZE - len(st.session_state.song_queue)
            add_songs_to_queue(get_ai_youtube_song_candidates(max_needed=needed))
            st.session_state.last_ai_search_time = time.time()
            st.rerun()

    if skip_clicked:
        st.session_state.current_song = None
        st.session_state.song_start_time = 0
        st.rerun()

    if refresh_clicked:
        candidate_songs = get_ai_youtube_song_candidates(max_needed=MAX_QUEUE_SIZE - len(st.session_state.song_queue))
        add_songs_to_queue(candidate_songs)
        st.session_state.last_ai_search_time = time.time()
        st.rerun()

    interpretation = st.session_state.get("ai_music_interpretation")
    if interpretation:
        st.markdown("#### AI interpretation")
        st.json(
            {
                "mood": interpretation["mood"],
                "bpm_range": [interpretation["bpm_min"], interpretation["bpm_max"]],
                "energy": interpretation["energy"],
                "search_query": interpretation["search_query"],
                "reason": interpretation["reason"],
            }
        )



def filter_tracks_by_controls(
    tracks: list[dict], min_bpm: int, max_bpm: int, desired_moods: list[str], allow_unknown_license: bool = True
) -> list[dict]:
    filtered: list[dict] = []
    for track in tracks:
        if not allow_unknown_license and track["license_status"] == "Unknown":
            continue
        if not (min_bpm <= track["bpm"] <= max_bpm):
            continue
        if desired_moods and not set(desired_moods).intersection(set(track["mood_tags"])):
            continue
        filtered.append(track)
    return filtered


def score_track(
    track: dict,
    business_type: str,
    time_of_day: str,
    desired_goal: str,
    desired_moods: list[str],
    crowd_level: int,
    noise_level: int,
    min_bpm: int,
    max_bpm: int,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if min_bpm <= track["bpm"] <= max_bpm:
        score += 30
        reasons.append("BPM is inside your selected range (+30).")

    mood_overlap = set(desired_moods).intersection(set(track["mood_tags"])) if desired_moods else set()
    if not desired_moods:
        score += 25
        reasons.append("No mood filter set, so this track remains mood-compatible (+25).")
    elif mood_overlap:
        score += 25
        reasons.append(f"Mood match found: {', '.join(sorted(mood_overlap))} (+25).")

    if track["best_time_of_day"] in {time_of_day, "Any"}:
        score += 15
        reasons.append("Time-of-day match (+15).")

    if track["best_business_type"] in {business_type, "Any"}:
        score += 15
        reasons.append("Business-type match (+15).")

    energy_score = 0
    if noise_level >= 70 and track["energy"] <= 55:
        energy_score = 10
        reasons.append("High noise environment: lower-energy track preferred (+10).")
    elif crowd_level <= 35 and desired_goal == "Increase energy" and track["energy"] >= 65:
        energy_score = 10
        reasons.append("Low crowd + increase-energy goal: higher energy is preferred (+10).")
    elif 40 <= track["energy"] <= 70:
        energy_score = 10
        reasons.append("Energy is balanced for current crowd/noise conditions (+10).")
    score += energy_score

    if track["license_status"] in {"Royalty-free", "Commercially licensed"}:
        score += 5
        reasons.append("Track has known safe license status (+5).")

    premium_genres = {"jazz", "acoustic", "lounge"}
    premium_moods = {"Calm", "Luxury", "Premium"}
    if desired_goal == "Premium experience":
        if premium_moods.intersection(set(track["mood_tags"])) or track["genre"].lower() in premium_genres:
            score += 8
            reasons.append("Supports premium-experience goal (calm/luxury/premium/jazz/acoustic/lounge bias).")

    if desired_goal == "Faster turnover" and track["bpm"] >= 105:
        score += 8
        reasons.append("Higher BPM supports faster-turnover intent.")
    if desired_goal == "Increase dwell time" and track["bpm"] <= 92:
        score += 8
        reasons.append("Lower BPM supports longer dwell time.")

    return score, reasons


def recommend_track(
    tracks: list[dict],
    business_type: str,
    time_of_day: str,
    desired_goal: str,
    desired_moods: list[str],
    min_bpm: int,
    max_bpm: int,
    crowd_level: int,
    noise_level: int,
) -> dict | None:
    eligible_tracks = filter_tracks_by_controls(
        tracks=tracks,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        desired_moods=desired_moods,
        allow_unknown_license=False,
    )
    if not eligible_tracks:
        return None

    ranked: list[dict] = []
    for track in eligible_tracks:
        score, reasons = score_track(
            track=track,
            business_type=business_type,
            time_of_day=time_of_day,
            desired_goal=desired_goal,
            desired_moods=desired_moods,
            crowd_level=crowd_level,
            noise_level=noise_level,
            min_bpm=min_bpm,
            max_bpm=max_bpm,
        )
        ranked.append({"track": track, "score": score, "reasons": reasons})

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[0]


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


def infer_time_of_day(hour_24: int) -> str:
    if 5 <= hour_24 <= 10:
        return "Morning"
    if 11 <= hour_24 <= 14:
        return "Lunch"
    if 15 <= hour_24 <= 17:
        return "Afternoon"
    if 18 <= hour_24 <= 22:
        return "Dinner"
    return "Late Night"


def apply_autopilot(profile: dict, live: dict) -> tuple[dict, list[str]]:
    updated = dict(live)
    notes: list[str] = []

    current_hour = datetime.now().hour
    inferred_block = infer_time_of_day(current_hour)
    if updated["time_of_day"] != inferred_block:
        updated["time_of_day"] = inferred_block
        notes.append(f"Time block auto-set to **{inferred_block}** from current hour ({current_hour:02d}:00).")

    goal_based_outcome = _map_business_goal_to_outcome(profile["default_goal"])
    desired_outcome = goal_based_outcome
    if live["crowd_level"] >= 80:
        desired_outcome = "Move people faster"
        notes.append("High crowd detected, so the AI optimized for faster turnover.")
    elif live["crowd_level"] <= 25:
        desired_outcome = "Keep people longer"
        notes.append("Low crowd detected, so the AI optimized to increase dwell time.")
    elif live["noise_level"] >= 75:
        desired_outcome = "Calm people down"
        notes.append("High ambient noise detected, so the AI optimized to calm the room.")

    updated["desired_outcome"] = desired_outcome
    if not notes:
        notes.append("Autopilot kept your current settings because live conditions are stable.")
    return updated, notes


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


def build_adjustment_actions(rec: dict, live: dict) -> list[dict]:
    actions: list[dict] = []
    crowd_level = live["crowd_level"]
    noise_level = live["noise_level"]
    current_energy = live["current_energy"]

    target_energy = rec["energy"].lower()
    energy_map = {"low": 30, "low-medium": 45, "medium": 55, "medium-high": 70, "high": 82}
    target_energy_score = energy_map.get(target_energy, 50)
    gap = target_energy_score - current_energy

    if gap >= 12:
        actions.append(
            {
                "action": "Raise energy in small steps",
                "how": "Add 2-3 higher-BPM tracks every 10 minutes until the room reaches your target vibe.",
                "priority": "High",
            }
        )
    elif gap <= -12:
        actions.append(
            {
                "action": "Lower intensity gradually",
                "how": "Switch to smoother tracks and reduce rhythmic density over 10-15 minutes.",
                "priority": "High",
            }
        )
    else:
        actions.append(
            {
                "action": "Hold current energy",
                "how": "Keep a stable blend and avoid abrupt jumps in BPM or track intensity.",
                "priority": "Medium",
            }
        )

    if crowd_level >= 75:
        actions.append(
            {
                "action": "Prioritize clarity over loudness",
                "how": "Choose cleaner mixes with less sonic clutter so conversations stay comfortable.",
                "priority": "High",
            }
        )
    elif crowd_level <= 25:
        actions.append(
            {
                "action": "Warm up the room",
                "how": "Use familiar, melodic tracks with moderate momentum to reduce 'empty room' feel.",
                "priority": "Medium",
            }
        )

    if noise_level >= 70:
        actions.append(
            {
                "action": "Avoid volume escalation",
                "how": "Do not chase ambient noise with more volume; instead use lighter arrangements.",
                "priority": "High",
            }
        )
    elif noise_level <= 25:
        actions.append(
            {
                "action": "Protect quiet comfort",
                "how": "Keep transitions gentle and maintain lower volume to avoid startling guests.",
                "priority": "Medium",
            }
        )

    actions.append(
        {
            "action": "Re-check every 15 minutes",
            "how": "Update crowd, noise, and energy inputs and let Whisper refresh the recommendation.",
            "priority": "Always",
        }
    )
    return actions


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


def atmosphere_snapshot(live: dict) -> tuple[str, str]:
    noise = live["noise_level"]
    crowd = live["crowd_level"]

    if noise >= 75:
        return "Loud", "Conversation strain detected"
    if noise >= 60:
        return "Active", "Conversation requires effort"
    if crowd <= 20 and noise <= 30:
        return "Too quiet", "Space feels flat for current traffic"
    return "Balanced", "Conversation comfort is healthy"


def time_context_label(time_of_day: str) -> str:
    now_text = datetime.now().strftime("%-I:%M %p")
    rush_map = {
        "Morning": "Morning setup in progress",
        "Lunch": "Lunch flow in progress",
        "Afternoon": "Afternoon pace in progress",
        "Dinner": "Dinner Rush in progress",
        "Late Night": "Late-night shift in progress",
    }
    return f"{now_text} ({rush_map.get(time_of_day, 'Operational block in progress')})"


def transition_plan(live: dict) -> list[str]:
    steps: list[str] = []
    noise = live["noise_level"]
    crowd = live["crowd_level"]

    if noise >= 70:
        steps.append("Reducing volume ceiling by 6% to improve speech clarity.")
    else:
        steps.append("Maintaining current volume ceiling while monitoring speech clarity.")

    if crowd >= 75:
        steps.append("Selecting cleaner, less dense tracks for crowded conditions.")
    elif crowd <= 25:
        steps.append("Introducing warmer tracks to prevent an empty-room feel.")
    else:
        steps.append("Holding a steady playlist profile for current occupancy.")

    steps.append("Re-scoring atmosphere every 15 minutes to keep conditions aligned.")
    return steps


def extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([^&]+)",
        r"(?:youtu\.be/)([^?&]+)",
        r"(?:youtube\.com/embed/)([^?&]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def render_youtube_audio_player(video_id: str, title: str = "", duration_seconds: int = 0) -> None:
    if not video_id:
        st.error("Missing YouTube video ID for player rendering.")
        return

    embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    st.iframe(embed_url, height=170)


def run_autodj_cycle() -> None:
    maybe_finish_current_song()
    maybe_start_next_song()
    maybe_refill_queue()
    maybe_start_next_song()


def render_now_playing_and_queue() -> None:
    run_autodj_cycle()

    st.markdown("### Now Playing (YouTube)")
    current_song = st.session_state.get("current_song")
    if current_song:
        render_youtube_audio_player(
            current_song.get("video_id", ""),
            current_song.get("title", "Unknown title"),
            duration_seconds=int(current_song.get("duration_seconds") or 0),
        )
        st.caption(
            f"{current_song.get('title', 'Unknown title')} · "
            f"{current_song.get('channel', 'Unknown channel')} · "
            f"{format_duration(int(current_song.get('duration_seconds') or 0))}"
        )
    else:
        st.info("No song currently playing. Auto-DJ will start once queue has songs.")

    st.markdown("### Queue (live updates, max 5 songs)")
    queue = st.session_state.get("song_queue", [])[:MAX_QUEUE_SIZE]
    if queue:
        for idx, song in enumerate(queue, start=1):
            st.write(
                f"{idx}. {song.get('title', 'Unknown title')} — "
                f"{song.get('channel', 'Unknown channel')} "
                f"({format_duration(int(song.get('duration_seconds') or 0))})"
            )
    else:
        st.caption("Queue is empty.")

    if st.session_state.get("auto_dj_enabled", True):
        st.caption("Auto-DJ is active. This panel refreshes every 20 seconds to show queue changes.")
        st.components.v1.html(
            """
            <script>
            setTimeout(() => window.parent.location.reload(), 20000);
            </script>
            """,
            height=0,
        )


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

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%);
            color: #0f172a;
        }
        .block-container {
            padding-top: 1.1rem;
            max-width: 1120px;
        }
        .stAlert {
            border-radius: 12px;
        }
        [data-testid="stSidebar"] {
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.35rem 0.55rem;
        }
        .stButton > button {
            background: linear-gradient(120deg, #2563eb, #4f46e5);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
        }
        .stButton > button:hover {
            filter: brightness(1.05);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.3rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: #e2e8f0;
            border-radius: 999px;
            padding: 0.35rem 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎵 Whisper")

show_secondary = st.sidebar.toggle("Show secondary workspaces", value=False)
st.sidebar.caption("Turn this on when you want AI recommendation, library, schedule, analytics, or profile editors.")

if show_secondary:
    live_tab, rec_tab, library_tab, sched_tab, analytics_tab, profile_tab, finder_tab = st.tabs(
        [
            "1) Live Atmosphere Control",
            "2) AI Recommendation",
            "3) Music Library",
            "4) Schedule Builder",
            "5) Analytics / Experiment Tracker",
            "6) Business Profile (Optional)",
            "7) AI Music Finder (Hidden)",
        ]
    )
else:
    live_tab = st.container()
    rec_tab = library_tab = sched_tab = analytics_tab = profile_tab = finder_tab = None

if show_secondary and profile_tab is not None:
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

        st.success("Profile saved in this session. These fields are optional for MVP use.")

with live_tab:
    st.subheader("Live Atmosphere Control")
    render_now_playing_and_queue()

    with st.container(border=True):
        auto_pressed = st.button("Let Whisper Handle This", type="primary", use_container_width=True)
        if auto_pressed:
            st.session_state.live["autopilot_enabled"] = True
            updated_live, autopilot_notes = apply_autopilot(st.session_state.profile, st.session_state.live)
            st.session_state.live.update(updated_live)
            st.session_state.live["last_transition_notes"] = autopilot_notes + transition_plan(st.session_state.live)

    if st.session_state.live.get("autopilot_enabled"):
        st.info("Whisper is actively adapting your space. Monitoring never stops after this transition.")

        with st.container(border=True):
            st.markdown("#### Current adjustment")
            progress = st.progress(0, text="Preparing atmosphere shift...")
            for pct in [20, 40, 60, 80, 100]:
                progress.progress(pct, text=f"Applying gradual transition... {pct}%")
                time.sleep(0.05)

            for note in st.session_state.live.get("last_transition_notes", []):
                st.write(f"- {note}")

            st.success(
                "Transition synced with the current atmosphere goal. Whisper remains in continuous monitoring mode and will keep adjusting automatically."
            )

    with st.expander("Advanced controls (optional)"):
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

        st.markdown("##### Music Filters")
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            st.session_state.music_filters["min_bpm"] = st.slider(
                "Minimum BPM", 50, 160, value=st.session_state.music_filters["min_bpm"]
            )
        with f2:
            st.session_state.music_filters["max_bpm"] = st.slider(
                "Maximum BPM", 50, 160, value=st.session_state.music_filters["max_bpm"]
            )
        if st.session_state.music_filters["min_bpm"] > st.session_state.music_filters["max_bpm"]:
            st.session_state.music_filters["max_bpm"] = st.session_state.music_filters["min_bpm"]
        with f3:
            st.session_state.music_filters["desired_moods"] = st.multiselect(
                "Desired moods",
                options=LIBRARY_MOODS,
                default=st.session_state.music_filters["desired_moods"],
            )

        filtered_preview = filter_tracks_by_controls(
            tracks=st.session_state.music_library,
            min_bpm=st.session_state.music_filters["min_bpm"],
            max_bpm=st.session_state.music_filters["max_bpm"],
            desired_moods=st.session_state.music_filters["desired_moods"],
            allow_unknown_license=True,
        )
        st.caption(f"{len(filtered_preview)} track(s) match current live filters.")

    st.divider()
    current_atmosphere, atmosphere_issue = atmosphere_snapshot(st.session_state.live)
    time_context = time_context_label(st.session_state.live["time_of_day"])
    st.markdown(f"### Current Atmosphere: **{current_atmosphere}** ({atmosphere_issue})")
    st.write(f"**Time of day:** {time_context}")
    st.write("**System Status:** Monitoring noise and conversation levels")

if show_secondary and finder_tab is not None:
    with finder_tab:
        render_ai_music_finder()

if show_secondary and rec_tab is not None:
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

        track_result = recommend_track(
            tracks=st.session_state.music_library,
            business_type=st.session_state.profile["business_type"],
            time_of_day=st.session_state.live["time_of_day"],
            desired_goal=st.session_state.profile["default_goal"],
            desired_moods=st.session_state.music_filters["desired_moods"],
            min_bpm=st.session_state.music_filters["min_bpm"],
            max_bpm=st.session_state.music_filters["max_bpm"],
            crowd_level=st.session_state.live["crowd_level"],
            noise_level=st.session_state.live["noise_level"],
        )

        st.markdown("### Suggested Track from Your Music Library")
        with st.container(border=True):
            if track_result is None:
                st.warning(
                    "No matching tracks found. Try widening the BPM range, selecting fewer moods, or adding more tracks."
                )
            else:
                selected = track_result["track"]
                st.write(f"**{selected['title']}** — {selected['artist']}")
                st.write(f"Genre: {selected['genre']} | BPM: {selected['bpm']} | Energy: {selected['energy']}/100")
                st.write(
                    f"Best fit: {selected['best_time_of_day']} / {selected['best_business_type']} | License: {selected['license_status']}"
                )
                st.success(f"Match score: {track_result['score']}")
                st.markdown("**Why this was selected**")
                for reason in track_result["reasons"]:
                    st.write(f"- {reason}")

                file_path = selected["file_path"].strip()
                if file_path and os.path.exists(file_path):
                    st.audio(file_path)
                else:
                    st.caption("Audio preview unavailable. Add a valid local MP3 file path.")

        st.markdown("### AI Adjustment Copilot")
        st.caption("A quick execution plan so the AI handles most of the moment-to-moment music adjustments.")
        actions = build_adjustment_actions(rec, st.session_state.live)
        with st.container(border=True):
            for idx, step in enumerate(actions, start=1):
                st.markdown(f"**{idx}. {step['action']}**  \nPriority: `{step['priority']}`  \n{step['how']}")

if show_secondary and library_tab is not None:
    with library_tab:
        st.subheader("Music Library")
        with st.container(border=True):
            with st.form("add_track_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    track_title = st.text_input("Track title")
                    artist = st.text_input("Artist")
                    file_path = st.text_input("File path or URL")
                    bpm = st.number_input("BPM", min_value=40, max_value=220, value=95, step=1)
                    mood_tags = st.multiselect("Mood tags", options=LIBRARY_MOODS, default=["Calm"])
                with c2:
                    genre = st.text_input("Genre", value="Ambient")
                    energy = st.slider("Energy level", 0, 100, value=50)
                    best_time = st.selectbox("Best time of day", options=TIME_OF_DAY_OPTIONS, index=5)
                    best_business = st.selectbox("Best business type", options=BUSINESS_TYPE_OPTIONS, index=0)
                    license_status = st.selectbox("License status", options=LICENSE_OPTIONS, index=0)

                add_track = st.form_submit_button("Add track", type="primary")
                if add_track:
                    if not track_title.strip():
                        st.error("Track title is required.")
                    else:
                        st.session_state.music_library.append(
                            {
                                "title": track_title.strip(),
                                "artist": artist.strip() or "Unknown Artist",
                                "file_path": file_path.strip(),
                                "bpm": int(bpm),
                                "mood_tags": mood_tags,
                                "genre": genre.strip() or "Unknown",
                                "energy": energy,
                                "best_time_of_day": best_time,
                                "best_business_type": best_business,
                                "license_status": license_status,
                            }
                        )
                        st.success("Track added to session library.")

        library_df = pd.DataFrame(st.session_state.music_library)
        if library_df.empty:
            st.info("No tracks in the library yet.")
        else:
            show_df = library_df.copy()
            show_df["mood_tags"] = show_df["mood_tags"].apply(lambda vals: ", ".join(vals))
            st.dataframe(show_df, use_container_width=True, hide_index=True)

if show_secondary and sched_tab is not None:
    with sched_tab:
        st.subheader("Daily schedule builder")
        with st.container(border=True):
            if st.button("Generate sample daily schedule", type="primary"):
                st.session_state.generated_schedule = build_schedule(st.session_state.profile)

            schedule_df = st.session_state.get("generated_schedule", build_schedule(st.session_state.profile))
            st.dataframe(schedule_df, use_container_width=True, hide_index=True)

if show_secondary and analytics_tab is not None:
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
