# 状态机管理器 (封装字典或 Redis 的读写)import time
import time
from typing import Dict, Any, Optional

class StateManager:
    """
    全局任务状态管理器 (State Repository)
    职责：隔离状态存储的底层实现。目前使用内存字典，未来可在此处替换为 Redis。
    """
    # 类的私有属性，真正的存储池，外部禁止直接访问
    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_task(cls, task_id: str) -> bool:
        """初始化任务，如果任务已在运行中则返回 False"""
        if task_id in cls._store and cls._store[task_id]["status"] in ["pending", "processing"]:
            return False
            
        cls._store[task_id] = {
            "status": "pending",
            "result_detailed_file_url": "",
            "result_opt_file_url": "",
            "log": f"[{time.strftime('%H:%M:%S')}] 请求已受理，分配任务 ID: {task_id}...\n"
        }
        return True

    @classmethod
    def set_processing(cls, task_id: str):
        """将状态更新为处理中"""
        if task_id in cls._store:
            cls._store[task_id]["status"] = "processing"

    @classmethod
    def append_log(cls, task_id: str, message: str):
        """流式追加日志"""
        if task_id in cls._store:
            cls._store[task_id]["log"] += message

    @classmethod
    def set_success(cls, task_id: str, detailed_url: str, opt_url: str):
        """任务成功闭环落库"""
        if task_id in cls._store:
            cls._store[task_id]["status"] = "success"
            cls._store[task_id]["result_detailed_file_url"] = detailed_url
            cls._store[task_id]["result_opt_file_url"] = opt_url
            cls._store[task_id]["log"] += f"[{time.strftime('%H:%M:%S')}] ✅ 任务圆满完成，文件已物理落盘。\n"

    @classmethod
    def set_failed(cls, task_id: str, error_msg: str):
        """任务失败处理"""
        if task_id in cls._store:
            cls._store[task_id]["status"] = "failed"
            cls._store[task_id]["log"] += f"[{time.strftime('%H:%M:%S')}] ❌ 发生致命错误: {error_msg}\n"

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """供 GET 接口获取任务状态"""
        return cls._store.get(task_id)