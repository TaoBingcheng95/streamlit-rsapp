from shapely.geometry import Polygon
import folium
import streamlit as st
from folium.plugins import Draw

from streamlit_folium import st_folium

import geopandas as gpd

st.write("### 遥感影像分割 🈹")

left, right = st.columns([7, 3])
height = 750

with left:
    # map = folium.Map(location=[30.3, 120.2], zoom_start=12, map='Stamen Terrain')
    
    # 加载carto的地图
    # folium.TileLayer(
    # tiles='https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    # attr='carto dark',
    # name='carto dark',
    # overlay=False,
    # control=True).add_to(map)
    
    # st_data = st_folium(map, width=1200)
    
    map = folium.Map(location=[30.3, 120.2], zoom_start=12,  tiles=None)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', name='Google Satellite', attr='Google Satellite').add_to(map)
    draw = Draw(export=True).add_to(map)
    
with right:
    b = st.button('按钮')
    if b:
        bounds = draw.get_bounds()
        gdf = gpd.read_file('/app/data/50206e88-ccda-4f77-974d-3660d9b1f8bb/result.shp')
        folium.GeoJson(gdf).add_to(map)
        map.location
with left:    
    st_data = st_folium(map, width=1000, height=750, returned_objects=[])
    idd = 1
        