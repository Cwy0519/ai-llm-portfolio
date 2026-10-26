package com.sgs.service;

import com.sgs.common.BusinessException;
import com.sgs.dto.LoginRequest;
import com.sgs.dto.LoginResponse;
import com.sgs.entity.SysUser;
import com.sgs.repository.SysUserRepository;
import com.sgs.security.LoginUser;
import com.sgs.security.TokenManager;
import com.sgs.security.UserContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 认证服务：登录、登出、当前用户信息
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final SysUserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final TokenManager tokenManager;

    public LoginResponse login(LoginRequest req) {
        SysUser user = userRepository.findByUsername(req.getUsername())
                .orElseThrow(() -> new BusinessException(401, "用户名或密码错误"));

        if (user.getStatus() == null || user.getStatus() != 1) {
            throw new BusinessException(403, "该账号已被禁用，请联系管理员");
        }

        if (!passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            throw new BusinessException(401, "用户名或密码错误");
        }

        List<String> roles = userRepository.findRoleCodesByUserId(user.getId());
        List<String> perms = userRepository.findPermCodesByUserId(user.getId());

        LoginUser loginUser = new LoginUser(user.getId(), user.getUsername(),
                user.getRealName(), roles, perms);

        String token = tokenManager.createToken(loginUser);
        log.info("用户 {} 登录成功，角色={}", user.getUsername(), roles);

        return new LoginResponse(token, user.getId(), user.getUsername(),
                user.getRealName(), roles, perms);
    }

    public void logout() {
        // 令牌由控制器清除，此处仅记录
        LoginUser u = UserContext.get();
        if (u != null) {
            log.info("用户 {} 退出登录", u.getUsername());
        }
    }

    public LoginUser currentUser() {
        return UserContext.require();
    }

    /** 修改密码 */
    public void changePassword(String oldPassword, String newPassword) {
        LoginUser current = UserContext.require();
        SysUser user = userRepository.findById(current.getUserId())
                .orElseThrow(() -> new BusinessException(404, "用户不存在"));

        if (!passwordEncoder.matches(oldPassword, user.getPassword())) {
            throw new BusinessException(400, "原密码不正确");
        }
        if (newPassword == null || newPassword.length() < 6) {
            throw new BusinessException(400, "新密码长度不能少于6位");
        }

        user.setPassword(passwordEncoder.encode(newPassword));
        user.setUpdateTime(LocalDateTime.now());
        userRepository.save(user);
        log.info("用户 {} 修改密码成功", user.getUsername());
    }
}
