# 基于多智能体协同的医疗健康咨询与辅助诊断系统

面向毕业设计/课程项目的一体化医疗咨询系统，包含：

- 患者端小程序
- 医生端 Web 管理后台
- FastAPI 后端服务
- 多智能体协同诊疗链路
- 医疗知识图谱与向量知识库
- 离线强化学习训练与策略激活能力

当前仓库内容已经不再是“代码框架设计”阶段，而是一个可运行、可扩展、已包含前后端与 RL 训练台的完整工程。

## 1. 项目概览

系统目标是用多个职责明确的智能体协同完成医疗健康咨询与辅助诊断场景中的核心流程：

- 患者发起咨询
- 系统执行分诊、追问、诊断辅助与报告关联
- 医生在后台查看会话、患者、病历和知识库
- 平台支持知识检索、OCR、知识图谱、训练数据导出与离线策略训练

当前代码里已经实现或接入了以下关键能力：

- 多智能体模式：`Moderator / PCC / MDT / ICT`
- 会话、消息、病历、医生患者管理
- 医疗知识图谱检索与 Chroma 本地向量库
- OCR 接口封装
- 离线 RL 数据集构建、训练、评估、策略版本激活
- 医生端训练台闭环流程：`构建数据集 -> 选择数据集训练 -> 查询运行 -> 激活策略 -> 评估`

## 2. 技术栈

### 后端

- FastAPI
- SQLAlchemy 2
- MySQL
- Redis
- Celery
- Transformers / Torch
- PaddleOCR / DashScope OCR 封装
- Neo4j
- Chroma / 本地 Embedding 模型

### 医生端

- Vue 3
- Vite
- Ant Design Vue
- Pinia
- ECharts

### 患者端

- 微信小程序项目结构
- 自定义组件与页面分层

## 3. 目录结构

```text
.
├── backend/                 后端服务
│   ├── app/
│   │   ├── api/v1/          API 路由
│   │   ├── agents/          多智能体与 RL 评估训练
│   │   ├── ai/              LLM / OCR / Embedding 封装
│   │   ├── knowledge/       知识图谱与向量检索
│   │   ├── models/          ORM 模型
│   │   ├── schemas/         Pydantic 模型
│   │   ├── services/        业务服务层
│   │   └── tasks/           Celery 任务
│   ├── data/                本地数据、训练导出、策略注册表
│   ├── scripts/             初始化和导入脚本
│   ├── tests/               后端测试
│   ├── main_dev.py          开发入口
│   └── pyproject.toml
├── frontend-doctor/         医生端管理后台
├── frontend-patient/        患者端小程序
├── docker/                  Docker 相关配置
├── docs/                    项目文档与过程文档
├── uploads/                 上传文件目录（本地运行时生成/使用）
└── README.md
```

## 4. 核心模块说明

### 4.1 多智能体协同

后端在 `backend/app/agents/` 下实现了多种协同模式：

- `moderator`：评估复杂度并选择协作模式
- `pcc`：单智能体问诊与诊断
- `mdt`：多智能体会诊
- `ict`：跨学科协作与综合输出

相关 API 位于：

- [backend/app/api/v1/agents.py](backend/app/api/v1/agents.py)

### 4.2 会话与病历

核心业务对象包括：

- 会话 `Conversation`
- 消息 `Message`
- 病历 `MedicalRecord`
- 用户 `User`
- 提醒 `Reminder`

主要路由：

- `auth`
- `conversations`
- `messages`
- `medical_records`
- `doctors`
- `reports`
- `reminders`

### 4.3 知识库与知识图谱

系统同时支持：

- Neo4j 知识图谱
- Chroma 本地向量知识库
- 本地 Embedding 模型缓存目录

相关实现位于：

- [backend/app/knowledge/](backend/app/knowledge/)
- [backend/app/ai/embeddings/](backend/app/ai/embeddings/)

### 4.4 RL 训练台

医生端已实现强化学习训练台，支持：

- 构建训练数据集
- 数据集资产化管理
- 选择已有数据集训练
- 查询 `run_id`
- 激活策略版本
- 离线评估策略

关键文件：

- [frontend-doctor/src/views/RLTraining.vue](frontend-doctor/src/views/RLTraining.vue)
- [frontend-doctor/src/api/agents.js](frontend-doctor/src/api/agents.js)
- [backend/app/api/v1/agents.py](backend/app/api/v1/agents.py)
- [backend/app/agents/evaluation/rl_trainer.py](backend/app/agents/evaluation/rl_trainer.py)
- [backend/app/agents/evaluation/policy_registry.py](backend/app/agents/evaluation/policy_registry.py)

## 5. 环境要求

建议环境：

