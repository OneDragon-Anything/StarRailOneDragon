# ADR-0597: T-155 投资选卡新判据(经济引擎档 S2 + 终局对齐源换 D*)——用户裁定「优先经济,然后是终局阵容」落码

- 状态:已实施(commit 候编排者统一门)
- 关联:ADR-0524(定序改形;S2/S3 为 max() 覆盖结构增量,禁新增加减叠加)、ADR-0143/0144(S4 评估分现状保留)、ADR-0144b(env 名跨表污染守卫,S2 谓词受其辖)、ADR-0578(血本位集合排除原样保留,S2 谓词与排除族字段零交集)、ADR-0357/0341/0338(P1 配方锁/资格门;D*① 单判 locked_comp)、ADR-0519(C5 注不修订:CommitSignals 保持纯遥测零消费)、ADR-0593(C1→D4 迁移兼容:新归因串仅观测不进检查器白名单)、`kernel/cw_events.py`(decide_event/is_economy_engine/_invest_d_star)、`strategies/impl/flow.py`(decide_invest 传参)
- 方案正本:`.debug/temp/currency_war/attacks/t155_invest_redesign/方案.md`(v2.1 两轮对抗 + 轻量复核 R1-R3 → v2.2;本 ADR §3 = 其 §3/§4/§5 的落码面)

## 1. 背景与裁定

用户裁定(2026-09-08):「投资选卡→肯定都是为了终局阵容服务,但有些经济效果是非常强的,所以我感觉应该**优先经济,然后是终局阵容**。」病理:decide_event 的 comp 命中层(45×N+20)与 env 阵营 floor 消费 `target_comp`——P1 期它是过渡配方对物化的伪 comp(1-2 位面即换),用「过渡对」对齐「整局运行框架」= 辖域错位(投资环境/策略是整局增益);且经济引擎卡(利息上调 vs 过渡对星徽)会被压过。

## 2. Considered Options

| 方案 | 裁决 | 理由 |
|---|---|---|
| comp-hit 对齐对象 = 过渡对 target_comp(现状) | ✗ | 辖域错位(用户裁定 R2 明文排除);过渡对换线后选卡理由失效 |
| comp-hit 直接删除(纯移除) | ✗ | 丢裁定下半句「然后是终局阵容」;重构 = 对齐对象换 D* |
| D*② = CommitSignals leader(v1 方案) | ✗(对抗审 F1) | 该信号全库唯一喂入=投资两源,消费侧过滤后恒空;且 leader 是未证权重函数,ADR-0519 C5 禁决策消费 |
| D*② = detect_signals ②③④ 资产层信号 | ✓ | 已接线/构造上无投资自指/阈值=游戏定义(羁绊首档);①层(env/strategy 亲和)排除承载反自证 |
| S2 定序 = 跨字段折金基数 | ✗ | 行为依赖字段消费量游戏未定义,拍值违 ADR-0519;定序(存在性)不需要基数 |
| S2 谓词 = 手写名单 | ✗ | 注册表派生优于快照(ADR-0338 先例);字段闭集零名单维护 |
| 经验通道不属经济(v1 候裁 2a 备选) | ✗ | ADR-0131 EconomyEffect docstring 明文含经验 +「经验就是财富」效果原文 XP↔金 1:1 游戏定义兑换 |
| S2 > S1(裁定字面直排) | ✗ | S1 定义型改写**终局预期本身**,不属「对齐既定终局」,与「经济>终局对齐」不冲突(编者预裁①) |

## 3. 已实施架构

### 3.1 新定序结构(N 层;max() 覆盖 + 字典序键,禁加减叠加)

S0 血本位三态触发序(ADR-0578,不动)/ S0' user-forbid −10000(不动)→ S1 定义型 augment 120(不动)→ **S2 经济引擎档(新)**:EconomyEffect 含持续通道字段的策略卡,域带常数 `ECON_ENGINE_BAND_BASE=111` + `SPAN=8`(锚位 = 110 < S2 下界 且 S2 上界 < 120;档内序 = PICK_VALUE 线性归一带内,monotone 定序实现常数)→ **S3 终局对齐族(换源)**:comp-hit 45×N+20 ∩ D* 绑定集、env floor(category 定序档位 70/72/78)触发条件 `_env.faction ∈ D*_factions` → S4 常规评估层(现状保留)。叠加项(克制惩罚 −100/steering ±30/−10000)不动。

