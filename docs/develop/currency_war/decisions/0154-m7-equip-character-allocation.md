# 0154 · M7 装备角色级分配(carry 定向穿戴 + 后排支持)

- **Status**: Accepted(2026-08-16;后排 drag 坐标外推待 live 验,验穿失败自动停该件不炸)
- **Context**: M29-M32 死因收敛到板质量上限:五对 tier-1 + 1星 + 装备分配粗糙。plaza 648 篇 51%
  谈装备且全部**角色特定**(「三月一鞋一风扇/花火杨叔回能/姬子双风暴」「那刻夏全套>生存>辅助,
  一定按这个顺序」);旧 EquipAll 只往**前排空槽**塞(ADR-0101 仅 key_equips 优先排序,无角色
  语义,后排恒裸装)。
- **Decision Drivers**: 方法论 M7(装备是角色特定的+有序);伤害天花板是 P2-4 墙的主因之一。
- **Considered Options**:
  - A. 只改排序(现状加强)—— 否:后排永远拿不到装备,carry(姬子/万敌多为前排)之外的
    辅助(花火/瓦尔特回能件)无语义。
  - B. 每角色装备偏好表(per-char key_equips)—— 数据量爆炸,plaza carry_equips 只有 carry 维度。
  - C. **comp 驱动两级分配(选中)**:key_equips 给 carry(按序)→ 其余场上 core → 剩余通用件
    按场上顺序兜底(前排先,受击/反甲类前排生效)。
- **Decision**:
  1. `equip_allocation(comp, deployed, owned, occupied)`(cw_comps,纯函数):容量 EQUIP_CAPACITY=3
     (D-49 布局约束),occupied[(row,slot)] 扣减;comp=None 全走通用兜底。
  2. EquipAll v2:SIFT 身份(`read_deployed_chars`)+ 两排已穿(`read_row_equipped` 前排4/后排
     screen_info 全量)→ 逐件 drag 到**该角色 avatar**。前排用实测常量(D-36/D-41);后排从
     screen_info rect 推导(drag_y=rect.y1+21 前排 329→350 校准外推;verify_y=rect.y2+14 与
     avatar_to_below 同式,前排 467→481≈479 互证)。
  3. 失败安全:验穿失败 retry 一次仍败 → 停该件(不炸流程);身份读失败(deployed 空)→ 整体
     退回旧 front-only 流程(offline fixture 兼容)。
  4. owned 列 reflow:每件重读 read_equips(原有模式),分配按当前 owned 重算(幂等)。
- **影响面**:equip_all.py(M7 主路径+fallback)/cw_comps.py(equip_allocation);测试 +2 守卫
  (carry 按序/容量与兜底)。live 验证判据:M33+ 日志 `M7 drag <装备> → <角色名>` 出现且
  carry 集齐 key_equips ≥2 件;P2-4 总伤进一步提升。
