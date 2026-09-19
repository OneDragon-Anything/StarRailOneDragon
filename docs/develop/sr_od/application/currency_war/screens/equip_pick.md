# 选择装备三选一(equip_pick · 货币战争-选择装备)

> 代码 = `operations/cw_screen/cw_screen_equip_pick.py::CwScreenEquipPick`(两 node 直继承 `SrOperation`)。职责:选择装备 overlay 一次访问——OCR 卡名 → 锁线契合打分 → 点卡即选(无独立确认钮,出战按钮由主流程处理)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_equip_pick.yml`。

## 1. 分发判定

- 外循环分支 0a0:**双 id_mark 门**——「货币战争-选择装备.标识-选择装备」∧「货币战争-选择装备.标识-请选择1个装备」同帧命中才派发(副题「请选择1个」与选择伙伴屏共享,单锚会误派)。
- 分发 = 阶段一身份行;与列车同行的历史碰撞(共享「请选择1个」副题位)由列车同行整行副题锚消解,单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1);**本屏无 op 内入口门**(入口判定归主循环 0 系分发双 id_mark,分发即门):观察 node = 三卡位 OCR 一次读 → `report_screen_equip_pick_obs` 落容器 `equip_pick_opts` 槽 → obs 挂实例属性;决策动作 node = 顶部重入出口门(`_pick_pending` 置位 → 「请选择」不在 = 点卡即选已落地 → success 交回)→ 零参决策 `match.strategy.decide_equip_pick()`(候选自容器槽;判据单一源 = kernel `cw_equip_value.py::decide_equip_overlay_pick`,共享机器 = 同文件 `key_fit_names`,判据归属 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) E18 同域的装备价值机器;本 op 零意向读,locked_comp 由策略入口注入 kernel)→ 选卡链经 `CwActionPickEquipOp` 派发(点卡即选机械链+自上报在动作 op 内,pick-op-unify 批)→ `round_wait` 循环推进(无防御上限;`node_max_retry_times=5` 现役值仅框架异常路径消费)。无 chosen_* 写端。

## 3. 观察面

观察 node = 三卡位 OCR 一次读(入口帧一次读,决策轮复用实例载体)。卡名读取 `_read_cards`:全图 OCR,文本带 y 235-300(卡名带,避开下方详情按钮),按 x 近邻分流到三卡槽(槽 x 常量数组,容差 160),同桶 join 为卡名文本。观察 payload = `CwScreenEquipPickObs`(`on_screen`/`options`/`screen`,住 `kernel/cw_screen_report/equip_pick.py`;options 列表序 = 画面物理卡位序左→右);report = `report_screen_equip_pick_obs` 候选写容器 `equip_pick_opts` 槽(无空门直写,空表照写——原写点防线逐位平移;match/gs 缺席的局外兜底路径跳过)。

## 4. 动作面

决策动作 node 选卡链(整体经动作工厂 `cw_overlay_pick_action.py::CwActionPickEquipOp` 派发,pick-op-unify 批;机械链+自上报零写在动作 op 内,派发 param 携真实选中 idx):

```
重入出口门(决策动作 node 顶部):_pick_pending 置位 → 「请选择」OCR(lcs 0.5)不在 =
  overlay 已关(点卡即选已落地)→ success 交回外循环(出战按钮由主流程处理);
  在 = 重走选卡(重点选)
texts = 观察轮 obs 载体 → decide_equip_pick()(零参;候选读容器 equip_pick_opts 槽)
target = (槽 x 常量[best], 卡名带 y 常量 280)→ 置 _pick_pending → 派发
  (动作 op 内:target mouse_move + click → 1.2s
   → 自上报 report_action_pick_equip_param)
  (机械交回,零判效)
```

交互陷阱:点卡即选(单步,无确认钮);重读选中态验效半拆除(验证废除,落地归重入出口门)。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入出口门「请选择」不在 | **画面终结** | round_success 交回外循环(出战由主流程) |
| 出口门「请选择」在(点击未落地) | 节点循环重入 | 重走选卡(`round_wait` 循环推进,不烧节点重试预算,无防御上限) |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身)。

## 6. 状态上报面

本屏无 chosen_\* 写端、无到账登记(选择存证通道已退役;装备到账归下一帧 owned 观察覆盖)。候选观察:`report_screen_equip_pick_obs` 候选写容器 `equip_pick_opts` 槽(空表照写)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5(「装备三选一」行,写端未接线申报)/ §4「事件选择」。

## 7. 子态与 overlay

本屏无子态、无 overlay 覆盖面。误派发防线 = 本屏双 id_mark 门(见 §1)。

## 8. 守卫与防线

- 双 id_mark 门防与选择伙伴屏互派(副题同文案)。
- 未锁线不绑囤牌方向(stash/伪 comp 打分面已随供给面收敛裁定移除;`_resolve_locked_key_fit` 注册表漂移按未锁保守处理,漏提权非错提权)。
- 卡位为实拍字面量类常量(未 area 化,坐标单一源清点挂账项;布局变更需实拍重校)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「选择装备」;op 内日志 tag = `[cw-equip-pick]`(卡名/选卡序号)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_two_node_family.py`(节点循环族两 node 形态锁:观察上报容器/入口门 miss fail/容器零参决策 + round_wait)。
- game 侧知识:无独立 game 画面档(建档与字段面 = `assets/game_data/screen_info/cw_equip_pick.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5)。
