# SeaTunnel 交互式配置工具使用说明

## 📖 概述

SeaTunnel 交互式配置工具提供友好的终端交互体验，帮助用户快速配置和执行数据同步任务，无需手动编辑配置文件。

## 🎯 核心功能

### 数据源支持

| 数据源类型 | 说明 | 支持模式 |
|-----------|------|---------|
| **MySQL 数据库** | MySQL→MySQL 数据同步 | STREAMING (CDC 实时) / BATCH (批量) |
| **HTTP API** | API 数据采集到 MySQL | BATCH |
| **测试模式** | 使用 FakeSource 生成测试数据 | BATCH |

### 特色功能

- ✅ **智能数据库选择**：自动检测并列出可用的数据库，用户只需选择即可
- ✅ **智能表选择**：自动获取数据库表列表，用户只需选择即可
- ✅ **连接测试**：自动验证 MySQL 连接、数据库、表是否存在
- ✅ **错误提示**：明确的错误提示（用户名/密码错误、数据库不存在、表不存在等）
- ✅ **字段映射**：支持修改源字段到目标字段的映射关系，支持修改字段类型
- ✅ **目标表自动创建**：当目标表不存在时，可根据字段映射配置自动创建表结构
- ✅ **CDC 实时同步**：支持 MySQL binlog 监听，实时增量同步
- ✅ **upsert 模式支持**：使用字段映射时自动采用 upsert 模式，避免主键冲突
- ✅ **跨平台支持**：Windows / Linux / Mac

## 🚀 快速开始

### 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.6+ |
| SeaTunnel | 2.3.0+ |
| MySQL Connector (可选) | `pip install mysql-connector-python` |

> 💡 **提示**：安装 `mysql-connector-python` 后可启用数据库列表检测、表列表获取、连接测试等功能

### 运行脚本

```bash
# Windows
python seatunnel-interactive.py

# Linux/Mac
python3 seatunnel-interactive.py
```

## 💡 交互流程示例

### 场景 1: MySQL→MySQL CDC 实时同步

```
==================================================
  SeaTunnel 数据采集配置向导
==================================================

【步骤 1/5】选择数据源类型

选择数据源类型:
  1) MySQL 数据库
  2) HTTP API
  3) 测试模式 (使用 FakeSource)
请选择 [1-3] [默认：1]: 1

✓ 数据源：MySQL 数据库

【步骤 2/5】配置源 MySQL 数据库

--- 配置源数据库 ---

源 MySQL 主机地址 [默认：127.0.0.1]:
源 MySQL 端口 [默认：3306]:
源 MySQL 用户名： root
源 MySQL 密码： ********

可用的数据库：
  1) source_db
  2) test_db
  3) production_db

请选择数据库 [1-3] 或输入数据库名： 1
✓ 已选择数据库：source_db

正在测试 MySQL 连接...
✓ 端口 3306 可访问
✓ 数据库连接成功

数据库 'source_db' 中的表：
  1) users
  2) orders
  3) products

请选择表 [1-3] 或输入表名： 1
✓ 已选择表：users

选择作业模式:
  1) STREAMING (实时同步)
  2) BATCH (批量同步)
请选择 [1-2] [默认：1]: 1
CDC Server ID [默认：100-200]:
启动模式 [initial/earliest/latest 默认：initial]: initial

【步骤 3/5】配置目标 MySQL 数据库

--- 配置目标数据库 ---

目标 MySQL 主机地址 [默认：127.0.0.1]:
目标 MySQL 端口 [默认：3306]:
目标 MySQL 用户名： root
目标 MySQL 密码： ********

可用的数据库：
  1) target_db
  2) backup_db

请选择数据库 [1-2] 或输入数据库名： 1
✓ 已选择数据库：target_db

正在测试 MySQL 连接...
✓ 端口 3306 可访问
✓ 数据库连接成功

数据库 'target_db' 中的表：
  1) users
  2) logs

请选择表 [1-2] 或输入表名： 2
✓ 已选择表：logs

【步骤 4/5】字段映射配置

当前字段映射：
============================================================
序号   源字段名         目标字段名       字段类型   操作
============================================================
1      id               id               INT       [删除]
2      username         username         STRING     [删除]
3      email            email            STRING     [删除]
4      created_at       created_at       DATETIME   [删除]
============================================================

操作选项：
  1) 修改目标字段名
  2) 修改字段类型
  3) 删除字段
  4) 手动添加字段
  5) 完成映射

请选择操作 [1-5]: 5

✓ 字段映射配置完成

【步骤 5/5】确认配置

确认生成配置文件并执行？[y/N]: y

正在生成配置文件...
✓ 配置文件已生成

注意：CDC 模式会持续监听 MySQL binlog，任务不会自动结束
按 Ctrl+C 可以停止任务

准备执行 SeaTunnel 任务...
```

### 场景 2: MySQL→MySQL 批量同步（使用字段映射）

