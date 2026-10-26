package com.sgs.config;

import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.Statement;

/**
 * 数据库关闭守卫
 *
 * 确保应用退出前正确关闭 H2 连接池，使数据库文件正常落盘。
 * 若进程被强制结束（任务管理器、强杀），H2 可能将数据库文件标记为只读。
 * 本类配合 DB_CLOSE_ON_EXIT=FALSE 使用，降低该风险。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DatabaseShutdownGuard {

    private final DataSource dataSource;

    @PreDestroy
    public void shutdown() {
        try (Connection conn = dataSource.getConnection();
             Statement st = conn.createStatement()) {
            // 主动执行检查点，将内存中的变更刷入磁盘
            st.execute("CHECKPOINT SYNC");
            log.info("数据库检查点完成，数据已安全落盘");
        } catch (Exception e) {
            log.warn("数据库关闭检查点失败（不影响数据完整性）：{}", e.getMessage());
        }
    }
}
