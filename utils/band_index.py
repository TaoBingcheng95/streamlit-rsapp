import collections
from dataclasses import dataclass
import json
import re
from typing import Dict, List
import streamlit as st


@dataclass
class BandIndex:
    name: str = ''
    text: str = ''
    formula: str = ''
    factors: Dict = None

    def get_bands(self) -> List[str]:
        pattern = re.compile(r"\{(\w+)\}")
        lst = pattern.findall(self.formula)
        # 去除重复元素
        result = list(set(lst))
        result.sort()
        return result


band_indices: List[BandIndex] = []

@st.cache_resource
def add_band_indices():
    # read json
    with open(r'data/band_indices.json', 'r') as f:
        data = json.load(f)
        for item in data:
            band_indices.append(
                BandIndex(
                    item['name'], item['text'], item['formula'],
                    collections.OrderedDict(item['factors']) if 'factors' in item else None))


def get_band_index(index_name: str) -> BandIndex:
    lst = [x for x in band_indices if x.name == index_name]
    if len(lst) > 0:
        return lst[0]
    return None


add_band_indices()