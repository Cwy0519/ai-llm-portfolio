"""不联网的自测脚本。

作用：用"假的模型"跑一遍完整流水线，验证切分、清洗、拼接、异常提示都对。
答辩前跑一次，能证明"我的程序逻辑是经过测试的"，比空口说可靠。

运行方式（在项目根目录）：
    .venv\\Scripts\\python.exe tests\\selftest.py
"""

import sys
from pathlib import Path

# 让脚本能 import 到上一级目录里的模块
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import services.translator as translator                    # noqa: E402
from config import Settings, config_problem                 # noqa: E402
from utils.postprocess import clean_output                  # noqa: E402
from utils.text_split import count_chars, split_text        # noqa: E402

PASSED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    """一个极简的断言函数：打印结果，失败就抛异常。"""
    global PASSED
    if condition:
        PASSED += 1
        print(f"  [通过] {name}")
    else:
        print(f"  [失败] {name}  {detail}")
        raise AssertionError(name)


def make_settings(**overrides) -> Settings:
    """造一个测试用的配置对象，不读 .env。"""
    base = dict(api_key="sk-test", base_url="http://127.0.0.1:1/v1", model="fake",
                timeout=5, max_chars=50, temperature=0.3, max_retries=0)
    base.update(overrides)
    return Settings(**base)


def fake_stream(settings, messages, temperature=None):
    """假的模型输出：故意带上"译文："前缀和代码块，用来验证清洗逻辑。"""
    body = "译文：```\n这是假译文。\n```"
    for ch in body:
        yield ch


# ---------------------------------------------------------------- 测试用例

def test_split() -> None:
    print("\n[1] 长文本切分")
    text = "第一句话在这里。第二句话稍长一点点。第三句话也不短。" * 8
    chunks = split_text(text, max_chars=60)
    check("切出了多段", len(chunks) > 1, f"实际 {len(chunks)} 段")
    check("每段都不超过上限", all(len(c) <= 60 for c in chunks),
          f"最长 {max(len(c) for c in chunks)} 字")
    check("没有空段", all(c.strip() for c in chunks))

    # 句子没被拦腰截断：除最后一段外，每段都应以句末标点结尾
    check("尽量按句切分", all(c[-1] in "。！？" for c in chunks[:-1]))

    # 单句超长时必须硬切，且仍然不超限
    long_sentence = "啊" * 200
    hard = split_text(long_sentence, max_chars=50)
    check("超长单句能硬切", all(len(c) <= 50 for c in hard) and len(hard) == 4)


def test_clean() -> None:
    print("\n[2] 输出清洗")
    check("去掉“译文：”前缀", clean_output("译文：Hello") == "Hello")
    check("去掉代码块", clean_output("```\nHello\n```") == "Hello")
    check("去掉包裹的引号", clean_output("“Hello”") == "Hello")
    check("空输入不报错", clean_output("") == "")
    check("正常文本不被误伤", clean_output("Hello world.") == "Hello world.")


def test_pipeline() -> None:
    print("\n[3] 完整流水线（用假模型）")
    # 把真正的网络调用换成假的
    translator.stream_chat = fake_stream

    settings = make_settings(max_chars=50)
    text = "第一句话在这里。第二句话稍长一点点。第三句话也不短。" * 6

    outputs = list(translator.process(
        text=text, target_lang="英文", mode="翻译", glossary="",
        bilingual=False, settings=settings,
    ))
    final_text, final_status = outputs[-1]

    check("有输出", bool(final_text))
    check("清洗后没有残留前缀", "译文：" not in final_text)
    check("没有残留代码块", "```" not in final_text)
    check("状态栏显示完成", "完成" in final_status, final_status)
    check("多段时确实分段了", len(outputs) > 10, f"共 {len(outputs)} 次刷新")


def test_bilingual() -> None:
    print("\n[4] 双语对照")
    translator.stream_chat = fake_stream
    settings = make_settings(max_chars=500)
    outputs = list(translator.process(
        text="只有一句话。", target_lang="英文", mode="翻译",
        glossary="", bilingual=True, settings=settings,
    ))
    final_text = outputs[-1][0]
    check("包含【原文】", "【原文】" in final_text)
    check("包含【译文】", "【译文】" in final_text)


def test_none_inputs() -> None:
    print("\n[5] 空输入 / 空术语表（Gradio 会传 None 进来）")
    translator.stream_chat = fake_stream
    settings = make_settings(max_chars=500)

    # 术语表没填时，Gradio 传的是 None 而不是 ""，这里必须不崩
    outputs = list(translator.process(
        text="测试。", target_lang="英文", mode="翻译",
        glossary=None, bilingual=False, settings=settings, style=None,
    ))
    check("术语表为 None 时不崩溃", bool(outputs[-1][0]))

    try:
        list(translator.process("", "英文", "翻译", "", False, settings))
        check("空输入应该报错", False)
    except ValueError as e:
        check("空输入报 ValueError", "输入是空的" in str(e))

    try:
        list(translator.process("hi", "英文", "不存在的模式", "", False, settings))
        check("非法模式应该报错", False)
    except ValueError as e:
        check("非法模式报 ValueError", "不认识的模式" in str(e))

    check("缺 key 时给出提示", config_problem(make_settings(api_key="")) is not None)
    check("填了 key 时通过检查", config_problem(make_settings()) is None)


def test_count() -> None:
    print("\n[6] 字数统计")
    check("忽略空白", count_chars("a b\nc") == 3)
    check("空字符串为 0", count_chars("") == 0)


def main() -> None:
    print("=" * 46)
    print("自测开始（不联网，不需要 API Key）")
    print("=" * 46)
    test_split()
    test_clean()
    test_pipeline()
    test_bilingual()
    test_none_inputs()
    test_count()
    print("\n" + "=" * 46)
    print(f"全部通过：{PASSED} 项检查")
    print("=" * 46)


if __name__ == "__main__":
    main()
