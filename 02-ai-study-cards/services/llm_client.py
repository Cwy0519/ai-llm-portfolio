"""和大模型说话的唯一出口。

这一层只做三件事：
    1. 发请求（非流式：一次拿到完整 JSON，方便解析）；
    2. 网络抖动时自动重试；
    3. 把各种异常翻译成"人话"，交给界面去提示。

为什么不用流式输出？
    卡片要的是完整 JSON，流式返回的是半截 JSON，反而更难解析。
    "边生成边显示"适合聊天和长文翻译，不适合结构化数据。

把所有网络细节关在这个文件里，好处是：换平台只改 .env，换界面不用改这里。

本文件用到的 Python 知识（答辩时指着某一行，先报名字再解释）：
    1.  import / from ... import ...            —— 导入模块
    2.  class 类 / 继承 Exception               —— 自定义一个异常类型
    3.  __init__ 构造方法 / self                —— 创建对象时把配置存到对象上
    4.  tuple[type[Exception], ...]             —— 类型提示：元组里装的是"异常类"
    5.  getattr(对象, "名字", 默认值)            —— 按名字取属性，没有也不报错
    6.  生成器表达式 (x for x in ...) / tuple()  —— 边算边收集，不先建列表
    7.  while True + try/except + continue      —— 重试循环的标准写法
    8.  raise / raise ... from e                —— 抛异常并保留原始异常链
    9.  多个 except 分支 + isinstance            —— 按异常类型分别处理
   10.  dict 字典 + **kwargs 解包                —— 动态拼"参数名=值"
   11.  条件表达式 a if 条件 else b              —— 一行里做选择
   12.  time.sleep(秒)                          —— 暂停一会儿（退避等待）
   13.  f-string                                —— 把变量塞进提示文字里
"""

# 【import 导入标准库】导入 time 模块，本文件只用它的 time.sleep() 让程序"停一会儿"
import time

# 【import 导入整个模块】import openai 之后，用 openai.BadRequestError 这种"模块.名字"取东西
import openai
# 【from ... import ...】只从 openai 模块里拿 OpenAI 这个类，后面能直接写 OpenAI(...)
from openai import OpenAI

# 【from ... import ...】从项目自己的 config 模块导入 Settings
#   Settings 是一个 dataclass，里面存 api_key / base_url / timeout 这些配置
from config import Settings


# 【class 类 + 继承】class 名字(父类)：括号里写 Exception，表示"继承内置异常类"
#   继承 Exception 后就有 raise / 被 except 捕获的资格；它和内置异常的用法完全一样
#   为什么自定义？见下面 docstring 的第一句
class LLMError(Exception):
    """我们自己定义的错误类型，界面只认识它，不需要认识 openai 的一堆异常。"""


# 可以重试的异常：网络抖动、超时、限流、服务端 5xx。
# 用 getattr 取，是为了不同版本的 openai 库里少某个异常时也不会崩。
# 【类型提示】左边写成 _TRANSIENT: tuple[type[Exception], ...]
#   "tuple[...]" 表示这是个元组；"type[Exception]" 表示元素是 Exception 的子类；
#   后面那个 "..." 表示个数不限（0 个、3 个都行）
# 【tuple() 转换】右边是一个 tuple(...) 调用，把生成器里的东西一次性收集成元组
_TRANSIENT: tuple[type[Exception], ...] = tuple(
    # 【生成器表达式】`cls for cls in (...)`：从候选元组里一个个取出 cls
    #   这里没写方括号，所以是生成器表达式（边算边交出去，省内存），外层由 tuple() 收集
    cls for cls in (
        # 【getattr 动态取属性】getattr(模块, "名字", 默认值)：按字符串名字取属性
        #   名字不存在时返回默认值 None，而不是抛 AttributeError
        #   为什么不用 openai.APIConnectionError？因为 openai 库换版本时异常类可能改名，
        #   直接点属性可能直接 AttributeError，用 getattr 就能"有就拿、没有就跳过"
        getattr(openai, "APIConnectionError", None),
        # 【getattr】连接失败：断网、DNS 错、代理不对，都是这一类
        getattr(openai, "APITimeoutError", None),
        # 【getattr】请求超时：服务器半天不回话
        getattr(openai, "RateLimitError", None),
        # 【getattr】限流 / 余额不足（HTTP 429）
        getattr(openai, "InternalServerError", None),
        # 【getattr】服务端 5xx：平台自己出问题了，这种"等一下再试"往往就好了
    # 【生成器里的 if 过滤】只保留不是 None 的项，把"这个版本的库里没有的类"过滤掉
    ) if cls is not None
)


