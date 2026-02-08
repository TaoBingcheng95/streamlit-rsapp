import folium
import streamlit as st
from folium.plugins import Draw

from streamlit_folium import st_folium

import os
import shutil
import json
import shapely
import geopandas

import torch
print(torch.cuda.is_available())

from seg import segutil,with_tif

st.write("### 遥感影像分割 🈹")

left, right = st.columns([7, 3])
with left:  
    map = folium.Map(location=[30.3, 120.2], zoom_start=12, tiles=None)    
    folium.TileLayer(
        tiles=
        'https://t2.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TileCol={x}&TileRow={y}&TileMatrix={z}&tk=d0a63baa051a4f9f4301f3e2373ecd29',
        attr='天地图矢量',
        name='天地图矢量',
        overlay=True,
        control=True).add_to(map)
    folium.TileLayer(
        tiles=
        'https://t2.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TileCol={x}&TileRow={y}&TileMatrix={z}&tk=d0a63baa051a4f9f4301f3e2373ecd29',
        attr='天地图注记',
        name='天地图注记',
        overlay=True,
        control=True).add_to(map)
    tif_url = 'http://minio:9000/vi-test/hzseg.tif'
    folium.TileLayer(tiles='http://192.168.148.214:8000/cog/tiles/{z}/{x}/{y}.png?url='+tif_url,
                    name='seg',
                    attr='seg',
                    overlay=True,
                    control=True).add_to(map)
    Draw(export=True).add_to(map)

    if "show" in st.session_state:
        if st.session_state.show:
            gdf = geopandas.read_file('/app/data/seg/shp/result/result.shp')
            g = folium.GeoJson(gdf.to_json()).add_to(map)
            b = g.get_bounds()
            map.fit_bounds(b)

    folium.LayerControl(position='bottomleft').add_to(map)    
    output = st_folium(map, width=1100, height=750, key='map1')

with right:
    btn = st.button('分析')
    if btn:
        tif_path = '/app/data/seg/tif/hzseg.tif'
        dest_dir = '/app/data/seg/tile'
        sam_checkpoint = '/app/data/seg/sam_vit_h_4b8939.pth'
        
        gj_str = json.dumps(output['last_active_drawing'])
        polygon = shapely.from_geojson(gj_str)
        # 切割成块
        id = segutil.split_tif(tif_path, dest_dir, polygon)

        tile_dir = os.path.join(dest_dir, id)

        # 跑AI
        with_tif.run(sam_checkpoint=sam_checkpoint, images_dir=f'{tile_dir}/*.tif')

        # 合并shp
        dest_dir = '/app/data/seg/shp/result'
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        os.mkdir(dest_dir)
        dest_shp = os.path.join(dest_dir, 'result.shp')
        segutil.merge_shps(tile_dir, dest_shp, polygon)
        
        shutil.rmtree(tile_dir)
            
        st.success('分析完成！')
            
        st.session_state['show'] = True
        st.experimental_rerun()

    
    
        
        

        
        