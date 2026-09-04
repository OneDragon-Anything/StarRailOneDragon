# ADR-0505: 入场清场清单单一源化与星徽秘典/补给改道

## 背景

入场清场（entry overlay 关闭）原为 prep_director 内手写 5 条 dict（W923 overlay 重设计评估件定为 A 面清场项:2 处真实行为变化+需断言门）。清场清单与 registry 的 overlay 定义双源漂移:registry 已知画面(星徽秘典/补给)被清场循环当作通用遮挡关闭,与其既定消费通道冲突。

## Considered Options

1. **prep_director 直遍历 registry 全量派生**(W923 原形态):消费循环侵入面大,prep_director 撤回缓存批(W929)后该文件需稳定,且完全体迁移需授权批——否决(暂)。
2. **observation_gate 桥接派生**(选定):`cw_observation_gate.ENTRY_OVERLAY_CLOSE` 手写 5 条改为消费 `derive_clearable()` 注册表派生,prep_director 消费循环一字不动;清场语义单一源=registry,桥接层只保留接线。
3. 保持手写清单+注释对齐:双源漂移根因不除——否决。

## Decision

- 清场集派生自 `derive_clearable()`(3 条:武装箱/积分奖励/中断挑战)。
- **两处行为变化(缺陷语义,W923 §二.2 设计定案意图,免开关,挂断言门)**:
  - 星徽秘典移出清场集 → 走 0i 选卡通道消化(清场循环误关会丢失选卡机会);
  - 补给移出清场集 → 走 bail→RunSupplyNode 通道(RunSupplyNode._in_node 标识已预核覆盖非节点期弹出形态)。
- 断言门:test_cw_overlay_registry 派生黄金+接线锁+退出路径存在性锁;w609 `_INTERACTIVE_OVERLAYS` 排除列 +2 防回流。

## Consequences

- 清场语义与 registry 单一源对齐;新增 overlay 画面只需 registry 登记,清场自动跟随。
- 星徽秘典/补给在场时的环入口日志断言归实机窗口验证(挂账)。
- prep_director 直遍历完全体迁移与 C 面切换互斥依赖 battle_loop 0i 手写分支(星徽秘典消化闭环依赖),未授权前不动。
