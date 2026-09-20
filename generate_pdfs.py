from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether

ROOT = Path(__file__).parent
OUT = ROOT / 'public' / 'pdfs'
OUT.mkdir(parents=True, exist_ok=True)

FONT = 'MicrosoftYahei'
try:
    pdfmetrics.registerFont(TTFont(FONT, r'C:\Windows\Fonts\msyh.ttc'))
except Exception:
    FONT = 'Helvetica'

weeks = [
('01', 'Python 工程化、Git 与命令行', 'Python engineering, Git & command line',
 '建立可维护 Python 项目的基础：环境隔离、文件与配置、错误处理、命令行界面和 Git 协作。',
 ['虚拟环境、pip、requirements.txt 与可复现安装', '项目目录、模块导入、类型注解和函数边界', '异常类型、错误信息、文件读写、JSON/CSV 和 UTF-8', 'PowerShell/Linux 的路径、进程、管道和退出码', 'git status/diff/add/commit/log、分支、合并、.gitignore'],
 '开发一个 JSON 文件版命令行 Todo 应用：新增、列表、搜索、完成、删除；处理文件不存在、JSON 损坏、重复 ID 和非法输入。每完成一个垂直功能就提交一次。',
 'README、依赖清单、示例数据、运行说明、至少 5 次有意义提交；程序可以从新目录安装后运行。',
 ['创建 venv 并激活，确认 python 与 pip 指向虚拟环境。', '用 argparse 或标准库实现清晰的子命令和 --help。', '为 JSON 读写封装函数，写入时使用临时文件或明确处理失败。', '写 5 个手工测试场景并记录预期与实际结果。', '检查 git diff，确认没有提交虚拟环境、密钥和生成文件。']),
('02', 'HTTP、REST API 与 FastAPI', 'HTTP, REST APIs & FastAPI',
 '理解浏览器如何调用后端，并把命令行程序升级为可测试的 HTTP 服务。',
 ['客户端/服务器、请求/响应、URL、路径参数和查询参数', 'GET/POST/PUT/PATCH/DELETE 与幂等性', '状态码、请求头、JSON body、Content-Type 和错误响应', 'FastAPI 路由、Pydantic 字段约束、依赖与自动 OpenAPI 文档', 'pytest、TestClient、fixture 和测试隔离'],
 '实现任务管理 API：创建、列表、详情、更新、删除；为不存在任务、非法字段、空标题、错误类型设计稳定响应。',
 'API 文档、请求/响应示例、参数验证、错误处理和至少 5 个接口测试。',
 ['用 curl 或 Swagger 逐个发送请求并记录响应状态。', '区分 400、404、409 和 422 的使用场景。', '将业务逻辑从路由函数中抽出，避免所有逻辑堆在 endpoint 内。', '测试重复调用 PUT/DELETE 的行为。', '运行 pytest 两次，确认测试不依赖执行顺序。']),
('03', 'SQL、数据库与 ORM', 'SQL, databases & ORM',
 '从文件存储过渡到持久化数据系统，理解关系、查询、索引和事务。',
 ['表/行/列、主键、外键、NOT NULL、UNIQUE 与一对多关系', 'SELECT、WHERE、ORDER BY、LIMIT、JOIN、GROUP BY 和聚合', '索引的查询收益、写入成本和选择性', '事务、提交、回滚、隔离的直观含义', 'SQLite、PostgreSQL、SQLAlchemy Session、模型和迁移'],
 '将任务 API 的存储改为数据库，加入 users 与 tasks 表、任务归属、分页、筛选和排序；实现一个 JOIN 查询并练习失败事务回滚。',
 'ER/关系图、初始化和迁移步骤、分页接口、筛选排序和 JOIN 示例。',
 ['先手写 SQL，再用 SQLAlchemy 对照生成查询。', '为 user_id、状态和创建时间思考索引，而不是盲目加索引。', '测试外键约束和删除用户时的行为。', '模拟异常后确认事务没有留下半条数据。', '重启服务并检查数据仍存在。']),
('04', 'Docker、测试与持续集成', 'Docker, testing & CI',
 '把本地服务整理成可以被别人启动、测试和持续检查的项目。',
 ['镜像、容器、层、Dockerfile、端口、volume 与网络', 'Docker Compose 服务、依赖、环境变量和健康检查', '单元测试、集成测试、测试数据库和日志', '配置分离、.env.example、密钥不入库', 'GitHub Actions 的触发、依赖安装和测试步骤'],
 '完成 Production-style Task Management API：FastAPI + PostgreSQL + SQLAlchemy + pytest + Docker Compose，并让 CI 自动运行测试。',
 'Dockerfile、Compose、测试套件、CI 工作流、健康检查和新开发者可执行的 README。',
 ['先在本地用 compose up --build 完整启动。', '验证容器重启后 volume 中的数据不丢。', '为健康检查、数据库连接失败和 CRUD 写集成测试。', '检查日志中不出现密码、token 或完整请求敏感内容。', '记录 CI 的真实运行链接；本地通过不能冒充 CI 通过。']),
('05', '机器学习基础', 'Machine-learning foundations',
 '能够从数据、指标和错误样本解释一个传统机器学习实验，而不是只调用 fit。',
 ['NumPy shape、索引、广播；Pandas 清洗、缺失值、编码和统计', '特征/标签、训练验证测试、baseline、分类与回归', '过拟合、欠拟合、数据泄漏和 Pipeline', 'Accuracy、Precision、Recall、F1、混淆矩阵', '交叉验证、随机种子、模型比较与错误分析'],
 '选择公开表格数据集，用 scikit-learn 完成清洗、baseline、两个模型比较和错误样本分析。所有预处理只在训练集拟合。',
 '数据来源和许可、可复现实验 notebook、模型比较表、混淆矩阵和错误分析。',
 ['先写任务定义和成功指标，再选模型。', '检查类别分布，解释为什么准确率可能误导。', '用 Pipeline 防止缩放或编码造成泄漏。', '固定随机种子并记录 Python/库版本。', '挑选至少 5 个错分样本，说明模型为何可能犯错。']),
('06', 'PyTorch 与神经网络', 'PyTorch & neural networks',
 '理解并能独立写出一个小型神经网络的训练、验证、保存和推理流程。',
 ['Tensor 的 shape、dtype、device 与批处理', 'Dataset、DataLoader、shuffle、batch size', '线性层、激活函数、损失函数和 logits', 'autograd、zero_grad/backward/step 与优化器', 'train/eval、no_grad、checkpoint、CPU/GPU 与过拟合'],
 '使用 Fashion-MNIST 完成小型 MLP 图像分类；记录训练/验证损失，保存最佳 checkpoint，编写独立推理脚本。无 GPU 时降低数据量和 epoch。',
 '训练曲线、配置文件、最佳权重、独立推理脚本和实验记录。',
 ['先用一个 batch 验证维度和 loss 能计算。', '检查训练模式与评估模式的差别。', '记录每轮训练时间、训练集和验证集指标。', '故意增大模型观察过拟合，并用 dropout/weight decay 做一次对比。', '重载 state_dict，确认推理结果可以复现。']),
('07', 'Transformer、Embedding 与模型 API', 'Transformers, embeddings & model APIs',
 '理解文本向量检索和模型 API 的工程边界，为 RAG 做准备。',
 ['token、上下文窗口和 attention 的直观作用', 'Transformer 和 tokenizer 的基本职责', 'embedding、向量维度、归一化和余弦相似度', 'Hugging Face 模型卡、输入输出和许可', 'API 超时、重试、结构化输出、限流和成本预算'],
 '将 Markdown/TXT 按段落切分并保留来源，生成 embedding，计算 top-k 语义搜索结果；用 FastAPI 提供接口并和关键词搜索比较。',
 '搜索 API、切分策略、10 个示例问题、失败检索记录和环境变量配置。',
 ['手算两个短向量的点积/余弦相似度，理解相似度含义。', '对同一文档比较不同 chunk 大小的结果。', '给外部 API 增加有限次数重试和超时。', '对模型返回做 schema 验证，错误时返回可理解信息。', '记录每次请求的 token/耗时/费用字段（没有真实费用就标记未测）。']),
('08', 'RAG 文档问答系统', 'RAG document Q&A',
 '把文档解析、检索、生成和引用连成一个可评测的应用。',
 ['上传→解析→chunk→embedding→检索→上下文→生成→引用数据流', 'PDF 页码、Markdown 段落、重复文件和解析失败', 'top-k、上下文长度、来源映射和 prompt 边界', '幻觉、拒答、证据支持与“有引用但答错”', '评测集、检索命中、回答正确和引用正确的区别'],
 '完成带文件上传、问答、来源页码和历史记录的 Document Q&A；为可回答、无答案和干扰问题建立 30 题评测集。',
 'FastAPI、简单网页、Docker、评测表；每个回答展示文件和页码；无证据时明确拒答。',
 ['先用 3 个小文档走通端到端数据流。', '保留每个 chunk 的 source_id、文件名和页码。', '测试重复上传、空文件、解析异常和超大文件。', '检查答案中的每个关键结论是否被引用片段支持。', '记录 top-k、chunk 大小和回答错误，形成下一轮改进清单。']),
('09', '软件质量、可靠性与维护', 'Quality, reliability & maintainability',
 '把能工作的 RAG 原型重构为更容易测试、排错和维护的服务。',
 ['API、service、retrieval、storage、configuration 分层', '依赖注入、mock、单元测试和集成测试边界', '日志级别、请求 ID、错误映射和敏感信息保护', 'async/await 与阻塞调用、超时和有限重试', '文件类型/大小限制、配置和密钥管理'],
 '抽出模型客户端、检索服务、存储适配器和配置；用 mock 模拟超时、限流、无效输出；完善上传检查。',
 '模块结构图、核心测试、结构化日志、配置样例、错误响应和上传限制。',
 ['画出请求经过的模块和依赖方向。', '为模型客户端写成功、超时、限流和格式错误测试。', '检查异常日志不包含 API key、完整 prompt 或用户私密文档。', '确认同步 SDK 不在 async endpoint 中阻塞事件循环。', '运行静态检查和测试，记录已知限制。']),
('10', '部署与基础系统设计', 'Deployment & basic system design',
 '理解一个 AI 应用从本地进程到可访问服务的组件和风险。',
 ['服务器、容器、反向代理、DNS、HTTPS、健康检查', '数据库连接、持久化、备份和重启恢复', '缓存、队列、后台任务和同步/异步选择', '并发、延迟、模型限额、成本和扩展瓶颈', '架构图、日志、环境变量和最小暴露端口'],
 '先完成本地部署演练和健康检查，再选择托管环境部署 RAG Demo；写请求流架构图和部署文档。',
 '可访问 Demo（真实部署后再填写）、部署说明、架构图和 2–3 分钟演示视频。',
 ['画出浏览器→后端→数据库/向量检索→模型的流程。', '测试服务重启、健康检查、模型超时和数据库不可用。', '配置 HTTPS 和最小开放端口；不要把开发服务器直接暴露公网。', '为模型接口设置速率/费用限制。', '在 README 标记实际测试日期、环境和未验证部分。']),
('11', '作品集、英文简历与项目表达', 'Portfolio, résumé & project storytelling',
 '把技术学习转化为招聘者可验证、可快速理解的证据。',
 ['README 的问题、功能、架构、启动、测试和限制', '截图、架构图、技术选型和真实指标', '英文项目 bullet 的行动、方法、结果', 'STAR 行为故事和项目 2/8 分钟讲解', '区分自己完成、课程要求和 AI 辅助内容'],
 '整理 Task API 和 RAG 两个仓库；补齐 README、截图、架构图、测试和评测；制作一页英文简历、Profile 和演示视频。',
 '两个完整仓库、一页英文简历、GitHub Profile、项目截图、架构图和演示视频。',
 ['从新目录按 README 运行一次。', '给每个项目写“问题→决策→结果→限制→下一步”。', '所有数字都附测试条件和日期，不编造性能。', '准备 60 秒介绍、2 分钟概览和 8 分钟深讲。', '审查链接、拼写、密钥和计划项目状态。']),
('12', '面试、模拟与集中申请', 'Interviews, mocks & applications',
 '把算法、工程、AI 和行为题组织成可复用的面试准备系统。',
 ['Python 容器、迭代器/生成器、异常、类型注解、异步', 'HTTP/REST、SQL JOIN/索引/事务、缓存', 'embedding、RAG、评测、幻觉和系统设计', '数组、哈希、链表、树、图、基础 DP 与复杂度', 'STAR、项目失败案例、扩展思路和岗位匹配'],
 '完成算法、项目讲解、AI 基础和行为四类模拟；每次记录不会的问题并复盘；准备岗位定制简历和申请追踪表。',
 '60 秒自我介绍、项目 2/8 分钟讲稿、模拟记录、复盘清单、定制简历和申请表。',
 ['每周至少一次计时算法题并口述复杂度。', '模拟解释 RAG 的数据流、失败模式和评测。', '回答“如果流量增加 100 倍，哪里先出问题”。', '完成至少 4 次模拟并记录改进前后。', '目标约 20 个高匹配申请；记录岗位、链接、日期、状态和下一步。'])
]

