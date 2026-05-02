-- ============================================
-- 医疗健康咨询与辅助诊断系统数据库初始化脚本
-- ============================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS `medical_system` 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `medical_system`;

-- ============================================
-- 2. 创建用户表 (users)
-- ============================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `email` VARCHAR(100) NULL UNIQUE COMMENT '邮箱',
    `phone` VARCHAR(20) NULL UNIQUE COMMENT '手机号',
    `hashed_password` VARCHAR(255) NOT NULL COMMENT '密码哈希值',
    `role` ENUM('patient', 'doctor', 'admin') NOT NULL DEFAULT 'patient' COMMENT '用户角色：patient/doctor/admin',
    `full_name` VARCHAR(100) NULL COMMENT '全名',
    `avatar_url` VARCHAR(500) NULL COMMENT '头像URL',
    `bio` TEXT NULL COMMENT '个人简介',
    `health_profile` JSON NULL COMMENT '患者健康档案',
    `doctor_title` VARCHAR(50) NULL COMMENT '医生职称',
    `doctor_department` VARCHAR(100) NULL COMMENT '医生科室',
    `doctor_hospital` VARCHAR(200) NULL COMMENT '所属医院',
    `doctor_license` VARCHAR(100) NULL COMMENT '执业证书编号',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',
    `is_verified` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已验证',
    `last_login_at` DATETIME NULL COMMENT '最后登录时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_phone` (`phone`),
    INDEX `idx_users_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 3. 创建会话表 (conversations)
-- ============================================
CREATE TABLE IF NOT EXISTS `conversations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `patient_id` INT NOT NULL COMMENT '患者ID',
    `doctor_id` INT NULL COMMENT '医生ID（可选）',
    `title` VARCHAR(200) NULL COMMENT '会话标题',
    `chief_complaint` TEXT NULL COMMENT '主诉',
    `status` ENUM('pending', 'active', 'paused', 'completed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '会话状态：pending/active/paused/completed/cancelled',
    `complexity_level` ENUM('low', 'medium', 'high') NULL COMMENT '复杂度级别：low/medium/high',
    `complexity_score` INT NULL COMMENT '复杂度评分（0-100）',
    `collaboration_mode` ENUM('pcc', 'mdt', 'ict') NULL COMMENT '协作模式：pcc/mdt/ict',
    `agent_count` INT NOT NULL DEFAULT 1 COMMENT '参与的智能体数量',
    `agent_ids` JSON NULL COMMENT '智能体ID列表',
    `message_count` INT NOT NULL DEFAULT 0 COMMENT '消息数量',
    `round_count` INT NOT NULL DEFAULT 0 COMMENT '对话轮次',
    `started_at` DATETIME NULL COMMENT '开始时间',
    `ended_at` DATETIME NULL COMMENT '结束时间',
    `last_message_at` DATETIME NULL COMMENT '最后消息时间',
    `extra_metadata` JSON NULL COMMENT '扩展元数据',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`patient_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`doctor_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_conversation_patient_status` (`patient_id`, `status`),
    INDEX `idx_conversation_doctor_status` (`doctor_id`, `status`),
    INDEX `idx_conversation_complexity_mode` (`complexity_level`, `collaboration_mode`),
    INDEX `idx_conversations_patient_id` (`patient_id`),
    INDEX `idx_conversations_doctor_id` (`doctor_id`),
    INDEX `idx_conversations_status` (`status`),
    INDEX `idx_conversations_complexity_level` (`complexity_level`),
    INDEX `idx_conversations_collaboration_mode` (`collaboration_mode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- ============================================
-- 4. 创建消息表 (messages)
-- ============================================
CREATE TABLE IF NOT EXISTS `messages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `conversation_id` INT NOT NULL COMMENT '会话ID',
    `user_id` INT NULL COMMENT '用户ID（发送者）',
    `role` ENUM('USER', 'ASSISTANT', 'SYSTEM') NOT NULL COMMENT '消息角色：USER/ASSISTANT/SYSTEM',
    `message_type` ENUM('text', 'image', 'file', 'system') NOT NULL DEFAULT 'text' COMMENT '消息类型：text/image/file/system',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `file_url` VARCHAR(500) NULL COMMENT '文件URL',
    `file_name` VARCHAR(200) NULL COMMENT '文件名',
    `file_size` INT NULL COMMENT '文件大小（字节）',
    `file_type` VARCHAR(50) NULL COMMENT '文件类型/MIME类型',
    `agent_name` VARCHAR(100) NULL COMMENT '智能体名称',
    `agent_id` VARCHAR(100) NULL COMMENT '智能体ID',
    `extra_metadata` JSON NULL COMMENT '扩展元数据（如OCR结果、结构化数据等）',
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已读',
    `is_edited` BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已编辑',
    `edited_at` DATETIME NULL COMMENT '编辑时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_message_conversation_created` (`conversation_id`, `created_at`),
    INDEX `idx_message_user_created` (`user_id`, `created_at`),
    INDEX `idx_message_agent_created` (`agent_id`, `created_at`),
    INDEX `idx_messages_conversation_id` (`conversation_id`),
    INDEX `idx_messages_user_id` (`user_id`),
    INDEX `idx_messages_role` (`role`),
    INDEX `idx_messages_agent_name` (`agent_name`),
    INDEX `idx_messages_agent_id` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- ============================================
-- 5. 创建病历表 (medical_records)
-- ============================================
CREATE TABLE IF NOT EXISTS `medical_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `patient_id` INT NOT NULL COMMENT '患者ID',
    `conversation_id` INT NULL COMMENT '关联的会话ID',
    `reviewed_by` INT NULL COMMENT '审核医生ID',
    `title` VARCHAR(200) NOT NULL COMMENT '病历标题',
    `status` ENUM('draft', 'confirmed', 'reviewed', 'archived') NOT NULL DEFAULT 'draft' COMMENT '病历状态：draft/confirmed/reviewed/archived',
    `chief_complaint` TEXT NULL COMMENT '主诉',
    `present_illness` TEXT NULL COMMENT '现病史',
    `past_history` TEXT NULL COMMENT '既往史',
    `physical_examination` TEXT NULL COMMENT '体格检查',
    `auxiliary_examination` TEXT NULL COMMENT '辅助检查',
    `diagnosis` JSON NULL COMMENT '诊断（JSON格式，支持多个诊断）',
    `treatment_plan` TEXT NULL COMMENT '治疗方案',
    `medications` JSON NULL COMMENT '用药信息（JSON格式）',
    `medical_advice` TEXT NULL COMMENT '医嘱',
    `follow_up` TEXT NULL COMMENT '随访建议',
    `content` JSON NULL COMMENT '完整病历内容（JSON格式）',
    `agent_name` VARCHAR(100) NULL COMMENT '生成病历的智能体名称',
    `agent_id` VARCHAR(100) NULL COMMENT '生成病历的智能体ID',
    `review_comment` TEXT NULL COMMENT '审核意见',
    `reviewed_at` DATETIME NULL COMMENT '审核时间',
    `archived_at` DATETIME NULL COMMENT '归档时间',
    `extra_metadata` JSON NULL COMMENT '扩展元数据',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`patient_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`conversation_id`) REFERENCES `conversations`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    INDEX `idx_medical_record_patient_status` (`patient_id`, `status`),
    INDEX `idx_medical_record_conversation` (`conversation_id`),
    INDEX `idx_medical_record_reviewed` (`reviewed_by`, `status`),
    INDEX `idx_medical_records_patient_id` (`patient_id`),
    INDEX `idx_medical_records_conversation_id` (`conversation_id`),
    INDEX `idx_medical_records_status` (`status`),
    INDEX `idx_medical_records_reviewed_by` (`reviewed_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='病历表';

-- ============================================
-- 6. 创建提醒表 (reminders)
-- ============================================
CREATE TABLE IF NOT EXISTS `reminders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `reminder_type` ENUM('medication', 'examination', 'follow_up') NOT NULL DEFAULT 'medication' COMMENT '提醒类型',
    `title` VARCHAR(200) NOT NULL COMMENT '提醒标题',
    `medication_name` VARCHAR(100) NULL COMMENT '药物名称',
    `dosage` VARCHAR(50) NULL COMMENT '剂量',
    `frequency` ENUM('once', 'daily', 'twice_daily', 'three_times_daily', 'weekly', 'custom') NOT NULL DEFAULT 'daily' COMMENT '提醒频率',
    `remind_time` VARCHAR(20) NULL COMMENT '提醒时间（如 08:00）',
    `start_date` DATETIME NULL COMMENT '开始日期',
    `end_date` DATETIME NULL COMMENT '结束日期',
    `notes` TEXT NULL COMMENT '备注',
    `status` ENUM('active', 'paused', 'completed', 'cancelled') NOT NULL DEFAULT 'active' COMMENT '提醒状态',
    `last_reminded_at` DATETIME NULL COMMENT '最后提醒时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_reminders_user_id` (`user_id`),
    INDEX `idx_reminders_status` (`status`),
    INDEX `idx_reminders_type` (`reminder_type`),
    INDEX `idx_reminders_user_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用药/检查/复诊提醒表';

-- ============================================
-- 完成
-- ============================================
SELECT 'Database initialization completed successfully!' AS message;

