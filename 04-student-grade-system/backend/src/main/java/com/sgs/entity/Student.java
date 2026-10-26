package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;

/** 学生信息 */
@Data
@Entity
@Table(name = "info_student")
public class Student {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true)
    private Long userId;

    @Column(name = "stu_no", nullable = false, unique = true, length = 30)
    private String stuNo;

    @Column(name = "class_id", nullable = false)
    private Long classId;

    @Column(name = "enroll_year")
    private Integer enrollYear;
}
