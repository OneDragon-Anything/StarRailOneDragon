# 踩坑案例:自动化 bug 排查(判据论据,上游起源)

> 以下完整排查历程来自 OneDragon 系列上游项目,作为 SKILL.md 4 节判据的**来源论据**保留。具体函数名 / 坐标 / 版本号是那次案例的偶然细节,**记这不进 SKILL.md**(`od-dev-writing-skills` 硬规范 4:design/ 允许具体例子作决策论据,SKILL.md 只写方法论)。星铁侧待补本游戏真实案例。

## 案例:某玩法运行全部失败

**症状**:用户反馈近期某玩法运行全部失败。

**弯路 1 —— analyze 误导** → SKILL §3(识别路径 = bot 路径):
`analyze_screen` MCP 显示「某画面匹配」,但 bot 运行时认不出。根因:analyze 走 `crop_first=False`(全图 OCR 再过滤),bot 运行时 `check_and_update_current_screen` → `is_target_screen` → `find_area_in_screen` 走 `crop_first=True`(先裁 rect 再 OCR)。OCR 模型迁移后,对**宽 text rect**(某「按钮-确定」原 rect 宽 940px)`crop_first=True` 检不出「确定」→ id_mark 缺一 → 不匹配 → 整局卡死。

**弯路 2 —— 换旧 OCR 模型又出新 bug** → SKILL §3(OCR 离线验参数)+ §2(数信号判循环):
切旧模型临时缓解漏检,但宽 rect + `lcs_percent=0.5` 把**大世界场景文字**(与「确定」LCS=0.5)误配成「确定」+ TAB → 大世界被误判成该选择画面 → 标题为空 → 死循环(实跑 12 通关后卡在某 NPC 前 ~2h,日志 2101 次 `fallback:none`)。

**采集 + 复现** → SKILL §4(识别时刻截图 + 离线同参数复现):
在路由节点加 `is_debug` 门控的 `save_screenshot`,采到各选择画面真实帧 → 离线脚本遍历 crop_first / lcs / rect 锁定根因 → 收紧 rect + 提高 lcs 阈值。

**进程 / 日志混淆** → SKILL §1(找对日志):
初期只翻 MCP server 日志(`.debug/sr_od_mcp/main_server.log`),没找到用户跑的痕迹 —— 用户是 GUI / 一条龙跑的,日志在 `.log/log.txt`。

---

## 非本 skill 范围:框架可排查性 follow-up(给后续改框架的人)

> 这次排查暴露的可排查性短板,**不属于本 skill 的排查方法论**(本 skill 教「在现有可排查性下怎么查」),记录备框架改进 —— 改了能减轻本 skill 判据的负担(例如看门狗落地后,§2「数重复记录判循环」的部分可简化)。

1. **路由节点卡死看门狗 + 诊断截图**:`round_retry` 类路由节点,N 次重试无进展 → 自动存诊断截图 + 日志明确报「卡在 X 画面,期望 Y」(现在能无声循环几小时)。
2. **画面匹配记命中明细**:精准匹配时日志记「命中哪些 id_mark(名 + 实际 OCR 值 + 置信度)」—— 误匹配靠这个一眼能看出,现在只记「匹配到 X」看不出为啥。
3. **screen_info lint**:text id_mark 的 rect 过宽 + `lcs_percent` 过低 → 标「易误匹配」风险(宽 text rect + 松 lcs = 误匹配磁铁)。
4. **OCR 模型迁移带 fixture 回归**:OCR 模型迁移时,用画面匹配的 fixture 套件在两模型下各跑一遍,抓迁移引入的识别回归。
