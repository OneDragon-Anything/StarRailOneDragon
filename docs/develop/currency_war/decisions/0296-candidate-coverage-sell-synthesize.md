# 0296. 决策框架 v2 候选生成补完:sell 通道语义对齐 + synthesize 独立通道

- 日期: 2026-08-25
- 状态: accepted

## 背景与动机

ADR-0291 骨架的层1 候选生成器只实现了买/升级/刷新/部署四类;
`decision_v2_candidate_coverage` 检查项(ADR-0291 新增,ADR-0294 收进
smoke 豁免表)结构层探针红:期待 sell/synthesize 两候选类型但生成器
未实现——骨架完整性缺口(ADR-0290 层1 枚举义务),不是参数问题。
旧 `_sell_tag` 虽有雏形,但 engine 阵营级卖禁(青雀/娜塔莎等真实角色
全被保护)+ for_gold 语义漂移(副本超额≠弱件折现),探针在合法态下
恒零 sell;synthesize 只有买侧 merge 标记,无独立通道。

## 决策

### 件1:sell 生成器重写(v1 卖通道语义对齐,豁免全部进生成器层)

- **标签三分**(优先序=registry.sell_tag_priority):
  - `off_target`:常态非目标死库存(`_target_names` 外);
  - `for_gold`:应急态弱件折现(hp≤`emergency_hp`,与 filters.
    is_emergency 同式内联——防 import 环);
  - `free_bench`:bench 满腾位让位([32]:目标件也降保护集,v1
    carry 腾位门 r416 语义)。
- **豁免过滤进生成器**(`_sell_blocked`,别在评分层重复判):
  r408 同轮已买不卖(星级加权 ≥3 让位豁免放行)/ engine_seed 2 轮
  年龄窗(ADR-0289 §5,单一源=line_strategy._seed_age_blocked 直通)/
  完整 3合1 份(copies==3)素材豁免(>3 冗余可卖)。
- **删 engine 阵营级卖禁**:v1 无此保护(protect=桥/线名单+close 阵营
  预滤);v2 生成层不做阵营价值预判——件值经评分层板面形态显影
  (卖出后形态查表自然降分,非正分即拒,ADR-0290 层2 语义);v1 的
  close 阵营预滤同理不迁移(它是评分缺失时代的代偿)。评分侧
  `off_target_sell_bias`(ADR-0293 标定 0.5)消费三标签不变。
- **边界**:sell 候选域=bench(执行面=SellBench;deployed 件卖出
  需 SellDeployed 策略动作,Action 联合未含——留后续批)。

### 件2:synthesize 独立生成器(_merge_bench 语义镜像)

- 全场域(bench∪deployed)同名同星 ≥3 份 → 每组一个候选
  (分组键=(char_id, star),cw_state._merge_bench 生产同源);
- 执行体=候选层本地 `Synthesize` 类型(**不进 cw_state.Action 联合**:
  合成在执行层是自动机制——simulate/_merge_bench 买入即并,无独立
  点击);评分交给 scoring 现有函数(当前 simulate 对其 no-op →
  板面查表恒 0 分差 →「非正分」不执行;升星形态增益的消费属形态域
  批后继);执行侧双保险:sim 执行链 isinstance 分派未知类型安全
  跳过、DecisionV2 非默认策略;
- sim 里买入即自动合并 → 独立通道常态零触发,服务**枚举完备性**
  (ADR-0290 层1 义务)与 live 重建态待合并显影;synthes 行为的
  sim 证据=买侧 merge 标记(d2_*_merge reason)。

### 件3:检查项修正与转绿

- 探针判据修正:探针注释「同名 2 份+店有第 3 张」但旧探针只放 1
  份饮月 → 合成候选在任何生成器语义下都不可能触发(结构性不可绿);
  补第 2 份使判据成立(修探针=修 check 侧 bug,非放水);
- 执行层判据映射修正:BuyCard 映射为小写 'buy',旧字面
  `{'BuyCard','LevelUp'} & exec_classes` 里 BuyCard 永不可命中
  (buy≠BuyCard)→ 有买无升级的健康 d2 批也误报死路;死路判据
  锚=buy(LevelUp 账本行不带 d2_ reason,不可达);
- smoke 豁免表移除 `decision_v2_candidate_coverage`(ADR-0294 登记
  的豁免清偿),回归 0 容忍。

## Considered Options(最值钱栏)

- **保留 engine 阵营级卖禁**:拒绝——v1 无此语义;阵营价值预判属
  评分层职责(板面形态),生成层预滤=通道制残影;探针实证真实角色
  全被保护 → 恒零 sell;
- **迁移 v1 close 阵营预滤(faction∈board 不卖)**:拒绝——同为评分
  缺失代偿;且探针态(青雀∈board 阵营)下仍结构性零 sell;
- **synthesize 进 Action 联合(新增 cw_state 动作类)**:拒绝——本批
  文件域限 candidates.py(cw_state 改动波及全部策略/执行链);合成
  在执行层是自动机制,独立动作类无执行语义支撑,留形态域批合流后
  按需评估;
- **sell 候选域扩到 deployed**:拒绝(本批)——无 SellDeployed 策略
  动作(仅在 prep 执行层),生成不可执行候选=噪声;留后续批。

## 验证(n=30 配对,seed 900000-900029,snapshot 池,单进程,同池
同 seed,decision_v2 臂注入;对照=仅 candidates.py 回退 HEAD,其余
工作树同态)

- 检查项:结构层 6 动作类全绿(violations=0);执行层 buy+synthesize
  在册,sell 执行 74 次(对照 37)、merge 买 6 次(对照 7);
- mean=22.70 vs 对照 24.03,**配对差 -1.33,在 ±1.93 分辨率底内**
  (逐 seed 双向:11 局变化,+90/-130 分布,非单边回归);团灭 1/30
  (对照 1/30)、hp_ge_60 1/30(对照 1/30);
- 定向测试:`test_cw_adr0296_candidate_generators.py` 10 锁(标签
  正确性/三豁免/合成分组与反例/检查项绿)全过;0291 骨架锁 14、
  0293 标定锁、smoke(含豁免移除后 0 容忍)全绿;ruff 通过。

## 后果

- 正:层1 枚举完备(六动作类全覆盖,检查项 0 容忍回归);v1 卖通道
  豁免语义单点进生成器(评分层不再重复判);检查项两处 check 侧
  bug(探针自相矛盾/执行层映射)修复;
- 负/风险:sell 更放行(37→74 次/30 局)依赖评分层把关——bench 形态
  折减(ADR-0295 在飞)低估 bench 件值时弱件可能被过早卖出(配对
  差 -1.33 在底内,方向待形态域批合流后复测);synthesize 独立通道
  sim 常态零触发(枚举完备性资产,执行消费待后继批)。
