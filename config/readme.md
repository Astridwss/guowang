# 虚拟环境 79服务器
conda activate vllm

# 开启网络代理
export HTTP_PROXY="http://192.168.0.83:13128"
export HTTPS_PROXY="http://192.168.0.83:13128"
export ALL_PROXY="http://192.168.0.83:13128"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
export NO_PROXY="localhost,127.0.0.1,::1,apiserver.cluster.local,.cluster.local,.svc,.svc.cluster.local,kubernetes,kubernetes.default,kubernetes.default.svc,192.168.0.80,192.168.0.83,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12"
export no_proxy="$NO_PROXY"

# 测试网络
curl -I https://www.baidu.com

# 配置国内官方镜像源
export HF_ENDPOINT=https://hf-mirror.com


# 启动ASR
模型启动：79服务器/data/home/wangshan/guowang_LLM下 python ars_server.py
fsmn-vad 把长录音切成有声音的碎段。
merge_vad 把碎段拼成 15 秒的合理块。
paraformer-zh 听出这些块里的字符，并给每个字打上时间戳。
ct-punc 根据语意把字符切分成带标点的句子。
campplus 听出谁在说话，并利用时间戳，把人和字符最终合并在一起。

# 通用语言模型 在80服务器
Qwen/Qwen3.6-35B-A3B-GPTQ-Int8

# VL模型 79服务器，声明使用 GPU 1，并在 8002 端口启动视觉 API
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2-VL-7B-Instruct \
    --port 8002 \
    --max-model-len 4096 \
    --trust-remote-code \
    --enforce-eager

    或
    推荐

modelscope download --model qwen/Qwen2-VL-7B-Instruct --local_dir /data/home/wangshan/guowang_LLM/Qwen2-VL-7B-Instruct
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server \
    --model /data/home/wangshan/guowang_LLM/Qwen2-VL-7B-Instruct \
    --port 8002 \
    --max-model-len 4096 \
    --enforce-eager

# embedding模型
CUDA_VISIBLE_DEVICES=2 python -m vllm.entrypoints.openai.api_server \
    --model BAAI/bge-large-zh-v1.5 \
    --port 8003 \
    --trust-remote-code \
    --enforce-eager

    或

modelscope download --model BAAI/bge-large-zh-v1.5 --local_dir ./bge-large-zh-v1.5
CUDA_VISIBLE_DEVICES=2 python -m vllm.entrypoints.openai.api_server \
    --model /data/home/wangshan/guowang_LLM/bge-large-zh-v1.5 \
    --port 8003 \
    --trust-remote-code \
    --enforce-eager




# 79服务器启动 vl 模型
临时设置国内镜像环境变量：$env:HF_ENDPOINT="https://hf-mirror.com"
下载模型：hf download deepseek-ai/deepseek-vl-7b-chat --local-dir ./deepseek-vl-7b-chat

conda activate vllm

CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
    --model /data/home/wangshan/guowang_LLM/deepseek-vl-7b-chat \
    --port 8002 \
    --max-model-len 4096 \
    --trust-remote-code \
    --enforce-eager



modelscope download --model iic/SenseVoiceSmall --local_dir ./SenseVoiceSmall
# 下载 VAD (语音端点检测) 模型
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch --local_dir ./fsmn-vad
# 下载 CAM++ (声纹识别/说话人分离) 模型
modelscope download --model iic/speech_campplus_sv_zh-cn_16k-common --local_dir ./campplus