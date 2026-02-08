import collections
from dataclasses import dataclass
import json
import re
from typing import Dict, List
import streamlit as st

@dataclass
class AIEDataset:
    name: str = ''
    gee_name: str = ''
    cloud_cover_prop: str = ''    
    select_bands: List = ''
    rename_bands: List = ''
    vis_params: Dict = ''
    scale: int = ''
    data_type:str = ''
    

aie_datasets: List[AIEDataset] = []

@st.cache_resource
def add_aie_datasets():
    # read json
    with open(r'data/aie_datasets.json', 'r') as f:
        data = json.load(f)
        for item in data:
            aie_datasets.append(
                AIEDataset(item['name'], item['gee_name'], item['cloud_cover_prop'], 
                           item['select_bands'], item['rename_bands'], item['vis_params'], item['scale'], item['data_type']))

def get_aie_dataset(dataset_name: str) -> AIEDataset:
    lst = [x for x in aie_datasets if x.name == dataset_name]
    if len(lst) > 0:
        return lst[0]
    return None

add_aie_datasets()