import minio
import json

minio_client: minio.Minio = None
bucket_name = 'vi-test'

def init_minio():
    with open("minio.conf", "r") as f:
        dic = json.load(f)
        return minio.Minio(**dic)

def upload_minio(file_name:str, file_path:str):
    minio_client.fput_object(bucket_name, file_name, file_path)
    
def list_tif():
    result = []
    objects = minio_client.list_objects(bucket_name)
    for obj in objects:
        result.append(obj.object_name)
    return result
    
minio_client = init_minio()