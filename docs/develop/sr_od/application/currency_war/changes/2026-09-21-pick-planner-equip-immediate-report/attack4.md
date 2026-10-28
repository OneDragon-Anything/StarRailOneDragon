# 第 4 轮对抗审查(核一·无前提攻击)

审查对象 = design.md / landing.md 现稿(2026-09-21-pick-planner-equip-immediate-report)。方法 = 逐项对码对正本实读核证,不锚定 attack/attack2/attack3 结论(仅用于核对历轮发现是否真清偿)。

## ① 总判

**需修订(不可定稿)**:发现 4 条,阻塞 1 条。方案主体(单相化契约、逐屏差异、时序等价论证、分支类型实码四分支口径、joy 收口序事实化、消费点迁移总表)经逐条对码核验成立;attack/attack2/attack3 的 10 项发现在现稿中逐项核对**均已真清偿**(F1 清偿核证 = test_cw_gain_chain import+10 调用已入 §2.2 表与 landing 3.2;F2 清偿核证 = logic-updates 条目扩至 :3/:23/:33/:37/:41;F3 = two_node_family :346/:348 入 landing 3.1 文件面;F4 = joy 收口序事实化,commit 14dd40977 实在,`+63 行`与 numstat 63/9 精确一致;F5 = cw_vocab docstring 措辞面入 landing 3.1;F6 = README §6:138 入清单;F7 = supply 注释 :733 实在)。唯一残留缺口 = `logic-updates/pick-planner.md` 正本更新条目清除面仍漏 §2 三行(attack3 F2 同形态第 3 犯),修毕即可收敛。

## ② 逐条发现

### F1 [阻塞] landing「正本更新清单」`game_state/logic-updates/pick-planner.md` 条目清除面漏 §2 :11/:13(两相/发射相表述)与 :17(weaken 零记账行)

- **位置**:landing.md「正本更新清单」第 7 条;design.md §1.1 症状 3「正本…残留分相表述…正本更新批收口,见 landing 清单」。
- **问题**:实读该文件,条目列清除面 = 文件头(:3)/§3(:23)/§5(:33)/§7(:41)/:37 过期句。**§2 逻辑态域集节遗漏三行**:
  - :11 「**两相**(上报宿主 = …与 pick_invest 同构)」节头;
  - :13 「**发射相**(evidence 缺省…):意图遥测日志行,容器零写」bullet;
  - :17 「**unknown**:零记账 + 留证行;**weaken**:零记账」——weaken 分支已随 commit 14dd40977 删除(`classify_planner_branch` 现役 cw_events.py :994-1026 无 weaken 产出,实码核证),该行**现在就已与代码不一致**,本批清两相时若不同步清即持续违反 AGENTS §9「正本必须自足、与代码现状一致」。
  三行均无 `EVIDENCE_OVERLAY_CLOSED` 字面量(兜底 grep 一段抓不到),也不在 action_ops §4.5 / action_exec §2(兜底 grep 二段的限定范围)——按清单字面执行 = 永不清除。:14 落地相 bullet 含常量字面量,兜底可抓,不在本条指控内。attack3 F2 指控清单已含「§2 :13 发射相 bullet」,现稿修订收编了 :3/:23/:33/:41 却**仍漏 :13 与节头 :11**,且本轮新增 :17 weaken 失真行——同错误形态第 3 次出现。
- **权威源证据**:`docs/…/game_state/logic-updates/pick-planner.md` :11/:13/:17 现文;`src/…/kernel/cw_events.py::classify_planner_branch`(:994-1026,无 weaken);commit 14dd40977 message「删 weaken 分类分支与常量(含弱化词未知名卡文落 unknown)」。
- **建议修法**:该条目清除面补「§2 :11(两相节头)/:13(发射相 bullet)/:17(weaken 行随弱化兜底档退役一并清)」;或在兜底段为该文件加「两相/发射相/落地相/weaken」措辞 grep。修法一句话即可,不动代码面。
- **严重级**:阻塞。

### F2 [建议] cw_vocab 注释连带「三处」面只在 landing 全列,design 总纲未回写(docstring 措辞面无 design 依据锚)

