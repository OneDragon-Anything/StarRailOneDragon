# 策略遥测 设计对抗报告（无前提攻击）

> 攻击对象：design.md + details/capture-store.md + details/render-assembly.md + landing.md + README.md。
> 方法：核一（无前提攻击）+ 核二（规范遵循，对照 `docs/develop/harness/iteration-design.md` §5/§7）+ 核三（治本核验）。
> 全部发现均经权威源逐项开核；行号为攻击时点实况，语义不符才算发现、行号漂移不算。

## 发现清单

### 高

**N1（高）回执关联的覆盖不变量与代码相抵：12/14 决策入口根本没有回执可 join**
- 设计锚：capture-store.md:26「时序边界：one decide → one action → one 执行 → one 回执（单动作循环不变量，`entry.py:427`…）」；design.md:26「动作回执行…带入 dtag；渲染器…按 dtag 精确 join，在每个动作节装配『策略依据』小节」。
- 证据：`note_action_receipt` 全仓仅 4 个生产调用点——prep 统一口（`prep_actions.py:318/:367`，只覆盖 prep 循环分派的动作）、close_shop 动作 op（`cw_close_shop_action.py:51`）、open_shop 直调体（`cw_op_open_shop.py:43`）、shop visit 落地门（`cw_screen_shop.py:287`，且 :647 明确 CloseShop 跳过由关店 op 承担）。而 pick 族 12 个入口全部由各自画面 op **直调** decide_*、无任何回执写入：`cw_screen_supply_node.py:311/:317`、`cw_screen_encounter.py:187/:196`、`cw_screen_invest_strategy.py:290/:344`、`cw_screen_invest_env.py:328/:373`、`cw_screen_megastar.py:200`、`cw_screen_partner.py:248`、`cw_screen_yinlang.py:186`、`cw_screen_bookcard.py:242`、`cw_screen_wish_trial.py:148`、`cw_screen_box_pick.py:266`、`cw_screen_fortune.py:154`、`cw_screen_expert_invite.py:217`——grep `note_action_receipt` 在 cw_screen 目录仅命中 cw_screen_shop。供给面旁证：`cw_vocab.py:667-668`「执行 op = CwActionPickXxxOp（…op 内自上报，零写）」——pick 族走上报函数族，不走回执域。
- 后果：①decide_prep_screen / decide_shop_action 之外的**全部决策**（一局里数量最大的恰恰是 pick 族）永远 join 不到回执，全部落进「未落地决策」注记——而 render-assembly.md:33 把未落地形态枚举为「空动作 CwActionObsParam、驱动器路径、被截断动作」，完全没预见「正常成功决策、只是无回执架构」这个将成为**主形态**的类；②用户需求「策略发出动作 op 的依据」对 pick 画面在报告里没有任何动作节可挂（动作节 = 回执行，render-assembly.md:5），功能目标对这些入口直接落空；③未落地注记的**章归属无键可依**：envelope 键闭集（design.md:28）无 screen/画面键，node.kind 只能粗定位节点型画面，box_card/fortune 等弹层挂哪个章未定义。
- 修复建议：三选一并写入总纲契约——①把 pick 族动作纳入回执域（动「每动作 op 恰一条回执行」四调用点不变量，`cw_game_state.py:1408-1412`，属契约级改动需申报）；②渲染侧按 entry+node 定死章归属映射；③显式申报 v1 可 join 面 = prep+shop 两入口，pick 族按「直调决策」专用注记语义渲染（与「未落地」区分），并给 envelope 增补章归属所需键。这是本迭代核心卖点（「决策↔执行精确 join」）的成色问题，必须在定稿前回答。

**N2（高）wrapper 包裹面未钉死：`decide_shop_screen` 被 名称规则 卷入 + super() 嵌套双记录，生产路径每次商店决策产脏数据**
- 设计锚：capture-store.md:13「对本类命名空间内名为 `decide_*` 的函数包一层记录 wrapper」「已标记的不再包（防 CwFlowStrategy 与 MandateV1Strategy 各自定义同一入口时双包）」；design.md:26「15 个零参 `decide_*`」；design.md:28「`emitted = [{op, reason, route_tag}]`（恰一动作）」。
- 证据：
  1. **计数失锚**：`cw_strategy.py:146-221` 实际 `@abstractmethod` 恰 **14** 个；该文件 docstring 自相矛盾（:13-14「零参入口 abstract 15」vs :82「零参入口 14」），设计取了过期的 15 未对码。「15」在名称规则下唯一凑法 = 14 抽象 + decide_shop_screen，而后者非零参契约入口。
  2. **list 返回破坏信封契约**：按名称规则，`decide_shop_screen`（`bridge.py:271-272`，签名 `(session, config) -> list`；`flow.py:815` 同名缺省实现）会被包裹，返回 0..N 个动作——「恰一动作」的 emitted 对 list 返回未定义。capture-store.md:27 一边预期驱动器路径产记录（「渲染侧按『未落地决策』申报」），一边未定义多动作信封形态——两条主张互相需要、契约却不相容。
  3. **super() 嵌套双记录（生产实害）**：`MandateV1Strategy.decide_shop_action`（`bridge.py:254`）末行 `return super().decide_shop_action()`（`bridge.py:269`），基类实现（`flow.py:725`）同为 decide_* 命名、同样被包——两层 wrapper 各自 dseq 自增、各发一条记录，回执 take 只命中内层 dtag，外层记录恒成孤儿。**每次生产商店决策 = 2 条记录 + 1 条未落地噪声**。landing.md:18 判据「单次 decide 调用产出一行记录」按真实类层次**不可满足**。防双包标记防的是「同一函数对象被包两次」，防不了调用链嵌套。
  4. 驱动器内循环（`bridge.py:328` 逐帧调 `self.decide_shop_action()`）在 sink 在场时一次驱动器调用再产 N+1 条。
