# pages/1_calendar.py
# カレンダー（FullCalendarのドット表示）＋「確定 / 予備日」色分け＋本番カウントダウン
#
# 依存:
#   pip install streamlit-calendar
# secrets.toml 必須キー:
#   ICS_URL
#   PERFORMANCE_DATETIME  # "YYYY-MM-DD HH:MM"
# 任意キー:
#   PERFORMANCE_TITLE
#   CONFIRMED_TAG, RESERVE_TAG
#   COLOR_CONFIRMED, COLOR_RESERVE, COLOR_OTHER

from __future__ import annotations

import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from streamlit_calendar import calendar

from lib.auth import require_auth
from lib.calendar_ics import load_events_df, get_fixed_performance_target
from lib.gcal_link import parse_iso_date_or_dt, build_google_calendar_url

JST = ZoneInfo("Asia/Tokyo")


def _clean_title_and_color(title: str) -> tuple[str, str]:
    """
    returns: (cleaned_title, color)
    - タイトルの先頭に「確定/その他」などは付けない（2重表記防止）
    - 判定に使うタグ（例: 【確定】）は表示から除去
    """
    conf_tag = st.secrets.get("CONFIRMED_TAG", "【確定】")
    resv_tag = st.secrets.get("RESERVE_TAG", "【予備】")

    color_conf = st.secrets.get("COLOR_CONFIRMED", "#2E7D32")  # green
    color_resv = st.secrets.get("COLOR_RESERVE", "#F9A825")    # yellow
    color_other = st.secrets.get("COLOR_OTHER", "#1E88E5")     # blue

    t = (title or "").strip()

    if conf_tag in t:
        cleaned = t.replace(conf_tag, "").strip()
        return cleaned, color_conf

    if resv_tag in t:
        cleaned = t.replace(resv_tag, "").strip()
        return cleaned, color_resv

    return t, color_other


def _extract_clicked_event(state: object) -> dict | None:
    """streamlit-calendar の返り値からクリックされた event dict を取り出す"""
    if not isinstance(state, dict):
        return None

    ec = state.get("eventClick")
    if not ec:
        return None

    # 典型: {"event": {...}, "view": {...}, ...}
    if isinstance(ec, dict) and isinstance(ec.get("event"), dict):
        return ec["event"]

    # まれに event 本体が直で来るケースにも保険をかける
    if isinstance(ec, dict):
        return ec

    return None


def _normalize_start_end(clicked: dict) -> tuple[date | datetime | None, date | datetime | None]:
    """
    FullCalendar の start/end を date or datetime に寄せる。
    - all-day: "YYYY-MM-DD" -> date
    - timed: ISO datetime -> datetime (JST)
    """
    start_raw = clicked.get("start")
    end_raw = clicked.get("end")

    start: date | datetime | None = None
    end: date | datetime | None = None

    if isinstance(start_raw, str) and start_raw:
        start = parse_iso_date_or_dt(start_raw)
    elif isinstance(start_raw, datetime):
        start = start_raw.astimezone(JST) if start_raw.tzinfo else start_raw.replace(tzinfo=JST)
    elif isinstance(start_raw, date):
        start = start_raw

    if isinstance(end_raw, str) and end_raw:
        end = parse_iso_date_or_dt(end_raw)
    elif isinstance(end_raw, datetime):
        end = end_raw.astimezone(JST) if end_raw.tzinfo else end_raw.replace(tzinfo=JST)
    elif isinstance(end_raw, date):
        end = end_raw

    # end が無い場合のデフォルト（表示/リンク用）
    if start is not None and end is None:
        if isinstance(start, datetime):
            end = start + timedelta(hours=1)
        else:
            end = start + timedelta(days=1)

    # datetime同士ならJSTへ
    if isinstance(start, datetime) and start.tzinfo is None:
        start = start.replace(tzinfo=JST)
    if isinstance(end, datetime) and end.tzinfo is None:
        end = end.replace(tzinfo=JST)

    if isinstance(start, datetime):
        start = start.astimezone(JST)
    if isinstance(end, datetime):
        end = end.astimezone(JST)

    return start, end


