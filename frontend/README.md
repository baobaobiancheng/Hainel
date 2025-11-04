# Smart Error Book - Frontend

基于 Vue 3 + TypeScript + Vite 的前端应用。

## 快速开始

### 安装依赖

```bash
# 推荐使用 pnpm
pnpm install
```

### 开发

```bash
pnpm dev
```

访问 http://localhost:5173

### 构建

```bash
pnpm build
```

### 预览

```bash
pnpm preview
```

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 请求
│   ├── assets/           # 静态资源
│   ├── components/       # 组件
│   ├── composables/      # 组合式函数
│   ├── layouts/          # 布局
│   ├── router/           # 路由
│   ├── stores/           # 状态管理
│   ├── types/            # TypeScript 类型
│   ├── utils/            # 工具函数
│   ├── views/            # 页面
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口
├── package.json
├── vite.config.ts
└── README.md
```

## 技术栈

- Vue 3 (Composition API)
- TypeScript
- Vite
- Pinia (状态管理)
- Vue Router
- Element Plus (UI 组件库)
- Axios (HTTP 客户端)
- ECharts (图表)

## 开发

### 代码规范

```bash
# ESLint 检查
pnpm lint

# 格式化代码
pnpm format
```

### 类型检查

```bash
pnpm vue-tsc
```

