# SeaTunnel 数据采集管理平台 - REST API 接口设计

---

## 📋 接口概览

| 模块 | 接口数量 | 说明 |
|------|----------|------|
| 数据源管理 | 8 | 数据源的 CRUD、连接测试、元数据发现 |
| 任务管理 | 10 | 任务的 CRUD、执行控制、状态查询 |
| 执行历史 | 4 | 执行记录查询、日志查看 |
| 调度管理 | 4 | 定时任务的启用/禁用 |
| 系统管理 | 3 | 健康检查、配置导出导入 |
| **合计** | **29** | |

---

## 🔐 通用规范

### 响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1713254400000
}
```

### 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 501 | SeaTunnel 执行失败 |

---

## 一、数据源管理 API

### 1.1 创建数据源

```http
POST /api/v1/data-sources
Content-Type: application/json
```

**请求体：**
```json
{
  "name": "MySQL_生产库",
  "type": "MYSQL",
  "description": "生产环境 MySQL 数据库",
  "host": "192.168.1.100",
  "port": 3306,
  "databaseName": "production_db",
  "username": "root",
  "password": "encrypted_password",
  "status": 1
}
```

**响应：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "MySQL_生产库",
    "type": "MYSQL",
    "createdAt": "2026-04-16T14:00:00"
  }
}
```

---

### 1.2 更新数据源

```http
PUT /api/v1/data-sources/{id}
Content-Type: application/json
```

**请求体：**
```json
{
  "name": "MySQL_生产库_更新",
  "host": "192.168.1.200",
  "password": "new_encrypted_password"
}
```

---

### 1.3 删除数据源

```http
DELETE /api/v1/data-sources/{id}
```

**响应：**
```json
{
  "code": 200,
  "message": "删除成功",
  "data": {
    "id": 1,
    "deleted": true
  }
}
```

---

### 1.4 获取数据源详情

```http
GET /api/v1/data-sources/{id}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "MySQL_生产库",
    "type": "MYSQL",
    "host": "192.168.1.100",
    "port": 3306,
    "databaseName": "production_db",
    "username": "root",
    "password": "******",
    "status": 1,
    "createdAt": "2026-04-16T14:00:00",
    "updatedAt": "2026-04-16T14:30:00"
  }
}
```

---

### 1.5 获取数据源列表

```http
GET /api/v1/data-sources
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | String | 否 | 筛选类型：MYSQL / API |
| status | Integer | 否 | 筛选状态：0 / 1 |
| page | Integer | 否 | 页码，默认 1 |
| size | Integer | 否 | 每页数量，默认 10 |

**响应：**
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": 1,
        "name": "MySQL_生产库",
        "type": "MYSQL",
        "host": "192.168.1.100",
        "status": 1,
        "createdAt": "2026-04-16T14:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 10
  }
}
```

---

### 1.6 测试数据源连接 ⭐

```http
POST /api/v1/data-sources/test-connection
Content-Type: application/json
```

**请求体：**
```json
{
  "type": "MYSQL",
  "host": "192.168.1.100",
  "port": 3306,
  "databaseName": "production_db",
  "username": "root",
  "password": "qwer123."
}
```

**响应（成功）：**
```json
{
  "code": 200,
  "message": "连接成功",
  "data": {
    "success": true,
    "message": "MySQL 连接成功，版本：8.0.32",
    "latency": 45
  }
}
```

**响应（失败）：**
```json
{
  "code": 500,
  "message": "连接失败",
  "data": {
    "success": false,
    "message": "Access denied for user 'root'@'192.168.1.100'",
    "errorCode": "CONNECTION_FAILED"
  }
}
```

---

### 1.7 获取数据库列表 ⭐

```http
GET /api/v1/data-sources/{id}/databases
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "databases": [
      "information_schema",
      "mysql",
      "production_db",
      "test_db"
    ]
  }
}
```

---

### 1.8 获取表列表 ⭐

```http
GET /api/v1/data-sources/{id}/tables
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| database | String | 是 | 数据库名 |

**响应：**
```json
{
  "code": 200,
  "data": {
    "database": "production_db",
    "tables": [
      {
        "tableName": "users",
        "tableType": "TABLE",
        "rowCount": 10000,
        "comment": "用户表"
      },
      {
        "tableName": "orders",
        "tableType": "TABLE",
        "rowCount": 50000,
        "comment": "订单表"
      }
    ]
  }
}
```

---

### 1.9 获取表字段信息 ⭐

```http
GET /api/v1/data-sources/{id}/columns
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| database | String | 是 | 数据库名 |
| table | String | 是 | 表名 |

