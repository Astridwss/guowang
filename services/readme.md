系统主要分为两条核心业务流水线：

🌊 流水线一：知识库构建 (造大脑) —— 将企业操作手册转化为向量化的“超级大脑”。

🌊 流水线二：日常话务处理 (用大脑) —— 每天处理新增客服录音，进行 RAG 意图识别、打分与脱敏。

📂 所有具体的业务逻辑全部封装在 services/ 目录下。

🌊 流水线一：知识库构建 (Knowledge Base Pipeline)

目标：将 Word 手册变成 pkl 高维向量大脑，并提供数据洞察。

步骤            脚本文件                                服务名称            核心作用说明

第 1 步         document_splitter.py                  文档拆分服务          读取 .docx 操作手册，按 Heading 标题层级切分为逻辑块，并剥离内嵌图片到本地。

第 2 步         vision_qa_extractor.py                视觉图文提取服务      读取上一步的图文切块，调用Qwen-VL提炼出标准的FAQ (问题、步骤、原因)。

第 3 步         vector_embedding.py                   向量化               

第 4 步         vector_embedding.py                   建立索引             将问题向量存库，回答做成字典映射的.pkl

附加步          knowledge_clusterer.py                聚类可视化服务        读取 .pkl 向量文件，使用 HDBSCAN 进行无监督聚类，降维(t-SNE/PCA)并生成可交互的 3D HTML 散点图，发现近期客诉热点。

路由一：Excel：清洗--向量化--入库
路由二：Word:  清洗--VL--向量化--入库
路由三：针对库聚类3D

🌊 流水线二：日常话务流转 (Daily Call Pipeline)

目标：处理 .wav 客服录音，进行智能结构化、RAG 融合、打分与安全脱敏。

步骤            脚本文件                                服务名称            核心作用说明

第 1 步         audio_conversation_parser.py            语音对话解析服务    读取 .wav，发送至ARS，完成声纹切分与转写，吐出带角色(客服/客户)的纯文本。

第 2 步         dialogue_extractor.py                   话务盲提炼服务      调用文本大模型对语音文本进行首轮提炼，精准提取出“客户核心问题”。

第 3 步         knowledge_retriever.py                  知识向量检索服务    将提取出的“核心问题”转为向量，与 faq_features.pkl 计算余弦相似度。严格执行 >= 0.8 的匹配阈值裁判，坚决不调大模型。

第 4 步         rag_synthesizer.py                      RAG 知识融合服务    如果上一步命中知识库，则将“标准 FAQ 答案”作为参考塞入 Prompt，让大模型生成完美的结构化解答；若未命中则直接返回。

第 5 步         sentiment_auditor.py                    满意度质检服务 接 语音对话解析服务     对原始对话进行情绪和质量打分。内置“分数压缩与托底算法”(保底及格线)，保障业务平稳。

第 6 步         data_desensitizer.py                    数据安全脱敏服务    摒弃脆弱的 JSON，通过极其稳健的逐行遍历正则解析，将手机号、金额等敏感信息抹除并生成映射表 [PHONE_1] -> 138xxxx。

🛠️ 辅助与扩展服务 (Standalone Services)

脚本文件                    服务名称        核心作用说明        
corpus_augmentor.py         语料增强服务    用于造数据。将一条原始客服录音，通过大模型以“急躁型”、“啰嗦型”、“专业型”进行 1 扩 3，为后期微调自有小模型积攒丰富语料。


llm_clients/ (通信网络层)：绝对与业务解耦的底层发报机。
    llm_client.py: 统一管控文本大模型 HTTP 请求。
    embedding_client.py: 本地向量模型推理引擎。
    asr_client.py: 语音转写微服务通信。

config/ (配置层)：
    prompts.py: 集中管理所有大模型 Prompt 资产的“弹药库”。

pipelines/ (调度层)：
    pipeline_daily_qa.py: 扮演“车间主任”，将流水线二的各个独立微服务组装成一条自动化的生产线。

main.py (统一入口)：



原来代码extract_from_word.py脚本业务流程: 它通过命令行传入一个 Word 文件路径，利用 python-docx 把里面的段落、表格读取出来，把内嵌的图片抠出来存进本地文件夹，最后把所有这些结构化信息打包成一个巨大的 elements.json 文件存在硬盘上。

原来代码optdocx_api.py脚本业务流程: 拆分--vl--保存成本地excel--向量化存储   输出应该接到聚类3D服务上  【document_splitter.py】  【vision_qa_extractor.py】
 
原来代码extract_features.py脚本业务流程：向量化 【vector_embedding.py】

原来代码speaker_diarization.py脚本业务流程：语音撰写；  【audio_conversation_parser.py】

原来代码opt_asr.py脚本业务流程：原始的ARS文本--LLM初次提炼--向量化/存储--向量检索--rag融合检索
    ARS文本来自：speaker_diarization.py(audio_conversation_parser.py)生成
    LLM初次提炼：对应新代码【services/dialogue_extractor.py】
    向量化: 对应新代码【services/vector_embedding.py】
    向量存储: 对应新代码【services/index_store.py】
    向量检索: 对应新代码【services/knowledge_retriever.py】
    rag融合检索: 对应新代码【services/rag_synthesizer.py】

原来代码cluster.py脚本业务流程：聚类    【knowledge_cluster.py】