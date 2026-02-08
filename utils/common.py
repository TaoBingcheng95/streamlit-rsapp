import base64
import streamlit as st
from rio_tiler.colormap import cmap
import matplotlib.pyplot as plt

@st.cache_resource
def get_colormap_names():
    cmap_ids = plt.colormaps()
    colormaps = cmap.list()
    intersection = [x for x in cmap_ids if x.lower() in colormaps]
    return intersection

def download_button(object_to_download, download_filename):
    try:
        # some strings <-> bytes conversions necessary here
        b64 = base64.b64encode(object_to_download.encode()).decode()

    except AttributeError as e:
        b64 = base64.b64encode(object_to_download).decode()

    dl_link = f"""
    <html>
    <head>
    <title>Start Auto Download file</title>
    <script src="http://code.jquery.com/jquery-3.2.1.min.js"></script>
    <script>
    $('<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}" download="{download_filename}">')[0].click()
    </script>
    </head>
    </html>
    """
    return dl_link