import os
from itertools import product
import rasterio as rio
from rasterio import windows
import uuid
import numpy as np
from rasterio.mask import mask
import shapely
from shapely.ops import transform as ops_trans
import pyproj
import pandas as pd
import geopandas as gpd
import glob
import os
import networkx as nx

def get_windows(image_array, image_transform, size=1024):
    '''
    
    '''
    nols, nrows = image_array.shape[2], image_array.shape[1]
    offsets = product(range(0, nols, size), range(0, nrows, size))
    big_window = windows.Window(col_off=0, row_off=0, width=nols, height=nrows)
    overlap = 10
    for col_off, row_off in  offsets:
        x = int(col_off/size)
        y = int(row_off/size)
        col_off -= x * overlap
        row_off -= y * overlap
        window = windows.Window(col_off=col_off, row_off=row_off, width=size, height=size).intersection(big_window)
        transform = windows.transform(window, image_transform)
        
        yield window, transform, x, y, window.height, window.width


def split_tif(tif_path, dest_dir, polygon):
    '''
    影像切片
    '''
    output_filename = 'tile_{}_{}.tif'
    
    id = str(uuid.uuid4())
    with rio.open(tif_path) as inds:
        size = 1024

        meta = inds.meta.copy()
        output_dir = os.path.join(dest_dir, id)
        os.mkdir(output_dir)
                
        polygon_3857 = geometry_transform(polygon)
        
        crop_image, crop_transform = mask(inds, [polygon_3857], crop=True)
        
        for window, transform, x, y, height, width in get_windows(crop_image, crop_transform, size):
            # print(window)
            meta['count'] = 3
            meta['transform'] = transform
            meta['width'], meta['height'] = size, size
            outpath = os.path.join(output_dir, output_filename.format(x, y))
            with rio.open(outpath, 'w', **meta) as outds:
                data = crop_image[:, window.row_off:window.row_off+window.height, window.col_off:window.col_off+window.width]
                shape = data.shape
                data = data[:3,:,:]
                if width < size or height < size:
                    new_data = np.zeros(shape=(3, size, size), dtype=data.dtype)
                    new_data[:,:shape[1],:shape[2]] = data
                    data = new_data
                outds.write(data)
                
    return id

def merge_shps(dir, dest_shp, polygon):
    '''
    合并文件夹内所有shapefile
    '''
    
    shp_files = glob.glob(dir + '/*.shp')

    # 以第一个为模板
    shp_a = gpd.read_file(os.path.join(dir, shp_files[0]))
    # 生成的shp有这个字段，这里用来填写递增序号
    shp_a['DN'] = range(1, len(shp_a) + 1)

    # 循环添加其他数据
    for n in range(1, len(shp_files)):
        shp_b = gpd.read_file(os.path.join(dir, shp_files[n]))
        shp_b['DN'] = range(1, len(shp_b) + 1)
            
        intersect_polygons = gpd.sjoin(shp_a, shp_b, how='inner', predicate='intersects', lsuffix='1', rsuffix='2')
        
        # 获取所有连通图
        G = nx.Graph()
        for index, row in intersect_polygons.iterrows():
            id_a = 'a:' + str(row['DN_1'])
            id_b = 'b:' + str(row['DN_2'])
            G.add_nodes_from([id_a, id_b])
            G.add_edge(id_a, id_b)
            
        unions = []
        components = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        for c in components:
            # 合并每个子网的多边形
            polygons = []
            for n in c.nodes():
                splits = n.split(':')
                shp = shp_a
                if splits[0] == 'b':
                    shp = shp_b                
                id = int(splits[1])
                row = shp.loc[shp['DN'] == id]
                geometry = row['geometry'].iloc[0]
                # 让其拓扑正确
                polygons.append(geometry.buffer(0))
            union = gpd.GeoSeries(polygons).unary_union
            unions.append(union)
        
        # 生成合并后的数据
        union_polygons = gpd.GeoDataFrame(geometry=unions, crs = shp_a.crs)
            
        non_overlapping_a = shp_a[~shp_a.DN.isin(intersect_polygons.DN_1)]
        non_overlapping_b = shp_b[~shp_b.DN.isin(intersect_polygons.DN_2)]

        shp_a = gpd.GeoDataFrame(pd.concat([non_overlapping_a, non_overlapping_b, union_polygons]))
        
        # 添加序号
        shp_a['DN'] = range(1, len(shp_a) + 1)

    valid = shp_a.geometry.is_valid
    if not valid.all():
        shp_a.geometry = shp_a.buffer(0)
        
    polygon_3857 = geometry_transform(polygon)
    
    shp_a = shp_a.clip(polygon_3857)
    shp_a.to_crs('EPSG:4326').to_file(dest_shp)
    
def geometry_transform(geometry):
    '''
    几何wgs84转3857
    '''
    wgs84 = pyproj.CRS('EPSG:4326')
    wm = pyproj.CRS('EPSG:3857')
    project = pyproj.Transformer.from_crs(wgs84, wm, always_xy=True).transform
    geom_3857 = ops_trans(project, geometry)
    
    return geom_3857
    