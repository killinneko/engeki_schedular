# app.py
# ホーム：本番カウントダウン＋直近の予定（カード表示）
#   - 📍 Googleマップで開く
#   - ➕ Googleカレンダーに予定を追加（予定作成画面を開く）
#
# 前提:
# - lib/auth.py, lib/calendar_ics.py, lib/gcal_link.py が存在
# - .streamlit/secrets.toml に以下がある:
#     ICS_URL
#     AUTH_SALT / AUTH_HASH
#     PERFORMANCE_DATETIME ("YYYY-MM-DD HH:MM")
#   任意:
#     PERFORMANCE_TITLE
#     CONFIRMED_TAG, RESERVE_TAG
#     COLOR_CONFIRMED, COLOR_RESERVE, COLOR_OTHER
#
# 起動:
#   streamlit run app.py

from __future__ import annotations

import html
from urllib.parse import quote_plus
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from lib.auth import require_auth
from lib.calendar_ics import load_events_df, get_fixed_performance_target
from lib.gcal_link import build_google_calendar_url

JST = ZoneInfo("Asia/Tokyo")


def build_google_maps_search_url(query: str) -> str:
    q = (query or "").strip()
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(q)}"


def render_countdown() -> None:
    """本番までのカウントダウンを表示"""
    target_dt, target_title = get_fixed_performance_target()
    now = datetime.now(JST)
    delta = target_dt - now

    st.subheader("⏳ 本番までのカウントダウン")

    if delta.total_seconds() < 0:
        st.success(f"🎉 {target_title} は開始済み（{target_dt.strftime('%Y-%m-%d %H:%M')}）")
        return

    days = delta.days
    hours = delta.seconds // 3600
    mins = (delta.seconds % 3600) // 60

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("日", f"{days}")
    c2.metric("時間", f"{hours}")
    c3.metric("分", f"{mins}")
    c4.metric("本番日時", target_dt.strftime("%Y-%m-%d %H:%M"))


def inject_card_css() -> None:
    """カード/バッジ/ドット用の最小CSS"""
    st.markdown(
        """
<style>
/* dot */
.dot {
  width: 10px; height: 10px; border-radius: 999px;
  margin-top: 8px;
  box-shadow: 0 0 0 4px rgba(0,0,0,0.03);
}

/* text */
.event-title { font-weight: 700; font-size: 1.02rem; line-height: 1.25; margin: 0; word-break: break-word; }
.event-meta  { color: rgba(0,0,0,0.62); font-size: 0.92rem; margin-top: 4px; word-break: break-word; line-height: 1.35; }

/* badge */
.badge {
  display: inline-block;
  font-size: 0.78rem;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(0,0,0,0.12);
  background: rgba(255,255,255,0.8);
  white-space: nowrap;
}
.badge-confirmed { border-color: rgba(46,125,50,0.35); color: #2E7D32; }
.badge-reserve   { border-color: rgba(249,168,37,0.45); color: #F9A825; }
.badge-other     { border-color: rgba(30,136,229,0.35); color: #1E88E5; }
</style>
""",
        unsafe_allow_html=True,
    )


