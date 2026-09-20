# 对抗审查报告（收敛确认轮 · attack3）

**总判定：blocker 1 / major 2 / minor 4 —— 前两轮 19 条发现（B1+M1-M5+m1-m4 共 10 条、A1-A9 共 9 条）全部收编闭合，收编质量高；但修订新引入的 §2.2 落位归权裁决与 landing P2/P3 阶段边界存在一处 B1 级同型的跨阶段断裂（to_slot 必填判据 vs 发射位归属 P3），照定稿开工 P2 必然撞墙返工。须再修（一处阶段边界修订）后可定稿。**

> 判据源：iteration-design.md §5/§7 + §1/§3。方法：逐条收编核对（读 attack.md / attack2.md 全部发现，对照修订后 design.md/landing.md 指认收编节号）+ 对新裁决（§2.2/§2.3/§2.4/§2.5/landing 七件）无前提攻击，事实主张逐条对码（文件:行）核实。行号锚为 2026-09-20 当前工作区。

---

## 一、收编闭合核对（任务一）

### attack.md（B1 + M1-M5 + m1-m4，10 条）

| 发现 | 收编位置 | 判定 |
|---|---|---|
| B1 tracked_books/mutate 链/sim 直调跨阶段断裂 | design §2.3（定稿形状+读写端闭合集入 P1）、§2.4（mutate_bench_deployed 重写保留+实机消费点名）、landing P1 范围（sim 两处 bench_place 直调同批改：cw_sim_nodes/cw_sim_opening） | 闭合。对码复核：mutate_bench_deployed 实机消费确为 cw_buy_card_action.py:173 + buy_card.py 升星腿（经 mutate_bench_deployed_local，cw_game_state.py:1845-1851），§2.4 点名无误 |
| M1 装备继承载体锁 | design §3 前置锁第 1 条 + landing P0① | 闭合 |
| M2 部署恒 held 锁 | design §3 前置锁第 2 条 + landing P0② | 闭合（锁位 P0 早于 kind 口改造 P2/P3） |
| M3 开拓者归一归属 | design §3 第 5 条（申报既有不对称缺陷）+ 前置锁第 3 条 + landing P3 归一口统一；§6 风险行 | 闭合（_apply_row_to_char 入 §2.4 删除族，对码 cw_exec_state.py:401 属实） |
| M4 CwSimFrame 体量/种子层保形 | design §2.5 + landing P5（M1 投影锁逐字节保形为先决） | 闭合（「M1」= 项目既有锁名「机制等价性验证锁 M1」，cw_vocab.py 模块头在案，非过程标签） |
| M5 sim 保真两处偏差申报 | design §2.2 行为变化申报第 2 项 + §3 前置锁第 4 条 + landing P0④/P1 判据 | 闭合（修复落点显式移 P1，R1 歧义消解） |
| m1 退役符号清单不完备 | design §2.4（deployed_place/bench_from_compact/deployed_from_compact/pad_bench/pad_deployed/bench_clear/deployed_clear/iter_occupied/deployed_occupied/_apply_row_to_char/unit_rows_to_deployed/deployed_slots_to_rows 全列） | 闭合 |
| m2 position_pref 派生点名 | design §2.1（单一源 = get_char(char_id).position_pref()，禁全局 get_role_position） | 闭合 |
| m3 死代码注释/正本连带 | landing 正本更新清单（fields.md §9、cw_registry.py） | 闭合（R3 同） |
| m4 inventory 数字口径 | design §4（词表明示 + src 696/60 实测复核**逐字吻合**） | 闭合（测试仓数字见本轮 minor N7） |

attack.md 复审残留 R1-R5：R1 ✅（修复落点 P1 申报）、R2 ✅（§2.3 deployed 侧定稿）、R3 ✅（正本清单）、R4 ✅（§2.4 全列 + §2.1 点名）、R5 ✅（采「现状基线留档 + 修复前后对照凭据」形态收编，P0④+P1 判据，属合法裁量而非锁）。

### attack2.md（A1-A9，9 条）

