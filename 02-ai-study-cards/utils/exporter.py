"""导出：把本次生成的全部卡片拼成一份 Markdown 文件。

为什么导出成 .md？
    Markdown 是最"通用"的格式：
    - 用记事本就能打开；
    - 贴进 Notion / Obsidian / 飞书文档能保留标题和列表；
    - 想要 Word 或 PDF，用 Typora、VS Code 插件一键转换。

本文件用到的 Python 知识（答辩时指着某一行，先报名字再解释）：
    1.  from datetime import datetime      —— 只导入 datetime 里的 datetime 类
    2.  datetime.now()                     —— 取"现在"这个时间点
    3.  日期格式化 {now:%Y-%m-%d %H:%M}     —— f-string 里的格式说明符
    4.  Path 路径拼接 / 运算符重载           —— 用 "/" 拼目录和文件名
    5.  Path.mkdir(parents=True, exist_ok=True) —— 建目录且"已存在也不报错"
    6.  Path.write_text(..., encoding=...)  —— 一行写完一个文本文件
    7.  列表推导式 [x for x in ... if ...]   —— 一边筛选一边建列表
    8.  生成器表达式 + str.join             —— 不建中间列表，直接连成字符串
    9.  dict 取值 CARD_TYPES[key].label      —— 字典取值 + 属性访问
    10. X | None 联合类型 + 默认参数         —— "可以不传，默认 None"
    11. or 兜底 a or b                      —— 左边是假值就用右边
    12. 字符串 rstrip / strip / + 拼接       —— 处理结尾多余空行
    13. 隐式字符串拼接（相邻字符串自动接）    —— 长文案分行写
"""

# 【from ... import ...】从 datetime 模块里只拿 datetime 这个类
#   注意模块名和类名一样，所以 from datetime import datetime 看着有点绕
from datetime import datetime
# 【from ... import ...】从 pathlib 拿 Path 类，用它来拼路径、建目录、写文件
from pathlib import Path

# 【项目内导入】EXPORT_DIR 是 config.py 里算好的"导出目录"Path 对象
from config import EXPORT_DIR
# 【项目内导入】CARD_TYPES 是"卡片英文名 → 卡片说明书"的字典，这里要取中文名 label
from prompts import CARD_TYPES
# 【项目内导入】count_chars 统计"去掉空白后的字数"
from utils.text_split import count_chars


