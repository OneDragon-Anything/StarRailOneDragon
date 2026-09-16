# 备战契约接口收口为单动作 · 对抗审查报告(attack2)

> 审查对象:本目录 README.md / design.md / landing.md(迭代设计三件)+ `strategies/impl/cw_strategy.py::CwStrategy.decide_prep_screen` docstring(工作区未提交修改)+ `strategy-docs/README.md`「策略↔流程契约」行(工作区未提交修改)。行号为当前工作区行号,漂移以符号定位为准。所有数值/引文/码点均直调代码与正本文档复核,未转述。

## 结论

发现 5 条:高 0 / 中 3 / 低 2。设计核心主张逐项直调核实全部成立(接口语义码点、None 通道三依据、决策核零改动论证、行为零变化论证、sim/replay 零影响、测试锁影响面、正本更新清单 11 行引文、两处 docstring/文档指针修改)。发现集中在**正本更新清单与死口径收敛的完备性缺口**——不导致行为变更,但会导致收尾后正本/注释残留自相矛盾的旧口径,且部分缺口是机械闭域检查的结构性盲区,验收时发现不了。

## 发现清单

### F1(中)正本更新清单漏挂 flow/README.md §1 架构图中跨行拆开的「决策取首项」

- 位置:`flow/README.md` L17-18(架构图画面指挥行:`…③-⑤单动作循环:决策取` / `│ 首项→期望态计算→执行…`,「取首项」被框图换行拆成两行);landing.md 正本更新清单 #1 只挂「§1 架构头注(L23 区域)」。
- 攻击过程:landing 3.3 闭域检查 = grep「取首项 / 空批 / list[PrepAction]」。grep 按单行匹配,L17 末尾「决策取」与 L18 开头「首项」跨行拆分,三个关键词对该处**全部不命中**。收口后「决策取首项」表述过期(决策 = 接口恰返回一个动作/None,消费端不再有取首项步骤),将成为清单外 stale 点,且收尾机械检查对其盲。
- 修正方向:清单 #1 范围由「L23 区域」扩为「§1 架构图画面指挥行(L17-18)与策略步进行行(L23)」;闭域检查关键词「取首项」改为「首项」(单字面即可命中跨行后的 L18),并注明框图区域需人工复核。

### F2(中)死口径注释收敛枚举不完备(四处),实现者将撞到设计未回答的「改不改」

design §2.2 对消费端声明了「相邻死口径注释同批收敛」(点名空批分支「契约 §4」注释与 lifecycle docstring「空批」句),§2.3 对 bridge docstring 声明改写「输出形状句 + 帧稳定截断批次表述」。但直调发现同批应收敛的死口径共四处未被任何一条覆盖:

1. `cw_screen_prep.py` L2007-2008(主循环 `run` 决策段头注释块):「三遍编排序保持(决策核输出逐帧取首项 = 单动作选择序…)」——收口后消费端不再取首项,表述过期。该注释块在 §2.2 码块替换段(L2028-2043)之外,「相邻死口径注释」枚举未含它。(同块 L2010-2011「逻辑态未建模的动作同判保守回退」系 R9 已删除分支的死口径,属既有遗留,建议顺带收敛。)
2. `bridge.py` L109(`MandateV1Strategy.decide_prep_screen` docstring 首句):「(契约 v1/v2 接口;序列决策契约正本 = flow/action_exec.md §1)」——双重死口径:契约 v1/v2 工作副本已灭失(`entry.py` L17-18 自证 CONTRACT_SERIES_DECISION.md 灭失);action_exec.md §1 实际内容 = 词表与注册表,不是「序列决策契约正本」,且「序列决策契约」本身随本批收口消亡。该句不属「输出形状句」,改写范围声明未覆盖。
3. `bridge.py` L114-115:「经帧稳定截断(契约 §3.2 逐类判 + §3.3 fail-closed)」——§3.2/§3.3 为已灭失契约工作副本的节号引用。若按「批次表述收敛」整句重写可自然消除,但设计稿未明说该括号引用的去留。
4. `bridge.py` L117:「入口内务 = 结算惰性 drain + 备战帧代次消费…」——「结算惰性 drain」已删除(`flow.py` `_consume_prep_direction_frame` docstring:「原前置的结算槽 drain 已删除」;实码 L127 只调帧代次消费)。死口径在改写范围声明之外。

影响:违反迭代规范「实现者无需再设计」(写作硬规则 2)——实现者改写 docstring 时对这四处要么自行拍板(绕过审查)、要么原样留下(收口后代码内残留与新契约矛盾的表述);且 landing 3.1 验收凭据「grep 复核(src 与消费端无残留 list 形状/旧文案)」未写死关键词集,上述四处均可能漏检。
修正方向:design §2.2/§2.3 点名四处一并收敛(与消费端「契约 §4」同款处置:灭失副本引用改语义表述或改指现行正本节);landing 3.1 验收凭据写死 grep 关键词集(建议:`取首项`/`契约 §`/`list[` 作用于三文件改动面)。

