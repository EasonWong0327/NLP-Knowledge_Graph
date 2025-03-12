from typing import List, Tuple, Dict, Set
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .base_processor import BaseProcessor

class EntityLinker(BaseProcessor):
    def __init__(self):
        """初始化实体链接器"""
        super().__init__()
        self.entity_aliases = defaultdict(set)
        self.entity_descriptions = {}
        self.entity_embeddings = {}
        
        # 加载实体别名词典(换成自己的，最好存成数据库的同义词table)
        self._load_entity_aliases()

    def _load_entity_aliases(self):
        """加载实体别名词典"""
        self.entity_aliases = {
            "阿里巴巴": {"阿里", "淘宝", "BABA"},
            "腾讯": {"腾讯控股", "WeChat", "00700.HK"},
            "百度": {"百度在线", "BIDU"},
            "京东": {"京东商城", "JD"},
            "美团": {"美团点评", "03690.HK"},
            # 更多实体别名...
        }
        
        # 实体嵌入
        for canonical, aliases in self.entity_aliases.items():
            self.entity_embeddings[canonical] = self.get_text_embedding(canonical)
            for alias in aliases:
                self.entity_embeddings[alias] = self.get_text_embedding(alias)

    def link_entities(self, entities: List[Tuple[str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """实体链接"""
        linked_relations = []
        
        # 实体链接
        linked_entities = {}
        for entity, type_, props in entities:
            canonical_entity = self._link_entity(entity)
            if canonical_entity and canonical_entity != entity:
                linked_entities[entity] = canonical_entity
                
                # 添加别名关系
                properties = {
                    'confidence': 0.9,
                    'source': 'entity_linking',
                    'alias_type': 'standard_name'
                }
                linked_relations.append((
                    entity,
                    "别名关系",
                    canonical_entity,
                    properties
                ))
        
        return linked_relations

    def _link_entity(self, entity_text: str) -> str:
        """实体链接"""
        # 1. 精确匹配
        for canonical, aliases in self.entity_aliases.items():
            if entity_text in aliases or entity_text == canonical:
                return canonical
        
        # 2. 模糊
        entity_embedding = self.get_text_embedding(entity_text)
        max_similarity = 0
        best_match = None
        
        for canonical, embedding in self.entity_embeddings.items():
            similarity = cosine_similarity(
                entity_embedding.reshape(1, -1),
                embedding.reshape(1, -1)
            )[0][0]
            
            if similarity > 0.9 and similarity > max_similarity:
                max_similarity = similarity
                best_match = canonical
        
        return best_match if best_match else entity_text

    def get_canonical_name(self, entity_text: str) -> str:
        """获取实体的规范名称"""
        return self._link_entity(entity_text)

    def get_aliases(self, entity_text: str) -> Set[str]:
        """获取实体的所有别名"""
        canonical = self._link_entity(entity_text)
        return self.entity_aliases.get(canonical, set())

    def add_alias(self, canonical: str, alias: str):
        """添加新的实体别名"""
        self.entity_aliases[canonical].add(alias)
        self.entity_embeddings[alias] = self.get_text_embedding(alias)

    def merge_entities(self, entity1: str, entity2: str):
        """合并两个实体（当发现它们实际上是同一个实体时）"""
        canonical1 = self._link_entity(entity1)
        canonical2 = self._link_entity(entity2)
        
        if canonical1 != canonical2:
            # 合并
            self.entity_aliases[canonical1].update(self.entity_aliases[canonical2])
            # 删除旧的
            del self.entity_aliases[canonical2]
            # update
            for alias in self.entity_aliases[canonical1]:
                self.entity_embeddings[alias] = self.get_text_embedding(alias) 