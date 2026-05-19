-- ============================================
-- 创建 API 用户数据表
-- ============================================
-- 数据库：target
-- 表名：api_users
-- 用途：存储从 API 同步的用户数据
-- ============================================

USE `target`;

-- 删除已存在的表（可选）
DROP TABLE IF EXISTS `api_users`;

-- 创建表
CREATE TABLE `api_users` (
  `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',
  
  -- 用户基本信息
  `gender` VARCHAR(20) COMMENT '性别',
  `title` VARCHAR(20) COMMENT '称谓',
  `first_name` VARCHAR(100) COMMENT '名',
  `last_name` VARCHAR(100) COMMENT '姓',
  
  -- 联系方式
  `email` VARCHAR(255) NOT NULL COMMENT '邮箱（唯一）',
  `phone` VARCHAR(50) COMMENT '电话号码',
  `cell` VARCHAR(50) COMMENT '手机号',
  
  -- 登录信息
  `username` VARCHAR(100) COMMENT '用户名',
  `password` VARCHAR(255) COMMENT '密码',
  
  -- 出生日期
  `dob_date` VARCHAR(50) COMMENT '出生日期',
  `dob_age` INT COMMENT '年龄',
  
  -- 地址信息
  `street_number` INT COMMENT '街道号码',
  `street_name` VARCHAR(255) COMMENT '街道名称',
  `city` VARCHAR(100) COMMENT '城市',
  `state` VARCHAR(100) COMMENT '州/省',
  `country` VARCHAR(100) COMMENT '国家',
  `postcode` VARCHAR(20) COMMENT '邮编',
  
  -- 坐标（用于地图定位）
  `latitude` DECIMAL(10, 6) COMMENT '纬度',
  `longitude` DECIMAL(10, 6) COMMENT '经度',
  
  -- 时区
  `timezone_offset` VARCHAR(10) COMMENT '时区偏移',
  `timezone_description` VARCHAR(255) COMMENT '时区描述',
  
  -- 元数据
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_city` (`city`),
  KEY `idx_country` (`country`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API 用户数据表';

-- ============================================
-- 插入示例数据（可选，用于测试）
-- ============================================
INSERT INTO `api_users` (
  `first_name`, `last_name`, `email`, `phone`, `city`, `country`
) VALUES (
  'Test', 'User', 'test@example.com', '123-456-7890', 'Test City', 'Test Country'
);

-- ============================================
-- 查询数据
-- ============================================
SELECT * FROM `api_users`;

-- ============================================
-- 清空数据（可选）
-- ============================================
-- TRUNCATE TABLE `api_users`;
