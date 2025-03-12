import re
from typing import List, Tuple, Dict, Set
from collections import defaultdict
import jieba
import jieba.posseg as pseg
from transformers import BertTokenizer, BertModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .base_processor import BaseProcessor

class RelationExtractor(BaseProcessor):
    def __init__(self):
        """初始化关系抽取器"""
        super().__init__()
        # 加载BERT模型
        try:
            self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
            self.model = BertModel.from_pretrained('bert-base-chinese')
        except:
            print("BERT模型未安装")
            self.tokenizer = None
            self.model = None

        jieba.initialize()

        # 写的较简单
        self._load_relation_patterns()

    def get_relation_types(self) -> List[str]:
        """获取所有支持的关系类型"""
        return [
            "投资关系", "合作关系", "从属关系", "竞争关系", "供应关系",
            "时序关系", "因果关系", "地理关系", "产品关系", "人员关系"
        ]

    def extract_relations(self, text: str, entities: List[Tuple[str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """关系抽取"""
        relations = []
        entity_texts = {e[0] for e in entities}
        entity_dict = {e[0]: e for e in entities}
        
        # 1. 基于BERT的关系分类
        bert_relations = self._extract_bert_relations(text, entities)
        relations.extend(bert_relations)
        
        # 2. 基于模板的关系抽取
        template_relations = self._extract_template_relations(text, entity_texts, entity_dict)
        relations.extend(template_relations)
        
        # 3. 基于依存句法的关系抽取
        dependency_relations = self._extract_dependency_relations(text, entity_texts, entity_dict)
        relations.extend(dependency_relations)
        
        # 4. 基于共现的关系发现
        cooccurrence_relations = self._extract_cooccurrence_relations(text, entities)
        relations.extend(cooccurrence_relations)
        
        # 5. 关系验证和去重
        relations = self._validate_and_deduplicate_relations(relations)
        
        return relations

    def _load_relation_patterns(self):
        """加载关系抽取模板"""
        self.relation_patterns = {
            "投资关系": [
                r"(\w+)(?:投资|收购|入股)(\w+)",
                r"(\w+)(?:获得|接受)(\w+)(?:投资|收购)",
            ],
            "合作关系": [
                r"(\w+)(?:与|和|同)(\w+)(?:合作|签署|达成)",
                r"(\w+)(?:携手|联合)(\w+)",
            ],
            "从属关系": [
                r"(\w+)(?:是|为)(\w+)(?:的子公司|的分支)",
                r"(\w+)(?:隶属于|属于)(\w+)",
            ],
            "竞争关系": [
                r"(\w+)(?:与|和)(\w+)(?:竞争|争夺)",
                r"(\w+)(?:是|为)(\w+)(?:的竞争对手|的对手)",
            ],
            "供应关系": [
                r"(\w+)(?:为|给)(\w+)(?:供应|提供)",
                r"(\w+)(?:采购|购买)(\w+)(?:的产品|的服务)",
            ]
        }

    def _extract_bert_relations(self, text: str, entities: List[Tuple[str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """使用BERT模型进行关系分类"""
        if not self.model or not self.tokenizer:
            return []
            
        bert_relations = []
        
        for i, (entity1, type1, props1) in enumerate(entities):
            for j, (entity2, type2, props2) in enumerate(entities[i+1:], i+1):
                # 构建输入序列
                sequence = f"{entity1}[SEP]{entity2}"
                inputs = self.tokenizer(
                    sequence,
                    return_tensors="pt",
                    padding=True,
                    truncation=True
                )
                
                # 获取BERT表示
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    # 使用最后一层的[CLS]标记的输出作为序列表示
                    sequence_embedding = outputs.last_hidden_state[:, 0, :]  # [batch_size, hidden_size]
                    
                    # similarity启发式方法
                    if type1 == type2:  # 同类型实体
                        similarity = float(torch.cosine_similarity(
                            sequence_embedding,
                            sequence_embedding
                        ).item())
                        
                        if similarity > 0.8:  # 相似度阈值
                            # 根据实体类型确定关系
                            relation_type = self._infer_relation_by_types(type1, type2)
                            if relation_type:
                                properties = {
                                    'confidence': float(similarity),
                                    'method': 'bert_similarity',
                                    'context': str(self.get_context_window(text, text.find(entity1), text.find(entity2)))
                                }
                                bert_relations.append((entity1, relation_type, entity2, properties))
        
        return bert_relations
        
    def _infer_relation_by_types(self, type1: str, type2: str) -> str:
        """根据实体类型推断关系类型"""
        type_relation_map = {
            ('Company', 'Company'): '合作关系',
            ('Person', 'Company'): '任职关系',
            ('Company', 'Product'): '产品关系',
            ('Company', 'Industry'): '所属行业',
        }
        
        return type_relation_map.get((type1, type2)) or type_relation_map.get((type2, type1))

    def _extract_template_relations(self, text: str, entity_texts: Set[str], entity_dict: Dict) -> List[Tuple[str, str, str, Dict]]:
        """基于模板的关系抽取"""
        template_relations = []
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    head = match.group(1)
                    tail = match.group(2)
                    if head in entity_texts and tail in entity_texts:
                        #获取上下文窗口
                        context = self.get_context_window(text, match.start(), match.end())
                        #提取关系属性
                        properties = self._extract_relation_properties(head, tail, relation_type, context)
                        #添加实体类型信息
                        properties['head_type'] = entity_dict[head][1]
                        properties['tail_type'] = entity_dict[tail][1]
                        template_relations.append((head, relation_type, tail, properties))
        
        return template_relations

    def _extract_dependency_relations(self, text: str, entity_texts: Set[str], entity_dict: Dict) -> List[Tuple[str, str, str, Dict]]:
        """使用依存句法分析提取关系"""
        relations = []
        words = pseg.cut(text)
        
        # 使用基于规则的方法提取关系
        for entity1_text in entity_texts:
            for entity2_text in entity_texts:
                if entity1_text != entity2_text:  # 避免自反关系
                    # 在这里添加基于词性和位置的规则
                    if self._check_relation_pattern(text, entity1_text, entity2_text):
                        relation_type = self._determine_relation_type(text, 
                                                                    entity_dict[entity1_text], 
                                                                    entity_dict[entity2_text])
                        if relation_type:
                            properties = {
                                'confidence': 0.7,
                                'method': 'dependency_rule',
                                'context': self.get_context_window(text, 
                                                                 text.find(entity1_text), 
                                                                 text.find(entity2_text))
                            }
                            relations.append((entity1_text, relation_type, entity2_text, properties))
        
        return relations

    def _check_relation_pattern(self, text, entity1, entity2):
        """检查两个实体之间是否存在关系模式"""
        # 获取实体在文本中的位置
        pos1 = text.find(entity1)
        pos2 = text.find(entity2)
        
        if pos1 == -1 or pos2 == -1:
            return False

        between_text = text[min(pos1 + len(entity1), pos2 + len(entity2)):max(pos1, pos2)]
        words = list(jieba.cut(between_text))
        
        # 关系触发词
        relation_triggers = ['投资', '收购', '合作', '签署', '发布', '研发']
        
        # 检查是否存在触发词
        return any(trigger in words for trigger in relation_triggers)

    def _determine_relation_type(self, text: str, entity1: Tuple[str, str, Dict], entity2: Tuple[str, str, Dict]) -> str:
        """确定两个实体之间的关系类型"""
        # 获取实体之间的文本
        pos1 = text.find(entity1[0])
        pos2 = text.find(entity2[0])
        between_text = text[min(pos1 + len(entity1[0]), pos2 + len(entity2[0])):max(pos1, pos2)]
        
        # 关系类型映射
        relation_patterns = {
            '投资关系': ['投资', '入股', '收购'],
            '合作关系': ['合作', '签署', '达成'],
            '产品关系': ['发布', '推出', '上线'],
            '研发关系': ['研发', '开发', '创新']
        }
        
        # 检查每种关系类型
        for relation_type, patterns in relation_patterns.items():
            if any(pattern in between_text for pattern in patterns):
                return relation_type
        
        # 如果没有找到明确的关系类型，就尝试根据实体类型推断
        return self._infer_relation_by_types(entity1[1], entity2[1])

    def _extract_cooccurrence_relations(self, text: str, entities: List[Tuple[str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """基于共现抽取关系"""
        cooccurrence_relations = []
        window_size = 50  # 共现窗口大小
        
        for i, (entity1, type1, _) in enumerate(entities):
            for entity2, type2, _ in entities[i+1:]:
                # 检查两个实体是否在指定窗口内共现
                if self._check_cooccurrence(text, entity1, entity2, window_size):
                    properties = {
                        'confidence': 0.6,
                        'method': 'co-occurrence',
                        'window_size': int(window_size),
                        'context': str(self.get_context_window(text, text.find(entity1), text.find(entity2)))
                    }
                    cooccurrence_relations.append((entity1, "共现", entity2, properties))
        
        return cooccurrence_relations

    def _check_cooccurrence(self, text: str, entity1: str, entity2: str, window_size: int) -> bool:
        """检查两个实体是否在指定窗口内共现"""
        pos1 = text.find(entity1)
        pos2 = text.find(entity2)
        if pos1 == -1 or pos2 == -1:
            return False
        return abs(pos1 - pos2) <= window_size

    def _extract_relation_properties(self, head: str, tail: str, relation_type: str, context: str) -> Dict:
        """提取关系属性"""
        properties = {
            'confidence': float(self._calculate_relation_confidence(head, tail, relation_type, context)),
            'context': str(context),
            'timestamp': self._get_current_timestamp()
        }
        return properties

    def _calculate_relation_confidence(self, head: str, tail: str, relation_type: str, context: str) -> float:
        """计算关系可信度"""
        # TODO: 实现更复杂的可信度计算逻辑
        return 0.8

    def _validate_and_deduplicate_relations(self, relations: List[Tuple[str, str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """关系验证和去重"""
        #集合去重
        unique_relations = set((head, rel, tail) for head, rel, tail, _ in relations)

        merged_relations = []
        relation_properties = defaultdict(list)

        for head, rel, tail, props in relations:
            relation_properties[(head, rel, tail)].append(props)
        
        # 计算综合置信度
        for (head, rel, tail) in unique_relations:
            props_list = relation_properties[(head, rel, tail)]
            merged_props = self._merge_relation_properties(props_list)
            merged_relations.append((head, rel, tail, merged_props))

        merged_relations.sort(key=lambda x: x[3].get('confidence', 0), reverse=True)
        
        return merged_relations

    def _merge_relation_properties(self, props_list: List[Dict]) -> Dict:
        """合并多个关系属性"""
        merged = {}
        
        # 合并置信度，取加权平均
        confidences = [float(p.get('confidence', 0.5)) for p in props_list]
        merged['confidence'] = float(sum(confidences) / len(confidences))

        sources = set()
        for props in props_list:
            if 'source' in props:
                sources.add(str(props['source']))
        merged['sources'] = list(sources)
        
        # 保留最高置信度上下文
        contexts = [(float(p.get('confidence', 0)), str(p.get('context', ''))) 
                   for p in props_list if 'context' in p]
        if contexts:
            merged['context'] = str(max(contexts, key=lambda x: x[0])[1])

        merged['timestamp'] = self._get_current_timestamp()
        
        return merged

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S') 