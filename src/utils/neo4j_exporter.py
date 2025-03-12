from typing import List, Tuple, Dict
from neo4j import GraphDatabase
import logging

class Neo4jExporter:
    def __init__(self, uri: str, username: str, password: str):
        """初始化 Neo4j 导出器
        
        Args:
            uri: Neo4j 数据库 URI
            username: 用户名
            password: 密码
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self.driver.verify_connectivity()
        except Exception as e:
            logging.error(f"连接Neo4j数据库失败: {str(e)}")
            raise

    def verify_connectivity(self) -> bool:
        """验证数据库连接是否正常
        
        Returns:
            bool: 连接是否正常
        """
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logging.error(f"数据库连接验证失败: {str(e)}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()

    def export_entities(self, entities: List[Tuple[str, str, Dict]]):
        """导出实体到 Neo4j
        
        Args:
            entities: 实体列表，每个实体是一个元组 (name, type, properties)
        """
        with self.driver.session() as session:
            for name, entity_type, properties in entities:
                # 确保所有属性值都是基本类型
                clean_props = self._clean_properties(properties)
                
                # 创建实体节点Cypher查询
                cypher = (
                    "MERGE (n:%s {name: $name}) "
                    "SET n += $properties "
                    "RETURN n"
                ) % entity_type
                
                try:
                    session.run(cypher, name=name, properties=clean_props)
                except Exception as e:
                    logging.error(f"导出实体 {name} 失败: {str(e)}")

    def export_relations(self, relations: List[Tuple[str, str, str, Dict]]):
        """导出关系到 Neo4j
        
        Args:
            relations: 关系列表，每个关系是一个元组 (head, relation_type, tail, properties)
        """
        with self.driver.session() as session:
            for head, rel_type, tail, properties in relations:
                clean_props = self._clean_properties(properties)
                cypher = (
                    "MATCH (head), (tail) "
                    "WHERE head.name = $head AND tail.name = $tail "
                    "MERGE (head)-[r:%s]->(tail) "
                    "SET r += $properties "
                    "RETURN r"
                ) % rel_type
                
                try:
                    session.run(cypher, head=head, tail=tail, properties=clean_props)
                except Exception as e:
                    logging.error(f"导出关系 {head}-[{rel_type}]->{tail} 失败: {str(e)}")

    def _clean_properties(self, properties: Dict) -> Dict:
        """清理属性值，确保它们是 Neo4j 支持的类型
        
        Args:
            properties: 原始属性字典
            
        Returns:
            清理后的属性字典
        """
        clean_props = {}
        for key, value in properties.items():
            if isinstance(value, (int, float, str, bool)):
                clean_props[key] = value
            elif isinstance(value, list):
                clean_list = []
                for item in value:
                    if isinstance(item, (int, float, str, bool)):
                        clean_list.append(item)
                if clean_list:
                    clean_props[key] = clean_list
            elif value is None:
                clean_props[key] = None
                
        return clean_props

    def clear_database(self):
        """清空数据库中的所有节点和关系"""
        with self.driver.session() as session:
            try:
                session.run("MATCH (n) DETACH DELETE n")
                logging.info("数据库已清空")
            except Exception as e:
                logging.error(f"清空数据库失败: {str(e)}")

    def create_indexes(self):
        """创建必要的索引"""
        with self.driver.session() as session:
            try:
                # 为实体名称创建索引
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name)")
                logging.info("索引创建成功")
            except Exception as e:
                logging.error(f"创建索引失败: {str(e)}")

    def get_statistics(self) -> Dict:
        """获取数据库统计信息
        
        Returns:
            包含节点数量和关系数量的字典
        """
        with self.driver.session() as session:
            try:
                # 获取节点数量
                node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                # 获取关系数量
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                
                return {
                    "node_count": node_count,
                    "relation_count": rel_count
                }
            except Exception as e:
                logging.error(f"获取统计信息失败: {str(e)}")
                return {"node_count": 0, "relation_count": 0} 