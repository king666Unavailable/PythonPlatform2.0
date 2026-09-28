/*
 Navicat MySQL Dump SQL

 Source Server         : local
 Source Server Type    : MySQL
 Source Server Version : 80042 (8.0.42)
 Source Host           : localhost:3306
 Source Schema         : python_platform

 Target Server Type    : MySQL
 Target Server Version : 80042 (8.0.42)
 File Encoding         : 65001

 Date: 28/09/2026 16:08:39
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ai_conversations
-- ----------------------------
DROP TABLE IF EXISTS `ai_conversations`;
CREATE TABLE `ai_conversations`  (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_ai_conversation_owner`(`owner_username` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ai_generation_tasks
-- ----------------------------
DROP TABLE IF EXISTS `ai_generation_tasks`;
CREATE TABLE `ai_generation_tasks`  (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending_review',
  `prompt` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `result_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_ai_generation_owner`(`owner_username` ASC) USING BTREE,
  INDEX `idx_ai_generation_status`(`status` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for ai_messages
-- ----------------------------
DROP TABLE IF EXISTS `ai_messages`;
CREATE TABLE `ai_messages`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `conversation_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_ai_message_conversation`(`conversation_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for assignment_items
-- ----------------------------
DROP TABLE IF EXISTS `assignment_items`;
CREATE TABLE `assignment_items`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint UNSIGNED NOT NULL,
  `position` int NOT NULL,
  `question_ref` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_id` bigint UNSIGNED NULL DEFAULT NULL,
  `score` decimal(8, 2) NULL DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_assignment_item_position`(`assignment_id` ASC, `position` ASC) USING BTREE,
  INDEX `idx_assignment_items_question`(`question_ref` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 531 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for assignment_makeup
-- ----------------------------
DROP TABLE IF EXISTS `assignment_makeup`;
CREATE TABLE `assignment_makeup`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint UNSIGNED NOT NULL,
  `deadline` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `time_limit` int NOT NULL DEFAULT 0,
  `assignment_kind` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `open_state` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'yes',
  `target_usernames_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `owner_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_assignment_makeup_assignment`(`assignment_id` ASC) USING BTREE,
  INDEX `idx_assignment_makeup_owner`(`owner_username` ASC) USING BTREE,
  INDEX `idx_assignment_makeup_active`(`assignment_id` ASC, `is_active` ASC) USING BTREE,
  CONSTRAINT `chk_assignment_makeup_kind_allowed` CHECK ((`assignment_kind` is null) or (`assignment_kind` in (_utf8mb4'homework',_utf8mb4'classwork',_utf8mb4'offline',_utf8mb4'mock',_utf8mb4'exam')))
) ENGINE = InnoDB AUTO_INCREMENT = 14 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for assignments
-- ----------------------------
DROP TABLE IF EXISTS `assignments`;
CREATE TABLE `assignments`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `deadline` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `time_limit` int NOT NULL DEFAULT 0,
  `open_state` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'yes',
  `target_usernames_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `assignment_kind` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'homework',
  `is_makeup` tinyint(1) NOT NULL DEFAULT 0,
  `is_mock` tinyint(1) NOT NULL DEFAULT 0,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft',
  `allow_answer_view` tinyint(1) NOT NULL DEFAULT 0,
  `question_titles_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `class_id` bigint UNSIGNED NULL DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_assignments_title`(`title` ASC) USING BTREE,
  INDEX `idx_assignments_owner`(`owner_username` ASC) USING BTREE,
  INDEX `idx_assignments_class_id`(`class_id` ASC) USING BTREE,
  CONSTRAINT `chk_assignments_assignment_kind_allowed` CHECK (`assignment_kind` in (_utf8mb4'homework',_utf8mb4'classwork',_utf8mb4'offline',_utf8mb4'mock',_utf8mb4'exam'))
) ENGINE = InnoDB AUTO_INCREMENT = 54 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for audit_logs
-- ----------------------------
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `actor_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `actor_role` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resource_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `resource_id` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `detail_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_audit_actor`(`actor_username` ASC) USING BTREE,
  INDEX `idx_audit_action`(`action` ASC) USING BTREE,
  INDEX `idx_audit_created`(`created_at` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 335 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for class_alert_preferences
-- ----------------------------
DROP TABLE IF EXISTS `class_alert_preferences`;
CREATE TABLE `class_alert_preferences`  (
  `teacher_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`teacher_username`, `class_id`) USING BTREE,
  INDEX `idx_class_alert_preferences_class`(`class_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for classes
-- ----------------------------
DROP TABLE IF EXISTS `classes`;
CREATE TABLE `classes`  (
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `teaching_class` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `academic_year` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `graph_class_id` bigint UNSIGNED NULL DEFAULT NULL,
  `teacher_name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_classes_title_teaching_class`(`title` ASC, `teaching_class` ASC) USING BTREE,
  INDEX `idx_classes_graph_class_id`(`graph_class_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 122 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for classes_preferences
-- ----------------------------
DROP TABLE IF EXISTS `classes_preferences`;
CREATE TABLE `classes_preferences`  (
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint UNSIGNED NOT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`, `role`) USING BTREE,
  INDEX `idx_classes_preferences_class`(`class_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for classes_student
-- ----------------------------
DROP TABLE IF EXISTS `classes_student`;
CREATE TABLE `classes_student`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint UNSIGNED NOT NULL,
  `enrollment_type` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `academic_year` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_classes_student`(`student_username` ASC, `class_id` ASC) USING BTREE,
  INDEX `idx_classes_student_student`(`student_username` ASC) USING BTREE,
  INDEX `idx_classes_student_class`(`class_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 861 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for classes_teacher
-- ----------------------------
DROP TABLE IF EXISTS `classes_teacher`;
CREATE TABLE `classes_teacher`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `teacher_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint UNSIGNED NOT NULL,
  `academic_year` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_classes_teacher`(`teacher_username` ASC, `class_id` ASC) USING BTREE,
  INDEX `idx_classes_teacher_teacher`(`teacher_username` ASC) USING BTREE,
  INDEX `idx_classes_teacher_class`(`class_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 39 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for code_runs
-- ----------------------------
DROP TABLE IF EXISTS `code_runs`;
CREATE TABLE `code_runs`  (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `student_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_ref` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `language` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'latest',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'submitted',
  `stdin_text` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `stdout_text` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `stderr_text` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `provider_error` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_code_runs_student`(`student_username` ASC) USING BTREE,
  INDEX `idx_code_runs_question`(`question_ref` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for feature_visibility_settings
-- ----------------------------
DROP TABLE IF EXISTS `feature_visibility_settings`;
CREATE TABLE `feature_visibility_settings`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `role` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `feature_label` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `group_label` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `icon` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `route_path` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `sort_order` int NOT NULL DEFAULT 0,
  `is_visible` tinyint(1) NOT NULL DEFAULT 1,
  `updated_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_feature_visibility_role_feature`(`role` ASC, `feature_id` ASC) USING BTREE,
  INDEX `idx_feature_visibility_role`(`role` ASC) USING BTREE,
  INDEX `idx_feature_visibility_visible`(`role` ASC, `is_visible` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3240 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_classes
-- ----------------------------
DROP TABLE IF EXISTS `graph_classes`;
CREATE TABLE `graph_classes`  (
  `id` bigint UNSIGNED NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `uid` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_graph_classes_uid`(`uid` ASC) USING BTREE,
  INDEX `idx_graph_classes_title`(`title` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_knowledge
-- ----------------------------
DROP TABLE IF EXISTS `graph_knowledge`;
CREATE TABLE `graph_knowledge`  (
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10, 2) NULL DEFAULT NULL,
  `difficulty` decimal(10, 2) NULL DEFAULT NULL,
  `mastery` decimal(10, 2) NULL DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT 0,
  `test_right_num` int NOT NULL DEFAULT 0,
  `taught` tinyint(1) NOT NULL DEFAULT 0,
  `id` bigint UNSIGNED NOT NULL,
  `graph_class_id` bigint UNSIGNED NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_graph_knowledge_graph_class_id`(`graph_class_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_node_refs
-- ----------------------------
DROP TABLE IF EXISTS `graph_node_refs`;
CREATE TABLE `graph_node_refs`  (
  `label_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `new_id` bigint UNSIGNED NOT NULL,
  `uid` varchar(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`new_id`) USING BTREE,
  INDEX `idx_graph_ref_label_uid`(`label_name` ASC, `uid` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_points
-- ----------------------------
DROP TABLE IF EXISTS `graph_points`;
CREATE TABLE `graph_points`  (
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10, 2) NULL DEFAULT NULL,
  `difficulty` decimal(10, 2) NULL DEFAULT NULL,
  `mastery` decimal(10, 2) NULL DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT 0,
  `test_right_num` int NOT NULL DEFAULT 0,
  `taught` tinyint(1) NOT NULL DEFAULT 0,
  `id` bigint UNSIGNED NOT NULL,
  `graph_class_id` bigint UNSIGNED NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_graph_points_graph_class_id`(`graph_class_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_questions
-- ----------------------------
DROP TABLE IF EXISTS `graph_questions`;
CREATE TABLE `graph_questions`  (
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `question_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `answer` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `programming_config_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `analysis` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty` decimal(10, 2) NULL DEFAULT NULL,
  `importance` decimal(10, 2) NULL DEFAULT NULL,
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `mastery` decimal(10, 2) NULL DEFAULT NULL,
  `exam_times` int NOT NULL DEFAULT 0,
  `homework_times` int NOT NULL DEFAULT 0,
  `question_count` int NOT NULL DEFAULT 0,
  `correct_question_count` int NOT NULL DEFAULT 0,
  `wrong_times` int NOT NULL DEFAULT 0,
  `taught` tinyint(1) NOT NULL DEFAULT 0,
  `graph_class_id` bigint UNSIGNED NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_graph_questions_title`(`title` ASC) USING BTREE,
  INDEX `idx_graph_questions_graph_class_id`(`graph_class_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 546 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_relationships
-- ----------------------------
DROP TABLE IF EXISTS `graph_relationships`;
CREATE TABLE `graph_relationships`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `relation_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_id` bigint UNSIGNED NOT NULL,
  `target_id` bigint UNSIGNED NOT NULL,
  `source_label` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_label` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `relation_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_graph_relationship_relation_id`(`relation_id` ASC) USING BTREE,
  INDEX `idx_legacy_rel_source_id`(`source_id` ASC) USING BTREE,
  INDEX `idx_legacy_rel_target_id`(`target_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 16668 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for graph_themes
-- ----------------------------
DROP TABLE IF EXISTS `graph_themes`;
CREATE TABLE `graph_themes`  (
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `importance` decimal(10, 2) NULL DEFAULT NULL,
  `difficulty` decimal(10, 2) NULL DEFAULT NULL,
  `mastery` decimal(10, 2) NULL DEFAULT NULL,
  `test_num` int NOT NULL DEFAULT 0,
  `test_right_num` int NOT NULL DEFAULT 0,
  `taught` tinyint(1) NOT NULL DEFAULT 0,
  `id` bigint UNSIGNED NOT NULL,
  `graph_class_id` bigint UNSIGNED NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_graph_themes_graph_class_id`(`graph_class_id` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for student_mastery
-- ----------------------------
DROP TABLE IF EXISTS `student_mastery`;
CREATE TABLE `student_mastery`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `student_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `class_id` bigint UNSIGNED NOT NULL,
  `node_type` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `node_id` bigint UNSIGNED NOT NULL,
  `node_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `attempted_count` int UNSIGNED NOT NULL DEFAULT 0,
  `correct_equivalent` decimal(12, 4) NOT NULL DEFAULT 0.0000,
  `wrong_equivalent` decimal(12, 4) NOT NULL DEFAULT 0.0000,
  `accuracy_score` decimal(6, 2) NOT NULL DEFAULT 0.00,
  `mastery_score` decimal(6, 2) NOT NULL DEFAULT 0.00,
  `last_answered_at` datetime NULL DEFAULT NULL,
  `calculation_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'legacy_compatible_v1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_student_mastery_node`(`student_username` ASC, `class_id` ASC, `node_type` ASC, `node_id` ASC) USING BTREE,
  INDEX `idx_student_mastery_student_class`(`student_username` ASC, `class_id` ASC) USING BTREE,
  INDEX `idx_student_mastery_node`(`node_type` ASC, `node_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 48978 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for student_questionnaires
-- ----------------------------
DROP TABLE IF EXISTS `student_questionnaires`;
CREATE TABLE `student_questionnaires`  (
  `student_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `responses_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_completed` tinyint(1) NOT NULL DEFAULT 0,
  `completed_at` datetime NULL DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`student_username`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for submission_grades
-- ----------------------------
DROP TABLE IF EXISTS `submission_grades`;
CREATE TABLE `submission_grades`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `submission_id` bigint UNSIGNED NOT NULL,
  `question_position` int NOT NULL,
  `time_spent_seconds` int UNSIGNED NULL DEFAULT NULL,
  `score` decimal(8, 2) NOT NULL DEFAULT 0.00,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'graded',
  `feedback` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `provider` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'objective',
  `grading_details_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_submission_grades_submission_question`(`submission_id` ASC, `question_position` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 19685 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for submissions
-- ----------------------------
DROP TABLE IF EXISTS `submissions`;
CREATE TABLE `submissions`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `assignment_id` bigint UNSIGNED NOT NULL,
  `student_username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `attempt_no` int NOT NULL DEFAULT 1,
  `makeup_window_id` bigint UNSIGNED NULL DEFAULT NULL,
  `submission_mode` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft',
  `answers_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `time_spent_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `score` decimal(8, 2) NULL DEFAULT NULL,
  `submitted_at` datetime NULL DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_submission_student_assignment`(`student_username` ASC, `assignment_id` ASC) USING BTREE,
  INDEX `idx_submission_status`(`status` ASC) USING BTREE,
  INDEX `idx_submission_makeup`(`makeup_window_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3229 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_admins
-- ----------------------------
DROP TABLE IF EXISTS `user_admins`;
CREATE TABLE `user_admins`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '系统管理员',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_user_admins_username`(`username` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_students
-- ----------------------------
DROP TABLE IF EXISTS `user_students`;
CREATE TABLE `user_students`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `gender` int NULL DEFAULT NULL,
  `study_class` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `stu_classify` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `test_num` int NOT NULL DEFAULT 0,
  `test_right_num` int NOT NULL DEFAULT 0,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_user_students_username`(`username` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 526 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for user_teachers
-- ----------------------------
DROP TABLE IF EXISTS `user_teachers`;
CREATE TABLE `user_teachers`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '教师',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_user_teachers_username`(`username` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------
-- Bootstrap admin account
-- The password_hash below is the Django PBKDF2 hash for the default password: admin123
-- This is idempotent: create admin if missing, otherwise preserve the existing password.
-- ----------------------------
INSERT INTO `user_admins`
    (`username`, `password_hash`, `name`, `is_active`)
VALUES
    (
        'admin',
        'pbkdf2_sha256$1000000$TJnyQmnrELsiikn3MAYs1B$WyylgD/LmQlBO5kH6rgaBLQ7NNZzWvmZOAz5UYJXAZI=',
        '系统管理员',
        1
    )
ON DUPLICATE KEY UPDATE
    `name` = VALUES(`name`),
    `is_active` = 1;
