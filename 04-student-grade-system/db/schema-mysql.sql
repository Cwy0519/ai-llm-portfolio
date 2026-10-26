-- =============================================================
--  学生成绩管理系统  数据库建表脚本
--  目标数据库: MySQL 8.0+
--  字符集    : utf8mb4
--  说明      : 本脚本为论文答辩演示用的标准 MySQL 版本。
--              系统运行时默认使用 H2 嵌入式数据库（结构完全一致），
--              如需切换 MySQL，见 application-mysql.properties。
-- =============================================================

DROP DATABASE IF EXISTS student_grade_system;
CREATE DATABASE student_grade_system
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE student_grade_system;

-- -------------------------------------------------------------
-- 1. RBAC 权限模型：用户 / 角色 / 权限
-- -------------------------------------------------------------

-- 用户表：所有登录账号（管理员、教师、学生共用一张表，通过角色区分）
CREATE TABLE sys_user (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    username      VARCHAR(50)  NOT NULL                COMMENT '登录账号',
    password      VARCHAR(100) NOT NULL                COMMENT '密码（BCrypt 加密存储）',
    real_name     VARCHAR(50)  NOT NULL                COMMENT '真实姓名',
    gender        TINYINT      DEFAULT 1               COMMENT '性别 1男 0女',
    phone         VARCHAR(20)  DEFAULT NULL            COMMENT '联系电话',
    email         VARCHAR(100) DEFAULT NULL            COMMENT '邮箱',
    status        TINYINT      NOT NULL DEFAULT 1      COMMENT '状态 1启用 0禁用',
    create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

-- 角色表
CREATE TABLE sys_role (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    role_code   VARCHAR(30) NOT NULL                COMMENT '角色编码 ADMIN/TEACHER/STUDENT',
    role_name   VARCHAR(50) NOT NULL                COMMENT '角色名称',
    remark      VARCHAR(200) DEFAULT NULL           COMMENT '备注',
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_code (role_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表
CREATE TABLE sys_permission (
    id         BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    perm_code  VARCHAR(60) NOT NULL                COMMENT '权限编码 如 student:add',
    perm_name  VARCHAR(50) NOT NULL                COMMENT '权限名称',
    perm_type  VARCHAR(20) NOT NULL DEFAULT 'API'  COMMENT '类型 MENU菜单 API接口',
    parent_id  BIGINT      DEFAULT 0               COMMENT '父级ID',
    PRIMARY KEY (id),
    UNIQUE KEY uk_perm_code (perm_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 用户-角色 关联表（多对多）
CREATE TABLE sys_user_role (
    id       BIGINT NOT NULL AUTO_INCREMENT,
    user_id  BIGINT NOT NULL COMMENT '用户ID',
    role_id  BIGINT NOT NULL COMMENT '角色ID',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_role (user_id, role_id),
    KEY idx_ur_user (user_id),
    CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES sys_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES sys_role (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联表';

-- 角色-权限 关联表（多对多）
CREATE TABLE sys_role_permission (
    id       BIGINT NOT NULL AUTO_INCREMENT,
    role_id  BIGINT NOT NULL COMMENT '角色ID',
    perm_id  BIGINT NOT NULL COMMENT '权限ID',
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_perm (role_id, perm_id),
    KEY idx_rp_role (role_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES sys_role (id) ON DELETE CASCADE,
    CONSTRAINT fk_rp_perm FOREIGN KEY (perm_id) REFERENCES sys_permission (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';

-- -------------------------------------------------------------
-- 2. 基础信息：学院 / 专业 / 班级
-- -------------------------------------------------------------

CREATE TABLE base_college (
    id            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    college_name  VARCHAR(100) NOT NULL               COMMENT '学院名称',
    college_code  VARCHAR(30)  NOT NULL               COMMENT '学院编码',
    PRIMARY KEY (id),
    UNIQUE KEY uk_college_code (college_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学院表';

CREATE TABLE base_major (
    id           BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    major_name   VARCHAR(100) NOT NULL               COMMENT '专业名称',
    major_code   VARCHAR(30)  NOT NULL               COMMENT '专业编码',
    college_id   BIGINT       NOT NULL               COMMENT '所属学院ID',
    PRIMARY KEY (id),
    UNIQUE KEY uk_major_code (major_code),
    KEY idx_major_college (college_id),
    CONSTRAINT fk_major_college FOREIGN KEY (college_id) REFERENCES base_college (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='专业表';

CREATE TABLE base_class (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    class_name  VARCHAR(100) NOT NULL               COMMENT '班级名称',
    class_code  VARCHAR(30)  NOT NULL               COMMENT '班级编码',
    major_id    BIGINT       NOT NULL               COMMENT '所属专业ID',
    grade_year  INT          NOT NULL               COMMENT '入学年份',
    PRIMARY KEY (id),
    UNIQUE KEY uk_class_code (class_code),
    KEY idx_class_major (major_id),
    CONSTRAINT fk_class_major FOREIGN KEY (major_id) REFERENCES base_major (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='班级表';

-- 学生表（业务信息，登录信息在 sys_user）
CREATE TABLE info_student (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    user_id     BIGINT      NOT NULL               COMMENT '关联用户ID',
    stu_no      VARCHAR(30) NOT NULL               COMMENT '学号',
    class_id    BIGINT      NOT NULL               COMMENT '班级ID',
    enroll_year INT         DEFAULT NULL           COMMENT '入学年份',
    PRIMARY KEY (id),
    UNIQUE KEY uk_stu_no (stu_no),
    UNIQUE KEY uk_stu_user (user_id),
    KEY idx_stu_class (class_id),
    CONSTRAINT fk_stu_user FOREIGN KEY (user_id) REFERENCES sys_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_stu_class FOREIGN KEY (class_id) REFERENCES base_class (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生信息表';

-- 教师表
CREATE TABLE info_teacher (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    user_id     BIGINT      NOT NULL               COMMENT '关联用户ID',
    teacher_no  VARCHAR(30) NOT NULL               COMMENT '工号',
    college_id  BIGINT      DEFAULT NULL           COMMENT '所属学院ID',
    title       VARCHAR(50) DEFAULT NULL           COMMENT '职称',
    PRIMARY KEY (id),
    UNIQUE KEY uk_teacher_no (teacher_no),
    UNIQUE KEY uk_teacher_user (user_id),
    CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES sys_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_teacher_college FOREIGN KEY (college_id) REFERENCES base_college (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教师信息表';

-- -------------------------------------------------------------
-- 3. 课程与教学任务
-- -------------------------------------------------------------

CREATE TABLE course (
    id           BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    course_code  VARCHAR(30) NOT NULL               COMMENT '课程编码',
    course_name  VARCHAR(100) NOT NULL              COMMENT '课程名称',
    credit       DECIMAL(3,1) NOT NULL DEFAULT 2.0  COMMENT '学分',
    course_type  TINYINT     NOT NULL DEFAULT 1     COMMENT '类型 1必修 2选修',
    status       TINYINT     NOT NULL DEFAULT 1     COMMENT '状态 1正常 0停用',
    PRIMARY KEY (id),
    UNIQUE KEY uk_course_code (course_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程表';

-- 教学任务：某教师在某学期教某班级某课程
CREATE TABLE teaching_task (
    id          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    teacher_id  BIGINT      NOT NULL               COMMENT '教师ID',
    course_id   BIGINT      NOT NULL               COMMENT '课程ID',
    class_id    BIGINT      NOT NULL               COMMENT '班级ID',
    semester    VARCHAR(20) NOT NULL               COMMENT '学期 如 2025-2026-1',
    PRIMARY KEY (id),
    UNIQUE KEY uk_task (teacher_id, course_id, class_id, semester),
    KEY idx_task_teacher (teacher_id),
    KEY idx_task_course (course_id),
    KEY idx_task_class (class_id),
    CONSTRAINT fk_task_teacher FOREIGN KEY (teacher_id) REFERENCES info_teacher (id),
    CONSTRAINT fk_task_course FOREIGN KEY (course_id) REFERENCES course (id),
    CONSTRAINT fk_task_class FOREIGN KEY (class_id) REFERENCES base_class (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='教学任务表';

-- -------------------------------------------------------------
-- 4. 成绩（核心业务）
-- -------------------------------------------------------------

-- 成绩表：记录平时/期中/期末原始分，以及折算后的总评
CREATE TABLE score (
    id             BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    student_id     BIGINT      NOT NULL               COMMENT '学生ID',
    course_id      BIGINT      NOT NULL               COMMENT '课程ID',
    semester       VARCHAR(20) NOT NULL               COMMENT '学期',
    usual_score    DECIMAL(5,2) DEFAULT NULL          COMMENT '平时成绩',
    midterm_score  DECIMAL(5,2) DEFAULT NULL          COMMENT '期中成绩',
    final_score    DECIMAL(5,2) DEFAULT NULL          COMMENT '期末成绩',
    total_score    DECIMAL(5,2) DEFAULT NULL          COMMENT '总评成绩（按权重折算）',
    grade_point    DECIMAL(3,2) DEFAULT NULL          COMMENT '绩点',
    input_by       BIGINT      DEFAULT NULL           COMMENT '录入教师ID',
    input_time     DATETIME    DEFAULT NULL           COMMENT '录入时间',
    update_time    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后修改时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_score (student_id, course_id, semester),
    KEY idx_score_student (student_id),
    KEY idx_score_course (course_id),
    CONSTRAINT fk_score_student FOREIGN KEY (student_id) REFERENCES info_student (id) ON DELETE CASCADE,
    CONSTRAINT fk_score_course FOREIGN KEY (course_id) REFERENCES course (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学生成绩表';

-- 成绩折算规则：可按课程配置不同权重
CREATE TABLE score_rule (
    id            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
    course_id     BIGINT      NOT NULL               COMMENT '课程ID，0 表示全局默认',
    usual_weight  DECIMAL(4,2) NOT NULL DEFAULT 0.30 COMMENT '平时成绩权重',
    midterm_weight DECIMAL(4,2) NOT NULL DEFAULT 0.20 COMMENT '期中成绩权重',
    final_weight  DECIMAL(4,2) NOT NULL DEFAULT 0.50 COMMENT '期末成绩权重',
    pass_score    DECIMAL(5,2) NOT NULL DEFAULT 60.00 COMMENT '及格线',
    PRIMARY KEY (id),
    UNIQUE KEY uk_rule_course (course_id),
    CONSTRAINT fk_rule_course FOREIGN KEY (course_id) REFERENCES course (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成绩折算规则表';

-- 成绩修改日志：实现"成绩安全录入"的审计追溯
CREATE TABLE score_log (
    id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    score_id    BIGINT       NOT NULL               COMMENT '成绩ID',
    operator_id BIGINT       NOT NULL               COMMENT '操作人ID',
    action      VARCHAR(20)  NOT NULL               COMMENT '动作 INSERT/UPDATE',
    old_value   VARCHAR(200) DEFAULT NULL           COMMENT '修改前内容',
    new_value   VARCHAR(200) DEFAULT NULL           COMMENT '修改后内容',
    operate_time DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (id),
    KEY idx_log_score (score_id),
    KEY idx_log_operator (operator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成绩修改审计日志';
