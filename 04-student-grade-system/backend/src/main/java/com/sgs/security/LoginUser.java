package com.sgs.security;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 当前登录用户上下文（基于 ThreadLocal）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginUser {

    private Long userId;
    private String username;
    private String realName;
    private List<String> roles;
    private List<String> permissions;

    public boolean hasPermission(String permCode) {
        return permissions != null && permissions.contains(permCode);
    }

    public boolean hasRole(String roleCode) {
        return roles != null && roles.contains(roleCode);
    }
}
