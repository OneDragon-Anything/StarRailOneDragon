# 14. 阶段节奏骨架(阵容无关 × 阵容参数)

> 总见 [README](README.md)。本文:**策略骨架** —— 把「每阶段(节点×等级)该做什么」抽象成**阵容无关的通用节奏**(一套),不同 T1 阵容只换**参数**(`level_plan`/`factions`/`core_chars`/`key_equips`)。灵活支持所有 T1,不为每阵容硬编码一套流程。
> 依据:2026-08-09 攻略调研(decisions D-21;bwiki 刷新概率表 🟢 + 米游社 V4.4 评级 🟢 + 3DM/巴哈/知乎节奏 🟢)。**对齐现有,不另起炉灶**:03 `level_plan`(等级→动作)/ 02 `_phase_weights`(位面×HP)/ 12 commit / F-3 α(t) commit-optionality。
> **2026-08-11 升级(D-94)**:§2 形式化为 `NodeGoal` dataclass + `get_node_goal` 查询原语 + `spend_mode` 档位映射;§3 加 HP 区行为(消除 40-50 真空带)+ streak 接线顺序 + 7 杠杆落地状态;§7 修副本数漂移(18→9,D-93);加 §8 实施路线。原 /goal「三轴重设计」稿(15)经 review 发现与本文 ~70% 重复(三轴 = 本文 §1-§2/§3/§4-§5)→ **净贡献合并入本文,15 删除**(单一源,防双源漂移)。

## 核心论点:骨架一套 × 参数化 comp

策略 = **阵容无关的骨架**(所有 T1 共用)× **阵容参数**(每 comp 填)。骨架驱动「何时升 / D / 锁 / all-in / 转」;参数告诉骨架「找谁、什么算成型」。

- **骨架**(本文 §1-§3 + 02/12):等级曲线驱动 + 经济线 + 保血/保经济切换 + commit/optionality(α)+ 观测驱动反馈。
- **参数**(03 `Comp` 数据类 / `data/comp_library.md`):`factions`/`form_tiers`/`core_chars`/`level_plan`/`key_equips`/`form_difficulty`/`countered_by_bosses`。

**`level_plan` 是骨架与参数的接缝**:骨架提供通用等级曲线(§1 概率表)+ 兜底 `_DEFAULT_LEVEL_GOAL`;comp 自带 `level_plan` 覆盖(如红A「2-7 上9」、阿雅「4-5 级 D 1费」)。无 comp 走通用,有 comp 走专属。**这正是 03「经济统一论」已写的设计,本调研用概率表坐实其地基**。

## §1 等级曲线 = 节奏锚(等级驱动一切)

**等级 = 上阵数上限 = 商店刷高费概率**(🟢 官方)。节奏围绕等级曲线:

- **Lv3 前**:纯冲等级(100% 1费,买牌=过渡,不升级=浪费)。🟢「4 级前主升级」。
- **Lv4**:首个有意义买牌级(出 2费 25% / 3费 10%)。
- **Lv6-7**:找 2-3费核心(2费峰值 Lv6 / 3费峰值 Lv7)。
- **Lv8**:找 4费 + 出 5费;**P2 2-7 关左右升 8 搜核心**(🟢 知乎)。
- **Lv9-10**:追 5费 + 关键卡追 3星。

### 商店刷新概率表 p(level, cost) ★ `level_plan` 硬输入(🟢 实机 OCR + VLM,D-91)

> 完整 Lv1-10 × 1-5费 实机落地(D-91,备战商店底部百分比条点开弹窗表,OCR + VLM 双源一致,每行和=100%)。**权威值 = 代码 `cw_shop_odds.REFRESH_PROB`**(单一源);本表与其一致,版本更新只改代码 + 同步本表(双源防漂移)。角色/装备/效果修正(如命运卜者·黑鹅 5费↑)留 A4.7(待数据采集)。

