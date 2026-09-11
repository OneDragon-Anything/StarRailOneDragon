# 0311 组合选择 readiness 统一维度(删 DOT2 特殊逻辑)

- 日期:2026-08-25
- 状态:accepted
- 裁定来源:用户 2026-08-25——「肯定更统一的处理方法更好,万一以后多了过渡可以用的羁绊呢,本质上这只是哪个容易被先凑出来,而不是优先级」;「过渡的过渡这种说法也删掉吧,避免误会」(误解记录 M11)

## 背景

`cw_system_cards.pick_card_combination`(C2 契约)落地时把「DOT2 门槛低」实现成了**两个卡专属特殊 if**:

1. `_WEIGHT_DOT_FIRST`:+1.0 分,只要在手 DOT 件 ≥2(dot_reachable)即加——DOT2 专属加成;
2. `_WEIGHT_TRIO_READY`:+6.0 分,铁三角三人全在手(trio_ready)直取仙舟3——例外条款。

配套文档措辞(「默认首站」「过渡的过渡」)进一步把「门槛低」固化成了「优先级特权」。

## 决策

- 组合打分改为 **readiness 统一维度**:`readiness = pieces / 激活所需件数`
  (DOT2=2、仙舟3=3、列车2=2、希儿系≈3[希儿+2 放大器判据折算]),
  对所有卡统一生效——门槛低的体系天然容易被先凑出(分高),不是优先级特权;
  **未来新过渡羁绊加入零改动**(只需登记激活件数)。
- **删两个特殊 if 与常量**(`_WEIGHT_DOT_FIRST`/`_WEIGHT_TRIO_READY`);
  铁三角全在手时仙舟3 的 pieces(3>2)与 readiness 双维自然最高——例外条款冗余。
- 文档措辞同步清理:「默认首站」「过渡的过渡」说法删除
  (p1_definition 组合规则3 重写 / transition_combos / combo_methodology / strategy_v4 点1·点2 / cw_sim docstring)。

## 行为对照

| 场景 | 旧 | 新 | 等价性 |
|---|---|---|---|
| 铁三角全在手+DOT2 可达 | 仙舟3(例外 +6) | 仙舟3(3+1=4 分 > dot 2+1=3) | 等价(①) |
| 仅 2 张 DOT 件在手 | dot2(首站 +1) | dot2(2+1=3 分最高) | 等价(②) |
| 2 列车件 vs 2 DOT 件 | dot2 恒胜(+1 特权压过意向) | 同分,来牌/词条/意向裁决 | **按裁定改变**(③) |
| 空窗(四系 0 件) | blank_window | blank_window(readiness 恒 0) | 等价(④) |

## Considered Options

- **保留例外条款只删 DOT 加成**:三人全在手时 readiness 双满格(1.0 vs 1.0)
  仅靠 pieces 差胜——若未来有 2 件激活且与仙舟同 pieces 的体系会误触例外;
  统一维度已覆盖,例外是冗余分支,删。
- **纯 readiness 替换 pieces**:①场景 1.0 vs 1.0 同分,tie-break 走 card_id
  字典序会误选 dot2——来牌主判据(pieces)必须保留,readiness 作加成维。
- **维持现状(双特殊 if)**:每加一个新过渡羁绊都要重估特权间互踩
  (DOT_FIRST 与 TRIO_READY 的互斥 if 已经是补丁味)——被用户裁定否决。

## 影响

- 代码:`cw_system_cards.py`(常量区 + `pick_card_combination`)、`cw_sim.py`(docstring 措辞);
- 测试:`sr-od-test/test/sr_od/app/currency_war/test_cw_system_cards.py`
  (锁旧特权的 2 条改写为 readiness 语义,新增等价性四项+统一维度锁);
- 文档:p1_definition / transition_combos / combo_methodology / strategy_v4(见上)。
