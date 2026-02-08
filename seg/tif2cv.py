from osgeo import gdal
import glob
import json
import cv2
import os
import numpy as np


def cumulative_count_cut(img, min_p=2, max_p=98):
    min_v = np.nanpercentile(img, min_p)
    max_v = np.nanpercentile(img, max_p)
    img[img < min_v] = min_v
    img[img > max_v] = max_v
    img = ((img - np.min(img)) / (np.max(img) - np.min(img)) * 255).astype("uint8")
    return img


if __name__ == '__main__':

    images = glob.glob(r"./data/*/*.tif")
    labels = glob.glob(r"./data/*/*.json")

    images.sort()
    labels.sort()

    labels_sort = [x.split('.json')[0] for x in labels]

    print(len(images))
    print(len(labels))

    for i, (image_path) in enumerate(images):

        image_filename = os.path.basename(image_path).split('.tif')[0]

        image = gdal.Open(image_path, gdal.GA_ReadOnly)
        image_trans = image.GetGeoTransform()
        image = image.ReadAsArray()
        '''
        image[0, :, :] = cumulative_count_cut(image[0, :, :])
        image[1, :, :] = cumulative_count_cut(image[1, :, :])
        image[2, :, :] = cumulative_count_cut(image[2, :, :])
        '''
        image = cumulative_count_cut(image, 0, 100)

        print(image.shape)
        # image = np.transpose(image, (1, 2, 0))
        # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        cv2.imwrite(image_path.split(".tif")[0] + ".tif", image)
