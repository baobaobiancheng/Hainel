# Smart Error Book - Backend

基于 FastAPI 的后端 API 服务。

## 快速开始

### 安装依赖

```bash
# 安装 uv
pip install uv

# 安装项目依赖
uv sync

# 安装开发依赖
uv sync --all-extras
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 运行数据库迁移

```bash
uv run alembic upgrade head
```

### 启动开发服务器

```bash
uv run uvicorn app.main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档。

## 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   ├── core/             # 核心功能
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑
│   ├── repositories/     # 数据访问层
│   ├── config.py         # 配置
│   └── main.py           # 入口
├── alembic/              # 数据库迁移
├── pyproject.toml        # 项目配置
└── README.md
```

## 开发

### 创建数据库迁移

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### 运行测试

```bash
uv run pytest
uv run pytest --cov
```

### 代码质量

```bash
# 格式化
uv run black .

# 检查
uv run ruff check .

# 类型检查
uv run mypy .
```

