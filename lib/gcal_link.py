from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Union

JST = ZoneInfo("Asia/Tokyo")


def parse_iso_date_or_dt(s: str) -> Union[date, datetime]:
    """
    FullCalendar から来る start/end を受け取り:
      - "YYYY-MM-DD" -> date (終日)
      - ISO datetime -> datetime (JST)
    """
    # all-day: "YYYY-MM-DD"
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return date.fromisoformat(s)

    # "....Z" は fromisoformat が読めないので補正
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    else:
        dt = dt.astimezone(JST)
    return dt


def _dt_to_gcal_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _d_to_gcal(d: date) -> str:
    return d.strftime("%Y%m%d")


def build_google_calendar_url(
    title: str,
    start: Union[date, datetime],
    end: Optional[Union[date, datetime]] = None,
    location: str = "",
    details: str = "",
    tz: str = "Asia/Tokyo",
) -> str:
    """
    Google Calendar の "予定作成テンプレ" URLを作る。
    """
    base = "https://calendar.google.com/calendar/render"
    params = {
        "action": "TEMPLATE",
        "text": title,
        "ctz": tz,
    }

    # all-day
    if isinstance(start, date) and not isinstance(start, datetime):
        if end is None:
            end = start + timedelta(days=1)
        if not (isinstance(end, date) and not isinstance(end, datetime)):
            raise TypeError("all-day start に対して end は date である必要があります")
        params["dates"] = f"{_d_to_gcal(start)}/{_d_to_gcal(end)}"
    else:
        if not isinstance(start, datetime):
            raise TypeError("timed event start は datetime である必要があります")
        if end is None:
            end = start + timedelta(hours=1)
        if not isinstance(end, datetime):
            raise TypeError("timed event end は datetime である必要があります")
        params["dates"] = f"{_dt_to_gcal_utc(start)}/{_dt_to_gcal_utc(end)}"

    if location:
        params["location"] = location
    if details:
        params["details"] = details

    return base + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
