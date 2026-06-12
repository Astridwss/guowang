import os
import sys
import re
from typing import Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 💡【彻底收口】：强制引入纯净配置底座，积木内部不留任何提示词硬编码
from core.prompts import DESENSITIZE_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class DataDesensitizerService:
    """
    智能化脱敏核心积木 (纯逻辑 Service 组件)
    职责：接收 ASR 文本流，动态编译并调度大模型交互，最终规整解析数据矩阵。
    """
    def __init__(self, base_url=None, api_key=None, model_name=None):
        self.llm_client = UnifiedLLMClient(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )
        # 从核心库统一读取系统级基座配置
        self.sys_prompt = DESENSITIZE_PROMPT["system"]

    def process_line(self, asr_text: str, tooltip: Dict[str, str] = None, model_name: str = None) -> Tuple[str, int, str, str]:
        """
        处理单条话务文本：动态决策分流并调用大模型
        """
        if not asr_text or str(asr_text).strip() == "":
            return "", 0, "无", "{}"

        # 💡【核心逻辑演进】：零拼接，通过数据字典动态灌注核心 prompts 模板的命名占位符
        if tooltip and len(tooltip) > 0:
            # 提取样例所需的关键字元组
            keys = list(tooltip.keys())
            vals = list(tooltip.values())
            
            first_key = keys[0]
            first_val = vals[0]
            second_key = keys[1] if len(keys) > 1 else first_key
            second_val = vals[1] if len(vals) > 1 else first_val

            # 灌注自定义动态模板
            user_content = DESENSITIZE_PROMPT["custom_user_template"].format(
                sensitive_list="、".join(keys),
                replacement_format="；".join([f"{k}：[{v}_1]、[{v}_2]等" for k, v in tooltip.items()]),
                first_key=first_key,
                first_val=first_val,
                second_key=second_key,
                second_val=second_val,
                raw_text=asr_text
            )
        else:
            # 灌注默认静态通用模板
            user_content = DESENSITIZE_PROMPT["default_user_template"].format(raw_text=asr_text)

        # 驱动大模型交互
        raw_output = self.llm_client.chat_text(prompt=user_content, system_prompt=self.sys_prompt)
        
        # 降级防御：防止由于网络超时返回空对象引发的后续崩溃错
        if raw_output is None:
            return "大模型连接超时，自动降级跳过该块", 0, "错误", "{}"

        # 剥离模型思考链路
        raw_output = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).split(r"</think>")[-1].strip()

        # 还原原脚本中经过生产压力检验的高精密度正则行扫描器
        desensitized_text = ""
        sensitive_mappings = {}
        lines = raw_output.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and "=" in line:
                mapping_match = re.match(r"\[([^\]]+)\]\s*=\s*(.+)", line)
                if mapping_match:
                    sensitive_mappings[mapping_match.group(1).strip()] = mapping_match.group(2).strip()
            elif not line.startswith("输出：") and not line.startswith("样例"):
                desensitized_text = desensitized_text + "\n" + line if desensitized_text else line

        if not desensitized_text:
            output_match = re.search(r"输出：\s*(.*?)(?=\n\[|$)", raw_output, flags=re.DOTALL)
            if output_match:
                desensitized_text = output_match.group(1).strip()

        sensitive_count = len(sensitive_mappings)

        # 基于前缀推断分类明细
        desensitized_types = []
        for key in sensitive_mappings.keys():
            if "ACCOUNT" in key: desensitized_types.append("账号")
            elif "PASSWORD" in key: desensitized_types.append("密码")
            elif "ORDER_ID" in key: desensitized_types.append("订单号")
            elif "PRICE" in key: desensitized_types.append("金额")
            elif "PHONE" in key: desensitized_types.append("电话")
            elif "EMPLOYEE_ID" in key: desensitized_types.append("人员编号")
            else: desensitized_types.append("其他敏感信息")

        desensitized_types_str = ", ".join(set(desensitized_types)) if desensitized_types else "无"
        
        return desensitized_text, sensitive_count, desensitized_types_str, str(sensitive_mappings)