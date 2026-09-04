# 0282 hp 三层:对账保旧 + 决策沿用真值 + 记录分字段

- 状态: accepted
- 日期: 2026-08-24
- 来源: 用户设计(2026-08-23 17:2x,进度树「hp 读不到三层规格」节,run165501 P2r1 hp=100 毒化第三次踩响的根治)

## 背景

HP 只在备战屏 **shop 关闭态**显示于右上角(2026-08-03 多样本确认);shop
开态该区物理为空 → `read_hp_opt` 返 None。旧链(read_game_state):

```
read_hp_opt → None → state.hp = 100 兜底(健康先验,决策层安全设计)
                       └ 遥测把 100 当真值记(hp_readable 位虽在,值仍毒)
```

- run165501 P2r1 实锤:真值 hp2 被记成 100,用户连环质疑;
- insights 2026-08-15(M19「P1 零损」误读)已记同病且修了 `read_hp_opt`
  保真版,**但只加保真版没改值语义 = 修复留一半**(第三次踩响);
- gold 侧同类信息只有 prep_director 的「gold 不可信」日志,遥测无字段。

## 决策(用户三层设计,原话要点)

1. **对账层(读不到=保旧)**:hp 进对账域——新读 None(shop 开态物理为空)
   ≠ 前值,**不是漂移是读失败,保旧不写**(复用 `reconcile_tracking` 双空读
   守卫思想)。新增 `cw_reconcile.reconcile_hp`:真值帧(非 None)才写
   `session.last_hp_real`(=「session 更新只在关态真值帧」,shop 开态读不到
   自然不写);新读非 None 且同域大幅上行(HP 只降不升,上行 ≥
   `HP_REAL_JUMP_CONFLICT`=30)→ `obs_conflict` 留证(仍采新:真值帧是
   物理读数,判读侧消费证据)。
2. **决策层沿用真值**:读不到 → 用 `session.last_hp_real`(hp2 比假 100
   安全,低血先验触发保血方向对);**全无真值(开局)才兜底 100**。
   `read_game_state` 的 hp 块整体改走 `reconcile_hp`(写入端本就用
   `read_hp_opt`,r319;本次改的是值语义与对账接线)。
3. **记录层如实**:`state.hp`=决策用值(真值或沿用值),`state.hp_readable`
   =是否真读(False=读不到)——「读不到」与「决策用值」分字段,不把
   兜底/沿用混进「真 100」。gold 同款:DecisionTrace 补 `gold_readable`
   字段(prep_director「gold 不可信」日志升级为字段),recorder 对拍语料
   同步带 hp/gold 双保真位。

## Considered Options

- **A. 遥测侧只在判读时过滤 hp_readable=False**:拒绝——值本身仍是假 100,
  任何不带位过滤的下游消费(对拍/聚合/未来视图)都会毒化;且决策层同帧仍
  吃假 100(保血方向错),这是 read_hp 2026-08-03 设计的安全缺口;
- **B. 读不到时 hp 记 None**:拒绝——GameState.hp 是 int 契约,gated_hp/
  pivot/plan 大量消费;把契约改 Optional 波及面大且决策层仍需一个值,把
  「给决策什么值」的裁决藏进各消费端 = 双源;
- **C. 三层分字段(选定)**——对账层单一裁决点(reconcile_hp 返回
  (决策用值, 是否真读)),决策/记录消费同源;沿用值本身是真值,比兜底
  100 更安全也更诚实;
- **D. 跳变守卫也保旧(上行 ≥30 时拒新读)**:拒绝——上行帧仍是物理真读
  (OCR 帧在),保旧会把偶发真值锁死;「HP 只降不升」是结算语义先验,留证
  交判读侧定夺(与 streak 双源留证同模式)。

## 影响

- `cw_reconcile.py`:`reconcile_hp` + `HP_REAL_JUMP_CONFLICT`(新对账域入口);
- `cw_strategy.py`:StrategySession 增 `last_hp_real`(备战现读域对账锚;
  与 `last_hp` 结算屏真值/gated_hp 新鲜度门分工并存);
- `cw_observation.py`:read_game_state hp 块改走 reconcile_hp;
- `cw_telemetry.py` / `cw_match_recorder.py`:gold_readable 字段 + 注释更新;
- `cw_state.py`:hp/hp_readable 注释语义更新(字段类型不变,schema 兼容);
- 测试:`test_cw_adr0282_0283.py`(①读不到保旧不写兜底 ②沿用真值
  ③跳变留证 ④开局兜底 100 ⑤见 ADR-0283)。
