package com.sgs.repository;

import com.sgs.entity.ScoreLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ScoreLogRepository extends JpaRepository<ScoreLog, Long> {

    List<ScoreLog> findByScoreIdOrderByOperateTimeDesc(Long scoreId);

    List<ScoreLog> findTop100ByOrderByOperateTimeDesc();
}
