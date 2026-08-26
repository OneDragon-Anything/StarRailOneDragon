# 0378 — P2 谱系三件:tracks 活引用根治 + [33] 稳态 LevelUp 多击组 + P2 核心件首件同息档门

- 日期: 2026-09-01
- 状态: accepted (采纳)
- 关联: ADR-0377(W193 分布验证场/裁决口径)、ADR-0372(W179 P1 早期买入门——件3 同构先例)、W185(恒 lv6 通道判读)、W183(方向② 修法谱系)、W190(巡检:W185 泛化方向的 P1-sim-only 先例)
- 批: W194(P2 修法谱系统裁批)

## 背景与问题

W193 交付 P2CombatCalib 分布验证场(ADR-0377)后,本批裁决三件积压:

1. **tracks 活引用**(W193 发现的既存缺陷):sim 账本行的
   `v3_intention` 经 `serialize_intention` 落账,但 `tracks:
   dict[str, LineTrack]` 字段落的是**活引用**——session 在 P2 段
   原地改 LineTrack 时,已落账的同局 P1 行 tracks 字段被污染
   (W193 对比门被迫排除该字段);
2. **W185 恒 lv6 通道缺陷**:decision_v2 一轮一击(每轮 XP 上限
   6)+ 唯一多击路径(remediation `[LevelUp]*n` 组)只在「轮内
   deploy_cap 拒绝」触发——而 `select_deployments` 在 deployed≥cap
   时把 bench 全归 held → 部署候选不生成 → deploy_cap 拒绝永不
   发生(**Catch-22**:恰是升级最该提速的 [33] 稳态「cap 满+目标件
   躺 bench」没有任何触发器)。run15 全 P2 恒 lv6,lv6→lv7 需
   ~7 轮超出死亡窗,W183 的 lv7 价格带(s=134.8→84.8)永不可达;
3. **W183 方向②首件优先**(本批探针升级为具体形态):P2 穷轮
   (gold<50)意向核心件自然出现在店被 HOARD 相位 interest_floor
   50 一刀切拦——n=10 seeds planes=2 探针:核心在店 6 轮漏买 5,
   全部 gold≤12 穷轮,弃购代价=核心再遇窗口(W183:3费@lv6 E=27
   次刷新/5费 7-8 级 60-180 轮)。

## 决策

三件全修(实装细节见下);件2/件3 各带独立 registry flag
(A/B 配对臂与回退粒度),默认 True。

### 件1 tracks 深拷贝(根治)

`serialize_intention` 的 dict/list 字段值经 `_to_jsonable` 递归
拷贝落账(嵌套 dataclass 走 asdict=深拷贝;tuple/str 不可变原样
保留,类型不漂移)。生产 `shop.py` 落账与 sim 账本同函数,一次
修复双侧生效。

### 件2 [33] 稳态 LevelUp 多击组(W185 方向 1 泛化)

- **构造**:`remediation.steady_state_levelup_group`——稳态判据
  (进轮快照 state:**plane ≥ 2** ∧ cap 满 ∧ bench 有方向件 ∈
  `_target_names`,与 `levelup_ev_basis` 人口位臂同源)∧ 前置守卫
  (非 boss 轮 [32]/level<level_max/cap 由 level 驱动)→ 发
  `[LevelUp]*clicks_to_next_level`(n 从 working xp_progress 现算,
  同轮主通道已采纳单击计入后取余量);授权=`levelup_ev_basis`
  按 n×总价单次判(稳态下人口位臂天然成立;可负担性 after≥0),
  auth_basis 逐击写入(ADR-0354 观测同构);
- **执行**:`arbiter._steady_levelup_pass`——arbitrate 末段、
  补偿趟**之前**(推进后的 working 回传给补偿趟重验,防双趟各自
  对陈旧金位验证);逐动作资源三约束+simulate 事务性重验,任一
  失败整组放弃(`v3_steady_lv_abandoned` 计数);插入位=首个已
  采纳 RefreshShop 之前(与补偿组同款旧店段语义);每轮至多一组
  (`session.v2_steady_lv_used` 轮键,decide_prep 轮首重置——刷后
  re-decide 段链不连发);
- **辖域 P2+(批内裁决)**:首版全位面泛化在 n=300 引入 P1 回归
  (never2 9→10[新增 42/268]/strict_mal 20→23/出口金 −3.01),
  违反「P1 指标不回退」硬门——辙回辖域 plane≥2:W185 病灶在 P2
  (run15 全 P2 恒 lv6),P1 的多击已由 deploy_cap 补偿臂覆盖
  (run16 p1r7 6 击形态),且 P1 零漂移随之变结构保证;