**响应：**
```json
{
  "code": 200,
  "data": {
    "database": "production_db",
    "table": "users",
    "columns": [
      {
        "columnName": "id",
        "dataType": "BIGINT",
        "nullable": false,
        "isPrimaryKey": true,
        "comment": "主键 ID"
      },
      {
        "columnName": "username",
        "dataType": "VARCHAR(50)",
        "nullable": false,
        "isPrimaryKey": false,
        "comment": "用户名"
      },
      {
        "columnName": "email",
        "dataType": "VARCHAR(100)",
        "nullable": true,
        "isPrimaryKey": false,
        "comment": "邮箱"
      },
      {
        "columnName": "created_at",
        "dataType": "DATETIME",
        "nullable": false,
        "isPrimaryKey": false,
        "comment": "创建时间"
      }
    ]
  }
}
```

---

## 二、任务管理 API

### 2.1 创建任务

```http
POST /api/v1/jobs
Content-Type: application/json
```

**请求体：**
```json
{
  "jobName": "用户数据同步任务",
  "jobDescription": "从生产库同步用户数据到数仓",
  "sourceId": 1,
  "sourceType": "MYSQL",
  "sourceDatabase": "production_db",
  "sourceTable": "users",
  "whereCondition": "status = 1",
  "isIncremental": 1,
  "incrementalColumn": "updated_at",
  "incrementalStartValue": "2024-01-01 00:00:00",
  
  "sinkType": "MYSQL",
  "sinkHost": "192.168.1.200",
  "sinkPort": 3306,
  "sinkDatabase": "warehouse",
  "sinkUsername": "root",
  "sinkPassword": "encrypted_password",
  "sinkTable": "dim_users",
  "primaryKeys": "id",
  "batchSize": 1000,
  
  "fieldMapping": [
    {"sourceField": "id", "targetField": "id", "fieldType": "BIGINT"},
    {"sourceField": "username", "targetField": "user_name", "fieldType": "STRING"},
    {"sourceField": "email", "targetField": "email", "fieldType": "STRING"},
    {"sourceField": "created_at", "targetField": "created_time", "fieldType": "DATETIME"}
  ],
  
  "scheduleType": "CRON",
  "cronExpression": "0 0 2 * * ?",
  "timezone": "Asia/Shanghai",
  "retryTimes": 3,
  
  "jobMode": "STREAMING",
  "parallelism": 1,
  "checkpointInterval": 10000,
  
  "status": 1
}
```

**响应：**
```json
{
  "code": 200,
  "message": "任务创建成功",
  "data": {
    "id": 1,
    "jobName": "用户数据同步任务",
    "status": 1,
    "createdAt": "2026-04-16T14:00:00"
  }
}
```

---

### 2.2 更新任务

```http
PUT /api/v1/jobs/{id}
Content-Type: application/json
```

---

### 2.3 删除任务

```http
DELETE /api/v1/jobs/{id}
```

---

### 2.4 获取任务详情

```http
GET /api/v1/jobs/{id}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "jobName": "用户数据同步任务",
    "sourceId": 1,
    "sourceName": "MySQL_生产库",
    "sourceTable": "users",
    "sinkTable": "dim_users",
    "scheduleType": "CRON",
    "cronExpression": "0 0 2 * * ?",
    "status": 1,
    "lastRunTime": "2026-04-16T02:00:00",
    "lastRunStatus": "SUCCESS",
    "fieldMapping": [...],
    "createdAt": "2026-04-16T14:00:00",
    "updatedAt": "2026-04-16T14:30:00"
  }
}
```

---

### 2.5 获取任务列表

