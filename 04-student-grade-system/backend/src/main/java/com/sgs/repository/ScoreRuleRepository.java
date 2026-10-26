package com.sgs.repository;

import com.sgs.entity.ScoreRule;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ScoreRuleRepository extends JpaRepository<ScoreRule, Long> {

    Optional<ScoreRule> findByCourseId(Long courseId);
}
