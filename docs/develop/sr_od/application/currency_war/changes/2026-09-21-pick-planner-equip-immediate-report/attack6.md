# 第 6 轮对抗审报告（核一·无前提攻击）

- 攻击对象：本目录 design.md / landing.md **现稿**（R5 清偿后）；README.md 仅上下文。
- 规范出处：docs/develop/harness/iteration-design.md §7 核一 + §5 卡点。
- 方法：不锚定 attack.md~attack5.md 结论，对现稿全新攻击；历轮发现仅用于核对是否真清偿。全部依据自行 read/grep 实证（代码 + 正本 + 测试 + git）。

## ① 总判

**收敛可定稿**——0 阻塞。发现 4 条建议级（S1–S4）+ 2 条微注记，全部为措辞/归属/正本清单完备性层，方案本体（单相化契约、时序等价、归一升级、joy 收口、消费点总表、验收锚）经逐项对码与对正本核验成立。建议 S1–S3 随批清偿后定稿（均为一句级修订），S4/注记可选。

## ② 逐条发现

### S1 [建议] design §2.2 表第 1 行（pick_equip 行）残留「确认点击后容器即持效果」措辞——attack2 F7① 只清偿到 landing，未回写 design

- **位置**：design.md §2.2 消费点迁移总表第 1 行迁移列：「测试改断言『确认点击后容器即持效果』」。
- **问题**：equip 屏「点卡即选、无确认步」是 design §2.1 自己声明并在 §3 验收锚 1（「equip：**点卡后**（不等下一帧）容器即持 owned」）与 landing 3.1（「『确认点击后』措辞不适用于本屏」）双重固化的口径；§2.2 该行却仍写「确认点击后」。同文档内部自相矛盾 + 与 landing 不同步 = attack2 F7① 的**未清偿残留**（该发现当年修了 landing 3.1，design 表行漏改）。测试重写者照 §2.2 行字面写断言描述会复现 F7① 指出的错误。
- **权威源证据**：design.md :53（措辞在场）vs design.md :40/§3 验收锚 1、landing.md 3.1 范围段（正确口径）；`cw_overlay_pick_action.py::CwActionPickEquipOp.run`（:597-:615 现码点卡→等→上报，无确认步）。
- **建议修法**：design §2.2 第 1 行迁移列改「测试改断言『点卡后容器即持效果』」。
- **严重级**：建议。

### S2 [建议] `OverlayPickExecEnv` 类 docstring（:109-:128，尤其 :124-:127「随发射透传给上报函数登记意图遥测」）的改写归属两阶段范围均不覆盖——共享叙述面无主

- **位置**：design §2.2 末行声明叙述面含「`OverlayPickExecEnv.leg_type/norm_item` 注释……各自屏阶段随批机械改写」；landing 3.1 文件面 = `cw_overlay_pick_action.py`（**仅 CwActionPickEquipOp 体**）；landing 3.2 文件面 = 同文件（**CwActionPickPlannerOp 体 + 模块头例外自述段**）。
- **问题**：env dataclass 的 docstring 是**共享单一处**，既不属任一 op 类体也不属模块头；两个阶段的文件面限定词（「仅……体」）都排除了它。单相化后 :125-:126「随发射透传给上报函数**登记意图遥测**」成过期表述（上报函数此后一口写完整效果）。兜底措辞 grep（「两相/落地相/发射相」）**不命中**「登记意图遥测」——该面四条路（3.1 范围/3.2 范围/design 行的「各自屏」归属/兜底 grep）全部罩不住。试读问题：服从「仅……体」约束的 worker 谁都不能改它。
- **权威源证据**：`cw_overlay_pick_action.py` :124-:127 实文；landing.md :10/:22 文件面限定词；design.md :64 叙述面行。
- **建议修法**：landing 3.2 文件面括注扩为「CwActionPickPlannerOp 体 + 模块头例外自述段 + `OverlayPickExecEnv` 类 docstring 腿型载荷段」（归 3.2，与 planner 载荷语义同源）。
- **严重级**：建议（注释层、默认不改亦无行为危害，但归属歧义违反「凭现稿能否开工」卡点）。

### S3 [建议] 正本更新清单漏 `op-layer.md` :36 出口①枚举句——迁移后枚举不全且 grep 罩不住

