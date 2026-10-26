package com.sgs.repository;

import com.sgs.entity.Teacher;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface TeacherRepository extends JpaRepository<Teacher, Long> {

    Optional<Teacher> findByUserId(Long userId);

    Optional<Teacher> findByTeacherNo(String teacherNo);

    boolean existsByTeacherNo(String teacherNo);
}