- **位置**:design.md §2.1 equip 段(仅「CwActionPickEquipParam.norm_item 字段注释」)与 §2.2 表(仅 supply 注释行)↔ landing 3.1「注释连带三处(含 attack3 F5 的两 param docstring『两相/落地相』措辞机械改写)」。
- **问题**:attack3 F5 的修复落点只在 landing;design §2.1/§2.2 无 docstring 措辞面。landing 3.1「设计依据」引用 design §2.2 表,而表内无该面——两文档对该子面不同步。landing 是账本唯一源、面已列全(:735-736/:910-911 实在,核证),worker 按 landing 可执行,故不阻塞;但 design §0 自称「深度 = 实现者无需再设计」,只读总纲者会漏该面。顺带:design §2.2 equip 行测试修法写「改断言『确认点击后容器即持效果』」,equip 屏无确认步(landing 3.1 已自我勘误「『确认点击后』措辞不适用于本屏」),design 侧措辞未同步。
- **权威源证据**:cw_vocab.py :735-736(supply 落地相/两相措辞 + :733 `normalize_equip_name` 过期引用)、:910-911(equip 落地相/两相措辞)——三处实在;landing 3.1 vs design §2.1/§2.2 文本对照。
- **建议修法**:design §2.2 表 cw_vocab 两行合并为「三处注释连带」并与 landing 措辞对齐;equip 行测试修法措辞改「点卡后」。
- **严重级**:建议。

### F3 [建议] 单相化后效果分支上报的 ChannelSig actor 静默换源未申报

- **位置**:design.md §2.1 两个新调用形 / §3 验收锚。
- **问题**:现落地相效果分支上报 actor = `'CwScreenYinLang'`(cw_screen_yinlang.py :218)/`'CwScreenEquipPick'`(cw_screen_equip_pick.py :136);单相化后仅剩动作 op 内调用,actor = `'CwActionPickPlannerOp'`/`'CwActionPickEquipOp'`(照现发射相形)。效果分支遥测/缺陷行的 actor 字段全量换值,设计零申报。供给/投资迁移批同款变化已被先例接受,方向无碍;属「应写一句的遥测面变化」,非行为缺陷。
- **权威源证据**:两画面 op 现调用点 sig 构造 vs cw_overlay_pick_action.py :424/:613 发射相 sig 构造。
- **建议修法**:§2.1 各屏一句「效果分支上报 sig actor 随调用点迁移动作 op 名(先例 = 供给/投资迁移批)」。
- **严重级**:建议。

### F4 [建议·存量] screens/README.md :36 统一形态句「决策动作 node = 重入裁决 + 决策 + 动作」缺「仅限未迁移屏」限定

- **位置**:screens/README.md :36(§3 画面形态概述段);landing 清单只列 README §5.5 与 §6:138。
- **问题**:op-layer.md :21-22/:33 已带「仅限未迁移屏/已迁移屏 = 派发即终结」限定,README :36 无——本批 equip/yinlang 迁出后该句对 13 屏中的 6 屏(equip/yinlang + 已迁 4 屏)失真,清单与兜底 grep 均不覆盖。属承袭存量失真(投资/补给/遭遇批已造成),非本批引入,量级低。
- **建议修法**:正本更新批顺手给 :36 补同款限定词,或显式声明存量豁免。
- **严重级**:建议。

## ③ 全量同步复查结果表

