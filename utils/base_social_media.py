from pathlib import Path
from typing import List

from base.config import config

SOCIAL_MEDIA_XIAOHONGSHU = "xiaohongshu"


def get_supported_social_media() -> List[str]:
    return [SOCIAL_MEDIA_XIAOHONGSHU]


def get_cli_action() -> List[str]:
    return ["upload", "login", "watch"]


async def set_init_script(context):
    stealth_js_path = Path(config.get("paths.base_dir")) / "utils/stealth.min.js"
    await context.add_init_script(path=stealth_js_path)
    return context
