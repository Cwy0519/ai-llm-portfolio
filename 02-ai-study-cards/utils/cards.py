"""卡片数据的三个转换：解析 → 校验 → 渲染。

为什么单独一个文件？
    模型不是程序，它可能：在 JSON 外面包一层 ```json、前面加一句"好的"、
    多写一个逗号、把 items 写成字符串……这些"脏活"集中在这里处理，
    业务代码只调 extract_json() / render_markdown()，不用到处写 try/except。

这也回答了一个常见问题："为什么不直接把模型返回的文字显示出来？"
    因为直接显示没法控制格式，也没法导出成结构化的文件。
    让它返回 JSON，我们就能统一渲染、统一复制、统一导出。

本文件用到的 Python 知识（答辩时随便指一处，先报名字再解释）：
    1. 自定义异常类 class X(Exception)  —— 用自己的错误类型区分"格式不对"
    2. re.compile 预编译正则            —— 一行正则反复用，先编译更快
    3. 原始字符串 r"..."                —— 里面的反斜杠不转义
    4. 非捕获组 (?:...) / 可选 ?        —— 只参与匹配、不单独占分组号
    5. 惰性匹配 .*? / re.S 标志         —— "尽量少匹配" + 让 . 能匹配换行
    6. re.search / match.group(1)      —— 找第一处匹配并取出第 1 组内容
    7. str.find / str.rfind / 切片      —— 用下标把 { ... } 截出来
    8. try / except / pass             —— 失败不吭声，继续往下试
    9. isinstance 类型判断             —— "这个值到底是不是字典 / 列表"
    10. dict.get + or 链兜底           —— 缺字段就给默认值，不抛 KeyError
    11. str() 强转 + strip()           —— 统一成字符串再去掉空白
    12. f-string / "".join / enumerate —— 拼出可读的 Markdown
    13. 默认参数 level: str = ""       —— 不传就是空字符串，算"假"
    14. return 提前返回                —— 检查不过就 raise，过了就 return
"""

# 【import 导入模块】json.loads() 能把 JSON 文本变成 Python 的字典
import json
# 【import 导入模块】re 是正则表达式库，用来"按模式找字符串 / 替换字符串"
import re

# 【from ... import ...】从 prompts.py 里拿 CardType 这个数据类，
#   这里只用它做类型提示、取字段（.emoji / .label / .front_label）。
from prompts import CardType


# 【自定义异常类】继承内置的 Exception，就得到一个"能 raise、能 except"的异常类型。
#   为什么不直接用 ValueError？这样上层可以只捕获 CardsParseError，
#   从而区分"模型返回格式不对"和别处冒出来的 ValueError，处理更精准。
class CardsParseError(Exception):
    """模型返回的内容没法变成卡片时抛这个错。"""


# 【re.compile 预编译 + 原始字符串】r"..." 里反斜杠不转义，写正则更省心。
#   (?:json)? 是非捕获组 + 可选：可以带 "json" 也可以不带，且不占用分组号；
#   (.*?) 是惰性匹配：尽量少地吃字符，碰到第一个 ``` 就收手；它是第 1 个分组；
#   re.S（DOTALL）让 . 也能匹配换行，否则跨行的代码块根本匹配不到。
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)      # 匹配 ```json ... ```
# 【字符组 + \s】[}\]] 表示"}"或"]"（] 在字符组里要转义），\s* 吃掉中间的空格，
#   两边加括号是为了在替换时用 \1 把那个括号字符原样保留下来。
_TRAILING_COMMA = re.compile(r",\s*([}\]])")              # 匹配 "a": 1,} 里的多余逗号


