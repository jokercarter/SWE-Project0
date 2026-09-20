export const learningCode = [
{week:'01', title:'Python 工程化与 Git', focus:'虚拟环境、数据模型、文件持久化和异常处理', code:`from dataclasses import dataclass, asdict
import json
from pathlib import Path

DATA = Path("todo.json")

@dataclass
class Task:
    title: str
    done: bool = False

def load_tasks():
    if not DATA.exists():
        return []
    try:
        return [Task(**item) for item in json.loads(DATA.read_text(encoding="utf-8"))]
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("todo.json 不是有效的任务文件") from error

def save_tasks(tasks):
    DATA.write_text(json.dumps([asdict(t) for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")

tasks = load_tasks()
tasks.append(Task("完成 Week 01 练习"))
save_tasks(tasks)
print(tasks)`},
{week:'02', title:'FastAPI 任务 API', focus:'路由、Pydantic 验证、状态码和测试', code:`from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Learning Tasks API")
tasks = {}

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)

class Task(TaskIn):
    id: int
    done: bool = False

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskIn):
    task_id = max(tasks, default=0) + 1
    task = Task(id=task_id, title=payload.title)
    tasks[task_id] = task
    return task

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    if task_id not in tasks:
        raise HTTPException(404, "task not found")
    return tasks[task_id]`},
{week:'03', title:'SQL 与事务', focus:'表关系、JOIN、参数化查询和回滚', code:`import sqlite3

db = sqlite3.connect(":memory:")
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE tasks(
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title TEXT NOT NULL,
  done INTEGER NOT NULL DEFAULT 0
);
""")
db.execute("INSERT INTO users(name) VALUES (?)", ("Joker",))
user_id = db.execute("SELECT id FROM users WHERE name=?", ("Joker",)).fetchone()[0]
db.execute("INSERT INTO tasks(user_id,title) VALUES (?,?)", (user_id, "Learn JOIN"))
db.commit()
rows = db.execute("""SELECT users.name, tasks.title
FROM users JOIN tasks ON tasks.user_id = users.id""").fetchall()
print([dict(row) for row in rows])`},
{week:'04', title:'测试与 Docker 思维', focus:'单元测试、边界条件和可重复运行', code:`def add_task(tasks, title):
    title = title.strip()
    if not title:
        raise ValueError("title cannot be empty")
    task = {"id": len(tasks) + 1, "title": title, "done": False}
    tasks.append(task)
    return task

def test_add_task():
    tasks = []
    result = add_task(tasks, "  write a test  ")
    assert result == {"id": 1, "title": "write a test", "done": False}
    assert tasks[0] is result

def test_reject_empty_title():
    try:
        add_task([], "   ")
    except ValueError as error:
        assert "empty" in str(error)
    else:
        raise AssertionError("empty title should fail")

test_add_task(); test_reject_empty_title(); print("2 tests passed")`},
{week:'05', title:'机器学习指标', focus:'训练/测试划分、混淆矩阵和 Precision/Recall', code:`def metrics(y_true, y_pred):
    tp = sum(a == b == 1 for a, b in zip(y_true, y_pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y_true, y_pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y_true, y_pred))
    tn = sum(a == b == 0 for a, b in zip(y_true, y_pred))
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    accuracy = (tp + tn) / len(y_true)
    return {"TP":tp,"FP":fp,"FN":fn,"TN":tn,
            "precision":round(precision, 3),
            "recall":round(recall, 3),
            "accuracy":round(accuracy, 3)}

print(metrics([1, 1, 0, 0, 1], [1, 0, 0, 0, 1]))`},
{week:'06', title:'PyTorch 训练循环', focus:'Tensor、Dataset、loss、反向传播和验证', code:`# 需要安装 torch：python -m pip install torch
import torch
from torch import nn

torch.manual_seed(0)
x = torch.randn(32, 2)
y = (x[:, 0] + x[:, 1] > 0).long()
model = nn.Sequential(nn.Linear(2, 8), nn.ReLU(), nn.Linear(8, 2))
loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.03)

for epoch in range(80):
    model.train()
    logits = model(x)
    loss = loss_fn(logits, y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

model.eval()
with torch.no_grad():
    prediction = model(x).argmax(dim=1)
    print("accuracy", (prediction == y).float().mean().item())`},
{week:'07', title:'Embedding 语义搜索', focus:'向量、余弦相似度、top-k 和来源保留', code:`import math

documents = [
    ("python", [1.0, 0.8, 0.1]),
    ("database", [0.1, 0.2, 1.0]),
    ("api", [0.8, 0.7, 0.2]),
]
query = [0.9, 0.8, 0.1]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    norm = math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))
    return dot / norm if norm else 0

ranked = sorted(((cosine(query, vector), source)
                 for source, vector in documents), reverse=True)
print("top-k:", ranked[:2])`},
{week:'08', title:'RAG 检索与引用', focus:'chunk、检索、证据上下文和拒答', code:`chunks = [
    {"text": "FastAPI uses Python type hints.", "source": "notes.md#1"},
    {"text": "A transaction can commit or roll back.", "source": "db.md#3"},
]

def retrieve(question, top_k=2):
    words = set(question.lower().split())
    scored = []
    for chunk in chunks:
        score = len(words & set(chunk["text"].lower().split()))
        scored.append((score, chunk))
    return [chunk for score, chunk in sorted(scored, reverse=True,
                                             key=lambda item: item[0])[:top_k]
            if score > 0]

def answer(question):
    evidence = retrieve(question)
    if not evidence:
        return {"answer": "证据不足，无法回答。", "sources": []}
    return {"answer": evidence[0]["text"],
            "sources": [item["source"] for item in evidence]}

print(answer("What does FastAPI use?"))`},
{week:'09', title:'可靠性与重试', focus:'超时、可恢复错误、日志和依赖隔离', code:`import time

class TemporaryError(Exception): pass

def retry(operation, attempts=3, delay=0.05):
    for number in range(1, attempts + 1):
        try:
            return operation()
        except TemporaryError:
            if number == attempts:
                raise
            time.sleep(delay * number)

calls = {"count": 0}
def flaky_service():
    calls["count"] += 1
    if calls["count"] < 3:
        raise TemporaryError("temporary outage")
    return "ok"

print(retry(flaky_service), "calls:", calls["count"])`},
{week:'10', title:'部署与健康检查', focus:'配置、健康检查、请求流程和安全边界', code:`import os
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")

def health_check(database_url):
    parsed = urlparse(database_url)
    if parsed.scheme not in {"sqlite", "postgresql"}:
        return {"status": "error", "reason": "unsupported database"}
    return {"status": "ok", "database": parsed.scheme}

print(health_check(DATABASE_URL))
# 生产服务还需要：反向代理、HTTPS、备份、日志和非 root 运行用户。`},
{week:'11', title:'项目表达与简历指标', focus:'README、架构说明、真实测量和 STAR', code:`project = {
    "problem": "Users need searchable answers from course documents.",
    "action": "Built a retrieval service with source metadata and evaluation cases.",
    "evidence": {"questions": 30, "citation_checked": True},
    "limitation": "The prototype depends on an external model API.",
}

def resume_bullet(item):
    evidence = item["evidence"]
    return (f"{item['action']} Evaluated {evidence['questions']} questions; "
            f"citation checks={evidence['citation_checked']}. "
            f"Limitation: {item['limitation']}")

print(resume_bullet(project))`},
{week:'12', title:'算法面试复盘', focus:'复杂度、哈希表、BFS 和可解释回答', code:`from collections import deque

def shortest_path(graph, start, target):
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None

graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
print(shortest_path(graph, "A", "D"))
# 口述：每个节点最多入队一次，所以时间复杂度 O(V+E)。`}
];

