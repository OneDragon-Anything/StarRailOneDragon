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
选 B,分四批:
1. **批次1(观测基建)**:`cw_observation_gate.wait_stable_frame`
   (clean 锚+双帧一致,统一 4 层等待)+ `observe_full`(组装既有
   按屏分模块的 reads——cw_observation/cw_identity_obs 不重写,
   只加组装层+稳定前置);PrepDirector 环入口与 battle_loop 稳定门
   改用它(并行期旧路径保留对拍);
2. **批次2(数字读帧态门)**:read_hp/read_gold/_board_pairs 补与
   read_shop_cards 同款帧态门(审查发现 h;hp=100 毒读根修);
3. **批次3(组合 op 降级)**:shop.py 识别段/deploy_bench 自读段上收,
   组合 op 变纯执行器(接收已识别状态+动作);决策不再降层;
4. **批次4(清理)**:删各层旧等待;钩子守卫统一走 gate;事件入口
   归一(handlers/run_nodes/0e 分支)评估。

## Consequences
- 观测有单一真值源;毒读类 bug 根治(hp=100/deployed 塌缩)
- 采集钩子不再自带守卫(挂 observe_full 后自然稳定)
- 迁移期双轨(旧新并存),每批独立可回退
