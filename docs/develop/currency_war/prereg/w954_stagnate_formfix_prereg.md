# PREREG:W954 停滞臂 form 假绿修正(sim A/B 预注册)

> 状态=判前写死,批跑前不得改线。设计出处=ADR-0509 修订节 + `docs/develop/currency_war/prereg/w954_transform_impl/CHECKPOINT_w957_reconcile.md`;证据底座=`w957_sim_hunt4/REPORT.md` §3.2(支B:form_ok 恒 1.00 假绿、core_count=1、板面冻结、死时攥金中位 87)。

## 命题

停滞臂(form 修正后)把 P2「锁线后板面冻结、金喂死线」形态转为可改判状态(降级 weak→骨架/salvage 停供),改善 P2 段存活与死时攥金,且不引入换线摇摆。

## 臂与注入

- 同工作树,开关 `intention_stagnation_arm_enabled`:off=缺省表(现行行为);on=sim 侧 `sim_decision_registry` 临时注入 replace(+该开关 True,批后还原)。
- `--planes 2 --pool snapshot --n 300` 双臂同 seed-base 配对(arm B seeds = arm A seeds + 偏移,记录于批次目录);池指纹双臂必同,异指纹=批作废。

## 验收线(跑前写死;不达=不合入,如实记录)

- **G1 触发面**(修正的靶形):on 臂出现 `revoke_evidence.kind='stagnate'` 的降级 >0 例,且逐例带 windows/gap/hp 证据字段;off 臂恒 0。触发例需集中在 form_ok=true 局(假绿靶形),纯假红触发例单列不混计。
- **G2 主判据**:P2 段存活率(on vs off=18.7% 基线)不降,且 P2 死局末金中位(基线 87)下降 ≥20%。
- **G3 防振荡**:换线/降级事件频率上界=每线每位面 ≤1(结构性,violations=0);局均 revoke 类事件数 on-off 不增。
- **G4 零漂移**:off 臂与 W957 批 B(957600)同 seed 抽样 20 局逐位一致(单帧锁之外的批级锚;若指纹不符先查在飞并行批)。
- **G5 哨兵**:触发率上界——on 臂 stagnate 触发局占比 ≤40%(超=判据过宽,回炉阈值,不硬开臂)。

## 判读与兑换

达线→开臂(翻默认+改写断言旧默认锁组);方向反/触发面仍空→回炉判据(先查 form_ok 账本真实分布再动阈值);无效→开关生命周期第 4 态清理或降级为观测。结论当场兑换,禁悬置。
