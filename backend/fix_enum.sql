-- 完全重建 messages 表以修复枚举问题
USE `medical_system`;

-- 删除现有的 messages 表
DROP TABLE IF EXISTS messages;

-- 重新创建 messages 表，使用正确的枚举值（大写）
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
    `extra_metadata` JSON NULL COMMENT '扩展元数据',
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

SELECT 'messages 表已重建，枚举值已修复为大写' AS result;