### F3(中)正本更新清单与闭域检查均到不了 projection_contract.md L89 的「族 B PrepAction 列表」死类名

- 位置:`flow/projection_contract.md` L89(§4.1 备战线数据流时间线):「决策(entry.emit 三遍编排;动作产出 = 族 B PrepAction 列表)」——与清单 #3 要改的 L90 同图相邻行。
- 攻击过程:①`PrepAction` 类已不存在(统一词表批后基类更名 `CwAction`,宿主 `kernel/cw_prep_actions.py` 头注自证「原为族 B 备战动作词表宿主」),「族 B PrepAction」双重死口径;②闭域三关键词逐一验证:「取首项」不在该行、「空批」不在该行、「list[PrepAction]」字面不命中「族 B PrepAction 列表」(裸名形态)——机械闭域检查对它结构性失效;③3.3 完成判据含「正本与实现一致」,该行是其已知反例,但清单未列、grep 拦不住,验收凭据(「grep 输出 + 文档对照 review」)下易被「grep 零命中 = 收敛完成」误读。stale 本体系统一词表批既有债,非本批新造成,但清单 #2/#7 已将同型死名(`list[PrepAction]`)的收敛划入本批义务域,同域相邻行的漏挂属清单完备性缺口。
- 修正方向:清单 #3 范围扩为「L89-90 区域」;闭域检查对「PrepAction」裸名加人工复核注记(不可直接 grep 裸名——`PrepActionExecutor` 等合法名会大量误中,需排除执行器名后复核)。

### F4(低)design §2.3「mandate.py 2 处截断点语义耦合注释申报」计数口径未声明

- 位置:design.md §2.3 理由 2。
- 攻击过程:grep mandate.py 中含 `truncate_frame_stable`/`classify_frame_stability` 的注释块实为 3 处(L1299 凑息卖接线位申报、L1753 影子面不辖申报、L1951-1957 M7 回排段说明)。按「独立申报注释」口径数 = 2(L1299/L1753,L1951-1957 算调用点就地说明),按关键词命中数 = 3。「4 处真实调用」主张本身核实成立(bridge.py L290 + entry.py L297/L1157 + mandate.py L1965),此条仅计数口径含糊,不影响「耦合成面」的论证结论。
- 修正方向:改「3 处」或标注计数口径(「独立申报注释 2 处 + 调用点说明 1 处」)。

### F5(低)design §2.6 判读锚点 2 的「改前局」基线来源未指明

- 位置:design.md §2.6 锚点 2:「备战发射分键分布…与改前局同型」。
- 攻击过程:「改前局」未写明来源(专门先跑一局改前基线局,还是取遥测账本历史局)。strategy-work §4 的「改前基线→改后对照」纪律语境是 sim 批;实机烟雾局此处是流程回归哨兵,基线取法是实现/判读者要自行选择的面。
- 修正方向:写死基线来源,如「对照 = 遥测账本最近数局备战 `prep_*`/`emitter_*` 分键分布」。

## 零发现的面(逐面列,含直调码点)

