import collections
from dataclasses import dataclass
import json
import re
from typing import Dict, List
import streamlit as st

@dataclass
class GEEDataset:
    name: str = ''
    gee_name: str = ''
    cloud_cover_prop: str = ''    
    select_bands: List = ''
    rename_bands: List = ''
    vis_params: Dict = ''
    scale: int = ''
    data_type:str = ''
    

gee_datasets: List[GEEDataset] = []

@st.cache_resource
def add_gee_datasets():
    # read json
    with open(r'data/gee_datasets.json', 'r') as f:
        data = json.load(f)
        for item in data:
            gee_datasets.append(
                GEEDataset(item['name'], item['gee_name'], item['cloud_cover_prop'], 
                           item['select_bands'], item['rename_bands'], item['vis_params'], item['scale'], item['data_type']))

def get_gee_dataset(dataset_name: str) -> GEEDataset:
    lst = [x for x in gee_datasets if x.name == dataset_name]
    if len(lst) > 0:
        return lst[0]
    return None

add_gee_datasets()