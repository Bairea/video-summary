"""任务产物目录与文件路径。与旧 TS fileStore.ts 行为一致。"""

from ..paths import resolve_task_dir, resolve_tasks_dir


def ensure_tasks_dir(output_dir: str | None = None) -> None:
    resolve_tasks_dir(output_dir).mkdir(parents=True, exist_ok=True)


def ensure_task_dir(task_id: str, output_dir: str | None = None) -> None:
    ensure_tasks_dir(output_dir)
    resolve_task_dir(task_id, output_dir).mkdir(parents=True, exist_ok=True)


def task_file(task_id: str, *parts: str):
    return resolve_task_dir(task_id).joinpath(*parts)


def remove_task_dir(task_id: str, output_dir: str | None = None) -> None:
    import shutil
    shutil.rmtree(resolve_task_dir(task_id, output_dir), ignore_errors=True)
