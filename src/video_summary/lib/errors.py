"""跨层共享的错误类型。"""

class JobCancelled(Exception):
    """任务被取消（用户取消或队列取消）。

    定义在 lib 层，供 lib/retry 引发、services/job_queue 捕获；
    job_queue 重新导出该名字以保持既有导入路径可用。
    """
