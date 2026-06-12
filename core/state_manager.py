# 文件路径：core/state_manager.py
import time
from typing import Dict, Any, Optional

class StateManager:
    """
    全局任务状态管理器 (State Repository)
    职责：提供通用的状态存取。彻底解耦业务，支持任意并发任务（RAG/数据增强/聚类等）。
    """
    _store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_task(cls, task_id: str) -> bool:
        """初始化任务"""
        if task_id in cls._store and cls._store[task_id]["status"] in ["pending", "processing"]:
            return False
            
        # 去掉写死的 RAG 字段，只保留最基础的状态和日志
        cls._store[task_id] = {
            "status": "pending",
            "log": f"[{time.strftime('%H:%M:%S')}] 请求已受理，分配任务 ID: {task_id}...\n"
        }
        return True

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务当前状态"""
        return cls._store.get(task_id)

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
    def set_success(cls, task_id: str, **kwargs):
        """
        任务成功闭环落库（高度通用化）
        使用 **kwargs 接收任意数量的产物字段。
        """
        if task_id in cls._store:
            cls._store[task_id]["status"] = "success"
            # 动态将传入的所有键值对（比如 result_file_url）合并到字典中
            cls._store[task_id].update(kwargs)
            cls._store[task_id]["log"] += f"[{time.strftime('%H:%M:%S')}] ✅ 任务完成，产物已物理落盘。\n"

    @classmethod
    def set_failed(cls, task_id: str, error_msg: str):
        """任务失败处理（通用异常捕获）"""
        if task_id in cls._store:
            cls._store[task_id]["status"] = "failed"
            cls._store[task_id]["log"] += f"[{time.strftime('%H:%M:%S')}] ❌ 任务执行失败: {error_msg}\n"
            
    @classmethod
    def update_task(cls, task_id: str, update_data: dict):
        """通用更新接口：允许直接传入字典覆盖/更新现有状态"""
        if task_id in cls._store:
            cls._store[task_id].update(update_data)