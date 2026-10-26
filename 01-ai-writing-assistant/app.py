"""应用启动入口：AI 智能写作助手。

职责范围：
- 读取 config.Settings（模型、端口、是否自动打开浏览器等）；
- 调用 ui.build_ui() 构建界面并 demo.queue()；
- 打印启动信息并 launch()。

使用 ``python app.py`` 启动；import 本模块不会启动任何服务。
"""

from __future__ import annotations

import socket

import config
from ui import TITLE, build_ui

_BANNER_WIDTH = 64


def _bind_host(host: str) -> str:
    """把监听地址转换为可用于 bind 检查的主机名。"""
    return host or "0.0.0.0"


def _is_port_free(host: str, port: int) -> bool:
    """探测端口是否空闲（只探测，不占用；探测完立即释放）。"""
    bind_host = _bind_host(host)
    family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            if family == socket.AF_INET:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, port))
    except OSError:
        return False
    return True


def _public_url(host: str, port: int) -> str:
    """给出一个能在浏览器里打开的地址（0.0.0.0 时用 127.0.0.1）。"""
    display_host = "127.0.0.1" if host in {"", "0.0.0.0", "::", "::0"} else host
    return f"http://{display_host}:{port}/"


def _print_startup(settings: config.Settings) -> None:
    """打印启动信息：模型、Key 状态、访问地址。"""
    print("=" * _BANNER_WIDTH)
    print(f"  {TITLE}  ·  启动中")
    print("=" * _BANNER_WIDTH)
    print(f"  模型    ：{settings.model}")
    print(f"  接口地址：{settings.base_url}")
    print(f"  API Key ：{settings.masked_key()}")
    print(f"  访问地址：{_public_url(settings.app_host, settings.app_port)}")
    problems = settings.validate()
    if problems:
        print("-" * _BANNER_WIDTH)
        print("  ⚠️ 配置提示（页面可打开，但需要修正后才能生成）：")
        for problem in problems:
            print(f"    - {problem}")
    print("-" * _BANNER_WIDTH)
    print("  按 Ctrl+C 停止服务")
    print("=" * _BANNER_WIDTH, flush=True)


def _print_port_busy(settings: config.Settings, error: object = "") -> None:
    """端口被占用时的中文提示。"""
    print("=" * _BANNER_WIDTH)
    print("  ❌ 启动失败：端口被占用")
    print("-" * _BANNER_WIDTH)
    print(f"  端口 {settings.app_port} 已被其他程序占用，无法启动服务。")
    print("  请修改项目根目录 .env 中的 APP_PORT（例如改为 7862），或在命令行设置：")
    print(f'    $env:APP_PORT="7862"')
    print("  然后重新运行 .venv\\Scripts\\python.exe app.py。")
    if error:
        print(f"  原始错误：{error}")
    print("=" * _BANNER_WIDTH, flush=True)


def main() -> int:
    """启动 Gradio 服务。返回进程退出码。"""
    settings = config.get_settings()
    _print_startup(settings)

    if not _is_port_free(settings.app_host, settings.app_port):
        _print_port_busy(settings)
        return 1

    demo = build_ui()
    demo.queue(default_concurrency_limit=4, max_size=64)

    print("  正在启动服务，请稍候……", flush=True)
    try:
        demo.launch(
            server_name=settings.app_host,
            server_port=settings.app_port,
            inbrowser=settings.app_inbrowser,
            show_error=True,
        )
    except OSError as exc:
        # 端口在探测后又被抢占、或地址无法绑定时也给出同样的中文提示
        _print_port_busy(settings, exc)
        return 1
    except KeyboardInterrupt:
        print("\n  已停止服务。")
        return 0

    print("\n  服务已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
