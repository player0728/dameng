-- ============================================
-- 创建 API 用户数据表（超简化版）
-- ============================================
-- 说明：只存储原始 JSON 字符串
-- ============================================

USE `target`;

-- 删除已存在的表
DROP TABLE IF EXISTS `api_users_raw`;

-- 创建超简单表 - 只有一个 JSON 字段
CREATE TABLE `api_users_raw` (
  `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',
  `content` LONGTEXT NOT NULL COMMENT 'API 返回的原始 JSON 数据',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API 用户原始数据表';

-- ============================================
-- 查询示例
-- ============================================

-- 查看所有数据
SELECT * FROM `api_users_raw`;

-- 查看 JSON 数据（格式化）
SELECT id, JSON_PRETTY(content) as json_data, created_at FROM `api_users_raw`;

-- ============================================
-- 清空数据（可选）
-- ============================================
-- TRUNCATE TABLE `api_users_raw`;
