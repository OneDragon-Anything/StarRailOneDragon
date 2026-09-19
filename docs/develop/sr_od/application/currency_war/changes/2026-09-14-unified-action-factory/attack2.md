# 统一动作工厂 对抗审查报告(第二轮·复核)

> 对象 = 修订稿 design.md/landing.md/README.md;参照 = attack.md(F1-F19+§六 8 项)、
> 修订回报 R1-R9/裁决1-3、地基正本 flow/action-logic-state.md。方法 = 8 项落文逐条
> 对稿核真 + R1-R9 交叉一致性 + 2a/2b 衔接试读 + 行号锚抽查(45+ 处, T-207 后现状)。
> 只读评审,不改文件(本报告除外)。

---

## 一、发现清单

### A1【landing §3.2a 文件面】批2a 漏 `kernel/cw_game_state.py`,逻辑态扩域落点不在施工面
- **问题**:2a 范围第 2 步明写「备战逻辑态建模扩域(`apply_prep_action_logic` 域集 +
  xp/level 的 LevelUp 分支)」,该写口与域集常量都住 `kernel/cw_game_state.py`
  (`PREP_PROJECTION_DOMAINS` :2082、`apply_prep_action_logic` :2085);但 2a 文件面
  kernel 侧只列 cw_vocab/cw_prep_actions/cw_deploy_logic/cw_exec_state,无
  cw_game_state。2b 面虽有该文件,标注仅「CompTransaction 提案分支删」。
- **修法**:2a 文件面补 `kernel/cw_game_state.py`(域集扩 + LevelUp 分支 +
  owned_equips/摘晶矿写口按 design §2.6 R9)。

### A2【landing §3.2a/§3.2b】LevelUp cost/auth_basis 装载批归属自相矛盾,2a 中间态 cost 源悬空
- **问题**:①2a 范围括号内出现「发射面 cost = xp_click_cost 现算,失读回退
  XP_CLICK_COST_FALLBACK」,而 2b 判据「LevelUp 装载锁(2b 半)」把同一件事列为
  2b 锁面——同一装载两批都申报;②2a 判据要「逻辑态 xp/level 推进」+ design 定案④
  逻辑态分支 = gold −cost,但 2a 阶段族B `LevelUp()` 无 cost 字段(2b 合并才有),
  中间态金腿取值源(执行缝 `_executed_gold_delta` 延续 or 写口现算)无文字,
  实现者必须自行设计。
- **修法**:2a 范围写死中间态(建议:2a 金腿维持执行缝金差、逻辑态只落 xp/level
  推进;2b 类合并翻转时金腿切 `action.cost` 直写,并把该切换补进 2b「消费面收口」);
  删 2a 括号内 cost 字样或注明「仅 2b 生效」。

### A3【design §2.6 R9 + landing 正本更新清单】枚举正本的转录义务悬空,LevelUp 行与定案相反
- **问题**:`flow/action-logic-state.md` 被申报为「批2/批3 实现规格来源」,但其 §3.3
  现状 = 「备战连点形态」+「apply_op_effect LevelUp 显式不推进(金账归执行缝、经验归
  XpLedger 观察)」——与 design 定案④(逻辑态直写 xp/level)**直接相反**;且 2a 落码
  后 §3.3/§3.7/§3.8/§4 分档全过时,但 2a/2b 范围与正本更新清单(8 文件)均不含该文档。
- **修法**:把「action-logic-state.md 同批转录(LevelUp 行按定案④;PickBoxCard/
  组合动作条目删;工具 7 类与 WearEquip 落 §4 形态)」写进 2a(或 2b)范围与正本
  更新清单;转录前 §3.3 加「待 2a 转录」提示行防误读。

### A4【design §2.6 锚点】cw_game_state.py 三处锚系统性偏移约 10 行
- **问题**:`PREP_PROJECTION_DOMAINS` 实际 :2082(稿 :2073)、`apply_prep_action_logic`
  实际 :2085(稿 :2076)、「同名异类禁混引」防线实际 :2113 附近(稿 :2103-2104)。
- **修法**:三处重锚(同文件同向偏移,疑 T-207 后又有他批改动)。

### A5【design §2.6 R7】「选卡决策半迁 kernel/决策侧」与现状有出入,落位文件未点名
- **问题**:`decide_box_card` 现役已在策略侧(`flow.py:656`/`cw_strategy.py:204`),
  打分单一源 `pick_equipment` 已在 `kernel/cw_equip_value.py`;真正待迁面 = 执行器内
  OCR 读卡名 + 调用编排(`_default_box_card` :1213-1250 的决策半)→ 新画面 op。
  「迁 kernel/决策侧」表述会让实现者误以为决策函数也要搬家;2a 文件面括号只写
  「穿戴计划/晶矿挑选的 kernel 模块选址随任务书」,未提选卡决策落位。
- **修法**:R7 改述为「OCR 读名与调用编排自执行器迁新画面 op,决策函数原位
  (decide_box_card 策略侧 / pick_equipment kernel 侧)」;或点名落位文件。

### A6【landing §3.3 判据】OpenBox terminal_wait 等价基准时点指代歧义
- **问题**:「terminal_wait 与现役开箱交回等待等价」——批2a 之前 OpenBox 不是终结
  动作,不存在「现役交回等待」;该基准实为 2a 落地后才有现行值,判据照字面
  不可机械验收。
- **修法**:2a 范围写死交回等待值来源(建议 = `_open_box` 动画等待
  `_OVERLAY_ANIM_WAIT_S` 或显式定值);批3 判据改「与批2a 落地值逐一等价」。

