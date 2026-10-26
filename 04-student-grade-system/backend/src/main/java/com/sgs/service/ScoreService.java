package com.sgs.service;

import com.sgs.common.BusinessException;
import com.sgs.dto.ScoreInputRequest;
import com.sgs.entity.Course;
import com.sgs.entity.Score;
import com.sgs.entity.ScoreLog;
import com.sgs.entity.ScoreRule;
import com.sgs.repository.CourseRepository;
import com.sgs.repository.ScoreLogRepository;
import com.sgs.repository.ScoreRepository;
import com.sgs.repository.ScoreRuleRepository;
import com.sgs.security.LoginUser;
import com.sgs.security.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 成绩服务：录入、折算、审计
 *
 * 【折算算法】
 *   总评 = 平时 × w1 + 期中 × w2 + 期末 × w3
 *   权重来自 score_rule 表，可按课程单独配置。
 *   若某分项缺失，按剩余项权重归一化计算（避免缺考导致总评为0）。
 *
 * 【绩点换算】
 *   90-100 → 4.0    85-89 → 3.7   82-84 → 3.3   78-81 → 3.0
 *   75-77  → 2.7    72-74 → 2.3   68-71 → 2.0   64-67 → 1.5
 *   60-63  → 1.0    <60   → 0.0（不及格）
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ScoreService {

    private final ScoreRepository scoreRepository;
    private final ScoreRuleRepository ruleRepository;
    private final ScoreLogRepository logRepository;
    private final CourseRepository courseRepository;

    private static final BigDecimal HUNDRED = new BigDecimal("100");

    /** 成绩明细列表 */
    public List<Map<String, Object>> listDetail(String semester) {
        LoginUser user = UserContext.require();
        List<Object[]> rows;

        // 学生只能看自己的成绩
        if (user.hasRole("STUDENT")) {
            Long studentId = currentStudentId(user.getUserId());
            rows = scoreRepository.findScoreDetailByStudent(studentId);
        } else {
            rows = scoreRepository.findScoreDetail(semester);
        }

        List<Map<String, Object>> list = new ArrayList<>();
        for (Object[] r : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("scoreId", r[0]);
            m.put("studentId", r[1]);
            m.put("stuNo", r[2]);
            m.put("studentName", r[3]);
            m.put("className", r[4]);
            m.put("courseId", r[5]);
            m.put("courseName", r[6]);
            m.put("credit", r[7]);
            m.put("semester", r[8]);
            m.put("usualScore", r[9]);
            m.put("midtermScore", r[10]);
            m.put("finalScore", r[11]);
            m.put("totalScore", r[12]);
            m.put("gradePoint", r[13]);
            list.add(m);
        }
        return list;
    }

    /**
     * 录入或修改成绩（含审计日志）
     */
    @Transactional
    public Map<String, Object> saveScore(ScoreInputRequest req) {
        LoginUser user = UserContext.require();

        if (!user.hasPermission("score:input") && !user.hasPermission("score:edit")) {
            throw new BusinessException(403, "无权限录入成绩");
        }

        Course course = courseRepository.findById(req.getCourseId())
                .orElseThrow(() -> new BusinessException(404, "课程不存在"));

        ScoreRule rule = ruleRepository.findByCourseId(req.getCourseId())
                .orElse(defaultRule());

        var existing = scoreRepository.findByStudentIdAndCourseIdAndSemester(
                req.getStudentId(), req.getCourseId(), req.getSemester());

        Score score = existing.orElseGet(Score::new);
        boolean isNew = existing.isEmpty();

        String oldValue = isNew ? null : describe(score);

        score.setStudentId(req.getStudentId());
        score.setCourseId(req.getCourseId());
        score.setSemester(req.getSemester());
        score.setUsualScore(req.getUsualScore());
        score.setMidtermScore(req.getMidtermScore());
        score.setFinalScore(req.getFinalScore());

        BigDecimal total = calculateTotal(req.getUsualScore(), req.getMidtermScore(),
                req.getFinalScore(), rule);
        score.setTotalScore(total);
        score.setGradePoint(calculateGradePoint(total));
        score.setInputBy(user.getUserId());
        score.setUpdateTime(LocalDateTime.now());
        if (isNew) {
            score.setInputTime(LocalDateTime.now());
        }

        Score saved = scoreRepository.save(score);

        // 写审计日志
        ScoreLog logEntry = new ScoreLog();
        logEntry.setScoreId(saved.getId());
        logEntry.setOperatorId(user.getUserId());
        logEntry.setAction(isNew ? "INSERT" : "UPDATE");
        logEntry.setOldValue(oldValue);
        logEntry.setNewValue(describe(saved));
        logEntry.setOperateTime(LocalDateTime.now());
        logRepository.save(logEntry);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("scoreId", saved.getId());
        result.put("totalScore", saved.getTotalScore());
        result.put("gradePoint", saved.getGradePoint());
        result.put("isNew", isNew);
        log.info("教师 {} {} 成绩：学生={} 课程={} 总评={}",
                user.getUsername(), isNew ? "录入" : "修改",
                req.getStudentId(), course.getCourseName(), total);
        return result;
    }

    /**
     * 成绩折算核心算法
     *
     * 若三个分项都存在：总评 = 各项 × 对应权重
     * 若部分缺失：只对存在的分项按权重归一化
     */
    public BigDecimal calculateTotal(BigDecimal usual, BigDecimal midterm,
                                     BigDecimal fin, ScoreRule rule) {
        BigDecimal w1 = rule.getUsualWeight();
        BigDecimal w2 = rule.getMidtermWeight();
        BigDecimal w3 = rule.getFinalWeight();

        BigDecimal weightedSum = BigDecimal.ZERO;
        BigDecimal weightSum = BigDecimal.ZERO;

        if (usual != null) {
            weightedSum = weightedSum.add(usual.multiply(w1));
            weightSum = weightSum.add(w1);
        }
        if (midterm != null) {
            weightedSum = weightedSum.add(midterm.multiply(w2));
            weightSum = weightSum.add(w2);
        }
        if (fin != null) {
            weightedSum = weightedSum.add(fin.multiply(w3));
            weightSum = weightSum.add(w3);
        }

        if (weightSum.compareTo(BigDecimal.ZERO) == 0) {
            return null;
        }

        return weightedSum.divide(weightSum, 2, RoundingMode.HALF_UP);
    }

    /** 绩点换算 */
    public BigDecimal calculateGradePoint(BigDecimal total) {
        if (total == null) {
            return null;
        }
        double t = total.doubleValue();
        double gp;
        if (t >= 90) gp = 4.0;
        else if (t >= 85) gp = 3.7;
        else if (t >= 82) gp = 3.3;
        else if (t >= 78) gp = 3.0;
        else if (t >= 75) gp = 2.7;
        else if (t >= 72) gp = 2.3;
        else if (t >= 68) gp = 2.0;
        else if (t >= 64) gp = 1.5;
        else if (t >= 60) gp = 1.0;
        else gp = 0.0;
        return BigDecimal.valueOf(gp).setScale(2, RoundingMode.HALF_UP);
    }

    /** 审计日志列表 */
    public List<ScoreLog> listLogs() {
        return logRepository.findTop100ByOrderByOperateTimeDesc();
    }

    private ScoreRule defaultRule() {
        ScoreRule r = new ScoreRule();
        r.setUsualWeight(new BigDecimal("0.30"));
        r.setMidtermWeight(new BigDecimal("0.20"));
        r.setFinalWeight(new BigDecimal("0.50"));
        r.setPassScore(new BigDecimal("60.00"));
        return r;
    }

    private String describe(Score s) {
        return String.format("平时=%s, 期中=%s, 期末=%s, 总评=%s",
                s.getUsualScore(), s.getMidtermScore(),
                s.getFinalScore(), s.getTotalScore());
    }

    private Long currentStudentId(Long userId) {
        return studentRepositoryRef.findByUserId(userId)
                .orElseThrow(() -> new BusinessException(403, "当前账号未关联学生信息"))
                .getId();
    }

    // 避免构造器循环依赖，使用字段注入
    @org.springframework.beans.factory.annotation.Autowired
    private com.sgs.repository.StudentRepository studentRepositoryRef;
}
