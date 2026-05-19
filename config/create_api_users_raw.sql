-- ============================================
-- 创建 API 用户数据表（简化版）
-- ============================================
-- 说明：直接存储 JSON 原始数据，避免字段映射问题
-- ============================================

USE `target`;

-- 删除已存在的表
DROP TABLE IF EXISTS `api_users_raw`;

-- 创建简化表 - 只存储 JSON 和基础字段
CREATE TABLE `api_users_raw` (
  `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',
  
  -- 存储原始 JSON 数据
  `raw_json` JSON COMMENT '原始 API 返回的 JSON 数据',
  
  -- 提取的关键字段（可选，方便查询）
  `email` VARCHAR(255) COMMENT '邮箱',
  `first_name` VARCHAR(100) COMMENT '名',
  `last_name` VARCHAR(100) COMMENT '姓',
  `city` VARCHAR(100) COMMENT '城市',
  `country` VARCHAR(100) COMMENT '国家',
  
  -- 元数据
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_email` (`email`),
  KEY `idx_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API 用户原始数据表';

-- ============================================
-- 查询示例
-- ============================================

-- 查看所有数据
SELECT * FROM `api_users_raw`;

-- 从 JSON 中提取数据
SELECT 
  id,
  JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.email')) as email,
  JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.name.first')) as first_name,
  JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.name.last')) as last_name,
  JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.location.city')) as city,
  JSON_UNQUOTE(JSON_EXTRACT(raw_json, '$.location.country')) as country,
  created_at
FROM `api_users_raw`;

-- ============================================
-- 清空数据（可选）
-- ============================================
-- TRUNCATE TABLE `api_users_raw`;
