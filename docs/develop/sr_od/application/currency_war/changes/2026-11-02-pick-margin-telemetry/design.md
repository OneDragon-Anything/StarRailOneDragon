# 候选分量遥测(pick-margin)迭代设计(总纲)

## 0. 元信息

- 迭代目标:补齐**三个低频决策面**的「次名分量」观测——用户裁定(2026-11-01 窄版):①投资环境三选一;②投资策略三选一;③部署定型(真实定型出口)。**遭遇面退出本批**(encounter_pick.py:215-273 为 κ_S 三态+cap 过滤+难度主序,无总分函数,margin 键无定义源;要造总分即第二评分器,违不变式)。
- 状态:定稿(四轮对抗收敛;末轮五项补句处置后,十处置面与直调核全部验证为真)
- 文档清单:无详设(单文档小批)
- 出处:局 g_20261101_125430 复盘观测面缺口(候选 #2)。

## 1. 问题与动机

- 现状:三个决策面只记最终决定(投资环境/策略只嵌胜者分解[invest_env.py:310-347 scores 为决策局部变量,InvestEnvDecision 只带 idx+reason];部署定型只落 deploy_diff 动作序列),次名分量无记录——复盘遇「选得奇怪」无法复算评分对错。
- 根因:**观测面缺项 + 数据通道缺项**(策略遥测正本纪律 strategy-telemetry.md:27「禁依赖决策入口内部局部量」使局部 scores 无法入 payload——通道须先决策)。
- 解决到哪:三面次名分量观测;明确不解决:商店逐牌评估全量、部署搜索组合枚举过程、遭遇面观测(无评分形态,痛点出现再立)。

## 2. 方案(单文档完整设计)

### 2.1 数据通道(先决,双通道定版;正本纪律修订申报)

**投资环境/投资策略 = 词表动作类字段通道**:`CwActionPickInvestEnvParam`(cw_vocab.py:733)/`CwActionPickInvestStrategyParam`(:708)加 `margin: dict | None = None` 字段(kw_only + action_key_exclude 元数据,照 route_tag 先例)——**两决策 dataclass(InvestEnvDecision/InvestStrategyDecision)同加 `margin: dict | None = None` 字段(kw_only 缺省,冻结类追加兼容);次名收集落点 = `_pick_decision` 两屏同构(自动覆盖 decide/decide_pick 双路径)**;flow.py 决策→动作转换处(:425/:485)从决策产物拷入;决策钩子签名改传 result(**基类签名 = `decision_payload(self, result=None)` 缺省参兼容形**——防第三方策略覆写旧签名时 TypeError 静默清零载荷,破坏性变更显式声明为「带缺省的非破坏扩展」;基类声明 cw_strategy.py:267 + bridge 覆写 :372 + wrapper :133 消费)——margin 经动作实例到达 payload 组装面。
**部署定型 = 私有槽通道 + 帧定界机制**(select_deployment 返回裸字典,emit 首动作与定型无关,词表通道结构性不成立;基类 docstring cw_strategy.py:271-272 现文既许「私有 state 槽自存、钩子里读」):
- **select_deployment 保持纯函数**:段 3 收集 top-2 后经**可选收集出参**(`margin_out: dict | None = None`,缺省不收集)携带——真实调用点(entry._step5_deploy)传入,虚拟 4 调用点(shop.py:1217/:1362/sell_candidates.py:342/supply.py:194,其中 sell_candidates 与 entry 实参形态相同,分流只能由调用侧承载)不传即零写入;
- **写入点 = entry._step5_deploy 内、deploy_diff 计算之后**(先算差异再写槽:diff 空 → `{"diff_empty": true}`,非空 → top-2 键形 §2.2-3)——diff 空形态的写入时点在真实出口,无第二实现;
- **帧定界 = 入口清 + 读后清双保险**:`deploy_margin` 槽在 bridge.decide_prep_screen 入口清空(防跨帧陈旧)+ **bridge 覆写的 decision_payload 内读槽后即清**(一次性消费,非部署帧读到恒空;**清槽挂点 = bridge 覆写——decision_payload.py 模块保持「纯读零写」纪律现行文不动,读后清不入该模块**)——落键帧集合 = 备战第 6 步实际到达且 payload 组装可见的帧;**异常路径申报**:prep 帧写槽后 emit 段/truncate 仍可抛异常(决策入口异常不调 payload 钩子,cw_strategy.py:117)→ 槽残留未消费,由下一 prep 帧入口清兜底;跨入口残角(异常后流程未停局且转非 prep 帧)可达窄(策略器异常通常即停局),如实申报为已知边界;
- 槽字段声明在 mandate_state.py StrategyState(槽位定义注释:坐标系/取值时机/写入端)。
strategy-telemetry.md:27 纪律修订:**主句改两类来源**(现读键[gs/state 现读]/产物透传键[词表动作字段与私有槽,均为决策帧出口时点快照])+ 括号禁令改「禁依赖未入决策产物与既许槽位的内部局部量」;**基类 docstring(cw_strategy.py:270-272)主句同批同步**(防码级纪律与正本纪律漂移)。

### 2.2 三面观测键(含边界值表)

1. **投资环境**(词表 margin 字段):`{"runner_up": 竞争域内次名, "runner_up_total": 次名总分, "margin": 差值}`——现值源 = 决策评分帧 `_score_frame` scores 列表(invest_env.py:335-343,含转向轴),禁用 option_total;**边界值表**:竞争域仅 1 候选 → `runner_up/margin = null`;全排除退化帧(:361 tag)→ 按全体域取次名,reason tag 已携退化标记供判读;空候选帧(idx=0 退化)→ 不落键。
2. **投资策略**(同形态,同边界值表):现值源 = 决策评分帧(invest_strategy.py:444-446 加次名收集变量,行为零变申报);取域 = 竞争域次名(:367-419)。
3. **部署定型**(私有槽):挑战者 = **成员集与胜者不同的最高板**(排序键 = 段 3 定序全键(l1,l2,l3,pos,stable,rng_tail)同款——与胜者比较的同一键,禁另立排序);键形 = `{"runner_up": 挑战者板签名(排序名列表), "first_diff_layer": 首异层号(1-3), "layer_gap": 层差}`(板签名承载判读所需「次高板是谁」);评分 = selection_score 三层字典序(:246-251,层间 10³ 隔离 :76-79)。**边界值表**:三层全同(尾键决胜)→ `first_diff_layer = 0, layer_gap = 0`;dedup 后仅一可行板(无挑战者)→ `runner_up = null, first_diff_layer/layer_gap = null`(与尾键决胜的 0/0 区分);搜索返 {}(:873-874)→ 不落键;diff 空收敛帧 → `{"diff_empty": true}` 形态。**虚拟定型边界(穷举)**:select_deployment 全部 5 调用点中,除 entry._step5_deploy(备战第 6 步,产物驱动实际板面的唯一真实出口)外——shop.py:1217(获取让位)/shop.py:1362(让位评估)/sell_candidates.py:342(卖出评估器)/supply.py:194(补给虚拟置牌)——**均不落键**(不传收集出参,§2.1)。

### 2.3 键挂载与登记

- decision_payload.py **新增顶层键** `pick_margin`/`deploy_margin`(现值键集直调 = **6 键**[direction/k_members/k_fallback/window/transition_candidates/member_rank])。
- **键登记单一源 = strategy-telemetry.md 键表,本批随批修复既有漂移**(码 6 键 vs 表 4 行 vs :27「三键组」三处口径矛盾)——正本更新:**键表回填 transition_candidates/member_rank 两行 + 新增 pick_margin/deploy_margin 行 + :27 主句改两类来源 + 键数统一**(键数统一的泛化面 = strategy-telemetry.md 正文计数/bridge.py:373 docstring/**decision_payload.py:3 与 :184 自身计数**)。

### 2.4 不变式

- 评分函数/比较语义/**决策结果**零变化(收集面加变量/拷贝不改序:argmax 与域过滤逻辑逐行不动,仅并行收集次名)。
- 只在决策帧落键:投资两面选卡帧(经词表字段)、部署第 6 步实际到达且 payload 组装可见的帧(经私有槽,入口清+读后清定界,含 diff 空收敛帧的 diff_empty 形态);虚拟定型 4 调用点不落键(不传收集出参,§2.2-3 穷举)。
- 零二次实现:分量读决策评分现值,禁第二评分器。
- 零新数值:margin/gap = 现值差,只记不判。
- 输出量:保守表述「每局数十事件级」(频率随落地批 journal 实测登记)。

## 2.5 验证法

1. 单帧测试:投资两面 margin 键(值序/竞争域次名/excluded 不入/边界值表三形态)、定型 margin 分层记法(首异层/三层全同 0/无挑战者 null/{}不落键/diff 空形态/虚拟 4 调用点不传出参不写槽/入口清与读后清的帧定界)。
2. L1 全绿;prereg:纯观测申报,零验收线受影响。

## 2.6 关键取舍

- **遭遇面退出**:无总分形态,margin 无定义源;非评分形态(可及集边界)另立不值当。
- **双通道(词表字段 + 私有槽)而非单一通道**:决策=dataclass 的面(投资两 pick)走词表动作类字段是正位(动作即产物);部署定型是多步中段产物(select_deployment 返裸 dict,emit 首动作与定型无关)——私有槽是基类 docstring 既许通道;两通道均为「决策帧出口时点快照」,纪律修订同步覆盖(telemetry 正本 + 基类 docstring 双位)。
- **select_deployment 保持纯函数 + 出参收集**:槽写入若放在函数体内,虚拟 4 调用点(sell_candidates 与 entry 实参形态相同)无法分流且污染真实决策帧——出参由调用侧选择,虚拟点不传即零写入。
- **帧定界双保险(入口清+读后清)**:仅靠入口清,prep 帧内第 6 步早退路径漏防;仅靠读后清,跨入口首帧可能读陈旧——双保险使「非部署帧读到恒空」成为结构性质。
- **部署收集面加变量而非结果重算**:定型后重算次名 = 跑两遍搜索(贵且要第二比较实现);并行收集零成本。
- **板签名挑战者而非单角色**:组合评分下「替代席」无单角色语义,板签名(键形内 runner_up 字段)承载判读所需「次高板是谁与成员差」。