styles = getSampleStyleSheet()
title = ParagraphStyle('TitleCN', parent=styles['Title'], fontName=FONT, fontSize=25, leading=32, textColor=colors.HexColor('#173f35'), alignment=TA_CENTER, spaceAfter=10)
subtitle = ParagraphStyle('SubtitleCN', parent=styles['Normal'], fontName=FONT, fontSize=11, leading=17, textColor=colors.HexColor('#66716a'), alignment=TA_CENTER, spaceAfter=20)
h1 = ParagraphStyle('H1CN', parent=styles['Heading1'], fontName=FONT, fontSize=17, leading=24, textColor=colors.HexColor('#173f35'), spaceBefore=18, spaceAfter=9)
h2 = ParagraphStyle('H2CN', parent=styles['Heading2'], fontName=FONT, fontSize=12, leading=18, textColor=colors.HexColor('#557948'), spaceBefore=13, spaceAfter=5)
body = ParagraphStyle('BodyCN', parent=styles['BodyText'], fontName=FONT, fontSize=10.5, leading=18, textColor=colors.HexColor('#29352f'), spaceAfter=8)
small = ParagraphStyle('SmallCN', parent=styles['BodyText'], fontName=FONT, fontSize=8.5, leading=13, textColor=colors.HexColor('#66716a'))
bullet = ParagraphStyle('BulletCN', parent=body, leftIndent=14, firstLineIndent=-9, bulletIndent=0, spaceAfter=4)
check = ParagraphStyle('CheckCN', parent=body, leftIndent=17, firstLineIndent=-17, spaceAfter=5)

