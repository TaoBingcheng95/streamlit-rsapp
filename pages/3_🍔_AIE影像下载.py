from io import BytesIO
import json
from math import nan
import os
from datetime import datetime, timedelta
import uuid
import requests
import re

import aie
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components

from Tea.exceptions import TeaException
from alibabacloud_tea_openapi import models
from alibabacloud_aiearth_engine20220609.models import *
from alibabacloud_aiearth_engine20220609.client import Client
            
from utils.aie_dataset import aie_datasets, get_aie_dataset
from utils.minio_util import list_tif, upload_minio


def aie_init(placeholder):
    placeholder.write('正在初始化AI Earth资源，请稍等。。。')
    token = 'ce58d796366f1bbe246142173d0d2d1d'
    aie.Authenticate(token=token)
    aie.Initialize()
    placeholder.empty()


@st.cache_data
def show_file_in_aie(data):
    gdf = gpd.read_file(data)
    geojson = gdf.to_json()
    geojson = json.loads(geojson)
    geom = geojson_to_geom(geojson)
    return geom


def addLayer_geom(map, name, geom, color='#808080'):
    """将geom加到地图里
    """
    vis_params = {"color": color}

    map.addLayer(geom, vis_params, name, bounds=geom.getBounds())


def geojson_to_geom(geo_json, geodesic=False, encoding="utf-8"):
    """geojson转到geom，只提取第一个
    按照geemap里geojson_to_ee修改，适合aie    
    """
    try:
        if geo_json["type"] == "FeatureCollection":
            for feature in geo_json["features"]:
                geom_str = feature["geometry"]
                geom = aie.Geometry(geom_str)
            return geom
        else:
            raise Exception("Could not convert the geojson to ee.Geometry()")

    except Exception as e:
        print("Could not convert the geojson to ee.Geometry()")
        raise Exception(e)


def get_image(aie_dataset, start_date, end_date, cloud_pct, roi):
    image = aie.ImageCollection(aie_dataset.gee_name) \
               .filterDate(start_date, end_date) \
               .filterBounds(roi) \
               .filter(aie.Filter.lte(aie_dataset.cloud_cover_prop, cloud_pct)) \
               .median()

    image = image.clip(roi)
    image = image.select(aie_dataset.select_bands)
    image = image.rename(aie_dataset.rename_bands)
    return image

def get_image_index(gee_dataset, start_date, end_date, cloud_pct, roi, expression):
    image = get_image(gee_dataset, start_date, end_date, cloud_pct, roi)
    expression = re.sub(r"b(\d+)", lambda match: f"b({int(match.group(1))-1})", expression)
    image = image.expression(expression).rename(['index'])
    return image

def get_export_images():
    names = []
    
    config = models.Config(
        # 您的AccessKey ID,
        access_key_id='LTAI5tJHV26za8AfH8HVznjk',
        # 您的AccessKey Secret,
        access_key_secret='LNstiAoeZQVwSXwho3xMKaeLBE7mxe',
        # 地域ID
        region_id='cn-hangzhou',
        # 访问的域名
        endpoint='aiearth-engine.cn-hangzhou.aliyuncs.com'
    )

    client = Client(config)
    
    try:
        list_user_raster_datas_request = ListUserRasterDatasRequest()
        list_user_raster_datas_request.page_size = 10
        list_user_raster_datas_request.page_number = 1
        list_user_raster_datas_request.from_type = 'developer_export'

        user_raster_list: ListUserRasterDatasResponse = client.list_user_raster_datas(list_user_raster_datas_request)
        for raster in user_raster_list.body.list:
            name = raster.raster.name
            names.append(name)
            
        return names
        
    except TeaException as e:
        # 打印整体的错误输出
        print(e)
        # 打印错误码
        print(e.code)
        # 打印错误信息，错误信息中包含
        print(e.message)
        # 打印服务端返回的具体错误内容
        print(e.data)

def download_export_images(name):
    
    config = models.Config(
        # 您的AccessKey ID,
        access_key_id='LTAI5tJHV26za8AfH8HVznjk',
        # 您的AccessKey Secret,
        access_key_secret='LNstiAoeZQVwSXwho3xMKaeLBE7mxe',
        # 地域ID
        region_id='cn-hangzhou',
        # 访问的域名
        endpoint='aiearth-engine.cn-hangzhou.aliyuncs.com'
    )

    client = Client(config)
    
    try:
        list_user_raster_datas_request = ListUserRasterDatasRequest()
        list_user_raster_datas_request.name = name
        list_user_raster_datas_request.page_size = 10
        list_user_raster_datas_request.page_number = 1
        list_user_raster_datas_request.from_type = 'developer_export'

        user_raster_list: ListUserRasterDatasResponse = client.list_user_raster_datas(list_user_raster_datas_request)
        print(user_raster_list.body)
        for raster in user_raster_list.body.list:
             data_id = raster.data_id
             name = raster.raster.name
             downloadRequerst = DownloadDataRequest()
             downloadRequerst.data_id = data_id
             downloadResp = client.download_data(downloadRequerst)
             url = downloadResp.body.download_url
             name += '.tif'
             tif_path = f'images/{name}'
             if os.path.exists(tif_path):
                 os.remove(tif_path) 
             import wget
             wget.download(url, tif_path)
             from utils.common import download_button
             with open(tif_path, 'rb') as f:
                buff = BytesIO(f.read())
                components.html(
                    download_button(buff.getvalue(), name),
                    height=0,
                )
             os.remove(tif_path)
             break
            
        
    except TeaException as e:
        # 打印整体的错误输出
        print(e)
        # 打印错误码
        print(e.code)
        # 打印错误信息，错误信息中包含
        print(e.message)
        # 打印服务端返回的具体错误内容
        print(e.data)
        
