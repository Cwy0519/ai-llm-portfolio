package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

/** 成绩修改审计日志 */
@Data
@Entity
@Table(name = "score_log")
public class ScoreLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "score_id", nullable = false)
    private Long scoreId;

    @Column(name = "operator_id", nullable = false)
    private Long operatorId;

    @Column(nullable = false, length = 20)
    private String action;

    @Column(name = "old_value", length = 200)
    private String oldValue;

    @Column(name = "new_value", length = 200)
    private String newValue;

    @Column(name = "operate_time")
    private LocalDateTime operateTime;
}
