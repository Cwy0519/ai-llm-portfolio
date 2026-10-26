package com.sgs.repository;

import com.sgs.entity.Score;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface ScoreRepository extends JpaRepository<Score, Long> {

    Optional<Score> findByStudentIdAndCourseIdAndSemester(Long studentId, Long courseId, String semester);

    List<Score> findByStudentId(Long studentId);

    List<Score> findByCourseIdAndSemester(Long courseId, String semester);

    List<Score> findBySemester(String semester);

    /** 成绩明细（带学生、班级、课程名称）——用于列表与统计 */
    @Query(value = "SELECT s.id AS scoreId, st.id AS studentId, st.stu_no AS stuNo, u.real_name AS studentName, " +
            "c.class_name AS className, co.id AS courseId, co.course_name AS courseName, co.credit AS credit, " +
            "s.semester AS semester, s.usual_score AS usualScore, s.midterm_score AS midtermScore, " +
            "s.final_score AS finalScore, s.total_score AS totalScore, s.grade_point AS gradePoint " +
            "FROM score s " +
            "JOIN info_student st ON st.id = s.student_id " +
            "JOIN sys_user u ON u.id = st.user_id " +
            "JOIN base_class c ON c.id = st.class_id " +
            "JOIN course co ON co.id = s.course_id " +
            "WHERE (:semester IS NULL OR s.semester = :semester) " +
            "ORDER BY co.course_name, st.stu_no", nativeQuery = true)
    List<Object[]> findScoreDetail(@Param("semester") String semester);

    /** 单学生成绩明细 */
    @Query(value = "SELECT s.id AS scoreId, st.id AS studentId, st.stu_no AS stuNo, u.real_name AS studentName, " +
            "c.class_name AS className, co.id AS courseId, co.course_name AS courseName, co.credit AS credit, " +
            "s.semester AS semester, s.usual_score AS usualScore, s.midterm_score AS midtermScore, " +
            "s.final_score AS finalScore, s.total_score AS totalScore, s.grade_point AS gradePoint " +
            "FROM score s " +
            "JOIN info_student st ON st.id = s.student_id " +
            "JOIN sys_user u ON u.id = st.user_id " +
            "JOIN base_class c ON c.id = st.class_id " +
            "JOIN course co ON co.id = s.course_id " +
            "WHERE s.student_id = :studentId " +
            "ORDER BY s.semester DESC, co.course_name", nativeQuery = true)
    List<Object[]> findScoreDetailByStudent(@Param("studentId") Long studentId);
}