- Python 3.13
- Node.js 18+
- MySQL 8
- Redis 7
- Neo4j 5

如果要完整启用知识库、OCR、Embedding、RL 训练等能力，还需要准备：

- 模型相关目录
- API Key
- 本地或远程数据库连接

## 6. 后端启动

### 6.1 安装依赖

推荐使用 `uv`：

```bash
cd backend
uv sync
```

如果不用 `uv`，也可以：

```bash
cd backend
pip install -r requirements.txt
```

### 6.2 配置环境变量

后端配置集中在：

- [backend/app/config.py](backend/app/config.py)

常用配置包括：

- MySQL：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- Redis：`REDIS_HOST`、`REDIS_PORT`
- JWT：`SECRET_KEY`
- LLM：`LLM_PROVIDER`、`LLM_MODEL_NAME`、`LLM_API_KEY`
- DeepSeek：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`
- Neo4j：`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`
- Chroma：`CHROMA_PERSIST_DIR`、`CHROMA_EMBEDDING_MODEL`

### 6.3 初始化数据库

仓库提供了若干 SQL 文件：

- [backend/init_database.sql](backend/init_database.sql)
- [backend/add_health_profile.sql](backend/add_health_profile.sql)
- [backend/fix_enum.sql](backend/fix_enum.sql)
- [backend/seed_doctors.sql](backend/seed_doctors.sql)

按你的数据库实际状态选择执行。

### 6.4 启动开发服务

项目当前更适合使用开发入口：

```bash
cd backend
uv run uvicorn main_dev:app --reload --port 8001
```

说明：

- `main_dev.py` 会注册当前开发常用路由
- 医生端默认代理到 `http://localhost:8001`

完整入口也可使用：

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8001
```

## 7. 医生端启动

```bash
cd frontend-doctor
npm install
npm run dev
```

默认开发端口：

- `http://localhost:3001`

代理配置见：

- [frontend-doctor/vite.config.js](frontend-doctor/vite.config.js)

其中：

- `/api` -> `http://localhost:8001`
- `/ws` -> `ws://localhost:8001`

## 8. 患者端说明

患者端位于：

- [frontend-patient/](frontend-patient/)

这是一个微信小程序目录结构项目，通常需要：

1. 在微信开发者工具中导入 `frontend-patient`
2. 根据后端地址调整请求配置
3. 按实际小程序环境编译运行

## 9. Docker

Docker Compose 配置位于：

- [docker/docker-compose.yml](docker/docker-compose.yml)

当前 Compose 主要包含：

- MySQL
- Redis
- Backend

使用前请先检查：

- Dockerfile 路径
- 端口映射
- 数据库账号密码
- 后端环境变量是否与你本地配置一致

## 10. 测试

后端测试位于：

- [backend/tests/](backend/tests/)

可按需运行：

```bash
cd backend
pytest
```

或针对 RL：

```bash
cd backend
pytest tests/test_rl_pipeline.py
```

## 11. 当前仓库中的重要说明

这个仓库包含了较多项目过程文档和实验产物，代码以外的资料也在仓库内保留。  
同时，为了避免 GitHub 大文件限制，以下本地资源默认被 `.gitignore` 排除，不会随仓库同步：

- `backend/.venv/`
- `backend/nlp_models/`
- `backend/models/`
- `backend/data/chroma_db/`
- `node_modules/`
- `uploads/`
- `*.zip`

这意味着你在其他机器拉取仓库后，需要自己准备：

- Python 虚拟环境
- 前端依赖
- NLP / Embedding 模型文件
- Chroma 本地持久化数据
- 上传目录

## 12. 推荐阅读顺序

如果你是第一次看这个项目，建议按下面顺序阅读：

1. 根目录 [README.md](README.md)
2. 后端入口 [backend/main_dev.py](backend/main_dev.py)
3. 后端配置 [backend/app/config.py](backend/app/config.py)
4. 医生端训练台 [frontend-doctor/src/views/RLTraining.vue](frontend-doctor/src/views/RLTraining.vue)
5. 多智能体与 RL 评估目录 [backend/app/agents/](backend/app/agents/)
6. 会话和病历 API [backend/app/api/v1/](backend/app/api/v1/)

## 13. 后续可继续改进的方向

- 为 README 增加数据库初始化的完整步骤
- 增加 `.env.example`
- 补充医生端与患者端截图
- 把部署方式拆成单独文档
- 为模型文件提供下载脚本与目录约定说明
- 为知识图谱和 RL 训练增加数据准备文档

---

如果你正在继续维护这个项目，建议把“环境准备文档”和“数据库初始化说明”单独拆到 `docs/` 里，再在 README 里只保留入口信息。
