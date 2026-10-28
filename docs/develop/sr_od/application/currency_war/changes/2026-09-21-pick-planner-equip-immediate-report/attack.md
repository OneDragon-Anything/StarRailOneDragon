# 核一·无前提攻击报告（第 1 轮）

- 攻击对象：`changes/2026-09-21-pick-planner-equip-immediate-report/` design.md + landing.md（README 仅上下文）
- 规范出处：docs/develop/harness/iteration-design.md §7 核一 + §5 写作硬规则
- 方法：自行 read/grep 核证据；代码实况以 `src/sr_od/application/currency_war/` 与 `sr-od-test/` 现盘为准；正本以 flow/action_ops.md、screens/op-layer.md、screens/*、game_state/fields.md 现盘为准。

## ① 总判

**需修订后定稿**。发现 7 条：**阻塞 2**（F1 验收锚 3 判据不可满足 + 正本清单漏文件；F2 正本清单条件条目指向不存在的文件名）+ 建议 4（F3/F4/F5/F6）+ 现状记录 1（F7）。3.1/3.2 实现 worker 凭现稿可开工；**末阶段正本更新批凭现稿不可开工**（清单条目 F1/F2/F3 不可执行/不完整）。修订面全部是文档判据与清单层，方案本体（单相化/换源/退役面）与权威源逐点吻合，零方案级推翻。

## ② 逐条发现

### F1 [阻塞] design §3 验收锚 3「全仓 grep `EVIDENCE_OVERLAY_CLOSED` 零命中（豁免 = 无）」按字面不可满足；且正本更新清单漏列两个含该常量的正本文件

- **对象位置**：design.md §3 锚 3（:71）；landing.md「正本更新清单」兜底行（:47）。
- **问题**：全仓 grep 现状（本次核）：除 src 四文件与两测试文件（均在清零面内）外，**docs 侧命中** = 正本 `game_state/logic-updates/pick-planner.md`（:14/:37，含「`EVIDENCE_OVERLAY_CLOSED` 单一定义在 pick_invest」过期句）与 `screens/planner.md`（:24/:55）——两者**均不在正本更新清单**；另有 changes/ 历史迭代工件（2026-09-21-joy-conditional-leg、2026-09-20-yinlang-starup-accounting、2026-09-21-invest-landing-chain、2026-09-21-event-refresh-unify-supply-pick、2026-09-21-gain-chain 各 design/attack 稿）多出命中。「全仓 + 豁免=无」口径 = 判据永红。这与直系前序迭代 event-refresh-unify-supply-pick 的 attack F1（同类判据被判阻塞、后修为链域限定）是同一错误形态，本批重犯。
- **权威源证据**：全仓 grep（ripgrep）输出如上；landing.md :40-47 清单逐条核对无 logic-updates/pick-planner.md、无 planner.md 实名条目。
- **建议修法**：①验收锚 3 / 兜底行口径收窄为「`src/` + `sr-od-test/` + docs 正本区（screens/、flow/、game_state/）零命中；豁免 = `changes/` 历史迭代工件（禁改的对抗审存档）」；②正本清单补 `game_state/logic-updates/pick-planner.md` 条目（两相描述整篇重写为单相 + 清「单一定义在 pick_invest」过期句）；③补 planner.md 条目（见 F2）。

### F2 [阻塞] 正本更新清单条件条目指向不存在的文件名：`screens/yinlang.md（如存在该篇）`——实际在册篇名 = `screens/planner.md`，全篇两相/重入裁决表述

- **对象位置**：landing.md :45「`screens/yinlang.md`（如存在该篇）：对应节更新 ← 3.2（正本更新批先核该篇在册性）」。
- **问题**：glob `screens/*.md` 确认 **无 yinlang.md**；银狼屏正本 = `screens/planner.md`（在册），其 :12（顶部重入出口门/round_wait 循环）、:24（§4 对照表「分步上报…落地相…`EVIDENCE_OVERLAY_CLOSED`」）、:29/:38（重入出口门节点序列）、:55（§5 落地相容器写）整段基于两相形态。条件「如存在该篇」对 yinlang.md 求值为否 → 该条目按字面执行 = 零动作；「先核该篇在册性」若只核 yinlang.md 这个名字就核出「不在册」收工，planner.md 永不更新 → 正本与实现不一致，违 AGENTS §9「正本必须自足、与代码现状一致」。兜底 grep（F1 修后）只能抓到 :24/:55 两处常量名，抓不到 :12/:29/:38 的重入裁决/round_wait 表述清除——不充分。
- **权威源证据**：glob 结果（37 篇无 yinlang.md）；planner.md :1/# 标题「银狼升星二选一(planner · 货币战争-银狼升星)」、:3 代码指向 `cw_screen_yinlang.py::CwScreenYinLang`——篇名与文件名不同源是本仓惯例。
- **建议修法**：条目去条件化、直接点名：`screens/planner.md`：§1 形态段/§4 对照表/§5 节点序列与容器写全部改单相即时上报 + 派发即终结表述 ← 3.2。equip 侧 `screens/equip_pick.md` 条目（:46）路径正确 ✓。

### F3 [建议] landing :43 op-layer §1.1「重入裁决『仅限未迁移屏』清单收敛——yinlang/equip_pick 行迁出」为幻影行引用

- **对象位置**：landing.md :43 第 1 分句。
- **问题**：op-layer.md 全文 grep `yinlang|equip_pick|YinLang|EquipPick` 零具名命中——§1.1（:21-22/:33/:36-38）只有泛化规则「仅限未迁移屏」，**不存在可「迁出」的 yinlang/equip_pick 具名行**。可执行的实际更新面是：§3 分型表 :88「节点循环」行（列 CwScreenEquipPick/CwScreenYinLang，形态列写 `round_wait` 循环——迁移后该两屏变派发即终结，行注甚至可能需挪型）、§1.2 :43 尾注「其余 pick 屏(策划/装备)现状见 §4.5 欠账标注」、§3 :96 括注同款。worker 按「yinlang/equip_pick 行迁出」找行找不到，只能自行揣度。
- **建议修法**：分句改写为「§1.1/:33/:36/:37 『投资两屏/补给/遭遇已迁』枚举句扩含策划/装备两屏；§1.2 :43 与 §3 :96 的『其余 pick 屏见 §4.5 欠账标注』引用句清零；§3 :88 节点循环行两屏注派发即终结」。

### F4 [建议] design §1.1 第 3 条标题「同名常量三处自持」与自身正文及实况（两处）矛盾

- **对象位置**：design.md :15。
- **问题**：标题写「三处自持」，正文列 pick_planner.py/pick_equip.py 两处并自结论「供给行清偿后成为全仓仅剩的**两处**」。第三处（pick_supply.py）已随 T-1 清偿，标题是清偿前计数残留，自相矛盾（§5 写作硬规则卡点：正文口径须自洽）。
- **建议修法**：标题改「同名常量两处自持」或「供给行清偿后仅剩两处」。

### F5 [建议] equip 归一换源的注释连带面未申报（偏离 T-1 模板先例未申报）：`cw_vocab.py` :733/:908 docstring 仍写 `norm_item = normalize_equip_name`

- **对象位置**：design §2.2 表末行（换源仅列 `cw_screen_equip_pick.py`）；landing 3.1 文件面（不含 cw_vocab.py）。
- **问题**：`kernel/cw_vocab.py` 两处 docstring（:733 供给行已改语境的对照行、:908 `CwActionPickEquipParam.norm_item` 定义注释）把归一器写作 `normalize_equip_name`；换源后 equip param 的归一来源变 `normalize_registry_equip_name`，:908 成为过期注释。T-1 先例（event-refresh landing 3.1）对同类连带显式申报了「本文件全部注释引用清理」；本设计声称照抄 T-1 模板却未申报此连带，属未申报的先例偏离（量级小：注释层）。
- **建议修法**：landing 3.1 范围/文件面补一句「`cw_vocab.py` :908 norm_item 注释随换源改写（:733 复核是否同批）」。

### F6 [建议] 取舍 4 对 upgrade 变换分支重复应用后果的论证失实：「档行 +1 两次 / 多升一次档」被本设计保留的前置硬校验结构性阻断

- **对象位置**：design.md :65（取舍 4 末句）。
- **问题**：`_apply_upgrade_transform`（pick_planner.py :118-219）恰一枚才变换+档+1；首次（错误前置的）应用已把容器中 (银狼LV.999, 2★) 变换为 1★ 并写回——确认未生效重派导致的第二次上报时 `count == 0`，走「零枚 → `planner_upgrade_source_missing` 留证零写」分支，**档不会 +1 两次**。真实后果 = 缺陷留证行 + 容器逻辑态与游戏真值失配（待观察覆盖自愈/对账暴露）——仍是「响亮暴露」域、取舍方向（接受不设防）不变，但论据错写。若日后有人按「反正会 +1 两次也接受」的记录做决策，会高估风险面。
- **建议修法**：取舍 4 末句改为「upgrade 变换分支重复上报被前置硬校验拦截为零枚留证（档不重复 +1），真实后果 = 缺陷行 + 逻辑态失配待观察对账，同域接受」。

### F7 [记录·并行批] joy-conditional-leg 在飞批的 rider 挂 planner 落地相门（`evidence == EVIDENCE_OVERLAY_CLOSED`），与本批删 evidence 参数存在时序性碰撞

- **现状**：`changes/2026-09-21-joy-conditional-leg/`（design/attack/attack-r3 在册）设计 rider 直接受益于落地相门；**本次核代码实况：`pick_planner.py` 现盘无任何 joy rider 代码**（全文 220 行已读，零 joy 符号）——彼批未落码。若彼批先落，本批 worker 将在设计未申报的现存代码上执行「落地效果分支逐位保持」。按任务边界非攻击对象，仅如实记录：建议 design §1.3 或 §2.0 补一句「与 joy-conditional-leg 在飞批的落点冲突由批间协调（rider 迁单相时点或重排）」。

## ③ 全量同步复查结果表

| 复查面 | 结果 |
|---|---|
| design §1 改动面 ↔ §2 方案 ↔ landing 三阶段 | 覆盖无遗漏无越界（3.1=equip 全件、3.2=planner 全件、末阶段=正本）；例外 = F5（cw_vocab 注释连带漏报）、F1/F2（正本清单自身缺漏）。landing 3.1 凭据含 `test_cw_yinlang_phase32.py` 全绿 = 跨阶段回归项，与「不含 planner 屏」边界不冲突（3.1 不动 planner 链路，测试应仍绿）✓ |
| 引用锚存在性（符号/路径/节） | `CwActionPickPlannerOp.run`/`CwActionPickEquipOp.run`/`pick_planner.py`/`pick_equip.py`/`cw_screen_yinlang.py`/`cw_screen_equip_pick.py`/`classify_planner_branch`/`normalize_equip_name`/`normalize_registry_equip_name`/`_PLANNER_EQUIP_ANCHORS`/`emit_overlay_confirm`/`decide_equip_overlay_pick`/`decide_equip_pick`/`CwActionPickEquipParam.norm_item`/`apply_equip_acquire_consequence`/`merge_cascade_write`/`effective_cost`/`test_cw_yinlang_phase32.py`/`test_cw_pick_channels_t60.py` 全部实存且语义与引用相符 ✓；docstring 引证「未锁态语义（仅泛用分支）」在 cw_screen_equip_pick.py :156-157 在册 ✓；正本引用面例外 = F1/F2/F3 |
| 消费点迁移总表 vs 全仓 grep | `EVIDENCE_OVERLAY_CLOSED` src 侧恰 4 文件（两定义+两 import 消费）✓、t60 EQUIP_EVIDENCE 面（import :40 + 调用 :127/:218）✓、yinlang_phase32 11 处（import + 10 调用，design 写「10+ 处」✓）；`_pick_pending`/`_pending_pick` 仅 equip_pick 本文件 ✓；`_confirm_pending`/`_pending_leg`/`_pick_param` 仅 yinlang 本文件 + planner op 置位（:408）✓（partner op :355 的同名置位属伙伴屏 `CwScreenPartner`，表已用「（yinlang）」限定，无过度退役）；`normalize_equip_name` equip 组装点换源 ✓、本体与银狼域消费面不动 ✓。**无遗漏、无过度**（src+test 口径；docs 侧缺口归 F1/F2） |
| T-1 模板一致性 | 单相一口写/删 evidence 参数/常量仅本文件退役/归一换源 fail-closed/外循环重派治理均与 T-1（event-refresh design §2.0B + landing 3.1）及已落码的 pick_supply.py 现盘一致；「T-1 立样 + 外溢候选登记」承接关系在 T-1 design §1.3 明文（「PickPlanner/PickEquip…另批复制」）✓；偏离一处 = F5（注释连带未照抄） |
| 增补 2/3 与 op-layer §1.2 合规 | 禁止清单第 4 条（:25 判重/防重复保护）原文支持「未生效重派→重复应用按 bug 接受、不设防」✓；「单相化后未生效重派=效果分支重复应用」与裁定兼容（裁定明言真报两次 = bug 域）✓；增补 3 零新增读屏成立——`emit_overlay_confirm` = 机械确认+固定等待+无条件 round_retry、不读屏（action_ops §2.3 :59 在册；entry_keyword 仅日志），equip 点卡定位由 env 传入 ✓ |
| upgrade 重复应用定性（攻击清单专项） | 见 F6：非「资源损坏」亦非「+1 两次」，被前置硬校验拦为零枚留证；属「响亮暴露修根因」域成立 |

## ④ 试读结论（逐阶段）

- **3.1（equip）实现 worker**：**可开工**。单相 report 改法、换源入口、删闩删出口门、行为测试三型用例（命中/未解析/泛用件）均凭现稿可直接落码；泛用件主张成立——`normalize_registry_equip_name` 键集 = `EQUIPMENT_ROSTER` 全量 158 键（cw_equipment_data.py :50 分类清单含简易 8/进阶 36 等泛用件），`_PLANNER_EQUIP_ANCHORS` 仅银狼 10 件锚（cw_events.py :916），「10 件锚对泛用件恒 ''、注册表级可命中」属实。卡点仅 F5（一处过期注释是否顺手改，无申报 → worker 需自拍板）。
- **3.2（planner）实现 worker**：**可开工**。时序等价论证成立——确认点击（新时点）与重入裁决出口（旧时点）之间只有 round_wait 轮的 OCR 重入检查，容器零写入（观察只发生在两 node 观察 node 与备战 heavy 帧；report_screen_planner_obs 在派发前已写完；单线程无并发写端），`_apply_upgrade_transform` 三态前置校验读的 bench/front/back 观察态两时点等值 ✓。equip 屏删 `_pick_pending` 后「点卡未落地」治理 = 外循环重识别重派 + observe 重写 `equip_pick_opts` 槽 → `decide_equip_pick()` 零参读自洽 ✓。重复应用后果表述失实（F6）不影响开工，只影响取舍记录。
- **末阶段正本更新批 worker**：**不可开工**。F2 条目条件求值为否即零动作（正确篇名未列）、F1 漏两个正本文件 + 判据口径永红、F3 幻影行引用——三项合计使「清单清零；正本与实现一致」判据不可达。先修清单再排批。

## ⑤ 零发现面声明

以下面逐项攻击后**零实质发现**（证据见 ③ 表与 ④）：方案层单相化契约本体；upgrade 分支三态+档行逐位保持可行性；`classify_planner_branch` 不动边界（分支类型判定副产品非入栏归一器的定性与代码相符）；equip 换源主张（泛用件在键集）；零写族屏（巨星/伙伴等）不迁移边界与 op-layer §2.2 现行合法形态一致；src+test 消费点完备性；测试锚与「10+ 处」计数；T-1 承接关系；增补 2/3 逐条合规。