| 检查项 | 结果 |
|---|---|
| EVIDENCE_OVERLAY_CLOSED 全域 grep(自行复核) | src 恰 4 文件(pick_planner :63 定义+:12/:74/:86、pick_equip :40 定义+:9/:48/:55、yinlang :49/:220、equip_pick :44/:137)✓;测试 t60 EQUIP_EVIDENCE 面(import :40 + :127/:218)✓、yinlang_phase32(import :55 + 恰 10 调用,「10+ 处」✓)、gain_chain(import :41 + 恰 10 调用)✓;docs 正本命中 = logic-updates :14/:37、planner.md :24/:55、equip_pick.md :24/:52——**全部在清单或兜底 grep 覆盖内** ✓;changes/ 豁免申报 ✓。判据「全域 grep 零命中(豁免 = changes/)」按字面可达 ✓ |
| `_pick_pending`/`_pending_pick` | equip_pick 本文件(:74/:79/:125-129/:169/:180)✓;bookcard/expert_invite 同名属彼屏,表已限定 ✓;**two_node_family :348 已入 landing 3.1 文件面(:346/:348,实文核证 = round_wait 断言 + 置位断言,单相化后均须改)** ✓;无遗漏无过度 |
| `_confirm_pending`/`_pending_leg`/`_pick_param` | yinlang 本文件(:108/:113/:116/:204-211/:255-256)+ pick op 置位 :408 ✓(均入表);:355 置位属 CwActionPickPartnerOp(伙伴屏),表已限定 ✓;wish_trial/partner/fortune/deploy_not_full 同名属彼屏 ✓;无遗漏无过度 |
| `normalize_equip_name`(equip 组装点) | equip_pick :47 import + :168 组装点 ✓;`normalize_registry_equip_name` 在册(cw_events :951,158 键分层归一,docstring「补给侧」措辞与本批复用无冲突——语义纯函数可复用,设计申报「T-1 已建入口」✓);本体与银狼域消费面不动 ✓;planner 侧 classify_planner_branch 副产品 norm_item 不升级(设计 §2.1 明示)与实码 :1010-1011 口径一致 ✓ |
| cw_vocab 三处注释 | :733(supply norm_item 引 `normalize_equip_name` = T-1 后过期)+ :735-736 / :910-911(两 param 落地相/两相措辞)实在 ✓(分布 → F2 同步缺口) |
| cw_overlay_pick_action 模块头 | :15-24「三线例外」自述段实在,含 pick_invest/pick_equip/pick_supply 分步自述(invest/supply 已迁现役失真、本批后 pick_equip/pick_planner 亦失真)✓;3.1 不动/3.2 改写分工明确 ✓;CwActionPickEquipOp.run 发射相注释 :606-608 随 3.1 体改 ✓ |
| 分支类型实码口径 | `_apply_equip_branch`(命中入栏+后果链 / '' 翻来源留证)、`_apply_upgrade_transform`(三态:恰一枚变换+档行 :254-273 / 多枚翻来源留证 / 零枚·未观察 `planner_upgrade_source_missing` / 现档≥5 封顶闸)、unknown 留证、unrouted 兜底零写——design §2.1/landing 3.2 四分支表述与实码逐分支一致 ✓;§2.3「二次上报走零枚分支、档行不 +1 两次」论据与 :232-237 实码一致 ✓ |
| joy 收口序事实 | commit 14dd40977 实在;pick_planner.py numstat = **+63/−9**(design「+63 行」精确);`_grant_joy_conditional` 挂落地相门(:94)、rng 形参在;现落地相调用不传 rng(yinlang :214-220),单相化后 op.run 调用同不传 rng → rider 行为逐位等值 ✓;test_cw_gain_chain import+10 调用实在 ✓ |
| 权威源条目节/行真实性 | action_ops §1 增补 2(:11)/增补 3(:13)/§2.3 欠账标注句(:59)/§4.5(:117-135,PickPlanner/PickEquip 两行 + 欠账标注段 :119)✓;action_exec §2 :24 原文与 attack2 F1 引用一致、「supply 确认行」= :33 ✓;op-layer :21-22/:33/:36-38/:43/:87-89/:96 ✓(§3 节点循环行 = :88,含 CwScreenEquipPick/CwScreenYinLang,landing「§3 节点循环行分型判据更新」有实锚);screens/README §5.5(:107-109)/§6(:138)✓;planner.md :12/:24/:29-40/:48-49/:55/:76 与 landing 五处清除面吻合 ✓;equip_pick.md :24/:52 ✓;op-layer §1.4/:43、§2.1/:51-55、§2.2/:78 chosen 留守规则与 design §1.3「零写族不解决」申报一致 ✓ |
| design §1↔§2↔landing 三阶段边界 | 3.1(equip)/3.2(planner)/末阶段(正本)互斥完备;§1.3 之外未发现漏 declared 面;文件面路径全部真实存在 ✓ |

## ④ 试读结论(逐阶段)

- **3.1 worker(equip)**:可开工。范围/文件面/行为测试三型(命中/未解析/泛用件)/受影响测试(含 two_node_family :346/:348、t60)具名,归一换源目标符号与语义(fail-closed)明确,无「待定/酌情」项。
- **3.2 worker(planner)**:可开工。四分支逐位保持 + joy rider 挂点保持 + rng 等值性(单相调用点同不传 rng)可从现稿推出;test_cw_gain_chain 机械改写面精确到 10 处;模块头改写归本阶段明确。
- **正本更新批 worker**:除 F1 所指 `logic-updates/pick-planner.md` §2 三行外可开工——该文件条目按现稿字面执行会漏 :11/:13/:17,且兜底 grep 双段均不兜底(阻塞点);其余 8 条清单条目锚位全部实核在册。

## ⑤ 零发现面声明

以下面经本轮全新攻击**零实质发现**:单相化统一契约与增补 2/增补 3 合规性(动作 op 零新增读屏——confirm 定位/点卡定位均现状保持);时序等价论证(upgrade 前置校验两时点间容器零写,论证成立);消费点迁移总表完备性(src+test 口径无遗漏无过度);equip 归一升级取舍(泛用件缺陷论证、fail-closed 同构);planner 载荷 env kwargs 不迁 param 取舍;增补 2 禁止清单第 4 条「重复应用不设防」的 upgrade 后果修正论据;验收锚 3 grep 口径可达性(豁免 = changes/ 已申报);三阶段依赖序与并行批(tool-gain-report/shop-refresh-terminal 非本批面)边界;joy rider 提交事实与收口序三步。
