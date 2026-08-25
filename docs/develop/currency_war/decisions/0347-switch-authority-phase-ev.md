# ADR-0347:切授权——相位地板 + EV 授权 + [12] 门收编总账 + DP 首次接线(经济循环总模型步②a)

- 状态:accepted(2026-08-26,W119)
- 判据:W113 经济循环总模型设计稿 §3.2(经济期望核算)/§3.4(替换行)/§6 迁移表步②行/§8 审计增补 1/2/3/6/7/11 条;口述 [11](无损购买)/[12](息引擎未立不追级)/[17](50 息律该花就花)/[28](守息过程)/[33](升级为阵容服务)
- 影响:decision_v2 新增 ev.py(授权总账)、arbiter(gold_floor/interest_rule/boss_levelup_ban/_active_floor 重写)、discipline(boss_window_active/_hard_node/assess_discipline)、filters(formed_stop 收编 form_ok)、phase(兜底门轮数判据)、scoring(bd['int_emb'] 息分量声明)、remediation(A2 镜像清)、strategy(DP 姿态轮缓存 + E6 latch 采样退场)、registry(form_floor/phase_fallback_min_round/boss_window_fallback_round 新增;formed_stop_min_level/levelup_interest_engine_gate 删除);遥测 dp_posture 字段 + 执行 log ev_auth;**default 栈零改动(冻结)**

## 背景

W114 影子批已让相位(FORM/HOARD/SPEND)每轮被计算并写遥测但零消费;
W118 建立 A 臂基线(相位分布 FORM 96%/form_ok 曾真 16%/三病症锚点)。
本批(步②a=实现+锁测试)开始消费相位:地板族与升级门从「轮数/等级
代理」切到「相位+期望核算(EV)授权」,同时把 v2 栈第一次接上 DP 求解器
(W115 审计 ③:v2 此前零 DP 消费,tribunal/DP 一整层经济智慧只长在
default 栈)。sim A/B 对照(步②b)另批,本批不跑标定。

## 决策

### 1. 相位地板替换阶梯地板(W113 §3.4 替换行)

`_active_floor` 覆盖态优先序不变(应急 rebirth → boss 窗 boss_floor →
war 模式 war_floor——旁路与节点授权逐位保留),常态分支换相位:
FORM → `form_floor`(新常量,初值 20=应急保底语义;**Q1 已裁决:决策器
=EV 授权,地板只是保险丝;四档 sim 对照(不设/10/20/30)归 ②b,本批
只接线不标定**);HOARD/SPEND → `interest_floor`(50)。阶梯地板
(10-49 档内全花)退场。

`gold_floor` 相位域细则:HOARD 下 [11] 无损购买例外(同档/1费)放行、
跨档拒(攒息,拒绝因「HOARD 攒息」);SPEND 下破平台候选**让位**
interest_rule 的 EV 裁决(此处硬拒会架空总账);DP 说花(姿态
level_up/refresh_budget>0)的 levelup/refresh 在 HOARD 获授权放行
(§3.2(d) 单步落地)。levelup 的金门槛整体让位 [12] 总账门,保险丝
form_floor。

### 2. interest_rule 恒拒 → EV 授权(W113 §3.2(d))

跨档消费(≥50 跌破 50,非同档/1费/满息结余特例——三者**原样保留**,
它们是 EV 规则的零息损特例)判 EV:`EV = V − C_interest`。
- V = 层3分剥离息分量:`val − bd['int_emb']`(int_emb 由 scoring 声明
  自己嵌入的息分量=息差,ADR-0332 平滑生效时=真实档损——单一源,
  仲裁层不重算);禁评分/授权两侧各算一遍息账(双重计罚)。
- `C_interest = tiers_crossed × R`,R=**跨位面**剩余节点
  (`cw_intention.total_remaining_nodes`,§8-3:位面末「存 20 进 P2」
  保本钱语义,只算本位面会系统性低估息损)。