| 等级 | 1费 | 2费 | 3费 | 4费 | 5费 | 该级 D 什么 |
|---|---|---|---|---|---|---|
| Lv1-3 | 100% | — | — | — | — | 别 D,冲等级 |
| Lv4 | 65% | 25% | 10% | — | — | 赌 1费阵容(阿雅) |
| Lv5 | 45% | 33% | 20% | 2% | — | 赌 1费(尾声) |
| Lv6 | 30% | **40%** | 25% | 5% | — | **2费峰值** |
| Lv7 | 19% | 30% | **40%** | 10% | 1% | **3费峰值**(姬子·启行 3费在这 D) |
| Lv8 | 18% | 25% | 32% | 22% | 3% | 4费/5费核心(升 8 搜) |
| Lv9 | 15% | 20% | 25% | **30%** | 10% | **4费峰值** + 5费 |
| Lv10 | 5% | 10% | 20% | 40% | **25%** | **5费峰值**(追 3星 5费) |

→ `level_plan[Lv] = roll, target_cost = 该级峰值费`(骨架默认;comp 可覆盖)。

## §2 节点×等级×动作骨架(阵容无关)

### §2.0 NodeGoal 结构(实施级形式化,D-94)

节点目标形式化为 `NodeGoal` dataclass(`plan()` 读),§2.1 表是其可读视图 `_DEFAULT_NODE_PLAN`:

```python
@dataclass
class NodeGoal:
    target_level: int           # 该节点目标等级(地板);显式 gate plan()
    spend_mode: str             # 驱动 economy 档位(映射见 §2.2);改名避 config.economy_mode 冲突
    action_focus: str           # 描述辅(指导 action 偏好,不直接驱动评分)
    danger_d: bool = False      # A8 遭遇前战力不足 → 弃息 D 保血
```

**字段消费者(谁读、怎么用)**:
- `target_level` → gate plan()(显式目标等级,`_expected_level` 辅,见下「责任分工」)。
- `spend_mode` → **驱动 economy 档位**,触达两消费者:`economy_score`(权重)+ `_maybe_sell_for_interest`(rush_level/allin 跳过卖息)。与 `config.economy_mode`(用户偏好微调)层级不同:NodeGoal.spend_mode 是**节点档位 gate**(主),config 是偏好(辅)。
- `action_focus` → 描述辅(d_search 偏 D 牌 / chase_star 偏追星;不直接进评分,`plan()` 启发式读)。
- `danger_d` → 弃息 D 保血(`_refresh_cap` 放宽 + economy 让位)。🔴 **前置**:`read_node_type` 识别准(现仅 boss 核实,遭遇/补给/巨星标签待多子态补)+ hp_trend + difficulty OCR(阶段 4)。

**查询原语 `get_node_goal(plane, round) -> NodeGoal`**:node_plan 用 `(plane, round_range)` 区间键(如 P1 中期 = plane 1, round 4-6)+ 单点键(2-7 = plane 2, round 7)。先精确单点 → 区间 → fallback。**fallback**(未匹配):`target_level = _expected_level(round)`、`spend_mode = adaptive`、`action_focus = rush_level`。首领节点号不定(1-7/1-8/1-9 因位面长度)→ 用区间(P1 后期 1-7~1-9)+ "首领前一轮"触发(lock_blood + danger_d)。

**责任分工(NodeGoal.target_level vs _expected_level)**:`NodeGoal.target_level`(节点目标,**显式 gate plan()**)主;`_expected_level`(等级曲线,02/14)辅(fallback + 节点内平滑)。**冲突 NodeGoal 赢**(节点目标覆盖曲线)。

### §2.1 节点×等级×动作骨架表(= `_DEFAULT_NODE_PLAN`,阵容无关)

> 表 = NodeGoal 实例的可读视图:`target_level` / `spend_mode` / `danger_d` 是 NodeGoal 字段(§2.0);动作 = `action_focus`(含经济行为,详 §2.2 spend_mode 映射)。

