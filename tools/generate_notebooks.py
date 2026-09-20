"""Rebuild editable teaching notebooks. Each code section is independently explained.
No network, API credentials, Docker daemon or external data is needed to Run All.
Deployment/cloud exercises are explicit follow-up work, never fabricated results.
"""
import json
from pathlib import Path
import nbformat as nb

ROOT=Path(__file__).resolve().parents[1]
LESSONS=[]
def lesson(title,concepts,code,exercise,solution):
    LESSONS.append((title,concepts,code,exercise,solution))

lesson('Python 工程化 / Engineering Python',
'''虚拟环境让一个项目的依赖版本不会污染另一个项目。Windows 用 `python -m venv .venv` 创建，`.venv/Scripts/python -m pip install ...` 安装；不要把虚拟环境提交到 Git。模块负责可复用逻辑，入口负责解析参数，数据目录保存运行时文件。类型注解帮助读者和静态检查工具，但不会自动阻止错误输入，所以边界仍要校验。

下面使用 dataclass 表达领域对象、pathlib 处理路径、JSON 保存数据、CSV 导出表格、argparse 解析命令。写入时先写临时文件再替换，避免半份 JSON；这只能提高单进程文件可靠性，不能替代多用户数据库事务。异常在能给出明确处理的地方捕获，损坏文件不应直接被空列表覆盖。

Git 工作区 → 暂存区 → 提交：`git diff` 检查修改，`git add 文件` 选择提交内容，`git commit -m "feat: persist tasks"` 记录快照。`git switch -c feature/todo` 建分支；合并冲突要读两边业务含义再修改，不是盲选一方。练习五次真实提交，不用脚本伪造历史。环境变量适合注入配置；密钥不写进源码或日志。''',
r'''# 所有输出放在本 Notebook 内核工作目录，重复运行不会破坏其他周数据。
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse, csv, json, os

@dataclass
class Task:
    id: int
    title: str
    done: bool = False

class JsonTasks:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[Task]:
        if not self.path.exists():
            return []
        # 不吞掉 JSONDecodeError，否则损坏的数据可能被静默覆盖。
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        return [Task(**row) for row in rows]

    def save(self, tasks: list[Task]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps([asdict(t) for t in tasks],
                                       ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def add(self, title: str) -> Task:
        title = title.strip()
        if not title:
            raise ValueError("标题不能为空")
        tasks = self.load()
        task = Task(max((t.id for t in tasks), default=0)+1, title)
        self.save(tasks+[task])
        return task

    def complete(self, identifier: int) -> None:
        tasks = self.load()
        target = next((t for t in tasks if t.id == identifier), None)
        if target is None:
            raise KeyError(identifier)
        target.done = True
        self.save(tasks)

# 用单独的演示文件确保每次执行可复现；真实 CLI 不应在启动时清空数据库。
repository = JsonTasks(Path("week01-demo/tasks.json"))
repository.save([])
parser = argparse.ArgumentParser()
parser.add_argument("title")
arguments = parser.parse_args(["学习 Git 与 JSON"])
created = repository.add(arguments.title)
repository.complete(created.id)
assert repository.load()[0].done
try:
    repository.add("  ")
except ValueError as error:
    print("预期的输入错误：", error)
with Path("week01-demo/tasks.csv").open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["id", "title", "done"])
    writer.writeheader()
    writer.writerows(asdict(t) for t in repository.load())
print("Python 环境：", os.environ.get("VIRTUAL_ENV", "由工作台显式选择解释器"))
print(repository.load())
''', '实现不区分大小写的搜索；保留 load 的损坏文件异常。增加删除功能并验证删除不存在 ID 的行为。',
r'''def search_tasks(repository, keyword):
    return [task for task in repository.load() if keyword.casefold() in task.title.casefold()]
assert len(search_tasks(repository, "git")) == 1
def delete_task(repository, identifier):
    tasks = repository.load()
    filtered = [task for task in tasks if task.id != identifier]
    if len(filtered) == len(tasks):
        raise KeyError(identifier)
    repository.save(filtered)
delete_task(repository, created.id)
assert repository.load() == []
print("搜索与删除验收通过")
''')

