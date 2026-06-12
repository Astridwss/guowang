## 使用方式
激活环境：.\venv\Scripts\activate
启动命令：bash star.sh    或 cd ./api/ && python -m uvicorn main:app
构建镜像：docker build -t 镜像名:版本 .
		ARM架构采用 FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-linuxarm64
		AMD架构采用 FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim
打包镜像：docker save -o 压缩包名.tar 镜像名:版本
配合后端需要挂载nfs,部署/启动容器：docker run -it -p 宿主机端口:8080 -v 宿主机路径:容器里路径 --name 容器名 /bin/bash
调试进入容器后启动命令：python -m uvicorn main:app --host 0.0.0.0 --port 8080

API的docs文档查看：部署ip:端口/docs，例如192.168.0.80:7511/docx

AMD镜像：./grid-algo-amd.tar
ARM镜像：./grid-algo-arm.tar

#  路由接口介绍
## 话务处理接口 (对应原 opt_asr.py)
## 路由：POST /api/v1/rag
整合的脚本：opt_asr.py 
输入: 
	{
		"work_dir": "C:/webace_2026/guowang/code/LLM/Smart_QA_System/data/",
		"task_id": "rag_002",
		"asr_file_url": "C:/webace_2026/guowang/code/LLM/Smart_QA_System/test_data/rawASR.xlsx",
		"faq_file_url": "C:/webace_2026/guowang/code/LLM/Smart_QA_System/test_data/FAQ.xlsx",
		"llm_config": {
			"chat_base_url": "http://192.168.0.80:8020/v1",
			"chat_model_name": "Qwen/Qwen3.6-35B-A3B-GPTQ-Int8",
			"embed_base_url": "http://192.168.0.79:8003/v1",
			"embed_model_name": "/data/home/wangshan/guowang_LLM/bge-large-zh-v1.5"
		}
	}
处理逻辑：
		FAQ.xlsx (知识库)：首先将FAQ.xlsx (知识库)的“问题”列向量化存储为 faiss.index，“答案”列存储为 metadata.pkl
		rawASR.xlsx (原始话务表)：
		第一轮大模型裸抽：大模型处理'ASR'列，输出 '问题、所属业务域、答案（原因、操作步骤、菜单路径）'
		正则提取核心问题：代码使用正则表达式 r'问题：\s*(.+)'，从大模型第一轮的回答中，把用户咨询的“核心问题”单独抠出来，赋值给 refined_question。
		向量化与相似度检索：
			将抠出来的 refined_question 交给 Embedding 向量模型（gte-Qwen2-7B），把它变成一组高维向量 refined_feature。
			将这个特征向量与一开始加载的 FAQ.xlsx 里的所有标准问题向量逐一计算余弦相似度（Cosine Similarity）。
			找出得分最高的那条 FAQ，记录下它的最高分 max_sim、标准问题 best_faq_question 和标准答案 best_faq_answer。
		RAG 判决与第二轮大模型生成：
			如果命中知识库（max_sim >= 0.8 且存在匹配项）：
			代码会把找到的标准 FAQ 问题和答案，强行塞进 Prompt 的尾部（“以下问答内容为外部知识库中检索到的相似信息，仅供参考...”），然后带着这段外部知识，第二次请求大模型。大模型参考了标准答案后生成的最终结果，定为 final_output。
			如果未命中（相似度 < 0.8）：
			直接把第一步大模型“裸抽”出来的 initial_output 作为 final_output。
打包返回：将这中间产生的 6 个关键变量打包成元组返回给多线程收集器。
	{
		task_id: str
		status: str
		result_detailed_file_url: Optional[str] = ""
		result_opt_file_url: Optional[str] = ""
		log: str
	}

输出：detailed_FAQ_output.xls
输出文件列名                                        数据来源与含义
ASR                                             直接来自输入文件rawASR.xlsx。即用户传入的原始客服录音转写文本 。  
refined_question                                来自第一轮大模型提炼。大模型从 ASR 中总结出的用户核心诉求，也是用于去知识库里检索的 query 。  
faq_question                                    来自输入文件FAQ.xlsx。如果相似度最高，这里显示命中的那条标准 FAQ 的问题；如果没匹配到，这里为空 。  
similarity                                      来自代码计算结果。由 Embedding 模型计算出的 refined_question 与 faq_question 之间的余弦相似度得分 。  
final_output                                    来自大模型最终输出。如果命中了知识库，这是大模型参考了标准 FAQ 重新润色后的回答；如果没有命中，这就是大模型第一轮凭借自己知识直接生成的回答 。  
faq_answer                                      来自输入文件 FAQ.xlsx。命中的那条标准 FAQ 的原始答案 。  

