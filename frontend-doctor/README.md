# 智能医疗诊断平台 - 医生端Web管理后台

## 项目简介

这是基于多智能体协同的智能医疗诊断平台的医生端Web管理后台，采用Vue 3 + Ant Design Vue构建。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **UI组件库**: Ant Design Vue 4
- **图表库**: ECharts 5
- **HTTP客户端**: Axios
- **构建工具**: Vite 5

## 项目结构

```
frontend-doctor/
├── src/
│   ├── views/              # 页面视图
│   │   ├── Login.vue       # 登录页
│   │   ├── Dashboard.vue   # 仪表盘
│   │   ├── Patients.vue    # 患者管理
│   │   ├── Conversations.vue # 会话管理
│   │   ├── Diagnosis.vue   # 辅助诊断界面
│   │   ├── Knowledge.vue   # 知识库查询
│   │   └── Records.vue     # 病历管理
│   ├── components/         # 公共组件
│   │   └── Layout.vue      # 布局组件
│   ├── api/               # API调用封装
│   │   ├── request.js     # Axios请求封装
│   │   ├── auth.js        # 认证相关API
│   │   ├── patients.js    # 患者管理API
│   │   ├── conversations.js # 会话管理API
│   │   ├── medicalRecords.js # 病历管理API
│   │   ├── knowledge.js    # 知识库API
│   │   └── diagnosis.js    # 诊断相关API
│   ├── store/             # Pinia状态管理
│   │   └── auth.js        # 认证状态管理
│   ├── router/            # 路由配置
│   │   └── index.js       # 路由定义
│   ├── App.vue            # 根组件
│   └── main.js            # 应用入口
├── index.html             # HTML模板
├── vite.config.js        # Vite配置
├── package.json          # 项目依赖
└── README.md             # 项目说明
```

## 功能模块

### 1. 登录认证
- 用户登录
- Token管理
- 路由守卫

### 2. 仪表盘
- 统计数据展示（今日咨询、待处理病历、活跃患者、诊断准确率）
- 最近会话列表
- 待审核病历列表

### 3. 患者管理
- 患者列表查询
- 患者详情查看
- 患者会话记录查看
- 患者信息管理

### 4. 会话管理
- 会话列表查询（支持状态筛选）
- 会话详情查看
- 消息记录查看
- 会话状态管理

### 5. 辅助诊断
- 会话选择
- 患者主诉展示
- 结构化病历编辑
- AI诊断建议展示
- 智能体分析展示
- 数据可视化（ECharts）
- 诊断提交

### 6. 知识库查询
- 关键词搜索（疾病、症状、药物等）
- 搜索结果展示
- 知识图谱可视化
- 临床指南查看

### 7. 病历管理
- 病历列表查询（支持状态筛选）
- 病历详情查看
- 病历审核
- 病历归档
- 新建病历

## 安装与运行

### 1. 安装依赖

```bash
npm install
```

### 2. 开发环境运行

```bash
npm run dev
```

访问 http://localhost:3001

### 3. 生产环境构建

```bash
npm run build
```

构建产物在 `dist` 目录

### 4. 预览构建结果

```bash
npm run preview
```

## 配置说明

### API代理配置

在 `vite.config.js` 中配置了API代理：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### 环境变量

可以创建 `.env` 文件配置环境变量：

```
VITE_API_BASE_URL=http://localhost:8000
```

## API接口说明

所有API接口定义在 `src/api/` 目录下，统一使用 `/api` 前缀，实际请求会被代理到后端服务。

### 主要API模块

- **认证**: `/api/v1/auth/*`
- **患者管理**: `/api/v1/patients/*`
- **会话管理**: `/api/v1/conversations/*`
- **病历管理**: `/api/v1/medical_records/*`
- **知识库**: `/api/v1/knowledge/*`
- **诊断**: `/api/v1/diagnosis/*`

## 路由说明

- `/login` - 登录页
- `/dashboard` - 仪表盘（默认首页）
- `/patients` - 患者管理
- `/conversations` - 会话管理
- `/diagnosis` - 辅助诊断
- `/knowledge` - 知识库查询
- `/records` - 病历管理

所有路由（除登录页外）都需要认证，未登录用户会被重定向到登录页。

## 状态管理

使用Pinia进行状态管理，当前包含：

- **auth store**: 管理用户认证状态、Token、用户信息等

## 注意事项

1. 确保后端API服务已启动（默认端口8000）
2. 登录后Token会存储在localStorage中
3. 所有API请求会自动携带Authorization头
4. 401错误会自动跳转到登录页

## 开发规范

1. 使用Composition API编写组件
2. 使用TypeScript类型定义（可选）
3. 遵循Vue 3和Ant Design Vue的最佳实践
4. API调用统一使用封装的request方法
5. 错误处理统一在request拦截器中处理

## License

ISC

