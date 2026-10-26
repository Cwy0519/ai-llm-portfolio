-- =============================================================
--  学生成绩管理系统  H2 建表脚本（MySQL 兼容模式）
--  与 db/schema-mysql.sql 结构完全一致
-- =============================================================

-- ---------- RBAC ----------
CREATE TABLE IF NOT EXISTS sys_user (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(50)  NOT NULL UNIQUE,
    password     VARCHAR(100) NOT NULL,
    real_name    VARCHAR(50)  NOT NULL,
    gender       TINYINT      DEFAULT 1,
    phone        VARCHAR(20),
    email        VARCHAR(100),
    status       TINYINT      NOT NULL DEFAULT 1,
    create_time  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sys_role (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_code  VARCHAR(30) NOT NULL UNIQUE,
    role_name  VARCHAR(50) NOT NULL,
    remark     VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS sys_permission (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    perm_code  VARCHAR(60) NOT NULL UNIQUE,
    perm_name  VARCHAR(50) NOT NULL,
    perm_type  VARCHAR(20) NOT NULL DEFAULT 'API',
    parent_id  BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sys_user_role (
    id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id  BIGINT NOT NULL,
    role_id  BIGINT NOT NULL,
    CONSTRAINT uk_user_role UNIQUE (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS sys_role_permission (
    id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id  BIGINT NOT NULL,
    perm_id  BIGINT NOT NULL,
    CONSTRAINT uk_role_perm UNIQUE (role_id, perm_id)
);

-- ---------- 基础信息 ----------
CREATE TABLE IF NOT EXISTS base_college (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    college_name VARCHAR(100) NOT NULL,
    college_code VARCHAR(30)  NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS base_major (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    major_name VARCHAR(100) NOT NULL,
    major_code VARCHAR(30)  NOT NULL UNIQUE,
    college_id BIGINT       NOT NULL
);

CREATE TABLE IF NOT EXISTS base_class (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(100) NOT NULL,
    class_code VARCHAR(30)  NOT NULL UNIQUE,
    major_id   BIGINT       NOT NULL,
    grade_year INT          NOT NULL
);

CREATE TABLE IF NOT EXISTS info_student (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     BIGINT      NOT NULL UNIQUE,
    stu_no      VARCHAR(30) NOT NULL UNIQUE,
    class_id    BIGINT      NOT NULL,
    enroll_year INT
);

CREATE TABLE IF NOT EXISTS info_teacher (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id    BIGINT      NOT NULL UNIQUE,
    teacher_no VARCHAR(30) NOT NULL UNIQUE,
    college_id BIGINT,
    title      VARCHAR(50)
);

-- ---------- 课程 ----------
CREATE TABLE IF NOT EXISTS course (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    course_code VARCHAR(30)   NOT NULL UNIQUE,
    course_name VARCHAR(100)  NOT NULL,
    credit      DECIMAL(3,1)  NOT NULL DEFAULT 2.0,
    course_type TINYINT       NOT NULL DEFAULT 1,
    status      TINYINT       NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS teaching_task (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    teacher_id BIGINT      NOT NULL,
    course_id  BIGINT      NOT NULL,
    class_id   BIGINT      NOT NULL,
    semester   VARCHAR(20) NOT NULL,
    CONSTRAINT uk_task UNIQUE (teacher_id, course_id, class_id, semester)
);

-- ---------- 成绩 ----------
CREATE TABLE IF NOT EXISTS score (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    student_id    BIGINT      NOT NULL,
    course_id     BIGINT      NOT NULL,
    semester      VARCHAR(20) NOT NULL,
    usual_score   DECIMAL(5,2),
    midterm_score DECIMAL(5,2),
    final_score   DECIMAL(5,2),
    total_score   DECIMAL(5,2),
    grade_point   DECIMAL(3,2),
    input_by      BIGINT,
    input_time    TIMESTAMP,
    update_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_score UNIQUE (student_id, course_id, semester)
);

CREATE TABLE IF NOT EXISTS score_rule (
    id             BIGINT AUTO_INCREMENT PRIMARY KEY,
    course_id      BIGINT      NOT NULL UNIQUE,
    usual_weight   DECIMAL(4,2) NOT NULL DEFAULT 0.30,
    midterm_weight DECIMAL(4,2) NOT NULL DEFAULT 0.20,
    final_weight   DECIMAL(4,2) NOT NULL DEFAULT 0.50,
    pass_score     DECIMAL(5,2) NOT NULL DEFAULT 60.00
);

CREATE TABLE IF NOT EXISTS score_log (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    score_id     BIGINT      NOT NULL,
    operator_id  BIGINT      NOT NULL,
    action       VARCHAR(20) NOT NULL,
    old_value    VARCHAR(200),
    new_value    VARCHAR(200),
    operate_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
