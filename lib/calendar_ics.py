from __future__ import annotations

import re
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar

JST = ZoneInfo("Asia/Tokyo")

@st.cache_data(ttl=300)
def load_events_df(ics_url: str) -> pd.DataFrame:
    r = requests.get(ics_url, timeout=20)
    r.raise_for_status()

    cal = Calendar.from_ical(r.content)
    rows = []

    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue

        title = str(comp.get("summary", ""))
        location = str(comp.get("location", ""))

        dtstart = comp.get("dtstart").dt
        dtend = comp.get("dtend").dt if comp.get("dtend") else None

        def to_dt(x):
            if isinstance(x, datetime):
                return x.astimezone(JST) if x.tzinfo else x.replace(tzinfo=JST)
            return datetime(x.year, x.month, x.day, tzinfo=JST)

        start = to_dt(dtstart)
        end = to_dt(dtend) if dtend else (start + timedelta(hours=1))

        rows.append({"start": start, "end": end, "title": title, "location": location})

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("start").reset_index(drop=True)
    return df

def get_fixed_performance_target() -> tuple[datetime, str]:
    perf_dt = st.secrets["PERFORMANCE_DATETIME"]  # "YYYY-MM-DD HH:MM"
    perf_title = st.secrets.get("PERFORMANCE_TITLE", "本番")
    target = datetime.strptime(perf_dt, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    return target, perf_title

def classify_kind(title: str) -> str:
    # 表示の補助（任意）
    rules = st.secrets.get("KIND_RULES", {"本番": "本番", "ゲネ": "ゲネ", "稽古": "稽古"})
    for k, v in rules.items():
        if k in title:
            return v
    return "予定"