- **位置**：landing 正本更新清单 op-layer 条目 = §1.2(:43)/:33/:96/§3 节点循环行；op-layer.md :36 实文：「①**终结动作**(1.4,……**投资两屏/补给/遭遇的选卡确认链按此语义:派发即终结**)」。
- **问题**：3.1/3.2 后策划/装备加入派发即终结族，:36 的出口①枚举变为不完整枚举（正本与实现一致性缺口）。该句不含「两相/落地相/发射相」字样，兜底措辞 grep 不命中；:21-22/:37 的「仅限未迁移屏」限定词迁移后仍真（不须改），与 :36 的枚举句性质不同——后者是会失效的现状快照式列举。
- **权威源证据**：op-layer.md :36 实文；对照同文件 :33/:87/:96（均已在清单内）。
- **建议修法**：op-layer 条目补「:36 出口①枚举句更新（策划/装备并入派发即终结枚举）」。
- **严重级**：建议。

### S4 [微] `action_ops.md` §1 :22 禁止清单例句本体过期（「现役 pick_invest 的『发射相/落地相』就是这种」）——兜底 grep 可命中但清单 action_ops 条目未点名 §1

- **位置**：action_ops.md :22（§1 增补 2 禁止清单第 2 条例句）；landing 清单 action_ops 条目只写 §4.5。
- **问题**：pick_invest 文件已随投资两屏迁移批删除，例句所谓「现役」早已不现役——承袭过期（attack2 已注记，至今未入清单）。兜底措辞 grep 含「发射相/落地相」会命中该句、且兜底条目是清单强制项（「← 收尾」），故 worker 有 mandate；风险仅在「兜底被读成可选扫一遍」时漏改。
- **权威源证据**：action_ops.md :22 实文；src 无 pick_invest.py（grep 零命中）。
- **建议修法**：action_ops 条目补「§1 :22 例句换现役反例或不举例」。
- **严重级**：微。

### 微注记（不计发现数）

- design §2.1「`pick_planner.py` +63 行」：commit 14dd40977 stat = 该文件 72 变更行（增删混合）——精确行数不可核，无实质影响；建议正本化时删行数或写「约」。
- README.md 进度面未列 attack5.md（报告链接止于 attack4、「第 1-4 轮」）——README 仅上下文非攻击对象，仅记同步 nit。

## ③ 全量同步复查结果表

