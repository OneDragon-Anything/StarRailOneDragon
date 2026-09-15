# 前进按钮(next_button · OCR 兜底推进)

> 代码 = `operations/cw_screen/cw_screen_next_button.py::CwScreenNextButton`(推进型骨架基类 = `_progression_base.py::CwProgressionScreenOp`)。职责:简报等画面的「下一步」前进按钮(外循环分支 5)的兜底推进——OCR 找到即点,无验效。

## 1. 分发判定

外循环分支 5:OCR「下一步」(默认 lcs;入口判定留外循环,与 `entry_ok` 同源同参);序位近外循环尾 = 兜底点击位([../flow/outer_loop.md](../flow/outer_loop.md) §2.2——0r 位面简报等先行分支已按各自画面锚接管,能落到本分支 = 该「下一步」不属于任何已建档画面档)。无画面档:`SCREEN_NAME`/`ENTRY_AREA` 空串 = 免锚,OCR 即入口。

## 2. 画面形态声明

**空决策形态**(推进族)。免锚形态:无「已离开本画面」观察信号,重入裁决不可达 → 推进发出即 `round_success` 交回(基类免锚分支;有界性归外循环重派/分发 bail 计数)。

## 3. 观察面

入口 = `round_by_ocr('下一步')`;零写端。

## 4. 动作面

单动作 = `round_by_ocr_and_click('下一步', success_wait=2)`(入口与点击两次 OCR 扫描——申报:该帧型每局出现次数少,成本可接受;无验效)。

## 5. 终结与交回

点击已发即 success 交回外循环全分支重判;推进未落地(二次 OCR miss)→ fail 交回重判。

## 6. 状态上报面

零写端。

## 7. 子态与 overlay

无。

## 8. 守卫与防线

无专属防线(兜底分支本性;节点预算 = 基类 2,其余重试归外循环)。

## 9. 遥测与锁面

journal op 名 = 「前进按钮」;无专属测试锁在册(锁面目录 = `sr-od-test/test/sr_od/application/currency_war/`)。
