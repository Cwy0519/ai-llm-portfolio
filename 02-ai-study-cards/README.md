# AI 学习卡片生成器

输入一段学习材料，一键生成 **5 种形式**的复习资料：问答卡、填空题、记忆口诀、知识要点、类比解释。
基于 **Python + Gradio + 大模型 API**，支持难度分级、长文自动分段、多类型并行生成、一键导出 Markdown。

> 一句话：**输入一段学习内容，AI 帮你生成多种形式的复习资料。**

![界面预览](docs/ui-home.png)

---

## 功能

| 功能 | 说明 |
|---|---|
| 5 种卡片形式 | 问答卡、填空题、记忆口诀、知识要点、类比解释，每种都有独立的提示词模板 |
| 自由勾选 | 想生成哪几种就勾哪几种（至少 2 种），每种单独调用一次模型 |
| 难度分级 | 入门 / 进阶 / 挑战，难度要求直接写进提示词 |
| 长文自动分段 | 材料超过 `MAX_CHARS` 字就自动切段生成，再合并，避免超上下文和"顾头不顾尾" |
| 并行生成 | 多种卡片用线程池同时请求，完成一种就在对应 Tab 显示一种 |
| 结果好读好复制 | Gradio Tabs 分栏展示，每个结果框右上角有复制按钮 |
| 一键导出 | 自动保存带时间戳的 Markdown 文件，也可以在页面上直接下载 |
| 间隔复习计划 | 按第 1 / 2 / 4 / 7 / 15 天自动排出复习日期（纯本地计算，不花模型调用） |
| 友好错误提示 | 没配 Key、401、404、429、超时、JSON 格式错误，都变成中文提示，界面不会白屏 |

---

## 快速开始（PyCharm）

### 1. 打开项目

PyCharm → **File → Open** → 选中 `study-cards-project` 这个**文件夹**。

### 2. 选解释器

右下角 **Python Interpreter** → 选择项目里的 `.venv`（本机已经建好；换电脑就
**Add Local Interpreter → Virtualenv → New** 新建一个，再执行下一步装依赖）。

### 3. 装依赖（换电脑才需要，本机已装好）

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. 配置 API Key

复制 `.env.example` 改名为 `.env`（本机已有 `.env`），填入：

```ini
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-5.3-flashx
```

> `.env` 已在 `.gitignore` 里，**不要提交、不要截图**。

### 5. 先自检，再运行

```powershell
.\.venv\Scripts\python.exe scripts\check_api.py     # 看到 [成功] 说明 Key 和网络都通了
```

右键 `app.py` → **Run 'app'**，浏览器自动打开 <http://127.0.0.1:7861>。
也可以双击 `run.bat`。

### 6. 跑自测

```powershell
.\.venv\Scripts\python.exe tests\selftest.py        # 68 项，不联网、不花钱
```

---

## 项目结构

```
study-cards-project/
├─ app.py                 程序入口：组装界面 + 启动服务
├─ config.py              配置：读 .env、校验配置
├─ prompts.py             提示词模板 + 5 种卡片类型定义（项目的"大脑"）
├─ services/
│  ├─ llm_client.py       网络层：调 API、重试、JSON 模式、异常翻译成人话
│  └─ generator.py        业务层：分段 → 调模型 → 解析 → 合并，并行处理多种类型
├─ utils/
│  ├─ cards.py            JSON 解析、字段校验、Markdown 渲染
│  ├─ text_split.py       长文本切分（按段 → 按句 → 硬切）
│  ├─ exporter.py         导出 Markdown 文件
│  └─ review_plan.py      间隔复习计划（纯本地日期计算）
├─ ui/
│  └─ layout.py           界面层：布局 + 事件绑定 + 错误提示
├─ scripts/
│  └─ check_api.py        连通性自检（先跑这个，再跑界面）
├─ tests/
│  └─ selftest.py         不联网自测（68 项）
├─ docs/
│  └─ ui-home.png         界面截图
├─ 答辩/                  答辩 PPT + 讲稿
├─ .env.example           配置模板
├─ requirements.txt       依赖清单
├─ run.bat                一键启动
└─ README.md              本文件
```

> **代码里已经有逐行注释**：每个语句上方都有 `# 【知识点】—— 在干什么`，
> 直接读源码就能看懂，不需要另找讲义。

**分层原则**：界面不知道网络细节，网络层不知道界面长什么样，提示词单独成文件——
改任何一层都不用动其它层。

---

## 数据流（一张图记住）

