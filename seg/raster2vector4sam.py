import os
from pathlib import Path
import numpy as np
from osgeo import gdal, ogr, osr, gdal_array, gdalconst


def raster2vector4sam(mask_arr, psz_raster, dst_vec, dst_layer_name="mask", driver_name='ESRI Shapefile'):
    """
    Description
    -------
    将掩膜数组转换为矢量文件
    reference : gdal_polygonize.py

    Parameters
    -------
    psz_raster : gdal.dataset
        原始的栅格文件
    mask_raster : string or pathlib.Path
        掩膜PNG文件
    dst_vec : string or pathlib.Path
        输出shapefile文件的路径.
    nodata : int
        影像路径.默认为0.
    dst_layer_name : string
        图层名称.默认为"mask".
    driver_name : string
        输出文件格式
    seg_id : int
        需要提取的分块索引

    Returns
    -------
    None.
    """

    try:
        src_ds = psz_raster
        # projection = src_ds.GetProjection()
        # im_GeoTransform = src_ds.GetGeoTransform()
        im_proj = src_ds.GetProjection()
        # im_width = src_ds.RasterXSize
        # im_height = src_ds.RasterYSize
        # src_band = src_ds.GetRasterBand(1)
        # src_band.SetNoDataValue(nodata)
        # mask_band = src_band.GetMaskBand()
    except RuntimeError as e:
        print(e)
        return False
    
    # create shapefile
    driver = ogr.GetDriverByName(driver_name)
    if Path(dst_vec).exists():
        print(f"{dst_vec} is exist and delete the old file!")
        driver.DeleteDataSource(str(dst_vec))
    else:
        if not Path(dst_vec).parent.exists():
            Path.mkdir(dst_vec.parent, exist_ok=True, parents=True)

    try:
        vec_ds = driver.CreateDataSource(str(dst_vec))
    except RuntimeError as e:
        print(e)
        return False  # sys.exit(0)
    
    srs = osr.SpatialReference()
    srs.ImportFromWkt(im_proj)
    dst_layer = vec_ds.CreateLayer(dst_layer_name, srs=srs)
    # dst_field: int = -1
    
    dst_fieldname = 'DN'
    fd = ogr.FieldDefn(dst_fieldname, ogr.OFTInteger)
    dst_layer.CreateField(fd)
    dst_field = 0
    
    pixel_dn = np.unique(mask_arr)
    
    for idx, item in enumerate(pixel_dn):
        if item == 0:
            continue
        mask_seg = np.zeros_like(mask_arr)
        mask_seg[mask_arr == item] = idx

        dst_ds = gdal_array.OpenArray(mask_seg)
        gdal_array.CopyDatasetInfo(src_ds, dst_ds, xoff=0, yoff=0)

        src_band = dst_ds.GetRasterBand(1)
        src_band.SetNoDataValue(0)
        mask_band = src_band.GetMaskBand()
    
        try:
            options = ['8CONNECTED=8']
            gdal.Polygonize(src_band, mask_band, dst_layer, dst_field, options, callback=None)  # 0gdal.TermProgress_nocb
            dst_layer.SyncToDisk()
        except RuntimeError as e:
            print(e)
            continue
            # return False  # sys.exit(0)

    vec_ds.Release()
    # del vec_ds

    return True



if __name__ == "__main__":

    raster_file = "tempresult\\vector2mask_bool_tmp.tif"
    vector_file = "test.shp"

    arr = gdal_array.LoadFile(raster_file)

    raster2vector4sam(arr, raster_file, vector_file)
