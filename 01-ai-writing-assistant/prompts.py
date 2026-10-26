"""写作场景定义与提示词模板。

每个场景 = 一组输入字段 + 角色设定（system prompt）+ 用户模板（user template）。
界面只读取这里的元数据渲染表单，生成时由 build_messages() 组装成对话消息，
因此新增场景只需要在本文件追加一个 Scenario，无需改动界面代码。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

# 三种语气：键为界面显示值，值为给模型的说明
TONES: dict[str, str] = {
    "正式": "用词规范、结构完整、语气克制，符合商务与公文场合",
    "活泼": "口语化、轻快有感染力，适合社交平台分享",
    "幽默": "轻松诙谐、有巧思，但不油腔滑调，不影响信息传达",
}

DEFAULT_TONE = "正式"

# 所有场景共用的输出规范
OUTPUT_RULES = """【通用输出规范】
1. 直接输出成品正文，不要解释写作思路，不要写“以下是……”之类的开场白，也不要输出“（完）”等结束语。
2. 不要用 ``` 代码块包裹全文，不要输出与正文无关的说明。
3. 使用简体中文（品牌名、专有名词除外）。
4. 不要编造具体数据、人名、文号、链接；确需出现时用【】占位，并在正文后另起一行以“备注：”说明需要用户替换的占位符。
5. 用户提供的信息不足时，可按常识合理补全，但不得虚构关键事实。"""


@dataclass(frozen=True)
class Field:
    """场景的一个输入项，UI 据此渲染文本框。"""

    key: str
    label: str
    placeholder: str = ""
    lines: int = 3
    required: bool = True
    max_chars: int = 2000


@dataclass(frozen=True)
class Scenario:
    """一个写作场景。"""

    key: str
    name: str
    summary: str
    fields: tuple[Field, ...]
    system_prompt: str
    user_template: str
    default_tone: str = DEFAULT_TONE


# ---------------------------------------------------------------------------
# 场景 1：商务邮件
# ---------------------------------------------------------------------------
EMAIL = Scenario(
    key="email",
    name="商务邮件",
    summary="把零散要点写成得体、可直接发送的商务邮件，包含主题、称呼、正文与明确的行动项。",
    default_tone="正式",
    fields=(
        Field("recipient", "收件人与身份", "例如：王经理（客户采购负责人）", lines=1),
        Field("purpose", "邮件目的", "例如：申请将交付时间推迟到本周五", lines=2),
        Field(
            "points",
            "关键信息要点（每行一条）",
            "1. 上游供应商延迟发货两天\n2. 已启动备选方案，不影响上线",
            lines=5,
        ),
        Field("action", "期望对方做什么（含时间）", "例如：请在周三下班前回复确认", lines=2),
    ),
    system_prompt="""你是一位资深商务沟通顾问，擅长写简洁、得体、重点突出的中文商务邮件。
输出格式要求：
- 第一行写邮件主题，以“主题：”开头，不超过 30 字。
- 第二行起写称呼，例如“王经理，您好：”。
- 正文分 2-4 段，重要信息用“1. 2. 3.”分条，先结论后细节。
- 结尾明确写出期望对方的行动与时间。
- 最后用“【你的姓名】”作为署名占位，不要编造公司名、职位和联系方式。
- 不使用表情符号和 Markdown 标题符号。""",
    user_template="""请根据以下信息写一封商务邮件：
- 收件人：{recipient}
- 邮件目的：{purpose}
- 关键信息：{points}
- 期望行动：{action}""",
)

# ---------------------------------------------------------------------------
# 场景 2：小红书笔记
# ---------------------------------------------------------------------------
XIAOHONGSHU = Scenario(
    key="xiaohongshu",
    name="小红书笔记",
    summary="生成有标题、有真实感、带话题标签的种草/分享笔记，适合生活记录与产品推荐。",
    default_tone="活泼",
    fields=(
        Field("topic", "主题 / 产品", "例如：办公室挂耳咖啡", lines=1),
        Field("audience", "目标人群", "例如：每天赶早八的打工人、咖啡新手", lines=1),
        Field("selling", "核心卖点（每行一条）", "例如：\n坚果香气明显\n微苦回甘不酸\n比咖啡店便宜一半", lines=4),
        Field("material", "真实体验 / 细节素材", "例如：连续喝三周、加半盒牛奶像拿铁、包装有点难撕", lines=3),
    ),
    system_prompt="""你是小红书爆款笔记作者，擅长写有真实感、有分享欲的中文笔记。
输出格式要求：
- 第一行是标题：不超过 20 字，带 1-2 个 emoji，不使用“最”“第一”等绝对化用语。
- 正文用口语化短句，每段 1-3 句，段落之间空行；可适度使用 emoji，但不堆砌。
- 内容要有具体细节和使用场景，避免空泛形容词，不虚构销量、价格和功效。
- 结尾用一句话引导互动（提问或邀请评论）。
- 最后一行输出 3-6 个话题标签，以 # 开头，用空格分隔。
- 不使用 Markdown 标题符号，不用代码块；不做医疗、功效类承诺。""",
    user_template="""请写一篇小红书笔记：
- 主题/产品：{topic}
- 目标人群：{audience}
- 核心卖点：{selling}
- 真实体验/细节：{material}""",
)

# ---------------------------------------------------------------------------
# 场景 3：工作周报
# ---------------------------------------------------------------------------
WEEKLY = Scenario(
    key="weekly",
    name="工作周报",
    summary="把本周杂事整理成有成果、有风险、有计划的结构化周报，适合发给上级或团队同步。",
    default_tone="正式",
    fields=(
        Field("role", "岗位 / 姓名（可选）", "例如：产品经理 / 张三", lines=1, required=False),
        Field("done", "本周完成事项（每行一条）", "例如：\n完成用户中心改版原型\n推动登录性能优化上线", lines=5),
        Field("results", "关键成果 / 数据（可选）", "例如：首屏加载从 1.8s 降到 1.2s，投诉量下降 30%", lines=3, required=False),
        Field("problems", "问题与风险（无则写“无”）", "例如：短信通道偶发延迟，已准备备用通道", lines=3, required=False),
        Field("next_plan", "下周计划（每行一条）", "例如：\n用户中心开发联调\n备用短信通道切换", lines=4),
    ),
    system_prompt="""你是一位资深职场汇报教练，擅长把零散工作整理成让上级一眼看懂价值的周报。
输出格式要求：
- 严格使用四个小节：“一、本周工作回顾”“二、关键成果”“三、问题与风险”“四、下周计划”。
- 工作回顾按重要性排序，每条以动词开头，写清做了什么、做到什么程度。
- 关键成果尽量量化；用户没给数据时只做定性描述，严禁编造数字。
- 问题与风险每条附上应对建议；用户写“无”时，本节写“本周无重大风险，按计划推进”。
- 下周计划按优先级排序，写清可交付的产出物。
- 使用简短的 Markdown 列表，不使用代码块和表情符号，不写空话套话。""",
    user_template="""请根据以下信息撰写一份本周工作周报：
- 岗位/姓名：{role}
- 本周完成事项：{done}
- 关键成果/数据：{results}
- 问题与风险：{problems}
- 下周计划：{next_plan}""",
)

# ---------------------------------------------------------------------------
# 场景 4：公文写作
# ---------------------------------------------------------------------------
OFFICIAL = Scenario(
    key="official",
    name="公文写作",
    summary="按常见公文文种规范生成通知、通报、请示、报告、函或会议纪要，格式规范、语体庄重。",
    default_tone="正式",
    fields=(
        Field("doc_type", "文种", "例如：通知 / 通报 / 请示 / 报告 / 函 / 会议纪要", lines=1),
        Field("issuer", "发文单位", "例如：XX 公司安全环保部", lines=1),
        Field("receiver", "主送单位", "例如：各部门、各所属单位", lines=1),
        Field("matter", "事由与背景", "例如：为防范安全事故，开展第四季度安全生产大检查", lines=3),
        Field("requirements", "具体事项 / 要求（每行一条）", "例如：\n检查范围覆盖车间与在建项目\n11 月 30 日前书面报送", lines=5),
        Field("deadline", "时限 / 落款日期", "例如：2025 年 11 月 30 日前；落款 2025 年 10 月 25 日", lines=2),
    ),
    system_prompt="""你是资深机关文秘，熟悉《党政机关公文格式》与常用文种的写作规范。
输出格式要求：
- 标题写成“发文机关 + 关于 + 事由 + 文种”，居中式的单行标题即可。
- 下一行写主送机关，以“：”结尾。
- 正文按“缘由—事项—要求”分层：开头交代依据和目的，主体分条列出事项，结尾提出执行要求。
- 根据文种调整语气与结语：通知用“特此通知”，请示用“妥否，请批示”，报告用“特此报告”，函用“特此函达”，会议纪要按议定事项组织。
- 落款写发文单位与日期；文号、联系人、电话一律用【】占位，不要编造。
- 使用规范书面语，不使用口语、网络用语和表情符号，不使用 Markdown 标题符号。""",
    user_template="""请起草一份公文：
- 文种：{doc_type}
- 发文单位：{issuer}
- 主送单位：{receiver}
- 事由与背景：{matter}
- 具体事项/要求：{requirements}
- 时限与落款：{deadline}""",
)

# ---------------------------------------------------------------------------
# 场景 5：小说片段
# ---------------------------------------------------------------------------
NOVEL = Scenario(
    key="novel",
    name="小说片段",
    summary="根据场景、人物与冲突写一段有画面感的小说正文，可指定叙事视角与情绪基调。",
    default_tone="正式",
    fields=(
        Field("setting", "场景（时间 / 地点 / 氛围）", "例如：雨夜的旧书店，只剩最后一盏灯", lines=2),
        Field("characters", "人物与关系", "例如：陈默（30 岁，沉默寡言）与书店女孩（旧识）", lines=2),
        Field("plot", "情节走向 / 冲突", "例如：陈默来追问三年前窗台上一封信的来历", lines=3),
        Field("pov", "叙事视角", "例如：第三人称限知（跟随陈默）", lines=1),
        Field("mood", "情绪基调", "例如：克制、潮湿、留有余味", lines=1),
    ),
    system_prompt="""你是一位擅长画面感与节奏的中文小说作者。
输出格式要求：
- 只输出 300-600 字的连续小说正文，不要大纲、不要分段小标题、不要作者解说。
- 严格按给定叙事视角写作：第三人称限知就只写视角人物能感知的内容。
- 用动作、对话、细节和感官描写推进情节，避免“他感到/她意识到”式的总结旁白。
- 对话独立成段，不用“他说”堆砌提示语；必要时用动作代替提示语。
- 结尾留有余味或悬念，但不解释含义。
- 不使用 Markdown 符号、分点列表和表情符号。""",
    user_template="""请写一段小说片段：
- 场景：{setting}
- 人物与关系：{characters}
- 情节与冲突：{plot}
- 叙事视角：{pov}
- 情绪基调：{mood}""",
)

SCENARIO_LIST: tuple[Scenario, ...] = (EMAIL, XIAOHONGSHU, WEEKLY, OFFICIAL, NOVEL)
SCENARIOS: dict[str, Scenario] = {item.key: item for item in SCENARIO_LIST}
DEFAULT_SCENARIO = EMAIL.key


def get_scenario(key: str) -> Scenario:
    """按 key 取场景，不存在时抛 KeyError。"""
    return SCENARIOS[key]


def resolve_scenario(value: str | None) -> Scenario:
    """兼容界面可能传入的 key 或场景名称。"""
    if not value:
        return SCENARIOS[DEFAULT_SCENARIO]
    if value in SCENARIOS:
        return SCENARIOS[value]
    for scenario in SCENARIO_LIST:
        if value == scenario.name:
            return scenario
    raise KeyError(f"未知写作场景：{value!r}")


def scenario_choices() -> list[tuple[str, str]]:
    """Gradio Dropdown 的选项：(显示名, 场景 key)。"""
    return [(scenario.name, scenario.key) for scenario in SCENARIO_LIST]


def tones() -> list[str]:
    return list(TONES)


def validate_values(scenario: Scenario, values: Mapping[str, str]) -> list[str]:
    """校验用户输入，返回可直接展示的问题列表。"""
    problems: list[str] = []
    for item in scenario.fields:
        text = (values.get(item.key) or "").strip()
        if item.required and not text:
            problems.append(f"请填写「{item.label}」")
        elif len(text) > item.max_chars:
            problems.append(f"「{item.label}」内容过长（最多 {item.max_chars} 字）")
    return problems


def _fill(template: str, values: Mapping[str, str]) -> str:
    """把模板中的 {field_key} 一次性替换为实际输入。

    不使用 str.format，避免用户输入中的花括号导致格式化异常。
    """
    if not values:
        return template
    pattern = re.compile("|".join(re.escape("{" + key + "}") for key in values))
    return pattern.sub(lambda match: values.get(match.group(0)[1:-1], ""), template)


def build_messages(
    scenario: Scenario,
    values: Mapping[str, str],
    tone: str | None = None,
) -> list[dict[str, str]]:
    """把场景 + 用户输入 + 语气组装成对话消息。"""
    tone = tone if tone in TONES else scenario.default_tone

    cleaned = {key: (value or "").strip() for key, value in values.items()}
    user_content = _fill(scenario.user_template, cleaned).strip()
    user_content = f"{user_content}\n\n【语气要求】{tone}（{TONES[tone]}）"

    system_content = f"{scenario.system_prompt}\n\n{OUTPUT_RULES}"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