```
【步骤 2/5】配置源 MySQL 数据库
...
选择作业模式:
  1) STREAMING (实时同步)
  2) BATCH (批量同步)
请选择 [1-2] [默认：1]: 2

【步骤 4/5】字段映射配置

当前字段映射：
============================================================
序号   源字段名         目标字段名       字段类型   操作
============================================================
1      id               user_id          INT       [删除]
2      username         user_name        STRING     [删除]
3      email            user_email       STRING     [删除]
4      created_at       create_time      DATETIME   [删除]
============================================================

操作选项：
  1) 修改目标字段名
  2) 修改字段类型
  3) 删除字段
  4) 手动添加字段
  5) 完成映射

请选择操作 [1-5]: 5

✓ 字段映射配置完成

验证目标表结构...
目标表不存在，根据字段映射创建表结构...
执行建表SQL: CREATE TABLE `target_users` (`user_id` INT NULL, `user_name` VARCHAR(255) NULL, `user_email` VARCHAR(255) NULL, `create_time` DATETIME NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
✓ 目标表创建成功
```

### 场景 3: API→MySQL 数据采集

```
【步骤 1/5】选择数据源类型
请选择 [1-3] [默认：1]: 2

✓ 数据源：HTTP API

【步骤 2/5】配置源 API

选择 API 类型:
  1) Random User Generator API (https://randomuser.me/)
  2) 自定义 API
请选择 [1-2] [默认：1]: 2

API URL: https://api.example.com/users
HTTP 方法 [默认：GET]:
JSON 内容字段 [默认：results]: data

✓ 自定义 API 配置完成

【步骤 3/5】配置目标 MySQL 数据库
...
```

### 场景 4: 测试模式

```
【步骤 1/5】选择数据源类型
请选择 [1-3] [默认：1]: 3

✓ 数据源：测试模式 (使用 FakeSource)

【步骤 2/5】配置作业参数

作业名称 [默认：Test_Job]:
选择作业模式:
  1) STREAMING (实时同步)
  2) BATCH (批量同步)
请选择 [1-2] [默认：2]: 2
并行度 [默认：1]:

✓ 测试模式会生成 3 条测试数据并输出到控制台
```

## ⚙️ 配置参数说明

### MySQL CDC 配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| CDC Server ID | MySQL binlog 复制服务器 ID | 100-200 |
| 启动模式 | CDC 启动位置 | initial |

**启动模式说明**：

| 模式 | 说明 |
|------|------|
| `initial` | 首次全量同步，然后增量同步 |
| `earliest` | 从最早的 binlog 位置开始 |
| `latest` | 从最新的 binlog 位置开始 |

### 字段映射配置

| 操作 | 说明 |
|------|------|
| 修改目标字段名 | 将源字段映射到不同的目标字段名 |
| 修改字段类型 | 更改目标字段的数据类型 |
| 删除字段 | 从映射中移除字段 |
| 手动添加字段 | 添加新的字段映射 |
| 完成映射 | 确认并保存字段映射配置 |

**支持的字段类型**：

| 类型 | 说明 |
|------|------|
| STRING | 字符串类型 (映射为 VARCHAR(255)) |
| INT | 整数类型 |
| DATETIME | 日期时间类型 |
| BOOLEAN | 布尔类型 |

### API 配置

| 参数 | 说明 | 示例 |
|------|------|------|
| URL | API 地址 | `https://api.example.com/users` |
| Method | HTTP 方法 | GET / POST |
| Content Field | JSON 数据字段路径 | `results` / `data.items` |

**Content Field 示例**：

```json
// API 返回格式
{
  "results": [
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 30}
  ]
}
// Content Field 填写：results

// 嵌套格式
{
  "data": {
    "items": [...]
  }
}
// Content Field 填写：data.items
```

## 🛡️ 错误提示

工具会在以下情况提供明确的错误提示：

| 错误类型 | 提示信息 |
|---------|---------|
| 端口不可达 | `连接失败：端口 3306 不可达` |
| 用户名/密码错误 | `连接失败：用户名或密码错误` |
| 数据库不存在 | `连接失败：数据库 'xxx' 不存在` |
| 表不存在 | `表 'xxx' 不存在于数据库中` |
| 主键冲突 | `Duplicate entry 'xxx' for key 'PRIMARY'` (使用 upsert 模式解决) |

## 🔧 高级配置

### 安装 MySQL Connector

```bash
pip install mysql-connector-python
```

安装后可启用：
- 自动获取数据库列表
- 自动获取数据库表列表
- MySQL 连接测试
- 表存在性验证

### 环境变量配置

```bash
# Windows
set SEATUNNEL_HOME=D:\software\apache-seatunnel-2.3.5

# Linux/Mac
export SEATUNNEL_HOME=/opt/seatunnel
```

### 字段映射与 save_mode

当使用字段映射功能时，系统会自动调整 save_mode：