- 修复建议：总纲把包裹面钉死为「cw_strategy.py 的 14 个零参决策入口」；明确 decide_shop_screen 不包（或单独定义多动作信封）；明确嵌套归属（建议：只在叶子具体类包——即标记了 `_abstract=True` 的中间基类命名空间不包，flow 层缺省实现经子类实例调用时由子类层单点记录；或 wrapper 检测调用链上已有活跃 wrapper 则直通）。landing 3.1 判据同步改写。

**N3（高）run_id 供给点与自家依赖约束自相矛盾，捕获缝无法按文开工**
- 设计锚：capture-store.md:6「decision 桶依赖矩阵只可依 data/kernel——**基类捕获缝不得引入策略包对 telemetry/app 层的 import**」vs capture-store.md:18 信封字段供给「`run_id` = `telemetry.state.current_run_id()`」+ capture-store.md:13/14「wrapper…填信封」。
- 证据：信封由 wrapper 填（capture-store.md:13-14、design.md:26「调用后由 wrapper 填信封」），envelope 键闭集含 run_id（design.md:28）且渲染按 `envelope.run_id` 过滤（render-assembly.md:13）——按文实现，`strategies/impl/cw_strategy.py` 内的 wrapper 必须读 `telemetry.state`，**同文档两节直接冲突**；若改由 sink（telemetry 侧）补齐 run_id/ts，又与「wrapper 填信封 + §2 供给清单」的文义相悖，实现者必须自行拍板（撞 §5.2 停手令）。设计自己引用的先例给出了解法模板却没用上：`cw_state_journal.py:403-405` `install_state_telemetry(..., run_id_provider=...)` provider 注入。
- 修复建议：二选一写死——①cw_strategy 加 `run_id_provider` 装配槽（仿 cw_state_journal 先例，装配点同 sink）；②明确「信封 run_id/ts 由 telemetry 侧 sink 落盘前补齐」，并在总纲接口契约里注明键闭集的**填充责任分工**。

### 中

**N4（中）kernel 决策上下文槽的残留面被错误标注为「理论无此形态」，且无测试复位入口**
- 设计锚：capture-store.md:26「陈旧 dtag 残留面 = 攻击审复核项」（把未决事项挂给攻击审 = §5.2「待定」变体）；landing.md:29「槽清空后（理论无此形态）不写 dtag 键」；capture-store.md:42「缺省 None = 零写——纯单测零副作用，conftest 无需清理」。
- 证据：take 只发生在 `note_action_receipt`；**真实存在**的「decide 后无回执」形态至少有：①obs 空动作 outer_loop 早退（`cw_screen_prep.py:813-821`，无回执返回主循环）；②停机刹车/执行异常/overlay bail（`cw_screen_prep.py:832-847`）；③supply 重调后零点击终结（`cw_screen_supply_node.py:317-324`）；④N1 的 pick 族全量；⑤单测直调 decide 不执行动作（如 `sr-od-test/.../test_invest_strategy.py:1058` 构造活策略核直调 decide_invest_env）。槽是进程级模块全局，跨测试残留会让后续「无 decide 的 note_action_receipt 直调」测试（open/close shop 单测）带出脏 dtag 键——这正是 `telemetry/state.py:157-183` reset_run_state 注释里实证过的「模块槽跨测试残留」病理，设计引用的先例 `cw_state_journal.py:506-519` 自己都配了 `set_run_id_provider(None)` 复位并注明「与 telemetry.state 复位簇同病理」。sink 句柄缓存（见 N10）同理。
- 修复建议：给槽加 `reset_decision_ctx()`（或 take 带 run_id 守卫），conftest/测试锁面列入清理项；landing 3.2 判据删「理论无此形态」改为「无在途 decide 时直调回执不写 dtag 键（显式清槽后断言）」。

**N5（中）正本更新清单第一行指错文件：action_exec.md 没有「回执契约节」**
- 设计锚：landing.md:77「`docs/.../flow/action_exec.md`（回执契约节：dtag 键语义） ← 3.2」。
- 证据：`flow/action_exec.md` 全文仅 2 处顺带提及「回执」（:21「不是动作回执」、:51「上报 executed 回执携带」），无回执契约节；回执契约正本家 = `game_state/fields.md`（fields.md:2157「唯一写入位置 = `note_action_receipt`…**回执契约单一节 = 本条**」、:2160「**回执契约**…」），且代码注释指认同一处（`cw_game_state.py:1384-1385`「码词表（暂住本 docstring，**正本家 = game_state/fields.md 回执契约节**）」）。撞 iteration-design.md §5.4「文件面真实路径」与定稿前逐一核锚要求。
- 修复建议：清单目标改为 `game_state/fields.md` 回执契约节（dtag 键并入契约条/码词表节）；若确要在 action_exec.md 落执行侧说明，写明「新增节」及其与 fields.md 单一节的分工。

