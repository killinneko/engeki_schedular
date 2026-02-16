import hashlib
import hmac
import streamlit as st

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def require_auth() -> None:
    if st.session_state.get("authed"):
        return

    st.title("🔒 スケジュールポータルサイト")
    pw = st.text_input("パスワード", type="password")

    if st.button("ログイン"):
        salt = st.secrets["AUTH_SALT"]
        stored_hash = st.secrets["AUTH_HASH"]
        given_hash = _hash_password(pw, salt)

        if hmac.compare_digest(given_hash, stored_hash):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("パスワードが違います")

    st.caption("※共有メンバーだけにパスワードを渡してください。")
    st.stop()
