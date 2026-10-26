# AI 翻译与润色工具

一个基于 **Gradio + 大模型 API** 的网页工具：粘贴原文，选择目标语言和模式，一键得到译文。
支持长文本自动分段、术语表固定译法、双语对照和流式输出。

![界面预览](docs/ui-home.png)

---

## 功能

| 功能 | 说明 |
|---|---|
| 翻译 | 把原文翻译成 7 种目标语言之一 |
| 润色 | 不改原意，只把表达改通顺，支持 3 种风格 |
| 翻译 + 润色 | 先翻译，再把译文润色一遍（最慢，效果通常最好） |
| 长文本分段 | 按段落/句子切成小段逐段处理，避免超长报错、前后术语不一致 |
| 术语表 | 一行一条 `源词=译词`，强制模型使用指定译法 |
| 双语对照 | 输出「原文 / 译文」交替对照，方便校对 |
| 流式输出 | 生成一个字显示一个字，不用干等 |
| 错误提示 | 没配 Key、超时、限流、地址写错，都会弹出中文提示且不崩界面 |

---

## 环境要求

- Windows 10 / 11
- Python 3.10 及以上（本项目在 3.13 上验证通过）
- 一个兼容 OpenAI 接口的大模型 API Key（DeepSeek、智谱、通义、月之暗面、本地 Ollama 都行）

---

## 安装

在项目根目录打开 PowerShell，依次执行：

```powershell
# 1. 创建虚拟环境（只需要做一次）
python -m venv .venv

# 2. 安装依赖（只需要做一次）
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果下载很慢，可以加国内镜像：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 配置

```powershell
# 把模板复制一份，改名为 .env
Copy-Item .env.example .env
```

然后用记事本打开 `.env`，填入你的 Key：

```ini
LLM_API_KEY=sk-你的真实密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

> ⚠️ `.env` 已经在 `.gitignore` 里，不会被提交，也不会泄露。
> 换平台时只需要改 `LLM_BASE_URL` 和 `LLM_MODEL` 两行，代码一行都不用动。

---

## 运行

**方式一（推荐）**：双击 `run.bat`

**方式二**：命令行

```powershell
.\.venv\Scripts\python.exe app.py
```

浏览器会自动打开 <http://127.0.0.1:7860>。

---

## 目录结构

```
ai-translator/
├─ app.py                 程序入口：组装界面 + 启动服务
├─ config.py              配置：读 .env，做配置检查
├─ prompts.py             提示词模板：翻译 / 润色
├─ services/
│  ├─ llm_client.py       网络层：调 API、流式接收、重试、异常翻译成人话
│  └─ translator.py       业务层：切分 → 拼提示词 → 调用 → 清洗 → 拼接
├─ utils/
│  ├─ text_split.py       长文本切分（按段 → 按句 → 硬切）
│  └─ postprocess.py      输出清洗（去前缀、去代码块、去引号）
├─ ui/
│  └─ layout.py           界面层：布局 + 事件绑定 + 错误提示
├─ tests/
│  └─ selftest.py         不联网的自测脚本
├─ docs/                  截图
├─ 答辩/                  答辩 PPT、讲稿、生成脚本
├─ .env.example           配置文件模板
├─ requirements.txt       依赖清单
└─ run.bat                一键启动
```

**分层原则**：界面不知道网络细节，网络层不知道界面长什么样，
提示词单独成文件——改任何一层都不用动其它层。

---

## 数据流

```
用户输入
   ↓
ui/layout.py          收集参数，检查配置
   ↓
services/translator.py  切分文本，逐段处理
   ↓
prompts.py            把文字套进提示词模板
   ↓
services/llm_client.py  发给大模型，流式收回
   ↓
utils/postprocess.py  清洗掉模型多余的前缀和包装
   ↓
ui/layout.py          每一小块都刷新到界面上
```

---

## 测试

```powershell
.\.venv\Scripts\python.exe tests\selftest.py
```

不需要联网、不需要 API Key，共 24 项检查，覆盖切分、清洗、拼接、
双语、空输入、异常提示等逻辑。

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 提示“还没有配置 API Key” | 没有 `.env` 或 Key 是占位符 | 按上面「配置」一节填写 |
| 401 无效 | Key 填错、复制时带了空格 | 检查 `.env`，重新粘贴 |
| 404 模型不存在 | 地址和模型名不匹配 | 对照 `.env.example` 里的对照表 |
| 429 限流/余额不足 | 请求太快或账户没钱 | 等几秒重试，或检查余额 |
| 超时 | 文本太长或网络慢 | 调大 `LLM_TIMEOUT`，调小 `MAX_CHARS` |
| 界面打开是空白 | 浏览器缓存了旧页面 | 按 `Ctrl + F5` 强制刷新 |

---

## 说明

- 本项目用于课程作业演示，API Key 与调用费用由使用者自行承担。
- 提交前请确认 `.env` 不在版本库中（`git status` 看不到它）。