# 【class 类】一个"薄封装"：外面只知道 complete(messages)，不知道底下是 openai
#   这叫"门面"思路——把复杂细节关在一个类里，换平台时只改这个文件
class LLMClient:
    """一个薄薄的封装：对外只暴露 complete(messages) -> str 这一个方法。"""

    # 【__init__ 构造方法】创建对象时自动执行，写成 LLMClient(settings) 就会调到这里
    #   第一个参数 self 代表"这个对象自己"，调用时不用手动传
    def __init__(self, settings: Settings):
        # 【self.属性 = 值】把配置对象挂在 self 上，同一个类的其它方法就能 self.settings 取到
        self.settings = settings
        # max_retries=0：关掉 SDK 自带的自动重试，重试逻辑我们自己控制，方便加提示
        # 【关键字参数】OpenAI(...) 里每个"参数名=值"都对应一个构造参数，顺序可以打乱
        # 【self._client】属性名前面加下划线，是"内部使用"的约定，提醒外面别直接碰它
        self._client = OpenAI(
            # 【关键字参数】api_key：密钥，来自 .env，代码里绝不写死
            api_key=settings.api_key,
            # 【关键字参数】base_url：接口地址，换平台只改 .env
            base_url=settings.base_url,
            # 【关键字参数】timeout：单次请求最多等多少秒，超时就抛超时异常
            timeout=settings.timeout,
            # 【关键字参数】max_retries=0：不让 SDK 偷偷重试
            #   为什么？因为 SDK 的重试我们看不见，也没法加"第几次重试"的提示；
            #   自己写重试循环，就能控制等待时间（下面的 1.5 * attempt 越等越久）
            max_retries=0,
        )
        # JSON 模式标记：有些平台/模型不支持，遇到 400 就自动关掉再试
        # 【布尔属性】存成对象属性而不是局部变量，因为"关掉之后下次也别再开"要记住状态
        self._json_mode = settings.json_mode

    # 【def 方法 + 类型提示】messages: list[dict] 是"消息列表"（每项是 role/content 字典）
    #   "-> str" 表示这个方法返回一个字符串（模型输出的原文）
    def complete(self, messages: list[dict]) -> str:
        """发一次请求，返回模型输出的纯文本（预期里面是 JSON）。"""
        # 【变量初始化】attempt 记录"已经重试过几次"，先设为 0
        attempt = 0
        # 【while True 无限循环】一直转，直到里面 return（成功）或 raise（放弃）才结束
        #   为什么不用 for 循环？因为"要不要再试一次"是条件判断，while + continue 最直白
        while True:
            # 【try/except】把可能失败的代码包起来，按异常类型分别处理
            try:
                # 【dict 字典字面量】把这一次请求的参数先装进字典
                #   好处：参数要不要加（response_format）可以后面用 if 决定
                kwargs = {
                    # 【字典的键必须是字符串】这里的键名就是接口的参数名
                    "model": self.settings.model,
                    "messages": messages,
                    "temperature": self.settings.temperature,
                }
                # 【if 判断 + 属性读取】只有配置里开了 JSON 模式，才加这个参数
                if self._json_mode:
                    # 告诉平台"我只要 JSON"，能显著降低格式出错的概率
                    # 【字典赋值】kwargs["response_format"] = ...：给字典新增一个键
                    #   {"type": "json_object"} 是平台规定的固定写法
                    kwargs["response_format"] = {"type": "json_object"}

                # 【**kwargs 解包】**kwargs 把字典拆成一个个"参数名=值"传进去
                #   这行等价于 create(model=..., messages=..., temperature=...)
                #   如果 kwargs 里多了 response_format，也会自动带上
                resp = self._client.chat.completions.create(**kwargs)
                # 【条件表达式 + 属性链】resp.choices 是列表；先判断非空再取 [0]
                #   写成 "if resp.choices else ''" 是为了防 IndexError（列表空时 [0] 会报错）
                content = resp.choices[0].message.content if resp.choices else ""
                # 【if + or 短路】content 是 None 或全是空白，都算"模型没说话"
                #   not content 先判 None/空串；.strip() 去掉空格换行后再看是否为空
                if not content or not content.strip():
                    # 【raise 抛自定义异常】抛 LLMError，调用方用 except LLMError 接
                    raise LLMError("模型没有返回内容，请再试一次。")
                # 【return 直接结束方法】成功了就交回文本，while 循环也一起结束
                return content

            # 【except 只接某一种异常】这一支只捕获我们自己抛的 LLMError
            #   注意：except 分支是"从上往下匹配"的，所以具体的一定写在笼统的前面
            except LLMError:
                # 【raise 不带参数】把当前异常原样继续往上抛，不做包装
                #   为什么要这一行？因为下面还有 except Exception 兜底，
                #   如果不先接住，我们自己的 LLMError 会被兜底分支再翻译一次
                raise

            # 【except 具体异常 as e】接住 openai 的"请求不合法"（HTTP 400）
            #   as e 把异常对象命名为 e，后面能读它的信息
            except openai.BadRequestError as e:
                # 有些平台不认 response_format，关掉 JSON 模式再试一次
                # 【if 判断状态】只有当前确实开着 JSON 模式，才值得"关掉重试"
                if self._json_mode:
                    # 【修改对象属性】把标记改成 False，下一轮就不会再带 response_format
                    self._json_mode = False
                    # 【continue 回到循环开头】跳过本轮剩下的代码，重新发一次请求
                    #   为什么能保证不无限循环？因为 _json_mode 已经被改成 False，
                    #   下一次再 400 就走下面的 raise，不会再 continue
                    continue
                # 【异常翻译 + raise ... from e】把原始异常 e 翻译成人话再抛
                #   "from e" 会保留原始异常（异常链），排查时能看到真正的技术原因
                raise LLMError(_friendly(e, self.settings.timeout)) from e

            # 【except Exception 兜底】except Exception 能接住几乎所有普通异常
            except Exception as e:  # noqa: BLE001 —— 兜住所有异常再翻译成人话
                # 【isinstance 判断】isinstance(e, _TRANSIENT)：e 是不是"可重试"的那几类
                #   同时要求"还没超过次数上限"，两个条件都满足才重试
                #   attempt < max_retries：比如上限 2，就最多补试 2 次
                if isinstance(e, _TRANSIENT) and attempt < self.settings.max_retries:
                    # 【自增】attempt += 1 等价于 attempt = attempt + 1
                    attempt += 1
                    # 【time.sleep 暂停】让程序睡一会儿再重试，这叫"退避"
                    #   1.5 * attempt：第一次等 1.5 秒，第二次等 3 秒——越等越久
                    #   为什么越等越久？因为限流/服务端抖动需要恢复时间，
                    #   立刻重试往往还是失败，还会加重对方压力
                    time.sleep(1.5 * attempt)   # 越等越久，给服务端一点恢复时间
                    # 【continue】回到 while 顶部，重新发请求
                    continue
                # 【最终失败】不是可重试异常，或者次数用完了：翻译成人话再抛
                #   from e 保留原始异常，方便在日志里看到根因
                raise LLMError(_friendly(e, self.settings.timeout)) from e


