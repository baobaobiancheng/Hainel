# 基于多智能体协同的医疗健康咨询与辅助诊断系统

## 项目简介

本项目旨在构建一个基于多智能体协同的医疗健康咨询与辅助诊断系统，通过多个专业化智能体的协作，为患者提供初步健康咨询服务，并为医生提供智能化的辅助诊断支持。

## 项目结构

```
medical-multi-agent-system/
├── backend/              # 后端服务（FastAPI）
├── frontend-patient/     # 患者端（小程序）
├── frontend-doctor/      # 医生端（Web管理后台）
├── docker/              # Docker配置
├── docs/                # 文档
└── 代码框架设计.md       # 详细框架设计文档
```

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: MySQL, Redis
- **ORM**: SQLAlchemy
- **AI框架**: LangChain, Transformers
- **异步任务**: Celery

### 前端
- **患者端**: Uni-app / Taro（小程序）
- **医生端**: Vue.js + Ant Design

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 修改 .env 中的配置
uvicorn app.main:app --reload
```

### 前端

详见各前端目录下的 README.md

## 文档

- [代码框架设计](./代码框架设计.md)
- [代码框架架构图](./代码框架架构图.md)
- [设计方案（优化版）](./设计方案（优化版）.md)

## 开发计划

1. ✅ 代码框架设计
2. ⏳ 后端基础框架搭建
3. ⏳ 多智能体系统实现
4. ⏳ 前端界面开发
5. ⏳ 系统集成测试

## 许可证

[待定]

