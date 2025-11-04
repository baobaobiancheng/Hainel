# 快速启动指南

## 🚀 5分钟快速体验

### 方式一：使用 Docker Compose（最简单）

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd smart-error-book

# 2. 启动所有服务（包括数据库、Redis、后端、前端）
docker-compose up -d

# 3. 等待服务启动完成（约30秒）
docker-compose logs -f

# 4. 访问应用
# 前端：http://localhost:5173
# 后端API：http://localhost:8000
# API文档：http://localhost:8000/docs
```

### 方式二：本地开发（推荐开发者）

#### 前置准备
- Python 3.11+
- Node.js 20+
- PostgreSQL 16
- Redis 7

#### 步骤 1：启动数据库和 Redis

```bash
# 使用 Docker 快速启动数据库
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=smart_error_book \
  -p 5432:5432 \
  postgres:16-alpine

docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### 步骤 2：启动后端

```bash
# 进入后端目录
cd backend

# 安装 uv（如果未安装）
pip install uv

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，确保数据库连接正确

# 运行数据库迁移
uv run alembic upgrade head

# 启动后端服务
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端将运行在：**http://localhost:8000**

#### 步骤 3：启动前端

```bash
# 新开一个终端，进入前端目录
cd frontend

# 安装 pnpm（如果未安装）
npm install -g pnpm

# 安装依赖
pnpm install

# 启动前端服务
pnpm dev
```

前端将运行在：**http://localhost:5173**

## 📝 首次使用

### 1. 注册账号

访问 http://localhost:5173/auth/register

- 用户名：至少3个字符
- 邮箱：有效的邮箱格式
- 密码：至少6个字符

### 2. 登录系统

使用刚注册的账号登录

### 3. 添加第一道错题

1. 点击左侧菜单「错题本」
2. 点击「添加错题」按钮
3. 填写错题信息：
   - 学科：如「数学」
   - 章节：如「二次函数」
   - 题目内容
   - 正确答案
   - 我的答案
4. 点击「提交」

### 4. 查看错题列表

在错题本页面可以看到所有录入的错题

## 🔍 验证安装

### 检查后端

```bash
# 访问健康检查接口
curl http://localhost:8000/health

# 应该返回
# {"status":"healthy","app":"Smart Error Book","version":"0.1.0","environment":"development"}

# 访问 API 文档
# 浏览器打开 http://localhost:8000/docs
```

### 检查前端

```bash
# 浏览器访问 http://localhost:5173
# 应该看到登录页面
```

### 检查数据库

```bash
# 连接 PostgreSQL
psql -h localhost -U postgres -d smart_error_book

# 查看表
\dt

# 应该看到以下表：
# users
# error_questions
# knowledge_points
# question_knowledge_mappings
# ai_analyses
# practice_records
```

## ⚙️ 环境配置说明

### 后端环境变量（backend/.env）

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/smart_error_book

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT 密钥（生产环境务必修改）
SECRET_KEY=your-very-secure-secret-key-min-32-chars

# AI API（可选）
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

### 前端环境变量（frontend/.env）

```bash
# API 地址
VITE_API_BASE_URL=http://localhost:8000/api
```

## 🐛 常见问题

### Q1: 后端启动失败，提示数据库连接错误

**A**: 检查 PostgreSQL 是否正常运行，端口是否正确

```bash
# 检查 PostgreSQL 状态
docker ps | grep postgres

# 或本地安装的 PostgreSQL
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

### Q2: 前端启动失败，提示端口占用

**A**: 修改 Vite 配置或停止占用端口的进程

```bash
# 查看端口占用
lsof -i :5173  # macOS/Linux
netstat -ano | findstr :5173  # Windows

# 修改端口（vite.config.ts）
server: {
  port: 3000,  # 改为其他端口
}
```

### Q3: uv 命令找不到

**A**: 确保已安装 uv

```bash
pip install uv

# 或使用 pipx
pipx install uv
```

### Q4: pnpm 命令找不到

**A**: 安装 pnpm

```bash
npm install -g pnpm

# 或使用 npx
npx pnpm install
```

### Q5: 数据库迁移失败

**A**: 删除迁移记录重新初始化

```bash
cd backend

# 删除现有迁移版本
rm -rf alembic/versions/*.py

# 重新创建迁移
uv run alembic revision --autogenerate -m "init"
uv run alembic upgrade head
```

## 🔧 开发技巧

### 热重载

- **后端**：使用 `--reload` 参数，代码修改后自动重启
- **前端**：Vite 自带热更新，保存即生效

### 调试

#### 后端调试
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 VSCode 调试配置
```

#### 前端调试
```typescript
// 使用浏览器开发者工具
console.log('debug info')
debugger;  // 断点
```

### 数据库查询日志

```python
# backend/app/config.py
# 设置 DEBUG=True 可以看到 SQL 查询日志
```

## 📚 下一步

1. **阅读完整文档**：[README.md](README.md)
2. **查看系统架构**：[智能错题本系统架构.md](智能错题本系统架构.md)
3. **API 文档**：http://localhost:8000/docs
4. **开发指南**：
   - [后端开发](backend/README.md)
   - [前端开发](frontend/README.md)

## 💡 最佳实践

### 代码提交前

```bash
# 后端
cd backend
uv run black .
uv run ruff check .
uv run pytest

# 前端
cd frontend
pnpm lint
pnpm format
pnpm vue-tsc
```

### 生产部署

参考 [README.md](README.md) 中的生产部署章节

---

🎉 **恭喜！您已成功启动智能错题本系统！**

有问题？[提交 Issue](https://github.com/yourusername/smart-error-book/issues)

