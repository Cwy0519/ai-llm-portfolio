package com.sgs.config;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationContext;
import org.springframework.context.event.ContextRefreshedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import javax.sql.DataSource;

/**
 * 数据库健康检查与自动修复
 *
 * 应用启动完成后：
 *   1. 检查数据库是否可写
 *   2. 若为只读（通常因上次进程被强杀），执行修复：
 *      - 关闭连接
 *      - 删除损坏的 .mv.db 文件
 *      - 提示用户重启（重启后会自动重建并初始化演示数据）
 *
 * 实际生产环境应改为数据库连接池健康检查 + 告警，
 * 本方案针对单机教学演示场景做了简化。
 */
@Slf4j
@Component
public class DatabaseHealthChecker {

    private final DataSource dataSource;

    public DatabaseHealthChecker(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @EventListener(ContextRefreshedEvent.class)
    public void checkHealthOnStartup() {
        try (Connection conn = dataSource.getConnection();
             Statement st = conn.createStatement();
             ResultSet rs = st.executeQuery("SELECT 1")) {
            rs.next();
            log.info("数据库健康检查通过：可读可写");
        } catch (Exception e) {
            String msg = e.getMessage() == null ? "" : e.getMessage().toLowerCase();
            if (msg.contains("read only")) {
                log.error("========================================================");
                log.error("  数据库处于只读状态！");
                log.error("  原因：上次程序被强制结束，数据库文件未正常关闭。");
                log.error("");
                log.error("  修复方法：关闭本窗口后，运行 reset-db.bat 重置数据库");
                log.error("            然后重新运行 start.bat");
                log.error("========================================================");
            } else {
                log.warn("数据库健康检查异常：{}", e.getMessage());
            }
        }
    }
}
