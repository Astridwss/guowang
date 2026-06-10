# 文件路径：utils/text_processor.py
import re

class TextProcessor:
    """
    全局共享的纯粹文本处理工具库
    职责：收拢全系统所有的正则表达式、清洗、Markdown去除和数据提取逻辑。
    """
    
    @staticmethod
    def clean_text(text: str, filter_invalid: bool = True, remove_punctuation: bool = False, remove_words: str = "") -> str:
        """核心：基础文本清洗"""
        if not isinstance(text, str): text = str(text)
        if filter_invalid and (text.lower() in ['nan', 'none', 'null', ''] or text.strip() == ''):
            return ""
        if remove_punctuation:
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', text)
        if remove_words:
            for word in [w.strip() for w in remove_words.split(',') if w.strip()]:
                text = text.replace(word, '')
        return text.strip()

    @staticmethod
    def remove_markdown(text: str) -> str:
        """核心：清洗大模型输出的 Markdown 标记"""
        text = re.sub(r'[*_`#>~]+', '', text)
        text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
        text = text.strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    @staticmethod
    @staticmethod
    def parse_llm_qa_extraction(raw_output: str, default_domain: str = "文档自动提炼") -> tuple:
        """
        核心：匹配最新原版 Prompt 的 5 字段输出格式。
        提取：问题、所属业务域、原因、操作步骤、菜单路径。
        """
        clean_text = TextProcessor.remove_markdown(raw_output)
        
        # 按照“问题：”进行物理分块
        segments = re.split(r'\n*(?=问题：)', clean_text)
        
        valid_texts = []
        payloads = []

        for seg in segments:
            seg = seg.strip()
            if not seg.startswith('问题：'): 
                continue

            # 使用强大的正则精准抠出各个字段
            q_match = re.search(r'问题：(.*?)(?=\n所属业务域：|\n答案：|$)', seg, re.S)
            domain_match = re.search(r'所属业务域：(.*?)(?=\n答案：|\n原因：|$)', seg, re.S)
            reason_match = re.search(r'原因：(.*?)(?=\n操作步骤：|$)', seg, re.S)
            step_match = re.search(r'操作步骤：(.*?)(?=\n菜单路径：|$)', seg, re.S)
            path_match = re.search(r'菜单路径：(.*?)$', seg, re.S)
            
            raw_q = q_match.group(1).strip() if q_match else ""
            raw_domain = domain_match.group(1).strip() if domain_match else default_domain
            raw_reason = reason_match.group(1).strip() if reason_match else ""
            raw_step = step_match.group(1).strip() if step_match else ""
            raw_path = path_match.group(1).strip() if path_match else ""
            
            # 过滤大模型幻觉产生的无意义内容
            if not raw_q or "无" in raw_q[:2]: 
                continue

            # 最终洗涤核心问题 (确保向量检索不偏移)
            clean_q = TextProcessor.clean_text(raw_q)
            
            # 将原因、步骤、路径优美地拼装成最终的 answer
            ans_parts = []
            if raw_reason and raw_reason != "无": ans_parts.append(f"原因：{raw_reason}")
            if raw_step and raw_step != "无": ans_parts.append(f"操作步骤：{raw_step}")
            if raw_path and raw_path != "无": ans_parts.append(f"菜单路径：{raw_path}")
            final_ans = "\n".join(ans_parts)

            if clean_q:
                valid_texts.append(clean_q)
                payloads.append({
                    "question": clean_q,
                    "answer": final_ans,
                    "domain": raw_domain
                })
                
        return valid_texts, payloads