## 数据增强接口 (对应原 cluster.py)
## 路由：POST /api/v1/augmentation
整合的脚本：augmentation_opt_asr.py
入参：
    {
		work_dir: str
		task_id: str
		source_file_url: str                             # 必须：原始对话 opt_ASR 表格路径
		llm_config: Optional[ModelConfig] = None         # 可选：平台下发的动态模型配置
	}
内部处理逻辑：

输出：
	{
		task_id: str
		status: str
		result_file_url: Optional[str] = ""  # 数据增强通常只有1个产物文件
		log: str
	}
	输出excel文件列名：opt_ASR原文	augment_1	augment_2	augment_3


## 知识聚类分析接口 (对应原 cluster.py)
## 路由：POST /api/v1/cluster
整合的脚本：cluster.py 
入参 (Request)：
	task_id: 任务ID
	work_dir: 工作目录
	faq_file_url: 带有问题的知识库表格（可以直接是接口1的产物，也可以是任意带有"问题"列的表格）
	clustering: 聚类算法类型 (可选，如 hdbscan, kmeans)
	n_clusters: 聚类数量 (可选)
	llm_config: 向量模型配置 (Embedding_LLM)
	这里要不要"dim_reduce"参数
内部逻辑：
	下载 faq_file_url。
	强制调用 VectorEmbeddingService 实时计算文本向量（取代 .pkl 读取过程）。
	执行降维（PCA/t-SNE）和聚类（HDBSCAN/KMeans）。
	生成可视化 HTML 或图表。
产物 (Response/State)：
	result_html_url: 聚类可视化html路径。


## 接口 1：文档解析与多模态抽取接口
## 路由：POST /api/v1/document_extraction
整合的脚本：extract_from_word.py + optdocx_api.py
入参 (Request)：
	task_id: 任务ID
	work_dir: 工作目录
	document_url: 原始 .docx 文件的下载路径
	llm_config: 多模态大模型配置 (VL_LLM)
内部逻辑：下载 Word -> 切割存图 -> 喂给视觉大模型 -> 清洗幻觉数据。
产物 (Response)：输出一个结构化的 faq_extracted.xlsx。


## 话务脱敏接口 (对应原 desensitization.py)
## 路由：POST /api/v1/desentitize
整合脚本：desensitization.py
入参：
	{
		work_dir: str
		task_id: str
		asr_file_url: str                                # 必须：待脱敏的原始客服对话 Excel 表格
		tooltip: Optional[Dict[str, str]] = None         # 可选：自定义敏感词映射字典, 例如 {"手机号": "PHONE"}
		llm_config: Optional[ModelConfig] = None         # 可选：大语言模型配置项
	}
内部逻辑：具体看提示词。核心是prompt.format(tooltip)
输出：
	{
		task_id: str
		status: str
		result_excel_url: Optional[str] = ""             # 产物1：脱敏后的明细 Excel 文件路径
		#result_image_url: Optional[str] = ""             # 产物2：脱敏字段数量分布统计图路径
		log: str
	}
	输出文件列名字：ASR原文	脱敏后文本	脱敏字段数量	脱敏类型	敏感信息映射

## 话务情绪分析接口 (对应原 raw_asr_sentiment_analysis.py)
## 路由：POST /api/v1/sentiment_analysis
整合脚本：raw_asr_sentiment_analysis.py
入参：
	{
		work_dir: str
		task_id: str
		asr_file_url: str                                # 必须：待分析的原始客服对话 Excel 表格
		llm_config: Optional[ModelConfig] = None         # 可选：多模态/大模型底层运行配置
	}
内部逻辑：具体看提示词。
输出：
	{    
		task_id: str
		status: str
		result_excel_url: Optional[str] = ""             # 产物：情绪质检完备的 Excel 表格物理路径
		log: str
	}
	输出文件列名：ASR	情感评分	情感结论	关键依据	改进建议