# 【def 函数 + 类型提示】参数是字符串（模型原样返回的文本），返回一个字典
def extract_json(raw: str) -> dict:
    """从模型返回的文本里抠出 JSON 对象。

    模型常见三种"不听话"的返回，这里都要兼容：
        1. 规规矩矩只返回 JSON；
        2. 外面包了一层 ```json ... ``` 代码块；
        3. 前面写"好的，以下是卡片："，或者 JSON 后面又啰嗦一句。
    """
    # 【or 兜底 + strip】raw 可能是 None，用 (raw or "") 换成空串，再去掉首尾空白
    text = (raw or "").strip()
    # 【真值判断】空字符串在 Python 里算"假"，所以 not text 就是"什么都没返回"
    if not text:
        # 【raise 抛异常】主动抛出自己定义的异常，让上层 try/except 去接
        raise CardsParseError("模型返回了空内容。")

    # 情况 2：优先取代码块里的内容
    # 【re.search】在整段文本里找第一处匹配，找不到会返回 None（不报错）
    fenced = _FENCE.search(text)
    # 【if 判断对象】匹配对象在 if 里算"真"，None 算"假"
    if fenced:
        # 【group(1)】取出第 1 个括号里的内容，也就是代码块中间那段 JSON
        text = fenced.group(1).strip()

    # 情况 3：只截取第一个 { 到最后一个 } 之间的部分
    # 【str.find】从左往右找 "{"，返回它的下标；找不到返回 -1
    start = text.find("{")
    # 【str.rfind】从右往左找 "}"，也就是"最后一个"右花括号
    end = text.rfind("}")
    # 【边界判断】没找到（-1）或者顺序反了（} 在 { 前面），都算失败
    if start == -1 or end <= start:
        # 【raise 抛异常】左右边界不成立，说明这次返回里没有 JSON
        raise CardsParseError("模型返回的内容里没有找到 JSON 对象。")
    # 【切片】start:end + 1 是"左闭右开"，所以 +1 才能把 } 也切进来
    text = text[start:end + 1]

    # 【try/except】先按标准 JSON 老老实实解析一次
    try:
        # 【return 返回结果】标准 JSON 解析成功，直接返回字典
        return json.loads(text)
    # 【捕获特定异常】只接 json.JSONDecodeError；别的错误照旧往外抛，不被掩盖
    except json.JSONDecodeError:
        # 【pass 占位】故意什么都不做：不返回也不报错，继续往下尝试"修复"
        pass

    # 二次尝试：模型有时会多写一个逗号（"a": 1,}），这在严格 JSON 里是非法的
    # 【re.sub 替换 + 反向引用】把 ",}" 换成 "}"；\1 代表第 1 个分组的内容。
    #   替换成 r"\1" 而不是 ""，才能保住那个 } 或 ]。
    fixed = _TRAILING_COMMA.sub(r"\1", text)
    # 【字符串比较】只有真的替换掉了东西（内容变了）才值得再解析一次
    if fixed != text:
        # 【再次解析】这次用"去掉多余逗号"后的文本再试一次
        try:
            # 【return 返回结果】去掉尾逗号后解析成功
            return json.loads(fixed)
        # 【再次捕获】还是失败就彻底放弃这一次修复
        except json.JSONDecodeError:
            # 【pass】继续往下走，由最后那句 raise 统一报错，避免两次报错信息混乱
            pass

    # 【抛出异常】两次都没成，只能用异常告诉调用方"这条返回废了"
    raise CardsParseError("模型返回的 JSON 格式不合法（可能有缺引号、多逗号）。")


# 【def 函数 + 类型提示】输入一个字典，输出一个"结构统一"的字典
def normalize(data: dict) -> dict:
    """把解析出来的 JSON 校验收拢成统一结构。

    - 缺字段就补默认值，不因为少一个 summary 就整段失败；
    - 类型不对、一张有效卡片都没有，就报错让上层显示提示。
    """
    # 【isinstance 类型判断】先确认传进来的是字典，不是列表或字符串
    if not isinstance(data, dict):
        # 【raise 抛异常】传进来的不是字典，类型不对
        raise CardsParseError("模型返回的不是 JSON 对象。")

    # 【or 链 + str() + strip】分三步走：取字段（缺了给 None）→ 转字符串 → 去空白；
    #   结果为空再用 or 兜底成 "学习卡片"，保证标题位置一定有字。
    title = str(data.get("title") or "").strip() or "学习卡片"
    # 【同上但更短】summary 允许为空，所以最后不再兜底文字
    summary = str(data.get("summary") or "").strip()

    # 【dict.get】取 items；取不到返回 None，下面用它判断类型
    raw_items = data.get("items")
    # 【类型校验】items 必须是列表；模型有时把整段写成一个字符串，那就直接报错
    if not isinstance(raw_items, list):
        # 【raise 抛异常】items 不是列表，说明模型返回的结构错了
        raise CardsParseError("JSON 里缺少 items 列表。")

    # 【类型提示 + 空列表】先建空列表，循环里往里放"洗干净"的卡片
    items: list[dict] = []
    # 【for 遍历】逐个检查模型给的每一张卡
    for item in raw_items:
        # 【isinstance + continue】不是字典的项直接跳过，避免后面 .get 报错
        if not isinstance(item, dict):
            # 【continue 跳过】不是字典的项直接跳过，不参与后续处理
            continue
        # 【三连取值】front / back / tip 都走同一套"取值 → 转字符串 → 去空白"流程
        front = str(item.get("front") or "").strip()
        # 【变量赋值】答案字段同样清洗：取值 → 转字符串 → 去空白
        back = str(item.get("back") or "").strip()
        # 【变量赋值】提示字段允许为空字符串
        tip = str(item.get("tip") or "").strip()
        # 【and 双条件】只有正反面都有内容，才算一张有效卡
        if front and back:          # 缺正反面的卡直接丢掉，不显示半张卡
            # 【append + 新建字典】用干净的三个字段组成新字典，丢掉模型多写的字段
            items.append({"front": front, "back": back, "tip": tip})

    # 【真值判断】一张有效卡都没有，就没必要再往下渲染了
    if not items:
        # 【raise 抛异常】一张有效卡都没有，整份结果不可用
        raise CardsParseError("items 里没有有效的卡片（front / back 不能为空）。")

    # 【返回新字典】固定三个键，上层就可以放心地 data["items"]、data["title"]
    return {"title": title, "summary": summary, "items": items}


