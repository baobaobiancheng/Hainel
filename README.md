# 智能错题本系统 (Smart Error Book)

一个基于 FastAPI + Vue3 的智能错题本系统，帮助学生更高效地管理和复习错题。

## 🎯 项目特色

- ✨ **现代化技术栈**：FastAPI + Vue3 + PostgreSQL + Redis
- 🚀 **高性能**：异步API，极速响应
- 🎨 **优雅界面**：基于 Element Plus 的现代化UI
- 🤖 **AI驱动**：智能错题分析、相似题推荐、知识图谱
- 📊 **数据可视化**：学习报告、统计分析
- 🔐 **安全可靠**：JWT认证、权限管理
- 📱 **响应式设计**：适配各种屏幕尺寸

## 📁 项目结构

```
smart-error-book/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心功能（数据库、安全等）
│   │   ├── models/        # 数据库模型
│   │   ├── schemas/       # Pydantic 模型
│   │   ├── services/      # 业务逻辑
│   │   └── main.py        # 应用入口
│   └── pyproject.toml     # uv 配置
│
├── frontend/               # Vue3 前端
│   ├── src/
│   │   ├── api/           # API 请求
│   │   ├── components/    # 组件
│   │   ├── layouts/       # 布局
│   │   ├── router/        # 路由
│   │   ├── stores/        # 状态管理 (Pinia)
│   │   ├── views/         # 页面
│   │   └── main.ts        # 入口文件
│   └── package.json
│
├── docker/                 # Docker 配置
├── docker-compose.yml      # Docker Compose
└── README.md              # 本文件
```

## 🛠️ 技术栈

### 后端
- **FastAPI**: 现代化 Python Web 框架
- **uv**: 极速 Python 包管理器
- **SQLAlchemy 2.0**: 强大的 ORM
- **PostgreSQL**: 可靠的关系型数据库
- **Redis**: 高性能缓存
- **Pydantic V2**: 数据验证
- **OpenAI/Claude API**: AI 分析

### 前端
- **Vue 3**: 渐进式 JavaScript 框架
- **TypeScript**: 类型安全
- **Vite**: 极速构建工具
- **Pinia**: 现代状态管理
- **Element Plus**: 企业级 UI 组件库
- **Axios**: HTTP 客户端
- **ECharts**: 数据可视化

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker (可选)

### 方式一：本地开发

#### 1. 后端设置

```bash
cd backend

# 使用 uv 安装依赖
pip install uv
uv sync

# 复制环境变量文件
cp .env.example .env
# 编辑 .env 文件，配置数据库等

# 运行数据库迁移
uv run alembic upgrade head

# 启动开发服务器
uv run uvicorn app.main:app --reload
```

后端将运行在 http://localhost:8000

#### 2. 前端设置

```bash
cd frontend

# 安装 pnpm (如果未安装)
npm install -g pnpm

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

前端将运行在 http://localhost:5173

### 方式二：Docker

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问：
- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 📚 核心功能

### 1. 错题管理
- ✅ 创建、编辑、删除错题
- ✅ 分类管理（学科、章节、难度）
- ✅ 标签系统
- ✅ 收藏和归档
- 🚧 OCR 图片识别（开发中）

### 2. AI 智能分析
- 🚧 错误原因分析
- 🚧 知识点提取
- 🚧 相似题推荐
- 🚧 解题思路生成

### 3. 知识图谱
- 🚧 知识点关联
- 🚧 薄弱点识别
- 🚧 学习路径规划

### 4. 智能练习
- 🚧 个性化题目推荐
- 🚧 复习计划生成
- 🚧 学习效果追踪

### 5. 学习报告
- 🚧 数据统计
- 🚧 可视化图表
- 🚧 周报/月报生成

*注：✅ 已完成 | 🚧 开发中*

## 🔧 开发

### 后端开发

```bash
cd backend

# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run ruff check .

# 创建数据库迁移
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### 前端开发

```bash
cd frontend

# 运行类型检查
pnpm vue-tsc

# 代码格式化
pnpm format

# 代码检查
pnpm lint

# 构建生产版本
pnpm build

# 预览生产构建
pnpm preview
```

## 📖 API 文档

启动后端后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要 API 端点

```
# 认证
POST   /api/v1/auth/register      # 用户注册
POST   /api/v1/auth/login         # 用户登录
GET    /api/v1/auth/me            # 获取当前用户

# 错题
GET    /api/v1/errors             # 获取错题列表
POST   /api/v1/errors             # 创建错题
GET    /api/v1/errors/{id}        # 获取错题详情
PUT    /api/v1/errors/{id}        # 更新错题
DELETE /api/v1/errors/{id}        # 删除错题

# AI 分析
POST   /api/v1/ai/analyze         # 分析错题
POST   /api/v1/ai/similar         # 查找相似题

# 知识图谱
GET    /api/v1/knowledge/graph    # 获取知识图谱
GET    /api/v1/knowledge/weak-points  # 薄弱点

# 练习
GET    /api/v1/practice/recommend # 推荐练习
POST   /api/v1/practice/submit    # 提交答案

# 报告
GET    /api/v1/reports/statistics # 统计数据
GET    /api/v1/reports/weekly     # 周报
```

## 🎨 界面截图

*开发中，待补充*

## 🗺️ 开发路线图

### MVP 阶段 (当前)
- [x] 项目架构设计
- [x] 用户认证系统
- [x] 错题基础管理
- [ ] AI 分析集成
- [ ] 基础数据统计

### V1.0
- [ ] OCR 图片识别
- [ ] 知识图谱可视化
- [ ] 智能练习推荐
- [ ] 完整学习报告
- [ ] 移动端适配

### V2.0
- [ ] 移动端 APP
- [ ] 社区功能
- [ ] 教师端功能
- [ ] 多人协作
- [ ] 付费功能

## 🤝 贡献

欢迎贡献代码！请先阅读 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 项目主页：https://github.com/yourusername/smart-error-book
- 问题反馈：https://github.com/yourusername/smart-error-book/issues

## 💡 致谢

感谢以下开源项目：
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

⭐ 如果这个项目对你有帮助，欢迎 Star！
