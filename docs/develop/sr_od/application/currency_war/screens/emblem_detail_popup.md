# 星徽详情弹窗(emblem_detail_popup · 货币战争-星徽详情)

> 代码 = `operations/cw_screen/cw_screen_emblem_detail_popup.py::CwScreenEmblemDetailPopup`。职责:「XX星徽套组」详情面板(1d,点球/装备操作误点开星徽图标触发)的一次访问——点右上 X 关回备战。路径根 = `src/sr_od/application/currency_war/`。

## 1. 分发判定

- 外循环分支 1d:双锚其一即接管——`货币战争-星徽详情.标识-流派星徽` ∨ `货币战争-星徽详情.标识-套组标题`;`entry_ok` 覆写为双锚其一,与分发判定同源同参([../flow/outer_loop.md](../flow/outer_loop.md) §2.2)。建档 = `currency_war_star_badge_detail.yml`。

## 2. 画面形态声明

**空决策形态**(纯推进)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(`entry_ok` 双锚其一复判,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → 双锚均 miss = 已离开本画面 → success 交回)→ 点 X 单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

轻观察:观察 node = `entry_ok` 双锚其一复判(单锚原语 + 第二锚合成)→ obs = `CwScreenEmblemDetailPopupObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/emblem_detail_popup.py`;无 report 接口)。零 GameState 写端。

## 4. 动作面

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