def p(text, style=body):
    return Paragraph(text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), style)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#d9ddd3'))
    canvas.line(18*mm, 14*mm, 192*mm, 14*mm)
    canvas.setFont(FONT, 8)
    canvas.setFillColor(colors.HexColor('#66716a'))
    canvas.drawString(18*mm, 8.5*mm, 'Joker Carter · SWE + AI learning roadmap')
    canvas.drawRightString(192*mm, 8.5*mm, f'Page {doc.page}')
    canvas.restoreState()

deep = {
'01': ['虚拟环境解决的是“同一台电脑上不同项目需要不同依赖版本”的问题。激活环境后，python 与 pip 都应指向环境目录；requirements.txt 记录的是项目依赖，不是 Python 本身。一个可复现流程是：创建环境、激活、安装、冻结版本、运行、退出。若 pip 安装成功但运行时找不到包，先检查解释器路径，而不是重复安装。', 'Git 的对象模型可以先理解为：工作区是你正在编辑的文件，暂存区是你准备提交的快照，提交是带作者、时间和父提交的不可变记录。一个好提交只完成一个可解释变化。分支只是移动到提交的指针；合并会把两个历史连接起来。', 'JSON 适合保存结构化的小数据，但写文件时如果进程中断，可能留下半个文件。可以先写临时文件，成功后替换原文件，并捕获 JSONDecodeError。Todo 的核心不在命令行，而在数据不变量：每条任务有唯一 id、标题、完成状态和创建时间。'],
'02': ['HTTP 请求由方法、目标 URL、请求头和可选 body 组成；响应由状态码、响应头和 body 组成。GET 应读取资源，POST 通常创建资源，PUT 表示用新表示替换，PATCH 做部分更新，DELETE 删除。状态码不是装饰：404 表示资源不存在，422 常表示输入校验失败，500 才是服务器未处理的错误。', 'FastAPI 路由只是入口，Pydantic 模型负责把不可信 JSON 转为受约束的 Python 对象。请求验证应在边界完成，业务层接收已经验证的数据。测试不应只断言 200，还要断言返回 JSON 的字段、错误状态和数据库/存储状态。', '一个安全的任务创建流程是：解析 body→验证标题非空和长度→生成 id→保存→返回 201。若保存失败，不应返回“创建成功”。详情接口查不到 id 时返回 404；更新接口应明确“缺少字段”和“字段值非法”的区别。'],
'03': ['关系数据库用表表达实体，用外键表达关系。tasks.user_id 不是普通数字，而是指向 users.id 的约束；它能阻止不存在的用户拥有任务。JOIN 的本质是按照键把两张表的行组合起来。分页必须有稳定排序，否则新增数据会导致用户翻页时重复或漏项。', '索引像目录：数据库可以少扫描数据，但要维护额外结构，所以不是越多越好。常见查询是 WHERE user_id=? ORDER BY created_at DESC，因此可以思考联合索引。事务把多个修改包成一个原子操作：全部成功提交，任何一步失败都回滚。', 'SQLAlchemy Session 管理一次数据库工作单元。提交前对象可能只在内存中；提交后才持久化。不要把一个全局 Session 复用给所有请求。迁移文件是数据库结构的历史，直接改模型不会自动修改已有数据库。'],
'04': ['镜像是构建产物，容器是运行实例；Dockerfile 描述如何构建，Compose 描述多个服务如何一起运行。容器删除后其中可写层可能消失，数据库必须使用 volume。端口映射的左边是主机端口，右边是容器内监听端口。', '测试金字塔的底部是快速、隔离的单元测试，上面是连接真实数据库的集成测试。一个测试失败时应能判断是业务逻辑、数据库、环境还是网络。CI 的价值是让干净机器重复安装依赖并执行测试，而不是把本地成功截图上传。', '配置要通过环境变量注入，.env.example 只放变量名和示例值。健康检查应检查服务是否真的能工作，例如能否建立数据库连接，而不是只返回一个静态字符串。日志要帮助定位问题，但不能泄露密码和 token。'],
'05': ['训练/测试划分模拟“用已知数据学习、用未见数据考试”。如果先用全量数据做标准化再切分，测试集的信息已经泄漏。Pipeline 把预处理和模型绑定，使交叉验证的每一折只在训练部分拟合。', '混淆矩阵的四格分别是 TP、FP、FN、TN。Precision 关注预测为正的样本有多少真的为正，Recall 关注所有正样本有多少被找回。医疗筛查通常更重视 Recall，垃圾邮件过滤可能要平衡误杀。选择指标必须联系业务代价。', 'baseline 是最低参照线，不是可有可无的模型。比较模型时固定划分和随机种子，报告均值与波动；只报告最高一次分数会隐藏不稳定。错误分析要回到原始样本，检查标签噪声、少数类和特征缺失。'],
'06': ['PyTorch 训练循环的核心是：取 batch、前向计算 logits、计算 loss、清空旧梯度、反向传播、更新参数。训练阶段需要梯度和 dropout；验证阶段使用 eval() 和 no_grad()。忘记切换模式会让验证结果不稳定，忘记清空梯度会把多个 batch 的梯度累加。', 'Dataset 定义如何按索引取一个样本，DataLoader 负责批处理和打乱。模型输入 shape 必须和层的期望一致；分类交叉熵通常接收未经过 softmax 的 logits 和整数类别。保存 state_dict 比保存整个运行对象更容易迁移。', '过拟合是模型记住训练样本而不能泛化。先画训练/验证曲线，再决定减小模型、增加数据、加入正则化或提前停止。GPU 只是计算设备，不会自动让数据和模型都在 GPU；每个参与计算的 Tensor 必须位于兼容 device。'],
'07': ['tokenizer 把文本变成模型能处理的离散 id；上下文窗口限制一次请求可携带的 token 数。embedding 把文本映射到向量空间，向量距离只能表达训练模型学到的相似性，不等于事实正确。余弦相似度比较方向，常用于忽略向量长度差异。', '语义搜索流程是：切分文档→为每段保存 source metadata→生成向量→查询向量→计算相似度→按分数取 top-k。chunk 太小会丢失上下文，太大会混入无关内容；top-k 太小会漏证据，太大又会挤占生成上下文。', '外部模型 API 是不可靠依赖。必须设置连接和读取超时，重试只针对可恢复错误，并限制次数和退避；不应对无效请求无限重试。结构化输出仍需本地 schema 验证，API 返回“看起来像 JSON”不等于数据有效。'],
'08': ['RAG 把“知识查找”和“语言生成”拆开。检索器负责找证据，生成模型负责根据证据组织语言。检索不到正确片段时，模型即使说得流畅也可能是幻觉；因此 prompt 应要求只使用给定证据，并在证据不足时拒答。', 'chunk metadata 是引用可信度的基础：至少保存文档 id、文件名、页码/段落、原文偏移。评测要分开看 retrieval hit、answer correctness 和 citation support；一个答案有引用不代表引用支持它。', '上传文件是输入边界，必须限制大小和类型，处理解析失败、重复文件和空文档。历史记录要保存问题、答案、引用和时间，但不要默认保存不必要的敏感原文。先用 30 题小评测集找错误类型，再调整 chunk、top-k 或 prompt。'],
'09': ['分层架构的目标是让变化隔离：HTTP 层变化不应迫使检索算法重写，数据库变化不应改变业务规则。依赖注入让服务接收接口或对象，因此测试时可以注入 fake repository 和 fake model client。', '超时是资源边界，不是异常装饰。请求超过 deadline 后要停止等待；重试必须判断错误是否幂等和可恢复。async endpoint 里调用阻塞 SDK 会占住事件循环，应该使用异步客户端或把阻塞工作移出事件循环。', '日志应记录 request_id、路由、耗时、结果类别和错误类型；不应记录 API key、完整 prompt 或用户文档。上传限制、schema 验证和统一异常处理共同组成防线，不能只依赖前端检查。'],
'10': ['反向代理接收公网 HTTP/HTTPS，再把请求转给本机应用；它可以处理 TLS、静态文件、域名和访问日志。健康检查应区分进程活着和依赖可用。公网部署至少要限制 SSH、开放必要端口、更新系统并备份数据。', '缓存适合重复且可安全复用的结果；队列适合耗时任务和削峰。缓存失效是核心问题，不能把包含用户权限的数据无条件共享。后台任务失败要有重试、状态和告警，否则用户会看到“提交成功”却永远没有结果。', '扩展前先测量：请求延迟、错误率、模型耗时、数据库查询时间和成本。流量增加时可能先受模型速率限制，也可能先受数据库连接池限制。架构图要标出数据流、信任边界和持久化位置。'],
'11': ['README 的第一屏要让陌生人知道项目解决什么问题、如何运行和如何验证。技术栈列表不能代替架构解释；项目 bullet 应说明你做了什么、用了什么方法、结果如何，且数字必须可复现。', '项目讲解顺序可以是：问题→用户/输入→架构→关键决策→失败案例→测试/指标→限制→下一步。招聘者常追问“为什么不用另一个方案”，所以要准备成本、复杂度和风险的比较。', '简历不能把计划写成经历，也不能把 AI 生成的代码写成完全独立完成。可以说明自己负责的部分、遇到的问题、验证方式和已知限制；诚实边界本身也是工程能力。'],
'12': ['算法题先澄清输入、输出、约束和边界，再选择数据结构。哈希表换空间换时间，双指针利用顺序，BFS 保证无权图最短边数，动态规划需要定义状态、转移和初始值。复杂度必须和代码循环对应。', '项目面试要能从用户请求讲到数据存储和失败恢复；AI 面试要区分 token、embedding、检索、生成和评测。系统设计回答应先估算规模，再给最小架构，最后讨论瓶颈、缓存、队列、监控和安全。', '行为题用 STAR，但不要编造故事。准备一次真实的错误、一次取舍、一次协作和一次学习新技术的经历；说明行动、结果和反思。申请追踪表让你知道哪个岗位、哪版简历和哪次面试需要跟进。']
}

