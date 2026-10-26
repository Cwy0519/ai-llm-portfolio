package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

/** 班级 */
@Data
@Entity
@Table(name = "base_class")
public class SchoolClass {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "class_name", nullable = false, length = 100)
    private String className;

    @Column(name = "class_code", nullable = false, unique = true, length = 30)
    private String classCode;

    @Column(name = "major_id", nullable = false)
    private Long majorId;

    @Column(name = "grade_year", nullable = false)
    private Integer gradeYear;
}
