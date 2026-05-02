# 医疗健康咨询患者端小程序

基于微信小程序开发的医疗健康咨询与辅助诊断系统患者端应用。

## 项目结构

```
frontend-patient/
├── app.js                 # 小程序入口文件
├── app.json              # 小程序全局配置
├── project.config.json    # 项目配置文件
├── sitemap.json          # 站点地图配置
├── package.json          # 项目依赖配置
│
└── src/
    ├── pages/            # 页面目录
    │   ├── index/        # 首页
    │   ├── consultation/ # 咨询对话页（WebSocket实时通信）
    │   ├── upload/       # 报告上传页
    │   ├── reminders/    # 用药提醒页
    │   └── profile/      # 个人中心
    │
    ├── components/       # 组件目录
    │   ├── ChatBubble/   # 聊天气泡组件
    │   ├── FileUploader/# 文件上传组件
    │   └── ReminderCard/ # 提醒卡片组件
    │
    ├── api/              # API调用封装
    │   ├── auth.js       # 认证相关API
    │   ├── conversations.js # 会话相关API
    │   └── messages.js   # 消息相关API
    │
    ├── utils/            # 工具函数
    │   ├── request.js    # 网络请求封装
    │   ├── websocket.js  # WebSocket封装
    │   └── helpers.js   # 辅助函数
    │
    └── store/            # 状态管理
        └── conversation.js # 会话状态管理
```

## 功能特性

### 1. 首页（index）
- 用户信息展示
- 快捷操作入口（开始咨询、上传报告、用药提醒）
- 最近咨询记录列表

### 2. 咨询对话页（consultation）
- 实时消息对话（WebSocket）
- 消息发送和接收
- 图片上传功能
- 自动滚动到底部
- 连接状态指示

### 3. 报告上传页（upload）
- 支持图片和文件上传
- 上传进度显示
- 文件预览和删除
- 报告提交功能

### 4. 用药提醒页（reminders）
- 提醒列表展示（进行中/已完成）
- 创建提醒
- 标记完成
- 编辑和删除提醒

### 5. 个人中心（profile）
- 用户信息展示
- 登录/退出登录
- 菜单导航
- 设置和关于

## 技术栈

- **框架**: 微信小程序原生框架
- **网络请求**: 封装的 wx.request
- **实时通信**: WebSocket（wx.connectSocket）
- **状态管理**: 自定义 store 模块
- **UI组件**: 自定义组件（ChatBubble、FileUploader、ReminderCard）

## 配置说明

### 1. API配置

在 `app.js` 中配置API基础URL：

```javascript
// 开发环境
this.globalData.apiBaseUrl = 'http://localhost:8000/api/v1'
this.globalData.wsBaseUrl = 'ws://localhost:8000/ws'

// 生产环境
this.globalData.apiBaseUrl = 'https://your-domain.com/api/v1'
this.globalData.wsBaseUrl = 'wss://your-domain.com/ws'
```

### 2. 小程序配置

在 `project.config.json` 中配置小程序AppID：

```json
{
  "appid": "your-appid"
}
```

## 使用说明

### 1. 安装依赖

本项目为微信小程序项目，不需要npm安装依赖。直接使用微信开发者工具打开即可。

### 2. 开发调试

1. 使用微信开发者工具打开项目目录
2. 配置小程序AppID（测试号或正式号）
3. 在 `app.js` 中配置正确的API地址
4. 开始开发和调试

### 3. 构建发布

1. 在微信开发者工具中点击"上传"
2. 填写版本号和项目备注
3. 上传成功后，在微信公众平台提交审核
4. 审核通过后发布

## API接口说明

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/logout` - 用户登出
- `GET /api/v1/auth/me` - 获取当前用户信息
- `PUT /api/v1/auth/me` - 更新用户信息
- `POST /api/v1/auth/change-password` - 修改密码

### 会话相关
- `POST /api/v1/conversations` - 创建会话
- `GET /api/v1/conversations` - 获取会话列表
- `GET /api/v1/conversations/{id}` - 获取会话详情
- `PUT /api/v1/conversations/{id}` - 更新会话
- `DELETE /api/v1/conversations/{id}` - 删除会话

### 消息相关
- `POST /api/v1/messages` - 发送消息
- `GET /api/v1/messages/conversation/{id}` - 获取会话消息列表
- `POST /api/v1/messages/mark-read` - 标记消息已读
- `GET /api/v1/messages/conversation/{id}/unread-count` - 获取未读消息数

### WebSocket
- `ws://domain/ws/conversation/{conversation_id}?token={token}` - 会话WebSocket连接
- `ws://domain/ws/user?token={token}` - 用户WebSocket连接

## 注意事项

1. **网络请求**: 所有API请求都需要在微信公众平台配置服务器域名
2. **WebSocket**: WebSocket连接也需要在微信公众平台配置域名
3. **文件上传**: 文件上传功能需要后端支持，目前为模拟实现
4. **提醒功能**: 提醒功能需要后端API支持，目前为模拟数据
5. **登录状态**: Token存储在本地存储中，应用启动时自动检查登录状态

## 开发建议

1. **错误处理**: 所有API调用都应包含错误处理逻辑
2. **加载状态**: 异步操作应显示加载提示
3. **用户体验**: 重要操作应有确认提示
4. **性能优化**: 长列表应使用虚拟滚动或分页加载
5. **代码规范**: 遵循微信小程序开发规范

## 待实现功能

- [ ] 图片上传功能完整实现
- [ ] 文件预览功能
- [ ] 提醒功能后端对接
- [ ] 消息推送通知
- [ ] 离线消息缓存
- [ ] 消息搜索功能
- [ ] 语音消息支持
- [ ] 视频通话功能

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现基础页面和功能
- WebSocket实时通信
- 文件上传基础功能

## 许可证

ISC

