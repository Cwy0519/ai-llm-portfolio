package com.sgs.service;

import com.sgs.common.BusinessException;
import com.sgs.entity.Course;
import com.sgs.entity.SysUser;
import com.sgs.entity.Teacher;
import com.sgs.repository.CourseRepository;
import com.sgs.repository.SysUserRepository;
import com.sgs.repository.TeacherRepository;
import com.sgs.security.LoginUser;
import com.sgs.security.UserContext;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.*;

/**
 * 基础信息管理：学生、教师、课程
 */
@Service
@RequiredArgsConstructor
public class BasicInfoService {

    private final SysUserRepository userRepository;
    private final com.sgs.repository.StudentRepository studentRepository;
    private final TeacherRepository teacherRepository;
    private final CourseRepository courseRepository;
    private final com.sgs.repository.SchoolClassRepository classRepository;
    private final PasswordEncoder passwordEncoder;
    private final jakarta.persistence.EntityManager em;

    private void requirePerm(String perm) {
        LoginUser u = UserContext.require();
        if (!u.hasPermission(perm)) {
            throw new BusinessException(403, "无权限执行该操作");
        }
    }

    // ================= 学生 =================

    public List<Map<String, Object>> listStudents() {
        requirePerm("student:view");
        @SuppressWarnings("unchecked")
        List<Object[]> rows = em.createNativeQuery(
                "SELECT st.id, st.stu_no, u.real_name, u.gender, u.phone, cl.class_name, " +
                "st.enroll_year, u.username, u.status " +
                "FROM info_student st " +
                "JOIN sys_user u ON u.id = st.user_id " +
                "JOIN base_class cl ON cl.id = st.class_id " +
                "ORDER BY st.stu_no").getResultList();

        List<Map<String, Object>> list = new ArrayList<>();
        for (Object[] r : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r[0]);
            m.put("stuNo", r[1]);
            m.put("realName", r[2]);
            m.put("gender", r[3]);
            m.put("phone", r[4]);
            m.put("className", r[5]);
            m.put("enrollYear", r[6]);
            m.put("username", r[7]);
            m.put("status", r[8]);
            list.add(m);
        }
        return list;
    }

    @Transactional
    public Long addStudent(Map<String, Object> body) {
        requirePerm("student:add");
        String username = str(body.get("username"));
        String stuNo = str(body.get("stuNo"));
        if (username.isBlank() || stuNo.isBlank()) {
            throw new BusinessException("账号和学号不能为空");
        }
        if (userRepository.existsByUsername(username)) {
            throw new BusinessException("账号已存在");
        }
        if (studentRepository.existsByStuNo(stuNo)) {
            throw new BusinessException("学号已存在");
        }

        SysUser u = new SysUser();
        u.setUsername(username);
        u.setPassword(passwordEncoder.encode(
                body.get("password") == null ? "123456" : str(body.get("password"))));
        u.setRealName(str(body.get("realName")));
        u.setGender(intv(body.get("gender"), 1));
        u.setPhone(str(body.get("phone")));
        u.setEmail(str(body.get("email")));
        u.setStatus(1);
        SysUser saved = userRepository.save(u);

        com.sgs.entity.Student s = new com.sgs.entity.Student();
        s.setUserId(saved.getId());
        s.setStuNo(stuNo);
        s.setClassId(longv(body.get("classId")));
        s.setEnrollYear(intv(body.get("enrollYear"), null));
        com.sgs.entity.Student savedStu = studentRepository.save(s);

        // 绑定 STUDENT 角色
        em.createNativeQuery("INSERT INTO sys_user_role (user_id, role_id) VALUES (:uid, " +
                        "(SELECT id FROM sys_role WHERE role_code='STUDENT'))")
                .setParameter("uid", saved.getId())
                .executeUpdate();

        return savedStu.getId();
    }

    @Transactional
    public void deleteStudent(Long id) {
        requirePerm("student:delete");
        com.sgs.entity.Student s = studentRepository.findById(id)
                .orElseThrow(() -> new BusinessException(404, "学生不存在"));
        studentRepository.delete(s);
        userRepository.findById(s.getUserId()).ifPresent(u -> {
            u.setStatus(0);
            userRepository.save(u);
        });
    }

    // ================= 教师 =================

    public List<Map<String, Object>> listTeachers() {
        requirePerm("teacher:view");
        @SuppressWarnings("unchecked")
        List<Object[]> rows = em.createNativeQuery(
                "SELECT t.id, t.teacher_no, u.real_name, u.gender, t.title, u.phone, u.username " +
                "FROM info_teacher t JOIN sys_user u ON u.id = t.user_id ORDER BY t.teacher_no")
                .getResultList();

        List<Map<String, Object>> list = new ArrayList<>();
        for (Object[] r : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r[0]);
            m.put("teacherNo", r[1]);
            m.put("realName", r[2]);
            m.put("gender", r[3]);
            m.put("title", r[4]);
            m.put("phone", r[5]);
            m.put("username", r[6]);
            list.add(m);
        }
        return list;
    }

    @Transactional
    public Long addTeacher(Map<String, Object> body) {
        requirePerm("teacher:add");
        String username = str(body.get("username"));
        String teacherNo = str(body.get("teacherNo"));
        if (username.isBlank() || teacherNo.isBlank()) {
            throw new BusinessException("账号和工号不能为空");
        }
        if (userRepository.existsByUsername(username)) {
            throw new BusinessException("账号已存在");
        }
        if (teacherRepository.existsByTeacherNo(teacherNo)) {
            throw new BusinessException("工号已存在");
        }

        SysUser u = new SysUser();
        u.setUsername(username);
        u.setPassword(passwordEncoder.encode(
                body.get("password") == null ? "123456" : str(body.get("password"))));
        u.setRealName(str(body.get("realName")));
        u.setGender(intv(body.get("gender"), 1));
        u.setPhone(str(body.get("phone")));
        u.setEmail(str(body.get("email")));
        u.setStatus(1);
        SysUser saved = userRepository.save(u);

        Teacher t = new Teacher();
        t.setUserId(saved.getId());
        t.setTeacherNo(teacherNo);
        t.setTitle(str(body.get("title")));
        t.setCollegeId(longv(body.get("collegeId")));
        Teacher savedT = teacherRepository.save(t);

        em.createNativeQuery("INSERT INTO sys_user_role (user_id, role_id) VALUES (:uid, " +
                        "(SELECT id FROM sys_role WHERE role_code='TEACHER'))")
                .setParameter("uid", saved.getId())
                .executeUpdate();

        return savedT.getId();
    }

    // ================= 课程 =================

    public List<Course> listCourses() {
        requirePerm("course:view");
        return courseRepository.findAll();
    }

    @Transactional
    public Course addCourse(Map<String, Object> body) {
        requirePerm("course:add");
        String code = str(body.get("courseCode"));
        if (courseRepository.existsByCourseCode(code)) {
            throw new BusinessException("课程编码已存在");
        }
        Course c = new Course();
        c.setCourseCode(code);
        c.setCourseName(str(body.get("courseName")));
        c.setCredit(body.get("credit") == null ? new BigDecimal("2.0")
                : new BigDecimal(body.get("credit").toString()));
        c.setCourseType(intv(body.get("courseType"), 1));
        c.setStatus(1);
        return courseRepository.save(c);
    }

    @Transactional
    public void deleteCourse(Long id) {
        requirePerm("course:delete");
        courseRepository.deleteById(id);
    }

    // ================= 班级列表（下拉用） =================

    public List<Map<String, Object>> listClasses() {
        @SuppressWarnings("unchecked")
        List<Object[]> rows = em.createNativeQuery(
                "SELECT cl.id, cl.class_name, m.major_name, co.college_name " +
                "FROM base_class cl " +
                "JOIN base_major m ON m.id = cl.major_id " +
                "JOIN base_college co ON co.id = m.college_id " +
                "ORDER BY cl.id").getResultList();
        List<Map<String, Object>> list = new ArrayList<>();
        for (Object[] r : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r[0]);
            m.put("className", r[1]);
            m.put("majorName", r[2]);
            m.put("collegeName", r[3]);
            list.add(m);
        }
        return list;
    }

    // ---------- 类型转换小工具 ----------
    private String str(Object o) {
        return o == null ? "" : o.toString().trim();
    }

    private Integer intv(Object o, Integer def) {
        if (o == null || o.toString().isBlank()) return def;
        return Integer.parseInt(o.toString());
    }

    private Long longv(Object o) {
        if (o == null || o.toString().isBlank()) return null;
        return Long.parseLong(o.toString());
    }
}