def get_download_url(name):
    
    config = models.Config(
        # 您的AccessKey ID,
        access_key_id='LTAI5tJHV26za8AfH8HVznjk',
        # 您的AccessKey Secret,
        access_key_secret='LNstiAoeZQVwSXwho3xMKaeLBE7mxe',
        # 地域ID
        region_id='cn-hangzhou',
        # 访问的域名
        endpoint='aiearth-engine.cn-hangzhou.aliyuncs.com'
    )

    client = Client(config)
    
    try:
        list_user_raster_datas_request = ListUserRasterDatasRequest()
        list_user_raster_datas_request.name = name
        list_user_raster_datas_request.page_size = 10
        list_user_raster_datas_request.page_number = 1
        list_user_raster_datas_request.from_type = 'developer_export'

        user_raster_list: ListUserRasterDatasResponse = client.list_user_raster_datas(list_user_raster_datas_request)
        print(user_raster_list.body)
        for raster in user_raster_list.body.list:
             data_id = raster.data_id
             downloadRequerst = DownloadDataRequest()
             downloadRequerst.data_id = data_id
             downloadResp = client.download_data(downloadRequerst)
             url = downloadResp.body.download_url
             return url            
        
    except TeaException as e:
        # 打印整体的错误输出
        print(e)
        # 打印错误码
        print(e.code)
        # 打印错误信息，错误信息中包含
        print(e.message)
        # 打印服务端返回的具体错误内容
        print(e.data)
        
def page_aie():
    st.write("### AI Earth影像下载 🍔")
    ph_init = st.empty()
    left, right = st.columns([7, 3])
    height = 750

    aie_init(ph_init)
    
    with left:
        map = aie.Map(center=[120.2, 30.3], zoom=12)

    with right:
        
        tabExport, tabDownload = st.tabs(
            ["创建下载任务", "下载数据"])
        
        with tabExport:
            select_dataset_name = st.selectbox('请选择影像集名称',
                                            [x.name for x in aie_datasets])
            roi_file = st.file_uploader(
                "上传矢量范围，geojson或shapefile(zip)",
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

            roi = None
            if roi_file:
                roi = show_file_in_aie(roi_file)
                addLayer_geom(map, 'roi', roi)
                b = roi.getBounds()
                bb = [[b[1],b[0]],[b[3],b[2]]]
                center = [(b[1] + b[3])/2, (b[0] + b[2])/2]
                map.center = center

            if roi == None:
                st.error('请先设置矢量范围！')
            else:
                aie_ds = get_aie_dataset(select_dataset_name)
                image = get_image(aie_ds, str(start_date), str(end_date),
                                cloud_pct, roi)
                map.addLayer(image,
                            aie_ds.vis_params,
                            aie_ds.name,
                            bounds=image.getBounds())
                
                selected_bands = st.multiselect("请选择要下载的波段，注意选择顺序",
                                                aie_ds.rename_bands,
                                                default=aie_ds.rename_bands)
                left_push, right_push = st.columns([1, 2])
                with left_push:
                    scale = st.number_input('分辨率(米)',
                                            min_value=10,
                                            max_value=100,
                                            value=aie_ds.scale,
                                            step=10)
                with right_push:
                    ph_file_name = st.empty()
                
                ph_expression = st.empty() 
                btn_download = st.button("影像生成")
                file_name = ''
                if btn_download:
                    expression = st.session_state.expression
                    file_name = st.session_state.file_name 
                
                ph_expression.text_input('设置计算公式，波段写成b1，为空下载原始影像', key='expression')
                ph_file_name.text_input('设置影像文件名（无需后缀名）', key='file_name')

                if btn_download:
                    if file_name == '':
                        st.error('请先设置文件名')
                    else:
                        try:
                            gee_ds = get_aie_dataset(select_dataset_name)
                            
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
                                                        
                            task = aie.Export.image.toAsset(image, file_name, scale)
                            task.start()
                            
                            st.success('影像生成中，请等待十分钟后去下载列表查看！')
                        except Exception as e:
                            st.error(e)
        
        with tabDownload:
            names = get_export_images()
            
            ph_select = st.empty()
            left_dl, right_dl, _ = st.columns([1,1,1])
            with left_dl:
                btn_refresh = st.button("刷新列表")
            with right_dl:
                btn_download = st.button("获取下载地址", type='primary')                            
            select_name = ph_select.selectbox('选择下载数据（从生成到可以下载至少十分钟）', options=names, key='raster_name')
            
            if btn_refresh:
                st.experimental_rerun()
            if btn_download:
                if select_name:
                    # download_export_images(select_name)
                    st.success(get_download_url(select_name))
                    


    with left:        
        map_html_source = map.to_html()
        components.html(map_html_source, height=height, scrolling=False)


page_aie()