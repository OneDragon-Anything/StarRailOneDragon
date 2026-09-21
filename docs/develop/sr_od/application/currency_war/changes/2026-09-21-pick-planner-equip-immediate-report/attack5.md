# 第 5 轮对抗审(核一·无前提攻击)

攻击对象 = 本目录 design.md / landing.md 现稿。历轮工件(attack~attack4)只用于核对历轮发现是否清偿,不作攻击锚。全部证据自行 read/grep 取自代码与正本现稿(锚位行号均为本轮实测)。

## ① 总判

**需修订**(阻塞 1 条 + 建议 4 条)。核心方案(单相化 + 证据闩退役 + T-1 模板复用)经逐条对码核验成立,历轮申报面(joy 事实化 / cw_vocab 注释 / two_node_family :346/:348 / test_cw_gain_chain 10 处 / 供给行 :733 过期注释)全部真实在册;阻塞项是消费点迁移总表的一个测试消费点漏报(会直接红),一行修法可清。

## ② 逐条发现

### A1. [阻塞] design.md §2.2 消费点迁移总表 | `_confirm_pending` 行漏报测试消费点 `test_cw_unified_action_4.py`(3.2 删置位即红)

- **位置**:design §2.2 表 `_confirm_pending`/`_pending_leg`/`_pick_param` 行——「现消费点 = 本文件读写点 + cw_overlay_pick_action.py::CwActionPickPlannerOp 体内置位」;landing 3.2 文件面「sr-od-test/ 受影响测试(含 test_cw_yinlang_phase32.py、test_cw_gain_chain.py)」。
- **问题**:`sr-od-test/test/sr_od/application/currency_war/test_cw_unified_action_4.py::test_planner_pick_op_clicks_target_and_confirm`(:322-:340)是 `CwActionPickPlannerOp` 行为锁,桩宿主显式带 `_confirm_pending=False`(:333)并断言 run 后 `op._confirm_pending is True`(:339)——锁的正是 3.2 要删的「体内置位行」。3.2 按现稿执行该测试必红;总表对 EVIDENCE 两行、test_cw_gain_chain 行均逐测试点名,唯独此行漏,与攻击清单第 5 项「无遗漏」要求直接冲突。
- **权威源证据**:cw_overlay_pick_action.py:408(置位行,3.2 删除对象);test_cw_unified_action_4.py:333/:339(消费断言);design §2.2 表第 4 行(消费点清单无此测试);landing 3.2 文件面(未点名)。
- **建议修法**:design §2.2 该行「现消费点」补 `test_cw_unified_action_4.py`(:333/:339 置位断言);landing 3.2 文件面「含」清单点名该文件(改写 = 删置位断言,点击链断言 :337-:338/:340 保留)。
- **严重级**:阻塞(表完备性破口 + 直接红;同 attack3 F1 前例同类,前例经修订收编)。

### A2. [建议] landing.md 正本更新清单 | pick-planner.md 「:14 无涉」与该行实际内容矛盾

- **位置**:landing 正本更新清单 pick-planner.md 行——「§2 三行(:11 两相节头/:13 发射相 bullet/:17 weaken 行)…清除 + :37…修正(:14 无涉——attack3 F2 锚位勘误…)」。
- **问题**:logic-updates/pick-planner.md :14 是**落地相 bullet**——「**落地相**(evidence = `EVIDENCE_OVERLAY_CLOSED`,消费面 = `CwScreenYinLang` 重入裁决出口『入口词不在 = overlay 已关』):腿型分派应用一次…」——恰是清单目标「两相与证据闩表述清除」的核心载体行,却未列入清除面且被显式标「无涉」。清单通篇是逐行锚位风格(:3/:11/:13/:17/:23/:33/:37/:41),末阶段批按单执行会留下 :14 的过期落地相表述(该行不含会被兜底 grep 命中的 action_ops/action_exec 范围,正本 grep 兜底也不辖此文件的此措辞——兜底只查 EVIDENCE_OVERLAY_CLOSED 字面,而 :14 有该字面,但「无涉」声明在先,存在指令冲突)。
- **权威源证据**:logic-updates/pick-planner.md:14(实测内容如述);landing.md:48(「:14 无涉」声明)。
- **建议修法**:把 :14 并入 §2 清除面(§2 三行 → §2 四行,或将 :11 节头行改述为「§2 整节重写」),删除「:14 无涉」或改注「attack3 F2 锚位勘误 = 原报 :14 的发射相表述实在 :13;:14 落地相 bullet 本身在清除面内」。
- **严重级**:建议(措辞矛盾;§2 若整节重写则实际无伤,但清单字面自相矛盾,末阶段批按字面执行有留残风险)。

