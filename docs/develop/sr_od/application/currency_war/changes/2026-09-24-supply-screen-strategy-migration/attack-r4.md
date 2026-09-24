# 对抗审查报告 · 第 4 轮（attack-r4）

> 审查对象:本迭代 design.md / landing.md / README.md(草案·对抗审中态全文)。
> 方法:三核(docs/develop/harness/iteration-design.md §7)并重;数值/口径/引文/码点全部直调源文件复核(禁转述),核对面清单见文末。
> 严重度:高 = 阻断落地的错误;中 = 设计缺陷,不修会误导实现或留下不可验收判据;低 = 局部不精确,有兜底但应修。

## 发现清单

### 发现 1(中)正本收口面漏三份画面文档——kernel `decide_supply` 删除后其指针/算法描述失指

- **位置**:design.md §2.7(文档面)与 landing.md 3.3 文件面、正本更新清单。
- **发现**:本批删除 `cw_events.decide_supply`(design §2.6),以下三份正本文档对它的指称随批死亡/过期,但三份文档面均未列:
  1. `docs/develop/sr_od/application/currency_war/screens/supply.md:12`——「缺省实现委托 `kernel/cw_events.py::decide_supply`」(flow 侧画面契约文档,委托目标本批死亡);同文件 `:33`/`:40-41` 动作面「重调一次按原评分选」语义随闸内嵌失真(见发现 4,重调分支恒落零点击,「按原评分选」不可达);
  2. `docs/game/screens/currency_war_supply.md:37`——「`decide_supply` 按 `target_comp.key_equips` 契合 + 装备通用价值选最优列」(本批替换该算法)、`:57`「`decide_supply` 代码已接(`RunSupplyNode` 调)」(符号死亡);`:39` 句含已死形参 `refresh_used` 且「无刷新按钮」为存量失实,随批加重;
  3. `docs/game/screens/货币战争-补给.md:32`(「→ decide_supply」)/`:39`(同上 refresh_used 句)。
  先例:2026-09-16 迭代 landing 曾列这两份 game 侧屏档为更新面;本批设计自己的同类收口(16 号稿 :74 行)已入清单,此三份属同类漏项。「已知点全列/正本更新清单清零 = 收尾完成」的申报与实况不符。
- **修正方向**:三份文件纳入 landing 3.3 文件面 + 正本更新清单(各补一行 ←3.3),或显式申报归「全仓 changes/ 引用清理批」并说明为何 flow 侧 `screens/supply.md` 的死指针可以悬到彼批——按 AGENTS.md「正本与代码现状一致」铁律,委托目标死亡不宜悬。

### 发现 2(中)design §2.6 实机判读锚点①-④无 landing 阶段承接(design↔landing 判据失同步)

- **位置**:design.md §2.6(sim 可观测性申报末句「验收 = 单帧锁(3.1)+ 实机判读锚点(事前写定):①…④」)对照 landing.md 3.1/3.2/3.3/末阶段。
- **发现**:design 把「实机判读锚点」列为验收构成,但 landing 四个阶段的完成判据/验收凭据均只覆盖单帧锁、grep、文档对照,无任何阶段承载实机判读核对。阶段小节 = 账本唯一源(iteration-design §3.1),账本不立则锚点①-④核对不会发生;anchor 事前写定了,「跑完核对」无归属。env 批先例 = landing 3.3 内含「实机一局对照」判据与凭据(实机局 run_id + 抽验帧记录)。属写作硬规则 4(判据同步)违例形态。
- **修正方向**:landing 增补实机判读判据(可并入 3.3 或独立小节):一局内核对锚点①-④(锁线帧终局成员优先 / 手握成品·组件的无钻帧不刷 / 三级全空帧仍刷 / P1 配方锁帧按钻或通用值),凭据 = run_id + 逐锚点对账记录。

### 发现 3(中)凑星 tiebreak 标注「待用户过目确认」= 开放项,无闭环载体;landing ⑦ 已把该语义建为验收面

