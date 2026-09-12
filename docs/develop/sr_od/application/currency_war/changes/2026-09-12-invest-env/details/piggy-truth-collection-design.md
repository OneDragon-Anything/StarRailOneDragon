# C 类扑满增益真值面:档案采集点定谳设计与落地泊位(T-152 设计段)

> 定位:invest-env 迭代数据批的**设计段**交付(T-152;承接 T-143 完成报告 §5-2
> 立项建议)。T-143 已交付识别面(sim 注入通路 + `piggy_reward` 写点修复);
> 本篇只设计**真值面**——「每个扑满奖励节点增益多少金」的实机档案采集方案。
> **纯设计零代码**:全部落码面归实机窗落地段(§6);唯一禁碰面 = 应用层
> `src/sr_od/application/currency_war/prep_actions.py`(用户域在飞;本设计
> 全部写点位置避开它,见 §4.5)。
> 寿命 = 迭代;正文引用的持久单一源 = 代码符号与在册文档路径。

## 1. 目标量定义(真值面到底采什么)

### 1.1 参数与语义

目标参数 = `reward_node_bonus_{normal|super}`(估算注册表
`kernel/cw_env_economy.ENV_ECONOMY_ESTIMATES`,当前缺位 → C 类通道 fail-closed
裸分维持)。变体映射单一源 = `cw_env_economy._REWARD_BONUS_VARIANTS`
(经济过热 → normal / 经济严重过热 → super)。

估值公式(`env_economy_value` 通道 6):**期望增益 × 剩余期望奖励节点数**。
剩余节点数因子 = `_REWARD_SLOTS` 槽位结构先验 ((1,1),(1,2),(1,8),(2,6)),
已由 2026-09-12 数据批落注册(样本量申报见 data-batch-estimates.md §7)。
本设计只辖**增益因子**。

### 1.2 增益的精确定义

```
reward_node_bonus_variant
    = E[扑满轮节点内金收入 | variant] − E[普通奖励轮节点内金收入]
```

- **扑满轮**:过热局中 `piggy_reward=True ∧ node_type='reward'` 的节点轮
  (确认帧口径,T-143 申报的跨轮滞留防线:识别标记会滞留到下一轮,
  统计面必须与节点类型联判)。
- **节点内金收入** = 该奖励节点为 bot 带来的、轮首三分量**之外**的金:
  - 轮首三分量已有单一源模型(`kernel/cw_economy.round_start_income`,
    奖励轮分支 = base + 连胜×win_reward_mult + 息;base =
    `reward_base_gold(plane, round)` 平面感知键;连胜 = `streak_gold` 真值表;
    全部【注】级真值,不在本设计重采范围);
  - **战利品金**(待采)的发放形态在册描述 = 普通奖励节点「通关给金币/装备/
    经验」(docs/game/currency_war/data/competitors.md 节点表)+ 清关后备战
    画面晶矿球「开启后可能获金币/角色/装备/稀有物品」
    (`obs/cw_identity_obs.py` 2026-08-14 建档注释);过热局替换为(超级)
    次元扑满后「掉落(超)多战利品」(效果原文,cw_invest_data id105/119)。
    **金的部分占多少、在哪一屏可见,即在册缺口**(invest_effects.md 经济过热
    条目:「掉落是否以金/物资/装备为主未知」)——本设计把它收敛为
    实机窗首验定谳项(§3.4 Q1-Q4)。
- **普通对照臂**:无过热环境局的普通奖励轮。它同样需要战利品金真值
  (晶矿球金),否则增益无从减起。sim 侧现有普通值 = `EVENT_GOLD_BY_ROUND`
  (sim/engine_p1,ADR-0447 校准总闸)是按轮次黑盒校准的「奖励球/节点事件金」
  残差表,非节点类型分键的分解真值,只能作对拍参照,不能当对照臂真值。

### 1.3 与基础/息/连胜的分离规则(就绪判据①要求的口径成文)

任一通道采到的「获得金」若含轮首三分量,按下式分离:

```
loot_gold = 获得金观测 − base − interest − streak_component
```

- `base` = `reward_base_gold(plane, round)`(kernel 单一源,P1r1=3/P1r2=4/
  其余 5);
- `interest` = `interest(轮首 gold, cap_resolved)`:轮首 gold 取该轮最早
  可信(`gold_readable=True`)决策帧;cap 持卡覆写经
  `cap_resolved_of_session` 同源聚合(装配端从决策帧 active_strategies 聚合,
  禁裸缺省 5——息律投资 cap=10 局会低估);
