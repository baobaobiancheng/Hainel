USE `medical_system`;

ALTER TABLE `users`
    ADD COLUMN `health_profile` JSON NULL COMMENT '患者健康档案' AFTER `bio`;