for wk, title_cn, title_en, intro, learn, build, ship, checks in weeks:
    path = OUT / f'week-{wk}.pdf'
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=17*mm, bottomMargin=20*mm, title=f'Week {wk} - {title_cn}', author='Joker Carter')
    # Fifteen deliberate textbook pages: concept, questions, answers, examples,
    # practice, solutions, and review. PageBreaks keep the PDF easy to navigate.
    pages = [
        ('本周导读 / Week overview', [intro, '本周目标：把主题从“知道名词”推进到“能解释、能实现、能验证”。请先通读，再按章节完成实验。']),
        ('知识地图 / Knowledge map', ['本周核心知识点：' + '；'.join(learn), '学习顺序：先建立最小概念模型，再阅读官方文档，随后写一个最小例子，最后把它接入本周项目。']),
        ('概念讲解 1 / Core concepts', [learn[0], '解释：它描述了本周系统中的基本对象、边界和输入输出。学习时要同时记录一个正常例子和一个失败例子。']),
        ('概念讲解 2 / Core concepts', [learn[1], '解释：把这个概念和项目中的一个函数、接口或数据结构对应起来。不要只抄 API；要说明为什么在这里需要它。']),
        ('概念讲解 3 / Core concepts', [learn[2], '解释：工程系统必须面对错误和不确定输入。设计时先问“错误在哪里被发现”，再问“用户看到什么响应”。']),
        ('关键问题 / Questions', [f'问题 1：{title_cn}最容易被初学者混淆的地方是什么？', '问题 2：如果输入为空、类型不对、服务不可用或数据重复，系统应如何表现？', '问题 3：怎样证明自己的实现确实有效，而不是只在一个示例上运行？']),
        ('问题解答 / Answers', ['解答：先给概念下可操作的定义，再用输入、处理、输出三段描述。边界情况必须成为测试，而不是等到演示时临时处理。', '解答：把失败划分为用户输入错误、外部依赖错误和程序缺陷；分别返回可理解提示、可重试响应或记录完整诊断。', '解答：使用独立测试、固定输入、可重复命令、日志和验收清单，避免只凭肉眼看一次输出。']),
        ('具体示例 / Worked example', [f'场景：{build}', '步骤 1：写出最小输入和预期输出；步骤 2：实现一条成功路径；步骤 3：加入一个失败输入；步骤 4：写测试或记录复现命令；步骤 5：提交代码并记录原因。', '示例分析：如果结果不符合预期，先定位是输入、状态、依赖还是断言问题，再做最小修复，不要同时改动多个模块。']),
        ('代码/流程示例 / Implementation example', ['伪代码：读取输入 → 验证输入 → 调用核心逻辑 → 保存或返回结果 → 记录可诊断日志。', '每一步都应有清晰的职责和可观察结果。核心逻辑尽量不直接依赖终端、网络或真实模型，这样可以用小测试替换外部依赖。', '请把伪代码翻译成你本周使用的语言和框架，并在 README 中放一个最小调用示例。']),
        ('动手实验 / Guided lab', [build, '实验要求：先建立最小版本，再分 3 次增加验证、错误处理和测试。每次运行都记录命令、输入、输出和耗时；每次修改都做一次 Git commit。']),
        ('练习题 / Exercises', [f'练习 1：用自己的话解释“{learn[0]}”并写一个最小例子。', f'练习 2：为项目设计 3 个正常输入、2 个边界输入和 2 个失败输入。', '练习 3：画出一次请求或程序运行的流程图，标明数据在哪里产生、改变和保存。', '练习 4：指出一个你会选择的替代方案，并比较它的成本、风险和适用范围。']),
        ('练习参考答案 / Model answers', ['答案思路：概念解释必须包含用途、输入输出和限制；最小例子只保留证明概念所需的代码。', '答案思路：正常输入验证主要功能，边界输入验证空值/极值/重复，失败输入验证错误响应和恢复方式。', '答案思路：流程图至少包含入口、验证、核心处理、持久化/返回和错误分支。', '答案思路：替代方案不能只写名称，要说明在当前项目规模下为什么选择或暂不选择。']),
        ('常见错误 / Failure modes', ['把“能运行一次”当成完成；忽略环境、版本、数据和随机性。', '把异常吞掉或返回模糊的“出错了”，让用户和开发者都无法处理。', '把业务逻辑、输入输出、数据库和外部 API 写在同一个超长函数里。', '为了通过一个样例硬编码结果，导致换输入就失败。', '把未测试、未部署或计划中的内容写成已完成成果。']),
        ('可交付成果 / Deliverables', [ship, '交付检查：源码可运行；README 可复现；测试或实验记录可核对；截图/日志不泄露密钥；所有性能和准确率数字都有测量条件。']),
        ('验收与复盘 / Check & reflection', ['逐项验收：' + '；'.join(checks), '完成后写下三个最重要概念、一个失败根因、一个保留的工程决策和一个下周问题。状态只有在证据齐全后才可勾选。'])
    ]
    story = []
    for index, (heading, paragraphs) in enumerate(pages):
        # Expand every teaching page with a definition, mechanism, example,
        # diagnostic question, and answer prompt. This keeps pages content-rich
        # instead of using whitespace to reach a page count.
        if index in (2, 3, 4):
            concept = learn[index - 2]
            paragraphs = paragraphs + [deep[wk][index - 2],
                f'具体判断：当输入改变、执行顺序改变或依赖不可用时，{concept}的结果会如何变化？请至少写出两个不同输入，并说明为什么结果不同。',
                f'小例子：为“成功、空输入、非法输入、重复操作、外部失败”各写一条记录。逐条记录预期行为、实际行为和证据；这比只展示一个成功截图更能证明理解。',
                '检查答案：如果你只能说“框架会自动处理”，说明还没有掌握。继续追问数据在哪里、哪一层负责验证、错误如何传播，以及怎样通过测试观察到它。'
            ]
        elif index == 5:
            paragraphs = paragraphs + [
                f'问题拆解：面对“{title_cn}”的题目，先画出对象和边界，再列出不变量。哪些值必须始终成立？哪些步骤可以重试？哪些错误必须立即停止？',
                '面试式追问：为什么这个方案比最简单的硬编码更可靠？时间/空间成本是什么？如果输入规模扩大十倍，哪一部分先成为瓶颈？',
                '学习要求：不要只看答案。先在纸上写出你的判断，再运行最小实验验证；若结果和预期不同，保留这个反例并解释原因。'
            ]
        elif index == 6:
            paragraphs = paragraphs + [
                '详细解答方法：先定义术语，再给出执行流程，最后说明边界情况。解答中应出现至少一个输入、一个中间状态和一个输出，而不是只有结论。',
                '如果答案涉及性能，请给出操作数量的增长趋势；如果涉及可靠性，请给出失败检测、恢复和再次运行的行为；如果涉及模型，请区分检索错误和生成错误。',
                '自测：遮住本页后，用两分钟向别人讲解；对方应能根据你的讲解写出一个最小测试。做不到时回到概念页补充。'
            ]
        elif index == 7:
            paragraphs = paragraphs + [
                f'逐步示例：围绕“{build}”，先构造最小输入。观察每一步的变量、数据结构和副作用；在关键节点打印或记录可诊断信息。',
                '变体一：把输入改为空值或极端值；变体二：让外部依赖返回错误；变体三：重复执行同一操作。比较三种情况下系统是否安全、可解释、可恢复。',
                '示例结论必须包含限制：这个示例证明了什么，没有证明什么，下一步需要怎样的测试或真实数据。'
            ]
        elif index == 8:
            paragraphs = paragraphs + [
                '实现时要区分“展示代码”和“生产代码”。展示代码帮助理解单个概念；生产代码还需要输入验证、错误处理、日志、测试、配置和可重复启动。',
                '建议先写接口契约：输入字段、输出字段、状态码/错误类型、持久化规则和超时。契约稳定后再选择具体库，避免让框架行为替代自己的设计。',
                '代码审查问题：这段逻辑能否单独测试？换成假的数据库或模型客户端是否仍能测试？异常是否会泄露密钥或用户内容？'
            ]
        elif index == 9:
            paragraphs = paragraphs + [
                '实验记录模板：日期、环境、命令、输入、预期、实际、日志、结论、下一步。只要有一个字段缺失，未来就很难解释为什么某次结果不同。',
                '完成最小版本后，故意制造一个错误并观察系统。可靠性学习的关键不是永远不出错，而是出错时能快速发现、清晰说明并安全恢复。',
                '完成实验后将结果写进 README 或学习日志，附上真实命令和截图，不要用“应该可以”替代证据。'
            ]
        elif index == 10:
            paragraphs = paragraphs + [
                '练习必须先独立完成。写出你的解法、复杂度和失败案例后，再对照参考答案。参考答案用于发现遗漏，不是替代思考。',
                '评分标准：概念准确 30%，示例可运行 25%，边界测试 20%，解释技术取舍 15%，记录和复现 10%。',
                '如果不会，记录“卡点类型”：术语不懂、流程不清、代码错误、环境问题或无法设计测试；不同卡点需要不同补救。'
            ]
        elif index == 11:
            paragraphs = paragraphs + [
                '参考答案不是唯一实现。判断答案质量时，检查它是否满足题目约束、是否处理边界、是否能被测试，以及是否解释了为什么这样选择。',
                '把参考答案改写成自己的版本：替换变量、数据、错误路径和测试；如果只能原样抄写，说明仍需回到概念和示例。',
                '最后写一个“我仍然不确定的地方”，下一周用实验、文档或面试题把它变成确定结论。'
            ]
        elif index == 12:
            paragraphs = paragraphs + [
                '错误分类：概念误解、边界遗漏、状态管理错误、依赖配置错误、并发/性能问题、测试假设错误。先分类再修复，避免盲目改代码。',
                '修复记录应包含复现步骤、根因、最小修复、回归测试和仍然存在的风险。没有回归测试的修复很容易在下一次改动中再次失败。'
            ]
        elif index == 13:
            paragraphs = paragraphs + [
                '交付物必须能被别人验证：源码、启动命令、依赖版本、测试命令、示例输入输出和已知限制缺一不可。只有截图而没有复现步骤，不能算完整交付。',
                '如果某项尚未完成，明确写 Planned / 计划中，并列出完成它所需的下一步。诚实的限制说明比虚构指标更能体现工程判断。'
            ]
        elif index == 14:
            paragraphs = paragraphs + [
                '复盘时不要只写“学到了很多”。写出一个具体前后对比：之前会犯什么错误，现在如何通过定义、示例、测试或日志避免它。',
                '把仍不熟练的点安排到下一周的第一项任务，并在下次复盘时检查是否真的解决。这样 PDF 才会变成可执行的学习系统，而不是一次性阅读材料。'
            ]
        if index in (2, 4, 6, 8, 10, 12, 14): story.append(PageBreak())
        if index == 0:
            story += [p(f'WEEK {wk}', small), Spacer(1, 5), p(title_cn, title), p(title_en, subtitle)]
        else:
            story += [p(f'WEEK {wk} · STUDY SECTION {index + 1:02d}', small)]
        story += [p(heading, h1)]
        story += [p(text, body) for text in paragraphs]
        if index == 1:
            story += [p('学习记录模板：概念 | 我的解释 | 最小例子 | 常见错误 | 参考链接 | 是否验证', h2)]
        if index in (5, 6, 10, 11):
            story += [Spacer(1, 12), p('请把答案写在自己的学习笔记中，再对照本页检查，不要只阅读答案。', small)]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f'Generated {len(weeks)} PDFs in {OUT}')
