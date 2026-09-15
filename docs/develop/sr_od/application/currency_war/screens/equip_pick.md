# 选择装备三选一(equip_pick · 货币战争-选择装备)

> 代码 = `operations/cw_screen/cw_screen_equip_pick.py::CwScreenEquipPick`(CwScreenOpBase 子类)。职责:选择装备 overlay 一次访问——OCR 卡名 → 锁线契合打分 → 点卡即选(无独立确认钮,出战按钮由主流程处理)。路径根 = `src/sr_od/application/currency_war/`。建档 = `assets/game_data/screen_info/cw_equip_pick.yml`。

## 1. 分发判定

- 外循环分支 0a0:**双 id_mark 门**——「货币战争-选择装备.标识-选择装备」∧「货币战争-选择装备.标识-请选择1个装备」同帧命中才派发(副题「请选择1个」与选择伙伴屏共享,单锚会误派)。
- 序位:**必须先于 0a(选择伙伴)**;序位单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2。

## 2. 画面形态声明

**单选族例外**(有选择面零逻辑态账,判据 = [README.md](README.md) §3)。五相位屏:**本屏无 op 内入口门**(入口判定归主循环 0 系分发双 id_mark,分发即门;round_retry 重入不经外循环分发 → `_handle_overlay` 顶部出口门补位);无 on_outcome 落地登记件;无 chosen_\* 写端。选卡判据 = 局内策略域已锁线装备契合(共享机器 `kernel/cw_equip_value.py::key_fit_names`;判据归属 = [../strategy-docs/13_pick_family.md](../strategy-docs/13_pick_family.md) E18 同域的装备价值机器,本 op 内联消费 key_fit_names 子串命中形态)。

## 3. 观察面

observe 段 = 轻观察帧引用(卡名读取归共享动作体现役内聚)。卡名读取 `_read_cards`:全图 OCR,文本带 y 235-300(卡名带,避开下方详情按钮),按 x 近邻分流到三卡槽(槽 x 常量数组,容差 160),同桶 join 为卡名文本。观察 payload = `EquipPickObservation`(仅帧引用);本屏不上报 GameState 容器观察。

## 4. 动作面

选卡链 `_handle_overlay`(两路径共享):

```
重入出口门:_pick_pending 置位 → 「请选择」OCR(lcs 0.5)不在 = overlay 已关
  (点卡即选已落地)→ success 交回外循环(出战按钮由主流程处理);
  在 = 重走选卡(计节点预算)
texts = _read_cards → 打分:已锁线 key_fit_names(_resolve_locked_key_fit:
  意向状态 locked_comp → comp.key_equips → key_fit_names;未锁 = 空集)
  子串命中 +100 / 无命中且含泛用增益词(伤害/强度/提高)+1 → argmax
  (并列取先序;全零 = 首卡)
target = (槽 x 常量[best], 卡名带 y 常量 280)→ mouse_move + click → 1.2s
→ 置 _pick_pending → round_retry(机械交回,零判效)
```

交互陷阱:点卡即选(单步,无确认钮);重读选中态验效半拆除(验证废除,落地归重入出口门)。动作词表:画面 op 直驱。

## 5. 终结与交回

| 条件 | 级别 | 交回落点 |
|---|---|---|
| 重入出口门「请选择」不在 | **画面终结** | round_success 交回外循环(出战由主流程) |
| 出口门「请选择」在(点击未落地) | 节点循环重入 | 重走选卡(计 `node_max_retry_times=5` 预算,超 → FAIL bail) |

「确认离开 = 画面终结」= [README.md](README.md) §6(本屏确认 = 点卡本身)。

## 6. 状态上报面

本屏无 chosen_\* 写端、无到账登记(选择存证通道已退役;装备到账归下一帧 owned 观察覆盖)。字段节 = [../game_state/fields.md](../game_state/fields.md) §3.4.5(「装备三选一」行,写端未接线申报)/ §4「事件选择」。

## 7. 子态与 overlay

本屏无子态、无 overlay 覆盖面。误派发防线 = 0a0 双 id_mark 门 + 序位(见 §1)。

## 8. 守卫与防线

- 双 id_mark 门防与选择伙伴屏互派(副题同文案)。
- 未锁线不绑囤牌方向(stash/伪 comp 打分面已随供给面收敛裁定移除;`_resolve_locked_key_fit` 注册表漂移按未锁保守处理,漏提权非错提权)。
- 卡位为实拍字面量类常量(未 area 化,坐标单一源清点挂账项;布局变更需实拍重校)。
- 无本屏专属停机钩子;守卫总册 = [../flow/guards.md](../flow/guards.md)。

## 9. 遥测与锁面

- journal op 名 =「选择装备」;op 内日志 tag = `[cw-equip-pick]`(卡名/选卡序号)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_obs_arch_event_screens_step3.py`(迁移结构锁)。
- game 侧知识:无独立 game 画面档(建档与字段面 = `assets/game_data/screen_info/cw_equip_pick.yml` + [../game_state/fields.md](../game_state/fields.md) §3.4.5)。