**N6（中）payload.k_members 的「同源读法」断章：K 空窗回退帧记录值 ≠ 决策实际输入**
- 设计锚：capture-store.md:33「`k_members: [str]` —— `predicates.line_members(direction_comp_of(gs))`（`entry.py:460` 同源读法）」。
- 证据：`entry.py:459-460` 只是起点，同块 :463-472 的 K 空窗回退把 k_members 换成 `cw_intention.k_empty_window_fallback(...)` 结果并计数 `prep_k_fallback_*`；payload 现读公式没有回退分支，回退帧（`direction_comp_of` 两键都空，`session_scope.py:377`「两键都空…= None——无方向帧由 K 空窗回退承接」）将记录 `k_members=[]` 而决策实际用的是回退名单。候选 A（上阵窗口自锁）复核恰依赖「决策帧上判据输入现值」（capture-store.md:35），这类帧的依据块会误导判读。
- 修复建议：payload 公式补回退分支（同源调 `k_empty_window_fallback`），或申报已知边界「回退帧 k_members 记 []、判读以 counters `prep_k_fallback_*` 键为准」——二选一写进 capture-store §3 与 strategy-telemetry.md 键表。

**N7（中）正本更新清单把「正本更新」花在 changes/ 过程件上**
- 设计锚：landing.md:81「`changes/2026-10-16-journal-review-renderer/details/render-spec.md`（章内结构补策略依据块与发现参数） ← 3.4」。
- 证据：该目标是**迭代过程区**文件——项目 AGENTS.md 文档规范铁律「changes/ 会不定期、无理由删减，代码与正本文档禁引其内容」；iteration-design.md §1 引用寿命分层同样把 changes/ 件定位为寿命=迭代的过程件。渲染器设计至今滞留 changes/ 是存量问题（`replay_to_md.py:32-34` 自认「设计 = changes/2026-10-16-journal-review-renderer/…以代码为准」），但本迭代的「正本更新清单」以清单清零=收尾完成，更新一个随时可被清理的文件 ≠ 正本自足。
- 修复建议：把渲染规范升正本（如 `docs/develop/sr_od/application/currency_war/review-renderer.md`）后列入清单；或将该行改为「过程件随批同步 + 升正本列为外溢项」，并在 §0/§1 申报。

**N8（中）join 对「重试链一节多回执」形态未定义**
- 设计锚：render-assembly.md:16「动作节的来源 = 回执行；回执行 `dtag`…→ `record`」（单数 join）；capture-store.md:24「受阻决策与随后重决策各自的 dtag 精确区分」。
- 证据：渲染器动作节有重试链形态——连续同 op 回执合并一节（`replay_to_md.py:109-120`，`chain: list`，合并规则「连续回执同 op 且前条 reason 非空」）。受阻→重派恰是设计自己声明的核心形态（capture-store.md:24）：链内第一条（受阻，dtag=D1）与第二条（重决策，dtag=D2）各匹配一条记录，一节两依据块的展示规则缺失。
- 修复建议：补链形态规则（如链条逐条列依据块，或节首回执 join + 链内差异注记），写入 render-assembly §2/§3 并进 3.4 测试锁面。

### 低

**N9（低）capture-store §2 末条锚句两实体混装**
- 设计锚：capture-store.md:27「`bridge.py:366` `decide_prep_frame` 的非生产驱动器 `decide_shop_screen`…」。
- 证据：`decide_prep_frame`（`bridge.py:366`，备战帧纯函数）与 `decide_shop_screen`（覆写在 `bridge.py:271`）是两个不相属实体，现句读作「前者的驱动器是后者」，语义不通；「不经 note_action_receipt」对两者都成立但理由不同（前者是被 decide_prep_screen 调用的纯函数、非包裹面；后者是回放驱动器）。
- 修复建议：拆两句，各自锚（:366 / :271），分别写明不经回执的原因。

**N10（低）sink 句柄缓存与「重定向后自动随根」矛盾**
- 设计锚：capture-store.md:41「根 = `telemetry/state.py:72` recorder 单例，sim 重定向后自动随根…(strategy_id, run_id) 句柄进程内缓存防逐帧 open」。
- 证据：换根语义 = 重建 recorder 单例（`telemetry/state.py:60-69`）；句柄按 (strategy_id, run_id) 缓存则换根后同键命中旧根句柄（测试复用 fixture run 名跨测试即触发）。与 landing 3.5「核验 recorder 重定向后 sink 落点随根」前提在缓存命中路径冲突。
- 修复建议：缓存键带根路径，或在 set_decision_sink 装配/换根时清缓存；测试锁面补「换根后写新根」条。

**N11（低）decide 返回非 CwAction 帧的信封形态未定义**
- 设计锚：capture-store.md:14「决策入口抛异常的帧不落记录」（只覆盖异常面）；design.md:28 emitted 摘要取自动作字段。
- 证据：非异常但非法返回形态实存——prep F3 拦截「策略输出非 CwAction」（`cw_screen_prep.py:809-812`，round_fail）。此时 wrapper 已成功返回、信封照填，op/reason/route_tag 读法对非动作对象无契约。
- 修复建议：定义该形态 emitted = `{op: <类型名>, reason: '', route_tag: ''}` 照记（F3 拒收本身即有判读价值），或声明不落——写进 capture-store §1。

## 三核结论

