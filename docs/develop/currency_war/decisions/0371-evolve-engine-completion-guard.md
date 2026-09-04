# 0371 — evolve 引擎补完守卫(「拥有≥门槛却从未同时上场」修法)

- 日期: 2026-08-29
- 状态: accepted (采纳)
- 关联: ADR-0363(引擎下界守卫=防拆,本批=促上,两者互补)、ADR-0367(transition_pair 保护副方向,本批补其「促上」半边)、ADR-0357(p1_pair)、W173 判读(证据基准)、W143 §7.2 候选2(首证)

## 背景与问题

W173(sim n=100,seeds 0-99,池 861fc9f6,invest on):never-2 局
(strict_mal ∧ max_engines<2,P1 成型失败)11 局中 **8 局 own-gap 型**
——曾拥有 ≥门槛 distinct target 件却从未同时上场 ≥门槛(6 局终局仍
手握 ≥门槛件躺备战席;run42 列车 own 4 种峰值上 1、run93 仙舟 own 5 种
峰值上 2、run70 列车 own 3 种上 1)。真供给缺 0 局。

W174 逐轮围栏重放归因(`w174_probe1.py`),三层复合:

1. **围栏 tgt 身份缺失(主)**:围栏 `target_factions` 来自
   `session.target_comp`——①锁局帧=锁定 comp 阵营、配方锁帧=None(空集);
   target 引擎体系(最近可成型引擎)不是锁定 comp 的阵营,其体系件在
   围栏里被归为 rest。三体系件靠 DEPLOY_FENCE 放行进 rest,但
   `ignition_gain` 只给「凑满前最后一张」加分(board<tier-1 的件零加分
   = 冷启动死角),cap 竞争败给锁线 tgt 件(run60 丹恒·饮月 r3-r9 连续
   held[非tgt]、run93 爻光、run15 藿藿)。
2. **cap 满无换人通道(终段锁死)**:r8-9 cap 7/7 全锁线件,围栏只能
   往空位上人,无 swap 机制(run42/46/60/93 的 r8-9)。
3. **演进事务方向偏移**:SKIP_FENCE 轮的 CompTransaction 全朝锁定 comp
   线换档,从不朝 target 引擎体系;W166 transition_pair 保护只「防拆」
   (off-lock 降级/留场资格),不「促上」。

次要:r288 列车门拦姬子;同名副本占 bench(3合1 素材不可上)。
run0 型「曾拥有后被卖出」是卖侧,不在本批辖域。

对照口述:**[20] 过渡是配方不是散买(件上场才算配方)**、**[13] 过渡
成型≈过 P1**(成型缺口=发令枪级);与 W143 §3.4 自毁域的边界:本批修
「从未同时上场」(上场选择),不动末轮 opportunistic(成了被拆)。

## 决策

**引擎补完守卫**(`registry.evolve_engine_completion_enabled`,默认开,
A/B 通道,关=回 W170 后行为;`cw_evolution.evolution_step` 完成提案
分支,**先于常规提案枚举**):

- 触发:pair 体系集(p1_pair ∪ transition_pair;希儿系=单卡判据,
  希儿在手未上场)非空,且某体系 owned(bench∪deployed)≥ tier ∧
  on-board(board_factions 口径)< tier → 缺口;多缺口取
  最接近成型者(board/tier 比,平手按 TRANSITION_TRAITS 序)。
  (**owned 口径已由 ADR-0381 修订**:distinct 名单数,非本 ADR
  首版的全羁绊逐件计数——副本是 3合1 素材非配方件,逐件计数造
  幻影缺口;up_cands 同批加列表内同名去重。)
- 动作 CompTransaction(`_engine_completion_tx`):bench 该体系成员
  (同名已在场剔除=W65 3合1 素材语义,且列表内同名去重=ADR-0381;
  最高星优先)上场;room 不足
  → undeploy deployed 中最弱**非保护**件(保护集=pair 全体系成员 ∪
  引擎件 ∪ 锁定目标件 ∪ 种子窗,复用 `_locked_protected_names` +
  pair 成员判据);bench 容量不足 → sell 最弱非保护 bench 件腾位;
  腾不出 → 不发射,落回常规提案。
- 发射纪律:simulate applied 校验,被拒 → 退避登记(独立签名
  `_COMPLETION_REASON`,2 轮窗);遭遇/boss 冻结轮不启动(与既有演进
  纪律一致);**末窗冻结豁免**(ADR-0363 件2 的同向例外):补完事务
  undeploy 非空时仍可发射,豁免复核 `_completion_freeze_exempt` =
  净效果 pair 体系 on-board 逐体系不减 ∧ 总引擎数不减——构造器结构
  保证(只下非保护件)之后果复核,「补上不是拆」。
- 先于常规提案的优先级依据:成型缺口即 P1 验收缺口([13]);W143
  候选2「evolve 引擎保护」的执行半边——W160 护「在场不被拆」,本批
  补「拥有必上场」。

## Considered Options

- **修围栏(select_deployments)给体系件 tgt 身份/点火冷启动加分**:
  拒为主修——围栏只能往空位上人,对 cap 满局(own-gap 终段主形态,
  8 局中 6 局 r8-9 cap 满)零能力;且围栏双消费面(sim+DeployBench op)
  改动波及面大。事务通道一次覆盖空位与 cap 满两态。
- **复用 execute_replacement 的 UpgradeOption 管线**:拒——三条件
  (2换1/核心/效果投影)语义是「新档换旧档」,与「补齐已拥有体系的
  上场」不同构;硬塞会拉扯 evaluate 语义。
- **末轮整体豁免补完(不做净效果复核)**:拒——复核一行成本换
  「构造器保证」的事后校验,防未来重构破坏不变量(动作索引五查⑤
  同型纪律:期望值类防线须有写入端与复核端)。
- **卖侧保护(run0 型曾拥有被卖)**:记档不修——卖出走 arbiter 候选
  评分,是买/卖决策门域(W143 §3.4/W175 谱系),与本批上场选择边界
  分明;混修=边界漂移。

## 验证

- 新单帧锁 8(`sr-od-test/test/sr_od/app/currency_war/
  test_cw_w174_engine_completion.py`):缺口帧补完上场(cap 满 run42
  型)/保护序(引擎件不被换下)/无缺口不发射(已成帧+owned<tier)/
  flag off 回退/末窗豁免/boss 冻结轮不启动/希儿系单卡/bench 溢出
  卖散件腾位;既有 evolution/w155/w166/w167 邻锁全绿;registry hash
  锁同步。
- sim A/B(同进程同池 snapshot 861fc9f6,seeds 0-99,inject on,
  flag off/on 配对):never-2 与 own_gap 局数、峰值上场收敛、
  strict_mal/engines2/hp/出口金如实对照——数字见 W174 报告
  (`.debug/temp/currency_war/cw_dev/deep_read/W174_报告.md`)。

## 影响

- cw_evolution(完成提案分支 + `_pair_systems`/
  `_engine_completion_tx`/`_completion_freeze_exempt` + 裸签名退避
  helper)、decision_v2/registry(`evolve_engine_completion_enabled`)、
  decision_v2/strategy(registry 注入一行)。
- strategy/02_comp.md §10 与 README 演进行同步语义指针。