```
用户粘贴材料
   ↓
ui/layout.py            收集参数、检查配置、校验"至少 2 种"
   ↓
services/generator.py   按 MAX_CHARS 分段；多种类型丢进线程池并行
   ↓
prompts.py              把材料 + 卡片类型 + 难度 + 数量套进提示词模板
   ↓
services/llm_client.py  发给大模型（JSON 模式），失败自动重试
   ↓
utils/cards.py          抠出 JSON → 校验字段 → 合并分段结果 → 渲染 Markdown
   ↓
ui/layout.py            完成一个刷新一个 Tab，最后写文件 + 生成复习计划
```

---

## 一天看懂路线（共约 3.5 小时）

> 不用一天全泡进去，按下面 8 段走；每段末尾"要能回答"的问题答不上，就回去看那一段。

| 时间 | 看 / 做什么 | 看完要能回答 |
|---|---|---|
| 0:00–0:20 | 跑起来，用示例材料生成一次 | 这个工具输入什么、输出什么？5 个 Tab 分别是什么？ |
| 0:20–0:50 | `config.py` + `prompts.py` | Key 从哪来？五种卡片的区别靠什么控制？ |
| 0:50–1:20 | `services/llm_client.py` | 为什么要重试？401/429/超时怎么变成中文提示？ |
| 1:20–1:50 | `utils/cards.py` | 模型返回的 JSON 可能有什么"脏数据"？怎么兜底？ |
| 1:50–2:20 | `utils/text_split.py` + `services/generator.py` | 长材料为什么要切？为什么用线程池？`yield` 有什么用？ |
| 2:20–2:50 | `ui/layout.py`（只看 `on_generate` 和 `build_ui` 骨架） | 点按钮后，数据依次经过哪些函数？9 个输出为什么必须对顺序？ |
| 2:50–3:10 | `app.py` + `tests/selftest.py` | 程序怎么启动？怎么证明"没改坏"？ |
| 3:10–3:40 | 合上代码，用自己的话讲 3 分钟 | 能不能讲清"它是什么 / 怎么做的 / 难在哪"？ |

**看懂的标准（三条都做到就算过）**：

1. 能画出上面的数据流，说出 5 个环节分别归哪个文件；
2. 能讲清 3 个技术点：统一 JSON 协议、长文分段、多类型并行；
3. 老师随便指一行，能说出"用了什么语法、为什么这么写"。

---

## 测试

```powershell
.\.venv\Scripts\python.exe tests\selftest.py
```

不联网、不消耗额度，覆盖：JSON 提取（代码块/废话/尾逗号）、字段校验、Markdown 渲染、
分段合并、长文硬切、提示词拼装、单类型生成、多类型并行、失败兜底、复习计划日期、
导出文件、配置检查、UTF-8/GBK 文件读取、界面构建，共 **68 项**。

---

## 常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 提示"还没有配置 API Key" | 没有 `.env` 或 Key 是占位符 | 按「配置 API Key」一节填写，重启程序 |
| 401 | Key 填错、复制时带空格 | 检查 `.env` 里的 `LLM_API_KEY` |
| 404 模型不存在 | 地址和模型名不匹配 | 对照 `.env.example` 里的平台对照表 |
| 429 限流 / 余额不足 | 请求太快或账户没钱 | 等几秒重试；少选几种卡片；检查余额 |
| 400 请求被拒绝 | 材料太长，或平台不支持 JSON 模式 | 调小 `MAX_CHARS`；把 `JSON_MODE` 改成 false |
| 某个 Tab 显示"JSON 格式不合法" | 模型偶尔没按格式输出 | 再点一次生成；或把 `TEMPERATURE` 调到 0.5 |
| 界面打开是空白 | 浏览器缓存了旧页面 | `Ctrl + F5` 强制刷新 |
| 端口被占用 | 7861 被别的程序占了 | 看终端实际打印的地址，用那个 URL |

---

## 提交前检查（很重要）

- [ ] **`.env` 不要提交**（里面有你的 Key）；仓库里只留 `.env.example`
- [ ] **`.venv/` 不要提交**（每个人电脑上不一样，装依赖即可）
- [ ] `.gitignore` 已经排除了 `.env`、`.venv/`、`exports/`、`.idea/`
- [ ] 截图 `docs/ui-home.png` 可以提交
- [ ] 答辩材料在 `答辩/`：PPT + 6 分钟讲稿

---

## 说明

- 本项目用于课程作业演示，API Key 与调用费用由使用者自行承担。
- 换模型只改 `.env` 里的 `LLM_MODEL`，代码一行不用动。