**核一（边界完整性/试读/对锚）**：详设合集对 §1「解决到哪」六项覆盖完整（1-4、6 归 capture-store，5 归 render-assembly），「明确不解决」四项申报清晰，无外溢误并；landing 五阶段 + 末阶段与设计依据互指成立，阶段间依赖（3.4 不硬依 3.3）划得准。但对齐权威源逐项核后发现三处**契约与代码形态不符**的硬伤：N1（回执覆盖不变量为假，join 机制对 12/14 入口失效）、N2（包裹面/嵌套语义未钉死，生产路径产脏记录、landing 3.1 判据不可满足）、N3（run_id 供给与依赖约束自相矛盾，捕获缝无法按文开工）。其余锚点核对**全部属实**：四调用点存在且经 note_action_receipt（cw_game_state.py:1364/:1408-1412/:1438 best-effort）、cw_vocab.py:146/:158-159、entry.py:275/:281/:427/:460、session_scope.py:314/:330/:371、mandate_state.py:341、telemetry/state.py:60/:72、decision_assembly.py:18 install_obs_ports 在场、cw_state_journal.py:403-405 provider 先例、recorder.replay_dir（recorder.py:71）、replay_to_md 章结构与「数据完整性」行（:1608-1610）、cw_sim_match_drive.py:142-144 重定向段、test_replay_render.py 存在；§1 症状对账数据属实（journal.jsonl:572 v=618 `m1p_plan_empty:12` 仅此一处、review_g 勘误节 :2004-2006 与 target_comp/locked_comp 全文零命中均复核成立）。任务提示点专项核：提示 4（telemetry 模块定名）已达标——capture-store §4 定名 strategy_telemetry.py、landing 3.1 引用一致；提示 5（零差异 vs 局头行）自洽——无策略文件时整行省略，逐字节一致承诺可成立；提示 3（两键都空 payload 形态）render 示例已画出 `comp=None`、line_candidates 缺省 `()` 可靠非崩，唯 k_members 回退分叉成 N6。

**核二（规范遵循）**：结构齐——总纲 §0-§2、两详设三段齐、landing 首节常规检查 + 各阶段七件齐、README 合模板、无过程叙事（仅「攻击审复核项」一处轻度过程措辞，并入 N4）。依据就地标注密度显著高于平均、可核性强，但**四处标注与权威源不符**：N1 的「单动作循环不变量」（断言了不存在的回执全覆盖）、N2 的「15 个零参」（计数未对码，代码 docstring 自相矛盾 14/15 未分辨）、N5 的正本清单目标节（文件真实但节不存在）、N6 的「同源读法」（断章了同块回退分支）——类型上都属「标了依据但依据被截取/未核」，正是 §5.1 要防的事故形态。landing.md:18 判据「单次 decide 产出一行」按真实类层次不可满足，属 §5.4 全量同步复查漏项。

**核三（治本核验）**：§1 归层**成立**——三症状（方向态零遥测 / 计数只有终局聚合 / 主路径缺位自证）的根都在「策略私有状态与决策依据无输出契约」这一约定层，与终态契约（策略状态实例私有、`cw_strategy.py:80-81` 实例不跨局）自洽，非实现层 bug；症状数据与勘误节实证吻合。§2 采集侧（基类结构缝「不靠实现自觉」+ 独立存储 + 信封契约）是治本姿势；**join 侧当前是建立在被误读的回执覆盖不变量上的半治本**（N1）——按现文落地，「精确 join」实际退化为 prep+shop 局部可用 + pick 族全量噪声注记，与「不解决」清单里被明确划走的项目不同，这是设计**以为已解决实则未解决**的面，必须修订申报而非带病定稿。同族二次件面合规：cw4_counters 迁移、per-strategy 渲染注册均已显式划出本迭代。

## 收敛判定建议

**需修订后复攻**。三个高危（N1/N2/N3）全部落在「总纲/详设契约与代码真实形态不符」档，修复动作明确（钉死包裹面与嵌套归属、申报 pick 族 join 语义与章归属键、消除 run_id 供给矛盾），不动摇方案骨架；修订后按 iteration-design §5.4 做全量同步复查（重点：14 计数口径、landing 3.1/3.2 判据改写、正本清单 N5/N7 两行）再走一轮定向复攻（只攻修订面 + N1 渲染语义）即可收敛。中危 5 项与低危 3 项建议随本轮一并修。

---

# R2 定向复攻（修订面 + 新面）

> 攻击对象 = R1 修订后的 design.md（契约 v2）/ capture-store.md / render-assembly.md / landing.md。
> 行号为 R2 攻击时点实况。新发现不与 R1 重复计数（R2-N 编号）。

## 4.1 R1 处置核验（N1-N11）

