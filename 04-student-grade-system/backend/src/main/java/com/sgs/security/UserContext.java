package com.sgs.security;

/**
 * 登录用户上下文持有者
 */
public final class UserContext {

    private static final ThreadLocal<LoginUser> HOLDER = new ThreadLocal<>();

    private UserContext() {
    }

    public static void set(LoginUser user) {
        HOLDER.set(user);
    }

    public static LoginUser get() {
        return HOLDER.get();
    }

    public static LoginUser require() {
        LoginUser u = HOLDER.get();
        if (u == null) {
            throw new com.sgs.common.BusinessException(401, "未登录或登录已过期");
        }
        return u;
    }

    public static void clear() {
        HOLDER.remove();
    }
}
