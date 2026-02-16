import streamlit as st
from lib.auth import require_auth
from lib.places import get_performance_venues

st.set_page_config(page_title="本番会場", page_icon="🎪", layout="wide")
require_auth()

st.title("🎪 本番会場")

venues = get_performance_venues()
if not venues:
    st.info("本番会場が未登録です（secrets の PERFORMANCE_VENUES を設定してください）。")
    st.stop()

for v in venues:
    with st.container(border=True):
        st.subheader(v.get("name", "（名称未設定）"))
        if v.get("address"):
            st.write(v["address"])
        if v.get("access"):
            st.write(f"**アクセス**：{v['access']}")
        if v.get("note"):
            st.caption(v["note"])
        if v.get("map_url"):
            st.link_button("Googleマップで開く", v["map_url"])
