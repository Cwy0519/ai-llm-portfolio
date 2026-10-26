# -*- coding: utf-8 -*-
"""提示词与领域知识：游戏测试场景模板 + 用例设计方法 + 消息组装。

这是本项目的"大脑"：新增一个游戏场景，只需要在 GAME_SCENES 里加一项，
界面下拉、提示词、统计都会自动适配，不用改其它文件。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Scene:
    key: str
    name: str
    focus: tuple[str, ...]      # 该场景要重点覆盖的业务点
    risks: tuple[str, ...]      # 该场景最容易出问题的点

    def brief(self) -> str:
        return "；".join(self.focus)


DESIGN_METHODS: dict[str, str] = {
    "等价类划分": "把输入划分为有效等价类与无效等价类，每个类至少一条用例，覆盖合法值与非法值",
    "边界值分析": "针对数量、长度、金额、时间、等级等边界，取 min、min-1、max、max+1 与越界值",
    "场景法": "按正常流、备选流、异常流设计端到端场景，验证业务流程是否走得通",
    "错误推测法": "基于测试经验推测易错点：重复提交、并发、网络中断、权限越界、数据溢出、状态残留",
    "正交实验法": "对机型、网络、账号状态等多因素组合，用正交思路挑出高性价比组合",
}

GAME_SCENES: dict[str, Scene] = {
    "登录与注册": Scene(
        key="login",
        name="登录与注册",
        focus=("账号密码登录", "手机号/验证码登录", "第三方授权登录", "注册与实名认证", "密码找回"),
        risks=("验证码过期与重发", "弱密码与特殊字符", "重复注册与账号绑定冲突", "异地登录与挤号", "实名信息不合法"),
    ),
    "充值付费": Scene(
        key="pay",
        name="充值付费",
        focus=("充值档位与首充双倍", "月卡/通行证", "支付回调与补单", "订单取消与退款", "优惠券与折扣叠加"),
        risks=("支付成功但发货不到账", "重复点击产生重复订单", "订单超时与回调丢失", "金额精度与分转元", "渠道差异与掉单"),
    ),
    "战斗与技能": Scene(
        key="battle",
        name="战斗与技能",
        focus=("普攻与技能释放", "技能冷却与连招", "伤害结算与暴击", "Buff/Debuff 叠加", "战斗结算与掉落"),
        risks=("冷却期间连点", "技能打断与状态残留", "伤害数值溢出与取整", "帧率波动下的判定", "结算掉线重连"),
    ),
    "背包与道具": Scene(
        key="bag",
        name="背包与道具",
        focus=("道具获得与使用", "背包扩容与排序", "堆叠与拆分", "道具过期与回收", "装备穿戴与替换"),
        risks=("满背包时获得道具", "数量为 0 或负数", "堆叠上限溢出", "使用中丢弃道具", "跨区数据不同步"),
    ),
    "组队与匹配": Scene(
        key="team",
        name="组队与匹配",
        focus=("创建/加入/退出队伍", "匹配与取消匹配", "队长转让与踢人", "副本开局与结算", "匹配超时"),
        risks=("多人同时操作造成的状态错乱", "匹配中下线", "队伍人数上限", "跨服匹配异常", "重复匹配请求"),
    ),
    "断线重连": Scene(
        key="reconnect",
        name="断线重连",
        focus=("弱网与高丢包", "切后台与杀进程", "重连后的场景恢复", "重连期间的奖励结算", "多端顶号"),
        risks=("重连后状态丢失或重复", "重连期间被扣体力/道具", "断线时仍能收到奖励", "重连风暴", "提示文案与引导"),
    ),
    "活动与签到": Scene(
        key="activity",
        name="活动与签到",
        focus=("每日签到与补签", "活动开启与结束时间", "奖励领取与重复领取", "排行榜刷新", "邮件发放"),
        risks=("跨天/时区导致的刷新异常", "活动结束瞬间的边界操作", "重复领取与并发领取", "排行榜并列与刷分", "邮件附件过期"),
    ),
    "通用/自定义": Scene(
        key="custom",
        name="通用/自定义",
        focus=("按用户描述的功能自行归纳业务点",),
        risks=("需求描述不完整导致覆盖不足，请补充输入/输出与状态变化",),
    ),
}

CASE_FIELDS = ("用例标题", "优先级", "用例类型", "设计方法", "前置条件", "操作步骤", "预期结果")

SYSTEM_PROMPT = """你是一位有 5 年经验的手游测试工程师，擅长把需求拆成可执行、可复现、覆盖到位的测试用例。

【输出要求】
1. 只输出一个 JSON 对象，不要输出任何解释、前言、Markdown 代码块以外的文字。
2. JSON 结构固定为：{"cases": [ {...}, {...} ]}
3. 每条用例必须包含以下字段，全部使用中文：
   - title：用例标题，一句话说清"在什么情况下验证什么"，例如"背包已满时领取邮件道具应提示并转为邮件暂存"
   - priority：P0 / P1 / P2 / P3 之一（P0=核心主流程，P1=重要分支，P2=一般，P3=低频或体验类）
   - type：功能 / 边界 / 异常 / 兼容 / 性能 / 安全 之一
   - method：本次使用的用例设计方法名
   - preconditions：前置条件，写清账号状态、数据准备、环境要求
   - steps：操作步骤，字符串数组，每步一个动作，3–6 步
   - expected：预期结果，必须可观察、可判定，不要写"正常显示"这种模糊描述
4. 用例要互相独立、可执行，禁止出现"同上""参考上一条"这类写法。
5. 不要编造具体数值配置（如"体力上限 120"），如需数值请写成区间或占位符（如"体力上限 N"）。
"""


def scene_names() -> list[str]:
    return list(GAME_SCENES.keys())


def method_names() -> list[str]:
    return list(DESIGN_METHODS.keys())


def get_scene(name: str) -> Scene:
    if name not in GAME_SCENES:
        raise KeyError(f"未知的游戏场景：{name}")
    return GAME_SCENES[name]


def build_user_prompt(scene: Scene, feature: str, methods: Sequence[str], count: int) -> str:
    """把场景、功能描述、设计方法、数量拼成一条用户消息。"""
    if not methods:
        raise ValueError("至少选择一种用例设计方法")
    method_lines = "\n".join(f"- {m}：{DESIGN_METHODS[m]}" for m in methods if m in DESIGN_METHODS)
    focus = "；".join(scene.focus)
    risks = "；".join(scene.risks)
    return f"""【测试场景】{scene.name}
【该场景常见业务点】{focus}
【该场景高风险点】{risks}

【本次要验证的功能】
{feature.strip()}

【必须使用的用例设计方法】
{method_lines}

【输出数量】{count} 条，且必须覆盖上面勾选的每一种设计方法，每种方法至少 2 条。
【额外要求】
- 至少 {max(1, count // 5)} 条异常/边界类用例，不要全都是主流程用例；
- 优先级分布要合理，P0 不超过总数的三分之一；
- 标题中体现验证意图，不要写成"测试登录"这种笼统说法。
"""


def build_messages(scene_name: str, feature: str, methods: Sequence[str], count: int) -> list[dict]:
    scene = get_scene(scene_name)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(scene, feature, methods, count)},
    ]
