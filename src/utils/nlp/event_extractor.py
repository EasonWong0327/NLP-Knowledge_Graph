import jieba
import jieba.posseg as pseg
from typing import List, Dict, Tuple

class EventExtractor:
    def __init__(self):
        """初始化事件抽取器"""
        jieba.initialize()
        
        # 事件触发词
        self.event_triggers = {
            '投资事件': ['投资', '收购', '入股', '融资'],
            '合作事件': ['合作', '签署', '达成', '协议'],
            '产品事件': ['发布', '推出', '上线', '研发'],
            '人事事件': ['任命', '升任', '离职', '加入'],
            '财务事件': ['营收', '利润', '亏损', '增长']
        }

    def extract_events(self, text: str, entities: List[Tuple[str, str, Dict]]) -> List[Dict]:
        """从文本中抽取事件"""
        events = []
        words = list(pseg.cut(text))

        for i, (word, flag) in enumerate(words):
            event_type = self._check_trigger_word(word)
            if event_type:
                # 事件参与者
                participants = self._find_event_participants(text, word, entities)

                event = {
                    'type': event_type,
                    'trigger': word,
                    'participants': participants
                }

                time_info = self._extract_time_info(text, word)
                if time_info:
                    event['time'] = time_info
                
                events.append(event)
        
        return events

    def _check_trigger_word(self, word: str) -> str:
        """检查词是否是事件触发词"""
        for event_type, triggers in self.event_triggers.items():
            if word in triggers:
                return event_type
        return None

    def _find_event_participants(self, text: str, trigger: str, entities: List[Tuple[str, str, Dict]]) -> Dict:
        """找到事件的参与者"""
        participants = {}
        trigger_pos = text.find(trigger)
        
        if trigger_pos == -1:
            return participants
        
        # 在触发词前后的窗口中查找实体
        window_size = 50
        
        for entity, entity_type, props in entities:
            entity_pos = text.find(entity)
            if entity_pos == -1:
                continue
            
            # 如果实体在触发词的合适距离内
            if abs(entity_pos - trigger_pos) <= window_size:
                # 根据实体类型和位置确定角色
                if entity_pos < trigger_pos:
                    role = self._determine_role(entity_type, 'subject')
                else:
                    role = self._determine_role(entity_type, 'object')
                
                if role:
                    participants[role] = entity
        
        return participants

    def _determine_role(self, entity_type: str, position: str) -> str:
        """根据实体类型和位置确定角色"""
        role_mapping = {
            'Company': {
                'subject': 'investor',
                'object': 'target'
            },
            'Person': {
                'subject': 'agent',
                'object': 'recipient'
            },
            'Product': {
                'subject': 'product',
                'object': 'product'
            }
        }
        
        return role_mapping.get(entity_type, {}).get(position, None)

    def _extract_time_info(self, text: str, trigger: str) -> str:
        """提取时间信息"""
        # re
        time_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}年\d{1,2}月',
            r'\d{4}年',
            r'\d{1,2}月\d{1,2}日'
        ]
        
        trigger_pos = text.find(trigger)
        if trigger_pos == -1:
            return None
        
        window_size = 50
        window_text = text[max(0, trigger_pos - window_size):min(len(text), trigger_pos + window_size)]
        
        import re
        for pattern in time_patterns:
            match = re.search(pattern, window_text)
            if match:
                return match.group()
        
        return None 