lesson('HTTP、REST 与 FastAPI',
'''浏览器是客户端，API 是服务器。HTTP 请求由方法、URL、头和可选请求体组成；响应由状态码、头和内容组成。GET 应只读取资源，POST 创建资源，PATCH 局部更新，DELETE 删除。201 表示已创建，204 表示成功且无响应体，404 表示目标不存在，422 表示输入不满足结构约束。错误不能总返回 200，否则调用者无法可靠判断失败。

FastAPI 路由将 HTTP 输入映射到函数。Pydantic 负责形状、类型和范围校验，不负责所有业务规则。`response_model` 限制响应字段，避免无意泄露内部数据。测试客户端在进程内执行真实路由与校验，不需要占用端口。内存字典只适合这周学习，进程重启就丢失；下一周迁移数据库。

pytest 的测试必须独立，fixture 可以为每个测试创建空存储；成功路径、边界和错误路径同样重要。不要用测试依赖执行顺序掩盖状态问题。运行 `uvicorn module:app` 后可以在 `/docs` 试 API；Notebook 中运行的是 TestClient，不会偷偷开启公网服务。''',
r'''from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)

class TaskPatch(BaseModel):
    done: bool

def make_api():
    app = FastAPI(title="Learning Task API")
    storage = {}

    @app.post("/tasks", status_code=201)
    def create_task(body: TaskCreate):
        if not body.title.strip():
            raise HTTPException(422, "Title cannot be blank")
        identifier = max(storage, default=0)+1
        storage[identifier] = {"id": identifier, "title": body.title, "done": False}
        return storage[identifier]

    @app.get("/tasks")
    def list_tasks(done: bool | None = None, limit: int = 20):
        if not 1 <= limit <= 100:
            raise HTTPException(422, "limit must be 1..100")
        return [t for t in storage.values() if done is None or t["done"] == done][:limit]

    @app.get("/tasks/{identifier}")
    def get_task(identifier: int):
        if identifier not in storage:
            raise HTTPException(404, "Task not found")
        return storage[identifier]

    @app.patch("/tasks/{identifier}")
    def patch_task(identifier: int, body: TaskPatch):
        task = get_task(identifier)
        task["done"] = body.done
        return task

    @app.delete("/tasks/{identifier}", status_code=204)
    def delete_task(identifier: int):
        get_task(identifier)
        del storage[identifier]
        return Response(status_code=204)

    return app

with TestClient(make_api()) as client:
    result = client.post("/tasks", json={"title": "Read HTTP docs"})
    assert result.status_code == 201
    identifier = result.json()["id"]
    assert client.get(f"/tasks/{identifier}").json()["done"] is False
    assert client.post("/tasks", json={"title": ""}).status_code == 422
    assert client.get("/tasks/999").status_code == 404
    assert client.patch(f"/tasks/{identifier}", json={"done": True}).json()["done"]
    assert len(client.get("/tasks?done=true").json()) == 1
    assert client.delete(f"/tasks/{identifier}").status_code == 204
    assert client.get(f"/tasks/{identifier}").status_code == 404
    print("8 个真实 HTTP 断言通过；OpenAPI 路径：", list(client.get("/openapi.json").json()["paths"]))
''','增加分页 offset，非法负数返回 422。练习为每项行为写独立 pytest 函数。解释 PATCH 和 PUT 的差别。',
r'''# 测试之间新建应用，确保存储隔离。
with TestClient(make_api()) as fresh_client:
    assert fresh_client.get("/tasks").json() == []
    assert fresh_client.get("/tasks?limit=0").status_code == 422
    assert fresh_client.post("/tasks", json={"title": " "}).status_code == 422
print("隔离、边界与空白输入测试通过")
''')

lesson('SQL、事务、索引与 SQLAlchemy',
'''关系数据库把数据组织为表；主键唯一标识一行，外键表达引用关系。一个用户有多个任务：users.id ← tasks.user_id。NOT NULL、UNIQUE、CHECK 和 FOREIGN KEY 是最后一道数据一致性约束，不能只靠页面校验。SQLite 默认可能不开外键，所以每条新连接显式设置 PRAGMA。

事务把一组修改作为一个整体：成功提交，失败回滚。例如转移任务与写审计日志必须同时成功。索引是额外的数据结构，能减少读取扫描，但需要空间并增加写入成本。用 EXPLAIN QUERY PLAN 检查实际执行计划；不要因为建了索引就假定每次查询都更快。分页必须有稳定排序，否则相同请求可能翻出重复/遗漏结果。

ORM 把 Python 对象映射到表，不能替你理解 SQL。Session 是工作单元，离开事务后要避免继续依赖懒加载。生产演进使用 Alembic 记录迁移；create_all 只创建缺失表，不是完整迁移工具。SQLite 与 PostgreSQL 的并发、类型和部署模型不同，上线之前要用真实目标数据库集成测试。''',
r'''from sqlalchemy import create_engine, event, ForeignKey, String, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))

engine = create_engine("sqlite:///week03-demo.db")
@event.listens_for(engine, "connect")
def constraints(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")
Base.metadata.create_all(engine)
# 只清理当前示例表的数据，使实验重复运行得到相同结果。
with engine.begin() as connection:
    connection.execute(text("DELETE FROM tasks"))
    connection.execute(text("DELETE FROM users"))
with Session(engine) as session, session.begin():
    user = User(name="Carter")
    session.add(user)
    session.flush()  # 获得主键，但此时事务尚未提交。
    session.add_all([Task(user_id=user.id, title=f"Task {i}") for i in range(8)])
with Session(engine) as session:
    query = select(Task.title, User.name).join(User).order_by(Task.id).offset(2).limit(3)
    print("JOIN + 稳定分页：", session.execute(query).all())
try:
    with Session(engine) as session, session.begin():
        session.add(User(name="RolledBack"))
        session.add(Task(user_id=999999, title="Invalid foreign key"))
except IntegrityError:
    print("外键错误导致整笔事务回滚")
with Session(engine) as session:
    assert session.scalar(select(User).where(User.name == "RolledBack")) is None
with engine.connect() as connection:
    print(connection.execute(text("EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE user_id=1")).all())
engine.dispose()
# 新建连接模拟服务重启后的重新读取，而不是依赖内存中的 ORM 对象。
reopened = create_engine("sqlite:///week03-demo.db")
with reopened.connect() as connection:
    assert connection.execute(text("SELECT count(*) FROM tasks")).scalar() == 8
print("持久化、JOIN、分页、回滚均通过")
''','写 GROUP BY 统计每个人的任务数；考虑没有任务的用户为什么需要 LEFT JOIN。',
r'''with reopened.connect() as connection:
    rows = connection.execute(text("SELECT users.name, count(tasks.id) FROM users LEFT JOIN tasks ON tasks.user_id=users.id GROUP BY users.id ORDER BY users.id")).all()
    print(rows)
    assert rows[0][1] == 8
reopened.dispose()
''')

