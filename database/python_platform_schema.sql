-- Python Platform 2.0
-- MySQL schema snapshot generated from the live python_platform database.
-- Generated: 2026-09-08
-- Scope: schema only; no account passwords or business data are included.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `python_platform`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `python_platform`;

CREATE TABLE IF NOT EXISTS `user_admins` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '系统管理员',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_admins_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_teachers` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '教师',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_teachers_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_students` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `gender` int DEFAULT NULL,
  `study_class` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `stu_classify` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `test_num` int NOT NULL DEFAULT '0',
  `test_right_num` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_students_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `student_questionnaires` (
  `student_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `responses_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_completed` tinyint(1) NOT NULL DEFAULT '0',
  `completed_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`student_username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `classes` (
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `teaching_class` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `academic_year` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `teacher_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_classes_title_teaching_class` (`title`,`teaching_class`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `classes_teacher` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `teacher_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint unsigned NOT NULL,
  `academic_year` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_classes_teacher` (`teacher_username`,`class_id`),
  KEY `idx_classes_teacher_teacher` (`teacher_username`),
  KEY `idx_classes_teacher_class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `classes_student` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `student_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint unsigned NOT NULL,
  `enrollment_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `academic_year` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_classes_student` (`student_username`,`class_id`),
  KEY `idx_classes_student_student` (`student_username`),
  KEY `idx_classes_student_class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `classes_preferences` (
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint unsigned NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`,`role`),
  KEY `idx_classes_preferences_class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `feature_visibility_settings` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `role` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_label` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `group_label` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `icon` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `route_path` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `sort_order` int NOT NULL DEFAULT '0',
  `is_visible` tinyint(1) NOT NULL DEFAULT '1',
  `updated_by` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_feature_visibility_role_feature` (`role`,`feature_id`),
  KEY `idx_feature_visibility_role` (`role`),
  KEY `idx_feature_visibility_visible` (`role`,`is_visible`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `graph_themes` (
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10,2) DEFAULT NULL,
  `difficulty` decimal(10,2) DEFAULT NULL,
  `mastery` decimal(10,2) DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT '0',
  `test_right_num` int NOT NULL DEFAULT '0',
  `taught` tinyint(1) NOT NULL DEFAULT '0',
  `id` bigint unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `graph_knowledge` (
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10,2) DEFAULT NULL,
  `difficulty` decimal(10,2) DEFAULT NULL,
  `mastery` decimal(10,2) DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT '0',
  `test_right_num` int NOT NULL DEFAULT '0',
  `taught` tinyint(1) NOT NULL DEFAULT '0',
  `id` bigint unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `graph_points` (
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10,2) DEFAULT NULL,
  `difficulty` decimal(10,2) DEFAULT NULL,
  `mastery` decimal(10,2) DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT '0',
  `test_right_num` int NOT NULL DEFAULT '0',
  `taught` tinyint(1) NOT NULL DEFAULT '0',
  `id` bigint unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `graph_questions` (
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `answer` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `programming_config_json` longtext COLLATE utf8mb4_unicode_ci,
  `analysis` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty` decimal(10,2) DEFAULT NULL,
  `importance` decimal(10,2) DEFAULT NULL,
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `mastery` decimal(10,2) DEFAULT NULL,
  `exam_times` int NOT NULL DEFAULT '0',
  `homework_times` int NOT NULL DEFAULT '0',
  `question_count` int NOT NULL DEFAULT '0',
  `correct_question_count` int NOT NULL DEFAULT '0',
  `wrong_times` int NOT NULL DEFAULT '0',
  `taught` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_graph_questions_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `legacy_graph_nodes` (
  `label_name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uid` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`),
  KEY `idx_legacy_nodes_label` (`label_name`),
  KEY `idx_legacy_nodes_uid` (`uid`),
  KEY `idx_legacy_nodes_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `legacy_graph_node_refs` (
  `original_node_id` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `label_name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `new_id` bigint unsigned NOT NULL,
  `uid` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`original_node_id`),
  UNIQUE KEY `uq_graph_ref_new_id` (`new_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `legacy_graph_node_properties` (
  `node_id` bigint unsigned NOT NULL,
  `property_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_value` longtext COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`node_id`,`property_name`),
  KEY `idx_graph_property_name` (`property_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `legacy_graph_relationships` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `relation_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_id` bigint unsigned NOT NULL,
  `target_id` bigint unsigned NOT NULL,
  `source_label` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_label` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `relation_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_legacy_relation_id` (`relation_id`),
  KEY `idx_legacy_rel_source_id` (`source_id`),
  KEY `idx_legacy_rel_target_id` (`target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `assignments` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `deadline` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `time_limit` int NOT NULL DEFAULT '0',
  `open_state` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'yes',
  `target_usernames_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `assignment_kind` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'homework',
  `is_makeup` tinyint(1) NOT NULL DEFAULT '0',
  `is_mock` tinyint(1) NOT NULL DEFAULT '0',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft',
  `allow_answer_view` tinyint(1) NOT NULL DEFAULT '0',
  `question_titles_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `class_id` bigint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_assignments_title` (`title`),
  KEY `idx_assignments_owner` (`owner_username`),
  KEY `idx_assignments_class_id` (`class_id`),
  CONSTRAINT `chk_assignments_assignment_kind_allowed`
    CHECK (`assignment_kind` IN ('homework','classwork','offline','mock','exam'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `assignment_items` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `position` int NOT NULL,
  `question_ref` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_id` bigint unsigned DEFAULT NULL,
  `score` decimal(8,2) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assignment_item_position` (`assignment_id`,`position`),
  KEY `idx_assignment_items_question` (`question_ref`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `assignment_makeup` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `deadline` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `time_limit` int NOT NULL DEFAULT '0',
  `assignment_kind` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `open_state` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'yes',
  `target_usernames_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `owner_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `legacy_assignment_id` bigint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_assignment_makeup_assignment` (`assignment_id`),
  KEY `idx_assignment_makeup_owner` (`owner_username`),
  KEY `idx_assignment_makeup_active` (`assignment_id`,`is_active`),
  CONSTRAINT `chk_assignment_makeup_kind_allowed`
    CHECK (`assignment_kind` IS NULL OR `assignment_kind` IN ('homework','classwork','offline','mock','exam'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `submission_details` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `input_context` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `correct` tinyint(1) NOT NULL DEFAULT '0',
  `relation_title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `relation_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `test_id` bigint unsigned NOT NULL,
  `student_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_submission_details_relation_id` (`relation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `submissions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint unsigned NOT NULL,
  `student_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `attempt_no` int NOT NULL DEFAULT '1',
  `makeup_window_id` bigint unsigned DEFAULT NULL,
  `submission_mode` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft',
  `answers_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `time_spent_json` longtext COLLATE utf8mb4_unicode_ci,
  `score` decimal(8,2) DEFAULT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_submission_student_assignment` (`student_username`,`assignment_id`),
  KEY `idx_submission_status` (`status`),
  KEY `idx_submission_makeup` (`makeup_window_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `submission_grades` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `submission_id` bigint unsigned NOT NULL,
  `question_position` int NOT NULL,
  `time_spent_seconds` int unsigned DEFAULT NULL,
  `score` decimal(8,2) NOT NULL DEFAULT '0.00',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'graded',
  `feedback` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `provider` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'objective',
  `grading_details_json` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_submission_grades_submission_question` (`submission_id`,`question_position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `code_runs` (
  `id` char(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_ref` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `language` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `version` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'latest',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'submitted',
  `stdin_text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_code` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `stdout_text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `stderr_text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `provider_error` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_code_runs_student` (`student_username`),
  KEY `idx_code_runs_question` (`question_ref`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_conversations` (
  `id` char(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ai_conversation_owner` (`owner_username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_messages` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `conversation_id` char(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ai_message_conversation` (`conversation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_generation_tasks` (
  `id` char(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending_review',
  `prompt` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ai_generation_owner` (`owner_username`),
  KEY `idx_ai_generation_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `actor_username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `actor_role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `resource_id` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `detail_json` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_actor` (`actor_username`),
  KEY `idx_audit_action` (`action`),
  KEY `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
