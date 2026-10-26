-- =============================================================
--  学生成绩管理系统  H2 初始化数据（幂等脚本）
--  使用 MERGE INTO ... KEY(...) 语法：
--  记录不存在则插入，已存在则更新，保证重复启动不冲突
--  所有账号密码统一为 123456（BCrypt 加密）
--  演示账号：admin / teacher1 / student1，密码均为 123456
-- =============================================================

-- ---------- 角色 ----------
MERGE INTO sys_role (id, role_code, role_name, remark) KEY (id) VALUES
(1, 'ADMIN',   '管理员', '拥有系统全部权限');
MERGE INTO sys_role (id, role_code, role_name, remark) KEY (id) VALUES
(2, 'TEACHER', '教师',   '管理所授课程与成绩');
MERGE INTO sys_role (id, role_code, role_name, remark) KEY (id) VALUES
(3, 'STUDENT', '学生',   '查询本人成绩');

-- ---------- 权限 ----------
MERGE INTO sys_permission (id, perm_code, perm_name, perm_type, parent_id) KEY (id) VALUES
(1,  'student:view',   '查看学生',    'API', 0),
(2,  'student:add',    '新增学生',    'API', 1),
(3,  'student:edit',   '编辑学生',    'API', 1),
(4,  'student:delete', '删除学生',    'API', 1),
(5,  'teacher:view',   '查看教师',    'API', 0),
(6,  'teacher:add',    '新增教师',    'API', 5),
(7,  'teacher:edit',   '编辑教师',    'API', 5),
(8,  'teacher:delete', '删除教师',    'API', 5),
(9,  'course:view',    '查看课程',    'API', 0),
(10, 'course:add',     '新增课程',    'API', 9),
(11, 'course:edit',    '编辑课程',    'API', 9),
(12, 'course:delete',  '删除课程',    'API', 9),
(13, 'score:view',     '查看成绩',    'API', 0),
(14, 'score:input',    '录入成绩',    'API', 13),
(15, 'score:edit',     '修改成绩',    'API', 13),
(16, 'score:audit',    '查看审计日志','API', 13),
(17, 'stats:view',     '查看统计分析','API', 0),
(18, 'user:manage',    '用户管理',    'API', 0);

-- ---------- 角色权限（管理员=全部，教师=8项，学生=2项） ----------
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (1, 1, 1);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (2, 1, 2);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (3, 1, 3);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (4, 1, 4);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (5, 1, 5);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (6, 1, 6);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (7, 1, 7);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (8, 1, 8);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (9, 1, 9);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (10, 1, 10);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (11, 1, 11);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (12, 1, 12);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (13, 1, 13);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (14, 1, 14);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (15, 1, 15);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (16, 1, 16);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (17, 1, 17);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (18, 1, 18);

-- 教师权限
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (19, 2, 1);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (20, 2, 5);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (21, 2, 9);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (22, 2, 13);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (23, 2, 14);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (24, 2, 15);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (25, 2, 16);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (26, 2, 17);

-- 学生权限
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (27, 3, 13);
MERGE INTO sys_role_permission (id, role_id, perm_id) KEY (role_id, perm_id) VALUES (28, 3, 17);

