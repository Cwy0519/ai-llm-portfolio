package com.sgs.controller;

import com.sgs.common.Result;
import com.sgs.dto.LoginRequest;
import com.sgs.dto.LoginResponse;
import com.sgs.security.LoginUser;
import com.sgs.security.TokenManager;
import com.sgs.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 认证接口 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final TokenManager tokenManager;

    /** 登录 */
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest req) {
        return Result.ok(authService.login(req));
    }

    /** 退出登录 */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader(value = "Authorization", required = false) String auth) {
        if (auth != null && auth.startsWith("Bearer ")) {
            tokenManager.remove(auth.substring(7));
        }
        authService.logout();
        return Result.ok();
    }

    /** 获取当前登录用户信息 */
    @GetMapping("/me")
    public Result<LoginUser> me() {
        return Result.ok(authService.currentUser());
    }

    /** 修改密码 */
    @PostMapping("/change-password")
    public Result<Void> changePassword(@RequestBody Map<String, String> body) {
        authService.changePassword(body.get("oldPassword"), body.get("newPassword"));
        return Result.ok();
    }
}
