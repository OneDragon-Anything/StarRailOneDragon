# ADR-0508: 危机带储备线降档(P36-a′)

## 状态
accepted(无条件落地,无开关——依据=P36-a′ 推论证明 + match4 复盘病灶
实证;续 ADR-0506 无开关政策)

## 背景
- 病灶实证(match4 复盘 #1):p2r1 hp3/金89/hp 可信——危机臂不开火,
  因 P2 排程升级费把储备线抬到 R*=90(守息线 50+升级费 40),溢余=0,
  ADR-0503 臂辖域 `overflow>0` 不满足。死亡门口持金闲置,与 ADR-0503/
  W907/P23.4「死亡域金终端价值≈0」直接矛盾。
- 机制(cw_economy.reserve_cap 实读):R* = interest_cap×10 + 窗口内
  排程升级费;应急带内排程升级照样计入 → 危机帧可被 R* 整体拦截。

## 决策
危机臂溢余基降档:应急带内取 g 本身(R*_crisis≡0),判据单一址=
`posture_release.crisis_overflow(state)`;消费点三处(`crisis_release_open`
辖域判定 + `release_directive` 危机分支预算式 + `reconcile_spend` 第二
分支对账分类,见「路由面后果」节)同址取数。**不动全局
reserve_cap**——防波及存息准入门/flip 臂等非应急
消费面;预算帽形态不变(仍 min(溢余, REFRESH_ROLL_CAP×刷价)),只改
帽可达性(病灶帧 budget=min(89,12)=12)。

## 证明(要旨;全文=p36 单篇 P36-a′ 节)
(i) 死亡域 P23.4(i):金终端价值≡0 ⇒ 储备(未来升级兑现)无保护对象,
R*>0 使 g≤R* 帧整臂静默=阻断严格劣(P36-a 阻断形态的 R* 形态复现);
(ii) 非死亡应急带弱占优:降档不放大预算帽,解锁提案仍受息档截断(P36-a
首刷豁免外)/boss_floor/g≥0 三门与 EV 过滤辖,近似偏差方向=支出侧如实
声明;(iii) 濒死带 P21 已证升级负——储备保护的恰是负 EV 通道,降档反而
改正;浅带升级授权不经危机预算不受辖。

## 路由面后果(P36-a′ 意图内漂移声明;审计钉护)

降档使 `crisis_release_open` 的辖域从「g>R*」扩为「应急带 g≥1」,两处
**路由面**随之漂移——均为意图内后果(死亡带金零价值 ⇒ 压库买授权无
意义、对账归 crisis 记录合理),声明+钉护如下:

- **路由面:奖励帧 buy_budget 短路**。应急带 1≤g≤R* 的奖励帧降档后被
  crisis 指令接管(posture wrap tag='release'),`attach_spend_authorization`
  对 release 帧短路(不重复授权),buy_budget 不再进入常规授权包。金额面
  无损:降档前该域溢余=0,buy_budget 本就为 0;漂移的是授权/回执路由。
  语义依据:压库买授权([1]/[15])的保护前提是「金有持有价值」,死亡带被
  P23.4 证伪——买授权让位危机搜索与 P36-a′ 同据。钉护=
  test_reward_frame_emergency_buy_budget_short_circuit(含非应急对照)。
- **对账面:reconcile 分类改道**。`crisis_release_open` 实为**三处消费点**
  (辖域判定/release_directive/reconcile_spend 第二分支)——降档后应急带
  g≥1 帧的未兑现对账从 downgrade(tag='存息')变为 'crisis_release' 只
  记录。语义依据:该域帧已由危机臂接管,姿态降级无意义;分类漂移是
  接管面的对账镜像。钉护=
  test_reconcile_downgraded_band_hands_to_crisis(非应急 downgrade 语义
  由既有 no_budget 表锁辖,不变)。
- **时序约定(P3-①,声明不改码)**:不变式车道的两个轮键态——
  ``v3_release`` 由 evaluate_release 装配并自带 latch 轮键
  (v3_release_round=plane,round),``v2_round_refreshes`` 由 decide_prep
  轮首重置、arbiter 刷新采纳点递增;两者复位/装配同在 decide_prep 轮首
  段,轮内跨段只增不清,轮键同源 ⇒ 无跨轮残留面。残留失效方向单向:
  若未来某路径漏复位,残留>0 → 车道判 False → 少刷(不变式欠兑现),
  **不产生滥刷方向**,故不引入第二轮键复核(复核字段自身也需要复位点,
  复杂度无净收益)。

## Considered Options
1. **危机臂内降档(采纳)**:辖域最小、判据单一址、预算帽不放大。
2. 全局 reserve_cap 应急带降档:波及 reward 帧 buy_budget/存息准入门等
   非危机消费面,行为变化无命题辖域,弃。
3. R*→刷价×保留刷新次数:反而把预算压低 2n(预算=min(g−R*,12)),与
   P36-a 不变式方向相反,弃。

## 后果
- 验证=test_cw_w951 病灶帧锁(hp3/金89 → budget 12;金 0 静默)+
  w917 重推锁(降档溢余基+金 0 残留)+危机域邻锁全绿+守卫移除红检
  (撤回降档→14 红)+L1 快速集+ruff。
- 实机观察挂账:match 5+ 危机帧判读关注「低金帧(g<R* 旧口径)开火后
  实花/hp 方向」(预算帽 12 封顶,金流暴露有界);回退评审条件同
  ADR-0506(执行缺位型哑火连续 ≥2 局)。
