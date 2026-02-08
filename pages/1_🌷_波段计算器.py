import json
import re
import urllib.parse

import cmasher as cmr
import leafmap.foliumap as leafmap
import matplotlib.pyplot as plt
import numpy as np
import requests
import streamlit as st

from utils.band_index import band_indices, get_band_index
from utils.common import get_colormap_names
from utils.minio_util import list_tif


def reset_rescale():
    st.session_state.rescale_min = 0
    st.session_state.rescale_max = 0


def page_raster_calculator():

    titiler_endpoint = 'http://192.168.148.214:8000'
    titiler_url = titiler_endpoint + '/cog/tiles/{z}/{x}/{y}.png'
    titiler_stats_url = titiler_endpoint + '/cog/statistics'

    st.write("### 遥感影像波段计算器 🌷")

    left, right = st.columns([7, 3])
    height = 750

    with left:
        map = leafmap.Map(location=[30.3, 120.2], zoom_start=12, tiles=None)
        map.add_tile_layer(url='https://t2.tianditu.gov.cn/vec_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=vec&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TileCol={x}&TileRow={y}&TileMatrix={z}&tk=d0a63baa051a4f9f4301f3e2373ecd29',
                           name='天地图矢量',
                           attribution='天地图矢量')
        map.add_tile_layer(url='https://t2.tianditu.gov.cn/cva_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cva&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TileCol={x}&TileRow={y}&TileMatrix={z}&tk=d0a63baa051a4f9f4301f3e2373ecd29',
                           name='天地图注记',
                           attribution='天地图注记')
    with right:
        tifs = list_tif()
        select_tif = st.selectbox('选择浏览影像', options=tifs)
        tif_url = f'http://minio:9000/vi-test/{select_tif}'
        try:
            bands = leafmap.cog_bands(tif_url, titiler_endpoint)
        except Exception as e:
            st.error(e)

        tabRGB, tabIndex, tabCustom = st.tabs(
            [":100:红绿蓝合成", ":coffee:常用指数计算", ":sparkles:自定义公式"])

        with tabRGB:
            selected_bands = st.multiselect("请选择3个波段组成RGB通道",
                                            bands,
                                            default=None)
            left_rescale, right_rescale = st.columns(2)
            with left_rescale:
                rescale_min_rgb = st.number_input('显示最小值',
                                                value=0.0,
                                                step=0.01,
                                                format='%.2f',
                                                key='rescale_min_rgb')
                
            with right_rescale:
                rescale_max_rgb = st.number_input('显示最大值',
                                                value=2500.0,
                                                step=0.01,
                                                format='%.2f',
                                                key='rescale_max_rgb')
            
            st.caption('Sentinel:0-2500, Landsat:8000-15000')

            btn_bands = st.button("确定", key='rgb')

            if btn_bands:
                if len(selected_bands) != 3:
                    st.error("请选择3个波段！")
                else:
                    lst = [int(x[1:]) for x in selected_bands]
                    titiler_url = titiler_endpoint + '/cog/tiles/{z}/{x}/{y}.png'
                    params = {
                        'url': tif_url,
                        'bidx1': lst[0],
                        'bidx2': lst[1],
                        'bidx3': lst[2],
                        'rescale': f'{rescale_min_rgb},{rescale_max_rgb}'
                    }
                    params = urllib.parse.urlencode(params)
                    pattern = r"bidx\d="
                    params = re.sub(pattern, "bidx=", params)

                    layer_url = f'{titiler_url}?{params}'

                    map.add_tile_layer(url=layer_url,
                                       name='RGB',
                                       attribution='RGB',
                                       min_zoom=10,
                                       max_zoom=15)

        with tabIndex:
            select_index_name = st.selectbox(
                '请选择指数名称：', [x.name for x in band_indices],
                format_func=lambda x: f'{x: <6} {get_band_index(x).text}',
                on_change=reset_rescale)

            if select_index_name:
                rs_index = get_band_index(select_index_name)
                st.caption(rs_index.formula)

                index_bands = rs_index.get_bands()

                # 展示公式里各个波段，选择
                sublists = [
                    index_bands[i:i + 3]
                    for i in range(0, len(index_bands), 3)
                ]

                for sub in sublists:
                    band1, band2, band3 = st.columns(3)
                    with band1:
                        band_name = sub[0]
                        st.selectbox(f'波段{band_name}',
                                     bands,
                                     key=f'band_{band_name}')
                    with band2:
                        if len(sub) > 1:
                            band_name = sub[1]
                            st.selectbox(f'波段{band_name}',
                                         bands,
                                         key=f'band_{band_name}')
                    with band3:
                        if len(sub) > 2:
                            band_name = sub[2]
                            st.selectbox(f'波段{band_name}',
                                         bands,
                                         key=f'band_{band_name}')

                factors = rs_index.factors
                # 展示公式里各个系数，填写
                if factors:
                    factor_keys = list(factors.keys())
                    sublists = [
                        factor_keys[i:i + 3]
                        for i in range(0, len(factor_keys), 3)
                    ]

                    for sub in sublists:
                        factor1, factor2, factor3 = st.columns(3)
                        with factor1:
                            factor_name = sub[0]
                            st.number_input(f'系数{factor_name}',
                                            value=factors[factor_name],
                                            min_value=0.0,
                                            max_value=10.0,
                                            format='%.2f',
                                            key=f'number_{factor_name}')

                        with factor2:
                            if len(sub) > 1:
                                factor_name = sub[1]
                                st.number_input(f'系数{factor_name}',
                                                value=factors[factor_name],
                                                min_value=0.0,
                                                max_value=10.0,
                                                format='%.2f',
                                                key=f'number_{factor_name}')

                        with factor3:
                            if len(sub) > 2:
                                factor_name = sub[2]
                                st.number_input(
                                    f'系数{factor_name}',
                                    value=factors[factor_name],
                                    min_value=0.0,
                                    max_value=10.0,
                                    format='%.2f',
                                    key=f'number_{factor_name}',
                                )

            if "rescale_min" not in st.session_state:
                st.session_state.rescale_min = 0
            if "rescale_max" not in st.session_state:
                st.session_state.rescale_max = 0
            left_rescale, right_rescale = st.columns(2)
            with left_rescale:
                ph_rescale_min = st.empty()
            with right_rescale:
                ph_rescale_max = st.empty()

            # 选择色带
            colormaps = get_colormap_names()
            colormaps.sort()
            select_cmp = st.selectbox(f'选择色带', colormaps, key='select_cmp')

            if select_cmp:
                cmap_range = cmr.get_sub_cmap(select_cmp, 0, 1)
                fig, ax = plt.subplots(figsize=(15, 1))
                # Getting only 50 values here so that colormaps are loading faster
                x = np.linspace(0, 1, 30)[None, :]
                ax.imshow(x, aspect='auto', cmap=cmap_range)

                ax.set_axis_off()
                ax.xaxis.set_visible(False)
                ax.yaxis.set_visible(False)
                st.pyplot(fig)

            btn_index = st.button("确定", key='index')
            if btn_index:
                # 得到可用的计算公式
                fomular = rs_index.formula
                for i in range(len(index_bands)):
                    fomular = fomular.replace(
                        '{' + index_bands[i] + '}',
                        st.session_state[f'band_{index_bands[i]}'])
                factors = rs_index.factors
                if factors:
                    for k in factors:
                        fomular = fomular.replace(k, str(factors[k]))
                if st.session_state.rescale_min == 0 and st.session_state.rescale_max == 0:
                    # 先求最大最小值，2%-98%
                    params = {'url': tif_url, 'expression': fomular}
                    params = urllib.parse.urlencode(params)
                    stats_url = f'{titiler_stats_url}?{params}'
                    response = requests.get(stats_url)
                    stats_result = json.loads(response.content)
                    for k in stats_result:
                        percentile_2 = stats_result[k]['percentile_2']
                        percentile_98 = stats_result[k]['percentile_98']
                        break
                    percentile_2 = round(percentile_2, 2)
                    percentile_98 = round(percentile_98, 2)
                    st.session_state.rescale_min = percentile_2
                    st.session_state.rescale_max = percentile_98

            rescale_min = ph_rescale_min.number_input('显示最小值',
                                                      step=0.01,
                                                      format='%.2f',
                                                      key='rescale_min')
            rescale_max = ph_rescale_max.number_input('显示最大值',
                                                      step=0.01,
                                                      format='%.2f',
                                                      key='rescale_max')

            if btn_index:
                # 展示
                params = {
                    'url': tif_url,
                    'expression': fomular,
                    'rescale': f'{rescale_min},{rescale_max}',
                    'colormap_name': select_cmp.lower()
                }
                params = urllib.parse.urlencode(params)
                layer_url = f'{titiler_url}?{params}'
                map.add_tile_layer(url=layer_url,
                                   name='VI',
                                   attribution='VI',
                                   min_zoom=10,
                                   max_zoom=14)

        with tabCustom:
            expr = st.text_input(label='请输入自定义公式: ',
                                        value='(b8-b4)/(b8+b4)')

            st.caption('波段写成b1、b2等，如NDVI公式这样写: (b8-b4)/(b8+b4)')
            st.caption("开方：sqrt(b4-b3)，乘方: (b1-b2)**2，三角函数: sin(b2)")

            if "rescale_min_custom" not in st.session_state:
                st.session_state.rescale_min_custom = 0
            if "rescale_max_custom" not in st.session_state:
                st.session_state.rescale_max_custom = 0
            left_rescale, right_rescale = st.columns(2)
            with left_rescale:
                ph_rescale_min = st.empty()
            with right_rescale:
                ph_rescale_max = st.empty()

            # 选择色带
            colormaps = get_colormap_names()
            colormaps.sort()
            select_cmp_custom = st.selectbox(f'选择色带', colormaps, key='select_cmp_custom')

            if select_cmp_custom:
                cmap_range = cmr.get_sub_cmap(select_cmp_custom, 0, 1)
                fig, ax = plt.subplots(figsize=(15, 1))
                # Getting only 50 values here so that colormaps are loading faster
                x = np.linspace(0, 1, 30)[None, :]
                ax.imshow(x, aspect='auto', cmap=cmap_range)

                ax.set_axis_off()
                ax.xaxis.set_visible(False)
                ax.yaxis.set_visible(False)
                st.pyplot(fig)

            btn_expr = st.button("确定", key='custom')
            
            if btn_expr:
                if st.session_state.rescale_min_custom == 0 and st.session_state.rescale_max_custom == 0:
                    # 先求最大最小值，2%-98%
                    params = {'url': tif_url, 'expression': expr}
                    params = urllib.parse.urlencode(params)
                    stats_url = f'{titiler_stats_url}?{params}'
                    response = requests.get(stats_url)
                    stats_result = json.loads(response.content)
                    for k in stats_result:
                        percentile_2 = stats_result[k]['percentile_2']
                        percentile_98 = stats_result[k]['percentile_98']
                        break
                    percentile_2 = round(percentile_2, 2)
                    percentile_98 = round(percentile_98, 2)
                    st.session_state.rescale_min_custom = percentile_2
                    st.session_state.rescale_max_custom = percentile_98

            rescale_min_custom = ph_rescale_min.number_input('缩放最小值',
                                                      step=0.01,
                                                      format='%.2f',
                                                      key='rescale_min_custom')
            rescale_max_custom = ph_rescale_max.number_input('缩放最大值',
                                                      step=0.01,
                                                      format='%.2f',
                                                      key='rescale_max_custom')

            if btn_expr:
                params = {
                    'url': tif_url,
                    'expression': expr,
                    'rescale': f'{rescale_min_custom},{rescale_max_custom}',
                    'colormap_name': select_cmp_custom.lower()
                }
                params = urllib.parse.urlencode(params)
                layer_url = f'{titiler_url}?{params}'
                map.add_tile_layer(url=layer_url,
                                   name='VI',
                                   attribution='VI',
                                   min_zoom=10,
                                   max_zoom=14)

    with left:
        # 靠这个刷新地图
        map.to_streamlit(height=height)


page_raster_calculator()