package com.sgs.entity;

import jakarta.persistence.*;
import lombok.Data;

/** 权限 */
@Data
@Entity
@Table(name = "sys_permission")
public class SysPermission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "perm_code", nullable = false, unique = true, length = 60)
    private String permCode;

    @Column(name = "perm_name", nullable = false, length = 50)
    private String permName;

    @Column(name = "perm_type", length = 20)
    private String permType;

    @Column(name = "parent_id")
    private Long parentId;
}
