package com.sgs.service;

import com.sgs.common.BusinessException;
import com.sgs.security.LoginUser;
import com.sgs.security.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * 统计分析服务：为 ECharts 提供图表数据
 *
 * 提供四类图表数据：
 *   1. 成绩分布（分段柱状图）
 *   2. 课程平均分对比（柱状图）
 *   3. 班级平均分对比（柱状图）
 *   4. 不及格率 / 及格率（饼图）
 *   5. 学生成绩趋势（折线图）
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class StatisticsService {

    @PersistenceContext
    private EntityManager em;

    /**
     * 成绩分布：把总评按 90-100 / 80-89 / 70-79 / 60-69 / <60 分段统计
     */
    public Map<String, Object> scoreDistribution(String semester) {
        String sql = "SELECT " +
                "SUM(CASE WHEN s.total_score >= 90 THEN 1 ELSE 0 END) AS excellent, " +
                "SUM(CASE WHEN s.total_score >= 80 AND s.total_score < 90 THEN 1 ELSE 0 END) AS good, " +
                "SUM(CASE WHEN s.total_score >= 70 AND s.total_score < 80 THEN 1 ELSE 0 END) AS medium, " +
                "SUM(CASE WHEN s.total_score >= 60 AND s.total_score < 70 THEN 1 ELSE 0 END) AS pass, " +
                "SUM(CASE WHEN s.total_score < 60 THEN 1 ELSE 0 END) AS fail, " +
                "COUNT(*) AS total " +
                "FROM score s WHERE s.total_score IS NOT NULL " +
                (semester != null && !semester.isBlank() ? "AND s.semester = :semester" : "");

        Query q = em.createNativeQuery(sql);
        if (semester != null && !semester.isBlank()) {
            q.setParameter("semester", semester);
        }
        Object[] row = (Object[]) q.getSingleResult();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("categories", List.of("90-100 优秀", "80-89 良好", "70-79 中等", "60-69 及格", "0-59 不及格"));
        result.put("values", List.of(
                toLong(row[0]), toLong(row[1]), toLong(row[2]),
                toLong(row[3]), toLong(row[4])));
        result.put("total", toLong(row[5]));
        return result;
    }

    /**
     * 各课程平均分、最高分、最低分
     */
    public Map<String, Object> courseAverage(String semester) {
        String sql = "SELECT c.course_name, AVG(s.total_score), MAX(s.total_score), MIN(s.total_score), COUNT(*) " +
                "FROM score s JOIN course c ON c.id = s.course_id " +
                "WHERE s.total_score IS NOT NULL " +
                (semester != null && !semester.isBlank() ? "AND s.semester = :semester " : "") +
                "GROUP BY c.id, c.course_name ORDER BY c.id";

        Query q = em.createNativeQuery(sql);
        if (semester != null && !semester.isBlank()) {
            q.setParameter("semester", semester);
        }
        @SuppressWarnings("unchecked")
        List<Object[]> rows = q.getResultList();

        List<String> names = new ArrayList<>();
        List<Double> avgs = new ArrayList<>();
        List<Double> maxs = new ArrayList<>();
        List<Double> mins = new ArrayList<>();

        for (Object[] r : rows) {
            names.add(String.valueOf(r[0]));
            avgs.add(round(r[1]));
            maxs.add(round(r[2]));
            mins.add(round(r[3]));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("courses", names);
        result.put("average", avgs);
        result.put("max", maxs);
        result.put("min", mins);
        return result;
    }

    /**
     * 班级平均分对比
     */
    public Map<String, Object> classAverage(String semester) {
        String sql = "SELECT cl.class_name, AVG(s.total_score), COUNT(*) " +
                "FROM score s " +
                "JOIN info_student st ON st.id = s.student_id " +
                "JOIN base_class cl ON cl.id = st.class_id " +
                "WHERE s.total_score IS NOT NULL " +
                (semester != null && !semester.isBlank() ? "AND s.semester = :semester " : "") +
                "GROUP BY cl.id, cl.class_name ORDER BY cl.id";

        Query q = em.createNativeQuery(sql);
        if (semester != null && !semester.isBlank()) {
            q.setParameter("semester", semester);
        }
        @SuppressWarnings("unchecked")
        List<Object[]> rows = q.getResultList();

        List<String> names = new ArrayList<>();
        List<Double> avgs = new ArrayList<>();
        for (Object[] r : rows) {
            names.add(String.valueOf(r[0]));
            avgs.add(round(r[1]));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("classes", names);
        result.put("average", avgs);
        return result;
    }

    /**
     * 及格 / 不及格比例（饼图）
     */
    public Map<String, Object> passRate(String semester) {
        String sql = "SELECT " +
                "SUM(CASE WHEN s.total_score >= 60 THEN 1 ELSE 0 END) AS passed, " +
                "SUM(CASE WHEN s.total_score < 60 THEN 1 ELSE 0 END) AS failed " +
                "FROM score s WHERE s.total_score IS NOT NULL " +
                (semester != null && !semester.isBlank() ? "AND s.semester = :semester" : "");

        Query q = em.createNativeQuery(sql);
        if (semester != null && !semester.isBlank()) {
            q.setParameter("semester", semester);
        }
        Object[] row = (Object[]) q.getSingleResult();

        long passed = toLong(row[0]);
        long failed = toLong(row[1]);
        long total = passed + failed;
        double rate = total == 0 ? 0 : Math.round(passed * 1000.0 / total) / 10.0;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("data", List.of(
                Map.of("name", "及格", "value", passed),
                Map.of("name", "不及格", "value", failed)));
        result.put("passRate", rate);
        return result;
    }

    /**
     * 单个学生各课程成绩（折线图）
     */
    public Map<String, Object> studentTrend(Long studentId) {
        LoginUser user = UserContext.require();

        // 学生只能看自己
        if (user.hasRole("STUDENT")) {
            Long selfId = currentStudentId(user.getUserId());
            if (!selfId.equals(studentId)) {
                throw new BusinessException(403, "只能查看本人成绩");
            }
        }

        String sql = "SELECT c.course_name, s.total_score " +
                "FROM score s JOIN course c ON c.id = s.course_id " +
                "WHERE s.student_id = :sid AND s.total_score IS NOT NULL " +
                "ORDER BY c.id";

        Query q = em.createNativeQuery(sql);
        q.setParameter("sid", studentId);
        @SuppressWarnings("unchecked")
        List<Object[]> rows = q.getResultList();

        List<String> courses = new ArrayList<>();
        List<Double> scores = new ArrayList<>();
        for (Object[] r : rows) {
            courses.add(String.valueOf(r[0]));
            scores.add(round(r[1]));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("courses", courses);
        result.put("scores", scores);
        return result;
    }

    /** 可选学期列表 */
    public List<String> listSemesters() {
        Query q = em.createNativeQuery(
                "SELECT DISTINCT semester FROM score WHERE semester IS NOT NULL ORDER BY semester DESC");
        @SuppressWarnings("unchecked")
        List<Object> rows = q.getResultList();
        List<String> list = new ArrayList<>();
        for (Object o : rows) {
            list.add(String.valueOf(o));
        }
        return list;
    }

    private long toLong(Object o) {
        if (o == null) return 0L;
        if (o instanceof Number n) return n.longValue();
        return Long.parseLong(o.toString());
    }

    private double round(Object o) {
        if (o == null) return 0.0;
        BigDecimal bd = new BigDecimal(o.toString()).setScale(1, RoundingMode.HALF_UP);
        return bd.doubleValue();
    }

    @org.springframework.beans.factory.annotation.Autowired
    private com.sgs.repository.StudentRepository studentRepositoryRef;

    private Long currentStudentId(Long userId) {
        return studentRepositoryRef.findByUserId(userId)
                .orElseThrow(() -> new BusinessException(403, "当前账号未关联学生信息"))
                .getId();
    }
}