1. **design 引用的正本句逐条核(存在性与转述准确性)**:op-layer.md §1.1 分域表述句(L21,design §2.1 依据 1 逐字核对一致)、§1.4 恒可用终结(L37)、§1.3 守卫断言(L31)、§4 次门(L153「cw_replay --diff 只重放商店决策面」);flow/README.md §2 契约形状成员 13(L40)、§2.1 管理器行封闭集 {mandate_v1}(L47)、§2.2 备战接口行(L64)与成员数句(L84)、§2.3 sim 消费面注记(L91)、§2.2 历史注 L82 生命周期机制四件;cw_strategy.py L111-115 B4 条款(基类 create_state 缺省 None);strategy-docs/26_battle_settlement.md §1 出战标准;strategy-work §4(L51 A/B 可观测性声明、L55 实机/sim 分工);CW skill SKILL.md「测试分层」行(L1 快速集命令真实存在)。
2. **消费端两处决策循环实态**(`cw_screen_prep.py`):`run` 主循环 L2025-2121 与 `lifecycle_decision_cycle` L2229 起逐段对——decide 调用点 L2029/L2234(与 design「~L2029/~L2234」吻合)、try/except 异常包装两处同构、F3 形状校验 `not isinstance(list) or not all(isinstance(a, CwAction))`、空批 `round_success('空批(本帧无动作),交回外循环重观察', wait=1.0)` 两处、取首项 `actions[0]` 两处——§2.2 before 事实与拟改码块逐行可对,新码块可直接落码,异常包装/None 分支/wait 值/文案申报(§2.6 两处 detail 与 F3 文案)与实码一致。
3. **None 通道三依据**:依据 1(正本句)见面 1;依据 2——`bridge.py::decide_from_turn` L259-291 仍返回 list、`entry.emit` ⑥ 无动作补 StartBattle(L936-944 实码)、`truncate_frame_stable` unknown 空返回边 L296-300 实码存在、分类表实数 17 类(_TRUNCATION_POINTS 11 + _TERMINAL 1 + _CONTINUE 1 + _CONDITIONAL 4,L200-217),恰全覆盖 entry import 的 17 个动作类,「不可达」论证成立(entry.py 头注 L15 的「18 类」为批 2a 前旧数,与 design 的 17 不冲突——design 取的是实码数,正确);依据 3(出战标准非缺省替身)见 26 号篇。
4. **决策核零改动论证(§2.3 理由 1/2)**:`_merge_ev_before_frame_end` L1140-1160(EV 卖面插首个截断点/终点之前,R197 症1)实码;帧稳定分类/截断 mandate_v1 包内真实调用恰 4 处(见 F4 行);M7 发射序回排 L1958-1970 实码。
5. **sim/replay 零影响(§2.4)**:src 全树 grep `decide_prep_screen`(13 处,零 sim/ 目录命中)与 `decide_from_turn`(真实调用仅 bridge.py L129 一处)——prep 面在 sim 无消费点;`tools/cw/replay_to_md.py` 零契约接口调用(L536 确为 decisions 记录流渲染备战/商店/补给三类 op 段)。
6. **测试与锁影响面(§2.5)**:sr-od-test 全仓 grep `decide_prep_screen` 仅 `test_cw_p2_blood_band.py` L215-218 abstract 桩子类(`*a, **kw`,形状免疫);全仓 grep「空批/非 list/list[CwAction]/actions[0]/策略输出非」零命中——「在册锁零更新义务」「无工具/测试/哨兵依赖旧文案」均成立。
7. **审查对象 2:`decide_prep_screen` docstring as-built 十句逐句核**——①返回 `list[CwAction]` + 波批遗留定性(签名 L121-122;单动作循环 2026-09-06 落码,flow/README §1 头注)✓;②输入 session 黑板 `prep_obs_frame`(`cw_strategy_session.py` L201-206)+ 跨步状态经 strategy_state 挂 session ✓;③两处消费循环同构取首项 ✓;④列表 = 三遍编排发射组织、尾部动作生产不消费(emit→truncate→[0],见面 3/4)✓;⑤空序列合法 + stall 兜底归外循环(L2038-2041)✓;⑥画面转移走 OpenShop/StartBattle 终结(prep.md §5)✓;⑦已退役语义 + `flow/action_exec.md` §2(机械执行无成败回执)/§3(无 fail-stop/恢复原语)指向真实且内容吻合 ✓;⑧帧稳定分类在决策核内辖发射组织(entry.py 实码)✓;⑨生命周期机制四件归流程侧(与 flow/README §2.2 L82 同清单)✓;⑩观察帧缺失即抛错(bridge L121-125 ValueError 实码)✓。注释规范合规(引用均为持久索引,无变更史叙事)。git diff 确认:HEAD 版为「序列契约 v1(2026-09-03 冻结)」波批口径,工作区已重写为 as-built 口径——与 design §1「现行文本已是 as-built 口径;landing 3.1 ① 的改写 = 新契约语义落位,非口径修复重复处理」声明一致。
8. **审查对象 3:strategy-docs/README.md「策略↔流程契约」行**——git diff 显示由「(四身份分离、17 接口、序列语义)」改为「(四身份分离、契约成员 13、单动作循环;序列语义为历史注)」;修改后各指向直调核实:契约成员 13(flow/README §2 L40/L84)、单动作循环(§1 头注)、序列语义历史注(§2.2 L77)、「flow/ 七篇」= flow/ 目录实际 7 个 md 文件(glob 核实)——修改后与现行事实一致,零发现。
9. **迭代规范遵循(iteration-design.md)**:README 三节结构与进度模板合规;design §0-§3 四节齐(单文档方案 §2 即完整设计,深度达标);landing 三个阶段小节七件齐(范围/设计依据/文件面/依赖/优先级建议/完成判据/验收凭据形式),固定末阶段 = 正本更新 + 清单;依据就地标注抽查全过(引用的依据全部真实存在);无过程叙事;引用寿命合规(landing 3.2 明示锁指针指向正本非 changes/)。清单 11 行引文与正本实文逐字核对全部存在且准确(L23/L64/L90/L28/L14/L21/prep L15/L32/L53/screens L130/22 L8)。
10. **治本三问**:§1 归层 = 表示层(接口形状)成立——消费语义已迁移(2026-09-06 落码)而返回形状未跟上,双向实证(消费端取首项 vs 签名 list);§2 修根 = 契约面形状收口,决策核内 list 保留有活机制依据(首项选择序),非症状补丁;备选 A-D 取舍论证无空洞(D 的「对称不是规范条款」与 op-layer §1.1 分域表述核验一致);第三方兼容面(B4、封闭集、响亮暴露不做垫片)与「恒返回一个动作」的全函数边界申报自洽。