| R1 | 修订处置 | 判定 | 核验依据 |
|---|---|---|---|
| N1 两级 join | 适用域申报（capture-store §2「本设计最重要的一条边界」）+ 章级挂载表（render-assembly §2）+ join 语义两级分立（design.md §2.3） | **修复成立**（遗留缺口转 R2-N2/N3/N4） | 12 选择族不走 dtag 的边界如实申报且与回执四调用点事实一致；章级零流程改动满足「观察、依据、动作」需求（关键取舍末条），R191 面干净 |
| N2 包裹面未钉死 | 显式 14 入口名闭集 + in-flight 守卫 + 取舍申报弃前缀规则 | **修复成立** | 闭集 14 名逐一核对 `cw_strategy.py:146-221` 全中；decide_shop_screen 排除（capture-store §1）；in-flight try/finally + 单线程声明覆盖 `bridge.py:269` super() 链；landing 3.1 判据改写（「decide_shop_screen 不被包裹；super() 嵌套链恰一条记录」） |
| N3 run_id 供给矛盾 | run_id 归 sink（wrapper 信封不含此键） | **修复成立** | design.md:28 + capture-store §2/§4 + 关键取舍新增「wrapper 填 run_id…弃」；渲染侧 run 过滤时序核过：journal 行 run_id 与 sink 读的 current_run_id 同源（`cw_state_journal.py:412` run_id_provider = telemetry 现读口），sink 丢空 run_id 行 → 落盘行恒带 run_id，渲染过滤无空值面 |
| N4 槽残留 | 空动作清槽 + 陈旧槽残余面推演 + 指纹一致性校验兜底 | **部分成立** | 推演的生产面结论经独立重推**成立**（四回执点各自前置 decide 覆盖槽，无「回执先于 decide」的生产路径）。缺口：①landing:29「槽清空后（理论无此形态）」原文未动，与 capture-store §2 推演自相矛盾（推演明说 pick 族置槽后无回执读取 = 槽带陈旧 dtag 是站常态）→ 转 R2-N7；②槽无测试复位入口（现状测试因 monkeypatch `note_action_receipt` 未暴露——`test_shop_screen_op.py:194/:274/:406`、`test_open_shop.py:15` 均打桩，但 3.2 自己的验收测试就需要确定性槽态） |
| N5 正本清单指错文件 | 改 fields.md 回执契约节 ~:2157 | **修复成立** | fields.md:2157「回执契约单一节 = 本条」实存，代码注释自指一致（landing:77） |
| N6 k_members 断章 | 按 entry.py:459-472 同源算法 + `k_fallback {hit, band}` 标注 | **修复成立** | capture-store §3 + landing 3.3 判据补 `k_fallback.hit` 直调一致；`cw_intention.k_empty_window_fallback` 返回 (fb, band) 二元组与 entry.py:466-471 消费形态吻合 |
| N7 render-spec 过程件入正本清单 | 移出清单，降 3.4 迭代内义务并注明寿命 | **修复成立** | landing:45/:47「该文件寿命 = 迭代，禁入正本清单」 |
| N8 链形态 join 未定义 | 逐条列依据（每条标各自 dtag，无 dtag 跳过） | **修复成立** | render-assembly §3 动作级；与渲染器 chain 形态（`replay_to_md.py:118-120`）对齐 |
| N9 锚句混装 | 锚句仍混装 + 新增「该路径零记录零 dtag」 | **部分成立** | capture-store §2 末条仍作「decide_prep_frame 的非生产驱动器 decide_shop_screen」未拆句；且「零记录」在闭集包裹语义下不精确——驱动器内层 `decide_shop_action` 被包（bridge.py:328 循环调用），装了 sink 即产逐动作记录；现势无 sink 流经该路径故经验为零，机制表述宜改「驱动器自身零记录（不在闭集），内层逐动作记录经内层 dtag 承载」 |
| N10 句柄缓存不随根 | 缓存键 = (recorder 根, strategy_id, run_id) | **修复成立** | capture-store §4，根变更即缓存失效，与 `telemetry/state.py:60` 换根重建单例语义对齐 |
| N11 非 CwAction 信封未定义 | 照常成记录 + getattr 缺省 `''` | **修复成立** | design.md:28 + capture-store §2；锚 `mandate.py:223`（四硬约束检查点节头）实存但语义偏松——检查点返回 (bool, str) 于 emit 内部消费，decide_* 出口实为 CwAction 或 obs，非 CwAction 出口真身是 F3 防御面（`cw_screen_prep.py:809-812`）；机制定义不受影响，锚宜改指 :809-812 |

**处置计数：成立 9 / 部分成立 2（N4、N9）/ 未采纳 0。**

## 4.2 R2 新发现

**R2-N1（高）指纹一致性校验的字面规则在 open/close shop 回执上必假阳——回执 op 存在两种命名域**
- 设计锚：render-assembly §3「回执 dtag 挂载前核 `envelope.emitted.op == 回执 op`；不符…→ 章尾注记 `- 策略 dtag 失配`」。
- 证据：四个回执点的 op 字段取值两种域——prep 统一口与 shop 落地门用**动作类型名**（`prep_actions.py:368` `op=type(action).__name__`、`cw_screen_shop.py:288` 同），而 open_shop 直调体用 **op 名 `'CwOpOpenShop'`**（`cw_op_open_shop.py:43`）、close_shop 动作 op 用 **`'CwActionCloseShopOp'`**（`cw_close_shop_action.py:51`）。信封 emitted.op = 动作类型名（design.md:28）→ 字面相等判 `CwActionOpenShopParam ≠ 'CwOpOpenShop'`、`CwActionCloseShopParam ≠ 'CwActionCloseShopOp'` **恒假**。
- 后果：每次开店/关店回执（每次商店访问的常规生命周期，一局数十次）必判失配 → 依据块被剥 + 失配注记洪泛——兜底防线反成主线路噪声源。
- 修复建议：op 归一对照（`CwActionOpenShopParam↔CwOpOpenShop`、`CwActionCloseShopParam↔CwActionCloseShopOp` 两行映射常量进 ENTRY_SCREEN_MAP 同区），或指纹只在 op 落动作名域的回执上核（op 名域回执跳过核、仅 dtag join）。

