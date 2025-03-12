import pyvis.network as net
from src.utils.nlp.entity_extractor import EntityExtractor
from src.utils.nlp.relation_extractor import RelationExtractor
from src.utils.nlp.knowledge_graph import KnowledgeGraph
from src.utils.nlp.event_extractor import EventExtractor
from src.utils.nlp.temporal_analyzer import TemporalAnalyzer

def process_text(text):
    """处理输入文本并返回处理结果"""
    entity_extractor = EntityExtractor()
    relation_extractor = RelationExtractor()
    event_extractor = EventExtractor()
    temporal_analyzer = TemporalAnalyzer()
    kg = KnowledgeGraph()
    
    # 处理流程
    entities = entity_extractor.extract_entities(text)
    relations = relation_extractor.extract_relations(text, entities)
    events = event_extractor.extract_events(text, entities)
    temporal_relations = temporal_analyzer.extract_temporal_relations(text, entities)
    
    # 添加到知识图谱
    kg.add_relations(relations)
    
    return entities, relations, events, temporal_relations, kg

def visualize_knowledge_graph(kg):
    """可视化知识图谱并保存为HTML文件"""
    network = net.Network(height='600px', width='100%', bgcolor='#ffffff', font_color='black')
    
    # 设置节点颜色
    colors = {
        'Company': '#ff7675',
        'Person': '#74b9ff',
        'Product': '#55efc4',
        'Time': '#a29bfe',
        'Amount': '#ffeaa7'
    }

    for node in kg.graph.nodes():
        node_type = kg.graph.nodes[node].get('type', 'default')
        color = colors.get(node_type, '#95a5a6')
        network.add_node(node, label=node, title=node, color=color)
    
    # 添加边
    for edge in kg.graph.edges(data=True):
        relation_type = edge[2]['relation_type']
        network.add_edge(edge[0], edge[1],
                        title=relation_type,
                        label=relation_type,
                        arrows='to')
    
    # 布局
    network.set_options('''
    var options = {
        "nodes": {
            "shape": "dot",
            "size": 20,
            "font": {"size": 14}
        },
        "edges": {
            "font": {"size": 12, "align": "middle"},
            "color": {"color": "#848484"},
            "smooth": {"type": "continuous"}
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based"
        }
    }
    ''')

    network.save_graph('knowledge_graph.html')
    print("知识图谱已保存为 knowledge_graph.html")

def main():
    """主函数"""
    try:
        with open('src/data/financial_news.txt', 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print("未找到示例文本文件，使用默认文本")
        text = """阿里巴巴于2023年8月15日宣布投资蚂蚁集团50亿元。
腾讯在2023年9月1日发布新一代安全产品腾盾。
字节跳动与百度在人工智能领域展开合作。"""
    
    print("开始处理文本...")
    # 主要的nlp处理
    entities, relations, events, temporal_relations, kg = process_text(text)

    print("\n识别的实体:")
    for entity, type_, props in entities:
        print(f"- {entity} ({type_})")

    print("\n抽取的关系:")
    for head, rel, tail, props in relations:
        print(f"- {head} --[{rel}]--> {tail}")

    print("\n识别的事件:")
    for event in events:
        print(f"- 类型: {event['type']}")
        print(f"  触发词: {event['trigger']}")
        print(f"  参与者: {event['participants']}")

    print("\n生成知识图谱可视化...")
    visualize_knowledge_graph(kg)
    print("\n处理完成！您可以在浏览器中打开knowledge_graph.html查看可视化结果")

if __name__ == "__main__":
    main() 