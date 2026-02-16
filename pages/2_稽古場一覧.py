import streamlit as st
from lib.auth import require_auth
from lib.places import get_rehearsal_places

st.set_page_config(page_title="稽古場一覧", page_icon="🏠", layout="wide")
require_auth()

st.title("🏠 稽古場一覧")

places = get_rehearsal_places()
if not places:
    st.info("稽古場が未登録です（secrets の REHEARSAL_PLACES を設定してください）。")
    st.stop()

for p in places:
    with st.container(border=True):
        st.subheader(p.get("name", "（名称未設定）"))
        if p.get("address"):
            st.write(p["address"])
        if p.get("note"):
            st.caption(p["note"])
        if p.get("map_url"):
            st.link_button("Googleマップで開く", p["map_url"])