// Each week is presented as a small notebook. The first cell is the complete
// runnable example; later cells are deliberately short, independent checks and
// exercises so a learner can run one idea at a time.
const cellExercises = {
 '01':'# Exercise: add a function that marks the first task as done.\n# Then run the cell again and inspect the JSON file.',
 '02':'# Exercise: add a GET /tasks endpoint and return an empty list initially.\n# Explain why a 404 is different from an empty collection.',
 '03':'# Exercise: add a query for only unfinished tasks.\n# Use a parameterized value instead of formatting SQL strings.',
 '04':'# Exercise: add one test for a duplicate title or invalid input.\n# Run the tests and explain what the assertion proves.',
 '05':'# Exercise: change the prediction list and recalculate precision and recall.\n# Which metric changes more and why?',
 '06':'# Exercise: change the learning rate and compare the final accuracy.\n# Record the result instead of guessing.',
 '07':'# Exercise: add a fourth document vector and see how top-k changes.\n# Explain why the highest score is not automatically a correct answer.',
 '08':'# Exercise: add a question with no matching words.\n# Confirm that the system refuses instead of inventing evidence.',
 '09':'# Exercise: make the fake service fail three times.\n# Decide whether retrying still makes sense and justify the limit.',
 '10':'# Exercise: add a health check for an unsupported URL scheme.\n# Explain why configuration belongs outside source code.',
 '11':'# Exercise: replace the placeholder evidence with a real measured number.\n# Include the test condition and date in the bullet.',
 '12':'# Exercise: add a disconnected node and explain why BFS returns None.\n# State the time complexity in terms of V and E.'
};
for (const item of learningCode) {
  const comment = `# Week ${item.week}: ${item.title}\n# Read the comments, run the cell, then change one small thing.\n# This is a teaching example; verify every claim with a test.`;
  item.cells = [
    {title:'核心实现 / Core implementation', purpose:'完整示例：先运行，再逐段阅读。', code:`${comment}\n\n${item.code}`},
    {title:'练习与思考 / Guided exercise', purpose:'先独立修改，再运行检查结果。', code:`# ${item.title}\n${cellExercises[item.week]}`},
  ];
}
