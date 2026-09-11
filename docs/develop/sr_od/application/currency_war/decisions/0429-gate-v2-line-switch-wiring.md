# ADR-0429:C4 存活轮数门接入 v2 换线通道

> **版本界碑(2026-09-04 ADR 存量 review;对象属 decision_v2 栈或旧策略代,现行权威 = strategy-docs/flow/proofs + dd-NNN 系)**:本 ADR 裁决的对象已亡——decision/ 整包(含 decision_v2 各模块)已随 b94e9cfb(dd-038)删除,现行唯一策略载体 = mandate_v1(kernel 吸收下沉判据)。本件仅存史料价值(记录设计 why/翻案史);**文内一切「后续应做 X/须换成 Y」类前瞻指令一律视为已亡,勿执行**。

## 状态

accepted(默认关;开臂归重测批裁决)

## 背景

W375 落码的 C4 换线存活轮数门(`cw_line_switch.survival_gate`,registry
`line_switch_survival_gate_enabled`,默认关)唯一消费点在
`strategies/default_strategy.py` 的 `update_target` 换线路径。W376 开臂
A/B 实证(读码+实验双证实):生产策略栈 `DecisionV2Strategy` 完整覆写
`update_target`(意向状态机,不调 super)→ 门在生产栈(sim 默认与
`strategy_id=decision_v2`)无行为通道——off 与 C4-only 两臂 300 局逐位
相等,C4 开关是无意义旋钮(W375 接线遗漏)。

v2 栈的换线决策实际位置:`cw_intention.update_intention` 意向状态机——
撤销出口①(核心 N 轮不可得)/②(更高层信号)把锁定线降级为弱意向
(`phase='weak'`,`weak_comp` 记原线),此后新信号对**另一条线**落锁
即是 v2 语义下的「换线」。

## 决策

把门接进 `cw_intention.update_intention` 的替代线锁定处,不改 v2 结构:

- 新增模块内私有判定 `_switch_gate_open(ist, state, session, sig,
  registry)`:仅当 `phase=='weak'` 且候选线 ≠ `weak_comp`(真换线)时调
  `cw_line_switch.survival_gate`(判据单一源不变,e_alt=候选线
  `cw_line_switch.e_rounds`);放行才 `_lock`,被拦保持弱意向、
  `last_event='gate_hold:<旧>-><新>'`,并按 `register_gate_block` 线对
  去重记账(同对同局只发一次日志,消费侧约定与 default 栈同款)。
- 辖域声明:初始锁线(unlocked→lock)、同线重锁(weak_comp==候选线)、
  P3 强制锁线(无在先承诺线,兜底语义)均非换线,不经门;plane≥2 与
  总开关由门内部自辖(关=放行,零漂移)。
- registry 注入:`update_intention` 增可选参 `registry=None`(沿用
  ADR-0366 session 透传同惯例),`DecisionV2Strategy.update_target` 透传
  `self.registry`——A/B 臂经 `dataclasses.replace` 构造的注册表由此可达
  (W376 C4 臂失效的直接根因面就是这条透传链缺失)。

### Considered Options

1. **在 `DecisionV2Strategy.update_target` 外围拦**(前后对比
   `ist.locked_comp`,被拦即回滚状态机):否——状态机已被改写后回滚是
   补丁形态,弱意向态不可观测且与单回合一次转移语义冲突。
2. **改 `cw_intention` 锁定决策内联判据**(本方案):接——换线裁决的
   真实位置,门在落锁前置拦,弱意向保持可观测,零结构改动。
3. **v2 弃用 E_rounds 门、另造 v2 版生存判据**:否——判据单一源原则,
   第二把尺=漂移源;门数学(W373 REDESIGN §3.4)与栈无关。

## 后果

- 生产默认路径(gate 关)行为逐位不变:`_switch_gate_open` 在门内
  `gate_off` 放行,e_rounds 纯计算无副作用;零漂移锚=off 臂与 W376
  off 臂 300 局逐位相等(W379 重测批断言)。
- 门开时行为增量限「撤销后换线」帧;拦截日志/计数与 default 栈同约定。
- 消费点从 1(default 栈)变为 2;default 栈路径不动。

## 验证

- 单帧锁 5(`sr-od-test/test/sr_od/app/currency_war/test_cw_w379_gate_v2_wire.py`):
  接线拦(保持弱意向+线对计数去重)/缺省关照旧落锁/同线重锁不辖/
  初始锁线不辖/registry 透传捕获(注入副本即门收到者)。
- W376 既有 C4 锁(test_cw_w373_c3c4_redesign / test_cw_p2_survival_band)
  与 test_cw_intention 全绿。
- 重测批 W379:`.debug/temp/currency_war/w379_gate_v2_wire/`(脚本可重跑),
  off vs C4-on 两臂 n=300,判据=W376 §2(拦截率/被拦局存活/死锁画像)
  +P17 回退守卫+off 臂对 W376 off 臂逐位锚。

## 判据

W376 报告(`.debug/temp/currency_war/w376_c3c4_gate_ab/REPORT.md`)裁决
①「C4 在生产策略栈无行为通道 → 接线修复批」;设计=REDESIGN §3.4;
判据单一源=`cw_line_switch.survival_gate`。

## 增补(2026-08-28):W379 重测诚实结论——v2 栈 0 触发,有效性待真实换线帧

接线事实补录(出处 W376 §0 + `.debug/temp/currency_war/w379_gate_v2_wire/REPORT.md`):
门原唯一消费点在 default 栈 `default_strategy.update_target` 换线路径;生产栈
`DecisionV2Strategy` 完整覆写 `update_target` → C4 开关在生产栈无行为通道
(W376 结构断言:off ≡ C4-only 两臂 300 局逐位相等)。本 ADR 决策即修复:
门串联进 `cw_intention.update_intention` 替代线锁定处 + registry 透传
(单帧锁 5 证明门在 weak→异线重锁帧被调且能拦)。

0 触发诚实结论(W379 重测,off vs C4-on,n=300/臂,池指纹
`7af8197782d42c05`):

- **接线成立**:零漂移锚=off 臂与 W376 off 臂 300 局逐位相等;P17 六项
  回退守卫两臂 diff=0。
- **但 v2 sim 下门 0 流量**:300 局 `switch_want=0/block=0`;n=60 诊断
  (revoke_exit①/②=0、evict=0、weak 态=0)证实 **v2 意向状态机的撤销
  出口在 sim 中零触发**——v2 按 [23] 教义「终局线由贯穿件锁定,不是
  pivot」锁定即持有,换线帧结构性缺位,门有消费点、无触发面。
- **裁决**:C4 生产默认关维持(registry 锁与 W373 零漂移锁全绿);门
  有效性(sim 口径)待真实换线帧出现才可测。W363 hp=29 死锁族是
  default 栈现象,v2 栈不适用;若要 v2 具备换线纠错能力,归「v2 撤销
  出口灵敏度」独立演进(非本 ADR 辖域)。
