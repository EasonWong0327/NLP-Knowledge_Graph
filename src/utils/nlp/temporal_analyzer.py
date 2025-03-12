from typing import List, Tuple, Dict
from datetime import datetime
import re
from .base_processor import BaseProcessor

class TemporalAnalyzer(BaseProcessor):
    def __init__(self):
        """初始化时序分析器"""
        super().__init__()
        self._init_time_patterns()

    def _init_time_patterns(self):
        """初始化时间模式"""
        self.time_patterns = {
            'date': r'\d{4}年\d{1,2}月\d{1,2}日',
            'month': r'\d{4}年\d{1,2}月',
            'year': r'\d{4}年',
            'quarter': r'\d{4}年第[一二三四]季度',
            'relative': r'[去今明后]年|上[个月季]|下[个月季]'
        }

    def extract_temporal_relations(self, text: str, entities: List[Tuple[str, str, Dict]]) -> List[Tuple[str, str, str, Dict]]:
        """时序关系抽取"""
        temporal_relations = []
        
        # 时间表达式
        time_entities = [(e[0], e[2].get('normalized', e[0])) 
                        for e in entities if e[1] == 'Time']

        time_entities.sort(key=lambda x: self._parse_time(x[1]))
        
        # 构建时序关系
        for i in range(len(time_entities) - 1):
            current_time, next_time = time_entities[i], time_entities[i + 1]
            
            # 找到与时间相关的事件或实体
            current_events = self._find_related_events(text, current_time[0])
            next_events = self._find_related_events(text, next_time[0])
            
            # 建立时序关系
            for curr_event in current_events:
                for next_event in next_events:
                    properties = {
                        'time_diff': self._calculate_time_diff(
                            current_time[1],
                            next_time[1]
                        ),
                        'temporal_order': 'before'
                    }
                    temporal_relations.append((
                        curr_event,
                        "时序关系",
                        next_event,
                        properties
                    ))
        
        return temporal_relations

    def _parse_time(self, time_text: str) -> datetime:
        """解析时间表达式"""
        try:
            if re.match(r'\d{4}年\d{1,2}月\d{1,2}日', time_text):
                return datetime.strptime(time_text, '%Y年%m月%d日')
            elif re.match(r'\d{4}年\d{1,2}月', time_text):
                return datetime.strptime(time_text, '%Y年%m月')
            elif re.match(r'\d{4}年', time_text):
                return datetime.strptime(time_text, '%Y年')
            else:
                return datetime.now()  # 默认返回当前时间
        except:
            return datetime.now()

    def _calculate_time_diff(self, time1: str, time2: str) -> str:
        """计算时间差"""
        t1 = self._parse_time(time1)
        t2 = self._parse_time(time2)
        diff = t2 - t1
        
        if diff.days > 365:
            return f"{diff.days // 365}年"
        elif diff.days > 30:
            return f"{diff.days // 30}月"
        else:
            return f"{diff.days}天"

    def _find_related_events(self, text: str, time_expr: str) -> List[str]:
        """查找与时间表达式相关的事件"""
        related_events = []
        window_size = 50
        time_pos = text.find(time_expr)
        if time_pos != -1:
            window_text = text[max(0, time_pos - window_size):
                             min(len(text), time_pos + len(time_expr) + window_size)]
            event_triggers = {
                "投资": ["投资", "收购", "入股"],
                "合作": ["合作", "签署", "达成"],
                "财务": ["营收", "利润", "增长"]
            }
            for event_type, triggers in event_triggers.items():
                for trigger in triggers:
                    if trigger in window_text:
                        related_events.append(trigger)
        return related_events

    def normalize_time(self, time_text: str) -> str:
        """标准化时间表达式"""
        #相对时间
        if re.match(r'[去今明后]年', time_text):
            current_year = datetime.now().year
            if time_text.startswith('去'):
                return f"{current_year-1}年"
            elif time_text.startswith('今'):
                return f"{current_year}年"
            elif time_text.startswith('明'):
                return f"{current_year+1}年"
            elif time_text.startswith('后'):
                return f"{current_year+2}年"

        if '季度' in time_text:
            quarter_map = {'一': 1, '二': 2, '三': 3, '四': 4}
            for zh, num in quarter_map.items():
                if zh in time_text:
                    year = re.findall(r'\d{4}', time_text)[0]
                    return f"{year}年Q{num}"
        
        return time_text 