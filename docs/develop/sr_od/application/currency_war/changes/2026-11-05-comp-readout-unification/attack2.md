# comp-readout-unification 无前提复审报告（attack2，归档）

> 攻击者自选角度：全部数据声称脚本复算 + 教义逐篇对源 + 立法自洽性审查。
> 验证脚本留存 `.debug/temp/attack2_verify1.py`（_verify2/_verify3）可复跑。
> 必改四项（A2-1/2/3/4）与澄清五项（A2-5~9）已全部落修订；裁决与证据如下存档。

## 总裁决：打回修订 →（修订后）可定稿

1 阻断 / 3 需修订 / 5 建议澄清，修订量均为一段内小改。

## 阻断

**A2-1 批 B 分配器行为申报与代码事实相反**：arms 键空间 = cw_loop.py:1860
`share = {c.carry: c.n_posts / total for c in PLAZA_CARRY_CLUSTERS if c.n_posts >= 15}`
——n_posts≥15 的 17 个聚类 carry 名。fallback 三值（银枝/飞霄/桑博）无簇 ∉ arms；
另有 4 条非空线（巡海/龙丹/昼神/DOT，簇 8-12 篇）同样 <15 ∉ arms。防线
`arm_id not in self._allocator.arms`（cw_loop.py:1784）照拦 → 统一后三空值线记账
**仍恒跳过**，原申报「变正常累计」不发生。两分支悬念由攻击者一行代码裁决：键 =
carry 名（第一分支命中，arm_key_of ≡ carry_anchor 成立；第二分支「家族键」死）。
→ 修订：§3 悬写实测；行为申报改「三空值线 + 四低篇数线 update 维持跳过（值不在
≥15 键空间），第六处收编零漂移」。

## 需修订

- **A2-2** A2 确认状态三处口径分裂（design §0 / equip-projection / attack.md vs
  README）——「带开放问题的定稿不存在」的形式阻断；「attack.md 已归档」入状态行
  属过程叙事。→ 三处同步已确认口径。
- **A2-3** 批 C §3 漏「4 套已迁移套 key_equips 顺序翻转」：黄泉/大黑塔/反甲白厄/
  DOT队 手编序 ≠ 投影序（黄泉 manual [电锯,风暴潮,螺旋桨,永动机] vs proj [电锯,
  永动机,螺旋桨,风暴潮]）；退役后一律变投影序 → equip_allocation 按序取件在容量
  紧张帧取件先后微变。→ §3 补顺序维申报。
- **A2-4** 引文笔误「风力风暴潮」实为「火力风暴潮」（cw_comps.py:941 实值）。

## 建议澄清（已随修订处理）

- A2-5 读口清单「分配器 arm 键」落点改单落点 cw_run_allocator（cw_loop 仅改调）；
- A2-6 rating_anchor 落 line_select 补管辖域豁免说明（评分口径取攻略重述 = 策略
  立场决策，同策略旁表依据）；
- A2-7 景元「归属待核」消除——教义实有到人明文（final_longtail_others.md:81
  「装备:景元 风暴潮 19=电锯 19>皮靴 12;镜流 皮靴 7(速度→神君叠段频率)」）；
- A2-8 roster-hygiene 方案节编号乱序重排；
- A2-9 批 A 两行式 grep 正则单向性注明依据（复核现状确无反序形态）。

## 已核相符（免复审清单，全部实测/对源，详见报告原文）

14 处清单 + 2 合法内联；shared 16 读点分类；LINE_ANCHOR 21 行/火花唯一分歧/
全等校验；三条验证数据复算；8 套空 assign 名单；恒等测试全仓不存在 + docstring
三处指认 + 多重集口径现状全绿；core∩shared 18/21；「目标线 K」零命中证实；p41
vs telemetry 口径分裂证实；六处 carry 承载定位；W16 边界论证成立；教义逐字核对
（final_yinlang_joy:51 / final_dot_kafka:40 / 银枝/飞霄/千冶/巡海/龙丹条目注）；
鸭型桩；faction_migration_snapshots；正本锚全集；基线 9a1fc0cf8；landing 文件面
全实存；测试仓保留策略一致。

## 定稿试读结论

批 A 可开工；批 B 除分配器块外可开工（A2-1 修复后全可）；批 C 修 A2-2/3/4 后可
开工；批 D 可开工；末阶段可开工。
