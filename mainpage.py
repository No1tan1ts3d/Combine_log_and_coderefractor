import streamlit as st

st.write("# Welcome to AI Tools Hub! 👋")

st.sidebar.success("Select a tools to get started")
st.markdown(
    """
    This is a collection of AI tools built with Streamlit and Python.
    Developed by Manjil.
"""
)

create_page = st.Page("fin1.py", title="Log Parser", icon=":material/add_circle:")
delete_page = st.Page("test1.py", title="Code Refractor", icon=":material/delete:")

pg = st.navigation([create_page, delete_page])
st.set_page_config(page_title="Data manager", page_icon=":material/edit:")
pg.run()

st.set_page_config(
    page_title="Ai Tools Hub",
    page_icon="👋",
)

