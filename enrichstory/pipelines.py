# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
from typing import Dict, Any, List


class EnrichStoryPipeline:
    def __init__(self):
        self.companies: List[Dict[str, Any]] = []
        self.employees: List[Dict[str, Any]] = []
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Limpeza básica dos dados
        for field in adapter.field_names():
            value = adapter.get(field)
            if isinstance(value, str):
                adapter[field] = value.strip()
        
        # Armazenar em memória
        item_dict = dict(adapter)
        if 'linkedin_url' in adapter.field_names():
            self.companies.append(item_dict)
        else:
            self.employees.append(item_dict)
        
        return item
    
    def close_spider(self, spider):
        # Retornar os dados coletados
        if self.companies:
            return self.companies[0]  # Retorna a primeira empresa encontrada
        return {}