**R2-N2（中）章级适用集合与未落地判定三表述互斥：prep/shop 未匹配记录归属未定**
- 设计锚：映射表含 prep/shop 共 14 行（render-assembly §2）vs「章级（无回执形态：12 选择族画面）」（§3）vs「未落地决策（两表都没挂上的：空动作、被截断动作）」（§3）。
- 证据/后果：prep 的空动作记录（stall 帧每次空转发一条，量大）dtag 未 join 时——按映射表行 1 判「已挂上」→ 章级挂载 → 备战章被 obs 记录淹没，且与「章级 = 12 选择族」矛盾；按「章级限 12」→ 表行 1/2 永不消费，「14 行闭集」名不副实。另一小缺口：未落地枚举未列非 CwAction 拦截帧形态（capture-store §2 已定义该形态照记）。
- 修复建议：一句话钉死——「动作级 join 失败的记录一律章尾注记；章级挂载仅适用映射表中 12 选择族行」；表头改「12 挂载行 + 2 申报行」或删去 prep/shop 两行；未落地枚举补非 CwAction 形态。

**R2-N3（中）章级索引缺「章实例」维度：同 node 内同屏多次开章时挂载目标未定义**
- 设计锚：render-assembly §1「按 `(entry, node)` 建章级索引」、§3「同章同 node 多次决策…按 ts 序全列」。
- 证据：章相邻合并键 = title（`replay_to_md.py:208-210` 注册纪律注），同 title 非相邻不合并——备战→商店→备战（商店访问返回主循环重入备战，常规形态）在同一 node 内开**两个**画面-备战章。`(entry, node)` 索引对此形态多候选章实例，设计未定义按章 ts 窗归属还是全落首章；「按 ts 序全列」只约束同一章实例内的排序，不解决跨实例归属。同章**跨 node** 无此问题（node 入键，已核）。
- 修复建议：补一句——章级 record 按 ts 落入时间窗覆盖它的章实例（渲染器章行自带 ts 域）；窗不覆盖（node 边界漂移）→ 未归节。

**R2-N4（中）star_tome 章补行的三个事实面未对齐（注册键未定 / 依据列含过注册表断言 / sim 广播名未用）**
- 设计锚：render-assembly §2 末行「decide_star_tome | 画面-星徽秘典 | 渲染器现无此章注册（两表零命中）——3.4 按 ACTOR_REGISTRY 选择族同规格补一行（决策面 True、0 观察键集 `('star_tome_opts',)`）」；box_card 行注「同键 CwScreenBookcard 形态并存，取箱子」。
- 证据：①**注册键未定**：新行按什么 key 注册没写——唯一候选 actor `CwScreenBookcard` 已被 画面-书卡 行占用（`replay_to_md.py:291`），同 key 改写 = 全量渲染改章名（含无策略文件的历史局，撞零差异硬承诺，render-assembly §1）；②**依据列含过注册表断言**：既有 CwScreenBookcard 行 0 观察键 = `box_card_names`，与代码写端矛盾——书卡屏实写 `star_tome_opts`/`star_tome_opts_xy`（`cw_screen_report/bookcard.py:49-71`、`cw_screen_bookcard.py:16/:173`），`box_card_names` 写端 = 武装箱（`cw_screen_report/box_pick.py:68`）——两屏**不共观察键**，「同键并存」基于过注册表行、事实不成立（该注册表行自身系渲染器存量错行，宜顺手勘误申报）；③**sim 广播名未用**：星徽秘典弹窗的 sim 画面广播值 = `'货币战争-星徽秘典弹窗'`（`cw_game_state.py:323` 域→画面映射），不在 SCREEN_REGISTRY 11 键内——补行的自然落点在此表（不与 actor 行冲突），而非「按 ACTOR_REGISTRY 同规格补一行」。live 侧 actor 行（画面-书卡）与 sim 侧新章并存的双轨命名差也需申报。
- 修复建议：star_tome 行改锚——SCREEN_REGISTRY 补 `'货币战争-星徽秘典弹窗' → 画面-星徽秘典`（决策 True、0 观察键 `('star_tome_opts',)`）并声明 live 侧 actor 归画面-书卡的差异；box_card 行删「同键并存」注；CwScreenBookcard 错行勘误列为 3.4 申报项。

**R2-N5（低）envelope node 键名与 journal node 键名不一致（round vs round_num）**
- 设计锚：design.md:28 `node = {plane, round, kind}`；渲染/journal 行模型 node = `{plane, round_num, kind}`（`test_replay_render.py:50-51` mkrow、`replay_to_md.py:16-17` node 组）。
- 后果：`(entry, node)` join 需一次键名映射，未声明则实现者各自拍板。
- 修复建议：envelope 键名对齐 `round_num`（一行改动），或 capture-store §2 申报映射。

**R2-N6（低）node 缺失帧（envelope node = null）的章级命运未定义**
- 设计锚：design.md:28「node…缺 = null」；render-assembly §1/§3 章级按 (entry, node) 归章。
- 后果：null node 记录章级无键可落——归未归节还是章尾注记，未说。决策发生在画面内、node 通常已锚定，低频形态，但契约显式允许 null 就该有归宿。
- 修复建议：null node → 章尾未落地注记（与 R2-N2 修法合流）。

