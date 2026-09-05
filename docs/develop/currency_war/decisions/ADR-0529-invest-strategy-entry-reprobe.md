# ADR-0529:投资策略屏入口锚动画帧复探(单探测 round_fail 退役)

日期:2026-09-06(20/21 局同型失败治本批)。状态:已实施。

## 背景与病灶

第二十局 01:41:30 与第二十一局 02:22:28 同型失败:`指令[货币战争-投资策略]
执行失败 返回状态 非投资策略屏`(operation.py ERROR,哨兵报警+退出;外层
重试自愈,局正常推进)。时点均在位面 1 早期投资策略节点首访。

失败机制:**识别面时序缺口**,非策略语义问题。投资策略节点首访时,派发帧
→ op 首帧之间落在「备战 → 金币过场动画 → overlay 淡入」过渡段
(screen_flow_timing.md #11:标题出现 1s 后三卡才稳定)。旧实现
`CwScreenInvestStrategy.handle` 对首帧做单探测「标识-请选择投资策略」,
miss 即 `round_fail`——而框架 `round_fail` **不吃**
`node_max_retry_times`(只有 `round_retry` 消耗重试预算,operation.py
RETRY 分支),单帧采样翻车直接炸出整个 op。编排者现场截图
(01:42:03)证实 30s 后已是选择成功的常态画面。

## 决策

入口判定加动画帧容忍,与 `cw_loop._invest_overlay_dispatch`(N5 分发判别
稳定化,第十五局两时序形态一正一误同一根因)**同族同法**:复探=短窗+
新截图。

- `CwScreenInvestStrategy._ensure_entry_screen()`:首探 miss →
  `ENTRY_REPROBE_WAIT_S`(0.8s,执行层时序常量,沿
  `CwLoop.INVEST_REPROBE_WAIT` 先例,非策略数值)后 `screenshot()`
  新截图复探,至多 `ENTRY_REPROBE_TIMES`(4)次;窗口内命中 = 继续;
  超窗仍 miss 才 `round_fail('非投资策略屏')`(防无限等真非目标屏)。
- 禁降识别阈值;锚判据(screen_info id_mark)与语义零变化;首帧命中
  常态路径零复探等待/零新截图(成本门控,同 N5 三审 C2)。

## Considered Options

- **采纳:短窗复探(本 ADR)**——治本于「单帧采样对动画期不稳定」,
  与 cw_loop 0e 分发已验证的同族手法;窗口有界,失败语义保留。
- 拒:把 `round_fail` 改 `round_retry` 吃重试预算——重试间隔受框架
  wait 语义控制、每轮整 op 级重入(日志噪声+哨兵仍触发),且未表达
  「过渡帧」这一根因。
- 拒:入口前固定 sleep 拉长——常态局每次多付固定延迟,治标。
- 拒:放宽锚 lcs/阈值——禁令,且治标(淡入期文本残缺非阈值问题)。

## 修订(2026-09-06,二次治本:超窗改 round_retry)

- **实证推翻原「拒 retry」的前提**:复探窗(3.2s)上线后第二十二局
  04:16:38 同型 ERROR 仍复发——个别过渡段长于窗口;且原选项分析中
  「哨兵仍触发」恰是 fail 路径的真实代价(round_fail 不吃重试预算、
  直接炸出整 op 产生 ERROR 行,20-22 局实证每次 fail 一次哨兵退出)。
- **修订裁定**:超窗后改 `round_retry`(消耗 node_max_retry_times=10
  预算,有界自愈;retry 不产生 ERROR 行,哨兵不再被触发)。复探窗
  (快速路径,常态零成本)与 retry(慢速兜底,有界)双层保留。
- 锁⑥(test_cw_invest_strategy_entry_tolerate.py)锁该语义:超窗 →
  retry 状态而非 fail。

## 修订二(2026-09-06,哨兵白名单裁定)

retry 的日志仍走 operation.py ERROR 级(「返回状态 投资策略屏未稳定,
复探超窗重试」),哨兵 PATTERNS 含「执行失败」会照常触发报警退出——
裁定:哨兵对该 status 行**豁免 HIT 但不豁免 STALL 累积**(行继续向下
喂 STALL/loop,重试耗尽后的 op_fail 终态行不含白名单词、照常报警;
真持续卡死由 HIT/STALL 双通道兜底)。载体 = cw_sentinel.py 白名单
(d8481bcf,三审 C1 修正为仅豁免 HIT)。

## 锁

`sr-od-test/test/sr_od/app/currency_war/test_cw_invest_strategy_entry_tolerate.py`
四条:①首帧 miss(备战过渡帧 fixture)→ 复探命中(投资策略 default
fixture)= 判定通过不报失败;②持续 miss → 恰好复探 ENTRY_REPROBE_TIMES
次后判失败(有界,间隔=ENTRY_REPROBE_WAIT_S);③首帧命中 → 零复探
等待/零新截图;④全流程集成锁:过渡帧起手经复探走完选卡+确认,不报
非投资策略屏。