| 情况 | save_mode | 说明 |
|------|-----------|------|
| 不使用字段映射 | create | 创建新表 |
| 使用字段映射 | upsert | 插入或更新记录 |

**upsert 模式说明**：
- 如果记录不存在，则插入新记录
- 如果记录已存在，则更新现有记录
- 自动处理主键冲突问题

### 目标表自动创建

当目标表不存在时，系统会根据字段映射配置自动创建表结构：

1. 如果不使用字段映射：使用源表结构创建目标表
2. 如果使用字段映射：使用映射后的目标字段名和类型创建表

建表SQL示例：
```sql
CREATE TABLE `target_table` (
  `user_id` INT NULL,
  `user_name` VARCHAR(255) NULL,
  `user_email` VARCHAR(255) NULL,
  `create_time` DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## 📁 生成的配置文件

配置文件默认保存在：

| 系统 | 路径 |
|------|------|
| Windows | `%TEMP%\seatunnel\generated_config.conf` |
| Linux/Mac | `/home/admin/openclaw/workspace/temp/generated_config.conf` |

### 配置文件示例

**MySQL CDC→MySQL 实时同步（使用字段映射）**：

```hocon
env {
  job.mode = "STREAMING"
  job.name = "MySQL_to_MySQL_Sync"
  parallelism = 1
  checkpoint.interval = 10000
}

source {
  MySQL-CDC {
    base-url = "jdbc:mysql://127.0.0.1:3306/source_db?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    hostname = "127.0.0.1"
    port = 3306
    username = "root"
    password = "******"
    database-names = ["source_db"]
    table-names = ["source_db.users"]
    server-id = "100-200"
    startup.mode = "initial"
  }
}

transform {
  FieldMapper {
    field_mapper = {
      id = user_id
      username = user_name
      email = user_email
      created_at = create_time
    }
  }
}

sink {
  Jdbc {
    url = "jdbc:mysql://127.0.0.1:3306/target_db?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "root"
    password = "******"
    database = "target_db"
    table = "target_users"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "upsert"
    primary_keys = ["user_id"]
  }
}
```

**MySQL BATCH→MySQL 批量同步（不使用字段映射）**：

```hocon
env {
  job.mode = "BATCH"
  job.name = "MySQL_to_MySQL_Sync"
  parallelism = 1
}

source {
  Jdbc {
    url = "jdbc:mysql://127.0.0.1:3306/source_db?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "root"
    password = "******"
    database = "source_db"
    table = "users"
  }
}

sink {
  Jdbc {
    url = "jdbc:mysql://127.0.0.1:3306/target_db?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "root"
    password = "******"
    database = "target_db"
    table = "users"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "create"
  }
}
```

## 🐛 故障排查

### 问题 1: 未安装 mysql-connector-python

**现象**：
```
警告：未安装 mysql-connector-python，无法获取数据库列表
警告：未安装 mysql-connector-python，无法获取表列表
```

**解决**：
```bash
pip install mysql-connector-python
```

### 问题 2: 字段不匹配

**现象**：
```
java.sql.SQLSyntaxErrorException: Unknown column 'name' in 'field list'
```

**原因**：源表和目标表字段不一致

**解决**：
1. 确保目标表结构与源表一致
2. 或使用字段映射功能调整映射关系
3. 或让系统自动创建目标表

### 问题 3: 主键冲突

**现象**：
```
Duplicate entry '1' for key 'testtable.PRIMARY'
```

**原因**：使用 append 模式时，目标表已存在相同主键的记录

**解决**：
1. 使用字段映射功能（系统会自动采用 upsert 模式）
2. 或手动清空目标表数据后重新执行

### 问题 4: CDC 任务立即结束

**原因**：STREAMING 模式需要 MySQL 开启 binlog

**解决**：
```sql
-- 检查 binlog 是否开启
SHOW VARIABLES LIKE 'log_bin';

-- MySQL 配置文件 my.cnf 添加
[mysqld]
log-bin=mysql-bin
binlog-format=ROW
server-id=1
```

### 问题 5: 连接超时

**解决**：
1. 检查 MySQL 服务是否运行
2. 检查防火墙是否开放端口
3. 检查 MySQL 用户是否有远程连接权限

```sql
-- 授予远程连接权限
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'password';
FLUSH PRIVILEGES;
```

### 问题 6: 自动创建表时字段类型为 null

**现象**：
```
java.sql.SQLException: Invalid column type: null
```

**原因**：使用字段映射时，SeaTunnel 无法正确推断字段类型

**解决**：
1. 系统会自动采用 upsert 模式，避免自动建表
2. 目标表不存在时，系统会根据字段映射手动创建表结构

## 📞 技术支持

如有问题，请检查：
1. SeaTunnel 是否正确安装
2. Python 版本是否符合要求 (3.6+)
3. MySQL 连接信息是否正确
4. 源表和目标表结构是否一致
5. 字段映射配置是否正确

---

**最后更新**: 2026-04-23
**版本**: 2.1.0
