# ADR-0213:PrepPhase 观测层重构——「稳定→全面识别→决策→执行」单循环

## Status
Proposed(2026-08-23;用户架构定调)

## Context
PrepPhase 的观察/识别职责散在 4 层,同一备战画面每层各判一遍且判法不一:
1. `battle_loop` 分支分发(3s 稳定门 `PREP_SETTLE_S`)
2. `PrepDirector._run_loop` 环入口(自己的特效消化门+heavy observe)
3. 组合 op 内部(`shop.py` 收起读 HP/开店读 gold;`deploy_bench` 自读部署态)
4. 采集钩子(自带 clean 守卫)

**全架构盘点(2026-08-23 补,98 文件 ~19k 行)**:
- 识别原语调用点(round_by_*/read_*)**254 处散布 20 文件**
  (battle_loop 51/shop.py 34/cw_observation 24/prep_actions 20/
  deploy_bench 19/prep_director 17…)——无统一观测入口;
- 组合 op(shop 483 行/deploy_bench 692 行/equip_all 437 行)是
  "mini director"(内部识别→小决策→动作→验证),与环同构嵌套;
- 事件处理三套入口:handlers×13 + run_nodes×2 + battle_loop 内嵌 0e 分支;
- 健康面(不动):数据层注册表/观测层按画面分模块(docstring 互认)/
  决策层三层语义(ABC→default 执行→line 策略)/telemetry/recognizers/sim。

实证暴露的病(2026-08-23 一天 6 起):
- hp=100 毒读(shop.py 在自己时序读 HP,动画帧 miss→100 默认;局31)
- deployed 6→1(heavy observe 落特效帧;16:42)
- 奖励钩子四次静默(自带守卫的时点假设连环错;r280-r299)
- 各层重复实现"等画面"(固定 sleep/单锚/轮询,3 种写法)

## Decision Drivers
- 用户定调的目标架构:**等待画面稳定 → 一次全面识别(含冲突处理)→ 决策 → 执行 → 下一次画面稳定 → 循环**
- 「等画面稳定」是框架核心纪律(od-dev-write-operation),不该有 4 份实现
- 观测集中后,冲突处理(reconcile/star 防抖/obs_conflict)收口一处

## Considered Options

### A. 就地整理 prep_director(不动组合 op)
- 优点:改动面小
- 缺点:shop.py/deploy_bench 内部的自读自判**原样保留**——hp=100 类毒读
  (shop.py 时序)不解决;治标

### B. 观测层横切(选定)
新建 `cw_observation_gate.py`(暂名):
- `wait_stable_frame(ctx, anchors, timeout)`:统一稳定门
  (clean 锚 + 双帧一致;替代 4 层各自的 sleep/单锚/轮询)
- `observe_full(ctx, frame)`:一次全面识别(state/board/bench/deployed/
  hp/gold/节点行/shop;内部 reconcile/star 防抖/obs_conflict)
- PrepPhase 循环重排:`stable = wait_stable(...) → obs = observe_full(stable)
  → decide → execute → 回 wait_stable`
- 组合 op(shop.py 等)降级为**纯动作执行器**:识别全部上收,
  只接收「已识别的状态+要执行的动作」
- 优点:单一观测真值;每层职责清晰(外层分发/director 决策+编排/
  op 纯执行);所有"等画面"一份实现
- 缺点:重构面大(shop.py 480 行/deploy_bench 700 行的识别段迁移);
  需要分批(先 gate+observe_full 并行跑通,再逐 op 降级)

### C. 推倒重写 PrepPhase
- 优点:最干净
- 缺点:风险不可控(备战链是现网最稳的链路;4 层虽乱但有 896 测试护着)

## Decision
选 B(观测层横切),方案经五轮对抗 review 收敛(定稿=
`cw_dev/重构方案-观测层-v4.md`,吸收 A/B/C/D/Y/终验全部
发现;gate 原语已落地 742d9f03+54f4e35f,flag off 零影响):

**核心定案**:
- wait_stable_frame:min_stable_s 连续稳定窗(首尾帧指纹
  一致,非相邻对——慢动画假稳定)+先 park+三 profile
  (关态[出战锚+圆数门双保险]/开态[收起锚]/弹窗态
  [ocr_keyword 降级,随钩子删]);一致性=锚+per-area 像素
  指纹(OCR 只用于锚);异常 raise 与超时 None 分流。
- 不换:PREP_SETTLE_S 3s 门/分支分发/read_hp 契约/
  GameState.hp/heavy-轻两档。
- director 入口失败:复用 _bail 3-strike(session 计数,
  reason 常量化),不造 round_fail 路径。
- 批次:1 gate 基建+5 站接线(关 3+开 2)+observe_full
  创建(P0②/invest_env 顺带)→ 2 数字读帧态门
  (read_hp_opt 迁移 3 点+readable 标志;recognizer 同源)
  → 3 组合 op 降级(单写者+substate)→ 4 清理。
- flag 4 个按机制分组(进 save 白名单+config.md);
  对拍=flag 二选一非双跑;gate 挂点不进钩子体。

**为何对抗 review 是本 ADR 的必要组成**:v1→v4 五轮拦下
双帧丢时间维度(重开 M47)/read_hp 爆炸面误判/board None
契约未定义/bail 绕 3-strike(无限 ping-pong)/异常折叠 None
(离线升级停机)等 8 个方案级错误——全部是"实现者会写出
错误版本"级问题。

## Consequences
- 观测有单一真值源;毒读类 bug 根治(hp=100/deployed 塌缩)
- 采集钩子不再自带守卫(挂 observe_full 后自然稳定)
- 迁移期双轨(旧新并存),每批独立可回退
