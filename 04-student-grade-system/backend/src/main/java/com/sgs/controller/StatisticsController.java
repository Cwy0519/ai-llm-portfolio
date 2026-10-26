package com.sgs.controller;

import com.sgs.common.Result;
import com.sgs.service.StatisticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 统计分析接口（供 ECharts 调用） */
@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatisticsController {

    private final StatisticsService statisticsService;

    /** 成绩分布 */
    @GetMapping("/distribution")
    public Result<Map<String, Object>> distribution(
            @RequestParam(required = false) String semester) {
        return Result.ok(statisticsService.scoreDistribution(semester));
    }

    /** 课程平均分 */
    @GetMapping("/course-average")
    public Result<Map<String, Object>> courseAverage(
            @RequestParam(required = false) String semester) {
        return Result.ok(statisticsService.courseAverage(semester));
    }

    /** 班级平均分 */
    @GetMapping("/class-average")
    public Result<Map<String, Object>> classAverage(
            @RequestParam(required = false) String semester) {
        return Result.ok(statisticsService.classAverage(semester));
    }

    /** 及格率 */
    @GetMapping("/pass-rate")
    public Result<Map<String, Object>> passRate(
            @RequestParam(required = false) String semester) {
        return Result.ok(statisticsService.passRate(semester));
    }

    /** 学生成绩趋势 */
    @GetMapping("/student-trend/{studentId}")
    public Result<Map<String, Object>> studentTrend(@PathVariable Long studentId) {
        return Result.ok(statisticsService.studentTrend(studentId));
    }

    /** 学期列表 */
    @GetMapping("/semesters")
    public Result<List<String>> semesters() {
        return Result.ok(statisticsService.listSemesters());
    }
}
