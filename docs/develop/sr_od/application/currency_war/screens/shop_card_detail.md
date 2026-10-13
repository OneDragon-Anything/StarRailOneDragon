# 商店卡牌详情弹窗(shop_card_detail · 货币战争-商店卡牌详情)

> 代码 = `operations/cw_screen/cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup`。职责:采晶矿误触开的「角色 offer 购买页」弹窗(中央角色大面板 + 底部五牌条 + 购买/角色详情双按钮 + 右上 X)的一次访问——点 X 关闭交回,**绝不点购买**。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 阶段一身份分发(旧外循环分支编号已停用):双 id_mark 门——`货币战争-商店卡牌详情.按钮-购买` ∧ `货币战争-商店卡牌详情.按钮-角色详情`(弹窗前景独有识别标志,两标志全中才接管,单标志不放行;判定 = `screen_utils.is_target_screen` 对建档 id_mark 组合全命中,任一 miss 即不识别;分发判定单一源 = [../flow/outer_loop.md](../flow/outer_loop.md) §2.2,本屏消费点 = `cw_loop.py::CwLoop._dispatch_identity_screen` 身份行 `if name == '货币战争-商店卡牌详情'` → 派发本 op;op 门 `entry_ok` 与分发判定同标志同逻辑——复判载体 = `cw_screen_shop_card_detail.py::CwScreenShopCardDetailPopup.entry_ok`,门语义见 §2)。
- 分发 = 阶段一身份行(双 id_mark 门):弹窗暗色衬底遮蔽底层全部识别标志(开商店三标志/备战两标志在该衬底下不命中);禁取衬底透出的底层标志作判据。建档 = `currency_war_shop_card_detail.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进;有购买面但买不买归商店域——关闭动作不代替购买决策)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(`entry_ok` 双 id_mark 门复判,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部落地复查(落地复查 = 动作发出后下一轮检查上一动作是否已生效——画面标志消失;下同。推进已发 → 双标志均 miss = 已离开本画面 → success 交回)→ 点 X 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 在用值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` 双 id_mark 门复判 → obs = `CwScreenShopCardDetailPopupObs`(`on_screen`/`screen`,位于 `kernel/cw_screen_report/shop_card_detail.py`;无 report 接口)。零 GameState 写端(牌面/金等底层事实归「商店开画面」分支商店访问入口观察)。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回外循环主循环 `cw_loop.py::CwLoop.loop` 重新识别画面并重判):

| 动作 op(动作类型清单参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进由画面 op 内置动作完成(`progress_once`:点「货币战争-商店卡牌详情.按钮-关闭」× 关闭,绝不点购买) | 画面 op 内置动作(内置动作 = 画面 op 内部代码直接执行的固定动作,不经动作注册表派发;`progress_once`:find_and_click 点建档中心,`success_wait=1.5`) | 无 report 接口(推进型规范形态,op-layer.md §3) | **是(推进即终结)**:点击后 `round_wait` 重入;落地复查双标志均 miss = 已离开 → `round_success` 交回(见 §5);推进未落地 = `round_fail` 交回 |

`progress_once` = `round_by_find_and_click_area(货币战争-商店卡牌详情.按钮-关闭, success_wait=1.5)`。X 复用大厅同族关闭模板(`cw_lobby_close`;备战右上数据统计按钮与 X 区重叠但模板实测零误配,交叉核对在案)。**语义红线:绝不点购买**——本画面唯一义务是关闭。

## 5. 终结与交回

推进已发 → `round_wait` 重入;落地复查 = 双标志均 miss = 已离开 → `success` 交回(无防御上限;dispatch 挂 `on_fail_retry`,消费 retry 池)。落点:**店开 → 「商店开画面」分支商店访问接管购买;备战 → 备战环**——弹窗任何时刻有主,无孤儿形态。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件(暗色衬底遮蔽形态的唯一直管分支);关闭后底层屏交回重判,购买语义回归商店访问域([shop.md](shop.md))。

## 8. 守卫与防线

`node_max_retry_times=2` 在用值仅框架异常路径消费 + 外循环 retry 池(on_fail_retry);X 零效果 → 重入再做一次,卡死形态为分钟级可见失败;无停机钩子/失配告警面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「商店卡牌详情」;frame_tag = `overlay_shop_card_detail`(dispatch 包装,on_result 日志闭包)。测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,shop_card_detail 在册);建档 = `currency_war_shop_card_detail.yml`。