lesson('测试、Docker 与持续集成',
'''单元测试聚焦小块纯业务逻辑；集成测试检验组件边界，例如 API 到数据库。Mock 应放在不稳定外部边界，不能把被测试的核心逻辑也替换成假的。日志服务于定位问题，不能记录密码、token 或完整隐私请求体。配置与代码分离，.env.example 只放示例，不放真实密钥。

Docker 镜像是可分发的文件系统和配置；容器是运行实例。COPY 的路径相对于构建上下文，.dockerignore 防止把密钥和大文件送入构建。容器内 127.0.0.1 指自身，Compose 服务之间用服务名通信。volume 让数据库数据跨容器重建存活。depends_on 不等于数据库立刻可用，需要健康检查或应用重连。

CI 每次提交自动装依赖、执行测试。下面生成可读的配置文件并在本机真实运行 unittest；生成 YAML 不是 GitHub Actions 已成功的证据。Docker 和 GitHub 流程需要你安装 Docker、连接仓库后再执行验证。''',
r'''from pathlib import Path
import unittest, logging, io, json
from unittest.mock import Mock

def create_task(title, repository):
    title = title.strip()
    if not title:
        raise ValueError("empty title")
    return repository.save({"title": title, "done": False})

class TaskTests(unittest.TestCase):
    def test_success(self):
        repository = Mock()
        repository.save.return_value = 42
        self.assertEqual(create_task("  learn CI ", repository), 42)
        repository.save.assert_called_once_with({"title":"learn CI", "done":False})
    def test_invalid_never_writes(self):
        repository = Mock()
        with self.assertRaises(ValueError): create_task(" ", repository)
        repository.save.assert_not_called()
    def test_storage_failure_propagates(self):
        repository = Mock()
        repository.save.side_effect = OSError("database unavailable")
        with self.assertRaises(OSError): create_task("test", repository)

output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TaskTests))
assert result.wasSuccessful()
print(output.getvalue())
folder = Path("week04-delivery"); folder.mkdir(exist_ok=True)
files = {
 "Dockerfile": "FROM python:3.13-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\",\"main:app\",\"--host\",\"0.0.0.0\",\"--port\",\"8000\"]\n",
 ".dockerignore": ".git\n.venv\n.env\n__pycache__\n",
 "compose.yaml": "services:\n  api:\n    build: .\n    ports: ['127.0.0.1:8000:8000']\n    environment:\n      DATABASE_URL: postgresql+psycopg://app:example@db/app\n    depends_on:\n      db:\n        condition: service_healthy\n  db:\n    image: postgres:17\n    environment:\n      POSTGRES_USER: app\n      POSTGRES_PASSWORD: example\n      POSTGRES_DB: app\n    volumes: ['dbdata:/var/lib/postgresql/data']\n    healthcheck:\n      test: ['CMD-SHELL', 'pg_isready -U app']\n      interval: 5s\n      retries: 10\nvolumes:\n  dbdata:\n",
 "ci.yml": "name: tests\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.13'\n      - run: pip install -r requirements.txt\n      - run: python -m pytest -q\n",
}
for name, content in files.items():
    (folder/name).write_text(content, encoding="utf-8")
    print("配置草稿：", name)
print(json.dumps({"event":"unit_tests_completed", "count":result.testsRun}))
''','把 Week 02 API 放入生成目录；补 requirements.txt 和健康检查，然后执行 docker compose up --build。不要把示例数据库密码用于公网。',
r'''# 配置静态检查只证明所需字段存在，不能冒充容器运行成功。
assert "127.0.0.1:8000:8000" in files["compose.yaml"]
assert ".env" in files[".dockerignore"]
print("本地单元测试真实通过；Docker/云端 CI 仍需实际运行验收。")
''')

lesson('机器学习：数据划分与可靠评测',
'''监督学习从特征 X 预测标签 y。分类预测离散类别，回归预测连续值。训练集用于拟合参数，验证集或交叉验证用于选择配置，测试集用于最后一次评估。提前用完整数据拟合标准化器会泄露测试分布；Pipeline 可以把预处理放进每个交叉验证折内部。

Accuracy=正确数/总数；Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1 是 Precision 与 Recall 的调和平均。少数类重要时高准确率可能只是一直猜多数类。欠拟合表现为训练和验证都差；过拟合常表现为训练好但验证差。随机种子控制部分随机性，不保证跨硬件逐位一致。

下面使用 sklearn 自带乳腺癌数据（公开 Wisconsin Diagnostic Breast Cancer 数据集），比较 Dummy、逻辑回归和决策树。类 0=malignant、1=benign，因此如果关注恶性病例，Recall 的 pos_label 要设 0，不能机械使用默认正类。错误分析应看真实误判、特征分布和样本来源，不能用测试集反复调参。''',
r'''import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

dataset = load_breast_cancer(as_frame=True)
X, y = dataset.data, dataset.target
assert X.isna().sum().sum() == 0
print("样本数、特征数：", X.shape, "类别比例：", y.value_counts(normalize=True).to_dict())
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, stratify=y, random_state=42)
models = {
    "majority baseline": DummyClassifier(strategy="most_frequent"),
    "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "tree": DecisionTreeClassifier(max_depth=4, random_state=42),
}
rows=[]
for name, model in models.items():
    cv = cross_val_score(model, X_train, y_train, cv=5, scoring="f1_macro")
    model.fit(X_train, y_train)
    prediction=model.predict(X_test)
    rows.append({"model":name,"cv_f1_macro":cv.mean(),"accuracy":accuracy_score(y_test,prediction),
                 "malignant_precision":precision_score(y_test,prediction,pos_label=0,zero_division=0),
                 "malignant_recall":recall_score(y_test,prediction,pos_label=0),
                 "f1_macro":f1_score(y_test,prediction,average="macro")})
results=pd.DataFrame(rows)
display(results)
prediction=models["logistic"].predict(X_test)
print("混淆矩阵，行=真实、列=预测：\n",confusion_matrix(y_test,prediction))
errors=X_test.loc[prediction!=y_test].copy()
errors["true"]=y_test.loc[errors.index]
errors["predicted"]=prediction[prediction!=y_test]
display(errors.head(5))
results.to_csv("week05-metrics.csv",index=False)
assert set(X_train.index).isdisjoint(X_test.index)
''','把 max_depth 从 1 改成 None，仅在训练集交叉验证中选择；解释 precision 和 recall 的业务取舍。',
r'''depth_scores={depth:cross_val_score(DecisionTreeClassifier(max_depth=depth,random_state=42),X_train,y_train,cv=5,scoring="f1_macro").mean() for depth in [1,2,4,8,None]}
print("只用训练集 CV 选择深度：",depth_scores)
print("最佳深度：",max(depth_scores,key=depth_scores.get))
''')