| 阶段(位面-节点) | target_level | spend_mode | danger_d | 动作(action_focus,含经济) |
|---|---|---|---|---|
| P1 早期(1-1~1-3) | 冲 Lv4 | saving | 否 | 纯升级;**主目标尽快向 50 金**(少 D,除非真过不去);买低费过渡 / 早期输出核心稳血存钱(过渡牌见 03 `transition_chars`);有余就升 |
| P1 中期(1-4~1-6) | Lv5-6 | interest | 是(A8 遭遇前) | **攒到 50 吃满 5息是引擎(主目标)**;少 D,靠过渡阵容 / 通用辅助稳血存钱;A8+ 战力不足+遭遇前 → 弃息 D 保血(保血 > 保经济) |
| P1 后期/首领(1-7~1-9) | Lv6 | hold | 首领前是 | 锁血过 P1 首领;观察发牌定 target;维持 50,超额买同费稀释牌池 |
| P2(2-1~2-7) | Lv7→**Lv8** | level | 否 | **2-7 左右升 8 搜核心**;放宽 D 上限 4-6;commit target;攒 50→升 8→用息 D;连胜保连胜 > 吃息 |
| P2 后期/首领 | Lv8 | spend | 是 | 成型;补质量(追 2星核心);血健康吃息,血危花光提质量 |
| P3(3-1~3-5) | Lv9-10 | allin | 是 | 上 9-10 找 5费 + 关键卡追 3星;成型锁血;高难遭遇对策装备;血健康吃息上 9,血危 all-in |
| P3 boss | Lv10 | allin | 否 | 全员成型;装备齐;花光 |

**P1→P2 转 target 时机**:P1 低费过渡保血 → P2 升 8 后看发牌 commit(谁的核心先到 commit 谁)。🟢 economy_research §6 + comp_library。

### §2.2 spend_mode → economy 档位映射

| spend_mode | 语义 | economy_score 权重 | _maybe_sell_for_interest |
|---|---|---|---|
| saving / interest | 攒息(前期 snowball) | economy 权重高 | 正常卖息 |
| level | 升人口(中期) | level 权重高 | 正常 |
| hold | 锁血观望(首领前) | 平衡 | 正常 |
| spend | 花钱提质量(commit / 搜核心) | 平衡偏质量 | 正常 |
| allin | 花光成型(P3 / 危血) | 质量优先 | 跳过 |
| adaptive(fallback) | 平衡 | 平衡 | 正常 |

`comp.node_plan` 可覆盖骨架(快 comp 早 commit / 慢 comp 慢升 8);与 03 §4 `level_plan` 接缝一致(node_plan 含 level_plan + 节点动作)。

## §3 经济线(利息 / 连胜 / 保血切换)

金币三源(🟢):① 战斗奖励;② **利息(每 10金 1息,50 封顶 5息)**;③ 连胜奖励(6 连胜+ 吃满)。

- **连胜中(2胜+)**:保连胜 > 吃息(断连胜亏 > 利息亏)。🟢 巴哈
- **连败(卖血)**:A8 高难慎用;血 >50 继续吃息,血 <40 止血 D。🟡 TFT 经典,货币战争 A8 慎用。
- **奖励/补给节点**:不花钱,留息白嫖。🟢 NGA
- **保血/保经济切换**:A8+ 遭遇前战力不足 → 弃息 D 保血(02 `_phase_weights` HP 危险→保血);血健康 → 保经济(吃息)。**触发条件阵容无关**(按 HP/难度/连胜)。

### HP 区行为(消除 40-50 真空带,对齐 HP_DANGER=40;D-94)

连败 fold 与保血 D 在 HP 40-50 区方向相反(fold 吃息输 / 保血 D 弃息 D)→ 明确各区行为,消除真空带:
- **hp > 50** + plane<3 + 非遭遇前关 → **fold**(吃息攒钱;`STREAK_FOLD_HP=50` **待实现**,02 R2-4b)。
- **hp 40-50** → **buffer**(攒息观望,既不 fold 也不弃息 D,留 buffer 防掉血)。
- **hp < 40**(HP_DANGER)→ **保血 D / allin**(弃息 D 提质量,economy 让位)。

### streak 接线顺序(防反向;D-94)

`read_streak` 已读 magnitude(**胜负语义未核** —— docstring 自承"正=连胜?待核")+ `economy_score` **未消费 `state.streak`**(cw_decisions.py:222 注释"待补 win_streak")。接线两步、**有序**:
1. **先胜负语义核**(read_streak 正负号 = 连胜/连败):🔴 阶段 4 OCR 核。
2. **语义核通过后** → economy_score 消费 state.streak。**未核前只 magnitude 档位不带方向**(防"连败当连胜"反向加成)。

### 7 杠杆落地状态(代码进度)

