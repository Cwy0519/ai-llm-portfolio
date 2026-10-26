package com.sgs.config;

import com.sgs.entity.Score;
import com.sgs.repository.ScoreRepository;
import com.sgs.service.ScoreService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 数据一致性校验器
 *
 * 启动时按统一算法重新计算全部绩点，确保
 * 初始化脚本中的绩点与程序算法完全一致。
 * 这样也避免"手工录入的种子数据"与"程序计算"两套逻辑打架。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DataIntegrityInitializer {

    private final ScoreRepository scoreRepository;
    private final ScoreService scoreService;

    @PostConstruct
    public void recalculateGradePoints() {
        try {
            List<Score> all = scoreRepository.findAll();
            int fixed = 0;

            for (Score s : all) {
                var expected = scoreService.calculateGradePoint(s.getTotalScore());
                if (expected != null && (s.getGradePoint() == null
                        || s.getGradePoint().compareTo(expected) != 0)) {
                    s.setGradePoint(expected);
                    scoreRepository.save(s);
                    fixed++;
                }
            }

            if (fixed > 0) {
                log.info("数据一致性校验：修正 {} 条成绩的绩点", fixed);
            } else {
                log.info("数据一致性校验：绩点全部正确（共 {} 条）", all.size());
            }
        } catch (Exception e) {
            // 校验失败不应阻断启动
            log.warn("数据一致性校验跳过：{}", e.getMessage());
        }
    }
}