| 发现 | 收编位置 | 判定 |
|---|---|---|
| A1 退役清单/消费面漏 30+ 文件 | design §4 外围消费面清单（A1 点名文件逐一在列，含 flow.py/entry.py/shop.py/criteria/sell.py/statefn/predicates.py/telemetry/schema.py/economy_cycle/cw_loop/cw_screen_prep/cw_shop_action_ops/sim/cw_sim_pool）+ landing P4 | 闭合（对码：外围清单与 bench_slots_of/deployed_slots_of 实测 188 处命中文件集吻合） |
| A2 synthesize 吃帧/种子通道矛盾 | design §2.4（sim 帧通道三件整体退役）+ §2.5 载体（builder 直写容器域） | 闭合（通道删除而非重写，矛盾消解；§2.5 数字 87 处/18 文件、116 处/32 文件实测吻合） |
| A3 bench 侧 position_pref 恒 back | design §2.2 行为变化申报第 1 项（恒后排→注册表派生真实生效，sim A/B+新锁）+ §1 根因二如实陈述「恒被丢弃」 | 闭合（对码复核：bench_slots_to_legacy cw_game_state.py:1478-1516 确不写 position_pref；assign_deploy_slots cw_deploy_logic.py:2186 柔取缺省 'back'，主张属实） |
| A4 faction 三类消费面 | design §2.1（装配/板面计数 cw_system_cards 未知名 '?'/羁绊 cw_bond_equips+board_by_row 三类口径） | 闭合 |
| A5 deployed tracked 形状未定稿 | design §2.3（list[Unit\|None] 定长 10、下标=deployed_idx 恒稳、0-3 前/4-9 后） | 闭合（对码：deployed_row_slot/deployed_idx_of cw_exec_state.py:327-353 与 0-3/4-9 口径、ADR-0392 注释逐字吻合） |
| A6 过程叙事/状态枚举 | design 全文已清（状态=「对抗审中」规范枚举；「M1 投影锁」= 项目既有锁名，非过程标签，见 M4 行）；landing 无叙事 | 闭合 |
| A7 landing 缺失/七件不全 | landing.md P0-P8 九阶段七件齐，账本唯一源落地 | 闭合（账本 T-8..T-16 criteria 逐一指向 landing §3.1-§3.9，节号全部真实存在；旧 T-1..T-7 已标 dead 附理由） |
| A8 TrackedBooks 形状描述失真 | design §2.3（bench/deployed 双列表） | 闭合（对码 cw_game_state.py:2050-2061） |
| A9 数字口径 | design §4 词表+范围标注 | 闭合（src 端逐字复核；测试仓端见 N7 微差） |

**收编小结：19/19 闭合，无收编引入新问题**（「M1 投影锁」初看似过程标签，核实为项目既有锁名，不计发现）。

---

## 二、新内容无前提攻击（任务二）

### [blocker] N1. P2「载荷缺 to_slot 无编译面」判据与发射位归属 P3 自相矛盾——P2 落地即断，B1 同型跨阶段断裂