# 【模块级私有函数】名字前面一个下划线：约定"只给本文件内部用"，外面不要 import 它
# 【类型提示】e: Exception 说明参数是异常对象；timeout: int 是超时秒数；-> str 返回一句话
def _friendly(e: Exception, timeout: int) -> str:
    """把异常翻译成用户能看懂、能自己解决的一句话。"""
    # 【isinstance 分支链】从具体到笼统地判断异常类型，命中哪个就返回哪句提示
    #   为什么要翻译？因为把 "Error code: 401 - invalid_api_key" 直接丢给用户，
    #   用户根本不知道该改什么；翻译成"检查 .env 里的 LLM_API_KEY"才叫能解决问题
    if isinstance(e, openai.AuthenticationError):
        # 【return 提前返回】函数一 return 就结束，后面的 if 不会再执行
        return "API Key 无效或已过期（401）。请检查 .env 里的 LLM_API_KEY 是否填对。"
    # 【isinstance】403：Key 有效，但没被授权用这个模型
    if isinstance(e, openai.PermissionDeniedError):
        # 【return 返回提示】403：Key 有效但没权限用这个模型
        return "当前 Key 没有权限调用这个模型（403）。请确认账号已开通该模型。"
    # 【isinstance】404：地址写错或模型名写错
    if isinstance(e, openai.NotFoundError):
        # 【return 返回提示】404：接口地址或模型名写错
        return "接口地址或模型名不存在（404）。请检查 LLM_BASE_URL 和 LLM_MODEL。"
    # 【isinstance】429：请求太快或余额不足
    if isinstance(e, openai.RateLimitError):
        # 【return 返回提示】429：请求太频繁或账户余额不足
        return "请求太频繁或余额不足（429）。等几秒再试，或检查账户余额。"
    # 【isinstance】超时：注意这里用了外层的 timeout 参数
    if isinstance(e, openai.APITimeoutError):
        # 【f-string】把 timeout 这个整数直接塞进提示里，用户就知道现在等了多少秒
        return f"请求超时（{timeout} 秒）。可以把 .env 里的 LLM_TIMEOUT 调大，或把 MAX_CHARS 调小。"
    # 【isinstance】连不上：先怀疑网络和地址
    if isinstance(e, openai.APIConnectionError):
        # 【return 返回提示】连不上服务器：先查网络和地址
        return "连不上服务器。请检查网络，以及 LLM_BASE_URL 是否写错。"
    # 【isinstance】400：参数/内容不合法的通用提示
    if isinstance(e, openai.BadRequestError):
        # 【return 返回提示】400：参数或内容不合法
        return "请求被模型拒绝了（400）。常见原因是材料太长，或该模型不支持当前参数。"
    # 【兜底分支】不认识的异常：至少把类型名和原文给人看，方便搜错误信息
    #   type(e).__name__ 拿到类名字符串，比如 "ValueError"；{e} 是异常的内容
    return f"调用失败（{type(e).__name__}）：{e}"
