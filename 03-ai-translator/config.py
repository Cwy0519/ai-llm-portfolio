"""配置模块：只做一件事——把 .env 文件里的值读成 Python 变量。

为什么单独一个文件？
    配置是"会变的东西"（换模型、换 key、调超时）。
    把它抽出来，其它文件就不用关心配置从哪来，改配置也不用翻业务代码。
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

# BASE_DIR 是当前文件所在的目录，也就是项目根目录。
# 用绝对路径加载 .env，避免"换个目录启动就读不到配置"这种坑。
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    """一次运行需要的全部配置，集中放在一个对象里往下传。"""

    api_key: str          # 大模型平台的密钥，绝不能写死在代码里
    base_url: str         # 接口地址（不同平台不一样）
    model: str            # 模型名
    timeout: int          # 单次请求超时（秒）
    max_chars: int        # 单个文本段的最大字数，超过就切分
    temperature: float    # 随机性：0 最稳定，1 最发散
    max_retries: int      # 网络失败时重试几次


def load_settings() -> Settings:
    """从环境变量读取配置；读不到就用默认值（默认值是 DeepSeek 的接口）。"""
    return Settings(
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip(),
        model=os.getenv("LLM_MODEL", "deepseek-chat").strip(),
        timeout=_to_int(os.getenv("LLM_TIMEOUT"), 60),
        max_chars=_to_int(os.getenv("MAX_CHARS"), 1200),
        temperature=_to_float(os.getenv("TEMPERATURE"), 0.3),
        max_retries=_to_int(os.getenv("MAX_RETRIES"), 2),
    )


def _to_int(value: str | None, default: int) -> int:
    """把字符串转成整数；转不动就用默认值，不让程序因为一个配置项崩掉。"""
    try:
        return int(value) if value else default
    except ValueError:
        return default


def _to_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value else default
    except ValueError:
        return default


# 这些明显是占位符，当作"没填"处理
_PLACEHOLDERS = {"", "你的key", "sk-xxx", "your-key", "在这里填你的key", "xxx"}


def config_problem(s: Settings) -> str | None:
    """检查配置是否可用。返回一句人话的错误提示；没问题返回 None。

    这个函数让"没配 key"变成一个友好的提示，而不是一串红色报错。
    """
    if s.api_key in _PLACEHOLDERS:
        return (
            "还没有配置 API Key。请把 .env.example 复制一份改名为 .env，"
            "在 LLM_API_KEY 后面填入你的密钥，然后重新启动程序。"
        )
    if not s.base_url.startswith("http"):
        return f"LLM_BASE_URL 看起来不对（{s.base_url}），它应该以 http 开头。"
    return None