lesson('PyTorch：训练、验证与独立推理',
'''Tensor 有 shape、dtype、device。线性层接收 [batch, features]，输出 [batch, classes]。CrossEntropyLoss 接收原始 logits 和整数类别，不要先做 softmax 再传入；它内部完成稳定的 log-softmax。反向传播计算梯度，optimizer.step 更新参数，zero_grad 清除旧梯度；漏掉清零会意外累积。

train() 与 eval() 改变 Dropout/BatchNorm 行为，不会关闭梯度。no_grad() 关闭梯度记录，降低推理内存。Dataset 描述样本，DataLoader 负责批处理和打乱；验证集不用于反向更新。保存验证损失最低的 state_dict，加载到同样结构的模型。

为保证本地立即运行，使用 sklearn 自带 8×8 手写数字图像，CPU 训练小型 MLP，不要求下载 Fashion-MNIST。这个教学实验不代表大规模图像系统。训练、验证、测试三份严格分开。独立推理脚本只加载模型、输入特征并输出预测。''',
r'''import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from pathlib import Path
import copy

torch.manual_seed(42);torch.set_num_threads(2)
digits=load_digits()
X=(digits.data/16).astype("float32");y=digits.target.astype("int64")
X_train,X_temp,y_train,y_temp=train_test_split(X,y,test_size=.3,stratify=y,random_state=42)
X_valid,X_test,y_valid,y_test=train_test_split(X_temp,y_temp,test_size=.5,stratify=y_temp,random_state=42)
loader=DataLoader(TensorDataset(torch.tensor(X_train),torch.tensor(y_train)),batch_size=64,shuffle=True)
def make_model():return nn.Sequential(nn.Linear(64,64),nn.ReLU(),nn.Dropout(.1),nn.Linear(64,10))
device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
model=make_model().to(device)
loss_function=nn.CrossEntropyLoss();optimizer=torch.optim.Adam(model.parameters(),lr=.01)
history=[];best=float("inf");best_state=None
for epoch in range(12):
    model.train();total=0
    for features,labels in loader:
        features,labels=features.to(device),labels.to(device)
        optimizer.zero_grad()
        loss=loss_function(model(features),labels)
        loss.backward();optimizer.step()
        total+=loss.item()*len(features)
    model.eval()
    with torch.no_grad():
        validation=loss_function(model(torch.tensor(X_valid).to(device)),torch.tensor(y_valid).to(device)).item()
    history.append((total/len(X_train),validation))
    if validation<best:
        best=validation;best_state=copy.deepcopy(model.state_dict())
model.load_state_dict(best_state)
torch.save({k:v.cpu() for k,v in best_state.items()},"week06-best.pt")
restored=make_model();restored.load_state_dict(torch.load("week06-best.pt",weights_only=True));restored.eval()
with torch.no_grad():
    predictions=restored(torch.tensor(X_test)).argmax(1).numpy()
print("测试准确率：",float((predictions==y_test).mean()),"设备：",device)
plt.plot(history);plt.legend(["train loss","validation loss"]);plt.xlabel("epoch");plt.show()
# 保存一个真正可独立运行的推理入口，而不是依赖当前 Notebook 的变量。
script="""import torch, json, sys
from torch import nn
model=nn.Sequential(nn.Linear(64,64),nn.ReLU(),nn.Dropout(.1),nn.Linear(64,10))
model.load_state_dict(torch.load("week06-best.pt",map_location="cpu",weights_only=True))
model.eval()
features=torch.tensor(json.load(open(sys.argv[1])),dtype=torch.float32).reshape(-1,64)
with torch.no_grad(): print(model(features).argmax(1).tolist())
"""
Path("week06-infer.py").write_text(script,encoding="utf-8")
''','移除 Dropout 后比较曲线。解释 eval 与 no_grad 的不同；用导出的脚本预测一个样本。',
r'''import json,subprocess,sys
Path("week06-input.json").write_text(json.dumps(X_test[:1].tolist()))
result=subprocess.run([sys.executable,"week06-infer.py","week06-input.json"],capture_output=True,text=True,check=True)
assert int(json.loads(result.stdout)[0])==int(predictions[0])
print("独立进程推理：",result.stdout)
''')