| 杠杆 | 状态 | 落点 |
|---|---|---|
| 攒 50 吃满息 | ✅ | `INTEREST_WEIGHT=4` + `_maybe_sell_for_interest` |
| 保连胜 > 吃息 | ✅ economy 消费 streak magnitude(2026-08-11,结算「连胜×N」前缀=方向 → economy 对称档位金) | C 杠杆 3(方向驱 plan:保连胜 vs fold,R2-4b)待做 |
| 连败 fold | 🟡 `STREAK_FOLD_HP=50` 待实现 | 02 R2-4b |
| 奖励关白嫖 | 🟡 node_plan 标奖励关 + `_refresh_cap` 收紧 | — |
| 牌池稀释 | 🟡 A4 牌池消耗追踪 | `POOL_COPIES_PER_CARD` 已有(D-93) |
| 保血 D | 🟡 静态 HP<40,无下关遭遇预判 | difficulty + hp_trend OCR(阶段 4) |
| 商店保底 | 🟡 `_refresh_expected_delta` 纳入 | §6 R5-7 |

## §4 骨架 vs 参数分离(设计关键 ★)

**阵容无关骨架(一套,所有 T1 共用)**:
1. 等级曲线驱动(§1 概率表,bwiki 硬数据)。
2. 经济线(§3:存 50 吃息→超额花 level_plan→连胜保连胜→奖励关白嫖)。
3. 保血/保经济切换(02,按 HP/难度/连胜动态)。
4. commit/optionality(12 + F-3 α:r_open≈2/r_close≈12,早灵活晚承诺)。
5. D 牌动态上限(02 `_refresh_cap`:常规≤2,关键回合放宽 4-6)。
6. P1 过渡→P2 commit 结构(§2,过渡牌可参数化)。
7. 牌池操纵(02 A4:买 1星同费非目标→卖,净 0,提目标概率)。
8. 观测驱动反馈(10:OCR 掉血/胜负→`comp_viability`→成型中弱 comp 转型)。

**阵容参数(每 T1 填 `Comp` 数据类,详 03 / comp_library.md)**:
- `factions` + `form_tiers`(4列车 / 3昼神+2鞋 / 6DoT…)。
- `core_chars`(姬子·启行+三月七 / Archer+远坂凛…)。
- `level_plan[Lv]`(该 comp 等级→动作曲线,用 §1 概率表填)。
- `key_equips`(反重力皮靴×2 / 以牙还牙甲×3 / 高周频电锯×2+火力风暴潮…)。
- `form_difficulty`(easy/medium/hard,决定早期偏 comp 强度还是易成型)。
- `countered_by_bosses` + `affix_synergy`(克它的 + **利它的**:正当防卫利燃血 → 遇则升权)。
- `transition_chars`(早期打工牌)+ `shared_chars`(转型复用)+ **通用过渡角色**(不属特定阵营、跨阵容打工 / 组建期支撑:银河学者、夜之半神打工、通用辅助知更鸟/星期日/缇宝/记忆主)。⚠️ **这三类是「灵活 + 前期存钱 + 组建期不掉血」的基础设施** —— 当前 COMP_LIBRARY `transition_chars` 全空、`shared_chars` 稀疏(review HIGH-2)→ optionality / 过渡机制没数据跑不起来。**该填 + 流派扩充调研后补全**(2026-08-11 用户)。

**换 comp 只换参数,骨架不变 → 灵活支持所有 T1**(工程化解法与备选见 D-21)。

**A 轴深度改动(灵活阵容)前置未就绪 → 拆后做(D-94)**:① optionality α(t) 集成进 evaluate(需 P0 实跑校准,02 L903 延后原因);② COMP_LIBRARY 多羁绊改(6+3 / 5+4 双羁绊,非单阵营堆;待 D-17 版本核实锁 V4.4 vs V3.7);③ 每套 comp `level_plan` 填全(现 9 套只列车填);④ ENV affinity 表(投资环境→comp 偏好);⑤ `transition_chars`。前置(P0 游戏验证 + 版本核实)就绪后单独设计。

