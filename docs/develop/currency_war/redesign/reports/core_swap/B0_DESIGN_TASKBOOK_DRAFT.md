# 批0 设计批任务书草稿(编排者暂存;等 R188 修复批结算后发出)

> 暂存原因:修复批正在编辑 IMPL_DESIGN.md,设计批同文件写面,必须串行。
> 派发时本文本为底,按修复批落地后的实况微调。

## 任务

换核重切设计批:把 IMPL_DESIGN.md 实现计划(§6.4 迁移序 + §1 cw4 包树 + 受牵连节)按「换核口径」重切到当前树形,裁决四项语义分歧,产出可直接指导落码批的现行计划。**用文档原生术语**(迁移序/包树/statefn/criteria/发射面;禁用会话黑话——对账批实证「批0/resolver 19条/意图发射器」无文档出处)。

## 输入(全读)

1. `.debug/temp/currency_war/redesign/IMPL_DESIGN.md`(对象本体)
2. `.debug/temp/currency_war/core_swap/CONTRACT_SERIES_DECISION.md`(序列契约 v1 草案)
3. `.debug/temp/currency_war/core_swap/BATCH0_RESLICE_INPUT.md`(免做/改造/新建三档底账 + ④-1..④-5 分歧清单)
4. `.debug/temp/currency_war/core_swap/FIXPOOL_EMITTER_DIGEST.md`(14+1 项发射器需求 + 四共根组)
5. `.debug/temp/currency_war/core_swap/SIM_CONSUMPTION_MAP.md`(A/B 接线约束:rng 中立/registry 属性/零漂移门/证明面边界)

## 要做的

1. **§6.4 迁移序重切**:按三档底账重写(保依赖序形式),每步带验收判据。批0 范围=新建(statefn 8 模块/audit 3 模块/cw4 包/挂后台效果谓词载体)+改造(_select 注册面/assemble 状态量缝/DecideAdapter 多元素绑定——④-1 裁决的连带改造)+前置缺陷(A9:aggregate_economy 枚举补全+sim flat;**排程约束=A/B 双臂同底座**——若随批0 修,声明旧臂基线重采义务;若独立前置批,给出切分线)。
2. **四分歧裁决**(④-1..④-5,每项=裁决+依据+文档改动):
   - ④-1 发射粒度:按序列契约=动作序列输出(与文档 L122 原生一致);DecideAdapter 绑定表单键→多元素列入改造件。
   - ④-2 参数纪律:在文档冻结族原文(标定通道冻结语义)框架内自洽推导。编排者倾向=registry 保持单一标定载体、provisional 纪律重释为「新参数进注册表须带标定状态申报」;与冻结原文冲突时以冻结原文为准并显式呈报冲突,禁默改任一边。
   - ④-3 证明层承载者:proof/line_selector ↔ cw_intention 映射写明,复用/新建分档(stop_buy 现役无对应物=新建)。
   - ④-5 输入面单一源:TurnState.snap vs prep_obs_frame 钉死一个,写明理由。
3. **修复池收编落点表**:14+1 项逐项→批1 哪个面(criteria 七面/发射面/mandate/proof/线级状态机);OPEN 项(P7 对账先决 D-B 深度/D-lv7/F4 度量先修)写进对应批检查点。
4. **批1 结构签名草案**:按序列输出契约(list[PrepAction];帧稳定截断由发射器判,契约 §3 表为初始枚举;输出含 mandate 语义时说明与契约词表的关系)。
5. **记账纪律**(硬约束):NMF 计数链同步(增位/改位重算 45 实指位口径——R186 教训);标链追加不重写;批时快照限定;IMPL_HISTORY.md 加节;design_telemetry.md 登记节加「设计变更」节;冻结族零触碰;冻结残余 11 项口径不动。

## 文件面

IMPL_DESIGN.md(编辑)+ IMPL_HISTORY.md(加节)+ design_telemetry.md(登记节)+ 分歧裁决牵连的 economy/latch 对应节——其余禁碰。

## 合格线

每个裁决论断+证据+推理链齐;设计可执行(落码批可直接照派);记账自检节(计数/标链/冻结三对账);与契约冲突处显式呈报不默改。