lesson('Attention、向量与检索 API',
'''Token 是模型处理的单位，不一定等于字或单词。Embedding 将 token/文本映射为向量，余弦相似度是两个向量夹角的余弦；先归一化后点积即可。相似度高不代表事实正确，更不代表片段能支持答案。Transformer 的 attention 用 QKᵀ 的相似度决定对 V 的加权：softmax(QKᵀ/√d)V。mask 控制能看哪些位置。

本例先计算可检查的 attention，再实现 TF-IDF + SVD 的小型潜在语义检索。它是本地教学基线，不是预训练神经 embedding，词表外和同义改写是失败点。真实模型应查看 Hugging Face model card、许可证、语言覆盖、最大长度和 pooling 方式；不能简单把任意 hidden state 当句向量。

生产模型 API 必须设置超时、有限重试和结构化输出验证。只对可安全重试的错误重试；不无限重复有副作用的生成。模型用量以服务实际返回为准。网站中的 Codex 助手使用本机配置，不要求你在 Notebook 放 API Key。''',
r'''import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel,Field

rng=np.random.default_rng(42)
Q,K,V=[rng.normal(size=(3,4)) for _ in range(3)]
scores=Q@K.T/np.sqrt(4)
scores-=scores.max(axis=1,keepdims=True)  # 防止 exp 溢出
weights=np.exp(scores);weights/=weights.sum(axis=1,keepdims=True)
assert np.allclose(weights.sum(axis=1),1)
print("注意力权重：\n",weights,"\n加权表示：\n",weights@V)

documents=["Python virtual environments isolate project dependencies.",
 "SQL transactions commit or roll back database changes.",
 "FastAPI validates HTTP requests and JSON responses.",
 "Neural networks learn weights using gradients and optimizers.",
 "Vector search compares normalized text embeddings.",
 "Git branches isolate source code changes for review."]
def chunks(text,size=9,overlap=2):
    if not 0<=overlap<size:raise ValueError("invalid overlap")
    words=text.split()
    return [" ".join(words[i:i+size]) for i in range(0,len(words),size-overlap)]
index=[{"document":i,"paragraph":j,"text":chunk} for i,d in enumerate(documents) for j,chunk in enumerate(chunks(d))]
vectorizer=TfidfVectorizer();matrix=vectorizer.fit_transform([x["text"] for x in index])
svd=TruncatedSVD(n_components=4,random_state=42)
vectors=normalize(svd.fit_transform(matrix))
def search(query,k=3):
    encoded=vectorizer.transform([query])
    if encoded.nnz==0:return []  # 不为完全未知的查询假造相关性
    query_vector=normalize(svd.transform(encoded))
    similarities=(vectors@query_vector.T).ravel()
    return [{**index[i],"score":float(similarities[i])} for i in np.argsort(-similarities)[:k]]
print(search("database transactions"))
app=FastAPI()
class Query(BaseModel):
    text:str=Field(min_length=1,max_length=500)
    k:int=Field(default=3,ge=1,le=10)
@app.post("/search")
def route(body:Query):return search(body.text,body.k)
with TestClient(app) as client:
    assert client.post("/search",json={"text":"SQL database"}).status_code==200
    assert client.post("/search",json={"text":"SQL","k":0}).status_code==422
assert search("zzunknownzz")==[]
''','记录 10 个查询的预期文档与实际首位结果。替换 SVD 为经过许可审核的句向量模型时，哪些索引需要重建？',
r'''queries={"SQL database":1,"Python dependencies":0,"HTTP JSON":2,"gradients optimizers":3,"embeddings":4,"Git branches":5}
hits=[]
for query,expected in queries.items():
    result=search(query,1)
    hit=bool(result and result[0]["document"]==expected)
    hits.append(hit);print(query,hit,result)
print("当前小样本 Recall@1：",sum(hits)/len(hits),"不是生产评测结论")
''')

