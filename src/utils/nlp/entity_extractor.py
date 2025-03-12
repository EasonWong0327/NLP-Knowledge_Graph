import jieba
import jieba.posseg as pseg
import re
from typing import List, Tuple, Dict, Set
from collections import defaultdict
from .base_processor import BaseProcessor
'''
更详细的ner，参考我的另外一个GitHub项目：https://github.com/EasonWong0327/NLP-NER
'''


class EntityExtractor(BaseProcessor):
    def __init__(self, model_path: str = "models/ner_model"):
        """初始化实体抽取器"""
        super().__init__()
        # 加载预训练的NER模型
        self.ner_model = self._load_ner_model(model_path)
        # 加载金融领域词典
        self._load_finance_dict()

    def extract_entities(self, text: str) -> List[Tuple[str, str, Dict]]:
        """
        实体识别
        Args:
            text: 输入文本
        Returns:
            实体列表，每个实体为(实体文本, 实体类型, 属性字典)的元组
        """
        entities = []
        seen_entities = {}  # 用于去重的字典
        
        # 1使用预训练NER模型识别实体
        ner_results = self.ner_model.predict(text)
        if ner_results:
            for result in ner_results:
                entity_text, entity_type = result
                properties = self._extract_entity_properties(entity_text, entity_type)
                entity_key = (entity_text, entity_type)
                seen_entities[entity_key] = (entity_text, entity_type, properties)
        
        # 2 规则模式
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entity_text = match.group()
                    # 获取实体属性
                    properties = self._extract_entity_properties(entity_text, entity_type)
                    entity_key = (entity_text, entity_type)
                    seen_entities[entity_key] = (entity_text, entity_type, properties)
        
        # 3 jieba分词进行补充识别
        words = pseg.cut(text)
        for word, flag in words:
            if flag.startswith('n'):  # n
                entity_type = self._determine_entity_type(word)
                if entity_type:
                    properties = self._extract_entity_properties(word, entity_type)
                    entity_key = (word, entity_type)
                    seen_entities[entity_key] = (word, entity_type, properties)

        entities = list(seen_entities.values())
        return entities

    def _load_ner_model(self, model_path: str):
        """加载NER模型"""
        class MockNERModel:
            def __init__(self):
                self.entity_types = ['Company', 'Industry', 'Product', 'Time', 'Metric', 'Currency']
            
            def predict(self, text):
                return []
        
        return MockNERModel()

    def _load_finance_dict(self):
        """加载金融领域词典和实体类型映射"""
        self.entity_patterns = {
            'Company': [r'.*公司$', r'.*集团$', r'.*银行$', r'.*证券$'],
            'Industry': [r'.*行业$', r'.*板块$'],
            'Product': [r'.*基金$', r'.*股票$', r'.*期货$'],
            'Time': [r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{4}年\d{1,2}月', r'\d{4}年'],
            'Amount': [r'\d+\.?\d*[万亿]?[美]?元', r'\d+\.?\d*%'],
            'Person': [r'.*总经理$', r'.*董事长$', r'.*总裁$']
        }
        
        self.finance_terms = {
            "股票": "Product",
            "基金": "Product",
            "债券": "Product",
            "期货": "Product",
            "证券": "Product",
            "银行": "Company",
            "保险": "Industry",
            "信托": "Industry",
            "投资": "Metric",
            "理财": "Product",
            "A股": "Product",
            "港股": "Product",
            "美股": "Product",
            "创业板": "Industry",
            "科创板": "Industry"
        }
        
        for word in self.finance_terms:
            jieba.add_word(word)

    def _determine_entity_type(self, text: str) -> str:
        """确定实体类型"""
        # 遍历实体模式判断类型
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                if re.match(pattern, text):
                    return entity_type
        return None

    def _extract_entity_properties(self, entity_text: str, entity_type: str) -> Dict:
        """提取实体属性"""
        properties = {}
        
        if entity_type == 'Company':
            properties['stock_code'] = self._extract_stock_code(entity_text)
            properties['industry'] = self._extract_company_industry(entity_text)
        
        elif entity_type == 'Product':
            properties['category'] = self._extract_product_category(entity_text)
        
        elif entity_type == 'Time':
            properties['normalized'] = self._normalize_time(entity_text)
        
        elif entity_type == 'Amount':
            properties['value'] = self._normalize_amount(entity_text)
            properties['unit'] = self._extract_amount_unit(entity_text)
        
        # 添加实体向量表示
        properties['embedding'] = self.get_text_embedding(entity_text)
        
        return properties

    def _extract_stock_code(self, company_name: str) -> str:
        """提取股票代码"""
        # TODO: 实现股票代码提取逻辑
        return ""

    def _extract_company_industry(self, company_name: str) -> str:
        """提取公司所属行业"""
        # TODO: 实现行业提取逻辑
        return ""

    def _extract_product_category(self, product_name: str) -> str:
        """提取产品类别"""
        # TODO: 实现产品类别提取逻辑
        return ""

    def _normalize_time(self, time_text: str) -> str:
        """标准化时间表达"""
        # TODO: 实现时间标准化逻辑
        return time_text

    def _normalize_amount(self, amount_text: str) -> float:
        """标准化金额"""
        # 移除非数字
        num = re.findall(r'\d+\.?\d*', amount_text)[0]
        value = float(num)
        
        # re
        if '亿' in amount_text:
            value *= 100000000
        elif '万' in amount_text:
            value *= 10000
            
        return value

    def _extract_amount_unit(self, amount_text: str) -> str:
        """提取金额单位"""
        if '美元' in amount_text:
            return 'USD'
        elif '欧元' in amount_text:
            return 'EUR'
        elif '港元' in amount_text:
            return 'HKD'
        else:
            return 'CNY' 