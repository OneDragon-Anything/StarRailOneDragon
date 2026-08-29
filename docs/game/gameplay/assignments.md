---
gameplay_name: 委托(派遣)
app_id: assignments
last_updated: 2026-07-29
source: WebSearch 攻略 + `application/assignments/` 代码 + phone_menu 委托子态 area
involves_screens: [菜单]
---

# 委托 / 派遣(assignments)

派遣角色做任务(按时间),自动积累材料。日常挂机收益。**不消耗开拓力**(只消耗时间)。解锁:开拓等级 13+。

## 玩法机制(攻略)

- **委托**(派遣):派角色(2 名/项)做任务,选委托时间,自动积累材料。
- **槽位**:至多 **4 项委托**(4 槽位)。每小时按所选委托积累奖励。
- **领取**:随时领取;领取后委托**持续运作**(无需重开)。
- **流程**:菜单「委托」→ 选材料类型对应委托 → 选委托时间 → 派遣角色 → 执行委托。
- 收益相对低(挂机补充),急需材料刷怪 / 模拟宇宙更高效。

## bot 流程(`application/assignments`)

`AssignmentsApp` 领奖励流程(节点):
- `open_menu`(开菜单 → 点「委托」)→ `_click_assignment`(点委托项)→ `_check_status`(检测状态:派遣中 / 可领取)→ `_claim_reward`(领取奖励)→ `_click_empty`(点空白关闭弹窗)→ `back_at_last`(返回)。
- `back_at_first` / `back_at_last`:流程首尾返回。

## 画面

2026-08-29 起有独立 screen 档(见 [screens/委托](../screens/委托.md));此前挂在 phone_menu 委托子态。要点:
- 识别锚:左上「委托」标题;「领取奖励」亮/灰=可领判据;三个材料分类 tab(选中白底)。
- 历史 area `菜单/委托-*` 仍被 `AssignmentsApp` 使用,未迁移。
- 交互实锤:tab 切换、领取奖励→获得物品弹窗;变更委托(派遣编辑)bot 不覆盖,出口未探。

## 备注 / 待查

- **已建档 fixture + 验证(2026-07-29)**:`screens/委托/委托派遣中.webp`(4 槽派遣中)。
  验证:实跑 `AssignmentsApp` **success**(委托 area 有效,**版本未大改影响**,无需修复)。
  测试 `sr-od-test/test/sr_od/application/assignments/test_assignments_app.py`(委托派遣中 →
  `_check_status` → STATUS_ASSIGNING)。**「委托可领 + `_claim`」分支 fixture 待条件**
  (委托有可领奖励时采;当前领完,派遣中)。
- **领取后持续**:委托领取后不重开(持续运作),bot 领奖励即可(不需重新派遣)。
- **4 槽位**:委托 4 槽位,bot 检测各槽状态(派遣中 / 可领)逐个领 —— 逻辑待 `_check_status` 细化。
- **委托 app 简单**:AssignmentsApp 仅领奖励流程(不派遣新委托,假设用户已配),派遣配置待确认是否 bot 覆盖。

## 参考来源

- [BWIKI 委托](https://wiki.biligame.com/sr/%E5%A7%94%E6%89%98)
- [百度经验 派遣方法](https://jingyan.baidu.com/article/dca1fa6f0bfabdb0a5405221.html)
- [9Game 派遣选择建议](https://www.9game.cn/bhxqtd/9473364.html)
- [3DM 派遣收益分析](https://ol.3dmgame.com/gl/233573.html)
