'''
语料增强服务
作用：将一条原始话务，以“急躁型”、“啰嗦型”、“专业型”等不同风格进行 1 扩 3，为小模型微调积攒语料。
对应原代码：zyy/augmentation_opt_asr.py。
'''
import os
import sys
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.prompts import AUGMENTATION_PROMPT
from core_clients.llm_client import UnifiedLLMClient

class CorpusAugmentorService:
    """
    对话语料增强服务 (1 扩 3 引擎)
    作用：将一条原始话务，以“急躁型”、“啰嗦型”、“专业型”等不同风格进行扩写。
    用于为小模型微调 (Fine-tuning) 积攒高质量、多样性的语料。
    """
    def __init__(self):
        # 初始化文本大模型底座
        self.llm = UnifiedLLMClient(model_type="text")
        self.system_prompt = AUGMENTATION_PROMPT.get("system", "你是一个专业的数据增强专家。")
        self.user_template = AUGMENTATION_PROMPT["user_template"]

    def process(self, raw_text: str) -> list:
        """
        核心业务方法：执行语料增强
        :param raw_text: 原始的真实话务文本
        :return: 包含 3 种不同风格对话的字典列表
        """
        if not raw_text or not raw_text.strip():
            return []

        # 组装 Prompt
        prompt = self.user_template.format(raw_text=raw_text)
        
        print("[语料增强服务] 正在调用大模型进行 1 扩 3 风格裂变...")
        response_text = self.llm.chat_text(prompt=prompt, system_prompt=self.system_prompt)
        
        # 安全解析大模型输出
        return self._parse_safely(response_text)

    def _parse_safely(self, text: str) -> list:
        """
        高鲁棒性提取：优先使用 JSON 解析，若大模型输出格式崩塌，则自动切换为正则硬提取。
        """
        if not text:
            return []
            
        # 1. 预清洗：去除大模型可能生成的思考链或 Markdown 标记
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # 【修复乱码与截断的关键】：使用 `{3}` 来匹配三个反引号，防止干扰前端渲染引擎
        clean_text = re.sub(r'`{3}(?:json)?', '', text).strip()
        clean_text = clean_text.replace('`' * 3, '')
        
        # 2. 尝试优雅的 JSON 解析
        try:
            data = json.loads(clean_text)
            if "samples" in data:
                return data["samples"]
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            print("[业务层警告] 增强服务 JSON 解析失败，自动启动正则防御机制...")
            
        # 3. 兜底方案：正则硬提取 (绝对防御大模型幻觉)
        # 针对我们在 prompts.py 中定义的格式：{"style": "急躁型", "dialogue": "..."}
        samples = []
        pattern = r'(?:"style"|style)\s*[:：]\s*["\']?(.*?)["\']?\s*[,，].*?(?:"dialogue"|dialogue)\s*[:：]\s*["\']?(.*?)["\']?(?=\n|\}|, {|$)'
        
        matches = re.findall(pattern, clean_text, flags=re.DOTALL)
        for style, dialogue in matches:
            samples.append({
                "style": style.strip(),
                "dialogue": dialogue.strip()
            })
            
        return samples


# ==========================================
# 独立测试模块
# ==========================================
if __name__ == "__main__":
    service = CorpusAugmentorService()
    
    # 模拟真实短客诉
    mock_raw_dialogue = """
    客户：我那个 ERP 系统里找不到物资收发货的菜单了。
    客服：您确认一下有库管员权限吗？清理一下浏览器缓存，路径是‘物资管理-库存管理-库存收/发货管理’。
    客户：好的看到了，谢谢。
    """
    
    print("\n--- 原始语料 ---")
    print(mock_raw_dialogue.strip())
    
    print("\n--- 开始执行语料裂变 ---")
    results = service.process(mock_raw_dialogue)
    
    if results:
        for idx, item in enumerate(results, 1):
            print(f"\n[{idx}. {item.get('style', '未知风格')}]")
            print(item.get('dialogue', ''))
    else:
        print("语料增强失败。")
