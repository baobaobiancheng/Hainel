-- ============================================
-- 标准科室医生账号种子数据
-- 默认密码：Doctor@123456
-- 首次登录后请修改密码。
-- ============================================

USE `medical_system`;

INSERT INTO `users` (
    `username`,
    `email`,
    `phone`,
    `hashed_password`,
    `role`,
    `full_name`,
    `doctor_title`,
    `doctor_department`,
    `doctor_hospital`,
    `doctor_license`,
    `is_active`,
    `is_verified`
) VALUES
    ('doctor_internal', 'doctor_internal@example.com', '18800001001', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '内科医生', '主治医师', '内科', '互联网医院', 'DOC-INTERNAL-001', TRUE, TRUE),
    ('doctor_surgery', 'doctor_surgery@example.com', '18800001002', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '外科医生', '主治医师', '外科', '互联网医院', 'DOC-SURGERY-001', TRUE, TRUE),
    ('doctor_pediatrics', 'doctor_pediatrics@example.com', '18800001003', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '儿科医生', '主治医师', '儿科', '互联网医院', 'DOC-PEDIATRICS-001', TRUE, TRUE),
    ('doctor_gynecology', 'doctor_gynecology@example.com', '18800001004', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '妇科医生', '主治医师', '妇科', '互联网医院', 'DOC-GYNECOLOGY-001', TRUE, TRUE),
    ('doctor_cardiology', 'doctor_cardiology@example.com', '18800001005', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '心内科医生', '主治医师', '心内科', '互联网医院', 'DOC-CARDIOLOGY-001', TRUE, TRUE),
    ('doctor_neurology', 'doctor_neurology@example.com', '18800001006', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '神经内科医生', '主治医师', '神经内科', '互联网医院', 'DOC-NEUROLOGY-001', TRUE, TRUE),
    ('doctor_orthopedics', 'doctor_orthopedics@example.com', '18800001007', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '骨科医生', '主治医师', '骨科', '互联网医院', 'DOC-ORTHOPEDICS-001', TRUE, TRUE),
    ('doctor_dermatology', 'doctor_dermatology@example.com', '18800001008', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '皮肤科医生', '主治医师', '皮肤科', '互联网医院', 'DOC-DERMATOLOGY-001', TRUE, TRUE),
    ('doctor_ophthalmology', 'doctor_ophthalmology@example.com', '18800001009', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '眼科医生', '主治医师', '眼科', '互联网医院', 'DOC-OPHTHALMOLOGY-001', TRUE, TRUE),
    ('doctor_ent', 'doctor_ent@example.com', '18800001010', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '耳鼻喉科医生', '主治医师', '耳鼻喉科', '互联网医院', 'DOC-ENT-001', TRUE, TRUE),
    ('doctor_psychiatry', 'doctor_psychiatry@example.com', '18800001011', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '精神科医生', '主治医师', '精神科', '互联网医院', 'DOC-PSYCHIATRY-001', TRUE, TRUE),
    ('doctor_emergency', 'doctor_emergency@example.com', '18800001012', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '急诊科医生', '主治医师', '急诊科', '互联网医院', 'DOC-EMERGENCY-001', TRUE, TRUE),
    ('doctor_general', 'doctor_general@example.com', '18800001013', '$2b$12$lxVlFwj22u91ZwdOXv78I.x0o7EQInNoUoFDqLl5eXj2NfD.4NzP6', 'doctor', '全科医生', '主治医师', '全科', '互联网医院', 'DOC-GENERAL-001', TRUE, TRUE)
ON DUPLICATE KEY UPDATE
    `email` = VALUES(`email`),
    `phone` = VALUES(`phone`),
    `hashed_password` = VALUES(`hashed_password`),
    `role` = VALUES(`role`),
    `full_name` = VALUES(`full_name`),
    `doctor_title` = VALUES(`doctor_title`),
    `doctor_department` = VALUES(`doctor_department`),
    `doctor_hospital` = VALUES(`doctor_hospital`),
    `doctor_license` = VALUES(`doctor_license`),
    `is_active` = VALUES(`is_active`),
    `is_verified` = VALUES(`is_verified`);
