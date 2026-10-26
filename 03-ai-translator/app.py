"""程序入口：只做"组装"和"启动"两件事。

启动流程：
    1. 读配置（.env）
    2. 检查配置，有问题就打印一句提示（但不阻止启动，界面上还会再提示一次）
    3. 搭界面
    4. 启动服务
"""

import sys

import gradio as gr

from config import config_problem, load_settings
from ui.layout import CSS, build_ui

# 固定端口，方便记忆；被占用时自动换一个
PORT = 7860


def main() -> None:
    # Windows 控制台默认编码可能不是 UTF-8，中文日志会乱码，这里强制一下
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    settings = load_settings()

    problem = config_problem(settings)
    if problem:
        print("[提示] " + problem)
    else:
        print(f"[配置] 模型 = {settings.model}")
        print(f"[配置] 地址 = {settings.base_url}")
        print(f"[配置] 分段上限 = {settings.max_chars} 字")

    demo = build_ui(settings)
    demo.queue()          # 开启队列：支持流式输出和并发请求

    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=PORT,
            inbrowser=True,       # 自动打开浏览器
            show_error=True,      # 终端里打印完整报错，方便排查
            theme=gr.themes.Soft(),
            css=CSS,
        )
    except OSError:
        print(f"[提示] 端口 {PORT} 被占用，改用随机端口启动。")
        demo.launch(
            server_name="127.0.0.1",
            inbrowser=True,
            show_error=True,
            theme=gr.themes.Soft(),
            css=CSS,
        )


if __name__ == "__main__":
    main()
