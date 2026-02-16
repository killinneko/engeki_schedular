import streamlit as st

def get_rehearsal_places() -> list[dict]:
    return list(st.secrets.get("REHEARSAL_PLACES", []))

def get_performance_venues() -> list[dict]:
    return list(st.secrets.get("PERFORMANCE_VENUES", []))