### A3. [建议] design.md §2.2 | 源码 docstring/注释迁移面未入表,且验收 grep 口径罩不住

- **位置**:design §2.2 表(只列 cw_vocab 注释三处与 cw_overlay_pick_action 模块头)与 §3 验收锚 3 / landing 兜底 grep(范围 = EVIDENCE_OVERLAY_CLOSED 字面全域 + 「两相/落地相/发射相」仅 action_ops §4.5 与 action_exec §2 两文档)。
- **问题**:随本批行为改写而失真的源码叙述面还有——①`cw_screen_equip_pick.py` 模块 docstring(:26-:34「重入裁决顶部…装备腿落地相按证据闩应用一次…两相语义」)与 act docstring(:117-:124);②`cw_screen_yinlang.py` 模块 docstring(:21-:38「效果腿证据闩…两相上报宿主…」)与 act docstring(:196-:203);③`cw_overlay_pick_action.py::CwActionPickEquipOp` 类 docstring(:579-:584「落地判定归画面 op 重入裁决」)与 run 内注释(:606-:608 发射相叙述);④`OverlayPickExecEnv.leg_type/norm_item` 字段注释(:124-:127「随发射透传给上报函数登记意图遥测」)。这些不带 EVIDENCE_OVERLAY_CLOSED 常量名者(①③④)验收锚 3 的 grep 与 landing 兜底 grep 均不命中,「正本与实现一致」判据亦不辖源码注释;表连 cw_vocab :733 一行注释都列了,却不列这四处,粒度不一致。
- **权威源证据**:上述文件行号实测;design §2.2 表;design §3.3;landing 兜底行。
- **建议修法**:表补一行「两屏画面 op 与 pick op 的模块/类/方法 docstring 及 env 字段注释两相叙述」→ 3.1/3.2 随批改写;或把兜底 grep 的「两相/落地相/发射相」扫描面从两文档扩到 src 改动文件。
- **严重级**:建议(行为不破、ruff 不查,但与本迭代「实现者无需再设计 + 零残留」的申报深度不齐)。

### A4. [建议] design.md §2.2 | `_pick_pending` 行「本文件读写点」漏 test_cw_screen_two_node_family.py :348(design/landing 失同步轻度形态)

- **位置**:design §2.2 表 `_pick_pending`/`_pending_pick` 行;landing 3.1 文件面。
- **问题**:该符号有测试消费断言(two_node_family :348 `assert op._pick_pending is True`)——landing 3.1 已点名(:346/:348),design 总表却写「本文件读写点」;同一表内 EVIDENCE 行均含测试消费点,此行漏(与 A1 同类但 landing 侧已补偿,故降级)。
- **权威源证据**:test_cw_screen_two_node_family.py:348;design §2.2 表第 3 行。
- **建议修法**:该行「现消费点」补 two_node_family :348。
- **严重级**:建议。

### A5. [建议] README.md | 进度行与事实不同步

- **位置**:本目录 README.md「设计对抗:未开始 · 报告=attack.md」。
- **问题**:attack2/3/4 已在目录内在册,第 5 轮在飞,「未开始」失真;报告指针只指 attack.md。README 虽为上下文件,但全量同步复查(清单第 4 项)按 design↔landing↔README 反查口径覆盖它。
- **建议修法**:进度行改「进行中(第 5 轮)/ 报告=attack5.md」或按账本实际态回填。
- **严重级**:建议。

## ③ 全量同步复查结果表