- **位置**:design.md §2.3(「排序依据…『能凑星者先』为会话内设计细化(**待用户过目确认**)」)对照 landing.md 3.1 验收凭据⑦。
- **发现**:这是全设计唯一开放语义项。iteration-design §6「带开放问题的定稿」不存在、硬规则 2(实现者无需再设计)以定稿为门槛——当前草案态挂起合法,但:①确认动作无载体指定(记录落在哪、回写到哪个裁定指针、由谁判定闭环)——按 strategy-work §2.6「挂确认」形态,确认须有同场记录与回写位;②landing 3.1⑦(凑星 tiebreak 单帧锁,含分跨备战席/上阵构造)已把该语义列为验收凭据,若确认不回或改序,该锁与设计 §2.3 连带返工;③2026-09-05 用户裁定已把「玩家过目」门改为编排者发起无前提对抗审(strategy-work §2.4),本设计的自设确认义务与该门的关系(额外严谨 or 遗留门形态)未申报。
- **修正方向**:二选一并写明——①指定确认载体与回写位置(如 §0 裁定指针增「凑星 tiebreak:用户 2026-09-XX 确认」行),定稿前回写;②援引 2026-09-05 裁定改由对抗审承担,删除「待用户过目确认」标记,「会话内设计细化」改为纯语义描述出处。

### 发现 4(低)`cw_screen_supply_node.py:279-280` 内联注随闸内嵌失真,不在 §2.6 注释收口清单(「已知点全列」不成立)

- **位置**:design.md §2.6(注释指针收口清单对该文件仅列 `:8-14`/`:242-245`/`:39-40`)对照 `cw_screen_supply_node.py:279-280`。
- **发现**:`:280`「kernel 刷新闸同源同值,本面 = 读缺/锚点缺不一致兜底」——闸内嵌 decide 后(容器读数 None 不产生建议),「读缺」分支不可达,重调触发面仅剩锚点缺失;`:279`「重调一次决策按原评分选」同失真(重调同输入同输出恒返 Suggestion → 零点击终结,按评分选卡不再可达)。`%2.4` 自身已推导出新语义,但收口清单漏掉承载旧语义的注释点,清单完备性申报被自己的方案证伪。(`:242-245` docstring 内同类句在已列锚范围内,整段改写可覆盖。)
- **修正方向**:收口清单补 `cw_screen_supply_node.py:272-280`(或声明该文件闸相关注释按 §2.4 新语义整段复审)。

### 发现 5(低)码点行号锚漂移(值对标签错类)

- **位置**:design.md §2.1/§2.3/§2.6。
- **发现**(实址 2026-09-24 直调):
  - `cw_game_state.py:210` → `'supply': 2` 域行实为 **:211**;
  - `cw_game_state.py:113`(TYPE_CHECKING SupplyOption)→ 实为 **:114**;
  - `cw_game_state.py:2124`(board = 上阵羁绊计数)→ 实为 **:2126**(:2124 是 enemy_affixes);
  - `cw_vocab.py:729/917`(「替代 SupplyPick」docstring)→ 实为 **:728/:916**。
  语义指称全部成立,仅行号偏移 1-2 行;design §2.7 已声明「行号锚以落批时实址为准」,故降为低,但 §2.1/§2.3/§2.6 的直调锚应按实址校正或改「符号名+文件」形态。
- **修正方向**:按上列实址校正,或统一改符号锚,避免后续轮次复耗对账成本。

### 发现 6(低)刷新判据对 tier-0 高通用值件不护刷——行为边界未进申报与实机锚点

- **位置**:design.md §2.4(三级全空定义)对照 §2.6 行为变化申报③与实机判读锚点②③。
- **发现**:「三级全空」的装备级判据只看 `equip_tier`,通用值不进刷新闸:全 tier-0 帧即使手握 `EQUIP_GENERIC_VALUE` 高档件(如 火力风暴潮=6,表自注「伤害征服核心乘区,最高优先」)仍判「全空」→ 建议刷。该行为与旧制同域(旧制无钻必刷,同样刷掉)、且是裁定结构(「存在任一非末级项 = 值得拿」)的忠实实现,非回归;但实机判读时「刷掉火力风暴潮类件」的帧将缺对账口径,易被误判为回归或判据错。重刷期望账已挂数据批,本条只涉申报完整性。
- **修正方向**:§2.6 行为变化申报③补一句边界(tier-0 帧内通用值定序只影响选卡不影响刷新,高档 tier-0 件不护刷,期望账归数据批)。

