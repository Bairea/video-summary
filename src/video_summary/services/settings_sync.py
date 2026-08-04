"""同步版本的设置读取，供 asyncio.to_thread 包裹后使用。"""

from ..repositories.settings_repo import load_settings

load_settings_sync = load_settings