| 核对面 | 结果 |
|---|---|
| design §1.3 解决/不解决 ↔ §2 ↔ landing 3.1/3.2/末阶段 | ✓ 互覆盖无遗漏无越界(equip 屏、planner 屏、正本批、四项明确不解决面均不在 landing 范围内出现) |
| EVIDENCE_OVERLAY_CLOSED 全域实况(src) | ✓ 恰两处自持(pick_planner.py:63 / pick_equip.py:40)+ 两画面 op 消费(yinlang :49/:220、equip_pick :44/:137)——「全仓仅剩两处两相形态」主张成立;pick_supply 无 |
| 测试消费面实测 | phase32 = import :55 + 10 处调用(:198-:340)✓「10+ 处」;test_cw_pick_channels_t60 = import 别名 EQUIP_EVIDENCE :40 + 调用 :127/:218 ✓;test_cw_gain_chain = import :41 + **恰 10 处** evidence= 调用 ✓;two_node_family equip act :346(WAIT)/:348(置位)✓;**test_cw_unified_action_4 :333/:339 = 漏报(A1)**;two_node_family 的 `_confirm_pending`(:271/:282)属祈愿屏,不受本批影响 ✓ |
| `normalize_equip_name` 消费点 | ✓ src 唯一组装点消费 = cw_screen_equip_pick.py:168;本体其他消费仅测试(phase32 :62/:157/:161,本体不动故不受影响)——表「无过度」成立 |
| cw_vocab :733 供给行过期注释 | ✓ 实测在位(``normalize_equip_name`` 措辞,supply 实际用 registry 入口 cw_screen_supply_node.py:304)——「T-1 遗留」主张成立;equip param docstring :906-:911 两相措辞在位 ✓ |
| `normalize_registry_equip_name` 复用(T-1 已建) | ✓ cw_events.py:951,158 键分层归一实现在册 |
| joy 收口序事实化 | ✓ commit 14dd40977 在库(pick_planner/cw_events/cw_gain_chain/cw_overlay_pick_action 四文件);测试面在独立仓 sr-od-test d3f5788e(条件腿 rider 锁组)——双侧提交事实成立;挂点 = 现落地相门(pick_planner.py:94)✓;「+63 行」数值未逐行复核(差异不影响结论) |
| 正本清单锚位逐条 | action_ops §1 增补 2/增补 3/§4.5 欠账段(:119,PickPlanner :127/PickEquip :135 两行)✓;action_exec §2 :24「其余屏(策划/补给/装备)」句 ✓;op-layer :33(已迁屏枚举)/:43(§1.2 欠账引用)/:96(§3 注悬空引用)/§3 :88(节点循环行含 YinLang/EquipPick)✓;planner.md :12/§4(:24-:31)/§5(:48-:49)/:55/:76 五处 ✓ §1 无涉 ✓;equip_pick.md :24/:26/:52 ✓;README §5.5(:105 节,:109 两相欠账句)/§6 :138(即时上报枚举)✓;fields.md §3.4 无需更新项核过(chosen 表述不辖 planner/equip,lv999 写端 :612 语义不变)✓;**pick-planner.md :14 = A2** |
| 腿型实码口径对齐 | ✓ classify_planner_leg 四步判定序与 weaken 退役(cw_events.py:994-:1024)↔ design「unknown 留证/弱化词落此/unrouted 兜底」一致;_apply_upgrade_transform 分支(unobserved/ceiling/零/多/恰一)↔ design「三态+档行逐位保持 + 前置硬校验」以「逐位保持」兜住 ✓;§2.3 重复应用后果论证(二次 → planner_upgrade_source_missing 留证零写)与码一致 ✓ |
| 时序等价论证(§2.0) | ✓ emit_overlay_confirm 零观察零判效(_overlay_confirm.py:91-:119),确认点击→上报窗内无容器写端;旧落地时点前亦无写(同 op round_wait 窗内仅 OCR 门)——论证成立 |
| sig actor 换名 + 增补 3 合规 | ✓ 现值 actor='CwScreenYinLang'/:218、'CwScreenEquipPick'/:137;供给/投资先例同款换名(action op 内 type(self).__name__)✓;迁移后动作 op 零新增读屏 ✓ |
| 账本 T-5 承接出处(design §0) | 未独立复核(账本不在本轮权威源清单;低风险,建议维持原申报) |

## ④ 试读结论(逐阶段)

- **3.1(equip)实现 worker**:能开工。单相调用点、registry 归一换源、闩/门删除、注释三处、two_node_family :346/:348 改写均有唯一解;无「看情况/待定」。附注:A3 的 equip 侧 docstring 若不列,worker 大概率仍会顺手改(ruff 不查,属申报深度问题非开工障碍)。
- **3.2(planner)实现 worker**:能开工,但按现稿跑完会在 test_cw_unified_action_4 处遇未申报红(A1)——修一行表/清单即可恢复「无需再设计」。
- **正本更新批 worker**:能开工;唯一风险点 = pick-planner.md :14 的「无涉」矛盾(A2),照单执行可能留残;其余锚位(含 action_exec supply 行复核、op-layer 四处、README §5.5/§6)均有唯一改法。

## ⑤ 零发现面声明

以下面本轮逐项攻击后**零实质发现**:边界完整性(§1↔§2↔landing 覆盖/越界);时序等价论证;腿型四分支与弱化退役的实码口径;joy rider 双仓事实化与收口序;normalize_registry_equip_name 复用与 fail-closed 同构主张;cw_vocab 注释三处真实性;grep 三段式口径的 design/landing 一致性;验收锚 1/2 行为级可判性;sig actor 换名申报与先例;增补 2/增补 3/原裁定的规范自洽;op-layer §2.2 chosen_* 不解决面的合法性;`_pick_pending` 之外各符号消费点的无过度性。