lesson('RAG：证据、引用与评测',
'''RAG 分为检索与生成。解析阶段保留原文页码和段落，chunking 影响可找到的证据，top-k 和上下文预算决定交给生成器的内容。来源 ID 应稳定，不能用页面展示顺序冒充原始来源。上传去重依赖内容哈希；相同文件名不一定相同内容。

本例是可离线验证的 extractive QA 基线：返回来源原句，证据不足拒答，不伪装成 LLM 生成。网站 Codex 助手则可接入真正的生成步骤。文档中的“忽略规则”是数据，不是指令。引用存在只证明编号有效，不证明该片段真的蕴含答案；需要独立评测。

检索命中率衡量正确片段能否进入 top-k，答案正确率衡量内容，引用支持率衡量论据对应。至少 30 道评测题应涵盖可回答、同义改写、跨文档、冲突和无答案。本例的模板生成题用于回归测试，不应冒充人工标注的真实评测集。''',
r'''import hashlib,json,re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

pages=[("python.md",1,"Python virtual environments isolate dependencies for each project."),
       ("sql.md",1,"A database transaction groups changes so they commit or roll back together."),
       ("http.md",1,"HTTP 404 means the requested resource was not found."),
       ("rag.md",2,"RAG retrieves source passages before generating a grounded answer."),
       ("testing.md",3,"Unit tests isolate business logic; integration tests check component boundaries.")]
sources={}
for filename,page,content in pages:
    digest=hashlib.sha256((filename+str(page)+content).encode()).hexdigest()[:12]
    sources[digest]={"file":filename,"page":page,"paragraph":1,"content":content}
ids=list(sources)
vectorizer=TfidfVectorizer(stop_words="english")
matrix=vectorizer.fit_transform([sources[i]["content"] for i in ids])
history=[]
def answer(question):
    vector=vectorizer.transform([question])
    scores=cosine_similarity(vector,matrix).ravel()
    best=int(scores.argmax())
    if scores[best]<.12:
        result={"answer":"Insufficient evidence.","source":None}
    else:
        identifier=ids[best]
        result={"answer":sources[identifier]["content"],"source":identifier,**sources[identifier]}
    history.append({"question":question,**result})
    return result
print(answer("What does HTTP 404 mean?"))
assert answer("Who won the football championship?")["source"] is None
# 5 个知识点 × 6 种模板 = 30 个回归问题，显式标为 synthetic。
topics=["Python virtual environments","database transaction","HTTP 404","RAG source passages","Unit tests"]
templates=["Explain {}", "What is {}?", "Describe {}", "Give evidence for {}", "Summarize {}", "Define {}"]
evaluation=[]
for i,topic in enumerate(topics):
    for template in templates:
        question=template.format(topic);result=answer(question)
        evaluation.append({"question":question,"expected_source":ids[i],"actual_source":result["source"],"correct":result["source"]==ids[i],"synthetic":True})
report=pd.DataFrame(evaluation)
assert len(report)==30
display(report)
print("检索命中率：",report.correct.mean())
report.to_csv("week08-evaluation.csv",index=False)
Path("week08-history.json").write_text(json.dumps(history,indent=2),encoding="utf-8")
''','手工写 10 道模板没有覆盖的问题，至少两道无法回答。不要调低阈值来强行提高可回答数量。',
r'''for question in ["What happens when a transaction fails?","How do I train a large language model?","What does missing resource mean?"]:
    result=answer(question)
    print(question,result)
    if result["source"] is not None:
        assert result["source"] in sources
        assert result["answer"]==sources[result["source"]]["content"]
print("来源存在检查通过；语义支持仍需人工核对。")
''')

lesson('可靠性、分层与异步',
'''路由层处理 HTTP，服务层编排业务，仓储层访问数据，检索器负责召回，模型适配器负责外部协议。分层的价值是让变化局部化，不是为每个函数都造一个抽象类。Protocol 可以描述接口，测试用内存实现替代网络边界。

异步用于等待 I/O，不自动加速 CPU 密集运算。阻塞解析需要线程/进程或后台任务。timeout 限制等待，取消必须传播到正在运行的工作。重试只适用于瞬时、可重放错误；校验失败、鉴权失败不应不断重试。记录请求 ID、阶段和耗时，避免原始密钥进入日志。

上传限制同时检查字节数、扩展名、解析结果和资源消耗。仅检查后缀不能保证内容安全。Notebook 本质可执行任意管理员代码，不是恶意代码沙箱；所以网站绝不允许访客执行。''',
r'''import asyncio,json,time,logging,io
from typing import Protocol
from dataclasses import dataclass
from unittest.mock import AsyncMock

class Retriever(Protocol):
    async def search(self,query:str)->list[str]: ...
@dataclass
class QAService:
    retriever: Retriever
    async def answer(self,query:str)->dict:
        if not query.strip():raise ValueError("empty query")
        # wait_for 会取消超时协程；真实适配器也要处理资源清理。
        passages=await asyncio.wait_for(self.retriever.search(query),timeout=.2)
        return {"answer":passages[0] if passages else "Insufficient evidence", "count":len(passages)}

async def retry_read(operation,attempts=3):
    for attempt in range(attempts):
        try:return await operation()
        except TimeoutError:
            if attempt==attempts-1:raise
            await asyncio.sleep(.01*2**attempt)

async def verify_service():
    retriever=AsyncMock();retriever.search.return_value=["A transaction is atomic."]
    service=QAService(retriever)
    assert (await service.answer("transaction"))["count"]==1
    retriever.search.assert_awaited_once_with("transaction")
    retriever.search.return_value=[]
    assert (await service.answer("unknown"))["answer"]=="Insufficient evidence"
    operation=AsyncMock(side_effect=[TimeoutError(),"success"])
    assert await retry_read(operation)=="success"
    assert operation.await_count==2
    async def slow(_):await asyncio.sleep(1)
    retriever.search.side_effect=slow
    try:await service.answer("slow")
    except TimeoutError:print("超时被正确传播")
    return {"event":"service_checks","success":True}

# Notebook 已有事件循环，所以使用 await；脚本入口才使用 asyncio.run。
print(json.dumps(await verify_service()))
def validate_upload(name,content):
    if len(content)>1024:raise ValueError("file too large for this demo")
    if not name.endswith((".txt",".md")):raise ValueError("unsupported type")
    return content.decode("utf-8")
assert validate_upload("notes.md",b"hello")=="hello"
''','补充空输入、解码失败、超出大小三个测试。把日志中 token/password 字段替换为 [redacted]。',
r'''def redact(fields):
    return {k:"[redacted]" if k.lower() in {"token","password","api_key"} else v for k,v in fields.items()}
assert redact({"token":"never-log-me","request_id":"r1"})=={"token":"[redacted]","request_id":"r1"}
for name,data in [("x.exe",b"a"),("x.txt",b"x"*1025),("x.txt",b"\xff")]:
    try:validate_upload(name,data)
    except (ValueError,UnicodeDecodeError):print("预期拒绝",name,len(data))
''')