- `streak_component` = `streak_gold(进轮连胜) × win_reward_mult`:进轮连胜
  取前一轮结算行 streak(档案 rounds 链);倍率 = STRATEGY_ECONOMY 聚合
  (取最大不叠乘,在册唯一非 1 值 = 伟大征服 3.0);
- 任一分量不可得(轮首 gold 失读/连胜链断裂)→ `loot_gold` 置 None
  (宁缺勿造);残差为负 = 分量模型与实际入账有出入,置 None + 对账行披露
  (不截 0、不冒认真值,数据治理「先隔离标注」同款)。

若通道直接读到**分项行**(结算屏金币总览的分项构成,§3.4 Q2),优先分项
直读、跳过建模扣除——零建模分量优于建模扣除。

## 2. 现役遥测面审查(有没有现成字段)

逐项审查结论:**无现成字段承载战利品金**,新增不可避免;但不同通道的
新增成本差异极大。

| 现役面 | 有什么 | 缺什么 |
|---|---|---|
| 决策帧快照(decisions 行 state/gold/gold_readable) | 备战画面 gold 存量逐帧在案(决策切片全帧全字段) | gold 差分 = 轮首三分量 + 备战净支出(买/卖/刷/升级)+ 战利品的混合(data-batch-estimates.md §6 在案定性),不可直接分离 |
| outcomes 行(telemetry/schema.OutcomeRecord) | hp/挑战进度/连胜/掉血 tooltip 三项/板深快照 | **无任何金币字段** |
| 结算屏解析(obs/cw_settlement_obs.parse_settlement_assets) | 「存量」(当前金币)已解析并写 session/结算覆盖 | 「**金币总览(获得)**」OCR 文本已在帧上、未结构化落行(docstring 在案:总览 = 本节点获得量)——**离真值最近的未采收面** |
| op_journal 动作回执行 | 商店四动作(Buy/Refresh/LevelUp/Close)执行回执带 post gold | 点球(ClickSpheres)/开箱(OpenBox)无回执行、无逐件金额(data-batch-estimates.md §6 在案) |
| 节点奖励六边形 probe | 已卸载的历史临时钩子(基础奖励真值已闭环,tools 注释与 data-collection.md 在案) | 非现役通道;且其目标(基础奖励)已有注册表值,不辖战利品 |

## 3. 候选通道与定谳方案

### 3.1 通道 A(主候选):扑满关结算屏「金币总览(获得)」直读

- **依据**:结算页含「金币总览 <获得>」与「存量 <当前>」两组金币数,
  **总览 = 本节点获得量**(`parse_settlement_assets` docstring,win 帧
  亲读证据口径);连胜档金采集史也实证总览面板「分连胜行」
  (data-collection.md 连胜钩子行)。
- **形态推定**:过热局奖励节点替换为扑满 = **奖励型战斗节点**(有战力要求、
  不掉血、打不过零奖励;invest_effects.md + user_playstyle 例外注记在案)
  → 按战斗节点族推定有结算屏,其总览含战利品金。
- **成本**:唯一新写点 = 结算观察段对总览数的结构化落行(OCR 文本同帧
  已在,零新增截图/识别);采集端成本全项目最低。
- **辖域边界**:总览 = 战斗结算时点的节点获得;清关后备战画面晶矿球金
  **不在总览内**(球在节点结算之后点击)。若扑满战利品发放形态含晶矿球段,
  通道 A 只覆盖战斗段——两段合账规则见 §3.4 Q3 定谳后固化。

### 3.2 通道 B(兜底 + 对照臂):备战环 gold 窗口差分 − 动作账扣除

- **定义**:对无结算屏的奖励轮(普通奖励轮,或 Q1 定谳扑满关无结算屏时),
  取该轮内最早与最晚两个可信 gold 决策帧作窗口,差分减去窗口内动作净支出
  (动作账逐笔在案:买价=卡费、卖价=费用退金表、刷价/升级价=现读注册表;
  金额不可得的动作项 → **整轮剔除**,先例 = tools/cw/loss_comp_bucket_replay.py
  「未知金流整轮剔除」口径)。
- **关键性质**:**纯装配端派生**(decisions 切片全帧 gold 在案),零新写点;
  **存量档案可回溯**——现有 146 局语料重装配即得普通对照臂大样本,
  普通基线不需要等实机窗。
- **边界**:gold_readable=False 帧处窗口作废(None);备战环内点球与
  买/卖的执行交错按动作账扣除,扣除模型的完整度决定精度(§6 阶段 2 锁)。

### 3.3 通道 C(备选,不推荐为主):晶矿球逐件直读

