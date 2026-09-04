# ADR-0346:相位影子观测(经济循环总模型步①;FORM/HOARD/SPEND 派生上线,零消费)

- 状态:accepted(2026-08-26,W114)
- 判据:W113 经济循环总模型设计稿 §3.1(2026-08-25 用户裁决版:等级不作为独立门槛、核心须上场、追赶态删除)+ §6 迁移路径表步①行;口述 [13](成型三件套)/[17](50 金息律)/[28](守息)/[33](升级为阵容服务)
- 影响:decision_v2 新增 phase.py(相位派生)、registry 常量 phase_form_score_gate、strategy.decide_prep 影子计算、cw_telemetry 决策迹三字段 + rounds 视图、shop.py/ prep_director 遥测透传、cw_sim 账本三字段;**零决策路径改动**

## 背景

三个实机/sim 病症(run11 息引擎立得晚 / run10 溢出金闲坐 / seed6 破息追级)共用一个
架构根:决策框架没有「战力 vs 经济期望」的统一判别变量(W113 §1)。架构级重设计已
定稿,迁移路径为渐进三步(影子→切授权→切调度)。本批只做步①:让相位每轮被计算并
写进遥测,**不被任何决策逻辑消费**——纯观测上线,为步②③提供对照基线与 sim 配对
前提(影子代码在场时同 seed 决策序列必须逐位一致=自证零行为)。

## 决策

### 1. 相位派生函数(独立模块 `decision_v2/phase.py`)

- `Phase` 枚举:FORM(凑过渡羁绊)/ HOARD(凑息)/ SPEND(花钱)。
- `derive_phase(state, session, registry)`:`NOT form_ok → FORM`;
  `form_ok ∧ gold < interest_floor(=50,registry 单一源) → HOARD`;
  `form_ok ∧ gold ≥ interest_floor → SPEND`。
- `form_ok(state, session, registry)`(裁决后版本,**无等级项**——等级通过上场
  完整性进入判定,人口上限不够→羁绊/核心上不了场→判假→留在 FORM,升人口=
  [33] 人口位通道):`intention_locked AND bond_tiers_met(board 只数上场,
  comp.form_tiers 全键满足)AND core_deployed_ok(intention_core 在 deployed
  且 star≥2——躺 bench 不算)`。线不可解析/无 form_tiers:保守 False(与
  formed_stop_active 同口径)。意向未锁(兜底局):降级
  `form_score ≥ phase_form_score_gate`。
- `form_score(state, registry)`:连续量副指标,归一 [0,1],**按上场阵容**
  (deployed only):过渡体系达成数(单一源 `cw_sim._engines_count`)+
  配方档小数(与 `scoring.board_rung_x` 同式系数),封顶 2 档除 2。
- 相位是**派生量不存跨轮状态**(session 只作遥测透传暂存,每轮重算)——
  天然免疫 session 丢失(W113 §3.1 硬判据)。

### 2. 注册表常量

`phase_form_score_gate = 0.5`(兜底局 form_ok 降级门,sim 校准域)。初值量纲推算:
form_score 满分 = 2 过渡体系(rung2,H3 胜率 77.8%),1 体系 = 0.5(rung1,
41.6%)——「战力 OK」保守取 1 体系档,与 formed_stop 族「成型下界」保守取向同族。

### 3. 遥测接线(只写不消费)

- 生产:decide_prep 入口计算 → `session.v3_phase/v3_form_ok/v3_form_score` →
  shop.py 轮行与 prep_director 步行 `extra['phase'/'form_ok'/'form_score']` →
  DecisionTrace 新字段 → decisions.jsonl;rounds 视图尾显 `ph=HOARD/ok/0.50`。
- sim:轮入口(首决策段)快照三值入账本行(与生产「每轮决策入口算一次」对齐;
  一轮多段取首段=轮初态)。
- **任何 if-相位-then-改行为的代码都属违例**——本批 diff 中相位只出现在
  计算/透传/展示三处。

### 4. 伴随缺口修复(遥测面,零行为)

接线时发现 ADR-0343 声明的 `extra['formed_stop']` 在 recorder 侧无 DecisionTrace
字段映射被静默丢弃(shop/prep_director 都在传)——补挂 `formed_stop` 字段,
ADR-0343 声明的生产通道自此真正落盘。sim 账本侧 formed_stop 原本就有,不受影响。

## Considered Options

- **相位进 discipline/assess_discipline(纪律族视图)**:否决——纪律族产出的是
  **决策消费**的覆盖态视图,相位放那里=邀请被消费,违背影子批零行为承诺;
  独立 phase.py 让「无消费点」可被 grep 审计(消费面=0 是本批验收项)。
- **form_score 复用 scoring.board_rung_x(混合域)**:否决——board_rung_x 含
  bench 折减(bench_form_weight),而相位语义是「上场了才算战力」(核心须上场
  裁决同向);且评分层函数被影子观测复用会给步② 制造隐式耦合。采用 deployed-only
  口径,体系/配方判定仍单一源(`_engines_count`/`recipe_tier`)。
- **相位写进 session 后由 formed_stop 消费(顺带统一谓词)**:否决——formed_stop
  的收编(P1/r7/lv≥5 项随裁决去除)是步② 的内容,影子批动它=行为变化,本批
  存在理由作废。双谓词族暂存,步② 合流(交接注记见 W114 报告)。
- **遥测不消费的例外:rounds 视图展示**:采纳——视图是判读面不是决策面,
  影子期就需要人眼看相位轨迹才能为步② 标定 gate。

## Consequences

- 行为零变化:决策路径无任何相位读取;sim 影子自证(同 seed 基线 HEAD vs
  工作区 decisions 序列逐位 diff 为空)见 W114 报告。
- 遥测 schema 追加三可选字段(旧记录缺省不破坏;jsonl 追加行,下游
  判读/检查器全 .get 兼容,已核)。
- 步②(切授权)交接:formed_stop_active 改为消费 `form_ok ∧ r≥formed_stop_
  min_round`(lv≥5 项随裁决去除);地板族换相位地板;[12] 门收编 EV 总账——
  相位派生本体无需再动。
- 回滚:git revert 本批即可(无状态迁移、无常量被既有代码消费)。
