import glob
import os
import torch
import cv2
from osgeo import gdal
import numpy as np
from tqdm import tqdm
from segment_anything import sam_model_registry, SamPredictor, SamAutomaticMaskGenerator
from . import tif2cv
from . import raster2vector4sam

os.environ["CUDA_VISIBLE_DEVICES"] = "1"


def show_anns(anns):
    if len(anns) == 0:
        return
    sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)

    cv2_tmp = sorted_anns[0]['segmentation']
    cv2_img = np.zeros((cv2_tmp.shape[0], cv2_tmp.shape[1]))
    count = 1
    for ann in sorted_anns:
        m = ann['segmentation']
        # print(np.unique(m))
        cv2_img[m == 1] = count
        count += 1
    # cv2.imwrite("./haha.png", cv2.applyColorMap(np.array(cv2_img*255, dtype=np.uint8), cv2.COLORMAP_JET))
    return cv2_img


def run(sam_checkpoint="/data/ccl/Grounded-Segment-Anything/sam_vit_h_4b8939.pth",
        images_dir='/data/ccl/Grounded-Segment-Anything/data/song_test/*.tif'):
    # try:
    #     os.system("rm " + finish_flag_path)
    # except:
    #     pass
    # sam_checkpoint = "/data/ccl/Grounded-Segment-Anything/sam_vit_h_4b8939.pth"
    device = "cuda"
    model_type = "default"
    sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
    sam.to(device=device)
    mask_generator = SamAutomaticMaskGenerator(sam)

    images = glob.glob(images_dir)
    images.sort()

    for image_path in tqdm(images, desc="Processing images"):
        image_tif = gdal.Open(image_path, gdal.GA_ReadOnly)
        image_trans = image_tif.GetGeoTransform()
        image = image_tif.ReadAsArray()

        image = tif2cv.cumulative_count_cut(image)
        image = np.transpose(image, (1, 2, 0))

        # image = image[:, :, 0:3]

        assert image.shape == (1024, 1024, 3)

        masks = mask_generator.generate(image)
        mask_in_one = show_anns(masks)

        save_path = image_path.replace('.tif', '.shp')
        raster2vector4sam.raster2vector4sam(mask_in_one, image_tif, save_path)

    # os.system('touch ' + finish_flag_path)


if __name__ == '__main__':
    run()
