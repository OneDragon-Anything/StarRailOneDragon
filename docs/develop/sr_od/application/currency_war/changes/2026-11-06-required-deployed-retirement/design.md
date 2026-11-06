# required-deployed-retirement 迭代设计（总纲）

## 0. 元信息

- 迭代目标：`Comp.required_deployed` 整字段退役（用户裁定，2026-11-05/06 字段排查会话五轮论证链，见 §1）——「点名件在场」判据改由锚体系承载（终局）/core 直接承载（过渡），部署侧灭零改评分折条。实例字段 10 → 9。
- 状态：定稿（对抗轮 10 攻击点全处置——阻断 1〔B1 跨线翻转证伪 → 方案重设计为两层支配编码〕/应修 4/可选 5，明细见 attack.md）。
- 文档清单：（无详设——单文档方案）。

## 1. 问题与动机（五轮论证链，用户裁定口径）

- 论证链（每环均已代码核实）：
  1. **锁线不看它**：line_select 证据分八分量无 required——锁线链路与该字段无关；
  2. **凑档不需要它**：faction_reqs 档位完成度已进部署 L1 评分（列车 4 板 4/4 > 列车 3 板 3/4），枚举取高分天然凑档；
  3. **优先级知识已存在但评分未消费**：希儿 ∈ core（rank 0）vs 银狼圈外——member_rank 只进了圈人池序与卖牌让位序，**选板终评（L1/L2/L3）无成员优先级项**——「同分板对」（无引擎板与有引擎板羁绊计数全同、L1 同分）只能靠 required 灭零这个**评分外硬约束补丁**分辨——补丁的根源是评分维度缺口，不是知识缺失；
  4. **过渡侧是恒等拷贝**：10/10 条 `required_deployed ≡ core_chars`（生成器两行 + 测试锁不变量）——「点名件全在板」就是「core 全在板」，字段只是数据拷贝；
  5. **买牌/部署均不依赖 form_progress**：fp 的真实消费 = 过渡锁定（cw_intention:577）、出战就绪配方分支（readiness_form_ok）、commit 时窗（equip_env）、穿戴/面板/sim 特征——这些消费需要「点名在板」合取支，但合取支的**数据源**不必是独立字段。
- 根因归层：required_deployed 是 or_reqs 退役时「希儿在场」合取支的搬迁安置 + 过渡生成器顺手复用的容器——历史迁移产物，非最优设计；「优先级进评分」与「锚体系承载点名件」两个既有机制均可替代其全部职能。
- 解决到哪：字段退役；fp 折法源替换（点名件 = 锚/core 统一表达式）；部署灭零改评分折条；全链测试/正本同步。
- 明确不解决（外溢面）：
  - **评分锚与聚类锚的分歧线**（火花星间旅人：评分锚花火 vs 聚类锚火花）：fp/部署扣分的点名件统一用 `carry_anchor`（kernel 单源——form_progress 在 kernel，不得 import 策略层的 rating_anchor，分层约束）；分歧线的行为影响如实申报（§2.3），若实战证明该线点名应跟评分锚，后续在锚体系内另裁；
  - 部署评分是否进一步接 member_rank 全序（逐角色优先级分）——本迭代只接「锚在场折条」（rank 0 的具名化），全序接入留策略侧立项。

## 2. 方案

### 2.1 核心机制：fp 折法源替换（cw_comps.form_progress）

折法分支 `for name in comp.required_deployed` 替换为**点名件统一表达式**：

```python
anchor = carry_anchor(comp)
named = (anchor,) if anchor else tuple(comp.core_chars)
```

