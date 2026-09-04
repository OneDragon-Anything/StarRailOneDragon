# ADR-0239 结算屏自身解析节点类型(生产链死亡的治本修复)

## Status

accepted(2026-08-22;r366;用户质询「节点识别为什么一直修不好」驱动;推翻 r362/r363 的修补路线)

## Context

node_type 错误历经三轮修补(r362 槽序表兜底/r363 词汇统一+锚定+写入端)仍未好。彻查局48 实锤根因:**生产链已死**——node_type 唯一活源是 `_probe_node_type`(挂 EnsureShopClosed 成功后),而当前备战流是 `RunBuyPhase→RunDeploy→RunEquip→StartBattle`,**EnsureShopClosed 零执行**(局48 全程 director 动作统计),probe 从不跑 → current/左移/槽序表全链无数据 → outcomes 恒「普通战斗」。前三轮修的都是这条死链的消费端(fallback 层层加),生产者从不点火——修不好是因为**没找到断电处**。r260 曾弃结算屏 OCR(全屏搜「奖励」误中金币区「基础奖励」),但那是匹配方法问题,不是源不好。

## Considered Options

1. 把 probe 挂到 RunBuyPhase(生产链复活):仍依赖备战期读到节点行(非 clean 帧常 skip)+跨帧状态;流再变又死。
2. **结算屏自身解析**(选):结算屏头部自带类型词(局48 七轮实拍:['挑战成功','奖励',...]/['挑战成功','1-3X点','战斗',...]/['挑战结束','遭遇',...])——在记录 outcome 的**同一时刻同一张屏**上读,零跨帧状态、零流依赖、首节点天然覆盖。
3. 两者并存(结算屏优先,probe 链兜底):已实现——read_round_outcome 内结算屏真值覆盖传参;probe 链保留(它还喂 plane_node_table 统计源)。

## Decision

`parse_settlement_node_type`:定位「挑战成功/挑战结束」头,其后 1-4 token 内**精确 token 匹配**类型词(战斗→普通战斗/奖励/遭遇/补给/首领→boss/巨星);「基础奖励」≠「奖励」不误中(r260 顾虑根除)。read_round_outcome 解析出即覆盖 battle_loop 传参(带覆盖日志)。锁测试 6 条(局48 真实 token 序列)。

## Consequences

- outcomes.node_type 从「备战期推断+多层兜底」变为「结算时刻屏面真值」;prep 流再演进不影响。
- 方法论教训(入 skill 防坑):**修消费端前先验生产端点火**(grep 运行期日志确认生产路径执行过;零执行=修 fallback 是安慰剂);跨天 append 日志 grep 必须带日期锚点(时间戳无日期,本日误把昨日行当今日证据追了半小时「双进程」鬼影)。
