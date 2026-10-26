package com.sgs.security;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 简易令牌管理器（内存实现）
 *
 * 说明：本系统为教学演示项目，采用服务端内存令牌，
 * 相比 JWT 更直观、便于在论文中讲解会话管理。
 * 生产环境可替换为 Redis 集中式存储。
 */
@Slf4j
@Component
public class TokenManager {

    private final Map<String, TokenInfo> tokenStore = new ConcurrentHashMap<>();

    @Value("${sgs.token-expire-minutes:120}")
    private long expireMinutes;

    public String createToken(LoginUser user) {
        String token = UUID.randomUUID().toString().replace("-", "");
        tokenStore.put(token, new TokenInfo(user, System.currentTimeMillis() + expireMinutes * 60_000));
        log.debug("为用户 {} 创建令牌 {}", user.getUsername(), token);
        return token;
    }

    public LoginUser getLoginUser(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        TokenInfo info = tokenStore.get(token);
        if (info == null) {
            return null;
        }
        if (info.expireAt < System.currentTimeMillis()) {
            tokenStore.remove(token);
            return null;
        }
        return info.user;
    }

    public void remove(String token) {
        if (token != null) {
            tokenStore.remove(token);
        }
    }

    public void refresh(LoginUser user) {
        tokenStore.forEach((k, v) -> {
            if (v.user.getUserId().equals(user.getUserId())) {
                v.user = user;
            }
        });
    }

    private static class TokenInfo {
        private LoginUser user;
        private final long expireAt;

        TokenInfo(LoginUser user, long expireAt) {
            this.user = user;
            this.expireAt = expireAt;
        }
    }
}