### 发现 7(低)08 号稿 E4 行编辑口径欠精确——「现有语义」格去留未指明

- **位置**:design.md §2.7(「`08_events.md` E4 行(`:19`):实现形态注更新(序数结构已落地;E4 数学仍待 derive,挂账不变)」)对照 08_events.md:19 行结构。
- **发现**:该行「现有语义(知识判据,先行形态)」格 = 「选项价值 vs 目标线组件/成品需求(组件缺口通道)」——此描述与实码本就不符(§1 症状 6),本批落地后矛盾加深。「实现形态注更新」未指明是该格整体替换为三级字典序/30 号稿指针,还是仅加注保留旧句;按后者执行则行内自相矛盾残留。
- **修正方向**:明确该格替换口径(照 13 号稿 `decide_invest_env` 行改法:现役语义格改写为序数结构描述 + 30 号稿单一源指针;P42/P40 挂账列不动)。

## 已核对为实的面(直调复核记录,供后续轮次免复耗)

以下 design 主张经打开源码/文档逐条核对成立,后续轮次无需求翻案:

- **kernel 码点**:`cw_events.py` :1(模块 docstring 补给句)/:583(段头)/:585-596(SupplyOption)/:599-605(SupplyPick)/:609-612(`_equip_value` 委托壳)/:616-647(decide_supply,只消费 equip/has_diamond,char 全程未触)/:633-635(无钻必刷)/:637/:641-642(key_fit +10 消费)/:786(`_equip_value` 唯一保留消费点 = planner)/:1002-1007(EVENT_PICK_TYPES 与 EventPick 联合;src 全仓无外部消费,safe 摘除该位)。
- **死代码申报**:`supply_reroll_decision` 全仓(src + sr-od-test)仅定义点 `cw_survey19_hooks.py:46-56`,零消费 ✓;`cw_survey19_hooks` src 唯一 import 点 = `cw_events.py:552-554` 只取 `encounter_tier_score` ✓;`sim/checks/ledger.py` 全仓零命中(src 无 sim/checks 目录)✓。
- **SupplyPick/SupplyOption 消费面**:src 仓 SupplyPick 无外部类型 import(仅 cw_events 内部 + cw_vocab docstring + cw_pick_supply_action.py:37 docstring)✓;SupplyOption 四方(obs `cw_node_obs.py:21`/容器 TYPE_CHECKING/sim `cw_sim_backend.py:78`/测试仓 test_cw_route_clear、test_cw_screen_report_ports)✓。
- **测试仓**:`test_cw_unified_action_4.py:27-33`(类型 import)/:303(构造点)恰此两处 ✓;两处 strategy 级 decide_supply stub(test_cw_obs_arch_event_screens_step3.py:47/61、test_cw_supply_pick_immediate_report.py:125)桩的是 `match.strategy.decide_supply`,flow 方法名保留即继续有效 ✓;kernel 侧 supply 决策无专用锁 ✓;`:120` EVENT_PICK_TYPES docstring 不枚举成员,摘位不受影响 ✓。
- **共享机器**:`cw_equip_value.py:36`(V4.4 meta 先验表自注)/:42-80(表本体)/:163-189(equip_tier,需求按计数、key 可含重复、空序列归 0、并列取输入序)与 design 转述逐字一致 ✓;近兑现/材料档语义 ✓。
- **两账口径与凑星**:`flow.py:712-718`(get_comp 失败回落未锁 + 告警)/:719-740(两账构造)/:729-731(`*_wf, *_wb` 展平先例)✓;`same_star_count`(`cw_merge_simulate.py:424-433`)对 list[Unit] 形状的 bench/deployed 均可读身份(`_entry_identity` :93-107,Unit 直读、非容器 fail-closed 跳过)——design「直传二元组被静默跳过」的警告经协议核实成立 ✓;`deployed_rows_of`/`bench_units_of` 签名与返回形状(`cw_game_state.py:3650/:3659`)✓;`_merge_bench` 同名同星 ≥3 合一(:337)✓;补给入席恒 1★(`pick_supply.py:48-50`)✓。
- **意向/接线**:`cw_intention.py:2075-2077`(降格清 locked_comp)✓;`pair_target_comp`(`cw_intention.py:1123-1194`)构造不传 key_equips → 恒空,design 申报②⑤的归因(判据形态变更非参照激活;P1 帧 key 参照两侧皆空)成立 ✓;`flow.py:326`/:327/:335-352/:353(target_comp 两臂)/:516-518/:545-546 ✓;`invest_env.py:388-401`(闸内嵌 None fail-closed 先例)✓;`cw_comps.py:102/:111/:112`(core/shared/transition 字段)✓。
- **op 层**:`cw_screen_supply_node.py:275-292`(重调路径)、闸放行条件、重调恒等返 Suggestion → 零点击,与 §2.4「op 语义不变、仅剩锚点缺触发面」推导一致 ✓;op 现行为(旧 kernel refresh_used 同源)下重调确曾落「按原评分选」,失真属注释层(发现 4)✓。
- **注册表**:`cw_equipment_data.py:53`(财富宝钻 effect 原文逐字)/:64-65(红钻/蓝钻星徽材料)/`cw_node_obs.py:215`(三钻检测集)✓。
- **sim**:`cw_sim_backend.py:78`/:573-585(占位分布每帧恰一带钻槽,char 恒空)→「新旧都恒选钻、刷新两侧永不触发、sim 读数恰同」的盲区机制成立 ✓;`sim_backend_runner.py:314-381`(真 CwLoop + 真 mandate_v1 装配)✓。
- **文档锚**:25 号稿 :3(族清单 11 屏含补给)/:4(拆分头注先例)/:11/:18 ✓;13 号稿 :18(改指先例)/:20/:40(「组件/成品需求」与实码不符属实)/§0:11(OCR 未就绪纪律)✓;08 号稿 :19(P42 component_demand/hoard_gaps + P40 变体② 在册口径)✓;16 号稿 :74(挂账在册;`:293` 死引用、ledger 锁零命中的替锚申报成立)✓;strategy-docs README §2(末篇 28,30 空闲)/§3(kernel 存量 = 待迁)✓;math_proofs 索引 P42(🔴 待标定 = λ 流/partner 到位率)与 design「P42 数值标定待落地」一致 ✓;env 批 design §1(:18)/投资策略批 design §1(:23)均登记补给为后续批、29 号稿被投资策略批占用(`29_invest_strategm_screen` 新建申报在其 landing 3.3)✓。
- **规范面**:宪法五/六引用与 00_framework §1 第 5/6 条一致; kernel 零指向 strategies 的 import 现状核实 ✓;encounter.py 为已搁置历史 EV 核(:1 docstring)✓;无过程叙事检查(design/landing 无「本轮/已改/第 N 轮」措辞)✓;landing 四阶段七件齐、设计依据指向真实存在 ✓;零调参攻击:全设计无新自由参数(+10 物理删除 = 未证即退役;通用值表按 16 号稿在册处置作定序常数消费且所有权申报在位)✓;prereg 保全清单在位(§2.6 验收线保全申报)✓;kernel 删除面全仓 grep 可达成(kernel 决策面零残留判据与实况对得上)✓。

## 结论

7 项发现(中 3 / 低 4 / 高 0)。核心面(码点、删除面、行为归因、sim 盲区机制、宪法对齐、零调参)经直调复核成立;3 项中级发现集中在**收口面完整性**(正本三份画面文档漏项)与**验证闭环**(实机锚点无阶段承接、凑星确认无载体),均不推翻方案本体,定稿前修毕即可。
