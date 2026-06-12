import os
import json
from pipelines.pipeline_daily_qa import DailyQAPipeline
from pipelines.pipeline_build_knowledge import BuildKnowledgePipeline

def show_menu():
    print("\n" + "="*50)
    print(" 🤖 Smart QA 智能客服 AI 中台 (微服务架构版)")
    print("="*50)
    print("请选择要执行的流水线任务：")
    print("1. [造大脑] 构建知识库 (Word -> 向量库pkl + 3D洞察)")
    print("2. [用大脑] 日常话务处理 (录音 -> 结构化质检脱敏)")
    print("3. 退出系统")
    print("="*50)

def main():
    while True:
        show_menu()
        choice = input("请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            print("\n>>> 启动：流水线一 (知识库构建)")
            # 替换为您本地真实的 Word 文件路径
            test_docx = "wxr/readme/国网商旅应用_ERP操作手册_v1.1.docx" 
            if not os.path.exists(test_docx):
                print(f"❌ 找不到测试文档: {test_docx}。请准备好真实文档。")
                continue
                
            pipeline = BuildKnowledgePipeline()
            pipeline.run(
                docx_path=test_docx, 
                output_faq_excel="FAQ_Generated.xlsx",
                output_pkl="faq_features.pkl"
            )

        elif choice == '2':
            print("\n>>> 启动：流水线二 (日常话务处理)")
            if not os.path.exists("faq_features.pkl"):
                print(" 警告：当前目录下找不到 faq_features.pkl！")
                print("RAG 融合检索将降级执行 (直接使用盲提炼结果)。建议先执行任务 1 构建知识库。")
            
            # 替换为您本地真实的音频文件路径（或者本地存好转写文本直接绕过ASR测试）
            test_audio = "test_audio.wav" 
            
            pipeline = DailyQAPipeline(faq_pkl_path="faq_features.pkl")
            
            # 这里调用 run() 会一口气走完 语音提取 -> 检索 -> 融合 -> 打分 -> 脱敏
            result = pipeline.run(test_audio)
            
            print("\n" + "-"*40)
            print("🏆 最终流水线产出报表：")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print("-"*40)

        elif choice == '3':
            print("安全退出系统。Bye!")
            break
        else:
            print("无效选项，请重新输入。")

if __name__ == "__main__":
    main()