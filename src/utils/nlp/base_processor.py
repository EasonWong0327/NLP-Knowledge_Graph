from transformers import BertTokenizer, BertModel
import torch
import numpy as np

class BaseProcessor:
    def __init__(self):
        """初始化基础处理器"""
        # 加载BERT模型
        try:
            self.tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
            self.model = BertModel.from_pretrained('bert-base-chinese')
        except:
            print("!!!!!：BERT模型未安装")
            self.tokenizer = None
            self.model = None

    def get_text_embedding(self, text: str) -> np.ndarray:
        """获取文本的向量表示"""
        if not self.model or not self.tokenizer:
            return np.zeros(768)  # 返回零向量作为默认值
            
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

    def calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0
        return np.dot(vec1, vec2) / (norm1 * norm2)

    def get_context_window(self, text: str, start: int, end: int, window_size: int = 50) -> str:
        """获取指定位置的上下文窗口"""
        start = max(0, start - window_size)
        end = min(len(text), end + window_size)
        return text[start:end] 