-- ---------- 用户（密码 123456） ----------
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(1, 'admin',    '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '系统管理员', 1, '13800000001', 'admin@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(2, 'teacher1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '张明', 1, '13800000002', 'zhangming@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(3, 'teacher2', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '李红', 0, '13800000003', 'lihong@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(4, 'student1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '王小明', 1, '13800000004', 'wxm@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(5, 'student2', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '刘芳', 0, '13800000005', 'liufang@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(6, 'student3', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '陈刚', 1, '13800000006', 'chengang@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(7, 'student4', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '赵雪', 0, '13800000007', 'zhaoxue@school.edu.cn', 1);
MERGE INTO sys_user (id, username, password, real_name, gender, phone, email, status) KEY (id) VALUES
(8, 'student5', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKTVKIUi', '孙磊', 1, '13800000008', 'sunlei@school.edu.cn', 1);

MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (1, 1, 1);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (2, 2, 2);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (3, 3, 2);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (4, 4, 3);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (5, 5, 3);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (6, 6, 3);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (7, 7, 3);
MERGE INTO sys_user_role (id, user_id, role_id) KEY (user_id, role_id) VALUES (8, 8, 3);

-- ---------- 学院 / 专业 / 班级 ----------
MERGE INTO base_college (id, college_name, college_code) KEY (id) VALUES (1, '计算机科学与技术学院', 'CS');
MERGE INTO base_college (id, college_name, college_code) KEY (id) VALUES (2, '经济管理学院', 'EM');

MERGE INTO base_major (id, major_name, major_code, college_id) KEY (id) VALUES (1, '软件工程', 'SE', 1);
MERGE INTO base_major (id, major_name, major_code, college_id) KEY (id) VALUES (2, '计算机科学与技术', 'CST', 1);
MERGE INTO base_major (id, major_name, major_code, college_id) KEY (id) VALUES (3, '信息管理与信息系统', 'IMS', 2);

MERGE INTO base_class (id, class_name, class_code, major_id, grade_year) KEY (id) VALUES (1, '软件工程2301班', 'SE2301', 1, 2023);
MERGE INTO base_class (id, class_name, class_code, major_id, grade_year) KEY (id) VALUES (2, '软件工程2302班', 'SE2302', 1, 2023);
MERGE INTO base_class (id, class_name, class_code, major_id, grade_year) KEY (id) VALUES (3, '计科2301班', 'CST2301', 2, 2023);

-- ---------- 学生 / 教师 ----------
MERGE INTO info_student (id, user_id, stu_no, class_id, enroll_year) KEY (id) VALUES (1, 4, '2023010101', 1, 2023);
MERGE INTO info_student (id, user_id, stu_no, class_id, enroll_year) KEY (id) VALUES (2, 5, '2023010102', 1, 2023);
MERGE INTO info_student (id, user_id, stu_no, class_id, enroll_year) KEY (id) VALUES (3, 6, '2023010103', 1, 2023);
MERGE INTO info_student (id, user_id, stu_no, class_id, enroll_year) KEY (id) VALUES (4, 7, '2023020101', 2, 2023);
MERGE INTO info_student (id, user_id, stu_no, class_id, enroll_year) KEY (id) VALUES (5, 8, '2023020102', 2, 2023);

MERGE INTO info_teacher (id, user_id, teacher_no, college_id, title) KEY (id) VALUES (1, 2, 'T2001', 1, '副教授');
MERGE INTO info_teacher (id, user_id, teacher_no, college_id, title) KEY (id) VALUES (2, 3, 'T2002', 1, '讲师');

-- ---------- 课程 ----------
MERGE INTO course (id, course_code, course_name, credit, course_type, status) KEY (id) VALUES (1, 'CS101', 'Java程序设计', 4.0, 1, 1);
MERGE INTO course (id, course_code, course_name, credit, course_type, status) KEY (id) VALUES (2, 'CS102', '数据库原理', 3.0, 1, 1);
MERGE INTO course (id, course_code, course_name, credit, course_type, status) KEY (id) VALUES (3, 'CS103', '数据结构', 4.0, 1, 1);
MERGE INTO course (id, course_code, course_name, credit, course_type, status) KEY (id) VALUES (4, 'CS201', 'Web前端开发', 3.0, 2, 1);
MERGE INTO course (id, course_code, course_name, credit, course_type, status) KEY (id) VALUES (5, 'EM101', '管理学原理', 2.0, 2, 1);

-- ---------- 教学任务 ----------
MERGE INTO teaching_task (id, teacher_id, course_id, class_id, semester) KEY (id) VALUES (1, 1, 1, 1, '2025-2026-1');
MERGE INTO teaching_task (id, teacher_id, course_id, class_id, semester) KEY (id) VALUES (2, 1, 3, 1, '2025-2026-1');
MERGE INTO teaching_task (id, teacher_id, course_id, class_id, semester) KEY (id) VALUES (3, 2, 2, 1, '2025-2026-1');
MERGE INTO teaching_task (id, teacher_id, course_id, class_id, semester) KEY (id) VALUES (4, 2, 2, 2, '2025-2026-1');
MERGE INTO teaching_task (id, teacher_id, course_id, class_id, semester) KEY (id) VALUES (5, 1, 4, 2, '2025-2026-1');

-- ---------- 成绩折算规则 ----------
MERGE INTO score_rule (id, course_id, usual_weight, midterm_weight, final_weight, pass_score) KEY (id) VALUES (1, 1, 0.30, 0.20, 0.50, 60.00);
MERGE INTO score_rule (id, course_id, usual_weight, midterm_weight, final_weight, pass_score) KEY (id) VALUES (2, 2, 0.20, 0.30, 0.50, 60.00);
MERGE INTO score_rule (id, course_id, usual_weight, midterm_weight, final_weight, pass_score) KEY (id) VALUES (3, 3, 0.30, 0.20, 0.50, 60.00);

-- ---------- 成绩（绩点严格按算法换算） ----------
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (1, 1, 1, '2025-2026-1', 88.0, 85.0, 92.0, 89.4, 3.7, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (2, 2, 1, '2025-2026-1', 76.0, 80.0, 71.0, 74.3, 2.3, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (3, 3, 1, '2025-2026-1', 95.0, 92.0, 96.0, 94.9, 4.0, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (4, 4, 1, '2025-2026-1', 62.0, 58.0, 55.0, 57.7, 0.0, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (5, 5, 1, '2025-2026-1', 84.0, 78.0, 86.0, 83.8, 3.3, 2, CURRENT_TIMESTAMP);

MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (6, 1, 2, '2025-2026-1', 90.0, 88.0, 91.0, 89.9, 3.7, 3, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (7, 2, 2, '2025-2026-1', 82.0, 75.0, 79.0, 78.9, 3.0, 3, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (8, 3, 2, '2025-2026-1', 70.0, 66.0, 73.0, 70.3, 2.0, 3, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (9, 4, 2, '2025-2026-1', 88.0, 90.0, 85.0, 87.1, 3.7, 3, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (10, 5, 2, '2025-2026-1', 55.0, 60.0, 52.0, 54.5, 0.0, 3, CURRENT_TIMESTAMP);

MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (11, 1, 3, '2025-2026-1', 85.0, 82.0, 88.0, 85.9, 3.7, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (12, 2, 3, '2025-2026-1', 91.0, 89.0, 94.0, 92.1, 4.0, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (13, 3, 3, '2025-2026-1', 78.0, 72.0, 80.0, 77.8, 2.7, 2, CURRENT_TIMESTAMP);
MERGE INTO score (id, student_id, course_id, semester, usual_score, midterm_score, final_score, total_score, grade_point, input_by, input_time) KEY (id) VALUES (14, 4, 3, '2025-2026-1', 68.0, 70.0, 65.0, 67.1, 1.5, 2, CURRENT_TIMESTAMP);