lesson('部署、缓存、队列与系统设计',
'''请求经过 DNS、HTTPS 反向代理、应用服务、检索/数据库、模型，再返回客户端。DNS 只映射名称，不负责运行应用；反向代理终止 TLS、转发请求。进程存活检查(liveness)与依赖就绪检查(readiness)不同。公开部署之前必须考虑认证、配额、上传限制、备份和日志。

缓存适合复用结果，需要 key、TTL 和失效策略；用户身份/权限影响结果时必须进入 key，否则可能泄露私人数据。队列把耗时工作移到后台，但带来重复投递、失败恢复和可观测性问题。内存 asyncio.Queue 只演示调度，进程重启会丢工作；可靠任务需要持久化队列。

同步模型简单但等待会阻塞请求，异步改善并发等待但增加取消与状态管理。先测瓶颈再扩容，检索、模型、数据库各有不同约束。下面只演示本地机制，不执行云部署，不宣称已获得公网 Demo。''',
r'''import asyncio,time
from dataclasses import dataclass,field
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

@dataclass
class TTLCache:
    ttl:float
    values:dict=field(default_factory=dict)
    def get(self,key):
        value=self.values.get(key)
        if not value:return None
        if time.monotonic()>=value[0]:
            self.values.pop(key,None);return None
        return value[1]
    def put(self,key,value):self.values[key]=(time.monotonic()+self.ttl,value)

cache=TTLCache(ttl=.05)
cache.put(("user-a","document-1","query"),"private answer")
assert cache.get(("user-b","document-1","query")) is None
await asyncio.sleep(.06)
assert cache.get(("user-a","document-1","query")) is None

async def pipeline():
    queue=asyncio.Queue(maxsize=2);completed=[]
    async def worker():
        while True:
            item=await queue.get()
            try:
                if item is None:return
                await asyncio.sleep(.01)
                completed.append({"id":item,"state":"indexed"})
            finally:queue.task_done()
    task=asyncio.create_task(worker())
    for identifier in range(5):await queue.put(identifier)
    await queue.put(None);await queue.join();await task
    return completed
print(await pipeline())
app=FastAPI()
@app.get("/health/live")
def live():return {"status":"alive"}
@app.get("/health/ready")
def ready():return {"status":"ready","storage":"demo-memory"}
with TestClient(app) as client:assert client.get("/health/live").status_code==200
diagram="""flowchart LR
 Browser --> Proxy[HTTPS reverse proxy]
 Proxy --> API[FastAPI]
 API --> DB[(Database)]
 API --> Retrieval[Document index]
 API --> Model[Model service]
 API --> Queue[Background queue]
"""
Path("week10-architecture.mmd").write_text(diagram,encoding="utf-8")
print(diagram)
''','解释缓存击穿、失效和用户隔离。设计后台文档解析状态：queued/running/succeeded/failed，并写故障恢复策略。',
r'''states={"queued":{"running"},"running":{"succeeded","failed"},"failed":{"queued"},"succeeded":set()}
def transition(current,target):
    if target not in states[current]:raise ValueError("invalid transition")
    return target
assert transition("queued","running")=="running"
try:transition("succeeded","running")
except ValueError:print("已完成任务不会被意外重新执行")
''')

lesson('作品集、真实证据与项目表达',
'''招聘者通常先看项目解决什么问题、你负责什么，再看技术与结果。README 应包含问题、安装、架构、测试、失败案例、限制和下一步。指标必须有测量定义、数据规模与环境，不能凭感觉写“性能提升 80%”。截图和视频是说明，不替代可复现测试。

英文简历 bullet 可以用 Action + Scope + Evidence：Built a document search API with source citations; evaluated retrieval on N labeled questions. N 必须来自实际记录。计划项目使用 Planned，未完成不写成 shipped。STAR：Situation、Task、Action、Result，重点是你做的取舍与可验证结果。

下面生成项目描述草稿和证据审计。它不会伪造 GitHub 仓库、简历经历或录制视频。最终一页简历仍要补真实教育信息、日期和联系方式。''',
r'''from dataclasses import dataclass,asdict
from pathlib import Path
import json

@dataclass
class Project:
    name:str
    status:str
    problem:str
    stack:list[str]
    evidence:list[str]
    limitations:list[str]

projects=[Project("Task Management API","planned","Persist and validate personal tasks",["FastAPI","SQLAlchemy","pytest"],[],["Not deployed"]),
          Project("Document Q&A","planned","Find evidence in learning documents",["Python","Retrieval","Codex"],[],["Evaluation not yet completed"])]
def render_readme(project):
    return f"# {project.name}\n\nStatus: {project.status}\n\n## Problem\n{project.problem}\n\n## Stack\n"+", ".join(project.stack)+"\n\n## Evidence\n"+"\n".join("- "+x for x in (project.evidence or ["Pending: add actual test commands and results"]))+"\n\n## Limitations\n"+"\n".join("- "+x for x in project.limitations)
folder=Path("week11-portfolio");folder.mkdir(exist_ok=True)
for i,project in enumerate(projects,1):
    content=render_readme(project)
    (folder/f"project-{i}-README.md").write_text(content,encoding="utf-8")
    print(content)
def audit(project):
    issues=[]
    if project.status=="completed" and not project.evidence:issues.append("Completed claim has no evidence")
    if not project.limitations:issues.append("Document known limitations")
    return issues
assert not audit(projects[0])
unverified=Project("Demo","completed","Example",["Python"],[],[])
assert len(audit(unverified))==2
story={"situation":"[real context]","task":"[your responsibility]","action":"[your technical decision]","result":"[measured result, or honest limitation]"}
(folder/"star-template.json").write_text(json.dumps(story,indent=2),encoding="utf-8")
print("请替换占位内容；不要把计划写成经历。")
''','为真实项目填一条带测试证据的 bullet。用 2 分钟解释一个失败案例，而不是只背技术栈。',
r'''def evidence_bullet(action,scope,measurement):
    if not measurement.strip():raise ValueError("Need real evidence before claiming an outcome")
    return f"{action} {scope}; {measurement}."
print(evidence_bullet("Implemented","input validation in a local learning API","verified empty-title rejection with TestClient"))
''')

