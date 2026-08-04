# `round_by_*` helper 家族(reference)

> `sr-od-dev-write-operation` 的 situational reference。SKILL.md 给选型表,本文件给逐 helper 语义 + 关键参数。

所有 helper 都返回 `OperationRoundResult`(success / wait / retry / fail),直接 `return self.round_by_xxx(...)` 即可。通用参数:`success_wait` / `success_wait_round`(成功后等)、`retry_wait` / `retry_wait_round`(retry 时等)、`pre_delay`(动作前等)、`color_range`(限定文字颜色)、`crop_first`(区域 OCR 先裁再识别)。

## OCR 类(找文字)

### `round_by_ocr_and_click(screen, target_cn, area=None, lcs_percent=0.5, ...)`
OCR 找 `target_cn` 文字 → 点其中心。找不到 → `round_retry`;点失败 → `round_retry`;点到 → `round_success(target_cn)`。
- `area`:限定搜索区域(`ScreenArea`)。**不传 = 全屏搜**(易撞同类文字,见 LCS 坑)。传 area = 固定位置识别,稳。
- `lcs_percent`:子序列匹配阈值,默认 **0.5**(松,易误匹配)。真匹配 1.0 不受提高阈值影响;收紧到 0.7~0.9 杀假匹配。
- `offset`:点击位置偏移。
- `remove_whitespace`:匹配前清空白(应对 OCR 多/少空格)。

### `round_by_ocr(screen, target_cn, area=None, lcs_percent=0.5, ...)`
只判定 `target_cn` 在不在,**不点**。在 → `round_success`;不在 → `round_retry`。用于"等某文字出现再进下一节点"。

### `round_by_ocr_and_click_by_priority(target_cn_list, ignore_cn_list=None, ...)`
按 `target_cn_list` **优先级**找,点第一个命中的。`ignore_cn_list` 防"已领取"误匹配"领取"这类(列出来不实际点)。多目标选一时用它。

## screen_info area 类(找固定 UI)

### `round_by_find_and_click_area(screen_name, area_name, until_find_all=None, until_not_find_all=None, ...)`
在 `screen_name` 画面的 `area_name` 区域找(模板 / OCR)→ 点。**带后验**:
- `until_find_all=[(screen, area), ...]`:点了之后等这些区域都出现才算 success(没出现 → `round_wait` 继续点)。
- `until_not_find_all=[...]`:点了之后等这些区域都消失才算 success。
- 适合"点按钮 → 等画面切换"的场景(点完没切换会重试点)。

### `round_by_find_area(screen, screen_name, area_name, ...)`
**只判定** area 在不在(不点)。在 → `round_success`;不在 → `round_retry`;区域没配置 → `round_fail`。

> ⚠️ `round_by_find_area` **只检测不点击**。要点必须用 `_and_click` 版或自己 `controller.click`。别拿 find 版当点击用。

### `round_by_click_area(screen_name, area_name, click_left_top=False, ...)`
**不判定,直接点** area 的中心(`click_left_top=True` 点左上角)。area 没配置 → `round_fail`。已知该处可点、不需判定时用它(最快)。

## 导航类

### `round_by_goto_screen(screen_name=None, ...)`
按 screen_info 的 route 从当前画面导航到 `screen_name`:识别当前画面 → 找路径 → 点路径上第一个跳板 area → `round_wait` 等切换 → 循环到目标画面。到 → `round_success`;识别不出当前画面 → `round_retry`;无路径 → `round_fail`。依赖 screen_info 的 screen route 数据。

## OCR 关键词与 LCS 匹配机制(必懂)

框架 OCR 匹配用 **LCS(最长公共子序列)/ 目标长度 ≥ `lcs_percent`**,不是"子串包含"。后果:
- 中文关键词与**别的画面文字共享 2+ 字子序列**就可能 ≥ 0.5 误匹配。例:4 字关键词与别处共享 2 字 → 2/4=0.5 命中。
- 全屏 `round_by_ocr*`(不传 area)天然易撞 —— 画面任何位置的同义文字都算。

**两档修**:
1. **止血**:该 helper 传 `lcs_percent=0.7~0.9`,或换更长 / 更独有关键词(如完整标题而非两字词)。
2. **根治**:用**固定位置识别** —— 关键词只在它**固定的画面位置**识别(传 `area` 圈定位置,不全文扫)。全屏 loose 匹配撞同类元素是根因;bound 到位置的 area 检测才稳。

判据:同 loop / 同画面里所有中文关键词都要审共享子串,不只改一个就收工。