**观察级(不立案)**:「G1 准入」有代码在册出处(`cw_op_tools.py:1/:11/:206`,
ADR-0529),非会话黑话;T-203 在仓内无引用,迁移清单三面与 T-192 判效拆除保留面
(`cw_refresh_shop_action.py:132` 「留证遥测半(候选 a)」)对应,批4 全仓扫描兜底
闭环;R7 批次归位/批4 锁面「以实际元组为准不记账目数」防数字漂移,成立。

## 二、attack §六 8 项落文核对表

| # | 项 | 结论 | 核对要点 |
|---|---|---|---|
| 1 | 合并清单按代码真值重写 | ✅ | 四行「族A 原样」:SellBench 五字段含 convert_reason 且顺序与 `cw_vocab.py:367-383` 逐字一致;LevelUp cost+auth_basis;SellDeployed 执行边换算;DeployMove faction/to_row 保留+发射位现取+零构造死类如实披露;家族树 CwAction+metadata 逐字段裁定+action_key 前后对照锁(F1/F2/F3/F12) |
| 2 | LevelUp 粒度定案 | ✅ | 唯一形态六条全落(单击语义/每帧一击+clicks_to_next_level 门/cost+auth_basis 口径/域集扩 xp/level+xp_apply_clicks/授权归属逐项/M2+posture+m1p 逐项);接缝残留见 A2/A3 |
| 3 | StartBattle/OpenShop 裁定 | ✅ | OpenShopOp execute=AssertionError+read_only 动作字段(:2415 分支核真)+terminal_wait 3/1.0(:1747-1754/:1959-1963 核真);StartBattle 在册例外+消费面+退役挂账 A6(F8/F9);OpenBox 基准见 A6 |
| 4 | 批2 文件面+import 策略 | ✅ | cw_prep_expect/cw_exec_state/cw_game_state/cw_loop/decision_assembly/sim 三 import 位全入 2b 面;「一次翻清不留 shim」写死;SELL_BENCH_* 迁居 cw_vocab(F4/F11);新遗漏见 A1 |
| 5 | 判据修正 | ✅ | 2b 序列不变限商店域(备战域由 2a 对照锁+形态锁承接,F14-7);换算收口=两边界各一处函数化+发射/决策面散点零残留(F10) |
| 6 | 跨批判读口径 | ✅ | 改名键清单(slot→bench_idx)+值域换算式(−1)+兼容窗落点(query/journal_query/tools/cw 双键)+「前后档不可直比」申报(F7);与 R1 不冲突(退役类旧数据可弃≠在役动作改名键) |
| 7 | 锚点勘误 | ✅* | 45+ 处抽查:词表 13 类/两链辖 12(组合 4+直执行 8,代码逐支清点)/OpenShop 流程层截流口径全对;:990/:1023/:1267/:1355-1356/:2082 侧(:2073 除外)/:2323/:2415/:1148/:106/:612-838 等几乎全中;仅 A4 三处偏移(F5) |
| 8 | 流程面 | ✅ | 末阶段依赖=批1-批4 全部(F16);README 阶段 0/6(批2 拆后自洽,F17) |

F1-F19 无漏网、无走样;F18(七件齐)/F19(无过程叙事)维持通过。

## 三、R1-R9 一致性结论

- **无裁定间冲突**。R1(退役=删)vs 批4 注册完备锁:类不在元组即不可复活,自洽;
  R1 vs 遥测兼容窗分属两类(退役类可弃/在役动作改名键建窗),不矛盾。
- R7 OpenBox 终结化 vs 批3 terminal 等价锁:2a 定值→批3 锁等价迁移,结构自洽
  (仅 A6 时点表述歧义);2a 交回机制(结束判定集合加 OpenBox)→批3 改读
  op.terminal,行为连续。
- R9 废除保守回退 vs 枚举文档 G1-G9:语义一致(枚举文档把「交回」降为缺口闭合前
  过渡手段并逐条带补档方法;G 缺口保守记账≠未建模回退分支);但规格来源时序冲突
  见 A3(唯一实质接缝)。
- 裁决3 零比对 vs 保留面迁移:三面清单与在册留证面对应,批4 扫描兜底「漏面不合格」,
  prep 域「零留证比对面」主张与 CV-diff 批2 删 + 工具对拍随原子化承接一致。
- 裁决2 拆分:依赖链 2a←批1+枚举文档 cond、2b←2a、批3←2b、批4←批3 清晰;
  两节点判据各自可独立验收(2a 七锁、2b 八判据+回归门);唯一悬空 = A1/A2。

## 四、试读终审

- 批1:**可开工**(env 协议/注册表/薄委托/「不含」清单/文件面齐)。
- 批2a:**补 A1/A2/A3 文字后可开工**(其余步骤——扫描、原子通路、ClickSpheres、
  武装箱全链、EXHAUSTION 重推——凭稿可施工)。
- 批2b:**可开工**(归一删除/换算收口/装载锁/兼容窗/sim seed 锁齐)。
- 批3/批4:**可开工**(裁定/等价锁/锁面形态齐)。

## 五、定稿判定

**仍差清单(可一次收敛,无方向性问题)**:A1(2a 文件面补 cw_game_state.py)、
A2(LevelUp 装载批归属写死+2a 中间态 cost 源定案)、A3(枚举文档转录义务落进
2a/2b 与正本更新清单)、A4(三锚重锚)、A5(R7 迁移面改述)、A6(OpenBox wait
基准时点写死)。骨架、合并清单、两线裁定、判据体系、流程面均已收敛且与代码
真值对得上;补齐 A1-A6 复过一遍批2a 试读即可定稿。
