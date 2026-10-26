# 怎么把这个作品集放到 GitHub（两种方法，选一种）

> 你现在的文件夹 `github-portfolio` 已经是**干净可上传**的状态：
> 已剔除 `.venv`（几百 MB）、`__pycache__`、`.idea`、`env`（JDK）、`target`、**还有所有 `.env` 密钥文件**。

---

## 方法 A：网页拖拽上传（0 安装，10 分钟搞定，推荐先用这个）

1. 打开 <https://github.com/new>
2. **Repository name** 填：`ai-llm-portfolio`
3. 选 **Public**（简历链接别人要能打开），**不要**勾选 "Add a README file"
4. 点 **Create repository**
5. 页面中间点 **"uploading an existing file"**
6. 打开电脑上的 `C:\Users\cgc\Desktop\个人\github-portfolio`
7. **先拖** 这 7 个文件/文件夹进去：`README.md`、`01-ai-writing-assistant`、`02-ai-study-cards`、`03-ai-translator`
8. 点 **Commit changes**
9. 再点 **Add file → Upload files**，把 `04-student-grade-system` 拖进去，再提交一次

> ⚠️ 网页一次最多上传 **100 个文件**，所以分 2 次拖。
> ⚠️ 拖之前确认电脑的「查看 → 显示隐藏文件」里没有带 `.env` 的——本文件夹里已经没有了，放心。

---

## 方法 B：装 Git 用命令行推送（以后改代码更方便）

1. 装 Git：<https://git-scm.com/download/win>（一路默认下一步）
2. 在 GitHub 网页新建**空仓库** `ai-llm-portfolio`（同样不要勾选 README）
3. 在 `github-portfolio` 文件夹里右键 →「在终端中打开」→ 执行：

```powershell
.\push-to-github.ps1 -GitHubUser 你的用户名
```

4. 第一次推送会弹浏览器让你登录 GitHub，登录后自动推送完成
5. 以后每次改了代码，只要再跑一次这个脚本就行（也可以单独 `git add . ; git commit -m "改了什么" ; git push`）

---

## 推完自检清单

打开 `https://github.com/你的用户名/ai-llm-portfolio`，确认：

- [ ] 首页 README 正常显示，3 张截图能看到
- [ ] `01` ~ `04` 四个项目文件夹都在
- [ ] 点进任意项目，能看到代码文件和它自己的 README
- [ ] **全局搜索 `api_key` / `sk-`，确认没有真实密钥**
- [ ] 简历上写的链接能直接打开（无痕窗口试一下）

---

## 关于你原来的 Key（重要）

你的 `study-cards-project\.env` 里有真实 API Key，**这次没有上传**。
但为了保险，去对应的平台（智谱 / DeepSeek 等）**重新生成一个 Key、把旧的删掉**，花 1 分钟，能避免以后误提交。

---

## 现在还没做的一步

简历里要写 `github.com/你的用户名/ai-llm-portfolio`，我需要你的**GitHub 用户名**才能填进去。
你找到后发给我，我 1 分钟内把两个版本的简历都更新好。
