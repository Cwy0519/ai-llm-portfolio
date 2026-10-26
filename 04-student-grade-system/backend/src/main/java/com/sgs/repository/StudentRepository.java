package com.sgs.repository;

import com.sgs.entity.Student;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface StudentRepository extends JpaRepository<Student, Long> {

    Optional<Student> findByUserId(Long userId);

    Optional<Student> findByStuNo(String stuNo);

    List<Student> findByClassId(Long classId);

    boolean existsByStuNo(String stuNo);
}
