# ADR-0313: 掉血报警语义定稿(报警非 ALL IN 触发 / 自然窗时限 / 血边际跳窗 / 三臂战斗节点计数器)

- 状态:accepted
- 日期:2026-08-25
- 背靠:R1 语义保真审查(载体批纪律族 7 条质疑)leader 裁决之项 1-4+项 6;
  W51 语义修复批执行,指挥官亲验通过(未 commit 时落档,随批 commit)。
  落点:`decision_v2/discipline.py`(项 1-5)+ `decision_v2/strategy.py`(项 6)。

术语:掉血报警 = 掉血三臂判据激活的纪律覆盖态(`BloodAlarmTracker`,
strategy_v4 点4);处置梯度 = 报警激活后的分级动作(①自然补强 → ②弃息 D
保血 → ③位面末 ALL IN);ALL IN = 花光提质量,仅位面末最后一战
(`plane_last_battle`)授权([18]/点7)。

## 背景与动机

decision_v2 载体批(ADR-0310)移植掉血报警纪律族时,五处语义走样
(R1 审查实证;「修前」即被否现状):

1. **【阻塞】报警分支 allin 字面 False**:`assess_discipline` blood_alarm
   分支 `DisciplineView(..., allin=False)` 硬编码,注释自认「allin 恒 False
   由本分支字面保证」。后果:报警激活(血最吃紧的死亡螺旋场景)+ 位面末
   boss 轮时,覆盖序 alarm > boss_breaker 遮蔽 boss 分支,地板停在
   boss_floor,位面末 ALL IN 窗([18]/点4 处置梯度③终点)被写没了。
2. **三臂窗口单位漂移**:`recent_losses` 只在战斗节点入窗,但窗口读作
   「最近 3/5 个入窗元素」——非战斗轮(reward/supply)穿插时慢性臂横跨
   远大于 5 轮的窗(可横跨整个位面按日历轮漂移)。
3. **处置梯度①「上界 1 轮」计时器全仓不存在**:报警激活立即 war+硬节点
   放行 refresh(即刻进②),「先给 1 轮自然补强机会」的时限语义丢失。
4. **[19] 血边际变量零消费**:连胜/血边际/来牌三变量中,血量安全边际
   (血 <40 本就是报警档 → 不等自然窗直接梯度生效)在 v2 报警分支无载体
   ——血 30(未到 emergency)照样先进①。
5. **(项 6)跨局键残留**:`on_match_start` 清 v3_* 主体但漏
   `v3_intention_key`/`v3_prev_hp`(顺手 `v3_last_intention_event` 同族)。
   session 跨局复用(续跑/replay,`_ensure_state` 的存在证明该路径真实)时:
   新局 (1,1) 撞旧键 → 首轮 update_target 不驱动意向;`v3_prev_hp` 带旧局
   终值 → 三臂首 record 的 hp_before 是上局血。

## 决策

1. **报警不是 ALL IN 的触发;位面末才是**——报警分支(①自然窗/②弃息 D
   两形态)均传 `allin=plane_last_battle(state, session)`,与 emergency/
   boss_breaker 兄弟分支同式。报警态下位面末 ALL IN 照常开通:授权来自
   位面末(「最后一战不花白不花」),不是来自报警;`allin` 仍是唯一清零
   地板的路径(`DisciplineView.arbiter_registry`)。
2. **三臂窗口单位 = 连续战斗节点计数器,跨位面重置**:窗口读作「最近
   N 个**战斗节点**」(战斗语义下「轮」=「战斗节点」,docstring 声明);
   非战斗节点不计入也不重置任何一臂(点4 冻结语义);`record(..., plane=)`
   位面变更 → 三臂+梯度计时全清(慢性臂不再按日历轮漂移横跨位面)。
   `_BATTLE_NODES` 补生产节点值「普通战斗」——生产链 node_type 产中文
   (battle_loop/cw_settlement_obs),旧集合 `{'battle','遭遇','boss','精英'}`
   里的 `'battle'` 永不命中,属死值;不删 `'battle'`(测试/sim 兼容)。
3. **梯度①自然补强窗时限 = 1 个战斗节点**:`BloodAlarmTracker.alarm_battles`
   计时器(报警激活期间累计喂入的战斗节点数;报警解除/跨位面清零)+
   常量 `BLOOD_GRADIENT_NATURAL_BATTLES`;窗内(`alarm_battles <= 1`)走
   ①`mode='economy'`(不弃息、不放行 refresh);窗耗尽(1 个战斗节点未
   达标)→ ②弃息 D 保血(war+硬节点放行 refresh,点12 保血通道)。
   ①臂失败代理(单场净掉血 ≥10 视为打输)保留,注释标注代理语义与
   sim 校准域。