**R2-N7（低）landing 3.2 判据措辞与 capture-store §2 推演矛盾 + 槽无测试复位口（N4 残留）**
- 证据：landing:29「槽清空后（理论无此形态）不写 dtag 键」——capture-store §2 推演自己明说 pick 族置槽后无回执读取是站常态，「理论无此形态」已不成立；且槽（kernel 模块全局）无测试复位正规入口（先例：`cw_state_journal.py:506-519` set_run_id_provider(None) + 「与 telemetry.state 复位簇同病理」注；`telemetry/state.py:157` reset_run_state 簇）。
- 修复建议：3.2 判据改「显式 set(None) 后回执不写 dtag 键」；capture-store §5 测试锁面补「槽复位入口存在且 conftest 可调」。

**R2-N8（低）strategy jsonl 句柄缓冲的 flush 纪律未声明**
- 设计锚：capture-store §4「(strategy_id, run_id) 句柄进程内缓存防逐帧 open」。
- 证据：journal 侧有收尾 flush 先例及其漏行实证（`telemetry/state.py:210-214` close_run 先 `flush_pending`——「批量 flush 阈值之间收尾时…档案装配读盘会漏行」）；strategy 句柄长持 + Python 缓冲，进程被杀窗丢尾帧记录（正常退出 / 3.5 复盘时序无碍）。
- 修复建议：声明逐写 flush（记录频率低，成本可忽略）或局终 flush 挂点；一句话即可。

**R2-N9（低）`__new__` 桩形态下的属性容缺未声明**
- 设计锚：capture-store §1「`self._dseq_counter` 自增（构造清零）」「wrapper 入口检查实例旗 `_decision_in_flight`」。
- 证据：本仓测试既有 `__new__` 桩形态惯例（`prep_actions.py:272`「getattr 容缺（__new__ 桩形态）」自证）；`__new__` 建的策略实例跳过 `__init__`，两属性缺省行为未定义 → best-effort 吞掉后**静默丢记录**（测试面难察觉）。
- 修复建议：两属性读法按仓内惯例 getattr 容缺（缺省 False/0，容缺时照常决策、降级不记录并 log.debug），写入 capture-store §1。

## 4.3 全量同步复查（design ↔ details ↔ landing ↔ README）

逐一开文件核过，锚**全部存在且语义相符**，除下述三处失同步：

- ✅ 回执四调用点行号：`prep_actions.py:367`、`cw_close_shop_action.py:51`、`cw_op_open_shop.py:43`、`cw_screen_shop.py:287` 全中（并核出其 op 字段两种命名域 → R2-N1）。
- ✅ `fields.md` 回执契约节 ~:2157 存在；`cw_game_state.py:1384-1385` 自指一致。
- ✅ 章键 14 行对照 `replay_to_md.py:211-310`：13 行章键实存且章名逐字相符（画面-备战/商店/投资环境/投资策略/补给/遭遇/巨星/伙伴/银狼策划/命运卜者/祈愿试炼/箱子/专家邀请）；star_tome 行「两表零命中」申报属实（其补行三事实面 → R2-N4）。
- ✅ capture-store 新锚：`cw_strategy.py:146-221`（14 名逐一对上）/:82-93/:96/:261/:80；`bridge.py:269/:271/:328/:338/:366`；`cw_vocab.py:158-159/:667`；`entry.py:281/:459-472`（k_empty_window_fallback 消费形态吻合）；`cw_screen_prep.py:805`、`cw_screen_shop.py:602`、`cw_screen_supply_node.py:311`；`telemetry/state.py:60`；`cw_game_state.py:1420-1422`；`mandate.py:223`（节头实存，语义偏松见 4.1 N11 行）。
- ✅ 渲染器锚：`replay_to_md.py:118-120`（chain）、`:208-210`（章相邻合并键 = title）、`:1652/:1685-1710`（`#### 0 观察` → 动作节×N → `#### 章内变化` → 尾注 → `#### 策略评价`——章级 `#### 策略依据` 小节插 0 观察之后与既有标题层级/顺序兼容，已核）。
- ✅ landing 3.1 文件面含 `cw_strategy.py` docstring 计数勘误（:14「15」→14），与 capture-store §1 勘误申报一致；3.4 判据含 star_tome 章注册行生效（可验收，唯 R2-N4 需先定键）。
- ⚠️ 三处失同步：landing:29 判据措辞未随 capture-store §2 推演更新（R2-N7）；capture-store §2 末条「零记录」与闭集包裹语义不精确（N9 部分成立残留）；render-assembly §2 box_card 行「同键并存」注基于过注册表事实（R2-N4②）。
- ✅ README 未动、进度口径（对抗:进行中）与两轮审查状态相符。

## R2 收敛判定建议

**仍需修订（轻量），修完 R2-N1..N4 可定稿。** R1 的主结构裁决全部立住：两级 join 与适用域申报、显式 14 闭集 + in-flight 守卫、run_id 归 sink、正本清单改 fields.md、render-spec 降迭代内义务、链形态逐条列依据——处置成立 9/11、无未采纳。剩余面集中在渲染装配细节契约：1 高（R2-N1 指纹 op 域错配，主线路假阳）+ 3 中（R2-N2 章级适用集三表述互斥 / R2-N3 章实例归属 / R2-N4 star_tome 行三事实面），修复均为局部语句与一张小映射表，不动骨架；低危 5 项（R2-N5..N9）可随批带走或显式申报。修订后无需第三轮全量复攻，做 R2-N1..N4 定向复核 + §5.4 全量同步复查即可定稿。

