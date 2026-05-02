# 后端服务

基于FastAPI的医疗健康咨询与辅助诊断系统后端服务。

## 项目结构

```
backend/
├── app/                    # 应用主目录
│   ├── api/               # API路由层
│   ├── core/              # 核心功能（认证、权限等）
│   ├── models/            # 数据库模型
│   ├── schemas/           # Pydantic模式
│   ├── services/          # 业务服务层
│   ├── agents/            # 多智能体系统
│   ├── nlp/               # NLP处理模块
│   ├── ml/                # 机器学习模块
│   ├── knowledge/         # 知识库模块
│   ├── ai/                # AI模型服务层
│   ├── database/          # 数据库访问层
│   ├── utils/             # 工具函数
│   └── tasks/             # 异步任务
├── tests/                 # 测试代码
└── scripts/               # 脚本工具
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 初始化数据库

使用提供的 SQL 文件初始化数据库：

```bash
# 方式1：使用 MySQL 命令行
mysql -u root -p < init_database.sql

# 方式2：使用 MySQL Workbench 或其他工具导入 init_database.sql
```

### 4. 运行服务

```bash
uvicorn app.main:app --reload
```

## 开发指南

详见 `代码框架设计.md`