```http
GET /api/v1/jobs
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sourceId | Long | 否 | 按数据源筛选 |
| status | Integer | 否 | 按状态筛选 |
| scheduleType | String | 否 | 按调度类型筛选 |
| page | Integer | 否 | 页码 |
| size | Integer | 否 | 每页数量 |

---

### 2.6 启动任务 ⭐

```http
POST /api/v1/jobs/{id}/start
```

**响应：**
```json
{
  "code": 200,
  "message": "任务已启动",
  "data": {
    "jobId": 1,
    "executionId": "1097046195525648385",
    "startTime": "2026-04-16T14:45:00",
    "status": "RUNNING"
  }
}
```

---

### 2.7 停止任务 ⭐

```http
POST /api/v1/jobs/{id}/stop
```

**请求体：**
```json
{
  "reason": "用户手动停止"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "任务已停止",
  "data": {
    "jobId": 1,
    "executionId": "1097046195525648385",
    "stopTime": "2026-04-16T14:50:00",
    "status": "CANCELLED"
  }
}
```

---

### 2.8 获取任务状态 ⭐

```http
GET /api/v1/jobs/{id}/status
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "jobId": 1,
    "executionId": "1097046195525648385",
    "status": "RUNNING",
    "startTime": "2026-04-16T14:45:00",
    "duration": 300,
    "metrics": {
      "readRows": 10000,
      "writeRows": 10000,
      "readBytes": 5242880,
      "writeBytes": 5242880
    },
    "checkpoint": {
      "lastCheckpointId": 5,
      "lastCheckpointTime": "2026-04-16T14:49:50"
    }
  }
}
```

---

### 2.9 生成 SeaTunnel 配置 ⭐

```http
POST /api/v1/jobs/{id}/generate-config
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "configContent": "env {\n  job.mode = \"STREAMING\"\n  job.name = \"用户数据同步任务\"\n  parallelism = 1\n  checkpoint.interval = 10000\n}\n\nsource {\n  MySQL-CDC {\n    base-url = \"jdbc:mysql://192.168.1.100:3306/production_db?useSSL=false...\"\n    ...\n  }\n}\n\nsink {\n  Jdbc {\n    url = \"jdbc:mysql://192.168.1.200:3306/warehouse?...\"\n    ...\n  }\n}",
    "configPath": "/tmp/seatunnel/job_1_config.conf"
  }
}
```

---

### 2.10 预览数据 ⭐

```http
POST /api/v1/jobs/{id}/preview
```

**请求体：**
```json
{
  "limit": 10
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "columns": ["id", "username", "email", "created_at"],
    "rows": [
      [1, "user1", "user1@example.com", "2024-01-01 10:00:00"],
      [2, "user2", "user2@example.com", "2024-01-02 11:00:00"],
      [3, "user3", "user3@example.com", "2024-01-03 12:00:00"]
    ],
    "total": 10000,
    "previewCount": 10
  }
}
```

---

## 三、执行历史 API

### 3.1 获取执行历史列表

```http
GET /api/v1/jobs/{jobId}/executions
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | String | 否 | 筛选状态 |
| startDate | String | 否 | 开始日期 |
| endDate | String | 否 | 结束日期 |
| page | Integer | 否 | 页码 |
| size | Integer | 否 | 每页数量 |

**响应：**
```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": 101,
        "executionId": "1097046195525648385",
        "startTime": "2026-04-16T02:00:00",
        "endTime": "2026-04-16T02:15:00",
        "durationSeconds": 900,
        "status": "SUCCESS",
        "triggerType": "CRON",
        "metricsReadRows": 10000,
        "metricsWriteRows": 10000
      },
      {
        "id": 100,
        "executionId": "1097046195525648384",
        "startTime": "2026-04-15T02:00:00",
        "endTime": "2026-04-15T02:10:00",
        "durationSeconds": 600,
        "status": "FAILED",
        "triggerType": "CRON",
        "errorMessage": "Connection timeout"
      }
    ],
    "total": 50,
    "page": 1,
    "size": 10
  }
}
```

---

### 3.2 获取执行详情

```http
GET /api/v1/executions/{id}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "id": 101,
    "jobId": 1,
    "jobName": "用户数据同步任务",
    "executionId": "1097046195525648385",
    "startTime": "2026-04-16T02:00:00",
    "endTime": "2026-04-16T02:15:00",
    "durationSeconds": 900,
    "status": "SUCCESS",
    "triggerType": "CRON",
    "seatunnelConfig": "...",
    "seatunnelLogPath": "/logs/seatunnel/job_1_20260416020000.log",
    "metrics": {
      "readRows": 10000,
      "writeRows": 10000,
      "readBytes": 5242880,
      "writeBytes": 5242880
    }
  }
}
```

---

### 3.3 查看执行日志 ⭐

```http
GET /api/v1/executions/{id}/log
```

**查询参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lines | Integer | 否 | 返回行数，默认 100 |
| offset | Integer | 否 | 偏移量 |

**响应：**
```json
{
  "code": 200,
  "data": {
    "executionId": "1097046195525648385",
    "logPath": "/logs/seatunnel/job_1_20260416020000.log",
    "lines": [
      "2026-04-16 02:00:00 INFO Job started",
      "2026-04-16 02:00:01 INFO Connecting to source database...",
      "2026-04-16 02:00:02 INFO Connection established",
      "2026-04-16 02:00:05 INFO Reading data from table users...",
      "2026-04-16 02:15:00 INFO Job completed successfully"
    ],
    "totalLines": 150
  }
}
```

