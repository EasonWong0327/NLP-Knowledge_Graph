from typing import List, Tuple, Dict
from collections import defaultdict
import networkx as nx
from .base_processor import BaseProcessor

class KnowledgeGraph(BaseProcessor):
    def __init__(self):
        """初始化知识图谱"""
        super().__init__()
        self.graph = nx.DiGraph()
        self.relation_types = set()

    def add_relations(self, relations: List[Tuple[str, str, str, Dict]]):
        """添加关系到知识图谱"""
        for head, relation_type, tail, props in relations:
            self.graph.add_edge(
                head,
                tail,
                relation_type=relation_type,
                properties=props
            )
            self.relation_types.add(relation_type)

    def get_relations(self, entity: str) -> List[Tuple[str, str, str, Dict]]:
        """获取实体的所有关系"""
        relations = []
        
        # 获取出边（实体作为头实体的关系）
        for _, tail, data in self.graph.out_edges(entity, data=True):
            relations.append((
                entity,
                data['relation_type'],
                tail,
                data['properties']
            ))
        
        # 获取入边（实体作为尾实体的关系）
        for head, _, data in self.graph.in_edges(entity, data=True):
            relations.append((
                head,
                data['relation_type'],
                entity,
                data['properties']
            ))
        
        return relations

    def query_relation_path(self, entity1: str, entity2: str, max_depth: int = 2) -> List[Dict]:
        """查询两个实体之间的关系路径"""
        relations = []
        
        # 两个实体的直接关系
        if self.graph.has_edge(entity1, entity2):
            edge_data = self.graph.get_edge_data(entity1, entity2)
            relations.append({
                'type': edge_data['relation_type'],
                'path': [entity1, entity2],
                'properties': edge_data['properties']
            })
        
        # 间接
        for path in nx.all_simple_paths(self.graph, entity1, entity2, cutoff=max_depth):
            path_relations = []
            path_properties = []
            
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                path_relations.append(edge_data['relation_type'])
                path_properties.append(edge_data['properties'])
            
            relations.append({
                'type': '->'.join(path_relations),
                'path': path,
                'properties': path_properties
            })
        
        return relations

    def get_subgraph(self, entity: str, depth: int = 1) -> nx.DiGraph:
        """获取以实体为中心的子图"""
        nodes = {entity}
        for _ in range(depth):
            new_nodes = set()
            for node in nodes:
                new_nodes.update(self.graph.predecessors(node))
                new_nodes.update(self.graph.successors(node))
            nodes.update(new_nodes)
        
        return self.graph.subgraph(nodes)

    def get_entity_statistics(self, entity: str) -> Dict:
        """获取实体的统计信息"""
        stats = {
            'degree': self.graph.degree(entity),
            'in_degree': self.graph.in_degree(entity),
            'out_degree': self.graph.out_degree(entity),
            'relation_types': defaultdict(int)
        }

        for _, _, data in self.graph.out_edges(entity, data=True):
            stats['relation_types'][data['relation_type']] += 1
        for _, _, data in self.graph.in_edges(entity, data=True):
            stats['relation_types'][data['relation_type']] += 1
        
        return stats

    def find_similar_entities(self, entity: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """查找与给定实体相似的实体"""
        if entity not in self.graph:
            return []
        
        similarities = []
        entity_embedding = self.get_text_embedding(entity)
        
        for other_entity in self.graph.nodes():
            if other_entity != entity:
                other_embedding = self.get_text_embedding(other_entity)
                similarity = self.calculate_similarity(entity_embedding, other_embedding)
                similarities.append((other_entity, similarity))
        
        # top_k个
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def merge_entities(self, entity1: str, entity2: str):
        """合并两个实体节点（当它们表示相同实体时）"""
        if entity1 not in self.graph or entity2 not in self.graph:
            return
        
        # 将entity2的所有边转移到entity1
        for pred in self.graph.predecessors(entity2):
            edge_data = self.graph.get_edge_data(pred, entity2)
            self.graph.add_edge(pred, entity1, **edge_data)
        
        for succ in self.graph.successors(entity2):
            edge_data = self.graph.get_edge_data(entity2, succ)
            self.graph.add_edge(entity1, succ, **edge_data)
        
        # 删除entity2节点
        self.graph.remove_node(entity2)

    def save_graph(self, filepath: str):
        """保存知识图谱"""
        nx.write_gpickle(self.graph, filepath)

    def load_graph(self, filepath: str):
        """加载知识图谱"""
        self.graph = nx.read_gpickle(filepath)
        self.relation_types = {
            data['relation_type']
            for _, _, data in self.graph.edges(data=True)
        } 