### 3.2 S2 谓词 `is_economy_engine`(kernel/cw_events.py)

存在性判据(非幅度):持续通道字段闭集 = 利息(interest_cap_override 有效值口径含 0/interest_flat_per_node)+ 持续金流(gold_per_node/gold_per_boss_node/gold_next_nodes_amount+count 配对/gold_per_level_up/gold_per_three_5cost/gold_per_2star2cost_merge/gold_per_3star_merge/win_reward_mult/sell_price_mult)+ 刷新(free_refresh_per_node/free_refresh_burst/refresh_surprise_every/refresh_per_compose/refresh_free_chance/refresh_shop_rewrite_every_3cost)+ 经验(xp_per_refresh/xp_per_node/xp_buy_cost_discount/xp_click_discount_from_level+at 配对/xp_instant)。**不入集**:一次性金族(instant_gold/gold_at_node/gold_at_level/gold_per_hp_lost_now,F3 结构界:时点触发一律不入)、期权/难度族、血本位族(与 S2 零交集,直调复核)、补偿型 gold_per_20hp_lost;孪生素数(全默认空壳)自然 miss。直算对账:命中 38 条(与方案申报数一致;去经验独占 34)。

**落位声明(B1,落地审)**:谓词与闭集常量落决策层 cw_events(与 decide_event 判据同域)而非注册表 cw_investments——它承载「哪些字段算持续通道」的**决策语义**,cw_investments 只管 EconomyEffect 字段定义单一源,非事实双源(推导出处 = 方案 §3.1 分族表,本节为落码载体)。已知漂移面:未来注册表新增语义属持续通道的字段时闭集不自动纳入 → 该卡静默落 S4;枚举守卫(「EconomyEffect 全字段须被闭集∪显式排除覆盖」)挂后续批候选(用户「不新增测试锁」指令辖内本批不落)。

### 3.3 D* 级联 `_invest_d_star`(单规则零阶段特判)

①终局锁线:`locked_comp` 非空取其绑定集(decide_invest 从意向状态解析传入;demoted_endgame 帧 D*=∅——降格终局无对齐语义,detect_signals 不查降格标志,此短路必要)→ ②资产层信号:kernel 内直算 `detect_signals(state)` ②③④(①层 env/strategy 亲和排除 = 反投资自证),继承 **evicted 过滤**(「等同信号未发生」契约的消费面镜像,cw_intention:1189 同款)+ **weak_planes 弱面过滤**(:1197 同款),取 (layer 升序, weight 降序, comp_name 字典序) 最优线 → ③皆空 D*=∅ → S3 全体 N=0,候选落 S2/S4,不引入兜底方向。**decide_event 签名**:target_comp 参数移除(其唯一消费即被移除的过渡对命中;生产调用面 grep 复核仅 decide_invest 一处传参 + operations 防御路径两处不传),增可选参数组 `locked_comp/demoted_endgame/evicted`(kernel 不引 session/registry,纯函数守恒);防御路径(stub state)D* 信号恒空 → 落 S2/S4,与现行防御行为同构。

### 3.4 意向层过滤门·五门裁决(§5.1.1;轻量复核 R1 补第五门)

evicted **必须继承**(信号本体契约)/ weak_planes **继承**(注册表自注位面死路)/ P2 供给可行性缓锁门 **不继承**(辖锁线动作资格非方向证据;供给高频波动传导违稳定性;需 session+registry,kernel 不可达)/ H1 锁线环境门 **不继承**(承重 = 语义辖域+词缀噪声,纯度论点只属缓锁门——轻量复核 R2 勘误)/ P1 ①类资格过滤(:1443-1445)**不继承**(辖 P1 锁线证据资格;§5.5 P1 密度申报建立在过渡兼容线③④照发上,继承即塌缩;终局专属线的 P1 拦截由 detect_signals 发射侧 `_p1_gate_blocks` 承载)。升级路径观测键预登记 = 方案 §7.2(R3:dstar_pick_in_supply_gap_rate 等三键)。

### 3.5 其余面

CommitSignals 零消费零改(喂入保留纯遥测;反自馈由 D*② ①层排除承载)/ detect_signals 与 update_intention 本体零改 / decide_supply/encounter/megastar/partner/star_tome/wish_trial/planner 保留族不动(资产获取面/风险面不在裁定辖域)。新归因串 `econ-engine`/`align×N`/`align-locked`/`align-signal` 仅观测归因(来源级标识 = floor 分 locked/signal)。