def main() -> None:
    st.set_page_config(page_title="カレンダー", page_icon="📅", layout="wide")
    require_auth()

    st.title("📅 カレンダー")

    # ===== 本番カウントダウン =====
    target_dt, target_title = get_fixed_performance_target()
    now = datetime.now(JST)
    delta = target_dt - now

    with st.container(border=True):
        st.subheader("⏳ 本番までのカウントダウン")
        st.write(f"**{target_title}**：{target_dt.strftime('%Y-%m-%d %H:%M')}（JST）")

        if delta.total_seconds() < 0:
            st.success("🎉 本番は開始済み（または終了済み）です。")
        else:
            days = delta.days
            hours = delta.seconds // 3600
            mins = (delta.seconds % 3600) // 60
            c1, c2, c3 = st.columns(3)
            c1.metric("日", f"{days}")
            c2.metric("時間", f"{hours}")
            c3.metric("分", f"{mins}")

    st.divider()

    # ===== iCal 読み込み =====
    ics_url = st.secrets["ICS_URL"]
    try:
        df = load_events_df(ics_url)
    except Exception as e:
        st.error("ICS の取得に失敗しました。ICS_URL が正しいか、ネットワーク接続を確認してください。")
        st.exception(e)
        st.stop()

    if df.empty:
        st.warning("予定が取得できませんでした（カレンダーが空、またはICSにイベントがありません）。")
        st.stop()

    # ===== events 変換（FullCalendar 用）=====
    events: list[dict] = []
    for _, r in df.iterrows():
        cleaned_title, color = _clean_title_and_color(str(r["title"]))
        events.append(
            {
                "title": cleaned_title,
                # streamlit-calendar は文字列を想定
                "start": r["start"].isoformat(),
                "end": r["end"].isoformat(),
                "backgroundColor": color,
                "borderColor": color,
                "extendedProps": {
                    "location": (r.get("location") or ""),
                },
            }
        )

    # ===== UI: 凡例と設定 =====
    conf_tag = st.secrets.get("CONFIRMED_TAG", "【確定】")
    resv_tag = st.secrets.get("RESERVE_TAG", "【予備】")

    st.markdown(
        f"""
- 🟢 **確定**（予定タイトルに `{conf_tag}` を含める：表示時はタグは消えます）
- 🟡 **予備日**（予定タイトルに `{resv_tag}` を含める：表示時はタグは消えます）
- 🔵 **その他**
        """.strip()
    )

    colA, colB = st.columns(2)
    with colA:
        view = st.selectbox("表示", ["月", "週", "リスト(週)"], index=0)
    with colB:
        show_time = st.checkbox("時刻を表示", value=True)

    initial_view = {"月": "dayGridMonth", "週": "timeGridWeek", "リスト(週)": "listWeek"}[view]

    calendar_options = {
        "initialView": initial_view,
        "locale": "ja",
        # ★ 月曜始まり（0=日, 1=月, ...）
        "firstDay": 1,
        # 月表示でも「ドット」っぽい表示にしたい → list-item
        # ※ timeGridWeek では通常のブロック表示になります
        "eventDisplay": "list-item" if initial_view == "dayGridMonth" else "auto",
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek",
        },
        "height": "auto",
        "displayEventTime": bool(show_time),
    }

    st.subheader("カレンダー")
    state = calendar(events=events, options=calendar_options, key="fullcalendar")

    # クリック情報を保持する箱
    if "selected_event" not in st.session_state:
        st.session_state.selected_event = None

    clicked = _extract_clicked_event(state)

    # クリックされたら保存（次のrerunでも残る）
    if clicked:
        st.session_state.selected_event = clicked

    # 表示に使うのは「今回クリック」or「前回保存」
    selected = st.session_state.selected_event


    # ===== クリックした予定の詳細表示＋Googleカレンダー追加 =====
    clicked = _extract_clicked_event(state)

    if selected:
        title = selected.get("title", "")
        location = (selected.get("extendedProps") or {}).get("location", "")

        start, end = _normalize_start_end(selected)

        if start and end:
            with st.container(border=True):
                st.subheader("📝 選択中の予定")
                st.write(f"**{title}**")

                if isinstance(start, datetime) and isinstance(end, datetime):
                    st.write(f"🕒 {start.strftime('%Y-%m-%d %H:%M')} 〜 {end.strftime('%H:%M')}")
                else:
                    # 終日
                    st.write(f"🕒 {start.strftime('%Y-%m-%d')}（終日）")

                if location:
                    st.write(f"📍 {location}")

                details = "共有ポータルから追加しました。必要ならメモを追記してください。"

                gcal_url = build_google_calendar_url(
                    title=title,
                    start=start,
                    end=end,
                    location=location,
                    details=details,
                    tz="Asia/Tokyo",
                )
                st.link_button("➕ Googleカレンダーに登録（自分のカレンダーへ）", gcal_url)
        else:
            st.info("クリック情報の時刻を解釈できませんでした。")

    # クリックしたイベントの情報（streamlit-calendar が返す場合のみ）
    if isinstance(state, dict) and state.get("eventClick"):
        with st.expander("選択中の予定（デバッグ）"):
            st.json(state["eventClick"], expanded=False)

    st.caption("※色分けしたい予定は、Googleカレンダーのタイトルに【確定】または【予備】を付けてください（表示時にはタグは消えます）。")


if __name__ == "__main__":
    main()