def render_upcoming_cards(df) -> None:
    """直近の予定をカード表示（Googleマップ / Googleカレンダーボタン付き）"""
    inject_card_css()

    CONF_TAG = st.secrets.get("CONFIRMED_TAG", "【確定】")
    RESV_TAG = st.secrets.get("RESERVE_TAG", "【予備】")

    COLOR_CONF = st.secrets.get("COLOR_CONFIRMED", "#2E7D32")  # 緑
    COLOR_RESV = st.secrets.get("COLOR_RESERVE", "#F9A825")    # 黄
    COLOR_OTHER = st.secrets.get("COLOR_OTHER", "#1E88E5")     # 青

    def parse_status(title: str):
        t = (title or "").strip()
        if CONF_TAG in t:
            return "確定", t.replace(CONF_TAG, "").strip(), COLOR_CONF, "badge-confirmed"
        if RESV_TAG in t:
            return "予備", t.replace(RESV_TAG, "").strip(), COLOR_RESV, "badge-reserve"
        return "その他", t, COLOR_OTHER, "badge-other"

    st.subheader("🗓 直近の予定（10件）")

    now = datetime.now(JST)
    upcoming = df[df["end"] >= now].head(10).copy()

    if upcoming.empty:
        st.info("直近の予定がありません。")
        return

    # 表示オプション
    col1, col2 = st.columns([1, 1])
    with col1:
        show_location = st.toggle("場所を表示", value=True)
    with col2:
        show_weekday = st.toggle("曜日を表示", value=True)

    wd = ["月", "火", "水", "木", "金", "土", "日"]

    for _, r in upcoming.iterrows():
        status, clean_title, color, badge_cls = parse_status(str(r["title"]))
        start = r["start"]
        end = r["end"]
        loc = (r.get("location") or "").strip()

        # 保険：end が無い/NaT の場合は 1時間後にする
        try:
            if end is None or (hasattr(end, "to_pydatetime") and end.to_pydatetime() is None):
                end = start + timedelta(hours=1)
        except Exception:
            end = start + timedelta(hours=1)

        if show_weekday:
            start_str = f"{start:%m/%d}({wd[start.weekday()]}) {start:%H:%M}"
            end_str = f"{end:%H:%M}"
        else:
            start_str = f"{start:%m/%d %H:%M}"
            end_str = f"{end:%H:%M}"

        title_esc = html.escape(clean_title)
        loc_html = html.escape(loc).replace("\n", "<br/>")

        # Googleカレンダー追加URL（予定作成画面）
        details = f"ステータス: {status}\n共有ポータルから追加しました。"
        gcal_url = build_google_calendar_url(
            title=clean_title,
            start=start,
            end=end,
            location=loc,
            details=details,
            tz="Asia/Tokyo",
        )

        # 1カード
        with st.container(border=True):
            c_dot, c_main, c_sc_btn,c_mp_btn = st.columns([0.02, 0.68, 0.15,0.15], vertical_alignment="top")

            with c_dot:
                st.markdown(f'<div class="dot" style="background:{color};"></div>', unsafe_allow_html=True)

            with c_main:
                st.markdown(f'<div class="event-title">{title_esc}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="event-meta">🕒 {start_str} – {end_str}</div>', unsafe_allow_html=True)

                if show_location and loc:
                    st.markdown(f'<div class="event-meta">📍 {loc_html}</div>', unsafe_allow_html=True)

            # with c_badge:
            #     st.markdown(f'<div class="badge {badge_cls}">{html.escape(status)}</div>', unsafe_allow_html=True)

            with c_sc_btn:
                # ボタンを縦に並べる
                st.link_button("➕予定", gcal_url, use_container_width=True)
            with c_mp_btn:
                if loc:
                    st.link_button("📍map", build_google_maps_search_url(loc), use_container_width=True)

    st.caption("※色分けしたい予定は、タイトルに【確定】または【予備】を付けてください（カード表示ではタグは消えます）。")


def main() -> None:
    st.set_page_config(page_title="Schedule Portal", page_icon="📅", layout="wide")

    # 認証
    require_auth()

    st.title("スキルアップ発表講座ポータル")

    # # 本番カウントダウン
    # with st.container(border=True):
    #     render_countdown()

    st.divider()

    # iCal 読み込み
    ics_url = st.secrets["ICS_URL"]
    try:
        df = load_events_df(ics_url)
    except Exception as e:
        st.error("ICS の取得に失敗しました。ICS_URL が正しいか、ネットワーク接続を確認してください。")
        st.exception(e)
        return

    if df.empty:
        st.warning("予定が取得できませんでした（カレンダーが空、またはICSにイベントがありません）。")
        return

    # 直近予定カード（Googleマップ / Googleカレンダー追加ボタン付き）
    render_upcoming_cards(df)

    st.caption("左メニューから「稽古場一覧」「本番会場」へ移動できます。")


if __name__ == "__main__":
    main()