- EV>0 放行(含破息——FORM 段买过渡件优先于息是用户原话本体),
  ≤0 拒(拒绝因带 EV 数值)。放行值写执行 log `ev_auth`(授权依据
  trace,验证门 5)。升级(levelup)不辖本门——升级走平台账(下条),
  双门并设会双重计罚。

### 3. [12] 升级门收编 EV 总账 + E6 latch 退场(§8-6/8-7)

arbiter(A1)与 remediation `_compensate_slot`(A2)两处逐字镜像一次清,
单一裁决点 = `ev.levelup_ev_authorized`,三路放行:
1. **[33] 人口位**(一等例外;W121 G1 修正 W113 §3.3 通道 2 的反向
   措辞):触发 = **cap−deployed==0(位子满)∧ bench 有等待上场的
   框架/目标成型件**,且花后 ≥ form_floor(人口位是阵容服务,不是
   抽干金流的许可)——「有单位等上场」的字面义是位子满了才需要升;
   deployed<cap 时该件直接上场即可(部署动作,[32](b):再升纯浪费)。
   当轮战力兑现,通常 >C_interest——[12] 拦的是「空位追级」;
2. **DP 花费授权**:DP 姿态说升级 且 花后 ≥ interest_floor(平台未破)
   ——DP 内生优化了金/级/存活全程期望,说升且平台未破即放行;
3. **静态 EV 平台账**:V(层3分剥离息分量)−(即时档损+满息平台延迟损)
   ×R ≥ 0。平台延迟损 = 花后 <50 时的满息缺口(interest_cap −
   interest(花后))——息引擎未立时追级把金拖在 50 以下,每轮少吃
   满息差,这是 seed6 病症(49 金连追两级)的账面化:49→41 虽不跨
   即时档,平台账 C≈R≫V → 拒。

旧门语义对照:旧「花后≥50」臂 ⊂ ③(C=0 时 V≥0 恒放行);旧
「曾达满息」latch 臂随 E6 退场删除——曾满息不构成破平台的授权,
破平台必须过账;旧 P1 lv<5 宽松门删除——早期升级由 ① 承接。
`v2_ever_full_interest` 字段保留(default 栈仍读写,default 冻结),
decision_v2 停止消费与采样。

### 4. DP 净新增接线(§8-6 硬性项)

`ev.dp_posture` 真实调 `cw_horizon._solved`(生产路径解,台账注入 +
指纹 memo;首解 ~0.3s/指纹,一局指纹数有限)。decide_prep 每轮入口
查询一次写 `session.v3_dp_posture`(RoundPosture,轮键缓存),仲裁层
各 gate 经 `round_posture` 读同一姿态(同轮口径一致)。消费面:
levelup 门 ② 臂、HOARD gold_floor 的「DP 说花→授权放行」。遥测
decisions 行新增 `dp_posture` 字段(授权依据 trace)。**实测声明**:
当前 DP 解在几乎全部 (t,gold,level,hp) 格说「升级/D」(存息姿态
罕见)——故 DP 不作 levelup 的无条件许可(② 臂带平台未破约束),
其有效作用域=HOARD 攒息段的花费授权;②b 观测 DP 姿态分布后再定
DP 授权的松紧。

### 5. boss 窗轮数统一进节点图(§8-2)

`discipline.boss_window_active` 单一源:主判据=节点图(node_type ∈
boss_round_node_types);轮数口径**全仓只在此处**且仅作 node_type
缺读兜底(P1 r≥`boss_window_fallback_round`(9)——P1 末节点恒为
boss 的节点图先验)。旧三处轮数口径(discipline P1 r≥5 遭遇预备窗
/arbiter ×2 P1 r≥9)一次收编。行为变化:节点图可读且非 boss 的
P1 r5-r8 不再入 boss_breaker(不再 war 模式/破息地板)——轮数代理
是 W115-B2 指认的双口径漂移源。

### 6. formed_stop 辖轮 comp 派生 + 消费 form_ok(§8-1;W114 交接)

