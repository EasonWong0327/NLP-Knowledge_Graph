import os
import logging
from dotenv import load_dotenv

load_dotenv('.env')

from src.utils.nlp.entity_extractor import EntityExtractor
from src.utils.nlp.relation_extractor import RelationExtractor
from src.utils.neo4j_exporter import Neo4jExporter

def setup_logging():
    """配置日志"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def test_neo4j_connection(uri: str, user: str, password: str) -> bool:
    """测试 Neo4j 连接
    
    Returns:
        bool: 连接是否成功
    """
    try:
        exporter = Neo4jExporter(uri, user, password)
        exporter.driver.verify_connectivity()
        exporter.close()
        return True
    except Exception as e:
        logging.error(f"Neo4j 连接测试失败: {str(e)}")
        return False

def main():
    setup_logging()
    
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        logging.error("请检查.env文件")
        return

    if not test_neo4j_connection(neo4j_uri, neo4j_user, neo4j_password):
        logging.error("无法连接到Neo4j，请检查连接信息和数据库状态")
        return

    # 示例文本
    text = """
【投资合作】2023年8月15日，阿里巴巴集团宣布与蚂蚁集团达成战略合作协议。根据协议，阿里巴巴将投资50亿元人民币，获得蚂蚁集团5%的股权。双方将在支付、金融科技等领域展开深度合作。

【产品发布】2023年9月1日，腾讯金融科技发布新一代智能风控系统"腾盾"。该系统采用先进的人工智能技术，可为金融机构提供全方位的风险管理解决方案。产品发布会上，招商银行、平安银行等多家金融机构表示将采用该系统。

【人事变动】2023年10月1日，中国建设银行宣布王建平出任首席风险官，全面负责银行风险管理工作。王建平此前担任建设银行金融科技部总经理，在金融科技领域有着丰富经验。

【财务报告】2024年第一季度，京东数科营收达到85.6亿元人民币，同比增长25.3%。其中，供应链金融业务收入占比最大，达到总营收的45%。公司预计2024年全年营收将突破400亿元。

【行业动态】近期，中国人民银行发布《金融科技发展规划（2024-2026）》，强调要推动区块链、人工智能等技术在金融领域的创新应用。百度、京东、阿里巴巴等科技巨头纷纷表示将加大在金融科技领域的投入。

【市场分析】截至2023年底，中国第三方支付市场规模达到万亿级别。其中，支付宝市场份额约40%，位居首位；微信支付紧随其后，份额约35%。分析师预计，2024年市场规模将进一步扩大。 
    """

    try:
        # 初始化抽取器
        entity_extractor = EntityExtractor()
        relation_extractor = RelationExtractor()

        # 抽取实体和关系
        entities = entity_extractor.extract_entities(text)
        relations = relation_extractor.extract_relations(text, entities)

        if not entities:
            logging.warning("未找到任何实体")
            return
            
        logging.info(f"抽取到 {len(entities)} 个实体和 {len(relations)} 个关系")
        
        # 打印实体和关系信息（调试用）
        logging.debug("实体列表:")
        for entity in entities:
            logging.debug(f"  - {entity}")
        logging.debug("关系列表:")
        for relation in relations:
            logging.debug(f"  - {relation}")

        # 初始化
        exporter = Neo4jExporter(neo4j_uri, neo4j_user, neo4j_password)

        try:
            # 清空数据库
            if input("是否清空数据库？(y/n): ").lower() == 'y':
                exporter.clear_database()

            exporter.create_indexes()

            logging.info("开始导出实体...")
            exporter.export_entities(entities)

            logging.info("开始导出关系...")
            exporter.export_relations(relations)

            stats = exporter.get_statistics()
            logging.info(f"导出完成！数据库中现有 {stats['node_count']} 个节点和 {stats['relation_count']} 个关系")

        except Exception as e:
            logging.error(f"数据导出过程中发生错误: {str(e)}")
        finally:
            exporter.close()

    except Exception as e:
        logging.error(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 