# 初始化脚本说明

本目录包含数据库初始化和管理相关的脚本。

## 脚本列表

### 1. `init_db.py` - 数据库初始化

**用途：** 创建数据库、初始化表结构

**使用方法：**
```bash
cd backend
python scripts/init_db.py
```

**功能：**
- 创建数据库（如果不存在）
- 验证数据库连接
- 初始化数据库表（可选，也可以直接使用 init_database.sql 文件）

**注意：**
- 也可以直接使用 `init_database.sql` 文件来初始化数据库
- 此脚本主要用于开发环境快速初始化

### 2. `seed_data.py` - 种子数据

**用途：** 插入测试数据和基础配置数据

**使用方法：**
```bash
cd backend
python scripts/seed_data.py
```

**功能：**
- 创建管理员用户（admin / admin123）
- 创建测试医生用户（doctor1 / doctor123）
- 创建测试患者用户（patient1 / patient123）

**注意：**
- ⚠️ 这些是测试账户，生产环境请修改密码
- 重复运行不会创建重复数据（会检查是否已存在）

## 使用流程

### 首次初始化

```bash
# 方式1：使用 SQL 文件（推荐）
mysql -u root -p < init_database.sql

# 方式2：使用 Python 脚本
python scripts/init_db.py

# 2. 插入种子数据
python scripts/seed_data.py
```

### 日常开发

```bash
# 如果需要重置数据
python scripts/seed_data.py

# 如果需要修改表结构，直接修改 init_database.sql 并重新执行
```

## 添加新脚本

1. 在 `scripts/` 目录下创建新的 Python 文件
2. 添加必要的导入和路径设置
3. 实现脚本逻辑
4. 添加 `if __name__ == "__main__":` 入口
5. 在本文档中添加说明

## 注意事项

- ⚠️ 所有脚本都会连接到实际数据库，请谨慎使用
- ⚠️ 生产环境使用前请先备份数据库
- ✅ 脚本设计为可重复运行（幂等性）
- ✅ 使用日志记录操作过程

