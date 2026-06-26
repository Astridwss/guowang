# 文件路径：services/data_desensitizer.py
import os
import sys
import re
import json
from collections import defaultdict
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prompts import DESENSITIZE_PROMPT, ENTITY_EXTRACT_TEMPLATE
from llm_clients.llm_client import UnifiedLLMClient

# 稳定高能的正则表达式模式
RULE_PATTERNS = {
    "ID_CARD": r'\b\d{17}[\dXx]\b',
    "PHONE": r'\b1[3-9]\d{9}\b',
    "EMAIL": r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
    "IP": r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
}

class PlaceholderManager:
    """
    统一占位符状态管理器
    """
    def __init__(self):
        self.entity_map = {}
        self.counter = defaultdict(int)

    def get_placeholder(self, entity: str, tag: str) -> str:
        if entity in self.entity_map:
            return self.entity_map[entity]

        self.counter[tag] += 1
        placeholder = f"[{tag}_{self.counter[tag]}]"
        self.entity_map[entity] = placeholder
        return placeholder


class DataDesensitizerService:
    """
    智能化高级脱敏核心积木 (基于确定性替换架构)
    """
    def __init__(self, base_url=None, api_key=None, model_name=None):
        self.llm_client = UnifiedLLMClient(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )
        self.sys_prompt = DESENSITIZE_PROMPT["system"]

    def _regex_desensitize(self, text: str, tooltip: Dict[str, str], manager: PlaceholderManager) -> Tuple[str, Dict[str, str]]:
        '''正则格式脱敏'''
        mappings = {}
        for keyword, tag in tooltip.items():
            if tag not in RULE_PATTERNS:
                continue
            
            pattern = RULE_PATTERNS[tag]
            matches = re.findall(pattern, text)
            
            for m in sorted(set(matches), key=len, reverse=True):
                placeholder = manager.get_placeholder(m, tag)
                text = text.replace(m, placeholder)
                mappings[placeholder] = m
                
        return text, mappings

    def _extract_entities(self, text: str, tooltip: Dict[str, str]) -> Dict[str, list]:
        '''LLM 实体抽取'''
        if not tooltip:
            return {}

        sensitive_definition = ""
        for k, v in tooltip.items():
            sensitive_definition += f"{k} -> 替换标签:{v}\n"

        prompt = ENTITY_EXTRACT_TEMPLATE.format(
            sensitive_definition=sensitive_definition.strip(),
            text=text
        )

        raw_output = self.llm_client.chat_text(prompt=prompt, system_prompt=self.sys_prompt)
        if not raw_output:
            return {}

        raw_output = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).split(r"</think>")[-1].strip()

        try:
            json_match = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(raw_output)
        except Exception as e:
            print(f"[Desensitizer Warning] JSON 解析失败，大模型原始输出: {raw_output}, 错误: {str(e)}")
            return {}

    def _entity_replace(self, text: str, entities: Dict[str, list], tooltip: Dict[str, str], manager: PlaceholderManager) -> Tuple[str, Dict[str, str]]:
        '''优先执行实体替换'''
        mappings = {}
        if not entities:
            return text, mappings

        for category, values in entities.items():
            tag = tooltip.get(category)
            if not tag or not isinstance(values, list):
                continue

            for entity in sorted(set(str(v) for v in values if v), key=len, reverse=True):
                entity = entity.strip()
                if not entity:
                    continue
                if entity not in text:
                    continue

                placeholder = manager.get_placeholder(entity, tag)
                text = text.replace(entity, placeholder)
                mappings[placeholder] = entity

        return text, mappings

    def _keyword_replace(self, text: str, tooltip: Dict[str, str], manager: PlaceholderManager) -> Tuple[str, Dict[str, str]]:
        '''执行关键字兜底替换 (收拾落单的纯关键字)'''
        mappings = {}
        keywords = sorted(tooltip.items(), key=lambda x: len(x[0]), reverse=True)
        
        for keyword, tag in keywords:
            if keyword not in text:
                continue

            placeholder = manager.get_placeholder(keyword, tag)
            text = text.replace(keyword, placeholder)
            mappings[placeholder] = keyword

        return text, mappings

    def process_line(self, asr_text: str, tooltip: Dict[str, str] = None, model_name: str = None) -> Tuple[str, int, str, str]:
        if not asr_text or str(asr_text).strip() == "":
            return "", 0, "无", "{}"

        if not tooltip:
            tooltip = {}

        manager = PlaceholderManager()
        final_mapping = {}

        # 1. 执行正则格式脱敏
        text, rule_mapping = self._regex_desensitize(asr_text, tooltip, manager)
        final_mapping.update(rule_mapping)

        # 2. 基于 Regex 后的文本进行 LLM 实体抽取
        entities = self._extract_entities(text, tooltip)

        # 3. 优先执行实体替换 (彻底避免碎片化冲突)
        text, entity_mapping = self._entity_replace(text, entities, tooltip, manager)
        final_mapping.update(entity_mapping)

        # 4. 执行关键字兜底替换 (收拾落单的纯关键字)
        text, keyword_mapping = self._keyword_replace(text, tooltip, manager)
        final_mapping.update(keyword_mapping)

        # 5. 反查标签分类并规整
        desensitized_types = []
        inv_tooltip = {v: k for k, v in tooltip.items()}
        
        for placeholder in final_mapping.keys():
            tag_match = re.match(r"\[([A-Za-z0-9_]+)_\d+\]", placeholder)
            if tag_match:
                tag_name = tag_match.group(1)
                ch_name = inv_tooltip.get(tag_name, tag_name)
                desensitized_types.append(ch_name)

        desensitized_types_str = ",".join(set(desensitized_types)) if desensitized_types else "无"

        return (
            text,
            len(final_mapping),
            desensitized_types_str,
            str(final_mapping)
        )