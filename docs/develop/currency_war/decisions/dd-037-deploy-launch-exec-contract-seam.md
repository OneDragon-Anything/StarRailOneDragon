# DD-037: 部署「发射×执行」契约接缝——发射门与执行器共用单一源谓词,no-op 状态可区分

## 背景

局 run 20260904_28xx(09:28 起局)第 11 局备战阶段卡死,G3 环级无进展守卫
(cw_loop,连续 3 备战环同签名动作批 ['RunDeploy'] ∧ 状态零推进)于 09:34:31
停机留证。日志三次同构:观测 `bench=1 deployed=3 gold=11` → 发射 RunDeploy →
执行方 deterministic 段配方底线规则命中(「列车 2 档 ∧ 仙舟 2<3 → 列车件留
bench」,仙舟基础线优先防挤占)→ `placed=0/0(跳过 1)` → 组合动作仍报
✓「已部署角色」→ 外循环视为行动完成,下环同观测再发射 → 循环。

这是「发射×契约接缝」家族的新变体(ARCH_REFLECTION_3STALLS.md):发射方
(`DecisionV2Strategy._main_flow_step` 部署段)与执行方(`CwOpDeploy`)对
「是否还有部署可做」使用**不同源的谓词**——执行方持有配方底线/去重/cap 等
全部留置规则,发射方只看「bench 有货 + 有空位」;空计划被包装成 ✓ 成功,
契约接缝把 no-op 伪装成进展。

## 决策

1. **单一源谓词**:kernel `cw_deploy_logic.select_deployments`(围栏/成对/
   cap/去重/配方底线/板空保底全在其中)为唯一判据源;新增薄包装
   `has_deployable(...)` 作「是否存在可部署件」谓词。
   - 发射方:`_deploy_up_candidates(obs, session)` 装配观察帧输入(SIFT
     bench/deployed 身份 + tracking 板面 + decision_target/框架 carry/锁定
     帧)调 `select_deployments`;部署段在 `up` 为空时**不发射 RunDeploy**
     ——bench 留置是合法稳态,直入装备段(阶段位越至 3)。
   - 执行方:`_deploy_deterministic` 的选人/排序段(原 tgt/rest 切分 + 散牌
     围栏 + `_deployment_order` 点火排序,与纯函数长期双源)整体替换为
     `select_deployments` 调用;op 只保留输入装配(SIFT 现读)与拖拽执行,
     循环内动态守卫(fresh 复查/动态 cap/逐件底线仲裁/落点验证)留作运行时
     防线。P24 残余补部署同样受底线辖(fill 段复验 r288,防 kernel 留 bench
     的列车件绕道补部署上板)。
2. **契约硬化**:执行器在 `placed=0` 时按计划空/非空二分——计划空 →
   `STATUS_NOOP`(「无部署可做(计划空,bench为合法稳态)」),计划非空 →
   `round_fail('部署未落地')`;只有 `placed>0` 才报 ✓「已部署角色」。
   no-op 与真实部署在返回状态上可区分,空计划不再伪装成进展。

## Considered Options

- **只改执行器返回值(发射方不动)**:否。执行器报 noop 后外循环仍会重识别
  同一观测、策略层仍发射 RunDeploy——死循环形态原样保留,只是把「✓ 谎报」
  换成「noop 循环」,G3 守卫照样触发。谓词不同源的病根不动,同一接缝会以
  其它动作批签名复发。
- **执行器静默跳过、维持 ✓ 现状**:否。正是本次事故的直接机制:noop 被计为
  进展 → 环级守卫唯一可依据的「动作批签名×状态推进」信号被污染,诊断只能靠
  日志逐环比对;且遥测(damage/decisions 账本)记录的是「已部署」假事实。
- **发射方复制一份执行方规则(轻量判断)**:否。双源正是病灶——规则每演进
  一次(如 ADR-0261 配方底线门)两侧就漂移一次,本次事故即漂移累积的爆雷。
- **采纳:kernel 单一源 + 发射门 + no-op 契约**:执行方与 sim 本就共享
  `select_deployments`(ADR-0261 裁决「1+3 组合」的方向),把发射方也接上
  同一入口,规则演进只改一处;执行器收敛后连「op 侧副本」一并消除。

## 后果

- 正面:局11 形态在发射前第一步即被抑制(重放锁钉死);执行器与 sim 的部署
  决策彻底同源,op 侧 `_deployment_order` 退役为锁测试对账面;no-op 状态可
  观测,环级守卫信号不再被污染。
- 代价/边界:发射门 cap 用 level 链(cap≈level,D-19),宝钻/诅咒加成帧门
  可能保守留 bench——留 bench 是合法稳态,比误判「有部署可做」再进死循环
  便宜(不对称取舍,同 r60/r64 口径);SIFT 未识别件走 fail-open(照旧上),
  门只在身份可判时收口。
- **同类发射点清单(准入审计)**:①`decision_v2/strategy.py` 空板出战守卫
  (phase 3 分支发 RunDeploy)——板空前提使 kernel 板空保底保证计划非空,
  不加门,留观;②`decision/cw4/mandate.py`(MandateV1Strategy,m5 开局/
  m1/m1′ 三处 RunDeploy)——A/B 备用核非现役,其发射判据为 mandate 自有
  体系,若上役需同样接 has_deployable 门(挂账于本 ADR);③`director_v2.py`
  的 v3 引擎 loop(sim 侧)——不落实机拖拽,不经本接缝。
- 回滚:git revert 单提交;行为无开关(默认无开关纪律)。
