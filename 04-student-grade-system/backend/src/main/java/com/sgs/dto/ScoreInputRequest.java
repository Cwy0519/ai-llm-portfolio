package com.sgs.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.math.BigDecimal;

/** 成绩录入/修改请求 */
@Data
public class ScoreInputRequest {

    @NotNull(message = "学生ID不能为空")
    private Long studentId;

    @NotNull(message = "课程ID不能为空")
    private Long courseId;

    @NotBlank(message = "学期不能为空")
    private String semester;

    @DecimalMin(value = "0", message = "平时成绩不能小于0")
    @DecimalMax(value = "100", message = "平时成绩不能大于100")
    private BigDecimal usualScore;

    @DecimalMin(value = "0", message = "期中成绩不能小于0")
    @DecimalMax(value = "100", message = "期中成绩不能大于100")
    private BigDecimal midtermScore;

    @DecimalMin(value = "0", message = "期末成绩不能小于0")
    @DecimalMax(value = "100", message = "期末成绩不能大于100")
    private BigDecimal finalScore;
}
