package com.sgs;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 学生成绩管理系统 启动类
 *
 * 技术栈：SpringBoot 3 + Spring Data JPA + H2/MySQL
 * 架构：B/S 前后端分离（RESTful API）
 */
@SpringBootApplication
public class StudentGradeSystemApplication {

    public static void main(String[] args) {
        SpringApplication.run(StudentGradeSystemApplication.class, args);
    }
}