| 核对面 | 结果 |
|---|---|
| design §1↔§2↔landing 三阶段覆盖 | ✓ §1.3 解决/不解决面与 3.1/3.2/末阶段范围互恰；不解决面（upgrade 语义/classify_planner_leg/零写族屏/decide_equip_overlay_pick）landing 均未越界；§1.3 之外未发现漏 declared 面 |
| 依据逐条对码（§1.1 现状锚） | ✓ pick_planner.py :86-:104 四分支/evidence 门/:63 常量自持注释、pick_equip.py :40/:55、yinlang :204-:222 重入裁决出口+`_pending_leg`/`_pick_param`、equip_pick :125-:138+`_pick_pending`/`_pending_pick`、PickPlannerOp :408 置位、PickEquipOp 发射相 :609-:615 全部实存且如述 |
| `normalize_registry_equip_name` 复用（T-1 已建） | ✓ cw_events.py :951 实现现盘；supply 先例 cw_screen_supply_node.py :304 在用；`normalize_equip_name` 本体 :930 不动、src 唯一组装点消费 = equip_pick :47/:168，无过度 |
| cw_vocab 注释连带三处 | ✓ :733（supply norm_item 引 `normalize_equip_name` = T-1 后过期，supply 实用 registry 入口）+:735-:736（supply 两相措辞）+:906-:911（equip 两相措辞）三处实在 |
| joy 收口序事实化 | ✓ commit 14dd40977 在主仓（rider + weaken 退役 + `unrouted_leg_zero_write`，commit message 自证）；`classify_planner_leg` 现役仅产 upgrade/equip/unknown（cw_events :994-:1026，无 weaken 分支）——「弱化词卡文落 unknown」口径与实码一致 |
| sig actor 换名申报 | ✓ 现役落地相 actor='CwScreenEquipPick'/'CwScreenYinLang'（两画面 op :135-:136/:217-:218），单相化后动作 op 类名（type(self).__name__ 先例在码）；§2.0 一句申报在册 |
| 测试面（attack5 新增） | ✓ unified_action_4 :322 名/:333 桩/:339 断言、two_node_family :346（round_wait 断言，随派发即终结须同改）/:348、gain_chain import :41 + 恰 10 处 evidence 调用、t60 EQUIP_EVIDENCE 面（:40 import + :127/:218）——行号逐个相符；t60 :156 emission-intent-only 测试属 3.1「受影响测试」面（「含」非穷举，可开工） |
| grep 三段式口径一致性 | ✓ design §3 验收锚 3 与 landing 兜底同口径（src + sr-od-test + docs 正本；豁免 changes/） |
| 正本清单条目节/行真实性 | ✓ logic-updates/pick-planner.md :3（两相上报+changes 引用）/​:11/:13/:14（evidence=EVIDENCE_OVERLAY_CLOSED+重入裁决表述）/​:17（weaken 行——与现役代码不一致主张成立）/​:23/:33/:37（「单一定义在 pick_invest」过期句）/​:41 逐行实在且完备（:15-:16 腿语义子行随 §2 节头重构覆盖）；planner.md §2(:12)/§4(:24,:29-:39)/§5(:48-:49)/§6(:55)/开放设计注(:76) 五处实在；equip_pick.md :24/:26/:52 在；action_exec :24「策划/补给/装备」句 + supply 复核在；screens/README §5.5(:109)/§6(:138) 在；op-layer :43/:33/:96/§3(:88) 在——例外 = S3（:36 漏） |
| 例外 = S1（design↔landing 措辞）/S2（env docstring 归属）/S4（action_ops §1 :22） | 见上 |
| 消费点迁移总表完备性（全仓 grep 复核） | ✓ `EVIDENCE_OVERLAY_CLOSED` src 恰 4 文件（两定义两消费）+ 测试 3 文件（t60/phase32/gain_chain）——与总表一致无遗漏无过度；`_confirm_pending`/`_pending_leg`/`_pick_param` yinlang 本文件 + planner op :408（partner :355/fortune/deploy_not_full/wish_trial/bookcard/expert_invite/obs_arch 测试同名属彼屏，表已限定「（yinlang）」+「CwActionPickPlannerOp 体内置位」）；`_pick_pending`/`_pending_pick` equip_pick 本文件 + two_node_family :348（bookcard/expert_invite 同名异类型属彼屏） |
| 规范遵循（action_ops §1 三裁定 + op-layer §1.4） | ✓ 增补 2（点完即写/禁验证禁判重——§2.0/§2.3 显式承接且 upgrade 重复应用修正论据与 `_apply_upgrade_transform` 二次上报 count=0→`planner_upgrade_source_missing` 实码一致）；增补 3（动作 op 零新增读屏——confirm 定位走 area_center/emit_overlay_confirm 机械确认，归一组装留画面 op）；原裁定禁验证 ✓；op-layer §1.4 形态契合 ✓ |
| 时序等价论证 | ✓ 成立——旧时点（重入裁决 OCR 后）与新时点（确认点击后）之间唯一中间操作 = 重入 OCR（round_by_ocr，零容器写），「两时点之间容器零写入」主张与实码相符；论证同时覆盖 joy rider（同窗零写） |
| README 反查 | ✓ 链接/阶段数与 design/landing 一致（attack5 缺列 = 微注记） |

## ④ 试读结论（逐阶段）

- **3.1（equip）实现 worker**：**可开工**。单相 report 改法、换源入口、删闩删出口门、行为锁三型、t60/two_node_family 受影响面、grep 判据均可凭现稿直接落码。卡点仅 S1（表行措辞与验收锚矛盾，worker 需辨析取 §3 口径）。
- **3.2（planner）实现 worker**：**可开工**。report 单相化四分支逐位保持、rider 挂点保持、置位删除、三测试文件改写指令明确。卡点仅 S2（env docstring 归属，默认不改无行为危害）。
- **末阶段（正本更新批）worker**：**可开工**。清单条目节/行锚全部实证可执行；兜底 grep 三段式口径两文档一致。缺口 = S3/S4（两句级补清单，不阻碍其余条目执行）。

## ⑤ 零发现面声明

以下经本轮全新攻击后**零实质发现**：方案层单相化契约本体与统一模板贴合；两屏拆两阶段与串行依赖；equip 归一升级主张（泛用件/银狼 10 件锚恒 ''/fail-closed 同构）；planner 归一不升级的定性（腿型分类器副产品）；upgrade 三态+档行逐位保持；joy rider 双仓事实与收口序；增补 2 第 4 条不设防取舍；planner 载荷 env kwargs 不迁 param；零写族屏不迁移边界（op-layer §2.2 合法形态）；验收锚 1/2 行为级可判性与判据可满足性；`_confirm_pending` 等符号的同名异屏无过度退役；边界完整性（§1.3 之外无漏 declared 面）。