# 【def 函数 + list[dict] 参数】接收"多段结果"组成的列表，返回合并后的一份
def merge_parts(parts: list[dict]) -> dict:
    """把长材料分段生成的多份结果合并成一份。

    标题和总结取第一段的，卡片全部拼起来；渲染时编号会从 1 连续往下排。
    """
    # 【初始化容器】先准备空列表、空标题、空总结，循环里逐步填充
    items: list[dict] = []
    # 【初始化】标题先占位，循环里取到第一个非空标题再赋值
    title = ""
    # 【初始化】总结先占位，同样取第一段非空的
    summary = ""
    # 【for 遍历】按顺序处理每一段结果
    for part in parts:
        # 【or 短路】title 为空时才去取 part 的 title；已经有值就不再覆盖，
        #   这样"标题取第一段非空的"就自然实现了。
        title = title or part.get("title", "")
        # 【or 短路】已经有总结就不再覆盖，保证「取第一段」
        summary = summary or part.get("summary", "")
        # 【list.extend】把这一段的所有卡片逐个追加到 items 末尾（append 会变成嵌套列表）
        items.extend(part.get("items", []))
    # 【真值判断】一段都没解析出卡片，说明整次生成都失败了
    if not items:
        # 【raise 抛异常】合并后仍然没有卡片，说明整次生成都失败了
        raise CardsParseError("没有解析出任何卡片。")
    # 【or 兜底 + 返回】标题再兜一次底，保证界面上有标题可显示
    return {"title": title or "学习卡片", "summary": summary, "items": items}


# 【def 函数 + 默认参数】level 可以不传，默认 ""（空字符串算"假"，表示没难度）
def render_markdown(card: CardType, data: dict, level: str = "") -> str:
    """把结构化数据渲染成好看的 Markdown。

    为什么用 Markdown 而不是自己拼 HTML？
        因为 Markdown 纯文本就能读、能复制、能存成 .md、能直接贴进笔记软件，
        而且界面里用的也是 Markdown 渲染，一份数据两处复用。
    """
    # 【f-string + 属性访问】card.emoji / card.label 拼成三级标题
    header = f"### {card.emoji} {card.label}"
    # 【if 真值判断】只有传了难度，才在标题后面追加 " · 进阶"
    if level:
        # 【+= 累加】等价于 header = header + f" · {level}"
        header += f" · {level}"
    # 【if + dict 取值】有 summary 才加一行 Markdown 引用（> 开头就是引用块）
    if data.get("summary"):
        # 【+= 累加】只有存在总结时，才在标题后追加一行引用块
        header += f"\n\n> {data['summary']}"

    # 【列表初始化】blocks 收集"每一张卡片各自的一段文字"，最后再拼起来
    blocks = [header]
    # 【enumerate(列表, 1)】同时拿下标 i 和元素 item，并且编号从 1 开始
    for i, item in enumerate(data.get("items", []), 1):
        # 【多行列表字面量】每行一个元素，最后一个元素后面的逗号可以保留
        lines = [
            # 【f-string + 下标取值】item['front'] 直接用键取值，这里确定有值
            f"**{i}. {card.front_label}：** {item['front']}",
            # 【空字符串占位】渲染出来就是"空一行"，让正反面不挤在一起
            "",
            f"**{card.back_label}：** {item['back']}",
        ]
        # 【dict.get 判断】tip 有内容才加提示行；空字符串算"假"，会被跳过
        if item.get("tip"):
            # 【append】先空一行，再写提示，避免和上面的答案粘在一起
            lines.append("")
            # 【append】把提示行追加到当前这张卡片的 lines 里
            lines.append(f"*💡 提示：{item['tip']}*")
        # 【join + append】把这一张卡的几行用换行拼成一段，再放进 blocks
        blocks.append("\n".join(lines))

    # 【join 拼接】卡片之间用 "---" 分隔线隔开；末尾补 \n 让 Markdown 更规整
    return "\n\n---\n\n".join(blocks) + "\n"