---

### 3.4 重试执行 ⭐

```http
POST /api/v1/executions/{id}/retry
```

**说明：** 基于历史执行配置重新运行任务

---

## 四、调度管理 API

### 4.1 启用调度

```http
POST /api/v1/jobs/{id}/schedule/enable
```

---

### 4.2 禁用调度

```http
POST /api/v1/jobs/{id}/schedule/disable
```

---

### 4.3 立即执行一次 ⭐

```http
POST /api/v1/jobs/{id}/schedule/trigger-now
```

**响应：**
```json
{
  "code": 200,
  "message": "任务已触发执行",
  "data": {
    "jobId": 1,
    "executionId": "1097046195525648386",
    "triggerTime": "2026-04-16T14:50:00"
  }
}
```

---

### 4.4 获取调度信息

```http
GET /api/v1/jobs/{id}/schedule
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "jobId": 1,
    "scheduleType": "CRON",
    "cronExpression": "0 0 2 * * ?",
    "timezone": "Asia/Shanghai",
    "isActive": true,
    "lastRunTime": "2026-04-16T02:00:00",
    "nextRunTime": "2026-04-17T02:00:00"
  }
}
```

---

## 五、系统管理 API

### 5.1 健康检查

```http
GET /api/v1/health
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "status": "UP",
    "timestamp": "2026-04-16T14:50:00",
    "components": {
      "database": "UP",
      "seatunnel": "UP",
      "scheduler": "UP"
    }
  }
}
```

---

### 5.2 导出配置

```http
POST /api/v1/jobs/{id}/export
```

**响应：** 返回配置文件（可下载）

---

### 5.3 导入配置

```http
POST /api/v1/jobs/import
Content-Type: multipart/form-data
```

**请求体：**
- `file`: 上传的配置文件

---

## 六、API 数据源专用接口

### 6.1 测试 API 连接

```http
POST /api/v1/data-sources/test-api-connection
Content-Type: application/json
```

**请求体：**
```json
{
  "type": "API",
  "apiUrl": "https://api.example.com/data",
  "apiMethod": "GET",
  "apiHeaders": {"Authorization": "Bearer xxx"},
  "apiParams": {"page": "1", "size": "100"}
}
```

---

### 6.2 测试 API 请求并预览

```http
POST /api/v1/data-sources/test-api-request
Content-Type: application/json
```

**请求体：**
```json
{
  "apiUrl": "https://api.example.com/data",
  "apiMethod": "GET",
  "apiHeaders": {},
  "apiParams": {},
  "dataPath": "data.list"
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "success": true,
    "responseTime": 250,
    "statusCode": 200,
    "dataPreview": [
      {"id": 1, "name": "item1"},
      {"id": 2, "name": "item2"}
    ],
    "rawResponse": "{...}"
  }
}
```

---

## 📎 附录

### A. 字段映射 JSON 格式

```json
[
  {
    "sourceField": "id",
    "targetField": "id",
    "fieldType": "BIGINT",
    "isPrimaryKey": true,
    "isEnabled": true
  },
  {
    "sourceField": "user_name",
    "targetField": "username",
    "fieldType": "STRING",
    "fieldLength": 50,
    "isEnabled": true
  }
]
```

### B. Cron 表达式示例

| 表达式 | 说明 |
|--------|------|
| `0 0 2 * * ?` | 每天凌晨 2 点 |
| `0 0/30 * * * ?` | 每 30 分钟 |
| `0 0 9-18 * * ?` | 每天 9 点到 18 点整点 |
| `0 0 2 ? * MON` | 每周一凌晨 2 点 |

### C. SeaTunnel 作业状态

| 状态 | 说明 |
|------|------|
| CREATED | 已创建 |
| SCHEDULED | 已调度 |
| DEPLOYING | 部署中 |
| RUNNING | 运行中 |
| CANCELLING | 取消中 |
| CANCELLED | 已取消 |
| FAILED | 失败 |
| SUCCESS | 成功 |

---

## 🔜 下一步

有了 API 设计文档，你可以：

1. **选择技术栈**（Spring Boot / Node.js / Python FastAPI）
2. **实现后端服务**
3. **开发前端页面**
4. **集成 SeaTunnel 执行引擎**

**需要我帮你：**
- 写某个接口的实现代码？
- 设计数据库访问层（DAO）？
- 写配置生成器的具体实现？