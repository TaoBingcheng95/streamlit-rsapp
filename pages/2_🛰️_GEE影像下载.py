### 认证 earthengine authenticate --auth_mode notebook

from io import BytesIO
from math import nan
import os
from datetime import datetime, timedelta
import re
import shutil

import ee
import geemap.foliumap as geemap
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components
from utils.common import download_button

from utils.gee_dataset import gee_datasets, get_gee_dataset
from utils.minio_util import list_tif, upload_minio



@st.cache_resource
def gee_init():
    ee.Initialize()
    
@st.cache_data
def uploaded_file_to_gdf(data):
    gdf = gpd.read_file(data)
    return gdf


# sentinel2
def maskS2clouds(image):
    qa = image.select('QA60')
    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloudBitMask = int(2**10)
    cirrusBitMask = int(2**11)
    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudBitMask).eq(0) and (
        qa.bitwiseAnd(cirrusBitMask).eq(0))
    print('maskS2clouds')
    return image.updateMask(mask)


# landsat8
def maskL8clouds(image):
    qa = image.select('BQA')
    # Bits 3 and 5 are cloud shadow and cloud, respectively.
    cloudShadowBitMask = int(2**3)
    cloudsBitMask = int(2**5)
    # Both flags should be set to zero, indicating clear conditions.
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0) and (
        qa.bitwiseAnd(cloudsBitMask).eq(0))
    return image.updateMask(mask)


def get_image(gee_dataset, start_date, end_date, cloud_pct, roi):
    image = (
        ee.ImageCollection(gee_dataset.gee_name).filterDate(
            start_date, end_date).filter(
                ee.Filter.lte(gee_dataset.cloud_cover_prop,
                              cloud_pct)).filterBounds(
                                  roi)  #  .map(maskS2clouds)
        .median())
    image = image.clipToCollection(roi)
    image = image.select(gee_dataset.select_bands, gee_dataset.rename_bands)
    return image

def get_image_index(gee_dataset, start_date, end_date, cloud_pct, roi, expression):
    image = get_image(gee_dataset, start_date, end_date, cloud_pct, roi)
    expression = re.sub(r"b(\d+)", lambda match: f"b({int(match.group(1))-1})", expression)
    image = image.expression(expression).rename('index')
    return image


def page_gee():
    st.write("### GEE影像下载 🛰️")
    left, right = st.columns([7, 3])
    height = 750
    
    gee_init()

    with left:
        map = geemap.Map(location=[30.3, 120.2],
                         zoom_start=12,
                         add_google_map=False)

    with right:
        select_dataset_name = st.selectbox('请选择影像集名称',
                                           [x.name for x in gee_datasets])
        roi_file = st.file_uploader(
            "上传矢量范围，geojson或shapefile(zip)，不要有中文字段名!",
            type=["geojson", "zip"],
        )
        left_date, right_date, right_cloud = st.columns(3)
        today = datetime.today()
        two_month_ago = today - timedelta(days=60)
        with left_date:
            start_date = st.date_input("起始日期", two_month_ago)
        with right_date:
            end_date = st.date_input("结束日期", today)
        with right_cloud:
            cloud_pct = st.number_input('最大云量百分比',
                                        min_value=1,
                                        max_value=100,
                                        value=30,
                                        step=1)

        import pandas as pd
        gdf = pd.DataFrame()
        if roi_file:
            gdf = uploaded_file_to_gdf(roi_file)
            try:
                roi = geemap.gdf_to_ee(gdf, geodesic=False)
                st.session_state["roi"] = roi
                map.add_gdf(gdf, "ROI")
            except Exception as e:
                st.error(e)

        if gdf.empty:
            st.error('请先设置矢量范围！')
        else:
            gee_ds = get_gee_dataset(select_dataset_name)
            image = get_image(gee_ds, str(start_date), str(end_date),
                              cloud_pct, roi)
            map.addLayer(image, gee_ds.vis_params, gee_ds.name)
            selected_bands = st.multiselect("请选择要下载的波段，注意选择顺序",
                                            gee_ds.rename_bands,
                                            default=gee_ds.rename_bands)
            left_push, right_push = st.columns([1, 3])
            with left_push:
                scale = st.number_input('分辨率(米)',
                                        min_value=10,
                                        max_value=100,
                                        value=gee_ds.scale,
                                        step=10)
            with right_push:
                now = datetime.now() + timedelta(hours=8)
                ph_file_name = st.empty()
            
            ph_expression = st.empty()
            btn_download = st.button("下载")
            file_name = ''
            if btn_download:
                expression = st.session_state.expression
                file_name = st.session_state.file_name                
            
            ph_expression.text_input('设置计算公式，波段写成b1、b2，如果为空下载原始影像', key='expression')
            ph_file_name.text_input('设置影像文件名（不要有空格，无需后缀名）', key='file_name')

            if btn_download:
                if file_name == '':
                    st.error('请先设置文件名')
                else:
                    try:
                        gee_ds = get_gee_dataset(select_dataset_name)
                        
                        image = None
                        if st.session_state.expression == '':
                            image = get_image(gee_ds, str(start_date), str(end_date),
                                            cloud_pct, roi)
                            image = image.select(selected_bands)
                            unmask_value = 0
                            if gee_ds.data_type == 'int':
                                image = image.toUint16()
                            if gee_ds.data_type == 'float':
                                image = image.toFloat()
                        else:
                            image = get_image_index(gee_ds, str(start_date), str(end_date),
                                            cloud_pct, roi, expression)
                        
                        file_name = f'{file_name}.tif'
                        #这个更快
                        tif_path = f'images/{file_name}'
                        geemap.download_ee_image(image,
                                                tif_path,
                                                roi.geometry(),
                                                'EPSG:4326',
                                                scale=scale,
                                                unmask_value=0)
                        # geemap.ee_export_image()
                        with open(tif_path, 'rb') as f:
                            buff = BytesIO(f.read())
                            components.html(
                                download_button(buff.getvalue(), f'{file_name}'),
                                height=0,
                            )

                        upload_minio(file_name, tif_path)
                        os.remove(tif_path)
                        st.success('影像已下载并推送至对象存储！')
                    except Exception as e:
                        st.error(e)

    with left:
        map.to_streamlit(height=height)


page_gee()