lesson('面试、算法复盘与申请追踪',
'''面试先澄清输入规模、边界和预期输出，再解释算法与复杂度。哈希表平均查找 O(1)，排序 O(n log n)，BFS 在无权图找最短路径 O(V+E)。不要只背结论，要能证明为什么队列按距离逐层扩展。Python 可变默认参数、浅拷贝、生成器与异常也是常见考点。

系统题从需求、数据模型、API、关键流程和瓶颈展开。缓存和队列不是必选项，要说明它们解决什么问题、引入什么失败。AI 题区分 embedding 相似、检索命中、答案正确与引用支持。行为题用真实 STAR 事例，允许承认不知道并解释验证方式。

申请追踪记录公司、岗位、状态、截止时间、面试和复盘。CSV 导出可能被电子表格当公式执行，以 =,+,-,@ 开头的单元格要防护。约 20 个针对性申请是行动目标，网站不能把创建记录等同实际投递。四次模拟面试需要真实完成并记录反馈。''',
r'''from collections import deque
from dataclasses import dataclass,asdict
from pathlib import Path
import csv,io

def shortest_path(graph,start,goal):
    queue=deque([start]);parent={start:None}
    while queue:
        current=queue.popleft()
        if current==goal:
            path=[]
            while current is not None:path.append(current);current=parent[current]
            return path[::-1]
        for neighbor in graph.get(current,[]):
            if neighbor not in parent:
                parent[neighbor]=current;queue.append(neighbor)
    return None
graph={"a":["b","c"],"b":["d"],"c":["d"],"d":[]}
assert shortest_path(graph,"a","d")==["a","b","d"]
assert shortest_path(graph,"a","a")==["a"]
assert shortest_path(graph,"d","a") is None
print("BFS：",shortest_path(graph,"a","d"))

def append_safely(value,items=None):
    # None 哨兵避免多次调用共享同一个默认列表。
    if items is None:items=[]
    items.append(value);return items
assert append_safely(1)==[1] and append_safely(2)==[2]

@dataclass
class Application:
    company:str
    role:str
    status:str="saved"
    reflection:str=""
applications=[Application("Example company (practice only)","AI SWE Intern")]
def safe_cell(value):
    return "'"+value if value.startswith(("=","+","-","@")) else value
stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(asdict(applications[0])))
writer.writeheader()
for application in applications:writer.writerow({k:safe_cell(v) for k,v in asdict(application).items()})
Path("week12-applications.csv").write_text(stream.getvalue(),encoding="utf-8-sig")
assert safe_cell("=1+1")=="'=1+1"
mock_plan=[{"type":kind,"completed":False,"feedback":""} for kind in ["algorithm","project","AI basics","behavioral"]]
print("模拟计划（未完成）：",mock_plan)
''','为 BFS 增加循环图测试，解释何时把节点标记为 visited。完成一次真实模拟后记录改进项，不要自动勾选四次模拟。',
r'''cyclic={"a":["b"],"b":["a","c"],"c":["b"]}
assert shortest_path(cyclic,"a","c")==["a","b","c"]
assert shortest_path({},"x","missing") is None
print("循环图与不存在目标测试通过；时间 O(V+E)，空间 O(V)。")
''')

def main():
    directory=ROOT/'notebooks';directory.mkdir(exist_ok=True)
    for index,(title,concepts,code,exercise,solution) in enumerate(LESSONS,1):
        notebook=nb.v4.new_notebook()
        notebook.metadata={'kernelspec':{'display_name':'Workbench Python','language':'python','name':'python3'},'language_info':{'name':'python'},'workbench':{'week':index,'status':'planned'}}
        # Split at natural sections: preserve shared state and retain substantial main implementation.
        notebook.cells=[nb.v4.new_markdown_cell(f'# Week {index:02} · {title}\n\n{concepts}\n\n## 学习方式 / How to study\n先预测代码结果，再逐行运行。改变一个输入、解释变化，最后不看参考实现重写关键函数。阅读不是掌握的证据；能独立实现、测试、解释失败才是。'),nb.v4.new_code_cell(code.strip()),nb.v4.new_markdown_cell('## 练习 / Exercises\n'+exercise+'\n\n先在下面独立完成，再展开参考实现。'),nb.v4.new_code_cell('# 在这里写你的实现；运行后检查边界。\n'),nb.v4.new_markdown_cell('## 参考实现与验收 / Reference and checks\n参考实现是一个可行方案，不是唯一答案。不要在未完成练习前直接复制。'),nb.v4.new_code_cell(solution.strip())]
        nb.validate(notebook)
        nb.write(notebook,directory/f'week-{index:02}.ipynb')
    print(f'Generated {len(LESSONS)} teaching notebooks')

if __name__=='__main__':main()
