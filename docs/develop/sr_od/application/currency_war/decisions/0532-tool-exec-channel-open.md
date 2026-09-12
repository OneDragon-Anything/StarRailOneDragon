# ADR-0532: 工具件消费执行通道建成开臂——RunTools 发射位 + CwOpTools 执行 op + 消耗确认通道

> 状态:已实施
> 出典:21 号稿 §3(工具件消费语义 v3)/§3.2(消耗确认通道)/§5(影响面);10 号稿 §2.1(工具判据收编源);ADR-0531(判据面先行,执行通道 fail-closed)。

## 背景与问题

ADR-0531 已落工具件消费**判据面**(`evaluate_tool_actions` 三道门冷启动分支 + `admitted_tool_actions` G1 发射位准入),但执行通道未建:`TOOL_EXEC_CHANNEL_READY=False` fail-closed,工具件(冶金炉/扳手等 7 件)在实机持续滞留无出口(第十五~十八局段跨局恒定形态,21 号稿 §1)。开臂判据挂账 = 工具拖曳 op 落码批交付(合法开关生命周期:strategy-work §3.3)。

## 决策

1. **消费语义定稿(判据挂 evaluate_tool_actions,零新判据)**:消费时机 = 门 A(备战期 owned 快照到达拍评估一次,不进跨轮计划);消费决策唯一入口 = `evaluate_tool_actions`(炉准入 = 死库存变现且非 m=1 专留;扳手闸/令牌/投影仪 fail-closed;特权卡 = key 含特权 ∧ 对应进阶成品在手)。本批不新增逐件判据——判据数学(P14 定理 2/3、门 B/C)单一源仍在 kernel 判据面。
2. **执行载体 = 新组合动作 RunTools**(不骑 M7 穿戴通道,21 号稿 §2.4-2 发射位不增殖纪律的例外面:这是新动作类的新发射位 M7.5,非第二装备发射位):
   - 发射位 = mandate_v1 M7.5:逐备战帧评估,`[cw!][tools]` 日志打拒因分键(21 号稿 §4 实机锚「评估有记录(消费或拒因分键)」),admitted 含 usable 才发;工具期闩 `cw4_tools_phase` 置位在**执行位**(`mark_tools_pass_executed`,与 M7 装备闩同型论证:单动作环下发射即置闩会闩烧而工具未消耗);
   - 执行 op = `cw_op_tools.CwOpTools`:G1 准入 → `plan_tool_drags` 逐件计划 → drag → 确认通道。炉目标 = `recycle_qualified` 死库存(与判据面同源同参,禁「画面首件」宽取 = 防误烧);特权卡目标 = key 特权件去后缀的进阶成品(栏内拖法)。
3. **工具消耗确认通道**(21 号稿 §3.2 硬门,四态登记+三分支):拖曳后 pre/post owned 现读对拍(`classify_tool_consume` 纯函数)——成功(工具∧目标全消)全量登记;部分消费按现读登记显影 `tool_partial_consume`;取消/落空全量不登记显影 `tool_consume_cancel`。漏做即重现 g_20260903_232823「永远清不掉」工具版。
4. **开臂**:`TOOL_EXEC_CHANNEL_READY` False→True。开臂判据兑现 = ①UI 建档前置以既有 owned 多列网格建档满足(工具 icon 与穿戴类同建档,「区域-道具装备」D-40,col2 冶金炉 click 实锤;炉/特权卡拖曳目标同为 owned 网格内 icon,无新画面,未走新增档)②CwOpTools 落码批交付。翻正后拒因分键仍分键可见(判据拒原样透传,准入拒仅通道回关时出现——对照锁 sr-od-test test_cw_equip_wear_semantics_21 G1 节重推为开臂/回关双态)。

## Considered Options

- **A(采纳) RunTools 独立发射位 + 执行位闩**:与 M7 装备转移发射门同构,单动作环语义自洽,拒因分键天然入遥测。
- B(弃) 骑 M7 RunEquip 通道内联执行工具:穿戴与工具消耗生命周期不同(闩语义/确认通道/拒因分键互相污染),且 M7 门①谓词刚因工具-only 库存修过活锁,复骑 = 回填同一活锁风险。
- C(弃) 无发射位,由执行 op 自评自执行:违反决策/执行分层(ADR-0461 裁定 3),执行层第二套时机判断 = 判据漂移源头。

- 锁面:sr-od-test `test_cw_tools_exec_channel.py`(执行链/确认通道/fixture 交互/发射位闩/词表)+ 21 号稿锁 G1 节开臂对照重推。

## 修订一(2026-09-06,三审 C1/三审阻断:执行环改 while 队列纯驱动)

- 初版执行环 for 遍历切片快照、循环内重赋 `plans` 为死代码:首件消费后
  reflow 使剩余计划持过期坐标拖曳,可误烧需求向量内件(烧毁不可逆,
  cancel 补救只覆盖拖曳落空,救不回已落错的首次拖曳)。
- 修订:执行环改 `run_tool_queue` while 队列纯驱动(模块级纯函数,离线可锁)
  ——每件 consumed/partial 后调 `replan_fn` 整条重建队列(fresh owned 现读
  + 重评 `evaluate_tool_actions`/`admitted_tool_actions`,坐标全现读);
  cancel 件直接丢弃不触发重规划(防 cancel→replan 同件死循环);
  `max_pass` 执行尝试硬上限防空转。载体 = ee59bfd0(+共享模板装载
  `get_equip_templates_cached`,63b6de5d)。
- 锁:多计划执行环 2 锁(双件帧重定位+无误烧断言/cancel 丢弃语义)+
  `test_runtools_reordered_before_truncation` 空锁改 M6 溢余真发射路径帧。

## 后果(初版)

- 工具件从「永久占 owned 快照」变为「可清账物件」;确认通道登记入 owned 期望态,对账端不再有幽灵件。
- 冷启动可执行件 = furnace_single / privilege_upgrade;扳手(去向登记制)/令牌(R(c) 缺档)/投影仪(冷启动分支外)仍 fail-closed,拒因分键照打,解锁各自候独立批。
- 验证边界(21 号稿 §4):拖曳执行与执行后对账不可 sim,验收走实机(首例「炉在 owned ∧ 评估有记录」局);sim 面只锁行为分布,后续批接 `TOOL_GRANT_INJECT` 注入基建。
- 锁面:sr-od-test `test_cw_tools_exec_channel.py`(执行链/确认通道/fixture 交互/发射位闩/词表)+ 21 号稿锁 G1 节开臂对照重推。