---

# R3 终轮复核（R2 修订面）

## 5.1 R2-N1..N4 定向复核

- **R2-N1（指纹 op 归一）→ 修复成立**。render-assembly §3:45 归一映射 `{'CwOpOpenShop': 'CwActionOpenShopParam', 'CwActionCloseShopOp': 'CwActionCloseShopParam'}`，其余字面相等——方向（回执 op → 动作类型名）与覆盖面正确：四个回执点中仅 open_shop/close_shop 落 op 名域（`cw_op_open_shop.py:43`、`cw_close_shop_action.py:51`），prep 统一口与商店落地门本就写动作类型名（`prep_actions.py:368`、`cw_screen_shop.py:288`），映射恰全覆盖、无遗漏域。主线路假阳消除。
- **R2-N2（章级适用集）→ 修复成立**。§3:43 钉死行 1-2 动作级 / 行 3-14 章级互斥，prep/shop 无回执匹配一律章尾未落地注记不入章级小节；§3:50 未落地定义改判据式「动作级无回执匹配的行 1-2 记录」（非 CwAction 拦截帧落入此定义，枚举不再冒充穷尽）。三表述互斥消除。附带一处括号枚举措辞偏松（「受阻后未重发」——受阻回执本身带 dtag 可 join，真身是停机刹车/截断类无回执形态），操作性定义已精确，不改不碍实现。
- **R2-N3（章实例归属）→ 修复成立**。§3:46 同键多章 FIFO：候选章按章首现序、records 按 dseq 序依次分配，并申报弃 ts 的理由（sim 冻结时间下 ts 不可分辨）——理由成立，分配确定性成立；错位后果有界（同 entry+node 内章归属可能偏、记录不丢失、dseq 序保持）。多实例分裂点在 ts 冻结下固有不可判定，FIFO 是确定性降级而非未决——建议 strategy-telemetry.md 键表随批补一句「多实例错位为已知降级」即可，不阻断。
- **R2-N4（star_tome 行）→ 修复成立**。§2:34 映射改 画面-书卡（依据改指真实写端 `cw_screen_report/bookcard.py:49-71`，存量错行如实申报）；:37-38 渲染器配套两修订——SCREEN_REGISTRY 补 `'货币战争-星徽秘典弹窗'`（`cw_game_state.py:323` 广播名）→ 画面-书卡 + CwScreenBookcard 键集 box_card_names→star_tome_opts（box_pick.py:68 证实两屏不共键，箱子行不动）——同 title 同规格纪律两行一致，live/sim 双轨章名统一；零差异承诺的例外被有界申报（landing 3.4 判据:51「例外仅书卡章 0 观察键集修复面，逐 hunk 归类」）。

## 5.2 随批低危复核（R2-N5..N9）

全部修复成立：**N5** node 键名对齐 round_num（design.md:28 契约 + capture-store §2:20）；**N6** null 帧不入章级、计数入局头「未归属 M 条」（design.md:28 + render-assembly §3:47/§4:54）；**N7** landing 3.2 措辞重写（「理论无此形态」已除，判据改三形态断言含跨测试残留）+ `reset_decision_tag()` 复位口入契约（capture-store §2:24）与 3.2 文件面（cw_decision_ctx.py + conftest）；**N8** 逐行写后即 flush（capture-store §4:44，附 flush_pending 漏行先例锚）；**N9** getattr 容缺申报（capture-store §2:21，emitted 读法 + `__new__` 桩形态；wrapper 体属性由 §5「全 best-effort」兜底，生产构造必经 `__init__` 清零，无生产残余面）。

## 5.3 全量同步复查

新引锚逐一开核全中：`cw_screen_report/bookcard.py:49-71`（书卡实写 star_tome_opts/xy）、`cw_screen_report/box_pick.py:68`（箱子写 box_card_names）、`cw_game_state.py:323`（广播名 '货币战争-星徽秘典弹窗'）、`mandate.py:223`（四硬约束检查点节头）、`bridge.py:328/:344-355`（驱动器内层循环与上报函数族分支）。交叉一致性：契约 v2（node round_num/null 处置/join 两级/14 闭集）↔ 两详设 ↔ landing 判据逐面吻合；landing 3.4 判据与 render-assembly 配套修订互指一致；3.2 判据/文件面与 capture-store §2:24 复位口一致。

两处一行级勘误随批带走（均非阻断——规范性答案已在场且唯一，零实现歧义）：①capture-store §2:30「渲染侧按章级挂载或未落地注记处理」——驱动器内层记录 entry=decide_shop_action 属行 2，按 render-assembly §3:43 适用集钉死只能未落地注记，「或章级挂载」三字删；②design.md:26 三处全降级句「渲染无策略文件 = 报告与现状零差异」——与 3.4 书卡章键集例外并提时加「（例外见 landing 3.4）」限定词。

## 5.4 定稿判定

**可定稿。** R1 三高危、R2 四重点（1 高 3 中）与随批五低危全部修复成立、零未采纳；上述两处一行勘误属文档同步化妆级（规范性判据在 render-assembly §3:43 与 landing 3.4 已唯一在场），不构成开放问题，随落地批顺手带走即可。按 iteration-design §6 生命周期，本迭代可进入「立阶段任务（照 landing.md 逐阶段 dag.py add）」。
