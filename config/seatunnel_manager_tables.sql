-- ============================================
-- SeaTunnel 数据采集管理平台 - 数据库表结构
-- ============================================
-- 数据库：seatunnel_manager
-- 字符集：utf8mb4
-- 创建时间：2026-04-16
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `seatunnel_manager` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `seatunnel_manager`;

-- ============================================
-- 1. 数据源配置表 (data_source)
-- ============================================
DROP TABLE IF EXISTS `data_source`;

CREATE TABLE `data_source` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `name` VARCHAR(100) NOT NULL COMMENT '数据源名称',
  `type` VARCHAR(20) NOT NULL COMMENT '数据源类型：MYSQL / API',
  `description` VARCHAR(500) COMMENT '数据源描述',
  
  -- MySQL 连接配置
  `host` VARCHAR(100) COMMENT 'MySQL 主机地址',
  `port` INT DEFAULT 3306 COMMENT 'MySQL 端口',
  `database_name` VARCHAR(100) COMMENT 'MySQL 数据库名',
  `username` VARCHAR(100) COMMENT 'MySQL 用户名',
  `password` VARCHAR(512) COMMENT 'MySQL 密码（加密存储）',
  `connection_params` TEXT COMMENT '额外连接参数（JSON 格式）',
  
  -- API 连接配置
  `api_url` VARCHAR(1000) COMMENT 'API 请求地址',
  `api_method` VARCHAR(10) DEFAULT 'GET' COMMENT '请求方式：GET / POST / PUT / DELETE',
  `api_content_type` VARCHAR(100) DEFAULT 'application/json' COMMENT 'Content-Type',
  `api_headers` TEXT COMMENT '请求头（JSON 格式）',
  `api_params` TEXT COMMENT '查询参数（JSON 格式）',
  `api_body` TEXT COMMENT '请求体（JSON 格式，POST/PUT 时使用）',
  
  -- API 认证配置
  `auth_type` VARCHAR(20) DEFAULT 'NONE' COMMENT '认证方式：NONE / BEARER / BASIC / API_KEY',
  `auth_config` TEXT COMMENT '认证配置（JSON 格式）',
  
  -- API 返回结果配置
  `data_path` VARCHAR(200) COMMENT '数据节点路径（如：data.list）',
  `response_format` VARCHAR(20) DEFAULT 'JSON' COMMENT '返回格式：JSON / TEXT',
  
  -- 状态与元数据
  `status` TINYINT DEFAULT 1 COMMENT '状态：0-停用 1-启用',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除：0-否 1-是',
  `created_by` VARCHAR(50) COMMENT '创建人',
  `updated_by` VARCHAR(50) COMMENT '更新人',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  INDEX `idx_type` (`type`),
  INDEX `idx_name` (`name`),
  INDEX `idx_status` (`status`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据源配置表';


-- ============================================
-- 2. 任务配置表 (job_config)
-- ============================================
DROP TABLE IF EXISTS `job_config`;

CREATE TABLE `job_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `job_name` VARCHAR(100) NOT NULL COMMENT '任务名称',
  `job_description` VARCHAR(500) COMMENT '任务描述',
  
  -- 源配置
  `source_id` BIGINT NOT NULL COMMENT '数据源 ID（关联 data_source.id）',
  `source_type` VARCHAR(20) NOT NULL COMMENT '数据源类型：MYSQL / API（冗余字段，方便查询）',
  `source_table` VARCHAR(100) COMMENT '源表名（MySQL 模式）',
  `source_database` VARCHAR(100) COMMENT '源数据库名（MySQL 模式）',
  `source_query` TEXT COMMENT '自定义 SQL 查询（MySQL 模式）',
  `where_condition` VARCHAR(500) COMMENT 'WHERE 条件',
  `limit_count` INT COMMENT '数据条数限制',
  
  -- 增量同步配置
  `is_incremental` TINYINT DEFAULT 0 COMMENT '是否增量同步：0-否 1-是',
  `incremental_column` VARCHAR(100) COMMENT '增量字段名',
  `incremental_start_value` VARCHAR(100) COMMENT '增量起始值',
  `incremental_current_value` VARCHAR(100) COMMENT '增量当前值（运行时更新）',
  
  -- 目标配置（MySQL）
  `sink_type` VARCHAR(20) DEFAULT 'MYSQL' COMMENT '目标类型：MYSQL',
  `sink_host` VARCHAR(100) COMMENT '目标主机地址',
  `sink_port` INT DEFAULT 3306 COMMENT '目标端口',
  `sink_database` VARCHAR(100) COMMENT '目标数据库名',
  `sink_username` VARCHAR(100) COMMENT '目标用户名',
  `sink_password` VARCHAR(512) COMMENT '目标密码（加密存储）',
  `sink_table` VARCHAR(100) COMMENT '目标表名',
  `primary_keys` VARCHAR(255) COMMENT '主键字段（逗号分隔）',
  `batch_size` INT DEFAULT 1000 COMMENT '批处理大小',
  
  -- 字段映射配置（JSON 格式）
  -- 示例：[{"source_field":"id","target_field":"id","field_type":"INT"}, ...]
  `field_mapping` TEXT COMMENT '字段映射配置（JSON 格式）',
  
  -- 调度配置
  `schedule_type` VARCHAR(20) DEFAULT 'MANUAL' COMMENT '调度类型：MANUAL-手动 / CRON-定时',
  `cron_expression` VARCHAR(100) COMMENT 'Cron 表达式（如：0 0 2 * * ?）',
  `timezone` VARCHAR(50) DEFAULT 'Asia/Shanghai' COMMENT '时区',
  `retry_times` INT DEFAULT 3 COMMENT '失败重试次数',
  `retry_interval` INT DEFAULT 60 COMMENT '重试间隔（秒）',
  
  -- 作业模式
  `job_mode` VARCHAR(20) DEFAULT 'STREAMING' COMMENT '作业模式：STREAMING / BATCH',
  `parallelism` INT DEFAULT 1 COMMENT '并行度',
  `checkpoint_interval` INT DEFAULT 10000 COMMENT 'Checkpoint 间隔（毫秒）',
  
  -- 状态与元数据
  `status` TINYINT DEFAULT 1 COMMENT '任务状态：0-停用 1-启用',
  `last_run_time` DATETIME COMMENT '最后执行时间',
  `last_run_status` VARCHAR(20) COMMENT '最后执行状态：SUCCESS / FAILED / RUNNING',
  `last_execution_id` VARCHAR(100) COMMENT '最后执行 ID（SeaTunnel 作业 ID）',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除：0-否 1-是',
  `created_by` VARCHAR(50) COMMENT '创建人',
  `updated_by` VARCHAR(50) COMMENT '更新人',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  INDEX `idx_source_id` (`source_id`),
  INDEX `idx_source_type` (`source_type`),
  INDEX `idx_status` (`status`),
  INDEX `idx_schedule_type` (`schedule_type`),
  INDEX `idx_job_mode` (`job_mode`),
  INDEX `idx_last_run_status` (`last_run_status`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_job_source` FOREIGN KEY (`source_id`) REFERENCES `data_source` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务配置表';


-- ============================================
-- 3. 任务执行历史表 (job_execution_log)
-- ============================================
DROP TABLE IF EXISTS `job_execution_log`;

CREATE TABLE `job_execution_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `job_id` BIGINT NOT NULL COMMENT '任务 ID（关联 job_config.id）',
  `execution_id` VARCHAR(100) COMMENT 'SeaTunnel 作业 ID',
  `job_name` VARCHAR(100) COMMENT '任务名称（冗余字段，方便查询）',
  
  -- 执行时间
  `start_time` DATETIME COMMENT '开始时间',
  `end_time` DATETIME COMMENT '结束时间',
  `duration_seconds` INT COMMENT '执行时长（秒）',
  
  -- 执行状态
  `status` VARCHAR(20) NOT NULL COMMENT '执行状态：RUNNING / SUCCESS / FAILED / CANCELLED',
  `trigger_type` VARCHAR(20) DEFAULT 'MANUAL' COMMENT '触发类型：MANUAL-手动 / CRON-定时',
  `error_message` TEXT COMMENT '错误信息',
  `error_stack` TEXT COMMENT '错误堆栈',
  
  -- 执行指标
  `metrics_read_rows` BIGINT DEFAULT 0 COMMENT '读取行数',
  `metrics_write_rows` BIGINT DEFAULT 0 COMMENT '写入行数',
  `metrics_read_bytes` BIGINT DEFAULT 0 COMMENT '读取字节数',
  `metrics_write_bytes` BIGINT DEFAULT 0 COMMENT '写入字节数',
  
  -- SeaTunnel 配置
  `seatunnel_config` TEXT COMMENT 'SeaTunnel 配置文件内容（用于追溯）',
  `seatunnel_log_path` VARCHAR(500) COMMENT 'SeaTunnel 日志文件路径',
  
  -- 元数据
  `created_by` VARCHAR(50) COMMENT '创建人/触发人',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`id`),
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_execution_id` (`execution_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_start_time` (`start_time`),
  INDEX `idx_created_at` (`created_at`),
  CONSTRAINT `fk_execution_job` FOREIGN KEY (`job_id`) REFERENCES `job_config` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行历史表';


-- ============================================
-- 4. 字段映射详情表 (job_field_mapping)
-- ============================================
DROP TABLE IF EXISTS `job_field_mapping`;

CREATE TABLE `job_field_mapping` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `job_id` BIGINT NOT NULL COMMENT '任务 ID（关联 job_config.id）',
  
  `source_field` VARCHAR(100) NOT NULL COMMENT '源字段名',
  `target_field` VARCHAR(100) NOT NULL COMMENT '目标字段名',
  `field_type` VARCHAR(50) DEFAULT 'STRING' COMMENT '字段类型：STRING / INT / BIGINT / DECIMAL / DATETIME / BOOLEAN / TEXT',
  `field_length` INT COMMENT '字段长度',
  `is_nullable` TINYINT DEFAULT 1 COMMENT '是否可空：0-否 1-是',
  `is_primary_key` TINYINT DEFAULT 0 COMMENT '是否主键：0-否 1-是',
  `default_value` VARCHAR(255) COMMENT '默认值',
  `transform_expression` VARCHAR(500) COMMENT '转换表达式（可选）',
  `is_enabled` TINYINT DEFAULT 1 COMMENT '是否启用：0-禁用 1-启用',
  `sort_order` INT DEFAULT 0 COMMENT '排序顺序',
  
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_source_field` (`source_field`),
  CONSTRAINT `fk_mapping_job` FOREIGN KEY (`job_id`) REFERENCES `job_config` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='字段映射详情表';


-- ============================================
-- 5. 定时任务调度表 (job_schedule)
-- ============================================
DROP TABLE IF EXISTS `job_schedule`;

CREATE TABLE `job_schedule` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键 ID',
  `job_id` BIGINT NOT NULL COMMENT '任务 ID（关联 job_config.id）',
  
  `schedule_type` VARCHAR(20) NOT NULL COMMENT '调度类型：CRON / FIXED_RATE / FIXED_DELAY',
  `cron_expression` VARCHAR(100) COMMENT 'Cron 表达式',
  `fixed_rate_ms` BIGINT COMMENT '固定频率（毫秒）',
  `fixed_delay_ms` BIGINT COMMENT '固定延迟（毫秒）',
  `timezone` VARCHAR(50) DEFAULT 'Asia/Shanghai' COMMENT '时区',
  
  `is_active` TINYINT DEFAULT 1 COMMENT '是否激活：0-否 1-是',
  `last_run_time` DATETIME COMMENT '最后运行时间',
  `next_run_time` DATETIME COMMENT '下次运行时间',
  
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_is_active` (`is_active`),
  INDEX `idx_next_run_time` (`next_run_time`),
  CONSTRAINT `fk_schedule_job` FOREIGN KEY (`job_id`) REFERENCES `job_config` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='定时任务调度表';


-- ============================================
-- 初始化数据（可选）
-- ============================================

-- 插入示例数据源（MySQL）
INSERT INTO `data_source` (`name`, `type`, `description`, `host`, `port`, `database_name`, `username`, `password`, `status`) 
VALUES 
('MySQL_源库', 'MYSQL', '生产环境 MySQL 源库', '127.0.0.1', 3306, 'seatunnel_prod', 'root', 'qwer123.', 1),
('MySQL_目标库', 'MYSQL', '目标 MySQL 数据库', '127.0.0.1', 3306, 'target', 'root', 'qwer123.', 1);

-- 插入示例任务配置
INSERT INTO `job_config` (
  `job_name`, `job_description`, `source_id`, `source_type`, `source_database`, `source_table`,
  `sink_host`, `sink_port`, `sink_database`, `sink_username`, `sink_password`, `sink_table`, `primary_keys`,
  `schedule_type`, `status`
) VALUES (
  'testtable 同步任务', '从 seatunnel_prod.testtable 同步到 target.testtable',
  1, 'MYSQL', 'seatunnel_prod', 'testtable',
  '127.0.0.1', 3306, 'target', 'root', 'qwer123.', 'testtable', 'id',
  'MANUAL', 1
);

-- ============================================
-- 视图：任务执行统计
-- ============================================
DROP VIEW IF EXISTS `v_job_execution_stats`;

CREATE VIEW `v_job_execution_stats` AS
SELECT 
  jc.id AS job_id,
  jc.job_name,
  jc.status AS job_status,
  COUNT(jel.id) AS total_executions,
  SUM(CASE WHEN jel.status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_count,
  SUM(CASE WHEN jel.status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
  SUM(CASE WHEN jel.status = 'RUNNING' THEN 1 ELSE 0 END) AS running_count,
  MAX(jel.start_time) AS last_execution_time,
  MAX(CASE WHEN jel.status = 'SUCCESS' THEN jel.start_time END) AS last_success_time,
  MAX(CASE WHEN jel.status = 'FAILED' THEN jel.start_time END) AS last_failed_time
FROM `job_config` jc
LEFT JOIN `job_execution_log` jel ON jc.id = jel.job_id AND jc.is_deleted = 0
WHERE jc.is_deleted = 0
GROUP BY jc.id, jc.job_name, jc.status;


-- ============================================
-- 完成提示
-- ============================================
SELECT '数据库表创建完成！' AS message;
SELECT '共创建 5 张表：data_source, job_config, job_execution_log, job_field_mapping, job_schedule' AS tables;
SELECT '共创建 1 个视图：v_job_execution_stats' AS views;