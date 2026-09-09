# 0622. 刷新费现场识别为准(金币差倒推退役,推翻 ADR-0456 不重建裁定的延伸)

- **Status**: accepted
- **Date**: 2026-09-09

## Context
刷新费 shop_refresh_cost 的观察通道历经两版:①刷新费徽标 OCR(小数字可靠性差,ADR-0456 裁定徽标退役,后续设计将「OCR 直读候选裁死不重建」一并固化);②BoardState 设计 v3.0 折入「金差推导」——点刷新前后两次金币读数差倒推,基价 2 作先验、只证偏差+买牌/刷新/升级同窗归因。

## Decision Drivers
- 玩家裁定 2026-09-09:「这个必须要靠现场识别为准，不能靠事后推导」——字段值必须直接来自画面读数。
- 金币差倒推的固有缺陷:只在点刷新那一刻工作;同窗多动作的归因靠约定不靠事实;改价事件(如长线利好)后首刷前字段停在基价,是推定值不是读数。

## Considered Options
1. 维持金币差倒推(否:玩家裁定推翻)。
2. 干净备战屏价签 OCR(否:刷新决策发生在商店开态,备战屏价签不在决策时刻)。
3. 商店开态刷新钮标价现场 OCR(取)。

## Decision
刷新费写端=商店开态刷新钮标价的**现场 OCR 识别**(reader 参照 cw_node_obs 先例;数字类误读用规则修复;识别失败=None 禁兜底);金币差倒推退役,其「只证偏差/同窗归因/P1r9+level5-6 证据域」约束一并作废。干净备战屏底部「文本-刷新金币数」区域读数实为利息徽标(ADR-0456 定谳,非刷价)——维持不识别、禁误接。落地批=子 agent 实现(定位标价 bbox→MCP 建档→reader→测试),验收后本 ADR 补实施行。

## Consequences
- 正向:字段值为画面真值,决策时刻即时可得;归因链约定面消失。
- 负向:小数字 OCR 误读风险回归——以数字规则修复+失败 None 兜底,可靠性待实装实测。
- 边界:免费帧不写语义不变;预算内基价常量(2 金)仍可作为消费端先验,但不再是字段写入依据。

## Links
- docs/develop/currency_war/design/BoardState-数据结构设计.md §3.3.4
- ADR-0456(徽标退役;本 ADR 推翻其「不重建」延伸)、ADR-0091(同型先例:刷新概率表实机 OCR 权威)

## Implementation (2026-09-09)
- 建档:商店开态档案新增「文本-刷新价格」area（bbox [1584,513,1664,558]，1080p；判定=测试仓 5 张 1080p 归档帧 `sr-od-test/screens/货币战争-备战-开商店/` 视觉直读+8x 放大精测，跨帧像素稳定；MCP upsert 落盘）。实机 shop-open 帧回验挂起（候有局批次顺带一帧）。
- reader:`sr_od/application/currency_war/obs/cw_shop_refresh_obs.py` `read_shop_refresh_price(ctx, screen)->int|None`——两级管线（裁 area 3x 放大→读空 OTSU 二值化重试；全帧 det 小目标必漏已离线实证）、可信域 [1,9]、金币图标并入规则（大写化 O→0，逐条扫描）、0 恒拒信（免费帧 None≠0）、识别失败=None 禁兜底。
- 测试:`sr-od-test/test/sr_od/app/currency_war/test_cw_shop_refresh_price.py` 11 passed（解析矩阵 5+全链 5 含两级接线锁与 area 缺失不触 OCR 防线+5 真帧锁恒读 2）；波及域回归 currency_war 快速层零新增红。
- 挂起:主链接线（cw_observation 消费面）归迁移批次一「刷新费观察通道重建」（§8.7）；免费帧「不写」调用方闸归 §3.3.7 接线批。
