package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;

/** 成绩折算规则 */
@Data
@Entity
@Table(name = "score_rule")
public class ScoreRule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "course_id", nullable = false, unique = true)
    private Long courseId;

    @Column(name = "usual_weight", nullable = false, precision = 4, scale = 2)
    private BigDecimal usualWeight;

    @Column(name = "midterm_weight", nullable = false, precision = 4, scale = 2)
    private BigDecimal midtermWeight;

    @Column(name = "final_weight", nullable = false, precision = 4, scale = 2)
    private BigDecimal finalWeight;

    @Column(name = "pass_score", nullable = false, precision = 5, scale = 2)
    private BigDecimal passScore;
}