# 【def 函数 + 多行参数】把多份结果拼成一整段 Markdown 文本
# 【类型提示】results 没标类型（可以是任何"能 for 的集合"），其它三个都标了；
#   "now: datetime | None = None" 表示"可以传一个时间，也可以不传"
def build_bundle_markdown(results, level: str, source_text: str,
                          now: datetime | None = None) -> str:
    """把多份生成结果拼成一份完整的 Markdown 文本（也用于界面里的"复制全部"）。"""
    # 【or 兜底】now 是 None 时取当前时间
    #   为什么留这个参数？测试时可以传一个固定时间，这样输出可复现、好比对
    now = now or datetime.now()
    # 【列表推导式】只保留 ok 为 True 的结果（失败的卡片不写进导出文件）
    #   r.ok 是 dataclass 的属性；if r.ok 就是"属性为真才留下"
    ok_results = [r for r in results if r.ok]
    # 【生成器表达式 + join】"、".join(...) 用一个顿号把多段文字连成一句
    #   括号里没有方括号，是生成器表达式：一边取一边连，不建中间列表
    #   CARD_TYPES[r.key].label：先用卡片英文名查说明书，再取中文名
    #   "if r.key in CARD_TYPES" 是防御：万一 key 不在字典里，跳过而不是 KeyError
    labels = "、".join(
        CARD_TYPES[r.key].label for r in ok_results if r.key in CARD_TYPES
    )

    # 【list 列表字面量】用方括号建列表，元素之间用逗号分隔；每个元素占一行更清楚
    lines = [
        # 【f-string + 日期格式化】{now:%Y-%m-%d %H:%M}：
        #   datetime 对象支持格式说明符——%Y 四位年、%m 两位月、%d 两位日、
        #   %H 两位小时（24 小时制）、%M 两位分钟
        f"# 学习卡片 · {now:%Y-%m-%d %H:%M}",
        # 【空字符串】往列表里放一个空串，作用是"输出时多一个空行"
        "",
        # 【f-string】把难度拼进这一行
        f"- 难度：{level}",
        # 【or 兜底】labels 是空串（一张都没成功）时显示"（无）"，避免出现空的冒号
        f"- 卡片形式：{labels or '（无）'}",
        # 【函数调用嵌在 f-string 里】{} 里可以直接调用函数，这里算材料字数
        f"- 材料字数：{count_chars(source_text)} 字",
        # 【列表里的空串】再空一行，然后放一条分隔线
        "",
        # 【Markdown 分隔线】三个减号在 Markdown 里渲染成一条横线
        "---",
        "",
    ]

    # 【for 遍历列表】逐个处理"成功的结果"
    for result in ok_results:
        # 【方法链】result.markdown 是渲染好的文本；.strip() 去掉首尾多余空白，
        #   否则拼接后会多出好几行空行
        lines.append(result.markdown.strip())
        # 【append】追加空串，等于插一个空行
        lines.append("")
        # 【append】每份卡片之间用分隔线隔开
        lines.append("---")
        # 【append】再空一行，让下一个标题不贴着分隔线
        lines.append("")

    # 【str.join + rstrip + 拼接】三步连在一起：
    #   1. "\n".join(lines) 用换行把列表里的字符串连成一个长文本；
    #   2. .rstrip() 去掉结尾多余的空行和空格；
    #   3. + "\n" 再补一个换行——很多编辑器要求文件"以换行结尾"
    return "\n".join(lines).rstrip() + "\n"


# 【def 函数】把拼好的 Markdown 真正写进文件
# 【返回类型 Path | None】成功返回文件路径，一张卡都没成功就返回 None
def save_bundle(results, level: str, source_text: str,
                now: datetime | None = None) -> Path | None:
    """写文件到 exports/ 目录，文件名带时间戳；全部失败时返回 None。"""
    # 【列表推导式】同样先筛出成功的结果
    ok_results = [r for r in results if r.ok]
    # 【if 真值判断】空列表算"假"：没有任何可写的内容
    if not ok_results:
        # 【return None】用 None 表示"这次没导出"，上层据此判断要不要提示用户
        return None

    # 【or 兜底】没传时间就用当前时间；下面拼文件名要用它
    now = now or datetime.now()
    # 【Path.mkdir】创建导出目录
    #   parents=True：如果上一级目录也不存在，一并创建（像 mkdir -p）
    #   exist_ok=True：目录已经存在时不抛 FileExistsError，直接当成功
    #   为什么两个都要？第一次运行 exports/ 不存在；第二次运行已经存在，
    #   少了 exist_ok 就会直接报错，程序每次第二次导出都崩
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)   # exist_ok：目录已存在也不报错
    # 【Path 的 / 运算符】Path 对象重载了 "/"，这里不是除法，而是"拼接路径"
    # 【时间戳文件名】%Y%m%d_%H%M%S 精确到秒：连续导出两次不会互相覆盖，
    #   而且文件名按时间排序就等于按导出顺序排，找文件很方便
    path = EXPORT_DIR / f"学习卡片_{now:%Y%m%d_%H%M%S}.md"
    # 【Path.write_text】一行把字符串写进文件；返回写入的字符数（这里不用，所以没接）
    # 【encoding="utf-8"】必须显式指定：Windows 默认编码是 GBK，
    #   不写就可能把 emoji、中文写成乱码，或读的时候报 UnicodeDecodeError
    path.write_text(
        # 【函数调用】复用上面的拼接函数；这里传 ok_results 是因为已经筛过了，
        #   而函数内部还会再筛一次——重复筛不会出错，是"幂等"的
        build_bundle_markdown(ok_results, level, source_text, now),
        encoding="utf-8",
    )
    # 【return】把路径交回去，界面可以用它显示"已保存到 xxx"
    return path
