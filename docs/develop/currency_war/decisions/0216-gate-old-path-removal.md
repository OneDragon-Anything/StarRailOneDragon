# 0216 观测 gate 旧路径删除(对拍期结束)

## Status

accepted(2026-08-22;用户定调「几个节点没问题后,可以删掉旧的代码」)

## Context

ADR-0213 观测层重构(4 批次,r297-r336)引入 `wait_stable_frame` 稳定门原语,以 4 个
yml-only 调试 flag(`gate_director`/`gate_shop_close`/`gate_shop_open`/`gate_hook`)逐机制
接线,flag off 保留旧路径活分支,对拍期切 on 验证。原切 on 判据:对拍 ≥3 局无 [cw!]
新增+无 path 混布。

实机对拍(局37/局38)暴露三个 gate bug 形态并修复:

- **#4 poll 成本模型错位(r344b)**:全图 OCR(crop_first=False,OCR 缓存复用口径,用户定调)
  ~5s/轮 > 旧 timeout 4.5s → 稳定窗结构性饿死(diag {'screen':0,'fp':1,'ok':0})。
  修:timeout 12s(≥2 轮 poll)+ grace poll + gate 末帧透传 `_observe`(OCR 缓存贯穿);
- **#5 shop buy 条件分支内局部 import 遮蔽(r345)+ #5b contextlib 同型(review H1,r346)**:
  UnboundLocalError,默认配置即活。修:模块级 import;
- **r2 停机根因(r346)**:战斗胜利后新回合备战进入时商店可能开着(游戏行为,合法稳定态),
  gate 只认关态 → 3-strike ping-pong 停机。修:超时分支先探开商店态(收起+round_retry
  重进),真特效/overlay 才 bail。

修复后局38 续跑 r1-r3 三个节点新路径全部干净:path=old 恒 0(6 次 path=new),无新增
[cw!] 失败类别(obs 留证类为重启重建噪声),买牌/部署/装备/出战全链无崩溃。

## Decision Drivers

1. 双路径维护成本:每个 gate 站点保留 flag 分支+旧路径,回归面翻倍;
2. 对拍证据已足:3 节点干净 + path 混布为 0,剩余节点类型(遭遇/boss)的 gate 行为
   与已验证站点同构(同原语同 profile);
3. 用户定调降低门槛:「几个节点没问题后即可删」,不必等满 3 局。

## Considered Options

- **A. 等满 3 局再删**:证据更厚,但每局 20-40min 且双路径维护持续;用户已定调降低门槛 → 弃。
- **B. flag 保留但默认 on**:零删除风险,但死配置复活面(GUI 静默抹值前科)+组合爆炸
  (每站点×2 路径)永续 → 弃。
- **C. 删除 flag+旧路径,gate 无条件化(选定)**:离线契约(截图异常→放行)与超时语义
  (fail-closed retry/bail/skip)逐站点保留;删除范围=config 字段+save 白名单+yml+
  7 处 src 消费点(prep_director×2/shop×3/prep_actions×1)+旧探针/旧轮询代码。

## Decision

选 C。逐站点语义:

| 站点 | gate 行为(唯一路径) | 超时 | 异常(离线契约) |
|---|---|---|---|
| director 环入口 | PROFILE_CLOSED 稳定窗,末帧透传 `_observe` | 开商店态容忍(收起重进)→ 真特效 bail(3-strike) | 放行(observe 自截图) |
| shop 买前收起 | PROFILE_CLOSED,稳定帧复用(M1) | fail-closed retry | 放行 |
| shop 开店 | PROFILE_OPEN | 放行(suppress;**刻意分层**:开店站超时已等满稳定窗,后续读在买循环内自带重试消化半开帧——与买前收起的 fail-closed 差异是设计非回归) | 放行 |
| shop 买后收起 | PROFILE_CLOSED | 放行(suppress) | 放行 |
| ensure_shop 双向 | 开/关 profile | 返回 False(机制恢复) | 旧单次验证 |
| 钩子前置 | PROFILE_CLOSED | 跳过 reward 采集 | 放行 |

已知观察项(r347 review M-1):环入口 collapse 容忍路径不经 `_bail`
3-strike 计数——有界(retry 上限 6 次/节点,耗尽走 director fail
streak ≥5 兜底),但收起点击失败时以无特征 generic fail 收场;实机
观察 `[cw] 环入口开商店态` 频率,频繁则落修法(click 失败返 False
走 bail 留证)。

回归锁:flag 不得回流(test_cw_gate_flags)/`_legacy_poll` 不得回流+fail-closed 语义
(test_cw_r336_batch4_locks)/旧探针锚不得回流+gate 必须在(test_cw_r297_p0_fixes)。

关联:r346 开商店容忍(局38 r2)、r345/#5b import 雷、r344b 成本模型(局37)。
