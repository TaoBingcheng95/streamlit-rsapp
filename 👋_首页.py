import streamlit as st
import ee

   
st.set_page_config(page_title="遥感工具集市",
    page_icon="👋",
    layout="wide")
    

st.write("# 欢迎来到遥感工具集市 👋")

st.write("")

st.markdown(
    """
    ##### 遥感工具集市提供一系列遥感工具，包括遥感影像的获取、遥感影像的展示、遥感影像的处理等。
"""
)

st.write("")

st.markdown(
    """
    ###### 👈 请在侧边栏选择一个工具使用！
"""
)

st.write("")


st.image('https://www.pandotrip.com/wp-content/uploads/2015/08/Top-10-Google-Great-Sandy-Photo-by-Google-Earth.jpg',
         width=880)