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

from core.prompts import AUGMENTATION_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class CorpusAugmentorService:
    """
    对话语料增强服务 (1 扩 3 引擎)
    作用：将一条原始话务，以“急躁型”、“啰嗦型”、“专业型”等不同风格进行扩写。
    用于为小模型微调 (Fine-tuning) 积攒高质量、多样性的语料。
    """
    def __init__(self, base_url=None, api_key=None, model_name=None, temperature=None):
        self.llm = UnifiedLLMClient(
            model_type="text",
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
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
        针对【纯文本轨道】的高鲁棒性文本切分器
        完美解析：版本1：... 版本2：... 版本3：...
        """
        if not text:
            return []

        # 1. 擦除思考链
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # 2. 使用正则动态切分三大版本块
        # 匹配 “版本X：” 或 “版本X:” 之后直到下一个版本或结尾的所有内容
        version_blocks = re.split(r'版本[123一二三][:：]', text)
        
        # 因为 split 会把“版本1：”前面的杂质带出来，我们只取后面切出来的有效文本块
        actual_contents = [block.strip() for block in version_blocks if block.strip()]
        
        samples = []
        styles = ["同义词替换增强", "句式转换增强", "问答重组增强"] # 完美映射原项目三大核心策略
        
        for i, content in enumerate(actual_contents[:3]):
            samples.append({
                "style": styles[i],
                "dialogue": content
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