点球开启的掉落若逐件带金额文本可 OCR,理论上可逐件落账。但点球动画
(~2s 飞向备战/商店/装备栏,screen_flow_timing #16)与逐件金额可读性
完全未观察,观察成本高、且仅覆盖晶矿球段。仅当 Q3/Q4 定谳显示
A/B 两通道都覆盖不了战利品主段时再立项。

### 3.4 实机窗首验定谳项清单(阶段 1 泊位的验收对象)

| # | 定谳问题 | 裁决影响 |
|---|---|---|
| Q1 | 扑满关有没有战斗结算屏? | 有 → 通道 A 主推;无 → 通道 B 升主通道并追加战斗段观察设计 |
| Q2 | 结算屏「金币总览」是单一总数还是分项行(基础/息/连胜/战利品)? | 分项行 → §1.3 走分项直读(零建模扣除);单一总数 → 建模扣除 |
| Q3 | 扑满战利品的发放形态:战斗内直发、清关后晶矿球、还是两者?普通轮晶矿球金与扑满轮是否同机制? | 决定通道 A/B 的辖域合账规则与增益口径边界 |
| Q4 | 普通奖励节点(无战斗)确认无结算屏?清关直发金(若有)在哪一屏可见? | 决定普通对照臂的通道归属(B 或 C) |

定谳批操作纪律:先建档(`od-dev-screen-onboarding`)再定采集点;扑满局
1-2 局画面流(自然到局或加速到局)全采样,离线判读产出纪要归本迭代目录。

## 4. 字段设计(新增遥测字段)

### 4.1 F1:outcomes 行 `gold_gained`(通道 A 真读字段)

| 项 | 设计 |
|---|---|
| 字段名 | `gold_gained: int \| None`(outcomes 行加法键,读端 `.get` 容忍,旧记录缺省 None 不破坏 schema) |
| 语义 | 结算屏「金币总览(获得)」= 本节点获得金币总量的直读真值(注意:是**总量**,分离到战利品在装配端做,见 F3) |
| 埋点位置 | 结算观察段(`operations/cw_screen/cw_screen_battle_wait.py` 结算观察半,与 `parse_settlement_assets` 消费同点同时序);解析纯函数扩展落点 = `obs/cw_settlement_obs.py`(新增 parse 函数,fixture 可单测)。**非 prep_actions 域** |
| 时序 | 与现役结算 OCR 同帧同源(零新增截图);结算页瞬窗特性与 damage tooltip 同族——读不到即 None,不重试不补帧(v1) |
| 值域 | `[0, 999]`;OCR miss / 面板缺席 = None(宁缺勿造);败局页若无该面板 = None——扑满败轮「打不过零奖励」的语义由统计面按节点胜负(progress_delta/killed)处置,不由本字段编码 |
| 治理 | 与 `hp_confidence` 可信门解耦(金币面板与 hp 面板独立在场);锚正则须带「获得」token 锚(与「存量」正则同族手法),fixture 用实拍结算屏存档校准 |

### 4.2 F2:rounds 行加法键(装配端透传与统一出口)

| 字段 | 类型 | 语义 |
|---|---|---|
| `piggy` | `bool \| None` | 该轮存在 `piggy_reward=True` 决策帧(识别面透传;None = 该轮无决策帧)。**滞留形态照录原值**,统计面联判 node_type(§1.2 确认帧口径);rounds 行现无该键(2026-09-12 核对 `_build_rounds`),纯加法 |
| `loot_gold` | `int \| None` | 战利品金统一真值出口(F3/F4 二选一产出;None = 不可得,宁缺勿造) |
| `loot_gold_basis` | `str` | 来源标记:`'settlement_overview'`(通道 A 分离)/ `'prep_window_diff'`(通道 B 派生)/ `''`(不可得)——判读与统计按 basis 分型,禁混池 |

### 4.3 F3:通道 A 派生契约(basis='settlement_overview')

前提:该轮有 outcomes 行且 `gold_gained` 非 None。
`loot_gold = gold_gained − base − interest − streak_component`(§1.3 分离规则;
分量取值源全部为档案行内数据 + kernel 单一源函数,装配端纯读派生、零新
运行时写入——与档案装配器「装配端纯读派生」惯例一致)。
分量不可得或残差 < 0 → `loot_gold=None`、basis 保留、对账披露
(披露键建议 `loot_reject_reason`,值域:`'component_missing'/'negative_residual'`)。

### 4.4 F4:通道 B 派生契约(basis='prep_window_diff')

前提:节点轮无结算屏行(普通奖励轮;或 Q1 定谳扑满关无结算屏)。
窗口 = 该轮最早与最晚可信(`gold_readable=True`)gold 决策帧;
`loot_gold = 窗口末 gold − 窗口首 gold − 窗口内动作净支出`,动作净支出 =
逐动作金额模型(买=卡费/卖=费用退金/刷·升=现价,单一源 = 现役动作回执
与注册表),金额不可得的动作 → 整轮剔除(loot=None,reason=
`'unknown_cashflow'`)。窗口内无动作且 gold 差 ≤ 0 → loot=0 是合法读数
(该轮无晶矿球金),**0 与 None 严格分写**。

### 4.5 禁碰面核查与 schema 治理

- 全部写点位置:结算观察段(cw_screen_battle_wait / cw_settlement_obs)、
  装配器(match_archive.py)、统计脚本(tools/cw/env_economy_estimates.py)
  ——**零触碰** `src/sr_od/application/currency_war/prep_actions.py` 与
  `kernel/cw_prep_actions.py`;若未来通道变体需要执行缝埋点(不为本设计
  推荐),届时按任务书归实机窗落地段并与用户域协调。
- 档案 schema:加法字段按在册惯例 bump(`SCHEMA_VERSION` 12 → 13,变更史
  注入版本注释块),存量档案经 `load_archive` 版本检查自动重装配补齐;
  读端全部宽容缺键。
- 装配器纪律:本批字段全部「装配端纯读派生/透传」,零新运行时写入面
  (F1 除外——它是结算观察段的唯一新运行时写点)。

## 5. 与 sim 识别面的对接契约(识别帧 × 真值金额配对)

### 5.1 配对键

- **槽位键** = `(plane, round_num)`(rounds 行现役键,1 基);
- **变体分键** = 开局环境(`opening.chosen_env` 档案现役面)∈
  `{经济过热→normal, 经济严重过热→super}`(映射单一源 =
  `_REWARD_BONUS_VARIANTS`;两变体**禁混池**,统计面按变体分别出参)。

### 5.2 识别面 ↔ 真值面的联接

| 面 | 载体 | 状态 |
|---|---|---|
| sim 识别面 | `sim/cw_sim_piggy.py` 注入批账本行 `piggy_reward`(确认帧 = True ∧ node='reward';三臂同 seed 对照;槽位先验 p1r1/p1r2/p1r8 与 p2r6) | 已通(T-143) |
| 实机识别面 | 决策行 `piggy_reward`(写点 = mandate_v1 两栈,判据单一源 `kernel/cw_reward_node.is_piggy_reward_frame`)→ F2 透传 rounds `piggy` | 已通(T-143 修复) |
| 真值面 | rounds `loot_gold`(+basis) | 本设计,落地段实现 |

配对规则:统计面取 `piggy ∧ node_type='reward' ∧ loot_gold 非 None` 行为
变体样本;`¬piggy ∧ node_type='reward' ∧ basis='prep_window_diff'` 行为
普通对照样本。识别滞留由确认帧口径防(T-143 leak 口径:标记与节点容器
联判),真值侧无需再防——loot_gold 挂在正确的轮槽上(装配键 = 节点轮)。

### 5.3 统计消费与三门就绪判据对齐

消费载体 = tools/cw/env_economy_estimates.py 扩 C 类统计段(重采入口
单一源不变,脚本不回写源码、注册表手工落):

- 估计:`bonus_variant = mean(样本集) − mean(对照集)`;区间 = 两均值差的
  bootstrap 95% percentile CI(分层按变体;bootstrap 手法与种子纪律沿用
  脚本现役段);
- **档案面门**:每变体可用扑满轮样本 ≥ 20 + 本篇 §1.3 分离口径成文
  (本篇即其载体);就绪判据的持久载体仍是 tools/cw/env_economy_estimates.py
  头注,届时以本篇口径更新之;
- **统计面门**:CI 下端 > 0(与注册表 fail-closed 门同语义:方向不闭合不落);
- **对拍面门**:sim 注入批槽位分布(p1r1/p1r2/p1r8 + p2r6)与实机 `piggy`
  轮槽位分布方向一致(两变体分键无结构性矛盾——混淆 = 采集点错);
  普通对照臂均值另与 sim `EVENT_GOLD_BY_ROUND` 同轮值方向对拍
  (黑盒校准表只作方向参照,不作相等断言);
- 落参后动作:值/CI/来源(本篇通道口径)/截止日四元组手工落
  `ENV_ECONOMY_ESTIMATES` 的 `reward_node_bonus_{normal,super}` →
  `env_economy_value` 通道 6 自动解锁;ECON_VALUE_NORM 上界重核算由构建
  校验(`_validate_estimates_governance`)强制兜底,机制在册。

### 5.4 存量数据处置申报

现有 8 扑满局档案(经济过热 ×7 + 严重过热 ×1)无 `gold_gained`
(真值从未被捕获)→ 按数据治理「不能修复就删除/隔离」裁定:**不回填、
不入统计**,维持 data-batch-estimates.md §6 的「零有效估计」申报;
存量普通局(146 局语料)经 F4 通道 B 回溯派生对照臂样本,历史脏区降权
口径(telemetry-reading「字段可信度分级」)照常适用。

## 6. 落地段泊位方案(实机门开后的执行序)

| 阶段 | 泊位 | 交付物 | 门 |
|---|---|---|---|
| 1. 画面定谳批 | 实机窗开**首泊位** | 扑满局 1-2 局画面流建档(od-dev-screen-onboarding 纪律)+ Q1-Q4 定谳纪要(归本迭代 details/) | Q1-Q4 全部有裁决;通道 A 可行性定谳 |
| 2. 字段落地批 | 定谳裁决后 | F1 写点 + F2/F3/F4 装配 + 档案 v13 bump + 统计段扩展 + 测试锁(解析 fixture 锁 / 装配派生锁 / 统计段锁 / 禁碰面核查) | 测试绿;`git diff` 零 prep_actions 触碰 |
| 3. 样本积累期 | 阶段 2 后常驻 | 逐局判读 loot 行质量(basis 分布/None 率);积累至每变体 ≥ 20 轮。normal 自然到局 ≈5.5%(约 4-5 局);super ≈0.7%——**加速选项** = 开局环境三选一重刷(重开只到 P1,成本低),由编排者按当时实机窗预算裁决 | 档案面门达量 |
| 4. 落参批 | 三门齐 | 统计脚本产出 → 手工落 `ENV_ECONOMY_ESTIMATES` → C 类通道解锁 → 策略行为验证(选卡帧 sim A/B:过热环境估值从裸分变域带) | 落参就绪判据三门(§5.3)全过 |

互斥协调:阶段 1/3 需要实机窗(与实机对局批互斥,单跑道纪律);阶段 2
落码面与用户域在飞批的互斥面 = 仅 `operations/cw_screen/cw_screen_battle_wait.py`
与 `obs/cw_settlement_obs.py` 的结算观察段(开工前查 staged 面逐文件点名)。

## 7. 风险与失效方向

| 风险 | 失效方向 | 处置 |
|---|---|---|
| Q1 定谳扑满关无结算屏 | 通道 A 作废;通道 B 只覆盖备战段,扑满战利品的战斗内获得部分(若 Q3 定谳为战斗内直发)无窗口 | 阶段 1 追加战斗段观察设计(战斗画面 gold HUD 观察批,另行立项);通道 A 的 F1 字段仍落(战斗节点通用面,不浪费) |
| 总览 OCR 命中率低 | gold_gained None 率高 → 样本量门难达 | fixture 校准锚正则;None 率进阶段 3 判读面板,持续 >50% 时回到识别层调参 |
| 分量模型误差(息入账时点/win_reward_mult 持卡局) | loot_gold 残差负值/系统性偏移 | 残差对账披露行(§4.3);对拍面用 sim 方向一致性兜底;系统性偏移 → 分离规则回炉(禁拍值硬凑) |
| super 变体样本积累慢 | 落参周期被拖长 | 加速到局选项(§6 阶段 3);或先落 normal(样本齐者先落,变体独立分键是设计使然) |
| 备战环动作账不完整(买/卖金额失读) | 通道 B 整轮剔除率升高 | 剔除率披露;对照臂样本量大(存量回溯),剔除容忍度高 |

## 8. 关键取舍

| 备选 | 为何放弃 |
|---|---|
| 只做装配端派生(通道 B 单通道,零新写点) | 扑满关战利品的战斗内获得不在备战窗口内(若 Q3 定谳为战斗内直发则结构性采不到);结算屏总览是游戏内直读的「本节点获得量」,弃真读用推算 = 放弃最高等级证据 |
| 逐件金额落账(通道 C 为主) | 逐件可读性未定谳、动画时序约束多、仅覆盖晶矿球段;降备选 |
| 复用已卸载的六边形 probe 扩展 | 其目标(基础奖励)已闭环且有注册表值;战利品非其辖域;复活临时钩子违背「采完删」生命周期纪律 |
| gold_gained 编码败轮零奖励语义 | 败局页面板缺席 = None 与「真零」不可混写;零奖励语义归统计面按节点胜负处置(§4.1) |
| 存量 8 扑满局回填 | 真值从未被捕获,回填 = 造数(数据治理禁);普通对照臂靠存量回溯派生,扑满臂只能新采 |