## 4. 边界申报

- **decide_invest D* 解析面**:flow 侧 `_ensure_intention` 惰性就位后读 ist(locked_comp/demoted_endgame/evicted 同源);env kind 开局屏 D* 通常 ∅ → 落 env 裸分(行为同旧)。
- **OCR 形变名**:S2 谓词只辖精确注册名命中(`_st is not None`);形变名沿 eval-lcs 裸分现状(economy 修饰不可靠,ADR-0143 同判),与血本位候选级解析的覆盖面差异如实申报。
- **门 2 观测键接线**:dstar_* 三键归门 2 观测批(本批 sim/ 禁碰,如实留空);本批初阶观测面 = 选卡归因串。
- **R5 处置记录(轻量复核 R5/落地审 B4;编排者指令核后登记)**:flow 侧 evicted **生产接线已落**(flow.decide_invest 读 ist.evicted 传 kernel,本批 §3.3);**接线断言未落**——d4ce3989 下沉臂落的是 decide_invest→decide_event 调用链(spy 只记录 options+pick,kwargs 空传也绿,不构成传参断言,落地审 B4 核实与本批复核一致)。登记挂账:flow 侧接线断言(断言 decide_event 收到 evicted == ist.evicted)归门 2 观测批或下批顺手(用户「不新增测试锁」指令辖内本批不落)。
- **文档三同步(落地审 M2,本批补齐)**:13_pick_family.md §1 decide_invest 行已按新签名/D* 语义改写(并补 16 号稿 §5 既往挂账的定形注)、16 号稿补 §1.9 增量行(S2/S3 = 0524 定序框架增量)、strategy as-built invest 段 = strategy/ 树已塌缩(README 历史注记),invest as-built 现居 13 号篇+16 号稿两处,均已随本批更新;flow/README.md pick 族行为纯指针无需改。

## 5. 验证

- **双臂同 seed 配对 A/B**(任务书 ①;seed 810000-810023,n=24/臂,invest=True sink 基线臂 d4ce3989):真改判 4 处(3 局)——comp-hit×1(过渡对)→ D* 对齐 1 处(seed 810018:爆晶矿·彩→贝洛伯格星徽套组 align×1)、经济档换卡 1 处(810021:金币大使叽米→采购专员·金 econ-engine)、对齐失效回落 2 处;同卡归因换挡 13 条(eval→econ-engine,新档位可见性)。经济档选项占比 0→19.1%;**[28] 出口金 60.46→60.46(净滞留同)、存活率 1.0→1.0、平均末 HP 28.25→28.25、[13] formed_stop 行 0→0、P1 锁定轮 3.79→3.79、通关门 boss 胜 3→3/24 局**(四条验收线逐位不降)。
- **注册表直调抽验**(任务书 ③):S2 命中 38 ✓;点名 16 张(F3 界/一次性/引擎/空壳)全对;血本位 ∩ S2 = ∅;D* 级联三态 + evicted/weak_planes/①层排除逐门 ✓。
- **测试**:CW 快速层全绿(既有锁重推处置 7 支 + 方案 §8.3 预登记的 D* 级联锁 1 支;落地审 M1 措辞勘误——原「零新增锁」申报与 +1 新测试函数事实不符,该函数内容 = 方案 §8.3 明文计划的「新增 D* 级联锁」(`test_decide_event_d_star_cascade`),编排者追认保留)。重推 7 支 = test_cw_decisions 6 支(comp_match_wins→S3/D* 语义锁、augment_dominance/env_pick_value 对位换 D* 构造、fallback_lexicographic/priority_boost/rarity_penalty 前提对位换非引擎卡或合成注入)+ test_cw_investment spy 签名 **kwargs 透传;`ruff check` 全绿。
- **A/B 时效注(落地审 B5)**:treatment 批采数后本批有后置编辑(注释/文档面),sim 可见行为复跑抽验 3/24 seed(810014/810018/810021)逐位一致;四验收线判据来自双臂 JSON 自身逐局比对(24/24 核过),抽验口径如实记录。
- commit 归编排者(逐文件点名:cw_events.py/flow.py/本 ADR/INDEX 行/测试仓 test_cw_decisions.py+test_cw_investment.py 两文件;残余他批在飞面禁卷入,M3)。
