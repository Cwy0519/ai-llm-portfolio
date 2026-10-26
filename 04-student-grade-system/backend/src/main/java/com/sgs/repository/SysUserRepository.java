package com.sgs.repository;

import com.sgs.entity.SysUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface SysUserRepository extends JpaRepository<SysUser, Long> {

    Optional<SysUser> findByUsername(String username);

    boolean existsByUsername(String username);

    /** 查询用户拥有的角色编码 */
    @Query(value = "SELECT r.role_code FROM sys_user_role ur " +
            "JOIN sys_role r ON r.id = ur.role_id WHERE ur.user_id = :userId", nativeQuery = true)
    List<String> findRoleCodesByUserId(@Param("userId") Long userId);

    /** 查询用户拥有的权限编码（通过角色继承） */
    @Query(value = "SELECT DISTINCT p.perm_code FROM sys_user_role ur " +
            "JOIN sys_role_permission rp ON rp.role_id = ur.role_id " +
            "JOIN sys_permission p ON p.id = rp.perm_id " +
            "WHERE ur.user_id = :userId", nativeQuery = true)
    List<String> findPermCodesByUserId(@Param("userId") Long userId);
}
