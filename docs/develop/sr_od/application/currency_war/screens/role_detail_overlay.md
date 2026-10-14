# 角色详情浮层(role_detail_overlay · 货币战争-备战-角色详情)

> 代码 = `operations/cw_screen/cw_screen_role_detail_overlay.py::CwScreenRoleDetailOverlay`。职责:点卡/点角色触发的详情弹窗(可合成列表/角色详情两变体)的一次访问——点面板外空白关闭结束本次访问。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(旧外循环分支编号已停用,本文不引编号):双 id_mark 门——`货币战争-备战-角色详情.按钮-装备推荐` ∧ `货币战争-备战-角色详情.备战标识-购买经验`(建档仅此两 area 挂 `id_mark: true`,判定 = `screen_utils.is_target_screen` 对建档 id_mark 组合全命中,任一 miss 即不识别;分发判定单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2,本屏消费点 = `cw_loop.py::CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-备战-角色详情'` → 派发本 op)。「备战标识-购买经验」为底层备战底部条识别标志(阶段二备战两标志成员,outer_loop.md §2.2):本浮层为右侧面板、不遮底部条,底层标志透出可命中——与商店卡牌详情弹窗的「暗色衬底全遮蔽、禁取底层标志」形态相反([shop_card_detail.md](shop_card_detail.md) §1)。
- op 门覆写申报:本 op 入口观察 `entry_ok` = `按钮-装备推荐` ∨ `装备详情-合成公式`(OR,两半区 = 角色详情/可合成列表两弹窗变体识别标志)。与分发门宽窄关系:同帧蕴含分发门全中 ⇒ op 门必真(`按钮-装备推荐` 为两门共用识别标志),反向不成立——`装备详情-合成公式` 半区不在分发判据内。op 门职责 = 分发后新帧的入口复判与落地复查(见 §2),不构成分发判据;分发后新帧可能两标志均失(弹窗已关的过渡帧)→ op 门 miss = `round_fail` 返回主循环重新判定。
- 位置约束标志形态:两弹窗变体识别标志(`按钮-装备推荐`/`装备详情-合成公式`,即 op 门标志集)均在右侧面板标志区,与商店卡牌详情弹窗天然互斥(该弹窗底部按钮不在右侧标志区内)——全屏文本判据在本族不可用(与商店卡牌详情弹窗底部按钮文本全等共享)。建档 = `currency_war_battle_prep_equip_detail.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(`entry_ok` 双标志其一复判(门语义与分发门宽窄申报见 §1);miss = round_fail 返回主循环重新判定)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部落地复查(落地复查 = 动作发出后下一轮检查上一动作是否已生效——画面标志消失;下同。推进已发 → 双标志均 miss = 已离开本画面 → success 结束本次访问)→ 点空白关闭单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 在用值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` 双标志其一复判 → obs = `CwScreenRoleDetailOverlayObs`(`on_screen`/`screen`,位于 `kernel/cw_screen_report/role_detail_overlay.py`;无 report 接口)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「返回主循环」= 本访问结束、控制权返回主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进由画面 op 内置动作完成(`progress_once`:点「货币战争-备战.区域-空白关闭」点面板外空白关闭) | 画面 op 内置动作(内置动作 = 画面 op 内部代码直接执行的固定动作,不经动作注册表派发;`progress_once`:find_and_click 点建档中心,`success_wait=1.5`) | 无 report 接口(推进型规范形态,op-layer.md §3) | **是(推进即终结)**:点击后 `round_wait` 重入;落地复查双标志均 miss = 已离开 → `round_success` 结束本次访问(见 §5);推进未落地 = `round_fail` 结束本次访问 |

`progress_once` = `round_by_find_and_click_area(货币战争-备战.区域-空白关闭, success_wait=1.5)`。关闭机制 = 点面板外空白(两 overlay 家族无关闭按钮,共用同一空白点);「区域-空白关闭」为纯定位区(find_and_click 点建档中心,点击语义等价且自带等待)。刻意不用 ESC:空白点在 overlay 未开时是无害空点,ESC 在浮窗已自关时落备战会误弹「中断挑战」。

## 5. 终结与交回

推进已发 → `round_wait` 重入;落地复查 = 双标志均 miss = 已离开 → `success` 结束本次访问(无防御上限;dispatch 挂 `on_fail_retry`,映射 loop 级 `round_retry` 消费 retry 池)。落点 = 备战(「备战」分支重判)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件(详情面板纯展示)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层(备战)返回主循环重新判定。

## 8. 守卫与防线

`node_max_retry_times=2` 在用值仅框架异常路径消费 + 外循环 retry 池(on_fail_retry);点空白零效果 → 重入再做一次,卡死形态为分钟级可见失败;无停机钩子/失配告警面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「详情弹窗」;frame_tag = `overlay_role_detail`(dispatch 包装)。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_screen_progression_inline.py`(推进型骨架内联形态锁,role_detail_overlay 已登记);建档 = `currency_war_battle_prep_equip_detail.yml`,空白点挂 `currency_war_battle_prep.yml`。
