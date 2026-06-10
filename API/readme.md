python -m uvicorn main:app --reload

路由： rag_router.py
输入: rawASR.xlsx (原始话务表)、FAQ.xlsx (知识库)
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
    打包返回：
        将这中间产生的 6 个关键变量打包成元组返回给多线程收集器。

输出：detailed_FAQ_output.xls

输出文件列名                                        数据来源与含义
ASR                                             直接来自输入文件rawASR.xlsx。即用户传入的原始客服录音转写文本 。  
refined_question                                来自第一轮大模型提炼。大模型从 ASR 中总结出的用户核心诉求，也是用于去知识库里检索的 query 。  
faq_question                                    来自输入文件FAQ.xlsx。如果相似度最高，这里显示命中的那条标准 FAQ 的问题；如果没匹配到，这里为空 。  
similarity                                      来自代码计算结果。由 Embedding 模型计算出的 refined_question 与 faq_question 之间的余弦相似度得分 。  
final_output                                    来自大模型最终输出。如果命中了知识库，这是大模型参考了标准 FAQ 重新润色后的回答；如果没有命中，这就是大模型第一轮凭借自己知识直接生成的回答 。  
faq_answer                                      来自输入文件 FAQ.xlsx。命中的那条标准 FAQ 的原始答案 。  