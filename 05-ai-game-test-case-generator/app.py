# -*- coding: utf-8 -*-
"""启动入口：读配置 → 构建界面 → 启动服务。

注意：`import app` 不会启动服务，方便测试与二次开发。
"""
from __future__ import annotations

import socket

from config import ConfigError, load_settings

DEFAULT_PORT = 7862


def port_in_use(host: str, port: int) -> bool:
    target = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((target, port)) == 0


def main() -> None:
    settings = None
    try:
        settings = load_settings()
        settings.check_ready()
        print(f"[配置] 已就绪：{settings.summary()}")
    except ConfigError as exc:
        print(f"[配置] 警告：{exc}")
        print("[配置] 界面仍会打开，但点击「生成用例」会提示配置错误。补好 .env 后重启即可。")

    from ui.layout import build_ui

    demo = build_ui(settings)
    host = settings.app_host if settings else "127.0.0.1"
    port = settings.app_port if settings else DEFAULT_PORT

    if port_in_use(host, port):
        print(f"[端口] {port} 已被占用，换一个端口：修改 .env 里的 APP_PORT")
        port += 1

    print(f"[启动] 浏览器打开 http://{host}:{port}/")
    import gradio as gr

    demo.launch(
        server_name=host,
        server_port=port,
        inbrowser=True,
        show_error=True,
        theme=gr.themes.Soft(),  # Gradio 6 起 theme 从 Blocks 移到 launch
    )


if __name__ == "__main__":
    main()