- **终局条目**：plaza_carry 非空或 fallback 命中 → 点名件 = 单锚（21/21 线有锚——fallback 补全后恒非空，脚本+测试守卫双确认）；
- **过渡条目**：无 plaza_carry、fallback 不含过渡条目名 → 点名件 = core 全员——与原 `required = tuple(core)` 逐位等价；
- **空羁绊线守卫形态钉死**（对抗轮 G1）：现码早退是复合条件 `if not core and not required`（or_reqs 时代残留）——机械替换后 named=('白厄',) 非空将使守卫失效，白厄 fp 从恒 0 变「白厄在板 0/1」→ 裸白厄板 fp=1.0 → 出战就绪误放行（「前中期上 = 裸装白厄送战损」被破坏）。**新守卫 = `if not comp.core_faction_reqs: return 0.0`**（档 0 空 → 恒 0，与 required 存在与否解耦）；
- **两前提 import 期断言正式化**（对抗轮 A2）：建库校验补「COMP_LIBRARY 全线 carry_anchor 非空」与「TRANSITION_LIBRARY 全条目 carry_anchor 为空」（现状由结构保证——combo 名含 '+'、fallback 键不含——正式化为防线防手改漂移）；
- fp 本体保持加权平均折法（named 作为普通一支进 (Σ档位+named)/(n+1)）：readiness（fp≥1.0 配方完备）语义自然（缺锚板 fp<1.0 不完备 ✓）、commit 时窗数值连续；跨线选择的灭零等价由部署 L1 两层编码承载（§2.2——fp 与 selection_score 本是两台机器，折法各异是既有结构）；
- 无类型分支（终局/过渡同一表达式）、无跨层 import（carry_anchor 本就在 cw_comps）。

单一源契约更新：`fp = 1.0 ⟺ 档 0 全键达标 ∧ 点名件在场`（named 语义随源替换更新）。**锚源敏感申报**（对抗轮 A3）：named 的锚源是统计字段（plaza_carry 聚类 + fallback）——版本重跑换锚 → fp/锁定/部署语义随之变（carry_anchor 体系固有性质，fp 新增为敏感消费之一，如实登记）。

### 2.2 部署侧改造（deploy_search）

1. **:241-244 灭零特判删除** → selection_score 的 L1 改**两层支配编码**（对抗轮 B1 修正——原「n/(n+1) 折条」方案被跨线反例证伪：希儿线满档缺锚板（旧 L1=0）可赢过万敌线部分板+万敌在场（旧 0.583e9）——满羁绊无引擎板胜出恰是原灭零要防的形态。软化折条只证了「完备板>缺锚板」单向命题，跨线同池 argmax 翻转不可接受）。**实现规格**（轮 2 B1 钉死）：新常量对 `_L1_NAMED_SCALE = 1e9` / `_L1_TIER_SCALE = 1e8`（L1 域顶 1.1e9，原 `_L1_SCALE` 注释同步）；`named_rate = |named ∩ names| / |named|` **独立分子分母**（不进现有 l1_num/l1_den 加权平均）；`l1 = named_rate × 1e9 + tier_rate × 1e8`——层间 10 倍域差保证任何满点名件板严格赢任何缺点名件板（轮 1 反例形态实测消除），层内档位完成度自由比较。白厄 members 承载支（:264-271，仅锁定窗）**保持 1e9 域原样**（锁定窗单线无跨线比较面，绝对值归一免动 margin 遥测/快照域）；白厄不挂 named 层（members 支分子已含锚，挂则双计——轮 1 B2）；margin 遥测 layer_gap 数值语义变两层混合差，注记随批。空羁绊线未锁定窗白厄候选 L1 保持 0（members 支仅锁定窗）——与过渡缺 core 板的「并列垫底（rng 可翻盘）」变「严格垫底」（轮 2 C1 申报）；
2. **:487/:496 圈人排序**：`required(0) > core(1) > 其余(2)` 的 required 层 → 锚层（`u.char_id == carry_anchor(comp)` 排位 0）。希儿线等价（锚=希儿）；过渡条目活跃窗（未锁定）**分层整体不触发**（`_line_rank` 未锁定窗恒 return 2，req/core 取自 locked_comp——轮 2 表述修正：零行为差结论不变、原「锚空不命中」论据不准），锁定窗 core 层承载。**第三情形申报**（对抗轮 B4）：20 条非希儿终局线锁定窗**新增** rank-0 锚（现状 required=() 无 rank-0）→ 池序/前缀骨架在锚与其他件的相对位变化（锚优先圈入骨架——行为增强方向，与 §2.3① 同理）。锚层可达性当前全库成立（轮 2 全库扫描「锚层不可达线」=0——火花线经 flows 欢愉命中档 0 键）；import 期断言补第三条「锚 ∈ members ∨ 锚羁绊 ∩ 档 0 键 ≠ ∅」防数据漂移静默空转（轮 2 E1）。

