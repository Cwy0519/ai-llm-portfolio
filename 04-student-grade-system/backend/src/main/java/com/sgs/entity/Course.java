package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;

/** 课程 */
@Data
@Entity
@Table(name = "course")
public class Course {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "course_code", nullable = false, unique = true, length = 30)
    private String courseCode;

    @Column(name = "course_name", nullable = false, length = 100)
    private String courseName;

    @Column(nullable = false, precision = 3, scale = 1)
    private BigDecimal credit;

    @Column(name = "course_type")
    private Integer courseType;

    private Integer status;
}
