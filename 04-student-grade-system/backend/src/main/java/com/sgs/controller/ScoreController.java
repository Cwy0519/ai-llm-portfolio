package com.sgs.controller;

import com.sgs.common.Result;
import com.sgs.dto.ScoreInputRequest;
import com.sgs.entity.ScoreLog;
import com.sgs.service.ScoreService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 成绩管理接口 */
@RestController
@RequestMapping("/api/scores")
@RequiredArgsConstructor
public class ScoreController {

    private final ScoreService scoreService;

    /** 成绩明细列表 */
    @GetMapping
    public Result<List<Map<String, Object>>> list(
            @RequestParam(required = false) String semester) {
        return Result.ok(scoreService.listDetail(semester));
    }

    /** 录入/修改成绩 */
    @PostMapping
    public Result<Map<String, Object>> save(@Valid @RequestBody ScoreInputRequest req) {
        return Result.ok(scoreService.saveScore(req));
    }

    /** 审计日志 */
    @GetMapping("/logs")
    public Result<List<ScoreLog>> logs() {
        return Result.ok(scoreService.listLogs());
    }
}
