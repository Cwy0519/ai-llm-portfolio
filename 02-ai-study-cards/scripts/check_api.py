"""连通性自检：确认 .env 配置正确、模型能正常返回 JSON。

第一次配置完 Key 之后先跑这个（只需要几秒钟，几乎不花钱）：

    .venv\\Scripts\\python.exe scripts\\check_api.py

它能一次性验证四件事：
    - .env 能不能被读到
    - 接口地址和模型名对不对
    - Key 有没有效
    - 模型会不会按 JSON 返回（这是整个项目最基础的假设）

本文件用到的 Python 知识（答辩时指着某一行，先报名字再解释）：
    1.  sys.path / 模块搜索路径            —— 让 Python 找得到项目里的模块
    2.  __file__ + Path.parent             —— 定位本文件、再往上一级两级
    3.  str(Path)                          —— Path 对象要转成字符串才能塞进 sys.path
    4.  sys.stdout.reconfigure(...)        —— 改控制台输出编码，避免中文乱码
    5.  hasattr(对象, "属性名")             —— 先问"有没有"，再决定要不要用
    6.  # noqa: E402                       —— 告诉代码检查工具"这里是有意为之"
    7.  f-string                           —— 把变量塞进提示文字
    8.  try / except 自定义异常             —— 接住 LLMError / CardsParseError
    9.  字符串切片 text[:200]               —— 只取前 200 个字符
    10. 函数返回退出码 0 / 1                —— 告诉命令行"成功还是失败"
    11. if __name__ == "__main__"          —— 只在直接运行时才执行
    12. raise SystemExit(main())           —— 把返回值当作进程退出码
    13. 单引号字符串里放双引号              —— 省掉一堆转义反斜杠
"""

# 【import 标准库】sys 用来改"模块搜索路径"和"标准输出编码"
import sys
# 【from ... import ...】Path 用来算"这个文件在哪"，比手拼字符串更可靠
from pathlib import Path

# 【Path + __file__】__file__ 是当前脚本的路径；.resolve() 变成绝对路径；
#   .parent 取上一级目录，连续两次 .parent 就是"scripts 的上一级"= 项目根目录
ROOT = Path(__file__).resolve().parent.parent
# 【sys.path.insert】sys.path 是"import 时去哪儿找模块"的目录列表，
#   下标 0 是最先找的位置。直接运行 scripts/check_api.py 时，
#   Python 只会把 scripts/ 放进 sys.path，import config 会找不到，
#   所以手动把项目根目录插到最前面
# 【str()】sys.path 里必须是字符串，而 ROOT 是 Path 对象，所以要转一下
sys.path.insert(0, str(ROOT))

# Windows 控制台默认不是 UTF-8，中文和表情会乱码
# 【hasattr 判断属性】不同 Python/环境里 sys.stdout 未必有 reconfigure 方法，
#   先 hasattr 问一句，有才调用，避免 AttributeError
if hasattr(sys.stdout, "reconfigure"):
    # 【方法调用 + 关键字参数】把标准输出改成 UTF-8；
    #   errors="replace" 表示遇到编不出来的字符就用替代符号，而不是直接抛异常
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 【import 位置说明】下面三行 import 故意写在 sys.path 修改之后——
#   因为不先改路径就 import 不到项目模块。
# 【noqa: E402】flake8 规则 E402 是"模块级 import 不在文件最顶部"，
#   这里是有意违反，noqa 就是告诉检查工具"别报这一条"
from config import config_problem, load_settings                          # noqa: E402
# 【项目内导入】LLMClient 负责发请求，LLMError 是它抛出的"人话版"异常
from services.llm_client import LLMClient, LLMError                       # noqa: E402
# 【项目内导入】解析 JSON 的函数和它专用的异常类
from utils.cards import CardsParseError, extract_json                     # noqa: E402


# 【def 函数 + 返回类型】main() 返回一个整数：0 表示成功，1 表示失败
#   为什么返回整数而不是直接 print？这样命令行、CI 都能根据退出码判断结果
def main() -> int:
    # 【函数调用】读 .env，得到配置对象
    settings = load_settings()

    # 【函数调用】检查配置是否可用：没问题返回 None，有问题返回一句人话
    problem = config_problem(settings)
    # 【if 真值判断】problem 非空（非 None）说明配置有问题
    if problem:
        # 【字符串 + 拼接】把标签和说明接起来打印，比 f-string 更直白
        print("[配置有问题] " + problem)
        # 【return 1】立刻结束函数并返回 1：后面的代码不再执行
        return 1

    # 【f-string】打印实际用的模型名，确认 .env 真的被读到了
    print(f"[配置] 模型 = {settings.model}")
    # 【f-string】打印实际用的接口地址
    print(f"[配置] 地址 = {settings.base_url}")
    # 【普通字符串】提示用户"正在请求"，因为这一步要等几秒
    print("[请求] 正在调用模型，请稍等…")

    # 【list + dict】构造两条消息：system 定身份，user 提要求
    messages = [
        # 【dict 字面量】role=system 是"设定规则"，content 是规则正文
        {"role": "system", "content": "你是一个测试助手，只输出 JSON。"},
        # 【单引号字符串 + 内部双引号】外层用单引号，里面就能直接写 JSON 的双引号，
        #   不用写成 \" 转义，读起来清爽很多
        {"role": "user", "content": '请只输出这个 JSON：{"ok": true, "msg": "你好"}'},
    ]

    # 【try/except 自定义异常】只接住网络层翻译好的 LLMError
    try:
        # 【创建对象 + 立刻调方法】LLMClient(settings) 建客户端，.complete(messages) 发请求
        raw = LLMClient(settings).complete(messages)
    # 【as e 绑定异常对象】e 里带着错误信息
    except LLMError as e:
        # 【str(e)】把异常对象转成它的文字说明
        print("[失败] " + str(e))
        # 【return 1】失败退出码
        return 1

    # 【切片】raw.strip() 先去首尾空白，[:200] 只取前 200 个字符，
    #   防止模型啰嗦一大段把终端刷爆
    print("[返回] " + raw.strip()[:200])

    # 【第二层 try】能连上不代表返回的是合法 JSON，所以再单独包一层
    try:
        # 【函数调用】从文本里抠 JSON；失败会抛 CardsParseError
        data = extract_json(raw)
    # 【except 具体异常】只接"解析失败"，其它异常不吞
    except CardsParseError as e:
        # 【字符串 + 拼接】先把标签和异常说明接成一段，再交给 print 打印
        print("[警告] 能连上模型，但返回的不是 JSON：" + str(e))
        # 【缩进续行】这行前面用 7 个空格对齐上一行的正文，纯属排版让提示更好看
        print("       可以把 .env 里的 JSON_MODE 改成 false 再试一次。")
        # 【return 1】仍然是失败：项目依赖"模型返回 JSON"这个前提
        return 1

    # 【f-string + dict】{data} 会调用字典的 str()，直接打印出解析后的内容
    print(f"[成功] API 配置可用，模型能正常返回 JSON：{data}")
    # 【return 0】约定：0 表示一切正常
    return 0


# 【if __name__ == "__main__"】只有"直接运行这个文件"时 __name__ 才等于 "__main__"；
#   如果它被别的文件 import，这段就不会执行（不会莫名跑一遍自检）
if __name__ == "__main__":
    # 【raise SystemExit】把 main() 的返回值当作"进程退出码"抛出去：
    #   0 → 成功；1 → 失败。命令行 echo $LASTEXITCODE（PowerShell 里）就能看到
    raise SystemExit(main())
