package com.sgs.controller;

import com.sgs.common.Result;
import com.sgs.entity.Course;
import com.sgs.service.BasicInfoService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 基础信息管理接口：学生 / 教师 / 课程 / 班级 */
@RestController
@RequestMapping("/api/basic")
@RequiredArgsConstructor
public class BasicInfoController {

    private final BasicInfoService basicInfoService;

    // ---------- 学生 ----------
    @GetMapping("/students")
    public Result<List<Map<String, Object>>> students() {
        return Result.ok(basicInfoService.listStudents());
    }

    @PostMapping("/students")
    public Result<Long> addStudent(@RequestBody Map<String, Object> body) {
        return Result.ok(basicInfoService.addStudent(body));
    }

    @DeleteMapping("/students/{id}")
    public Result<Void> deleteStudent(@PathVariable Long id) {
        basicInfoService.deleteStudent(id);
        return Result.ok();
    }

    // ---------- 教师 ----------
    @GetMapping("/teachers")
    public Result<List<Map<String, Object>>> teachers() {
        return Result.ok(basicInfoService.listTeachers());
    }

    @PostMapping("/teachers")
    public Result<Long> addTeacher(@RequestBody Map<String, Object> body) {
        return Result.ok(basicInfoService.addTeacher(body));
    }

    // ---------- 课程 ----------
    @GetMapping("/courses")
    public Result<List<Course>> courses() {
        return Result.ok(basicInfoService.listCourses());
    }

    @PostMapping("/courses")
    public Result<Course> addCourse(@RequestBody Map<String, Object> body) {
        return Result.ok(basicInfoService.addCourse(body));
    }

    @DeleteMapping("/courses/{id}")
    public Result<Void> deleteCourse(@PathVariable Long id) {
        basicInfoService.deleteCourse(id);
        return Result.ok();
    }

    // ---------- 班级 ----------
    @GetMapping("/classes")
    public Result<List<Map<String, Object>>> classes() {
        return Result.ok(basicInfoService.listClasses());
    }
}