4. **血边际跳窗**:常量 `BLOOD_MARGIN_LOW_HP=40`([W10 D8-5] hp<40 报警档
   同源);`state.hp < 40` → 跳过①自然窗直入②(escalated 条件之一)。
   [19]③「来牌顺不顺」未消费——docstring 声明欠账(定性变量,sim 层
   无载体,挂实机语料后补)。
5. **(项 6)跨局键清理+喂入口径**:`on_match_start` 补清三项
   (`v3_intention_key`/`v3_prev_hp`/`v3_last_intention_event`);on_round_end
   的全局节点号 `t` 从硬编码 9 换 `NODES_PER_PLANE` 派生,plane 用
   `obs.plane`(N2 权威:结算时位面可能已推进)传入 tracker 做跨位面重置。

## Considered Options

- **报警分支维持 allin 字面 False(修前现状)**——被否:emergency/
  boss_breaker 兄弟分支都传 `plane_last_battle` 同式,报警分支单独硬编码
  是实现笔误非设计;「报警不是触发」约束的是**触发条件**(报警本身
  永不单独开 ALL IN),不是要封死位面末授权——字面 False 把两者混了,
  恰在血最吃紧的场景丢掉终局授权。
- **报警态下位面末不开 ALL IN(更保守读法)**——被否:位面末最后一战
  之后不存在「保留下轮资源」的语义,不花白不花;保守读法只是把实现
  笔误合理化。
- **三臂窗口按日历轮重实现(每轮计窗)**——被否:reward/supply 轮无
  掉血语义,入窗稀释报警信号;冻结语义(非战斗节点不计入不重置)与
  计数器口径(战斗语义下轮=战斗节点)是点4 原文的自洽读法。
- **跨位面不重置**——被否:慢性臂按日面轮漂移可横跨整个位面,把上个
  位面的掉血趋势带进新位面的处置判断(R1 裁决原文:「战斗节点计数器,
  跨位面重置——慢性臂漂移修掉」)。
- **梯度①时限维持无计时器(报警即 escalated)**——被否:「先给自然
  补强机会」是点4 S4 明文,无计时器=语义丢失;计时器按日历轮计也被否
  (同窗口单位判据),用战斗节点计数 `alarm_battles`。
- **血边际新建独立报警档**——被否:`BLOOD_MARGIN_LOW_HP=40` 与
  [W10 D8-5] hp<40 报警档同源,只是「跳过①直入②」的加速器,不是新档
  ——新档会造成两个报警态的覆盖序问题。
- **「来牌顺不顺」强行建模**——被否(R1 裁决「留,实机语料后校准」):
  定性变量 sim 层无载体,凭空数值化=拍脑袋;显式声明欠账优于假实现。
- **跨局键靠 `_ensure_state` None 归一化兜底**——被否:该守卫只归一
  None/类型不符,`v3_intention_key` 撞键值与 `v3_prev_hp` 旧局终值都是
  合法类型,兜底不触发;跨局复用路径真实存在(replay/续跑),显式清。
- **测试策略:锁字面 False 为什么是「锁实现」**(R1 点名,项 7):
  旧 `test_blood_alarm_does_not_trigger_allin` 断言 `disc.allin is False`
  字面——它锁的是旧 bug 的副作用:位面末场景在它的 fixture 里不重叠,
  「报警不触发 ALL IN」的语义边界(位面末该 True/非位面末该 False 两向)
  一向都没锁。修语义而不红=测试在睡。重写为两向语义锁
  (`test_blood_alarm_semantics_allin_only_plane_last`:报警+位面末 boss
  → allin=True+war_floor==0;报警+非位面末 → allin=False+interest_floor
  保持)。判据:测试应锁「该输入下的确定行为(语义)」,不锁实现副产物。

## 影响

- 代码:`decision_v2/discipline.py`(项 1-5:报警分支同式/计数器与重置/
  计时器/血边际常量/`_BATTLE_NODES` 补值)、`decision_v2/strategy.py`
  (项 6:补清跨局键/`t` 派生/`obs.plane` 传入)。
- 测试:`test_cw_w35_decision_v2_carrier.py`——重写 1 条(两向语义锁)+
  新增 4 条(非战斗节点不计入不重置/跨位面重置/梯度时限两段/血边际跳窗/
  跨局键两行为面)。
- 文档:strategy as-built(03_tactics §3 纪律族段、README decision_v2 行)
  同步报警梯度语义;本 ADR 为 why 单一源。
- 行为面变化(合流总验关注):报警首战窗 economy 化、位面末报警 ALL IN
  通、三臂窗口收窄。