**⚠️ α(t)/optionality 与 commit 正交(ADR 0096,解 review round-2 HIGH-1)**:α(t)/optionality 在 **eval**(奖 bench 上属 ≥2 comp 的**通用角色**,非 off-direction 核心);commit 在 **maybe_pivot**(target 粘性防振荡)。两者管不同决策,softened prefilter 放过的通用角色正是 optionality 奖的 → 一致,不矛盾。

## §5 T1(A8 顶级)阵容的节奏要点(引 comp_library.md,不重复评级)

> 评级(strength / form_difficulty)单一源在 `data/comp_library.md`(V4.4 🟢 米游社 `76807134`,推翻 V3.7);本文**不重复评级**(避免双源漂移),只列 comp_library 没有的「核心节奏要点」(本骨架视角 = level_plan / 成型标志)。

| 阵容 | 核心节奏要点(level_plan / 成型标志) |
|---|---|
| 列车同行·姬子·启行 | 3费核心,7-8级成型(9人口更优);**4 列车同行=赢一半** |
| 命运圣杯·红A(Archer) | 4个5费;**2-7 到 3-2 上9 找 Archer 锁血,3-5 上10 找2星过遭遇4** |
| 欢愉队 | 双5费双3星;爻光不可替代 |
| 万敌单C(夜神+燃血) | **正当防卫词缀利它**(反伤→燃血→角斗场→更强);成型快 |
| 减益黄泉 | V4.4 配千冶·刃质变 |
| 击破(波提欧/流萤) | 后期;6击破解锁 |
| 贝洛伯格+物质分解液(邪道) | 反重力皮靴×2+分解液「左脚踩右脚」无限叠加;**刚需贝洛伯格星辉** |
| DOT 队(过渡) | 位面1强/P2乏力/P3需转;**低费过渡保血权威** |

详每阵容完整参数(core/form/equip/difficulty/weakness)查 `data/comp_library.md`。本调研在其上补红A运营时机、欢愉/减益细节(后续补 comp_library 字段)。

**辅助 > 非核心羁绊**(🟢 D-17):缇宝/星期日/记忆主/知更鸟 价值高于凑非核心羁绊 → 骨架选 comp 优先抓通用辅助。**跨阵容共用核心**(optionality 用):知更鸟/风堇/布洛妮娅/三月七/银河学者+夜之半神(打工)。

## §6 关键机制利用

- **财富宝钻(团队规模+1)**(🟢 D-19):后台 6 基准 +1 可变(无论是否穿戴);deploy 运行时实测槽位,不硬编码 6。
- **装备(A8 最高杠杆,D-17/D-18)**:每局 ≥3(开局+P1boss+P2boss+奖励/补给);反重力皮靴×2(鞋修:阿雅/桑博/那刻夏)/ 光速螺旋桨(3昼神)/ 高周频电锯+火力风暴潮(通用输出)/ 以牙还牙甲×3(反甲)/ 物质分解液(桑博青雀)/ 掩体生成枪+冷笑话引擎(列车反震)。机制=拖拽(D-18 live 验)。
- **投资环境/策略**:**概念股送装备件**(R5-5)→ 昼神/追击送轮滑鞋(→反重力皮靴)、仙舟送折叠小刀(→高周频电锯)、列车送幸运星 → 选环境优先匹配 target 核心装备合成件。**「净化身心」克 DoT/减益** → 选阵须检测避开(D-17)。
- **商店保底**(R5-7):每第 5次刷新必出 5张同费(采购专员·彩每5/·金每7缩短)→ 关键回合刷到第5次 D 牌估值跳升。
- **砂里淘金电表倒转**(条件触发,识别到才切,非默认追求)。
- **巨星(盛会之星)**:持有盛会之星角色触发;绑 `target.core_chars` 含盛会之星角色,否则按 buff 契合(星期日=前后台强度/知更鸟=幸运一击/黑天鹅=5费增伤)。

## §7 待核实