**证据**：
- landing.md:32（P2 范围）+ :38（P2 判据「载荷缺 to_slot 无编译面」）+ design.md:35（`CwActionDeployMoveParam` 增 `to_slot` 合成完整落位意图）。
- 全仓 `CwActionDeployMoveParam(` 生产构造点仅两处：`strategies/impl/mandate_v1/mandate.py:2279-2281`、`operations/cw_loop.py:248-249`（grep 全量核实，无第三处）。两文件均归属 **P3**（landing.md:47 文件面：strategies/impl/mandate_v1/*、operations/cw_loop.py）；P2 文件面（landing.md:34）= kernel/cw_vocab.py、统一动作工厂与部署执行 op、sim/cw_sim_engine.py——不含任何发射位。
- 现状 `CwActionDeployMoveParam` 无 to_slot 字段（cw_vocab.py:544-556）。

**实现者视角杀伤**：P2 把 to_slot 设为必填（判据明令无默认），落地瞬间 mandate.py:2279 与 cw_loop.py:248 两处构造即 TypeError，L1 必红；两文件的修复（发射 to_slot）按 landing 归属在 P3——P2 在自己的文件面与判据框架内**无合规落地路径**。三条出路全部违文本：给 to_slot 默认值（违 P2 判据）；P2 顺手改发射位（违 P3 文件面，且 mandate 发射位改写正是 P3 的策略落位主体）；P2/P3 合并（阶段拆分重设计，B1 已裁定此类「闭合集与阶段结构矛盾」为 blocker）。

**修复方向**：P2 文件面纳入两发射位的 to_slot 最小接线（透传 assign_deploy_slots 现成第三元 `_slot`——mandate.py:2268 / cw_loop.py:243 均已拿到 slot 只是现丢弃，透传 = 零行为变化的机械接线），并在 P2 范围明示「本阶段发射槽位 = kernel assign 现值透传，策略接管落位在 P3」。

### [major] N2. P2 落位语义改写的真实宿主（deploy_move 上报函数 / cw_sim_actions）不在 P2 文件面，且文件面误指 cw_sim_engine.py

**证据**：
- sim 应用部署动作的宿主 = `sim/cw_sim_actions.py:112-113`（apply_player_action 直调 `report_action_deploy_move_param`），非 landing.md:34 所写的 `sim/cw_sim_engine.py`（该文件是引擎类 CwSimEngine，cw_sim_engine.py:305）。
- 容器写侧的「落位决定」现宿主 = `kernel/cw_action_report/deploy_move.py:95-99`：`deployed_place`（首空槽 + 排满 fallback 另一排，**完全忽略槽位意图**）——这正是 §2.2「框架零落位决定」要消灭的写路径落位，也是执行器「发出即记账」的落容器通道（cw_deploy_move_action.py:59-61 docstring 自证）。该文件在 landing 仅出现于 **P3** 文件面（且只为「归一口」），P2 文件面没有它。
- deployed_place 的全部消费点：deploy_move.py:97、cw_vocab.py:1270（mutate 部署腿，P1 重写 ✓）、prep_actions.py:800（P1 闭合集 ✓）——只剩 deploy_move.py 无阶段归属做 (to_row,to_slot) 语义改写。

**实现者视角杀伤**：照 P2 文件面执行（执行器 + sim engine 段）而不动 deploy_move.py 上报函数，则执行器拖 (to_row,to_slot)、容器/sim 记账仍按首空+fallback 落位——两侧分叉，tracked/board 与实际画面错位，恰是「隐藏行为变化」且 L1 不显影（两套首空规则在多数局面同结果）。P2 判据「sim 对目标槽有人按交换语义应用（锁）」倒逼实现者找到真宿主，但文件面指错方向 = 实现者要么越阶段改文件、要么按错文件面交出不完整实现。

**修复方向**：P2 文件面补 `kernel/cw_action_report/deploy_move.py`（落位腿改 (to_row,to_slot) 直落 + 目标槽有人=交换）与 `sim/cw_sim_actions.py`（或改写为「sim 应用 = 上报函数，见 deploy_move.py」），替换误指的 cw_sim_engine.py。

### [major] N3. P1 tracked 翻形与 P2 删首空位现读之间，执行器 `empty_deploy_slots(tracked)` 的过渡形态未设计——getattr 柔取下静默错排，不红不炸

**证据**：
- P1 把 `tracked_books.deployed` 翻成 `list[Unit | None]`（design §2.3）；执行器现读 = cw_deploy_move_action.py:74-79：`pad_deployed(tracked)` → `empty_deploy_slots(tracked, ...)`，读点在 **P1 闭合集内**（§2.3 点名 cw_deploy_move_action）但 P2 才「删首空位现读」。
- `empty_deploy_slots`（cw_deploy_logic.py:2141-2157）用 `getattr(d,'position_pref',None) or 'back'` / `getattr(d,'slot',0)` 柔取字段：喂 `Unit` 表**不报错**——Unit 无 position_pref（恒 None→'back'）、Unit.slot = 行内 1 基信息位（cw_game_state.py:3709-3712 合成段自证行内口径）→ 前后排占用集合全部算错（前排角色全计成 back、槽号取行内值）。
- `_track_move_deployed`（prep_actions.py:774-802）同样在 P1 翻形后须经 deployed_place（BenchChar 签名）——P1 需给一版即弃的过渡写法，design 未点名。

**实现者视角杀伤**：P1 提交时这段代码不会炸（getattr 全兜住）、L1 也大概率绿（多数测试不覆盖执行器现读路径），错误以前后排占用错读的形式潜伏到 P2 才被消灭——「逐阶段测试全绿」承诺对一个静默行为漂移窗口失效，正是 §2.4 映射约定要防的坐标事故形态。

**修复方向**：design §2.3 或 landing P1 补一句：P1 期 cw_deploy_move_action/_track_move_deployed 的占位/落位读一律经 `deployed_row_slot`（§2.1 换算单一源）按下标派生排与槽号，禁 getattr 柔取旧信息位。

### [minor] N4. P6 完成判据引用 P5 已删除的分支——「shop_empty_off_screen 分支语义不变」锚点悬空

**证据**：landing.md:89（P6 判据「识别域调用面（shop_empty_off_screen 分支）语义不变」）指向 `synthesize_from_game_state` 的商店三态分支（cw_game_state.py:3765-3779）；该函数 P5 整体退役（landing.md:71，§2.4 sim 帧通道删除）。全仓生产调用面为零（grep 核实：src 内仅注释与自身），「识别域调用方」= 测试种子。P5 后种子直写容器，三态语义（买空=[empty×5] / 离屏=leave_screen/None）在种子层的表达口径未点名。

**杀伤**：P6 验收对着已删函数名核判据 = 不可验收；三态语义（用户三态裁定 2026-09-13 在案）在种子重写时的保真无判据挂点。

**修复方向**：判据改写为「商店三态语义（买空/离屏/失读）在种子直写容器路径下等价表达（observe [empty×5] / leave_screen）并有对照」。

### [minor] N5. design §3 引用记法「§3.1-3.4 / §3.5」把编号列表项当节号——锚点形式与文档结构不符

**证据**：design §3 是「不变量 1-5 编号列表 + 前置锁块」，无 §3.x 小节标题；landing.md:20 引「§3.1-3.4」、landing.md:46 引「§3.5」、design.md:26,83,89 亦多处引「§3.5」，实指列表第 5 项（开拓者归一）。读者按节号找 §3.5 会落空。

**修复方向**：统一改为「§3 不变量 5（开拓者归一）」式引用。

### [minor] N6. §2.4「全量裁决」清单外仍有多枚 BenchChar 形状符号，且 §4 grep 验收词表不含它们——漏改不显影

**证据**：`iter_deployed_slots`（cw_exec_state.py:512）、`_session_tracked`（cw_exec_state.py:39）、`_card_to_bench`（cw_vocab.py:1218，缺省 position_pref='back'——A3 同源病灶）、`_identity_of`/`merge_material_stale_names`/`_apply_full_bench_merge_buy`（cw_merge_simulate.py:79/381/473）、`mutate_bench_deployed_local`（cw_game_state.py:1845）、`_slot_sig`（collect_ore.py:58）。所在文件均在 P1/P4 文件面内（隐性覆盖），但 §4 验收词表（design.md:94）与 P7 判据「词表 grep 归零」不含这些符号名——BenchChar 退役后若某个被漏改（如 _card_to_bench 仍在产 BenchChar），P7 验收不显影。

**修复方向**：§4 词表补列（或 P7 判据加「`BenchChar` 一词在 src grep 归零」兜底——该词已含在词表内，但 `def .*=.*BenchChar` 形状签名可作二重网）。

### [minor] N7. §4 测试仓计数 370 处/41 文件与实测不符（口径未标）

**证据**：按 §4 自带词表实测 sr-od-test：行命中 381 处 / 42 文件（src 端 696/60 与申报逐字吻合）。差异或为快照时点/口径，但按词表行命中不可能少于申报的处数，370 为低估或统计口径未标注（硬规则 1）。

**修复方向**：修数或注明统计口径；不影响排期结论（量级成立）。

---

## 三、定稿试读结论（逐阶段「凭这份能开工吗」）

- P0 ✅（四件锁判据可执行，含红绿对应要求）。
- P1 ⚠️ 可开工，但 cw_deploy_move_action/_track_move_deployed 的过渡口径需现场拍板（N3）。
- P2 ❌ 开工即撞 N1（发射位断裂）+ N2（宿主指错）。
- P3-P8 ✅（依赖序合理；P5 投影锁/种子数字实测吻合；P6 判据锚点 N4；账本 criteria 锚全存在）。
- 全量同步复查：design↔landing↔README 相互引用锚存在（design.md:7↔landing.md:3↔README）；正本更新清单 6 条锚（strategy-docs/fields.md §3.2.5/§4.2/§9、action-logic-state.md、projection_contract.md、data/cw_registry.py）抽验存在；账本 T-8..T-16 → landing §3.1-§3.9 全部真实。

## 四、三核小结

- **核一·无前提**：非零（N1-N7）。§2.2 现状主张对码全部属实（executor 首空现读 cw_deploy_move_action.py:74-91、kernel 定排 assign_deploy_slots/empty_deploy_slots、select_deployments 在 kernel、备战候选 position_pref 恒丢弃——bench_slots_to_legacy 不写 position_pref + assign 柔取缺省 'back' 双证）；§2.3 deployed 下标口径与 deployed_row_slot 逐字吻合；§2.4 抽查符号（含四死函数，test_cw_economy.py:14 命中为 docstring 非调用）全部属实；§2.5 名字表达纪律可执行（注册表 position='front' 角色在册，data/cw_chars.py 37 处 'front' 命中，P3 新锁可种）。伤在阶段边界（N1/N2/N3），不在方案本体。
- **核二·规范遵循**：§5 规则 2（实现者无需再设计）被 N1（P2 无合规路径）/N2（文件面误指）触犯；规则 1 依据标注被 N7 触犯；规则 4 全量同步复查残留 N4/N5。状态枚举、无过程叙事、landing 七件、账本同步全部合规。
- **核三·治本**：消灭换形 + 落位决策权归策略层均修根（前者消灭表示层信息销毁点，后者把「谁上场去哪」从框架还给它所属的策略知识层）；无同族第 3 件症状补丁迹象。

## 五、复审判定

**须再修**：N1 为 B1 同型阶段断裂，一字修订（P2 文件面补发射位透传 + 落位宿主两文件）即可消解；N2/N3 随 N1 一并三行收口。修后即可定稿开工——方案本体与收编质量已到可定稿水位。