### 2.3 行为变化申报（不做 A/B 模拟对照，沿 or-reqs-retirement 先例：实机首局观察记遗留待办）

| # | 变化 | 帧域与方向 |
|---|---|---|
| ① | **全 21 线新增「缺锚 fp 降折条」**（现状仅希儿线有 required 折条）| 缺锚帧（如缺姬子·启行的列车板）fp 由档位满值 1.0 降为 n/(n+1)——配方完备（fp≥1.0）从「档位达标」收紧为「档位达标 ∧ 锚在场」，commit 时窗（0<fp<0.4）数值同步变化（对抗轮实例：银枝群攻单键线——群 2/3 无锚板 fp 0.667→0.333 落入 hold 窗、仅锚在板板 0→0.5 翻为 committed，双向翻转可达）。**方向 = 行为增强**（引擎不在场不该判完备/出战——与希儿线现状保护同构的全线推广）；白厄（档 0 空）恒 0 不变 |
| ② | 部署缺锚从灭零改 L1 两层编码的第一层 | **等价域 = 原灭零的防形态保证**（「满点名件板恒压缺点名件板」跨线 argmax 恢复——轮 1 B1 反例消除）。两层编码同时引入三处新比较序（轮 2 自审 A + 外部 A2 合并申报，均属 ① 的部署投影、方向一致）：(i) 跨域——部分点名件过渡板（named_rate=0.5 → 5e8 级）现压缺锚终局板（tier×10⁸），旧序终局板赢（过渡灭零）；(ii) **对称翻转**——希儿线缺锚板（旧恒 0 灭零）新 1e8 级现压非希儿线缺锚板（2e7 级）——原灭零过严面（希儿缺锚板输给任何板）解除，方向 = 引擎在场优先的统一序；(iii) 同域板间序——两板同缺点名件时序从 L2/L3 决序变 tier 层先决。过渡条目折权重（m=2..5 名 core 占分母可达 50%）同编码处理；层间严格性的数据边界 = 过渡 core 规模 m ≤ 9（m=10 平局、m≥11 翻转——现状 m∈{1..5}，建库校验补 m≤9 断言，轮 2 B2） |
| ③ | 过渡侧逐位等价 | named(core) ≡ 原 required(core)，fp/锁定判据零差 |
| ④ | 希儿线逐位等价 | named=(希儿,) ≡ 原 required=(希儿,) |
| ⑤ | 火花线点名件 = 火花（聚类锚） | 现状该线 required 空、无点名保护；退役后获得锚折条（锚=火花）——fp/部署在缺火花帧收紧。评分锚（花火）分歧如实申报，归 §1 外溢 |
| ⑥ | sim 特征 `final_form_progress` 数值变化 | 遥测连续性断点登记（①的同源投影）；sim 战力模型如有依赖该特征的阈值行为，建模侧自查 |

### 2.4 系统级变化清单