- 🔴 **升级费用逐级表**:无 web 源,须游戏内「数据银行」图鉴提取(代码估算 6→10 累计≈262 ≈ 攻略270,大致对);文档标待图鉴,不写死(02 `LEVEL_UP_COST_TABLE`)。⚠️ **B/C 轴前置**(node_plan 金门控依赖,现粗估 ±20%)。
- 🟡 **V4.5 meta**:未找到专项,暂沿用 V4.4(本次调研);版本更新重核。
- 🟡 **副本数**:**9 张/种**(D-93 定;5费 NGA 实锤 + 3指数推理 +「每种相同」共识,旧「18」已纠正)。部分场景/效果可能 >9(A4.7 待查)。代码 `POOL_COPIES_PER_CARD=9`(cw_shop_odds)。
- 🟡 **D 牌上限**:攻略共识关键回合放宽 4-6(02 `_refresh_cap` 已动态,实机校准)。

## §8 实施路线(D-94,优先级 + 依赖)

**纯逻辑(可现在做)**:
1. **升级费用表实机核**(B/C 前置):图鉴补权威值(`LEVEL_UP_COST_TABLE` 现粗估 ±20%)→ node_plan 金门控准。🔴 先做。
2. **node_plan 编码**(B):`NodeGoal` + `get_node_goal` + `plan()` gate + `_DEFAULT_NODE_PLAN`(替代纯 `_expected_level` 等级级目标)。✅ **core done(2026-08-11)**:7 条节点规则(P1 saving/interest/hold、P2 level、P3 allin)+ plan() target_level gate + _maybe_sell_for_interest allin/level 跳卖息。**剩余**:spend_mode→economy_score 权重(§2.2,与 _phase_weights 重叠需统一)+ danger_d(卡 OCR)。
3. **streak 接线**(C,**有序**):① 先胜负语义核(read_streak 正负号);② 通过后 economy_score 消费 state.streak(未核前只 magnitude 档位不带方向)。
4. **牌池稀释 + 商店保底**(C):A4 牌池消耗追踪 + `_refresh_expected_delta` 纳入保底。

**需 OCR(阶段 4)**:5. 保血 D 预判(difficulty + hp_trend + node_plan `danger_d`);6. HP 预算动态(PerformanceTracker 接线)。

**A 轴(拆后做,待前置)**:7. optionality 集成(待 P0 游戏验证);8. COMP_LIBRARY 多羁绊改(待 D-17 版本核实锁版本)。

**共同阻塞**:阶段 4 OCR(streak 语义 / difficulty / hp_trend)。纯逻辑 1-4 可现在做;观测驱动 5-6 后做;A 轴 7-8 待前置。**重设计真贯彻三轴,OCR 接线是不可跳过的前置**(README「观测驱动」在没 OCR 前是开环)。

## 来源(证据等级)
- 🟢 [bwiki 货币战争词条](https://wiki.biligame.com/sr/货币战争) — **完整刷新概率表 Lv1-10**(本次新取,level_plan 地基)+ 玩法机制
- 🟢 [官方玩法说明 sr.mihoyo.com/news/160700](https://sr.mihoyo.com/news/160700) — 等级=上阵数 / 利息 / 连胜(机制权威)
- 🟢 [知乎 吃利息 pin/1974931732982690220](https://www.zhihu.com/pin/1974931732982690220)(每10金1息)+ [A8N30 升8时机 zhuanlan/p/2007524819692982561](https://zhuanlan.zhihu.com/p/2007524819692982561)(P2 2-7升8搜核心)
- 🟢 [3DM A8-20 通关 gl/599517](https://shouyou.3dmgame.com/gl/599517.html)(贝洛伯格+分解液+鞋分三层节奏)+ [巴哈 snA=12306](https://forum.gamer.com.tw/C.php?bsn=72822&snA=12306)(保血>利息、断连胜亏>利息亏)
- 🟢 [米游社 V4.4 评级 article/76807134](https://www.miyoushe.com/sr/article/76807134)(T1 评级,推翻 V3.7)+ [姬子·启行 76824096](https://www.miyoushe.com/sr/article/76824096) + [红A 76924524](https://www.miyoushe.com/sr/article/76924524) + [D牌期望 77074467](https://www.miyoushe.com/sr/article/77074467)
- 🟢 [NGA tid=45570754](https://ngabbs.com/read.php?tid=45570754)(奖励关白嫖 / 买同费稀释牌池)+ [tid=45557485](https://ngabbs.com/read.php?tid=45557485)(5费9张实锤)
- 🔴 升级费用逐级表:无 web 源(须游戏内图鉴)
