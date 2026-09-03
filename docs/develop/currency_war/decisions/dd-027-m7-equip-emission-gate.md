# DD-027: M7 装备转移发射门——持有面谓词换变换面谓词 + 备战期装备闩

- 状态: accepted
- 日期: 2026-09-04
- 关联: DD-020(序列决策契约)、dd-016(执行守卫)、ADR-0387(owned 快照全量含工具件)、2fa50afb(备战期开店闩,同构先例)

## 1. 背景与问题(实机活锁事故)

2026-09-03 23:47 起实机局(局起点 23:26)备战面进入 RunEquip 环:外循环每轮
重识别备战画面 → 策略发射 `[RunEquip]` → 执行侧 `CwOpEquipAll` 0 穿成功返回
→ 交回外循环 → 无限重复。日志实证(`.log/mcp_server.log.2026-09-03`,
23:47–23:59 窗口 204 次,跨越 00:13 stop_run 终局):

```
[cw-equip] 无穿戴候选(count=2,全工具/空)→ 停
[cw][director] RunEquip → ✓ 装备 M7 装备 0 件(角色级分配)
[cw-loop] 备战环返回(success=True status=序列完成(RunEquip),…)
```

卡死画面: `.debug/sr_od_mcp/screenshot/screenshot_20260903_235357_473679.png`
(备战 1-6,回合数与金经全窗口无变化)。该局战利品只剩 2 件**工具类**装备
(拆装扳手/冶金炉一类,注册表 `category='工具'`,机制上不可 drag 穿戴)。

## 2. 根因(证据链钉死)

`mandate.run_mandate` M7 发射位修复前为:

```python
if getattr(session, 'last_owned_equips', None):   # 非空即发
    out.append(Emitted(RunEquip(), True, 'm7_equip_transfer'))
```

三步定谳:

1. **谓词是持有面**: `last_owned_equips` 的写端(cw_op_equip_all 每次现读
   覆写,ADR-0387 定谳**全量含工具件**——采集层无权丢数据)保证只要有任何
   装备在库(含永不消耗的工具件),列表永非空 → 谓词永真。
2. **执行侧零变换**: CwOpEquipAll 的穿戴决策过滤工具类(与 owned 快照写端
   口径相反,by design)→ 工具-only 库存下每轮 0 穿成功返回。
3. **空批出口被封死**: entry 侧 StartBattle 只在动作批为空时发射;M7 每帧
   恒发 RunEquip ⇒ 批恒非空 ⇒ 出战永不可达,备战环活锁。

前一起卡死(M2 每帧重燃 OpenShop)由 2fa50afb 备战期开店闩修复;闩生效后
批内开店意图消失,恒非空的 M7 发射位成为下一个(也是最后一个)挡在空批
出口前的发射位——本环是闩的**暴露效应**,非闩的回归。

## 3. 修法(Why)

M7 发射门改为**变换可能性两件套**(mandate.py 内,dd-027):

1. **可穿存在性 `m7_wearable_exists(owned)`**: owned 存在注册表已登记且非
   工具类的件。持有面谓词换成变换面谓词——M7 的领域是「穿上会改变装备
   分布」,发射条件必须是该变换存在对象。未登记名按不可穿保守侧,与执行
   侧 wearable 过滤同口径(EQUIPMENTS 命中才进穿戴决策)。
2. **备战期闩 `cw4_m7_equipped_phase`**: 同 (plane, round) 备战期只发一次,
   发射时置闩,位面/轮次推进自动失效(新发放件重评)。与开店闩同构论证:
   执行侧一次完整穿戴 pass 信息完备(内含稳帧/补救链/拉黑/分配归因),
   期内重开输入不变结果不变;本闩额外兜住门①盖不住的零变换重燃变体
   (过渡期 hold 全攒着/分配方案空/拖拽对全拉黑——可穿件在但穿不动,
   同样会 0 穿重发)。跳过计数 `equip_latch_skip_m7`。

**为什么不是加冷却**: 闩键 = (plane, round) 语义相位,非时间;失效条件 =
游戏状态推进,与开店闩同一「决策推论非禁令」语义。门①+门②缺一不可:
只有门① 则 hold/拉黑变体仍活锁;只有门② 则工具-only 库存每期仍白跑一次
~15s 的装备 op。

### Considered Options

- **(采纳)门①+门②**: 治本(谓词换域)+ 防重燃记账(闩,先例 2fa50afb)。
- 只清账(发射后清空 last_owned_equips): 回归——快照写端每轮覆写,清了
  再生;且破坏 ADR-0387 全量采集语义(遥测/特征消费面依赖持有面真值)。
- 执行侧改(0 穿返回 fail): 把决策层谓词错误推给执行层 fail-stop,外循环
  retry 链照旧重发,活锁换形态;且执行层无法区分「该穿没穿成」与「没对象可穿」。
- 只门①(变换面谓词): 修掉本次事故形态,但 hold/拉黑等「有可穿件但穿不动」
  变体在实机多帧备战环同样成环(sim 单回合决策不可见),留门②兜住。

## 4. 影响

- 消费面: 仅 entry.py prep 路径调 `run_mandate`(shop.py 只用 MandateFrame
  算成本,不调);sim 同路径单回合决策,闩不触发,行为零漂移。
- `last_owned_equips` 其余消费面(adapter/expected_state/telemetry)不读
  发射门,零影响。
- 回归锁: `sr-od-test/.../test_cw_m7_equip_gate.py` 9 用例(工具-only 不发/
  可穿发射/混装发射/未登记名保守侧/同期一次+计数/推进重武装/发射才置闩/
  与开店闩双向独立)。
- 遗留平行源声明: `'工具'` 类名常量(EQUIP_TOOL_CATEGORY)与执行侧
  `_TOOL_CATEGORIES` 同值平行(执行侧文件不在本批文件面),单一源化归后续批。
