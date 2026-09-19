# 前进按钮(next_button · OCR 兜底推进)

> 代码 = `operations/cw_screen/cw_screen_next_button.py::CwScreenNextButton`(两 node 直继承 `SrOperation`)。职责:简报等画面的「下一步」前进按钮(外循环分支 5)的兜底推进——OCR 找到即点,无验效。

## 1. 分发判定

外循环分支 5:OCR「下一步」(默认 lcs;入口判定留外循环,与 `entry_ok` 同源同参);位置近外循环尾 = 兜底点击位([../flow/outer_loop.md](../flow/outer_loop.md) §2.2——0r 位面简报等先行分支已按各自画面锚接管,能落到本分支 = 该「下一步」不属于任何已建档画面档)。无画面档:`SCREEN_NAME`/`ENTRY_AREA` 空串 = 免锚,OCR 即入口。

## 2. 画面形态声明

**空决策形态**(推进族)。两 node 直继承 `SrOperation`(合同 = [op-layer.md](op-layer.md) §1.1):观察 node = 入口门(OCR「下一步」,与分发判定同源同参;miss = round_fail 交回外循环重判)+ obs{on_screen} 挂实例属性;决策动作 node = 顶部重入裁决(推进已发 → OCR 不命中 = 已离开本画面 → success 交回)→ 点击「下一步」单次推进 → `round_wait` 循环推进(无防御上限;`node_max_retry_times=2` 现役值仅框架异常路径消费)。空决策形态无 report 接口。

## 3. 观察面

观察 node = `round_by_ocr('下一步')` → obs = `CwScreenNextButtonObs`(`on_screen`/`screen`,住 `kernel/cw_screen_report/next_button.py`;无 report 接口)。零写端。

## 4. 动作面

单动作 = `round_by_ocr_and_click('下一步', success_wait=2)`(入口与点击两次 OCR 扫描——申报:该帧型每局出现次数少,成本可接受;无验效)。

## 5. 终结与交回

推进已发 → `round_wait` 重入;重入 = OCR「下一步」不命中 = 已离开 → `success` 交回外循环全分支重判;推进未落地(点击 OCR miss)→ `round_fail` 交回重判。

## 6. 状态上报面

零写端。

## 7. 子态与 overlay

无。

## 8. 守卫与防线

无专属防线(兜底分支本性;`node_max_retry_times=2` 现役值仅框架异常路径消费)。

## 9. 遥测与锁面

journal op 名 = 「前进按钮」;测试锁 = `sr-od-test/test/sr_od/application/currency_war/test_cw_screen_progression_inline.py`(推进型骨架内联形态锁,next_button 在册)。
