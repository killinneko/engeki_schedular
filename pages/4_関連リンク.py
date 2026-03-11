import streamlit as st

st.set_page_config(
    page_title="関連リンク",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 関連リンク")

links = st.secrets.get("links", [])

if not links:
    st.info("リンクが登録されていません。secrets.toml を確認してください。")
    st.stop()


# -----------------------------
# カテゴリ分け
# -----------------------------
groups = {}

for link in links:
    category = link.get("category", "その他")
    groups.setdefault(category, []).append(link)


# -----------------------------
# 表示
# -----------------------------
for category, items in groups.items():

    st.subheader(category)

    cols = st.columns(3)

    for i, link in enumerate(items):
        col = cols[i % 3]

        title = link.get("title", "")
        url = link.get("url", "#")
        icon = link.get("icon", "🔗")

        with col:
            st.markdown(
                f"""
                <a href="{url}" target="_blank">
                    <div style="
                        padding:16px;
                        border:1px solid #ddd;
                        border-radius:12px;
                        margin-bottom:12px;
                        text-align:center;
                        font-size:18px;
                        background-color:#fafafa;
                    ">
                        {icon}<br>
                        <b>{title}</b>
                    </div>
                </a>
                """,
                unsafe_allow_html=True
            )