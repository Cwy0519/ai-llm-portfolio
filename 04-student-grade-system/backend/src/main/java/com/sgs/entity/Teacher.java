package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

/** 教师信息 */
@Data
@Entity
@Table(name = "info_teacher")
public class Teacher {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false, unique = true)
    private Long userId;

    @Column(name = "teacher_no", nullable = false, unique = true, length = 30)
    private String teacherNo;

    @Column(name = "college_id")
    private Long collegeId;

    @Column(length = 50)
    private String title;
}
