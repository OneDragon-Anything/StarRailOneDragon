# dd-020:序列决策契约——动作发射接口统一升序列/次(备战 decide_prep_screen 单动作→list,同构商店)+ fail-stop/帧稳定截断冻结

> 类名/路径已随 2026-09-03 命名迁移与流程重构持续更替,本文代码锚为批时快照(2026-09-03),漂移按「契约占位」处理不立案。

- Status: accepted(2026-09-03,用户整包批准三裁决点;正文权威 = `.debug/temp/currency_war/redesign/CONTRACT_SERIES_DECISION.md` v1,汇合点后 as-built 归 `strategy/07_plugin.md` 更新承接)
- 关联: dd-014(黑板接口前身)、dd-017(P3b 编排切换)、`prereg/w971_flow_layer/DESIGN.md[已删·git 84370361 可溯]`

## 背景

dd-014 落黑板接口后,动作发射类接口粒度分裂:商店线 `decide_shop_screen(session, config) -> list[Action]` 已是序列(空序列=决策完成触发关店,`buy_cards` 执行至首个 RefreshShop 截断);备战线 `decide_prep_screen(session, config)` 契约仍「返回一个 PrepAction」,靠外循环逐动作重观察重决策转出系列。v2 契约层(`decision_v2/contracts.py` Decision/AtomOp)起草过批语义,但其执行引擎 DirectorV2 已随 W971 P3b 内环拆除退出生产。接口表达力不足处策略意图泄漏进流程侧(实证:遭遇分支刷新 `pick.refresh` 旗标 + handler 侧重决策循环,dd-004)。

## 决策

1. **接口形态**:备战线升级 `decide_prep_screen(session, config) -> list[PrepAction]`,与商店线同构;执行序=列表序。生产接口=裸 list——`decision_v2` 的 Decision/AtomOp 层不进生产接口(保留 sim/离线驱动);若流程侧需要该形状须回契约改版,禁静默双轨。
2. **序列语义**:fail-stop(任一动作未落地→余下丢弃→heavy 重观察→重调接口);帧稳定域核心条款(序列内第 i+1 个动作不得依赖第 i 个执行后的新观察——发射器判「本动作后画面能否静态推出」,不能则截断);逐动作期望态对账保留(砍的是重决策不是验证);生命周期机制(幂等键/连败→恢复→屏蔽/stall 门/强制出战)归流程侧框架,策略器不自实现。
3. **截断规则初始枚举**:RefreshShop=截断点(牌面变);CompTransaction fill 消费店槽=截断点(后续 BuyCard 引用陈旧槽位;sim engine_p1 实现先例);合成触发=截断点(满栏买入自动合成使 bench 形变不可静态精确预测);拖拽族=条件(ADR-0316 槽位模型下 bench 索引结构恒稳,序列内下标安全是结构保证;逐动作名-槽一致性复检为语义防线;board 空位/星级按前序累积静态推出,推不出即截断);BuyCard/LevelUp=可续;出战=终点(仅可作末位,landing 即环出口)。增补条目须回契约改版,禁只改代码。
4. **空批与控制流**:空序列合法=「本帧无动作可发」;商店线语义不变(空=完成→关店);备战线兜底处理(连续空批过 stall 门后强制出战或交外循环)由流程侧定义并写入其实现文档,策略侧不感知;策略器禁用空批表达控制流。控制流走词表内特殊动作(DeferSpheres 词表成员,defer 计数归框架;BailToOuter 已退役仅防御性兜底),不进 execute 验证链。
5. **迁移期适配**:现役单动作核包长度 1 序列适配器,行为与现状等价;新核=同接口替换,切换对流程侧零感知。
6. **版本化**:契约条款改动动版本号(v1→v2),禁静默改义(先例:SNAPSHOT_SCHEMA_VERSION)。

## Considered Options

- **备战线维持单动作(双轨)**:被否决——终态已定(序列),对将换接口 build=新核落成即二次迁移;sim 里两形态动作流理论等价,A/B 对比的是决策质量非调用粒度;
- **生产接口用 Decision{ops,control} 形状**:被否决——DirectorV2 退役后该层仅剩 sim/离线用途,DecideAdapter 只支持单元素批是双表示层徒增适配的实证;生命周期机制在流程侧直接挂在动作与 action_key 上;
- **备战空批兜底在契约里定死一种**:被否决——空批处理是执行编排语义,归画面 op,契约定死会冻结流程侧实现自由;
- **两套动作词表(PrepAction/Action)v1 统一**:被否决——词表合并是流程侧后续重构,混入拖契约定稿;留 v2。

## Consequences

- 流程侧备战段升序列执行可与策略器换核**并行**(单元素适配器先行,行为零变更);汇合点=换接新核一次切换。
- 策略器换核的发射器按序列输出,帧稳定截断判断在策略器侧(契约 §3 初始枚举);DecideAdapter 绑定表多元素化列改造件。
- **sim A/B 证明面边界**(2026-09-03 测绘,sim 只消费 update_target+decide_shop_screen):A/B 证明=商店波经济决策;prep 编排域(收球/开箱/典籍/腾席/开商店时机/出战时机)sim 无实体真值源,防线=契约锁+适配器零漂移门+实机。
- pick 类接口不在本轮;遭遇刷新类「旗标+handler 编排」泄漏记 v2 收编候选。
- 契约正文权威链:CONTRACT_SERIES_DECISION.md(工作副本,冻结 v1)→ 汇合点后 strategy/07_plugin.md as-built 承接。

## 修订记录

- **v2(2026-09-03,用户批准)**:§3 截断规则表按接口分域(商店线/备战线)+备战词表 12 类逐类补判(含 4 退役类退役标注)+SwapDeploy 系新增分类+§3.3 未识别动作 fail-closed 处置条款(计数披露义务归遥测键登记纪律,契约不立法键名)。其余条款零改动。对抗审查链:IMPL_ADV_R192 症1→R193 症1-4→R194 症4(修复全闭环)。提案档=`.debug/temp/currency_war/redesign/CONTRACT_V2_PROPOSAL.md`(已归档)。