`formed_stop_active` = P1 ∧ r ≥ max(锁定线 typical_form_round,
formed_stop_min_round) ∧ `form_ok`——谓词族单一源收口(filters 内
board/核心/lv≥5 三项重复实现删除;**行为变化点**:核心必须上场 2★
(旧 bench∪deployed)、lv≥5 项删除(Q2 裁决:等级通过上场完整性进入
form_ok)、辖轮随锁定线 typical_form_round(4-8)派生(早成型
DOT队辖 7 / 晚成型昼神阿雅辖 8)。

### 7. form_score 兜底门校准判据(§8-11)

W118 实测:兜底局 score≥0.5 在 r2-r3 即转真(1 过渡体系≠战力 OK)。
加**轮数下限**判据(合取):`round_num ≥ phase_fallback_min_round`(=5,
灭 r2-r3 误转真、r5 双体系帧保留;门值标定留 ②b,独立于 Q1 四档)。

### 8. C_interest 的 R 跨位面口径写死(§8-3)

见决策 2:R=total_remaining_nodes(当前节点+后续两位面全部),口径
注释在 `ev.cross_plane_remaining_nodes`——位面末攒金在下位面继续吃息。

### default 栈冻结(明确不动)

cw_economy/cw_plan/cw_evaluate/default_strategy 的旧门(latch/等级门/
阶梯地板)全部不动——它是回退保险与 W118 基线臂;A3/A4/C1/C2
(default 侧 [12] 门镜像与 hp 查表)本轮不收编,收编漏删风险以
「default 冻结+两栈解耦」消解。

## Considered Options

- **DP 姿态作 levelup 无条件许可**(§3.2(c) 字面「V_level=DP 姿态
  ΔV」):否决——实测 DP 解几乎恒说「升级/D」(其世界模型里等级→
  板强→存活主导),无条件许可=门全开,seed6 病症复辟;折中=② 臂
  「DP 说升 ∧ 平台未破」,存息保护的语义由静态平台账 ③ 兜底。
- **interest_rule 与升级门共用同一 C 公式**( tiers×R):否决——
  买/刷新的息损是即时档损(结算息按花后金),升级的病灶是平台建立
  延迟(seed6:49→41 不跨即时档但每轮少吃满息差),两种口径各自
  写死并注释;强行统一=发明公式。
- **HOARD 地板=50 且不给 [11] 例外**(§3.4 字面):否决——[11]
  同档花费零息损,地板硬拒会杀掉全部档内购买(45 买 3 都拒),
  与「[11] 特例原样保留」直接矛盾;例外在 gold_floor 相位域内实现。
- **保留 r≥5 遭遇预备窗**(boss 窗合一的保守项):否决——W115-B2
  指认的就是该轮数代理(与 arbiter r≥9 双口径漂移);节点图可读时
  以节点为准,预备窗语义由 EV 授权(破息买过账)承接。
- **C_interest 只算本位面剩余节点**:否决——§8-3 显式要求含下位面
  (位面末保本钱语义);只算本位面在 P1 末/P2 末系统性低估息损。

## Consequences

- 行为变化面(②b sim A/B 的对照锚):FORM 段金 <20 买入被保险丝
  拦(早期买入推迟)、P1 r5-r8 非 boss 节点退出 war 模式、跨档买从
  恒拒变 EV 裁决、升级从 latch 门变三路总账、formed_stop 辖轮随
  comp 派生。
- 已登记待裁(ci_smoke 豁免,ADR-0289 纪律):`deploy_fills_cap`
  (FORM_FLOOR 压低早期买入→deployed 增长慢,seed16 1/25;归 Q1
  四档对照)、`levelup_interest_engine_gate`(旧判据与 [33]/DP 授权
  的 <50 升级冲突,25 局 16 例;判据需改读授权依据或按 hp/interest
  净效应定案)。
- 掉血报警三臂(BloodAlarmTracker)与应急态/ALL IN 语义**逐位未动**
  (旁路铁律;扑满 reward 节点也未入三臂的 _BATTLE_NODES——ADR-0348
  挂账,旁路优先)。
- 检查锚点 `levelup_below_floor_violations`(W113 §3.2)在 ②b 的
  读法需带授权依据(dp_posture/ev_auth),不能沿用旧 0 容忍口径。
