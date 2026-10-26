"""程序入口：只做"组装"和"启动"两件事。

启动流程：
    1. 读配置（.env）
    2. 检查配置，有问题就打印一句提示（但不阻止启动，界面上还会再提示一次）
    3. 搭界面
    4. 启动服务

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1.  import / from ... import ...   —— 导入模块、导入别的文件里的函数
    2.  def 函数 / 类型提示 -> None     —— 把一段逻辑包起来复用
    3.  if / else、真值判断             —— 条件分支
    4.  f-string                       —— 字符串里嵌变量
    5.  hasattr() / 属性访问            —— 判断对象有没有某个属性
    6.  try / except OSError           —— 只接住"端口被占用"这一类异常
    7.  函数调用 + 关键字参数            —— 用"参数名=值"传参，顺序无所谓
    8.  None                           —— "没有值"的空值
    9.  if __name__ == "__main__"      —— 程序入口
"""

# 【import 导入模块】导入 Python 自带的 sys 模块
#   后面用 sys.stdout 拿到"标准输出"（终端），再改它的编码
import sys

# 【import ... as 起别名】导入 gradio 界面库，起短名 gr，后面写 gr.themes 更省事
import gradio as gr

# 【from ... import ...】从 config.py 里拿两个函数：检查配置、读取配置
#   能这样 import，是因为 config.py 和本文件在同一个目录（Python 会先找当前目录）
from config import config_problem, load_settings
# 【from ... import ...】从 ui/layout.py 里拿样式字符串 CSS 和建界面的函数 build_ui
from ui.layout import CSS, build_ui

# 固定端口，方便记忆；被占用时自动换一个
# 【模块级常量 + 大写命名】PORT 写在函数外面，整个文件都能用
#   全大写是"这是常量、别随便改"的约定，Python 语法本身并不强制
PORT = 7861


# 【def 定义函数 + 类型提示】定义程序主函数；"-> None" 表示它不返回任何东西
#   把步骤都放进函数，是为了最后 if __name__ 那一句能干净地调用
def main() -> None:
    # 【if + hasattr 判断属性】hasattr(对象, "属性名") 判断对象有没有这个属性
    #   sys.stdout 是终端输出流；老版本 Python 可能没有 reconfigure，所以先判断再调
    if hasattr(sys.stdout, "reconfigure"):
        # 【方法调用 + 关键字参数】把终端输出编码强制成 UTF-8，中文日志才不会乱码
        #   errors="replace" 表示遇到编不了的字符不报错，换成一个替代符号
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 【函数调用 + 赋值】读取 .env 里的配置，返回一个 Settings 对象（里面有 Key、地址、模型）
    settings = load_settings()

    # 【函数调用】检查配置：没问题返回 None，有问题返回一句中文提示
    #   注意它只是"检查"，不会抛异常，所以这里不用 try
    problem = config_problem(settings)
    # 【if 真值判断】字符串有内容算"真"，None 算"假"
    if problem:
        # 【print + 字符串拼接】"+" 把前缀和提示拼成一句话打印到终端
        print("[提示] " + problem)
    # 【else 分支】没有问题时，把关键配置打印出来，方便确认"到底连的是哪个模型"
    else:
        # 【属性访问 + f-string】settings.model 取对象的属性，再嵌进字符串
        print(f"[配置] 模型 = {settings.model}")
        # 【属性访问 + f-string】接口地址，出问题时可以对照它检查 .env
        print(f"[配置] 地址 = {settings.base_url}")
        # 【属性访问 + f-string】单段最多多少字，超过就会被切段
        print(f"[配置] 单段上限 = {settings.max_chars} 字")
        # 【属性访问 + f-string】是否让模型按 JSON 格式返回
        print(f"[配置] JSON 模式 = {settings.json_mode}")

    # 【函数调用】把配置传给界面层，搭出一个 gr.Blocks 界面对象
    #   本文件自己不摆组件，所有组件的细节都在 ui/layout.py 的 build_ui() 里
    demo = build_ui(settings)
    # 【方法调用】开启请求队列：支持并发请求，也支持 on_generate 那种多次 yield 的进度刷新
    #   不开队列的话，Gradio 无法把"生成中 → 完成"一步步推给浏览器
    demo.queue()          # 开启队列：支持并发请求和生成器式的进度刷新

    # 【try/except 捕获指定异常】把启动代码包起来，只接住 OSError（端口被占用会抛它）
    try:
        # 【函数调用 + 关键字参数】启动网页服务；参数靠"名字="指定，顺序可以打乱
        demo.launch(
            # 【关键字参数】只监听本机地址，同一个局域网里的别人访问不到
            server_name="127.0.0.1",
            # 【关键字参数】用上面定好的 7861 端口，浏览器地址就是 127.0.0.1:7861
            server_port=PORT,
            inbrowser=True,       # 自动打开浏览器
            show_error=True,      # 终端里打印完整报错，方便排查
            # 【关键字参数 + 创建对象】选"柔和"主题；gr.themes.Soft() 是现场创建一个主题对象
            theme=gr.themes.Soft(),
            # 【关键字参数】把 ui/layout.py 里那段自定义 CSS 传进去，放开页面宽度
            css=CSS,
        )
    # 【except 指定异常类型】只接 OSError；别的异常（比如写错参数名）仍会正常抛出
    except OSError:
        # 【f-string】把被占用的端口号打进提示里，告诉用户"我知道发生了什么"
        print(f"[提示] 端口 {PORT} 被占用，改用随机端口启动。")
        # 【函数调用 + 关键字参数】第二次启动：故意不传 server_port，让 Gradio 自己找空闲端口
        #   这是"降级启动"：功能一样，只是地址栏的端口号变了
        demo.launch(
            server_name="127.0.0.1",
            inbrowser=True,
            show_error=True,
            theme=gr.themes.Soft(),
            css=CSS,
        )


# 【if __name__ == "__main__"】只有"直接运行这个文件"时才执行 main()
#   被别的文件 import 时（比如测试脚本），不会莫名其妙地启动一个网页
if __name__ == "__main__":
    # 【函数调用】执行主函数，程序从这里真正跑起来
    main()
