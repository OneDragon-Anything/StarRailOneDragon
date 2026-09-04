# ADR-0286: sim↔生产三活跃分叉合批(xp 真值化 + 轮岗建模 + cap 真值接线)

- 状态:accepted
- 日期:2026-08-24
- 批次来源:批㉓ F3/F4(压测报告 `sim_压测_批㉓_2026-08-24.md`)+ 批㉔ F1/F3/F5(`sim_压测_批㉔_2026-08-24.md`),全部已裁决
- 关联:r421;ADR-0219(三消费面纪律)/ADR-0276(sim 接线先例)/ADR-0281(cap 噪声族留证)/ADR-0284-0285(前两批 sim 语义修)

## 背景与问题

批㉓/批㉔ 压测定位三个「现行 line_v2 栈真正改变 sim↔生产行为」的 GameState
字段缺口(其余简报/env/held 维随管线休眠,不构成活跃分叉):

1. **xp_progress**(批㉓ F3):生产 82% 真值(1562/1903 行)vs sim 恒 None。
   `cw_economy.clicks_to_next_level` 是 line_v2 追级门/boss-breaker LevelUp EV 的
   活消费点——sim 恒按「0 进度向上取整」估点击数,追级类 EV 系统性偏。
2. **refresh_probs 轮岗**(批㉓ F4):生产 20% 决策行(361/1806)带轮岗翻倍
   概率条真值(投资环境每备战阶段随机翻倍一档,cw_plan r77 接线已声明机制),
   sim 恒基线表 → 供给分布缺「随机翻倍一档」机制。
3. **cap 真值读后即弃**(批㉔ F1):生产 `read_deploy_cap` 读到 cap=level+宝钻数
   (D-53/局38 r2 实证)但 GameState 无字段、决策层 14 个 `max_units()` 消费点
   全 level-only → 宝钻局策略误判「板满」(批㉔ F2:52.6% 生产决策帧暴露在
   闸门上);干预臂量级 cap+1 → avg_hp +1.42(批㉔ F3,边缘显著,量级信号)。
   前置拦路项:read_deploy_cap 自带 cap<level 误读族(批㉔ F5,ADR-0281 15 行
   实测),裸接 = 把读错抬到决策层。

## 决策

三件合卷,一条主线:**活跃分叉逐字段真值化,sim 与生产同语义。**

1. **xp_progress 真值化**(cw_sim):sim 结算处维护 `st.xp_progress`——买牌/
   买经验累 `XP_PER_BUY`(与生产同源常量),轮末升级按 `XP_TO_NEXT_LEVEL`
   清零结转;`clicks_to_next_level` 消费点从此读到真值。
2. **轮岗建模**(cw_shop_odds.rotation_probs + cw_sim):新增
   `ROTATION_CHANCE=0.2`(对齐生产 20% 帧率)与 `rotation_probs(level, tier)`
   ——翻倍档 p'=2p、其余档按剩余质量重归一 p·(1−2p)/(1−p)(实读对拍
   60/22/15/3 舍入邻域一致);sim 每备战期掷轮岗事件,轮岗表写
   `st.refresh_probs`(未掷中 None=退基线,生产「未读到概率条」同态),
   `draw_shop`(开态+每次刷新)消费轮岗后表;lv1-3 纯 1 费(2p≥1)结构性
   无可翻倍档 → 恒 None,与生产同态。line_strategy `_sample_cost` 实读
   st.refresh_probs 自动获益(未碰 line_strategy)。
3. **cap 真值接线**(cw_state/cw_observation/cw_sim):
   - F5 噪声门先行:`read_deploy_cap_debounced` 域防抖(cap<level 或
     |cap−level|>DEPLOY_CAP_MAX_DIFF=2 → 独立重截一帧重读;重读入域采重读值,
     仍域外 obs_conflict 留证 + None 拒信——与 r414 域判定同族);
   - GameState 新增 `deploy_cap: int|None`;`read_game_state` 写入防抖后真值;
   - **决策层单点收口**:`max_units()` 优先读 deploy_cap(≥level 才信),
     level 兜底——14 个消费点(cw_plan×11/cw_evaluate×2/cw_events×1)只经
     max_units 一处即全接;
   - sim 宝钻通道:`simulate_p1(diamond_cap_prob=0.0)` 参数化——每备战期以
     此概率 +1 宝钻,cap=level+宝钻数;**注入频率待实机语料统计(replay cap
     键落地后可采),先按 0 建通道留参数**,baseline 与旧树同态。

## Considered Options

- **cap 直接进决策不防抖**(paddle 直读当权威,deploy_bench r64 同款):
  拒绝——批㉔ F5 已实测误读族(cap<level 15 行,全 diff≥2),裸接 = 把
  「低读阻塞上阵」风险从执行层抬到决策层,且宝钻局收益(边缘显著)cover
  不了误读局的板满误判;防抖门成本 = 域外帧多一次截图。
- **max_units 改 14 个消费点逐个接**:拒绝——双源漂移面大;单点收口是
  既有设计(max_units 本就是唯一语义出口),只改一处全接。
- **xp 用 cw_state.simulate(LevelUp) 的账本路径回填**:拒绝——sim 决策循环
  的 xp 是本地变量,买牌路径不经过 simulate(LevelUp);在结算处直接维护
  与生产 OCR 真值同语义,是最小且同源的接法。
- **轮岗精确复刻游戏重归一公式**(实读 22/15 vs 模型 22.9/14.3):
  部分采——整数百分比 OCR 舍入下无法分辨;采用「翻倍档×2 + 其余按剩余
  质量重归一」的机制化模型(锁只锁翻倍档=基线×2),残差 <1 个百分点,
  待更高精度语料再校。
- **sim 宝钻按批㉔ F4 观测频率(钻石族 augment 低频)先验注入**:拒绝——
  语料窗内宝钻 offered 未选、无 chosen 实例,频率真值不存在;建通道留参数
  (默认 0)是唯一不引入伪信号的形态。

## 影响

- sim n=300 基线移轴:轮岗+xp 改变供给与追级节奏(新旧数字见任务报告,
  A/B 分辨率底 ±1.93hp);宝钻通道默认 0 不影响 baseline。
- 生产:宝钻局(cap>level)决策层不再误判板满;cap<level 误读帧被防抖拒信
  (决策回退 level 兜底 = 与旧行为一致,零回归面)。
- sim-wiring.md:xp_progress/refresh_probs 移入「已接线」,deploy_cap 新增行
  ( GameState 36→37 字段)。

## 回归验证

- 新锁 `test_cw_adr0286_sim_truth_wiring.py`(9 测):xp 三态(开局 (0,4) /
  3 买后 cur=12 / 升级结转 (2,20))、轮岗两态(翻倍档=基线×2+重归和=1 /
  非法档 None;sim 事件帧真值形状+频率量级;draw_shop 消费轮岗表
  0.6 vs 0.30)、cap 防抖两态(域内直采/域外重读恢复与仍异拒信)、
  max_units 优先级四态、sim 宝钻通道参数化(默认 0 恒 None/prob=1 真值)。
- sim-wiring 对账锁更新(17+12+3+5=37)。