1. **字段删除**：`Comp.required_deployed`（定义 :133-137、终局数据 :578 希儿行、生成器填充 :1168）+ 墓碑注记（沿 equip_taboos 先例）；
2. **fp 折法**：cw_comps.form_progress 的 required 分支 → named 统一表达式（§2.1）；docstring 契约措辞同步；
3. **部署**：deploy_search :241/:487/:496 三处读法改造（§2.2）；
4. **生成器**：`_build_transition_combos` 删 `required_deployed=tuple(core)` 行；`_validate_transition_combos` 不变（无 required 校验）；
5. **测试同步**（sr-od-test 显式路径 grep 全量处置）：
   - test_cw_comps:268（锁 required=('希儿',) 断言）→ 删/改锁 named 语义；
   - test_cw_transition_library:74（required == core 不变量）→ 删（字段消失，不变量随之消灭）；
   - test_deploy_search:122（missing_zeroes_l1）→ 改写为「两层编码第一层支配」断言（锁 ② 的跨线灭零等价语义）；
   - test_select_deployment:54（构造 required_deployed=('瓦尔特','杰帕德') 桩）→ 桩改造（构造锚或 core 承载）；
   - **test_cw_batch_stats_p1_proxy:160（getattr 字符串形态读 required_deployed——前判例：`.field` 模式 grep 搜不到，必须显式路径字符串搜）**；
   - fp 曲线测试（test_cw_comps 希儿 fp 五值/`:271-274`）：折条等价 → 数值不变（④），断言保留；
   - **test_faction_migration_identity**（对抗轮 F1 补列：快照 JSON 逐位断言 65 板 × 21 线的 fp+L1——改后大面积红，含 half/mixed 板缺锚帧与火花线 formed 板 fp 1.0→0.5〔火花∉core 全库唯一构局〕）：处置 = 重生成快照（gen_faction_snapshots.py）+ 测试 docstring 注明「required-deployed-retirement 后基线」——快照的回归基线作用随迭代推进换代（faction_reqs 迁移时代语义退役），非覆盖漂移；
6. **sim 语料**（对抗轮 E1）：corpus_extract.py 的 `EXTRACTOR_VERSION` 自述「特征语义变更时递增」——fp 语义变（含 best_line argmax→core_star_depth 连带漂移）应**递增版本号 + 语料重建**；win_model M1 与 ab_judge 已核实不消费 fp（无代码级阈值行为）；
7. **正本**：12 号篇（形态端口措辞——required 承载说明改锚/core）、10 号稿存留表（删 required_deployed）、24 号部署篇（L1 键组 + 灭零措辞）、comp-definition skill（「成型」族措辞「AND 档 + required 在板」→「AND 档 + 点名件（锚/core）」）；**proofs/p87**（对抗轮补：引用该字段）加退役指针注记（沿 P42 横幅先例，留档豁免）。

### 2.5 知识归宿登记

| 知识 | 归宿 |
|---|---|
| 「引擎必须在场」（终局逐线） | carry_anchor 体系（plaza_carry + CARRY_ANCHOR_FALLBACK——已有，零新增数据；分歧线外溢 §1） |
| 「点名件整体在板」（过渡组合） | core_chars 直接承载（fp 统一表达式的回落半边） |
| 「评分外硬约束 = 补丁形态」教训 | 本迭代判例（与「即时锁退役分数说话」「key_items 退役证据分承载」同链第三件——评分维度缺口应补评分项，不应造字段旁路） |

### 2.6 接口契约（破坏面）

- `Comp.required_deployed` 属性消失：生产消费 2 文件（cw_comps / deploy_search——对抗轮 D1 更正：cw_intention 消费的是 fp 值非字段，无需改写；含 getattr 字符串形态清查）随批改写；grep 清零（src + sr-od-test **显式路径** + tools）为验收判据，墓碑注记豁免；
- `form_progress` 签名不变、返回值语义（named 折条）按 §2.3 申报变化；下游（readiness_form_ok/commit 门/穿戴/sim 特征）零改动承接；
- `carry_anchor` 消费面扩大（fp/部署新增两个读点）——它已有 5 处统一读口先例，无新契约。锚费用窗口事实（对抗轮 C2 修正）：16/21 锚 ≤ 3 费（列车锚姬子·启行 = 3 费非 5 费），fp 收紧在锁定后期的实际暴露面中庸。

### 2.7 验收

- grep `required_deployed`（三域：src / sr-od-test 显式 / tools）零命中（墓碑豁免）；
- fp 数值回归：希儿线/过渡条目逐位等价断言（④③）+ 空羁绊线恒 0 断言（G1 新守卫）；
- L1 跨线断言：缺锚板严格输给任何满锚板（两层支配编码的层间严格性——锁 ② 灭零等价）；
- test_faction_migration_identity 快照重生成后全绿；
- L1 快速集全绿（受影响域点名 + 全量待并行批稳定后补跑，沿 comp-data-row-cleanup 先例登记）。
