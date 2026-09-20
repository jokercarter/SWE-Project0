# Joker Carter · SWE + AI workbench

本地全栈学习工作台：公开作品集 + 12 周课程 + Jupyter Notebook + 文档知识库 + 本机 Codex。React/TypeScript/Vite 前端，FastAPI/SQLAlchemy/SQLite 后端。尚未绑定域名或发布公网。

## 启动

Windows，Node.js 22+、Python 3.13。已安装依赖的当前电脑：

```powershell
.\start.ps1
```

首次安装或重建隔离环境：

```powershell
.\start.ps1 -Install
```

访问 [工作台](http://127.0.0.1:4173/app/) 或 [首页](http://127.0.0.1:4173/)。第一次访问由你设置管理员用户名和至少 12 位密码；没有默认密码、没有公众注册。测试账号只存在于独立临时数据库。

启动器构建网站、运行 Alembic 迁移，然后隐藏运行本地服务。日志在 `.workbench/server.log`、`.workbench/server-error.log`，PID 在 `.workbench/server.pid`。端口占用会明确报错，不会自动杀掉其他程序。停止：

```powershell
.\stop.ps1
```

前台调试：`npm run build`，再 `npm start`。修改后端需要重启；修改前端需要重新 build。`requirements.lock.txt` 与 `package-lock.json` 锁定依赖；PyTorch 使用 CPU wheel，避免原先 Anaconda 的 OpenMP 冲突。不要使用 `KMP_DUPLICATE_LIB_OK` 掩盖依赖问题。

## 使用地图

| 页面 | 功能 |
|---|---|
| `/app/dashboard` | 真实章节进度、记录学习时长、到期提醒和操作记录 |
| `/app/courses` | 12 周中英文路线、48 个章节检查、PDF、复习日期和 Notebook |
| `/app/tasks` | 创建/编辑/删除、列表/看板、状态、优先级、标签、日期、搜索和筛选 |
| `/app/notes` | Markdown 编辑预览、自动保存、课程关联与复习日期 |
| `/app/notebooks?week=01` | 12 个 ipynb，代码/Markdown 单元、排序、增删、运行、停止、重启、图表、保存和导入导出 |
| `/app/documents` | PDF/MD/TXT 解析、去重、全文搜索、页码、阅读和关联 |
| `/app/ai` | 本机 Codex 连接状态、独立聊天、多轮、流式、停止、历史、选中来源预览和引用 |
| `/app/applications` | 公司岗位、申请阶段、截止时间、面试安排、复盘、CSV 导入导出 |
| `/app/projects`, `/app/articles` | 草稿、编辑预览、发布、撤回；项目另有 Planned/Completed 状态 |
| `/app/materials`, `/app/profile` | 发布课程资料链接、个人介绍、联系邮箱、GitHub、简历链接 |
| `/app/settings` | 数据备份、恢复预览、确认合并、旧浏览器进度迁移 |
| `/portfolio/`, `/blog/` | 只显示已发布的项目/文章，搜索、详情、图表与测试证据 |

原有 `/`、`/projects/`、`/about/`、`/learning/`、`/learning/code/`、`/projects/pathfinder/` 以及 12 个 PDF 地址保留。旧代码页的运行按钮现在进入认证后的 Notebook，原 `/api/run-python` 任意执行分支已删除。

项目架构字段支持 Mermaid，例如：

```text
flowchart LR
  Browser --> FastAPI
  FastAPI --> SQLite
  FastAPI --> Codex
```

代码、日志、用户笔记不会因为切换界面语言而被机器翻译或覆盖。界面有中文/英文和深浅主题；课程路线双语，教学代码的解释与注释以中文为主，保留英文技术词。

## Notebook 学习内容

源码在 `notebooks/week-01.ipynb` 到 `week-12.ipynb`，生成器 `tools/generate_notebooks.py` 可重新生成**课程模板**，不会覆盖数据库里的个人编辑。每周包括原理解释、带注释主体实现、独立练习、参考实现与断言。先尝试练习，再读答案。

1. Python 工程、类型、异常、JSON/CSV、Todo 仓储与 Git。
2. FastAPI、Pydantic、CRUD、HTTP 状态与真实接口测试。
3. SQLAlchemy、主外键、JOIN、分页、索引、事务回滚和持久化。
4. Mock、unittest、Docker/Compose/CI 配置与交付边界。
5. NumPy/Pandas、公开数据集、Pipeline、交叉验证、模型比较和错误分析。
6. PyTorch 手写数字图像分类、训练/验证、曲线、checkpoint 和独立推理。
7. Attention 数值计算、向量归一化、TF-IDF/SVD 检索基线与搜索 API。
8. 来源保留、extractive QA 基线、拒答、历史与 30 道合成回归题。
9. 分层接口、AsyncMock、超时、有限重试、上传校验、日志脱敏。
10. TTL 缓存、身份隔离、异步队列、健康检查与架构。
11. README、证据审计、英文 bullet 与 STAR 草稿。
12. BFS 边界、Python 常见问题、申请 CSV 与模拟面试追踪。

这些是可运行教学实验，不会替你完成真实 GitHub CI、云部署、简历事实填写或求职申请。第 7 周本地基线不是预训练 embedding 模型，第 8 周离线实验不是 LLM；真正的模型问答在 Codex 助手中。原 PDF 保留，未在这次将其重写为完整教材。阅读代码不等于掌握全部知识，需要独立练习与项目验收。

## 本机 Codex

参考 [官方 app-server 文档](https://developers.openai.com/codex/app-server)。后端通过 stdio JSON-RPC 管理独立子进程，沿用本机模型、服务商与可用认证。它不能接管当前桌面对话，不复制凭据，也不是离线模型。

在 Codex 助手搜索并勾选来源，查看片段和代码后发送。只发送当前问题、选中内容及该网站会话历史，不默认读取求职记录。来源编号经服务端核对；编号真实不等于答案一定正确，仍可点击文件页码检查证据。

如果显示 unavailable：在终端检查 `codex --version`、`codex app-server --help`，按 Codex 官方登录流程完成认证，再点击重新检查。不要把密码、API Key 或认证文件粘贴到网站。超时/服务错误不自动重放请求，避免额外操作或重复计费。

## 数据与恢复

所有私人数据保存在 `.workbench/workbench.db`，内核输出文件在 `.workbench/kernels/`。不要删除 `.workbench` 来升级。JSON 备份不含管理员密码、会话、Codex 凭据或内核输出文件。恢复会按 ID 合并并覆盖匹配记录，先导出一份当前备份。

旧 localStorage 进度需要预览后确认，只生成旧里程碑，不自动勾选新版章节。跨安装导入的 Codex 历史只读，须新建网站会话；不会借备份导入任意桌面会话。

## 验证

```powershell
npm run typecheck
.venv/Scripts/python -m pytest backend -q
.venv/Scripts/python tools/verify_notebooks.py
npx playwright test
.venv/Scripts/python tools/verify_live.py
```

最后一项会创建临时网站会话并调用真实本机 Codex，可能消耗当前服务额度；所有集成测试使用临时数据目录。测试报告和截图在 `output/`，详细记录见 [测试报告](docs/TESTING.md)。

架构、数据库和权限说明见 [ARCHITECTURE.md](docs/ARCHITECTURE.md)。Notebook 是管理员本地代码执行，不是恶意代码隔离环境；此服务保持仅本机访问，公开部署应把作品集与执行服务分离。