- **flag**:`registry.levelup_multihit_enabled`(False=逐位回
  W193 后行为)。

与 [18]/[32] 口径调和:hp 不是触发器(稳态判据不含 hp);
boss 轮禁升保留(boss_window_active 前置守卫);息平台账=
levelup_ev_basis 按 n×总价(W185 报告预设口径)。

### 件3 P2 核心件首件同息档门(W183 方向②)

- **判据**(`arbiter._p2_core_firstpiece_exempt`,gold_floor 拒绝
  前的逐笔放行;W179 p1_early 的 P2 同构,配方对语义换核心目标
  语义):plane≥2 ∧ 常态经济态 ∧ 买入件∈意向核心名集
  (`_core_names` 单一源)∧ **首件**(working 现持 deployed∪bench
  无同名,镜像 W175 distinct 纪律)∧ **买入后同息档**([11] 逐字
  口径,跨档照旧走既有通道)∧ 单轮 <1 笔([31]②「目标件刷新
  出现=唯一最高优先级,只买它」);
- 零刷新授权(与 W170/W185 刷门管辖动作不交集);auth
  ['p2_core'] 授权 trace + `session.v2_round_p2_core` 轮计数;
- **flag**:`registry.p2_core_firstpiece_enabled`。

## Considered Options

- 件2 次选(W185 方向 2「LevelUp 候选按需多份」):candidates 层
  发 k 个单击候选逐击裁决——改动小但层4 语义复杂化(逐击分数/
  约束裁决与整组事务性冲突),弃;
- 件2 不推荐(W185 方向 3「靠刷新 re-decide 自然多击」):run15 型
  死局刷新全拒(W183:V_D s>g),此路径在该形态下恰好死,弃;
- 件3 备选「扩展 p1_early_gate 到 P2」:该门建在 P1 配方对语义
  (p1_early_pair,P2 恒空)上,扩 P2 需另造对象语义——不如独立
  小门干净,弃;
- 件3 更宽变体(非同档也放/多笔/含骨架件):单窗内无证据支撑,
  按 W179 先例取最窄口径([11] 同档+单笔+核心首件),A/B 后再议。

## 验证

(数字见批报告 `.debug/temp/currency_war/cw_dev/deep_read/W194_报告.md`
与本 ADR「影响」节;脚本数据 `.debug/temp/currency_war/w194_p2line/`。)

- 单帧锁 13(test_cw_w194_p2_multihit:件1×3/件2×7/件3×3)+
  邻锁(W179/W185 相关既有锁)全绿;
- 件1 零漂移:sim planes=2 单局 P1 行 v3_intention 全 JSON 可序列化
  且 tracks 为快照 dict(修复前=LineTrack 活引用,json.dumps 抛
  TypeError);
- 三臂 A/B(n=300 同池 861fc9f6 重放同 seed,A 臂双 flag off 精确
  复现 W193 B 锚 never2 9 同名单/strict_mal 20/出口金 31.32)+
  敏感性端点(β∈{0,.15}×γ∈{0,.10}×事件金双臂,A/C 双臂,
  ADR-0377 裁决口径)。

## 影响

- 代码:`cw_telemetry.py`(serialize_intention 深拷贝)/
  `decision_v2/registry.py`(两 flag)/`remediation.py`
  (steady_state_levelup_group)/`arbiter.py`(_steady_levelup_pass
  + _p2_core_firstpiece_exempt + 采纳计数)/`strategy.py`
  (轮键/跨局清零);
- 三臂 A/B 关键数字(n=300,池 861fc9f6 重放,A=双 off 精确复现
  W193 B 锚):P1 全指标三臂逐位一致(never2 9 同名单/strict_mal
  20/出口金 31.32,硬门断言);件② P2 金带走量 14.43→10.79、
  D 次数 1.51→0.89、胜率 0.1731→0.1749(hp0 不变);件③ carry
  笔数 +31、其余中性;
- 敏感性端点(8 格,A vs C):金带走量 **8/8 一致下降**(分布级
  改善成立——靶病理指标);胜率 6/8 升 2/8 反向(β=0.15 两格,
  不裁存活分布级);
- 判读锚点:稳态组日志 `[cw][d2][steady-lv]`;授权 trace
  `ev_auth.p2_core`;放弃计数 `v3_steady_lv_abandoned`;
- 实机边界记档:sim 种群 run15 型恒 lv6 不可复现(A 臂 lv7
  reach 已 1.0——sim re-decide 段链与实机单趟 op 的结构差),
  多击组对实机的缺陷消除效果留实机恢复后首验局。
