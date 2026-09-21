# 星徽详情弹窗(emblem_detail_popup · 货币战争-星徽详情)

> 代码 = `operations/cw_screen/cw_screen_emblem_detail_popup.py::CwScreenEmblemDetailPopup`。职责:「XX星徽套组」详情面板(1d,采晶矿/装备操作误点开星徽图标触发)的一次访问——点右上 X 关回备战。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1d:阶段一身份行,判据 = 建档 id_mark 组合**全命中**(`货币战争-星徽详情.标识-流派星徽` ∧ `货币战争-星徽详情.标识-套组标题`;[../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。`entry_ok` 覆写为双锚其一(OR)——op 接管面比分发面宽(单锚帧分发不接,op 内重入裁决以任一锚在 = 未离开),与分发判定不同源。建档 = `currency_war_star_badge_detail.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(`entry_ok` 双锚其一复判,分发判定 = 建档双 id_mark 组合全命中,见 §1;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 双锚均 miss = 已离开本画面 → success 交回)→ 点 X 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` 双锚其一复判(单锚原语 + 第二锚合成)→ obs = `CwScreenEmblemDetailPopupObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/emblem_detail_popup.py`;无 report 接口)。零 GameState 写端。

## 4. 动作面

**动作 op 与交回对照表**(本篇唯一动作清单;「交回外循环」= 本访问结束、控制权交回 `cw_loop.py::CwLoop.loop` 重判):

| 动作 op(词表参数) | 发出方式 | 上报 | 触发返回外循环 |
|---|---|---|---|
| 无动作 op——单步推进留守 op 内(`progress_once` 点 X 关闭) | 画面 op 留守臂(`progress_once`:`round_by_find_and_click_area` 点 `货币战争-星徽详情.按钮-关闭`,success_wait=1) | 无 report 接口(推进型规范形态,op-layer.md §3) | 是(重入裁决:点 X 已发 ∧ 双锚均 miss = 已离开 → `round_success` 交回;其一在 = `round_wait` 再推进) |

`progress_once` = `round_by_find_and_click_area(货币战争-星徽详情.按钮-关闭, success_wait=1)`(点 X 后等关闭动画再交回裁决)。**刻意不用 ESC**:X 是弹窗内坐标永远安全,ESC 在面板已关时落备战会误弹「中断挑战」——该红线禁在 op 内「顺手统一」成 ESC。

## 5. 终结与交回

推进已发 → `round_wait` 重入;重入 = 双锚均 miss = 已离开 → `success` 交回(无防御上限)。落点 = 备战(1 分支重判)。

## 6. 状态上报面

无:零逻辑态直写、零落地登记件(详情面板纯展示,无画面事实可采)。

## 7. 子态与 overlay

本 op 自身即 overlay 处理件;命中即自处理,底层(备战)交回重判。

## 8. 守卫与防线

`node_max_retry_times=2` 现役值仅框架异常路径消费;无停机钩子/安灯面(细则 = [../flow/guards.md](../flow/guards.md))。

## 9. 遥测与锁面

- journal op 名 = 「星徽详情」;frame_tag = `overlay_emblem_detail`(dispatch 包装)。
- 测试锁:`sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,emblem_detail_popup 在册);建档 = `currency_war_star_badge_detail.yml`。
