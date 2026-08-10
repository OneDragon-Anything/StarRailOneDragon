# 货币战争 · 决策日志(Decision Log)

> **试点规范(2026-08-03,暂仅货币战争)**:设计文档 = **干净的正文(strategy/)= what** + **本日志 = why**。
> 正文只讲"设计是什么",依据/备选/历史放这里,分开不混写。
>
> **格式**:append-only 按时间倒序(新决策加在顶部)。每条 `D-NN` 紧凑条目:
> - **决策**:一句话 what。
> - **为什么**:why(用户定调/实据/权衡)。
> - **备选**:考虑过什么、为什么不选(**最值钱的字段**,防后人重复扯皮)。
> - **状态**:采用/实验/推翻。反转用 `↺ 推翻 D-XX`。
> - `· §X` 反引到正文(strategy/0N 或 data/)。
>
> **粒度**:密度可变 —— 重磅架构决策多写,权重/数值一句话。不追求一决策一文件(决策多,奢侈)。
> 老条目不改正文(append-only);推翻就新写一条标 supersedes。

---

## 重置说明(2026-08-09)

自主推进期(/goal、/loop)积累的决策(**旧 D-15 ~ D-155**)经判定**不可信**(盲操作 / 不读日志 / 不建画面模型 / 违反预期外画面协议 → cw 代码缺乏对玩法状态的真实理解),已从本文件**删除**。**D-1~D-14 保留**(重走期,可信);新决策从 D-17 续(D-15/D-16 跳过)。完整旧版(D-01~D-155)在 git:`git show HEAD:docs/game/currency_war/decisions.md`(1080 行)。

⚠️ **悬空引用**:strategy/12·13、data/、screens/currency_war_prep 等仍引 D-15~D-155(D-86/D-90/D-106/D-148/D-155…),均指**已删废弃决策,不再维护**(查含义看上述 git 旧版)。

⚠️ **append-only 违规说明**:本删除违反"append-only,推翻用 `↺ 推翻 D-XX` 标注非删"铁律;历史在 git 可查(未丢),但本文件单一源对 D-15~D-155 断裂。彻底修 = restore D-15~D-155 + 顶部标 ↺ 不可信(待 focused 任务,涉及旧 D-17/D-18 与新 D-17/D-18 编号冲突需重排,不在长 session 尾仓促做)。

决策编号从 **D-1 重新开始**。新决策基于重走方法论产生:`od-dev-gameplay-automation` playbook(逐阶段达标)+ `od-dev-progress-tracking` 任务树(状态机 + 防偏离门)。自主 cw 代码标 `# 未验证`,进对应画面时按 skill review 重审后才可信,调完删注释。

## D-1 (2026-08-09)【诊断·重要】观察地基实测可用 → 策略(集中度)才是死 r9 真阻塞;策略层解锁

- **决策**:跑 baseline bot 诊断(r1-7 实跑 + 日志)表明:**观察地基可用** —— 身份跟踪(`灵砂/乱破/大丽花` tracked)+ board 阵营 OCR(`击破/夜之半神`)+ gold/hp/level/round 全读对。bot 死 r9 的**真因 = 策略 naive**:`deploy-swap` 卖 off-target(含佩佩,实测**可卖** —— deployed-lock 是误判,gameplay doc 待修)+ `fill-all`「**无 target/集中 → 全 9 槽填满**」→ 散板无羁绊聚焦 → 战力弱 → 输。
- **为什么**:防偏离门解锁条件 ①(权威源画面子态①-⑤)对 **WORKING 观察满足**(身份/棋盘/经济实测准);3.1(变槽位)/3.3(面板身份)是**增强**(变槽位坐标 / SIFT 漂移恢复),非策略阻塞。②端到端跑通(实测)、③客观指标(round/HP/胜负)已定义 → **策略层解锁**,聚焦集中度 deploy/comp。
- **备选**:① 继续磨观察(3.1/3.3 集成进 flow)—— 诊断显示非阻塞,降优先级(留作漂移恢复/变槽位补,不卡策略);② 全盘重写策略 —— 过激,先改集中度(deploy 别 fill-all、comp 聚焦买/留 target 阵营)。
- **状态**:采用(诊断)。观察机制(3.1/3.3)记进度树待集成;deployed 可卖修正 gameplay doc 的 deployed-lock 误判。
- **⚠️ 纠偏(2026-08-09 自审子 agent)**:本条标题/原结论"策略层解锁"**过度乐观** —— 依据仅**单局(r1-7)诊断**,且 D-12 后证观测回路当时是**断的**(deploy 不更新 tracking → buy 用漂移数据)。按防偏离门:三解锁 ①(权威源画面子态①-⑤)②(端到端观测回路)**实为未过**,仅 ③(客观指标)过 → **策略层仍应锁**。本条"解锁"降级为"诊断假设";D-6/D-9/D-11 在此误判下动了核心策略模块,其"集中有效"结论**作废,待 D-12 观测回路验通后重验**。
- `· gameplay.md(deployed-lock) / strategy/`

## D-2 (2026-08-09)【bug·策略】deploy 集中度 factions/flows 命名空间错位 → 流派羁绊永不 match → fill-all

- **决策**:`deploy_bench._deploy_all_slots` 集中度匹配改用 char **全羁绊**(factions ∪ flows),非只 factions。同步 `_fcount` 计数也含 flows。
- **为什么**:诊断日志(`集中度诊断`)显示 `deploy_idx=[]` → fill-all。根因:`Comp.factions` 混**阵营**(仙舟/银河学者)+ **流派**(击破/追击/持续伤害/减益)于一个「羁绊」命名空间(如 `巡击青雀 factions=[仙舟,追击]`);但 `Character` 拆 `.factions`(阵营)/`.flows`(流派),deploy 只查 `.factions` → **流派羁绊**(椒丘 flows=持续伤害/减益、大丽花 flows=击破)**永不 match** target → deploy_idx 空 → fill-all 散板。
- **备选**:① 拆 `Comp.factions` 为阵营/流派两字段(治本但大改 comp 模型 + 全 callers)—— 记 TODO,先修匹配;② 只改 deploy 不动 comp —— 选(本次),最小解阻塞。
- **状态**:采用(deploy_bench 已改,ruff 过)。⚠️ 同类 bug 蔓延 `cw_decisions`(`bc.faction`/`card.faction` 单字段 vs `target.factions`,~10 处)—— 那些用单 faction 字段(来源不一:bench=阵营[0] / shop OCR=卡面羁绊),需系统审(待策略重做)。
- `· cw_chars(Character 模型) / cw_comps(Comp.factions)`

## D-3 (2026-08-09)【bug·策略】deploy-swap 无 bench 守卫 → 卖光 deployed 无补 → 空板必输

- **决策**:`deploy-swap` 的 `_sell_all_deployed` 前加守卫:**bench 无角色(SIFT read_bench_chars 计数 0)则禁止 sell**。
- **为什么**:实测(12:08:58)bot 板散(8 阵营全 off-target vs DoT target)→ deploy-swap 卖光 deployed,但 bench_count=0 无补 → **空板出战必输**。sell-all 是为清 starter 重 deploy target,但 bench 空时卖 = 自杀。守卫:bench 有角色才 sell。
- **备选**:① 禁用 deploy-swap —— 过激(有 bench 时清 starter 合理);② 只卖 off-target deployed 不卖 target —— 更优但需身份(D-2 修了 deploy 匹配,deploy-swap 可复用),记 TODO。选 bench 守卫(最小止血)。
- **状态**:采用(deploy_bench 已加守卫,ruff 过)。根因仍是 buy 未集中(散板才触发 swap)—— 待策略重做(buy 聚焦 target 阵营)。
- `· deploy_bench(_sell_all_deployed)`

## D-4 (2026-08-09)【bug·机制】deploy SIFT 占用误判空前排 → 跳前排 → 空板出战阻塞 → bot 卡死

- **决策**:`_deploy_all_slots` 的 `occupied_front/back` **不再预填 SIFT**(改靠 retry-stick 实际 stick 判占用)。
- **为什么**:bot 卡死循环(buy→deploy→buy→deploy 不进战斗)。链路:`read_deployed_chars`(SIFT)误判空前排槽为占用(`occupied(SIFT) front=[1,2,3,4]`)→ deploy `if try_idx in occ: continue` 跳前排 → 全拖后排 → **前排空** → 出战被「前台区域无角色」阻塞(出战 click 4× 未落地 → 备战单轮失败 → 外层 loop 重入 → 再 deploy)。SIFT 占用对备战立绘不可靠(脸近景库 ≠ 半身)。retry-stick(实际 drag 后 bench 计数降 = 真占用)才是可靠占用信号。
- **备选**:① 修 SIFT —— 治本但难(半身 ≠ 脸库,3.x 验过);② **CV 占用检测**(亮度/方差:空槽 placeholder vs 立绘)—— 更准,待做(D-4 是止血,弃 SIFT 预填;CV 占用是后续);③ 保留 SIFT —— 会再卡。选弃 SIFT 预填(最小止血)+ CV 占用作后续。
- **状态**:采用(deploy_bench 已改 occupied 预填为空 + SIFT 仅日志;ruff 过)。⚠️ D-4 单独不够:弃 SIFT 预填 → deploy 试全槽(多拖,用户观察到循环拖动)→ **需 CV 占用检测**(只拖空槽)才彻底。身份同理:deploy 不知前后台角色 → 待面板身份(3.3)集成。
- `· deploy_bench(_deploy_all_slots occupied) / insights(SIFT 不可靠)`

## D-5 (2026-08-09)【机制】deploy 占用检测:SIFT → CV 灰度 std(`slot_occupied`)

- **决策**:deploy_bench `_deploy_all_slots` 的 occupied_front/back 改用 `currency_war_cv.slot_occupied`(槽中心 ±55 区域灰度 std > 25 = 已占),替 SIFT(`read_deployed_chars`)。
- **为什么**:D-4 只弃 SIFT 预填(靠 retry-stick),deploy 仍试全槽 → 多拖(用户观察到循环拖动)。CV `slot_occupied` 给**可靠占用**:空槽 placeholder 灰度 std ~11,立绘 ~39-67,阈值 25 干净分离;**不依赖角色身份/颜色**(白角色也准),远胜 SIFT 半身。deploy 据此只拖**空槽**(前排优先)→ 前排能填 → 出战通(解 D-4 的卡死链)。
- **备选**:① 修 SIFT(半身 ≠ 脸库,难);② 亮度阈值(立绘亮度也高,但 std 对「内容 vs placeholder」更稳);③ 颜色/饱和(白角色低饱和失效,见 D-2 时期椒丘问题)。选灰度 std(稳 + 简单)。
- **状态**:采用(deploy_bench 已接 + currency_war_cv.slot_occupied;ruff 过)。**单元验证**:screenshot 上 front[1/3 占,2/4 空] back[1/2/3/6 占,4/5 空] 与 ground truth 全对。**端到端(deploy 填前排 → 出战通)待 run 验**。
- `· currency_war_cv.slot_occupied / deploy_bench(_deploy_all_slots occupied)`

## D-6 (2026-08-09)【诊断·策略】死 p2r1 真因:板散(无 tier-2)→ HP 崩;集中被身份卡

- **决策**:**集中(叠 tier-2 同阵营)是存活关键**,且**被身份卡**(deploy 不知 bench 角色阵营 → 无法叠 → off-target 填满散板)→ **3.3.2 身份集成是集中的前置**。
- **为什么**(实跑一局日志):p2r1 `hp=1 lv=6 board={击破:1,仙舟:1,夜之半神:1,银河学者:1,持续伤害:1,盛会之星:1}` target='DOT队'。**6-7 阵营全 ×1,零 tier-2**;target DoT 但只 1 持续伤害(场上的是击破/其他)。板散 → 每轮掉血 → 位面 1 末 HP=1 → 位面 2 r1 即死。commit 兜底(round≥2)早触发,off-target skip 也早生效,但**早播的散(starters/r1 买)+ deployed 难清**使板持续散;且 deploy 不知 bench 阵营 → 填 off-target 加剧散。
- **备选**:① 强制 commit-from-r1 / 降 COMMIT_FRAC —— 只影响 r1 少量买,不解决持久散(否);② deploy 弃 off-target 填(少 bodies 早死更惨)—— 否;③ **身份集成后 deploy 按"叠已有阵营"排序**(target 优先 + 同阵营次之 + 新阵营最后)→ 叠出 tier-2(选中);④ select_comp 选 shop 可得的阵营(减 target-availability 错配)—— 后续。
- **状态**:采用(诊断 + **ship 了代码**:cw_comps.py:545 select_comp 可得性权重 `0.15+0.85*shop_supply`,原日志仅标"诊断"低估了对核心模块锁的触发)。**下一步 = 3.3.2 身份集成**(让 deploy 知 bench 阵营)。指标:板阵营数下降 / 出现 tier-2 / p2 存活轮数。
- **⚠️ 待重验(2026-08-09 自审)**:本诊断 + select_comp 权重改动的"集中有效/无效"结论,是在**观测回路断(buy 用漂移 tracking)**前提下得出 → **作废,待 D-12 观测回路验通后重验**。
- `· cw_decisions(buy/concentration) / 3.3.2(身份集成)`

## D-7 (2026-08-09)【机制】deploy 确定性部署:CV 占用 → 拖空槽 → CV 验源槽空(替 trial-and-error)

- **决策**:`deploy_bench._deploy_deterministic`:CV `slot_occupied` 知 bench 哪些槽有角色 + stage 哪些槽空 → 每个有角色的 bench 槽拖到一个空 stage 槽(前排优先)→ CV 验「源 bench 槽空了」=成功。替旧 `_deploy_all_slots`(trial-and-error,试全槽 + SIFT 验 bench count)。
- **为什么**:D-5(CV 占用)给可靠占用后,部署可确定性:只拖空槽、CV 验源空(同时覆盖 place + swap)。旧 trial-and-error 废拖空 bench 槽 + 换槽试错 + 依赖 SIFT count(D-4 弃)。CV 验替 SIFT,准且快。
- **备选**:① 保留 trial-and-error(D-4/D-5 后多余);② SIFT 验(deployed SIFT 占用不可靠,D-4);③ CV 占用 + 验源空(本次选)。选③。
- **状态**:采用 + run 验(D-7 实测:CV 验源槽空,放置成功;cap 内 deploy + 出战通,bot 推进 r1-8/boss)。属做法二 deploy op 实现(非核心策略模块)。后续 D-8(排序接 SIFT 身份)/ D-10(卖 off-target)在本方法上扩展。

## D-8 (2026-08-09)【机制·策略】deploy 集中度排序接 SIFT 身份(替 bench_slot_map 跟踪)

- **决策**:`deploy_bench._deploy_deterministic` 的 target-first 排序,改用 SIFT `read_bench_chars`(71 CW 立绘库)读 bench 真实角色身份 → 真实羁绊(阵营 ∪ 流派)判 target,替 `bench_slot_map` 跟踪。
- **为什么**:D-6 诊断集中的前置是「deploy 知 bench 阵营」。原排序读 `_match.bench_slot_map`(shop.py pixel-diff 跟踪,char→物理槽),但该 map **不完整**(pixel-diff 漏检 / 跨回合漂移)→ target 角色在 map 里认不出 → 永远落 `rest` → 不优先 → 集中失败、填 off-target 散板。3.3 身份基础已解决(71 CW 立绘采集 + SIFT 30-49 内点可靠),`read_bench_chars` 直接给 bench 真实身份 → 真正的 target-first 排序 → 集中叠 tier-2。
- **备选**:① 修 bench_slot_map(pixel-diff 本质不稳,弃);② 不排序纯填板(回到 D-6 前的散板);③ 每轮 SIFT 重读 bench(本次选,9 槽 SIFT 一次,可接受)。选 SIFT 身份(治本,替不完整跟踪)。
- **状态**:已实现(deploy_bench `_deploy_deterministic` 排序块 + 签名加 templates;ruff 过)。**待 server 重启 run 验**:目标 = target 角色优先上场 → 板阵营数下降 / 出现 tier-2 / 位面 2 存活。⚠️ 依赖 select_comp 的 target 正确(D-6 可得性权重已减错配);buy 集中度(7.2)仍待做 —— deploy 排序只是「让买到的 target 先上」,买不集中则 bench 仍散。
- **注**:`bench_slot_map` 现仅 shop.py 写、deploy 不再读(`_deploy_all_slots` 是死代码),已冗余 —— 后续清理(shop.py 写 + deploy 删除循环一并删)。
- `· deploy_bench(_deploy_deterministic 排序) / cw_identity_obs(read_bench_chars) / 5.3(deploy 接身份)`

## D-9 (2026-08-09)【bug·策略】committed target 被信号1(涌现)反复翻转 → 振荡 churn → 散板

- **决策**:`maybe_pivot` 信号1(更优 comp 涌现)对**已 commit** 的 target **不再翻转** —— commit 即锁定,只有信号3(HP 危机)/信号2(ceiling 不可达)/drought_bail/losing-streak 能解锁。
- **为什么**:实测(D-6 局)r1-7 target=击破流萤 → r1-8 target=DOT队(均 committed,round≥2)。`comp_score` 随 board 每 round 抖动(board 因 buy 变)→ 信号1 反复越阈值(COMMIT_STICK_FACTOR×1.5=0.15 阈压不住大 board 波动)→ target 振荡 → buy 每轮为不同 comp 买 → 永不集中 → 散板(8 阵营×1)→ HP 崩 → 死 p2r1。这是 target→buy→board→comp_score→target 自反馈环。治本:斩断环 —— committed target 不被 board 抖动驱动的信号1 翻转。人玩同理:commit 后不因「略优 comp」弃成型,只危机/不可达才转。
- **备选**:① 再提 COMMIT_STICK_FACTOR(×2/×3)—— 治标,大波动仍可超,且难定值;② 信号1 改比 form_progress(稳定单调)非 comp_score(抖动)—— 更精细但复杂,待 D-9 验后看是否需要;③ commit 后完全锁(本次选,信号3/2/drought/losing 仍解锁,安全)。选③(最干净,直接斩环)。
- **状态**:已实现(maybe_pivot 信号1 块:committed && !losing → 跳过 + 日志;ruff 过)。**待 run 验**:target 应停止轮间振荡 → buy 单方向 → 板阵营数下降。⚠️ `COMMIT_STICK_FACTOR` 现 maybe_pivot 不再用(死常量,待清);commitment 仍由 COMMIT_FRAC/COMMIT_ROUND(target_committed)定义。配合 D-8(deploy 集中)+ 本修复(target 稳定),buy 才有单一方向可集中。
- **⚠️ 程序注记(2026-08-09 自审)**:本条改 `cw_comps`(核心策略模块),当时核心锁 ①② 未过 → 程序上该等观测回路。但**振荡 bug 本身(r1-7 击破流萤↔r1-8 DOT队)是 `on_round_end` 日志直接观测**(session.target_comp.name 轮间翻转,非 tracking 依赖)→ bug 真实、fix 直接验(target r1-2/3/4 稳定也是直接观测)。下游"集中度提升"效果仍属推断,待 D-12 观测回路验通后随 D-6 重验。
- `· cw_comps(maybe_pivot 信号1) / 7.1(target 稳定)`

## D-10 (2026-08-09)【bug·机制】deploy-swap 一次性冻结 → off-target 永驻板 → bench target 上不了场 → 死锁慢失血

- **决策**:`deploy_bench` deploy-swap 改为**卖 off-target deployed(留 target)+ 1:1 替换上限**,替旧「一次性 sell-all」。bench 有 target 单位时,卖掉板上 off-target(`read_deployed_chars` 识别,≤ bench target 数)给 bench target 腾位。
- **为什么**:D-8+D-9 run 实测死锁:r1-6 bench 堆满 **target(击破)单位**(`艾丝妲/乱破×2/阮·梅/大丽花`,SIFT 识全击破),但**上不了场** —— 板满(lv4 cap=4)+ 旧 `deploy_swapped=True` 一次性冻结 → off-target 永远卖不掉 → bench target 堆着、板冻结 off-target → 每轮掉血 → 死。bot 其实**在买 target 集中**(集中化发生),卡在「上场」这步。修:解开 sell —— 卖 off-target 给 target 腾位。人玩同理:确认方向后卖杂牌上阵核心。
- **备选**:① 解冻旧 sell-all(一次性→每轮)—— 毁板上 target(merged star)+ 每轮 churn,否;② 保留一次性 + 改 buy 不买 off-target —— buy 已买 target(bench 证据),根因不在 buy 在上场;③ 只卖 off-target(留 target,本次选)—— 不毁 target、自收敛(板全 target 停)、1:1 上限保板大小。选③。
- **状态**:已实现(`_sell_offtarget_deployed`:read_deployed_chars 识别 off-target + 1:1 替换上限 max_sell=bench_target 数;swap 块去 deploy_swapped 一次性;`_deploy_deterministic` 改 fresh `self.screenshot()` 看 post-sell 空槽;ruff 过)。**待 run 验 + 首验 read_deployed_chars**:① read_deployed_chars 身份准否(日志详记,首跑核实);② 卖 off-target → bench target 上场 → 板阵营数降 / tier 叠。⚠️ `deploy_swapped` flag + `_sell_all_deployed` 现冗余(待清);依赖 D-9(target 稳,否则 off/target 判据漂)。
- `· deploy_bench(_sell_offtarget_deployed / swap 块 / _deploy_deterministic fresh screenshot) / cw_identity_obs(read_deployed_chars 首用)`

## D-11 (2026-08-09)【策略·调参】7.2 buy 囤 target:`BENCH_TARGET_WEIGHT` 3→8(让集中速率跟上)

- **决策**:`cw_decisions.BENCH_TARGET_WEIGHT` 3.0 → 8.0(bench 上 target 单位的 eval 权重)。
- **为什么**:D-8/9/10 集中系统机制都通,但**集中速率被 buy 卡** —— greedy buy 第 2+ 张 target 卡(板满落 bench)delta = +BENCH_TARGET_WEIGHT(3) − 金成本 + 协同递减 ≤0 → buy 停在 1-2 张(buy 统计:买1×12,从不买3+)→ bench 极少积 target → D-10 `max_sell=bench_target` 每1轮只 1:1 换 1 个 off-target → 板 6-8 阵营来不及在 ~9 轮内集中 → boss 战损大 → p2r1 死。**D-10 的 1:1 上限其实最优**(卖更多只被 bench off-target 补,净减=bench_target 数)→ 唯一杠杆是**让 buy 成量囤 target**。提权重至 8:每张 bench target +8(常数,不随协同递减)→ delta 持续正 → buy 板满时囤 target → D-10 下轮成量换(lv4 板满 4 off + bench 4 target → 一轮全换)。
- **备选**:① 松 D-10 1:1 上限 —— 净减不变(bench off-target 补位),无效,否;② 改 buy+deploy 非原子(囤 bench 不即上)—— 大改,且 deploy op 已分开处理;③ 提 bench target 权重(本次选)—— 最小、对症、与 D-10 max_sell 协同。选③。
- **状态**:**二次回退 =3.0(2026-08-09 A/B 负)**。重实现 =8 后 fresh A/B:D-11 局板**更散(r1-8 无 tier-2,全 ×1)**、p2r2 hp3 **< baseline(D-14)hp16**。**D-11 未帮集中反更散 → p2 更弱**。结论:**buy hoard 单杠杆不治 p2 死** —— bot 能激进买(7 张/轮),非 buy-quantity 限;板散是 comp 选择/pivot + deploy 集中度问题,非 buy 权重。D-11 两次试(=8)两次回退,确认非杠杆。=3 保留。
- `· cw_decisions(BENCH_TARGET_WEIGHT) / 7.2(buy 集中)`

## D-12 (2026-08-09)【机制·观测回路】deploy 后 SIFT 真实身份纠 tracking 漂(3.3.2,解锁核心锁 ②)

- **决策**:`deploy_bench` 加 `_reconcile_tracking`:deploy 完成(shop 关、bench/deployed 全可见)后,用 SIFT `read_bench_chars`+`read_deployed_chars` 读**真实身份**重置 `session.tracked_bench_chars`/`tracked_deployed`(保留旧 tracking 的 star,按 char_id 匹配)。
- **为什么**:观测回路断点根因 —— deploy op 视觉拖拽(D-7/D-8/D-10)不调 `mutate_bench_deployed` → session.tracked_bench_chars/tracked_deployed 滞留(已上场的还显在 bench、已卖的还显在 deployed)→ 下轮 buy 用**漂移 tracking** 做集中度判断(`bc.faction` 错)→ 错。read_game_state 的 deployed 也是 tracked+rebuild(假身份)。D-12 在 deploy 后(真实态)用 SIFT 纠正 → 下轮 buy 用准 tracking。**完成观测回路 → 解锁核心锁 ②(端到端观测回路通)**,为策略调优(深度集中)扫前置。
- **备选**:① 在 read_game_state 加 SIFT —— shop-open 时 shop overlay 可能遮前排 + 循环内多次调贵,否;② 用详情面板 OCR 读 deployed 身份(task#115)—— 慢(逐个点开)+ SIFT 已验证可靠(D-10),否;③ deploy 后 SIFT 纠 tracking(本次选)—— shop 关准确、复用 D-8/D-10 已有 SIFT、保留 star。选③。
- **状态**:**已验证(2026-08-09 16:34 局,pre-log 直证纠漂)**。补 pre-log + 修 star multiset 碰撞(review 要求)后重启验:r1 deploy pre=`bench=[阿格莱雅,艾丝妲] deployed=[]` → post=`bench=[爻光,阿格莱雅,艾丝妲] deployed=[希儿,藿藿,飞霄]` —— **tracking 滞留(deployed 空却实际 3 个已上场),D-12 纠正**。pre≠post 直证纠漂(非 no-op)。**观测回路闭合 → 解锁核心锁 ②(端到端观测回路)**。⚠️ star multiset 防重复 char_id 碰撞;SIFT star 恒1,身份准为主。shop.py 过时注释已修。
- `· deploy_bench(_reconcile_tracking) / cw_identity_obs(read_bench_chars+read_deployed_chars) / 3.3.2(身份集成进 obs)`

## D-13 (2026-08-09)【bug·观测】level OCR 间歇误读(等级倒退)→ 单调守卫(做法二 obs 可靠性)

- **决策**:`cw_observation.read_game_state` 加 **level 单调守卫**:读出 level < `session.last_level_obs`(上次真值)→ 用上次(等级局内只升不降);`StrategySession` 加 `last_level_obs` 字段(新局默认 0)。
- **为什么**:3rd 自审 §4 抓 —— read_level OCR 间歇把 5/6 读成 4(实测 r1 lv4→r2 lv5→**r3 lv4**(倒退)→r4 lv6→**r4 lv4**)。等级不可能降 → lv4 是 OCR 误读(非 _expected_level 兜底:p1r3 兜底=5)。level 字段不可信 → **max_units/cap/economy 全跟着错**(cap 读低 → deploy 少 → 板弱)。守卫:单调不降(读出<上次=误读,用上次),治 OCR 倒退症状。
- **备选**:① 修 OCR 数字识别本身(难,不确定为何 5/6→4);② 放宽区域重读(区域已收紧);③ 单调守卫(本次选,简单 + 治倒退症状)。注:守卫不修「真升 OCR 滞后读旧值」(real 6 OCR 5 → 守卫保 5 漏升),但倒退(6→4)是明确错,守卫先治此;OCR 本身待另修。
- **状态**:**已验证(2026-08-09 16:55 局)**:r1 lv4 → r2 lv5(单调不降),守卫触发 **6 次**(OCR 把 lv5 读成 3/4 被纠正;证据备份 run_D13_1655_evidence.log)。level 字段可信 → max_units/cap/economy 不再因 level 误读错。属做法二 obs。
- `· cw_observation(read_game_state level 守卫) / cw_strategy(StrategySession.last_level_obs)`

## D-14 (2026-08-09)【策略·经济】_saving_for_level 去 _board_strong 门 → 弱板也攒级升级(破 chicken-egg,p2 杠杆)

- **决策**:`cw_decisions._best_improving_action` 的 `_saving_for_level` **去掉 `_board_strong` 门控**(原 line 538 `_saving_for_level = _saving_for_level and _board_strong` 删除)。`_saving_for_interest` 仍门控(息是经济,板强才囤)。
- **为什么**:4th 自审 + 经济诊断 —— bot 卡 lv6 大半局(die p2)。根因:`_saving_for_level` 被 `_board_strong`(form_progress≥0.4)门控 → tier-2 弱板(form_progress<0.4)→ **不攒级 → 花金在买/刷 → 永不升级 → 卡 lv6 cap → 上不了更多单位 → 永 tier-2 → p2 死** = chicken-egg(弱板→不升→弱)。旧门控意图"板弱该花钱建板别囤",但 buy 受可得性限(DoT 稀疏凑不齐 tier-3,见 insights)→ 钱浪费在 refresh/off-target → 没升级 → 永弱。**升级是 tempo 投资**(提 cap + shop 高费刷新率),任何板都该追。去门控:弱板也攒级(抑制 off-target 买+refresh 浪费,留 target 买 + 攒金)→ 够 cost 下轮 plan level gate(优先)升级。
- **备选**:① 提 INTEREST_WEIGHT(让攒息值 → 但不直接促升级);② 改 level_plan 更激进(治本但复杂);③ 去 _board_strong 门(本次选,最小、直击 chicken-egg)。选③。
- **状态**:**已验证有效(2026-08-09 resume+fresh 局)**:D-14 后 lv6 时 gold 达 **53**(baseline max 43)→ bot **升1次 到 lv7**(plan `买1张 升1次` @ gold=53 lv=6;baseline gold≤43<48 够不着)。**D-14 修对了 leveling**(saving 不足→够不着 cost→卡 lv6),5th 自审"改错层"是基于 baseline gold"43-50"的误读(实际 max 43<48,够不着非"够却不升")。**但 p2 仍死**(resume 局升到 lv7 仍挑战失败)→ p2 存活还需 **comp 质量(tier-3,见 insights comp 可得性诊断)**,leveling 必要不充分。D-14 保留(真修)。
- **【核心锁声明(2026-08-09,审查 P1-b)】**:D-14 改 `cw_decisions`(核心策略模块),防偏离门 ① 未过 → 按门核心模块改动该等 ①。但 D-14 **不像 D-6/D-9 作废**:D-6/D-9 的"集中有效"结论依赖 buy tracking(② 未通时漂移),而 D-14 的"leveling 修对"结论是 **plan 日志直接观测**(gold 53→升 lv7,非 tracking 依赖)→ 证据基础可信,② 通不通都不影响。故 D-14 **保留 + 显式声明 ①-例外**:① 过后 comp 层重做时复审(确认去 `_board_strong` 门不与新 comp 逻辑冲突),在此之前"leveling 修对"作可信结论,但下游"p2 存活需 comp 质量"仍待 ①。
- `· cw_decisions(_saving_for_level 去门) / 收尾·策略(经济 tempo)`

## D-17 (2026-08-09)【研究·证据基】货币战争机制攻略研究(经济/装备/A8 阵容)—— 后续 economy/equip/comp 改动权威依据

- **决策**:后台子 agent(clean context)查米游社/bwiki/TapTap/17173/豌豆荚攻略源,产出给代码用的机制依据(带证据等级「原文确认/通则推断/未查到」+ 来源 URL)。三条核心:
  - **Q1 经济**:利息每 10 金 1 息(原文,17173)、50 金封顶 5 息(通则);等级 3→10 且=上阵数上限(原文);**正确节奏 = 先冲等级(4级前主升级)→ 维持 50 金吃满息 → 多余金币刷牌/买同费卡(卡池稀释提目标卡概率);奖励关不花钱留息**;**升级费用表攻略不记 → 从游戏内「数据银行」图鉴取**(代码现表是估,但 6→10≈262 与攻略"270"吻合,大致对)。→ 印证 bot「囤金不升级」是坑;D-14 leveling 方向对(攒够 cost 就升),gold<50 不花符合"维持50息线"。
  - **Q2 装备**:攻略说**拖拽**穿戴 + 拆装扳手拆 + 2 简易合 1 进阶;**攻略未提「装备推荐」按钮**(但 VLM 实测 2 样本[万敌+镜流]看到该按钮稳定存在 → 攻略只讲手动拖拽,按钮功能待 live 验);每局保底 ≥3 装(开局+1 / p1boss+1 / p2boss+1 + 奖励/补给节点);**装备是 A8 成型关键**(「1雅1鞋成型」、反重力皮靴必备,裸装输)→ **bot 当前完全不装(EquipAll 解绑 e9747690)是 p2 大杠杆**。
  - **Q3 A8 阵容**:**A8 是均衡混搭(6+3 双羁绊:6DoT+3昼神 / 5能量+4昼神 / 6燃血+5夜神),非纯单阵营叠高** → 印证「集中到 tier-3 做不到」(正确策略本非纯集中);四大羁绊阈值(贝洛伯格2人激活最低/昼神3人/减益8人/DoT6人);「净化身心」环境克 DoT/减益 → 选阵须检测环境;辅助(缇宝/星期日/记忆主/知更鸟)> 非核心羁绊。
- **为什么**:p2 死多因子,单杠杆调(D-11/14/15)皆不治;需权威机制依据定方向而非凭猜。研究带证据等级 + 来源,可直接入代码或指引下一步。
- **对后续指引(非本条代码改动)**:① **装备 = 最高杠杆**(bot 裸装)→ 优先 live 验「装备推荐」机制 → 重启用 EquipAll;② comp 从「集中」转「均衡 6+3」(收尾大改,核心锁通后);③ economy tempo D-14 已大致对,微调靠图鉴费用表;④ 升级费用表从「数据银行」图鉴提取(权威单一源,优先游戏内图鉴)。
- **状态**:研究完成(证据基已立)。后续 D-18+(economy/equip/comp 具体改动)引用本条。
- **来源**:官方 sr.mihoyo.com/news/160700(机制);bwiki wiki.biligame.com/sr/货币战争(装备/合成/拆装);TapTap V3.7 攻略(升级节奏/牌库);17173 上分+四大羁绊;豌豆荚(A8 三套阵容);4399(1雅1鞋成型)。米游社 content_id 未取到(官方页 JS 渲染)。
- **注**:decisions.md 缺 D-15(formation_cost 强化后回退)/ D-16(drought invested-guard)两策略改动记录(doc-sync 漏),待补。
- `· docs/game/currency_war/strategy/ / insights.md / prep doc(装备推荐按钮)`

## D-18 (2026-08-09)【机制·装备】live 验装备穿戴 = 拖拽(非 click;装备推荐=浏览)

> ⚠️ **后半(L164-165)已自修正**:装备区 x1800-1918 是装饰球体(非装备),`equip_all` 区域错。**前半(装备推荐=浏览 / drag 机制)仍有效**。D-23 增量补充(装备槽在详情面板)。

- **决策**:live 实测(手动导航到备战 + 买牌部署藿藿)验装备穿戴机制:
  - 「装备推荐」按钮(~x1509,y816)click → 弹「推荐装备/次选装备」列表(OCR 实锤),**非自动穿**。
  - 点列表装备 → 弹装备信息详情(生命之环:stats/适配角色/合成公式),**不穿戴、无穿戴按钮**。
  - → click-flow 全是信息浏览;**装备机制 = 拖拽**(research 攻略 + 排除法)。
- **为什么**:D-17 疑「装备推荐」一键穿;live 证伪 → EquipAll **无 clean one-click**,必须走 drag(修 e9747690 回归)。
- **状态**:机制确认(拖拽)。**drag 回归根因已诊断(2026-08-09 重接 EquipAll + 跑 bot 实测)**:`_detect_equip_icons` 亮度检测**有假阳性** —— 把 r1-1 装备区**装饰球体误判成 owned equip icon**(检测到 2 个 @ (1851,189)/(1851,316),但 r1-1 无真装备;VLM 确认是装饰球体)→ drag 假 icon → 假"装备成功"(icon 2→1 是球体被位移,非真装备)+ transient 出战"找不到按钮"retry(bot 恢复到 r1-2)。**极可能就是 e9747690 原回归根因**:板满时假 drag 释放到角色→位移→前台空;r1-1(未满)没位移但 transient 出战失败。**修法 = 修检测(拒装饰球体,只认真装备 icon)** —— 需先看真装备 icon 长啥样(r1-5 补给后,detect-only 跑到那时截图核)。EquipAll 已**撤销重接**(回 买→部署→出战,不假触发);equip_all.py 保留 drag 截图诊断 + 检测代码待修。
- **⚠️ detect-only 跑到 r1-6(补给后已有装备)再核(2026-08-09)**:装备区 x1800-1918 **仍是装饰球体**(VLM 2 样本一致:r1-1 + r1-6)→ **检测区域从根本上错(整片球体非装备),不是"拒球体"能修**。owned 装备**不在 x1800-1918**(可能 x1252-1800 左半,或补给给的装备直接在角色身上)。**→ 装备需先正确建档装备区(owned 装备位置/外观,走 od-dev-screen-onboarding)再重建检测**;equip_all(x1800-1918 亮度检测)整个建在错区域上,待建档后重写。EquipAll detect-only 重接已撤(回 买→部署→出战)。
- **副产物(economy)**:plan 日志证 bot 能负担就升级(r1-6 gold54→升1、r1-8 升2),负担不起才"买0升0"= 符合维持50息线 → **economy 没坏**,p2 死主因 = 裸装 + comp 没深成型,非 economy。"gold74 lv5"是 OCR level 误读(D-13 守卫未全治)。
- **备选**:放弃装备 lever(裸装输但能出战)—— 否(research 称装备 A8 必备,大杠杆)。
- `· strategy/07 / prep doc(装备推荐机制) / equip_all.py(drag 回归待修) / cw_state.card_cost(=card.cost,买卡费用认得)`

## D-19 (2026-08-09)【机制·经济】团队规模上限 = level + 财富宝钻(后排槽位非固定 6)

- **决策**:deploy 槽位数 = **前排固定 4 + 后排基准 6**,但**团队规模上限可被财富宝钻(装备,无论是否穿戴)+1**(`equipment.md:211`),诅咒·宝石剑泽尔里奇对应 -1。→ 后排槽位**不可硬编码 6**,deploy_bench 须按运行时实测槽位数部署。
- **为什么**:用户确认(前排不变、后排特殊环境/钻石等增加)+ 数据核实(equipment.md:211 财富宝钻「团队规模上限+1」;红钻/蓝钻是合成材料不加位;投资环境 84 + 投资策略 315 条均无加位机制)。原 prep doc「前排是否也变待核」由用户拍板:**前排固定**。
- **备选**:① 硬编码 6 —— 错(财富宝钻 +1,实测见过后排 7);② 运行时实测槽位数(本次选,deploy 须动态);③ 静态表 —— 无(随装备动态)。
- **状态**:机制确认(已补 prep doc + gameplay doc max_units 行)。deploy_bench 现 baseline 前4后6,**待改运行时实测**(核心锁① 过后 deploy 重做时)。`· prep doc / gameplay.md(max_units)`。

## D-20 (2026-08-09)【纠正·身份】立绘库 character_cw_portrait 采了+deploy_bench 用了;脸库旧实测不适用;备战 recognizer 接入角色识别

- **决策**(三件):
  1. **立绘库真相纠正**:货币战争立绘库 `character_cw_portrait`(**采了,71 角色,中文 key,含变体分开采:姬子/姬子·启行、刃/千冶·刃…**)—— `deploy_bench._get_templates` 实际加载它(**非** character_avatar 脸库)。旧 docstring(currency_war_char_id / cw_identity_obs)说 character_avatar,**过时、与代码不符**(曾误导判错)。已修 docstring 对齐立绘库 + L115 离线 demo 也改立绘库。
  2. **「不可靠(4 角色)」是脸库旧实测**:`currency_war_char_id` docstring 的 2026-08-06「4 角色强命中」实测明说用 character_avatar 脸库;立绘库 `character_cw_portrait` **实际效果从未实测**(理论上更可靠:域匹配 + 含服装,变体分开采或可区分共脸)。**实测前勿据脸库旧结论判立绘库不可靠**。
  3. **备战 recognizer 接入角色识别**:`battle_prep_recognizer` 现产 `front_line`/`back_line`/`bench`(`read_deployed_chars`/`read_bench_chars` 纯读 SIFT,templates 从 `ctx.cw_portrait_templates` 取,未加载→None 不自己 load)。诚实标注可靠性待实测,未实测前不据该字段做硬决策。
- **为什么**:用户质疑「立绘库采了为何没用」→ 核实发现 docstring 过时 + 代码实际用立绘库 + 脸库旧实测被误套到立绘库。`read_deployed_chars`/`read_bench_chars` 经核实是**纯读**(`identify_slots` 纯 CV 不写 session),可安全进 recognizer(并发安全)。
- **备选**:① recognizer 不产角色(旧立场)—— 否(立绘库该用 + 纯读入口存在 + 结果供智能体交叉验证非盲信);选接入 + 标注。② recognizer 自己 load templates —— 否(重操作 + 副作用,违纯读);用已缓存 `ctx.cw_portrait_templates`。
- **状态**:docstring 修对齐立绘库 + recognizer 接入角色识别(测试 34 过)。**待实测**:立绘库命中率(需游戏,核心锁①子项)—— 决定角色识别可不可信。`· currency_war_char_id/cw_identity_obs docstring / battle_prep_recognizer / 进度树(① 子项)`。

## D-21 (2026-08-09)【策略·设计】阶段节奏骨架(阵容无关 × 阵容参数)+ 完整刷新概率表

- **决策**:策略骨架 = **阵容无关的通用节奏(一套)** × **阵容参数(每 comp 填 `level_plan`/`factions`/`core_chars`/`key_equips`)**,灵活支持所有 T1,不为每阵容硬编码流程。写进 `strategy/14_phase_skeleton.md`。核心:等级曲线驱动(+ bwiki 完整刷新概率表 Lv1-10 作 `level_plan` 硬地基)+ 节点×等级×动作骨架 + 经济线 + 骨架/参数分离(`level_plan` 接缝)。
- **为什么**:用户要「总结每阵容每阶段做什么」灵活支持所有 T1。工程化解法 = 不为每阵容写流程,而是骨架统一 + 参数化 `level_plan`(03 已有 level_plan 设计,本调研用概率表坐实地基 + 系统化节点动作)。最大增量 = bwiki 完整刷新概率表(现有 economy_research 只有「7级3费=0.4」一个点)+ 节点动作表 + 骨架/参数分离论点。
- **备选**:① 每阵容硬编码一套阶段流程 —— 不灵活(新增阵容要写流程),否;② 纯 eval 驱动无阶段骨架 —— 缺节奏指导(何时升/D/all-in,A8 节奏关键),否;选 骨架×参数(03 `level_plan` 的系统化)。
- **状态**:`14_phase_skeleton.md` 写好(设计文档,what)。**不改核心策略代码**(锁①未过;02 `SHOP_REFRESH_TABLE` 接 A4、`level_plan` 填 comp 都是锁①过后实现)。V4.4 评级 🟢(推翻 V3.7 阿雅降 B);升级费用 🔴 待图鉴;V4.5 🟡 沿用。`· strategy/14 / 03(level_plan)/ 02(SHOP_REFRESH_TABLE)`。

## D-22 (2026-08-09)【验证·身份】立绘库 character_cw_portrait 实测可用(6/6 有角色槽命中)—— 推翻脸库旧结论 + 验证 D-20 接入对

- **决策**:①-b 实测**初步通过**。离线脚本(`.debug/temp/currency_war/test_portrait_recog.py`)对 r1-8 备战截图(`cw_equip_detect_1786279596669.png`)跑 SIFT `identify_character` 对 `character_cw_portrait`:
  - **VLM ground truth**:前排4 + 后排1 + 备战栏1 = 6 个有角色槽;其余空。
  - **SIFT 立绘库**:6/6 有角色槽**全命中**(藿藿/赛飞儿/砂金/不死途/丹恒·饮月/不死途,inliers 29-48 高分);空槽全 None(best=0-1,不误识别)。
  - **命中率 100%**(本样本)。
- **为什么**:验证 D-20 接入角色识别是否可靠(立绘库从未实测,脸库旧结论说只 4 角色强命中)。实测:立绘库(域匹配)对有角色槽全命中 + 空槽不误 → **可靠**,推翻脸库旧结论。**D-20 接入角色识别是对的**(非假信号)。
- **备选/待**:① 据脸库旧结论判立绘库不可靠 —— 实测推翻,错;② 角色名准确性 —— SIFT 高 inliers + 重复槽(前排4=备战1 都不死途)一致 + 砂金金发/丹恒饮月黑发合理,但**待详情面板 OCR(#115)确认 ground truth**;③ 样本量小(1 截图 6 角色),**待共脸变体样本**(姬子/姬子·启行,SIFT 能否靠服装区分 —— 库已分开采)。
- **状态**:①-b 初步实测通过(立绘库可用)。待:更多样本(共脸变体)+ 角色名 ground truth(#115)。`· currency_war_char_id/cw_identity_obs docstring(实测可用)/ 进度树①-b / test_portrait_recog.py`。

## D-23 (2026-08-09)【机制·装备】①-a 实测增量补充 D-18 后半:装备槽在详情面板(owned 不在备战装备区)

- **决策**(①-a live 实测,r1-8 备战,点藿藿详情面板):
  1. **装备区(区域-道具装备 x1252-1918)= 装饰球体 + 扳手**(VLM 实测:顶扳手 y90-120 + 装饰球体 y130-710),**无 owned 装备 icon / 装备槽**。**印证 D-18 后半(L165 已自修正:装备区球体)**;prep doc 旧「装备槽右列 x1805-1885」是 D-18 crop VLM 误判(L165 已修,①-a 再确认,非「推翻 D-18」—— D-18 前半 drag 机制仍有效)。
  2. **角色装备槽 = 详情面板**(点 deployed 角色 → 右侧面板):3 槽横向,终结技区下 / 装备推荐上(y~700-800);r1-8 藿藿 **3 槽全空(裸装,深色 □)**。**owned 装备不在备战装备区,装备槽在详情面板**(drag 穿戴)。
  3. **owned 装备源待探**:从哪 drag 到槽(点槽弹 owned 列表?装备推荐弹推荐列表 D-18)。装备机制 = drag(D-18)。
- **为什么**:①-a 核心问题(D-18 留:owned 装备在哪)。本轮 live 实测**增量补充 D-18 后半**(L165 已认装备区球体 → ①-a 定位 owned 在详情面板装备槽)。`equip_all`(x1800-1918 亮度检测)建在错认知上(装备区是装饰球体非装备),①-a 完整建档后重写。
- **状态**:①-a 进行中(#128)。已建档装备区结构(装饰球体)+ 装备槽位置(详情面板)。**待**:① 精确装备槽坐标(crop 交叉 —— VLM grounding 与 OCR 装备推荐位置冲突,不可信);② owned 装备源(点槽探);③ 三态样本(空 r1-8 / 填充 需 owned);④ 重建 `_detect_equip_icons` + 重开 drag。`· prep doc 装备区 / equip_all / 进度树①-a`。

## D-24 (2026-08-10)【审查·P0】核心模块锁名存实亡:5 核心模块工作区 carryover(D-6~D-14)+ shop_supply 引用作废 D-6 —— 待用户 git 回退

- **决策**(review `a248e08a8c3973cc3` P0):① 未过(核心策略模块该锁),但 `git status` 显示 **5 核心模块工作区被改**(cw_strategy/cw_decisions/cw_comps/cw_strategy_manager/cw_investments,D-6~D-14 自主推进期 carryover)。具体:
  - **maybe_pivot(cw_comps:644-652,D-9)**:commit 后信号1 不翻转(`_committed and not _losing → 跳过`)。D-9 有记录 + 程序注记(振荡 bug 直接观测非 tracking 依赖;下游集中度待①重验)—— 类 D-14 可①-例外声明。
  - **shop_supply(cw_comps:545)**:`(0.15+0.85*)` 注释「D-6 实验:加严」—— **引用已作废 D-6**(进度树 D-6 作废待重验)改核心模块 = 自相矛盾,该①过后回退/重做。
- **为什么**:review P0「声明锁定 + 工作区未授权改动」是最危险状态(下次会话读进度树以为锁着,实则行为已变)。治本 = ① 过后回退核心模块基线重做(carryover 都标作废待重验)。
- **状态**:**待用户决定 git 回退**(回退 5 核心模块到 HEAD 基线,① 过后重做)—— 不擅自 git(CLAUDE.md 版本控制约束 + 不可逆)。当前:进度树/decisions 标注 carryover 作废待重验。`· cw_comps(maybe_pivot:644 / shop_supply:545) / 进度树防偏离门`。

## D-25 (2026-08-10)【机制·装备】research **假设**(待填充态 live 核,review P1 降级):装备库面板=拖拽穿戴/合成;r1-8 裸装=空态。⚠️ r1-6 反例未解(owned 源位置待全幅核)

- **决策**(research 攻略 web):货币战争装备区 = **独立面板**(对局「角色/装备/消耗品」标签,点「装备」进),owned 装备存放处;**拖拽**装备到角色头像穿戴 + 两散件拖拽合成。
- **①-a D-23 认知修正(降级为假设,review P1)**:D-23 说「装备区装饰球体无 owned」—— r1-8 裸装(没 owned)→ 球体可能是空态。**但 research 攻略只证「拖拽穿戴」机制(装备库面板),不等于备战画面 x1252-1918 的 UI 布局**(攻略机制 ≠ UI 布局)。**⚠️ r1-6 反例(D-18 L167):r1-6 补给后有 owned,装备区 x1800-1918 仍球体** —— 说明 owned 不在右半 x1800-1918(可能在左半 x1252-1800,未查)。故「装备区=owned源 / equip_all 方向对」**仅假设**,待填充态全幅(x1252-1918 左右半)live 核。
- **为什么**:①-a owned 源卡点。research 攻略说装备库面板(拖拽),**但 r1-6(有 owned)右半球体未解** → owned 源位置(右半?左半?别处?)**待 live 全幅核**,勿据空态+攻略翻盘(review P1 cherry-picking 纠正)。
- **状态**:①-a 认知修正(装备区=owned 源,r1-8 空态)。**下轮**:跑到补给节点(有 owned)看装备区填充态(icon 长啥样)+ 区分空/填充 + 重建 `_detect_equip_icons`(形状/边框,非亮度)→ 重开 drag。来源:[17173 萌新攻略](http://news.17173.com/content/11072025/175303925.shtml)+[官方玩法说明](https://sr.mihoyo.com/news/160700)。`· prep doc 装备区 / D-18(装备机制 drag)/ D-23(装备区空态修正)`。

## D-26 (2026-08-10)【机制·装备】r1-6 全幅 VLM 印证:装备区(x1252-1918)=装饰(球体+角色立绘)非 owned;**推测** owned 源=装备库面板(独立,未 live 观测);D-25 假设错,D-18 对

- **决策**(①-a r1-6 截图全幅 VLM,解 review P1 r1-6 反例):r1-6(补给后)装备区(x1252-1918)**全幅** —— 右半(x1800-1918)装饰球体 + 左半(x1252-1800)**角色立绘**(非 owned),**无 owned 装备 icon**。
- **含义**:① 备战「区域-道具装备」(x1252-1918)= **装饰**(球体+角色立绘),非 owned 源。② owned 源 = **装备库面板**(独立面板,research「角色/装备/消耗品」标签),备战无入口(OCR 无「装备」标签)。③ **D-25 假设(装备区=owned源)错** —— 装备区是装饰;owned 源=装备库面板独立。④ equip_all(x1800-1918 检测装备区)**错**(检测装饰)—— **D-18 结论对**(装备区球体,owned 不在 x1800-1918)。
- **为什么**:review P1(r1-6 反例未解)。r1-6 全幅 VLM 印证装备区装饰(非 owned),解 r1-6 反例(有 owned 仍球体 = 装备区本就装饰,非「空态」)。owned 源=装备库面板(独立,入口待找)。
- **状态**:①-a owned 源 = 装备库面板(独立,备战无入口,待找 —— 可能补给节点选装备时开)。**下轮**:bot 到补给节点看装备库面板 + owned icon。`· prep doc 装备区(装饰,非 owned)/ D-18(结论对)/ D-25(假设错)/ review P1`。

## D-27 (2026-08-10)【纠正·装备·重大】cw_equip SIFT 识别到 owned icon —— 推翻 D-18/D-23/D-25/D-26 VLM 球体误判;owned 源=装备区(x1800-1918 右列),①-a 鸡生蛋解除

- **决策**(用户质疑 + cw_equip SIFT 验证,test_equip_recog.py):①-a 全程 VLM 把装备区 owned icon 误判「装饰球体」(D-18/D-23/D-25/D-26)。**cw_equip SIFT 识别到 owned icon**:
  - r1-6:拆装扳手(工具)@(1836,172)。
  - r1-8:生命之花+轮滑鞋(简易)+拆装扳手(工具)@(1836-1849,172-315)。
  - inliers 11-32(高,可靠)。
- **推翻**:owned icon **在装备区右列(x~1800-1918)**,非「装饰球体」(VLM 误判)。owned 源 = **装备区**(备战可见),非「装备库面板独立」(D-26 推测错)。**①-a 鸡生蛋解除**(owned 源=装备区,bot 备战可见,不需到补给)。
- **equip_all 重建方向**:x1800-1918 亮度检测**区域对**(owned 在那),但**亮度不够**(owned icon vs 空槽球体都亮)→ 改 **cw_equip SIFT 模板匹配**(154 件,inliers≥10),非亮度。
- **为什么**:用户质疑「cw_equip 模板库建了为何不用」→ 核实 cw_equip(154 icon)建了(harvest_equip_codex),识别函数没实现(cw_equipment.py 只数据);用 cw_equip SIFT 验证 → 命中 owned → 推翻 VLM 球体。
- **教训**:①-a 全程 VLM(球体)误判,有 cw_equip 模板库不用 —— **识别优先用已有模板库 SIFT,不凭 VLM**(VLM 对小 icon 不可信,CLAUDE.md)。鸡生蛋 memory 作废(owned 源非补给)。
- **状态**:①-a 重新激活(owned=装备区,cw_equip SIFT)。**下一步**:建 read_equips(用 cw_equip SIFT,像 read_deployed_chars)+ 重建 equip_all(SIFT 非亮度)+ 测试。`· test_equip_recog.py / cw_equipment.py / equip_all(重建) / D-18·D-23·D-25·D-26(球体误判推翻)`。

## D-28 (2026-08-10)【确认·装备】D-27 tiebreaker:crop 单 owned icon 放大 4x → VLM 复核确认真装备 icon(扳手/轮滑鞋/饰品);审查 P0-2「单点反转假阳性」担忧推翻,D-27 方向成立

- **决策**(审查 P0-2 质疑 D-27 证据不足 → crop tiebreaker):D-27 只验 r1-6/r1-8 两张、inliers 偏低(11-32)就推翻 D-18~D-26 四条 VLM 观测,审查合理质疑「可能从 VLM 单点误判摆到 SIFT 单点误判」。做决定性 tiebreaker:把 SIFT 命中点 ±55px crop 放大 4x(crop_equip_icons.py)→ analyze_image GLM-4.5V ground truth 复核。
- **结果**(VLM 放大后判定):3 个命中点全是**可识别装备 icon** ——
  - 拆装扳手@(1836,172):银灰金属扳手,C 形开口,六边形框,右下「1」(数量)。
  - 轮滑鞋@(1849,239):粉白紫具象轮滑鞋,4 轮。
  - 生命之花@(1849,315):圆形饰品,银边红底绿区白几何花纹。
  - 右列整列:r1-8 三装备 icon + 红渐变背景;r1-6 扳手 + 背景装饰竖条(非球体)。
- **确认**:D-27 SIFT 命中**经 VLM 放大 ground truth 复核为真装备 icon**,非假阳性。**审查 P0-2「D-27 可能单点反转假阳性」担忧推翻**。D-18~D-26 VLM「球体」误判根因 = **全图送 VLM**(小 owned icon ~60px 在 1920×1080 全图丢细节 → 误判球体),违反 CLAUDE.md「视觉大模型·小目标先裁切+放大(破 32×32 patch 天花板),全图送小 icon 必丢细节」。放大后 VLM 自己看清是装备。
- **修正 D-27 教训**:D-27 教训「识别优先用已有模板库 SIFT,不凭 VLM」**过窄**。真正教训 = **跨多样本 + ground truth 交叉验证**(gameplay-automation 证据纪律);小目标必**裁切放大**(CLAUDE.md),全图送 VLM 必丢细节。SIFT 同样会假阳性(审查 P0-3 指出 equip_rect 含左半立绘区 → 立绘图案可能假匹配),VLM 也会误判(球体)—— **单一方法都不可信,交叉验证治本**。
- **遗留**(审查 P0-3 read_equips 代码缺陷,待修):① centroid 用 RANSAC `mask` 过滤的 inlier,非全部 `good`(含 outlier);② equip_rect 收紧到右列(x1800-1918,排除左半 x1252-1800 立绘区);③ min_inliers 提到 ≥15 + 簇聚合(同坐标 ±20px 多命中归一)。①-a 仍需建 screen_info area + 三态 fixture(审查 P1-1,tiebreaker 是认知非建档)。
- **状态**:D-27 方向**确认成立**(SIFT 对,VLM 球体错)。下一步:① read_equips 三处修;② ①-a 建 screen_info area(owned icon pc_rect 右列)+ 三态;③ 多样本(≥5 跨局面 + 空槽假阳性率,待游戏回货币战争)。`· D-27(确认)/ D-18·D-23·D-25·D-26(球体误判,根因全图送 VLM)`。

## D-29 (2026-08-10)【数据·核实】用户三问(装备/投资策略/投资环境效果)核实 —— 都已采集(用户认知过时);equip_all 重建可用 effect 决策

- **决策**(用户曾问「没采集装备效果?」「投资环境/策略效果有收集吗?」→ 核实三处数据完整性,证据纪律不凭用户认知):三处**都已采集**(V4.4 全量),用户认知过时(D-27 前可能未全)。
  - **装备效果**:代码 `cw_equipment.py` EQUIPMENTS(153 件)`Equipment.effect` 字段**主体填了** —— 进阶/特权/星徽/白昼/命运/骇客/特殊全有效果原文(如「反重力皮靴:速度增幅+15%可叠加」);简易(7)/工具 effect 空(**合理** —— 基础属性无特殊效果)。**equip_all 重建(①-a)可用 effect 决策选装备**(哪个装备给哪个角色)。
  - **投资策略效果**:data doc `investment_strategies.md` 全量(315 条:棱彩114+金125+银76,米游社原文 V4.4);代码 `INVESTMENT_STRATEGIES` 只收 T0(event_whitelist 决策用,全量随事件/补给决策接线补全)。
  - **投资环境效果**:代码 `cw_investments.py` `INVESTMENT_ENVS` 全量(7 类有名环境,`InvestmentEnv.effect` 填,游戏内图鉴核对 83 总/68 解锁);**代码单一源**(原 investment_envs.md doc 已删,符 CLAUDE.md「代码全量后 doc 冗余删」)。
- **为什么核实**:用户提数据缺口 → 不凭「用户说没」接受,核实代码/doc(证据纪律)。结论:三处采集齐,V4.4 全量。
- **遗留**:投资策略数据量不一致(米游社 channel/map/209/212 = 216 vs data doc investment_strategies.md = 315)—— 来源/channel 差异,低优待核(非本轮阻塞)。
- **状态**:数据完整性确认(装备/投资策略/投资环境效果都采集)。equip_all 重建(①-a)用 Equipment.effect 决策选装备 + read_equips 识别 owned icon + drag 穿戴。`· 用户三问(过时)/ equipment.md(data doc)/ investment_strategies.md(315)/ cw_investments INVESTMENT_ENVS(代码单一源)`。

## D-30 (2026-08-10)【纠正·误识别·重大】游戏一直在货币战争 —— 「位面过渡」画面没建档被误识别模拟宇宙,致多轮「卡游戏」错判

- **决策(用户指出「建档问题+id_mark 区分」+ 点空白推进验证)**:纠正多轮「游戏在模拟宇宙,①-a 卡游戏」错判 —— **游戏一直在货币战争对局中**。「位面过渡」画面(货币战争,3 位面进度 1 金 2/3 灰 + 点击空白继续)**没 screen_info entry + id_mark** → analyze 模糊撞「模拟宇宙」(都有「位面」,is_precise=False)→ 误判「偏离模拟宇宙」停了多轮。
- **纠正证据**:点空白处推进 → analyze「货币战争-投资环境」is_precise=**true**(货币战争局内节点)。位面过渡是货币战争前序。
- **处理**:建「货币战争-位面过渡」screen(currency_war_plane_transition)+「提示-点击空白继续」area(基础)。**id_mark 区分模拟宇宙待多样本**(需模拟宇宙位面选择截图对比独有锚)→ gap。
- **方法论(跨玩法偏离/误识别,用户 2026-08-10 提炼)**:① analyze 命中非目标玩法 → **先怀疑误识别**(点空白推进验证/核实特征),别急着判「偏离/卡游戏」停;② **误识别/偏离都不停** —— 导航回目标或点空白推进;③ **没建档画面(误识别根因)→ 按 screen-onboarding 建 + id_mark 区分别玩法**。已写 skill_feedback.md(screen-onboarding 补「跨玩法偏离」分支)+ 两个 cron prompt 加这条。
- **教训**:多轮把货币战争位面过渡误判模拟宇宙 → 「卡游戏」错判浪费多轮。根因 = **没核实**(点空白推进一秒就证伪,没做)+ 画面没建档。符重置四教训「凭猜不核实」(凭 analyze 模糊结果猜「模拟宇宙」)。`· 模拟宇宙误识别(纠正)/ 位面过渡建档(基础 id_mark 待补)/ skill_feedback(跨玩法偏离分支)`。

## D-31 (2026-08-10)【证据·装备·假阳性】read_equips 1-1 假阳性:空槽 UI(蓝环白十字)误识别幸运星(inliers=15)→ 装备区需画面模型(owned icon 槽位 vs 空槽 UI)

- **决策(1-1 备战 read_equips + crop VLM tiebreaker)**:read_equips 1-1 命中 2:拆装扳手@(1840,172) inliers=13(VLM 确认银灰扳手 = **真装备** ✓)+ 幸运星@(1854,244) inliers=15(VLM 确认 = **蓝环白十字功能性 UI**,非装备!**假阳性** ✗)。
- **根因**:装备区右列槽位:有装备 = owned icon(六边形深灰框 + 装备图案);**空槽 = 蓝环白十字「添加」UI**(点选装备穿)。read_equips SIFT 把空槽 UI 误匹配幸运星模板(inliers=15 反比真装备 13 高)。**审查 R2 P0-2「SIFT 假阳性」担忧成真**(D-28 tiebreaker 确认 r1-8 真,但 1-1 暴露假阳性)。
- **处理**:①-a **先建装备区画面模型**(screen-onboarding:owned icon 槽位 vs 空槽 UI 布局,六边形框 vs 蓝环白十字区分)→ 再 read_equips(CV 框型过滤空槽 UI / owned 槽位定位)+ equip_all。符记忆「检测op前先建档」+ 审查「画面模型」。
- **教训**:read_equips 建在未建档装备区 → 假阳性。证据纪律(审查 R2/R3)坚持 tiebreaker 才发现(1-1 幸运星 inliers=15 偏高可疑,crop VLM 证伪)。**read_equips min_inliers=10 + 簇聚合不够降假阳性**(假 inliers 15 > 真 13),需画面模型(框型/槽位)非纯阈值。
- **状态**:read_equips 假阳性确认(空槽 UI)。①-a 转「先画面模型」。下一步:装备区 owned/空槽 画面建档(1-1 + r1-8 对比槽位布局)。`· read_equips 假阳性(蓝环白十字 UI)/ 装备区画面模型(待建)/ 审查 R2 P0-2(成真)`。
- **蓝色过滤验证(2026-08-10,排除简单颜色法)**:命中点 HSV 蓝色比例 —— 1-1 假阳性幸运星 0.122 **低于** r1-8 真 owned(拆装扳手 0.146 / 生命之花 0.197 / 轮滑鞋 0.300)。**简单蓝色阈值区分不了**(假阳性蓝比真 owned 还低)→ 需框型(owned 六边形深灰框 vs 空槽蓝环白十字)或槽位画面模型,非颜色阈值。

## D-32 (2026-08-10)【装备·drag 证伪】①-a equip_all drag 验证:D-18 落点 y350 过时,drag 扳手 → 前排 avatar 没穿装备(扳手回);需重验 drag 机制

- **决策(①-a drag 验证,游戏 click ground truth)**:drag 扳手@(1840,172) → 前排-1 avatar (743,350)(D-18 FRONT_SLOTS y350,caa07f32「WORKS」)**失败**。read_equips drag 后扳手还在@(1840,172)(没穿走,inliers=13 同前),VLM 前排-1「红色 icon」= 误判(角色自带,非装备)。
- **证伪**:D-18 drag 落点 y350(avatar drop zone)**不 work** —— drag owned → 前排 avatar 没穿装备(扳手回装备区)。印证 e9747690 解绑根因「drag 致前台区域无角色 → stall」(装备 drag 机制有问题)。
- **待重验**:装备 drag 到哪穿?角色装备栏坐标(非前排 avatar y350?角色身上装备槽?) + drag 操作。需游戏 click ground truth(drag 装备 → 不同落点试,看 icon 减)+ VLM 看角色装备栏。
- **教训**:D-18 caa07f32「y350 WORKS」可能那时偶然/版本变/我 drag 不对。①-a equip_all 重建前必须搞清 drag 机制(D-18 落点已证伪,insights 记)。read_equips(owned 识别 D-28/D-31)+ VLM 验证(过滤假阳性)ready,但 drag 机制(穿装备)未通。
- **状态**:①-a drag 机制待重验(D-18 落点证伪)。下步:游戏 drag 装备试不同落点(角色装备栏位置)+ click ground truth。`· D-18(落点证伪)/ e9747690(解绑根因 drag stall 印证)/ read_equips(owned 识别 ready)/ D-31(假阳性 VLM 过滤)`。

## D-33 (2026-08-10)【装备·路径·重大】装备推荐 list-select 路径(点角色→详情→装备推荐→列表弹)前 3 步通 —— 免 drag 路径可行(D-17 既定,被 D-32 跳过,R6 P1-1 补测)

- **决策(审查 R6 P1-1 + 游戏测)**:D-17 已识别「装备推荐」list-select 路径(点已部署角色 → 详情面板 → 装备推荐按钮 → 弹推荐/次选装备列表 → 点选穿戴),D-32 跳过直接测 drag(失败)。本轮补测:**前 3 步通** —— 点前排-1 角色 (743,398) → 详情面板开(三月七,属性/战技/装备推荐按钮 @(1465,802))→ 点装备推荐 → **推荐列表弹**(推荐装备 4 + 次选装备 4)。
- **意义**:装备推荐 list-select 路径**可行 + 免 drag**(drag 路径 D-32 失败 + e9747690 回归风险)。equip_all 重建该优先**装备推荐 list-select**(点角色 → 详情 → 装备推荐 → 列表 → 点推荐装备穿戴),非 drag。
- **待验(穿戴 + 推荐性质)**:① 点推荐装备图标 = 穿戴?(未测,需坐标 + click ground truth)② 推荐装备性质:owned 可穿 vs 理想装备展示?1-1 owned 只拆装扳手(工具),推荐列表 8 图标 → 可能**理想装备**(图鉴推荐,非 owned,点不能穿)。需 bot 有 owned 穿戴装备(补给/奖励)确认推荐穿。
- **坐标**:推荐装备图标 VLM grounding 不准(给 [x,y] 非 bbox + 偏中央,详情面板右半;CLAUDE.md VLM grounding 幻觉)。需 screen_info 建装备推荐列表 area or CV 检测(od-dev-ui-region-detect)。
- **状态**:装备推荐 list-select 路径前 3 步通(免 drag 可行)。下一步:① bot 获 owned 穿戴装备(推进对局到补给/奖励)② 建装备推荐列表 screen_info area ③ 点推荐装备验穿戴 ④ equip_all 重建(list-select 优先,drag 备选)。`· D-17(装备推荐路径既定)/ D-32(drag 失败,工具)/ R6 P1-1(补测路径)/ e9747690(drag 回归,免 drag 优)`。

## D-34 (2026-08-10)【装备·tiebreaker+纠正】1-4 减益星徽真 owned 穿戴类(tiebreaker 确认)+ D-33 纠正(装备推荐=提示非穿戴,D-18 live 知识回归)+ drag 穿戴类待验(D-23 装备槽)

- **tiebreaker(1-4 bot stop 备战 crop VLM)**:减益星徽@(1847,322) = VLM「方形蓝星角框 + 圆粉底白螺旋图案」= **真 owned 穿戴类装备(星徽)**✓;治疗星徽@(1854,248) = 「蓝环白十字空槽 UI」= **假阳性**(D-31 同);拆装扳手@(1840,172) = 工具(非穿戴)。
- **D-33 纠正(审查 R7 + D-18 live,知识回归)**:装备推荐 list-select「免 drag 可行」**过早**。D-18(2026-08-09)已 live 实测:点装备推荐 → 弹列表 → 点列表装备 → **弹装备信息详情(stats/适配/合成),不穿戴无穿戴按钮**。gameplay.md:54「推荐装备=提示(hint)」。VLM 核实推荐图标无 owned 标记(图鉴式)。**推荐列表 = 提示/图鉴浏览,非穿戴路径**。真穿戴 = drag 穿戴类装备。
- **drag 穿戴类待验(审查 R7 + D-23)**:D-32 drag 失败因拖工具(非穿戴类)。真未测:drag **穿戴类**(减益星徽,1-4 有)→ 角色详情面板装备槽(D-23 坐标,非前排 avatar y350)→ 验 icon 减=穿。caa07f32「WORKS」未证真穿(可能亮度检测噪声/球体位移,D-18 诊断),drag 对穿戴类仍开放假设。
- **教训**:D-33 没引 D-18 live 结论(装备推荐=信息浏览),重发现浪费一轮。**行动前重读 D-17/D-18/D-23**(装备机制)防知识回归。
- **状态**:减益星徽(穿戴类)到 1-4(bot stop)。下一步:重读 D-23(装备槽坐标)+ drag 减益星徽 → 装备槽验穿。⚠️ 审查 R7:onboarding-first(装备区 owned/空槽 + 装备槽 + 推荐弹窗画面模型)。`· D-33(纠正,推荐=提示)/ D-18(live 结论回归)/ D-23(装备槽坐标待读)/ 减益星徽(穿戴类 owned,1-4)`。

## D-35 (2026-08-10)【装备·drag 穿戴类成功·重大】轮滑鞋(简易穿戴)drag → 详情面板装备槽 = 穿成功(read_equips icon 减)!D-32 工具失败 + D-34 穿戴类方向对

- **决策(①-a drag 验,1-6 备战飞霄详情面板 + 装备区轮滑鞋)**:drag 轮滑鞋@(1850,242) → 装备槽行中心 (1650,755)(区域-装备槽 [1400,712,1900,798],onboarding-first 建)**成功** —— read_equips drag 后命中 **0**(轮滑鞋没了 = 穿了!)。
- **意义**:drag **穿戴类装备**(轮滑鞋简易)→ 角色详情面板装备槽 = **穿成功**(icon 减)。D-32 drag 拆装扳手(工具)失败(工具拆装备非穿)+ D-34 穿戴类方向对 → **drag 穿戴类 work,工具类不 work**。D-18 caa07f32「WORKS」可能是真穿(穿戴类,非工具)。
- **①-a drag 机制确认**:① drag owned **穿戴类**(排除工具:拆装扳手/冶金炉/随便骰子等)→ 详情面板装备槽(区域-装备槽 [1400,712,1900,798])② icon 减=穿成功 ③ 工具类单独处理(拆装扳手拆装备,非 drag 穿)。
- **待验**:① read_equips 0 可能详情面板遮装备区 —— VLM 验装备槽有轮滑鞋 icon 确认穿 ② 多样本(不同穿戴装备 drag)③ equip_all 重建(read_equips 候选 + VLM 过滤假阳性空槽 UI + 过滤工具类 + drag 穿戴类 → 装备槽)。
- **状态**:**drag 穿戴类成功**(①-a 重大突破)。①-a 框架:read_equips(owned D-28/D-31)→ VLM 过滤(假阳性空槽 UI)→ 过滤工具类 → drag 穿戴类 → 详情面板装备槽(区域-装备槽)。`· D-32(工具失败)/ D-34(穿戴类方向)/ D-18 caa07f32(WORKS 真穿穿戴类)/ 区域-装备槽(onboarding-first 建)`。

## D-36 (2026-08-10)【装备·drag 穿戴类成功·真证】关详情 + drag 轮滑鞋 → 前排 avatar = 穿成功(read_equips 关详情 3 轮滑鞋减)!纠正 D-35(详情遮装备区 read_equips 0 假象)

- **决策(①-a drag 验纠正 D-35,关详情路径)**:D-35 误判(read_equips 0 详情遮装备区假象 + VLM 诱导问误判)。本轮纠正:**关详情面板(装备区 x1800-1918 可见,不被详情遮)+ drag 轮滑鞋(穿戴类,@1849,239 装备区 owned)→ 前排 avatar (743,350)**(D-18 路径)→ read_equips(**关详情,非遮真验**)命中 **3**(减益星徽+拆装扳手+治疗星徽)—— **轮滑鞋没了(穿了!)**。
- **真证**:read_equips drag 前(关详情)4(含轮滑鞋)→ drag 后(关详情)3(轮滑鞋减)。**关详情 read_equips 真验(非 D-35 遮态 0 假象)**。
- **①-a drag 穿戴类机制确认**:① 装备区 owned 可见(**不开详情面板**,详情面板 x1700-1920 遮装备区 x1800-1918)② drag **穿戴类**(轮滑鞋等,排除工具拆装扳手)→ 前排 avatar (743,350)(D-18 路径,**非详情装备槽 D-23**)③ read_equips(**关详情,非遮**)icon 减 = 穿成功。
- **教训(D-35 误判)**:① read_equips 详情面板遮装备区(x1800-1918 被详情覆盖)→ 遮态 read_equips 0 假象,**必须关详情验**(证据纪律)② VLM 诱导问(「轮滑鞋穿了?」)致误判,客观问(「装备区几个 icon」)才准 ③ drag 装备源需装备区可见(不被详情遮)。
- **状态**:**drag 穿戴类成功(D-18 前排 avatar 路径,关详情)**。①-a 框架:read_equips(owned,关详情装备区可见)→ VLM 过滤(假阳性空槽 UI)→ 过滤工具类 → drag 穿戴类 → 前排 avatar (743,350)。`· D-35(误判遮假象,纠正)/ D-18(前排 avatar WORKS 真穿穿戴类)/ D-32(工具失败)/ 详情面板遮装备区(布局)`。

## D-37 (2026-08-10)【纠正·装备区面板模型·重大】右侧面板=「选中驱动」常驻信息面板(非开/关弹窗)+ D-35「详情遮装备区」纠错 + read_equips 假阴性(和平手枪漏检,第三重不可靠)

- **决策(装备区面板模型,实证 + 代码 read_deployed_id_op/equip_probe/battle_loop)**:右侧面板(区域-道具装备 x1252-1918)**不是开/关弹窗,是选中驱动的常驻信息面板** —— 总显示当前选中实体:点装备 icon → 装备详情(名/类型,详情-装备名 x1450-1620);再点/展开 → 可合成列表 overlay;点已部署角色 → 角色详情(名/属性/天赋/详情+出售)。
- **进出交互(用户问「怎么进来和关闭」)**:进来 = 点装备 icon(装备详情)/ 点角色(角色详情);关闭 = ① 可合成列表 overlay → **ESC**(条件 ESC,代码 battle_loop:263 / exit:66 / start:83,实测验证关 overlay);② 角色详情 → **点空白(备战席/商店下方,用户提示;代码 PANEL_CLOSE=700,400 空前台区)**;⚠️ 装备详情 base 勿 ESC(bug#2 → 中断挑战)。`收起`=商店折叠;`出售`=角色详情卖装备按钮(非装备弹窗)。
- **D-35 纠错**:「详情面板 x1700-1920 遮装备区 x1800-1918 → read_equips 0」**错**。实测 read_equips 装备详情面板**开**时仍 5 命中(拆装扳手/光能电池/生命之花/治疗星徽/减益星徽,x1839-1853)。D-35 所述「遮装备区」面板是**角色详情面板**(更宽,点角色触发),非装备详情面板(窄 x1450-1620,不遮 icon)。**read_equips 不受装备详情面板影响**。
- **read_equips 假阴性(NEW,第三重不可靠)**:和平手枪@(1854,248)(点击确认真 owned + 详情显示)read_equips **没命中**(SIFT 漏,< min_inliers 10)。叠加 R11(空槽假阳性 + 和平手枪→治疗星徽 名错),read_equips **三重不可靠**:漏真 owned + 空槽误匹配 + 名错。
- **为什么(重要)**:equip_all 地基 = read_equips。三重不可靠 → drag 验证(D-36「名减判穿」)连锁失效(R11 P0):漏 owned(没装)+ 空槽假阳(drag 空槽)+ 名错(名减判错)。**装备区需画面模型(槽位 owned/empty CV,非 SIFT 名)做地基**,read_equips 退位或仅作 hint。
- **备选**:① 画面模型 = 装备 icon 列槽位(动态 CV 定位)+ slot_occupied CV(D-5 灰度 std)判 owned/empty → drag owned 槽 → 验槽位变 empty(位置 CV,非名);② read_equips 保留作 hint(定位候选),CV 验 owned/empty 过滤。
- **状态**:**装备区面板模型建(选中驱动 + 进出交互清楚)+ D-35 纠错 + read_equips 三重不可靠实证**。①-a 下步:建装备区槽位画面模型(screen_info area + owned/empty CV + 三态 fixture),equip_all 重建在地基上。`· D-35(纠错:装备详情不遮 icon,角色详情才遮)/ D-36(名减判穿,read_equips 名错地基不稳)/ R11(假阳性+名错+drag 验连锁失效 P0)`。

## D-38 (2026-08-10)【纠正·用户权威】装备列「加号」= 星徽 icon(非空槽);无空槽 → read_equips「空槽假阳性」framing 作废(D-31/D-37 纠正)

- **决策(用户权威,两次确认)**:装备 owned icon 列**无空槽**。我(D-31)+ R11 误判的「蓝环白十字空槽 UI」**实为星徽(星徽)icon**(星徽图标 = 蓝星边框 + 白十字/+ 图案,视觉似空槽 +,但真 owned 装备)。用户原话:「加号是星徽,没有加号空槽」。
- **纠正 D-31/D-37**:「read_equips 空槽假阳性」**作废** —— 那些位置是真星徽 owned,非空槽;read_equips 匹配星徽名(治疗星徽/幸运星)到那些位置**可能本就正确**。
- **read_equips 实际问题(收窄)**:① **假阴性**(漏真 owned,如和平手枪 SIFT 漏,@1854,248 点击实锤);② **偶发名错**(和平手枪→治疗星徽 类)。**无「空槽假阳性」**(无空槽)。
- **equip_all 含义(简化)**:① **不需假阳性过滤**(无空槽,read_equips 命中皆真 owned);② **工具类识别仍需可靠**(drag 工具如拆装扳手会拆角色装备 D-32,有副作用,不能盲 drag 测试);③ 穿戴验证用位置(icon 消失)非名。
- **教训(VLM 误判游戏知识)**:VLM(我 + R11)把星徽 icon 误判空槽 —— VLM 不懂游戏,白十字/+ 图案视觉歧义。**游戏知识(「这是什么」)以用户/图鉴/click 验为准,非 VLM 推断**;VLM 仅客观描述(图案/颜色/位置)可用。
- **状态**:**装备列无空槽,加号=星徽,read_equips 无空槽假阳性**。①-a 转向:detect 所有 owned icon 位置(皆装备)+ **可靠识别工具类**(免盲 drag 拆装)+ drag 穿戴类 + 位置验。slot_occupied CV(owned/empty)**作废**(无 empty)。`· D-31/D-37(空槽假阳性 framing 作废)/ R11(空槽分析同样误判)`。

## D-39 (2026-08-10)【证据·read_equips 可靠性验证·重大去险】read_equips 名准确(4/4 click 验)+ 无假阳性;漏检由 min_inliers 10→7 修复 → 阈值 7 可靠,equip_all 地基稳(非 R11「建在沙上」)

- **验证方法**:click 每个 read_equips 命中 → OCR 详情名 vs SIFT 名(1-6 备战)。
- **结果(4/4 click 实锤 SIFT 名全对)**:y169 拆装扳手[工具]✓(详情 拆装扳手/消耗品)/ y252 和平手枪[简易]✓ / y336 折叠小刀[简易]✓ / y555 治疗星徽[星徽]✓(详情 治疗/流派星徽)。(y407 光能电池/y464 生命之花/y628 减益星徽 未 click 但 SIFT 一致。)
- **结论**:read_equips **名准确**(验过全对)+ **无假阳性**(无空槽 D-38)+ **漏检可修**(min_inliers=10 漏 和平手枪/折叠小刀 → **阈值 7 全命中**,5/3 同 7 无杂散 → 7 稳)。**旧「三重不可靠」overblown**(基于误判 D-31 + 阈值 10 过严漏检)。
- **①-a 含义(重大简化/去险)**:read_equips **阈值 7 可靠**(检出全部 owned + 名/类准 + 无假阳)→ equip_all 地基**稳**。equip_all:read_equips(thr7)→ 过滤工具(EQUIPMENTS.category,拆装扳手✓ 验)→ drag 穿戴类 → 验证(名既准,名减或位置 CV 均可)。R11 P0「连锁失效」风险降(名准)。
- **待办**:① read_equips min_inliers 默认 10→7(`cw_equipment.py`,D-28 设的 10 过严)+ 跨局面验证阈值 7 无假阳;② equip_all 用 thr7 read_equips 重建 + 位置验;③ D-36 多样本降级(R12 偏差3)。
- **状态**:**read_equips 阈值 7 可靠(名准+无假阳+漏检修),equip_all 地基稳,①-a 大幅去险**。`· D-38(+=星徽 无空槽)/ D-31·R11(三重不可靠 overblown)/ D-28(min_inliers=10 过严 → 7)`。

## D-40 (2026-08-10)【纠正·用户权威·多列网格】装备 owned = 多列网格(col1 x1800-1918 + col2 x1660-1800 + ...);冶金炉@x1784 真实 col2 → read_equips equip_rect 扩 x1620-1918 覆盖多列(thr7 实测 8/8)

- **决策(用户权威,第三次纠正单列假设)**:装备 owned **不止一列**(用户:「应该有2列」「默认5列从右往左」)。col1(x1800-1918)=7 icon;**col2(x1660-1800)=冶金炉@x1784**[工具/消耗品](click 实锤);col3+(x1530-1660)空。**共 8 owned,2 列**。
- **我之前的错**:① read_equips equip_rect=(1800,1918) 仅扫 col1 → 漏 col2 冶金炉;② 把 thr10 wide-scan 的冶金炉@x1784 误判「noise」(实真);③ squares 漏消耗品边框(拆装扳手+冶金炉同盲点)。**根因:单列假设 + thr10 漏弱匹配**。
- **修复**:read_equips `equip_rect` 默认 (1800,1918) → **(1620,1918)**(多列,覆盖 col1-3,排除立绘 x1252-1450 + 面板 x1450-1620)。thr7 实测 x1620-1918 扫 = **8/8 全命中两列无杂散**(thr10 wide-scan 噪点是阈值过高漏弱匹配,非区域宽)。
- **网格识别现状**:thr7 + wide equip_rect(x1620-1918)**单次扫即覆盖多列**(非固定 cell per-column)。固定 cell 模型(装备格-cIrJ)是未来硬化(更鲁棒),当前 zone 扫够用。
- **待办**:① col4-5 若溢到面板区(x1450-1620)需关面板扫(equip_all 前置关面板);② 跨局面验证 x1620-1918 无立绘/面板假匹配;③ equip_all 用多列 read_equips 重建 + count 验穿(R13 中-3)。
- **状态**:**装备多列网格确认(col1+col2=8),read_equips equip_rect 扩多列,thr7 单次扫覆盖**。`· D-39(thr7 名准)/ 用户三纠正(+=星徽·多列·8个)/ R13 中-2(多列 doc-code drift 现对齐)`。

## D-41 (2026-08-10)【证据·equip_all LIVE + 合成机制·重大】equip_all 机制验通(column 8→4);合成发现(轮滑鞋+生命之花→步步生花,穿戴触发);count-verify 报3实4(合成消耗2件);read-equipped below-avatar SIFT 读步步生花正确

- **equip_all LIVE 测**(run_operation,daemon 重启 server 加载新代码):read_equips(thr7,x1620-1918)→8 owned→过滤工具→drag 穿戴类→前排 avatar→count 验穿。**column 8→4(4 件移出),equipped 报 3**。机制(drag+count)**通**。
- **合成机制发现(用户确认)**:**轮滑鞋 + 生命之花 → 步步生花**(进阶)。equip_all 给飞霄(已有轮滑鞋)装生命之花 → **自动合成步步生花**(穿戴触发合成)。below-avatar SIFT 读到步步生花(@x735,inliers=7)—— **正确,非误判**(我先前错判 mis-match;VLM+用户实锤)。
- **count-verify 失真根因(R16 P0-2)**:合成消耗 **2 件**(生命之花+轮滑鞋)→ column count −2,但 equip_all `equipped+=1`(报3实4)。且被消耗的轮滑鞋**在角色身上**(非 column 视野)→ count-verify 在「不知角色装备态」下验 → 不可靠。
- **read-equipped**(R15 step1 核实):below-avatar mini icon SIFT **可读**(步步生花正确);char-detail 装备槽 SIFT 0 命中(槽 icon 更小)。→ **avatar-slot ground truth(下方 mini icon)可行**,替 count-verify。
- **治本方向(R15/R16)**:count-verify → **avatar-slot ground truth**(drag 后读目标 avatar 下方 mini icon 确认新装备,非 column count 减)—— 免受合成/列 reflow/漏检干扰;同时让 equip_all 知「装到了谁身上」(P0-2 多槽 + 策略基础)。
- **合成配方采集**:codex(数据银行→装备图鉴)进阶详情「合成公式」= 2 简易(步步生花=生命之花+轮滑鞋 实锤)。全量表待 codex 采(web bwiki 部分且矛盾:以太钻 类别不一致;codex 简易行有以太钻 → equipment.md 标进阶可能有误,待核)。⚠️ **入代码前先拆生成器地雷(R16 P0-1)**。
- **状态**:**equip_all 机制验通 + 合成机制发现(穿戴触发)+ count-verify 失真根因(合成)+ read-equipped below-avatar SIFT 可行**。①-a 下步:① **拆生成器地雷**(P0-1,`cw_equipment_data.py` 拆出 SIFT)② 合成配方 codex 采 → equipment.md → class `recipe` 字段 → regen ③ count-verify 改 avatar-slot ground truth。`· D-40(多列)/ D-39(thr7)/ R15·R16(count-verify→avatar-slot)/ 用户(合成确认)`。

## D-42 (2026-08-10)【重构·P0-1 生成器地雷拆除】cw_equipment 拆数据/SIFT 双文件(cw_equipment_data 生成 + cw_equipment SIFT);gen 写 _data → 覆盖地雷除

- **背景(R16 P0-1)**:`gen_equip_registry` 覆盖 `cw_equipment.py` → 删 L218+ SIFT(read_equips/load_equip_templates)→ ImportError。SIFT 手加在生成产物后,不在 template。R17 复核确认(gen target 仍 cw_equipment.py),本轮修。
- **决策(拆双文件)**:① `cw_equipment_data.py`(生成器产物:Equipment+_eq+EQUIPMENTS+get_equip,dataclass only);② `cw_equipment.py`(手维护 SIFT:load_equip_templates/read_equips,`from .cw_equipment_data import` + `__all__` re-export 给旧 caller);③ `gen_equip_registry.py:119` target 改 `cw_equipment_data.py`(+ docstring)。
- **验证**:ruff 双文件过;import OK(EQUIPMENTS=153 same,cw_equipment/equip_all 均 import 正常);read_equips 仍 4 hits(115501 截图,功能不变)。生成器只写 `_data`,永不碰 `cw_equipment.py` SIFT → **覆盖地雷除**。
- **遗留**:① `cw_equipment_data.py` untracked(待 `git add`,R17 P1);② 以太钻门类错(待 regen 修,R17 P2;现 unblocked 可 regen);③ **recipe 入 Equipment class**(用户指令「效果+合成入 class」,待加 `recipe` 字段 + gen 解析 + regen)。
- **状态**:**P0-1 地雷拆除完成(cw_equipment 拆数据/SIFT,gen 写 _data)**。recipe 入 class 解锁(下一步:加字段+改 gen+regen)。`· R16 P0-1(地雷)/ R17 P0(target 改)/ 用户(效果+合成入 class)`。

## D-43 (2026-08-10)【用户指令完成·recipe 入 Equipment class】Equipment 加 recipe 字段 + gen 解析合成配方段 + regen → 21 进阶配方入代码

- **用户指令**:「效果、合成路径都加入到 py 文件的装备 class 里」。效果原已在(生成);**合成路径(配方)本轮入**。
- **决策**:① `Equipment` 加 `recipe: tuple[str,str] | None = None`(进阶 = 2 简易;非进阶/待核 → None);② `gen_equip_registry` 加 `parse_recipes()`(解析 equipment.md「进阶合成配方」段 → `{进阶:(A,B)}`)+ main 合并 + `_eq` emit recipe;③ regen `cw_equipment_data.py`(P0-1 已拆,regen 安全,不碰 SIFT)。
- **验证**:regen 153 件;**recipes filled 21**(步步生花=`('生命之花','轮滑鞋')`✓ 用户确认;武器大师/掩体生成枪 等);ruff 双文件过;read_equips 4 hits 不变(功能不受影响)。
- **遗留**:① **15 待核配方**(7 漏幸运星 + 8 off-screen/×2)→ recipe=None,待 codex 滚动重采补;② 以太钻门类(equipment.md 标进阶,codex/SIFT 示简易,待移简易段 + regen);③ regen 计数 **153 vs 154 icon**(R17 noted,待核漏哪个);④ `cw_equipment_data.py` untracked(待 git add)。
- **状态**:**recipe 入 Equipment class 完成(21 配方,用户指令达成)**。效果 + 合成均在代码(see code → understand)。`· D-42(P0-1 拆分 → regen 安全)/ D-41(合成机制)/ 用户(效果+合成入 class)`。

## D-44 (2026-08-10)【equip_all 验穿治本·avatar-slot CV-diff】count-verify 替为 avatar-slot CV-diff(drag 前后对比目标 avatar 下方 mini icon 区)—— robust 合成/reflow/read漏检

- **背景(R19治本③/D-41)**:count-verify D-41 实测**报3实4 失真**(合成消耗2件 → column count 扰 + read漏检)。需 avatar-slot ground truth(直接观测 avatar 装备态,非间接推断 column)。
- **决策**:equip_all 验穿改 **avatar-slot CV-diff**:drag 前 crop 目标 avatar 下方 mini icon 区(`BELOW_ICON_Y=479`,D-41 测),drag 后 crop 同区,`np.abs(pre-post).mean() > BELOW_DIFF_THRESHOLD(8.0)` = 穿[新装/合成都变 icon],不变 = drag 落空。
- **robust 3 路**(count-verify 的 3 失效路全治):① **合成**(轮滑鞋+生命之花→步步生花:avatar 下方 icon 滑轮鞋→步步生花,diff 高 ✓);② **列 reflow**(avatar 下方位置固定,不受 column reflow);③ **read漏检**(直接 CV-diff,不依赖 read_equips count)。
- **验证**:ruff 过;import OK(BELOW_ICON_Y=479 THRESH=8.0);read_equips 不变。**dormant**(待 live 测跨局面调阈值)。
- **遗留**:① BELOW_ICON_Y=479 + THRESH=8.0 待 live 跨局面调(单局 1-6 设);② avatar-slot 只验「变了」(穿了),不区分新装 vs 合成(策略层若需区分须 SIFT-identify below-icon)。
- **状态**:**equip_all 验穿改 avatar-slot CV-diff(robust 合成/reflow/漏检,count-verify 失真治本)**。①-a equip_all 鲁棒性提升。`· D-41(count-verify 失真)/ R19治本③(avatar-slot)/ R15·R16(count→avatar-slot 方向)`。

## D-45 (2026-08-10)【证据·已穿装备识别 + recognizer 缺口·路径定】below-avatar SIFT 1件✅ 2-3件失效(icon 缩小);template match partial(简易✅ 进阶 borderline);read_equips=owned 列非已穿;recognizer 无已穿字段(gap);路径 template match + 集成

- **澄清两个识别**(R20):`read_equips` = owned 列(**未穿**装备,thr7 SIFT 4/4 验 D-39)**≠ 角色已穿装备**。①-a 之前的工作是 owned 列,not 已穿。
- **已穿装备识别实测**(below-avatar mini icon):
  - **1 件**:SIFT ✅(步步生花 inliers=8 / 治疗星徽 inliers=5;icon 较大 ~50px)。
  - **2 件**:SIFT ❌(icon 缩小 ~35px,SIFT patch 天花板失效);**template match partial**(折叠小刀 简易 0.78✅ / 步步生花 进阶 0.53 borderline vs 轮滑鞋 0.52)。
  - **3 件**:更差(icon 更小)。
- **根因**:below-avatar mini icon 随装备数缩小;SIFT(关键点)对 <~50px 失效;template match(像素)更好但 complex 进阶 icon borderline(98px 模板缩放到 35px 丢细节)。
- **recognizer 缺口**(R20):`battle_prep_recognizer` 产 front_line/back_line/bench(角色身份),**无已穿装备字段** → 策略层不知「谁穿了什么」→ comp 评分 / equip_fit 无地基。这是 ①-a 的真正缺口。
- **路径**(R20 治本,共识):① **template match 替 SIFT**(方案 A,mini icon 固定尺寸 TM>SIFT);② **mini-templates**(35px native 采,非 98px 缩放)修 complex borderline;③ **recognizer 加 `front_equips` 字段**(below-avatar TM 纯读,给策略层地基);④ equip_all CV-diff 验穿(D-44)**不卡**(只检测「变了」,不需读身份)。
- **状态**:**已穿装备识别 1件✅ 2-3件 partial;recognizer 缺已穿字段;路径 template match + mini-templates + 集成**。①-a 下一核心块(fresh context 做)。`· D-44(CV-diff 验穿)/ D-41(below-avatar SIFT)/ R20(识别缺口 + 路径)/ 用户(1~3件 + 集成问)`。

## D-46 (2026-08-10)【证据·穿戴装备识别 mini-template + recognizer 集成·重大】native 34px mini(实战裁)修进阶 borderline(步步生花 0.565→0.907);read_equipped_below 双模板;recognizer 加 front/back/bench_equips;飞霄跨位置(前排/后排)2 件一致

- **mini-template 验证(D-45② 落地)**:below-avatar mini icon 是游戏渲染 34px(含 UI 边框/底色)。98px 纯 icon 模板缩放到 34px 丢细节 → 进阶 borderline(步步生花前排 0.603 / 后排 0.565,< 0.6 漏检)。**native 34px mini**(从实战 below-avatar 裁,含 UI 装饰):步步生花前排 1.000 / 后排 0.907;折叠小刀 1.000 / 0.970。**mini 完胜,跨位置 >0.9 稳定**。
- **根因**:below-avatar mini icon 有 UI 装饰(边框色=稀有度);98px 纯 icon(codex 裁)无装饰 → 缩放后 mismatch。native mini(实战裁)含装饰 → 高 val。
- **read_equipped_below 双模板(D-45①+②)**:① ``tmpl_minis``(34px native,优先,multi-scale 0.8-1.5 覆盖 1/2/3 件 icon 尺寸变);② ``tmpl_grays``(98px,fallback,简易可用 / mini 库未覆盖装备)。NMS 合并取 val 最高(mini 高自动赢)。
- **mini 库**(``assets/template/cw_equip_mini/``):实战裁 native 34px。首批:步步生花+折叠小刀(飞霄 2 件,``.debug/temp/cw_equip_probe/harvest_minis.py`` 裁)。**渐进建**(实战遇新装备补采)。
- **recognizer 集成**:``BattlePrepRecognizer`` 加 ``front_equips``/``back_equips``/``bench_equips``(``dict[slot_idx, list[name]]``)。``ensure_equip_tm_templates(ctx)`` 加载缓存(幂等,并发安全)。产出「谁穿了什么」给策略层地基。
- **跨位置验证(用户核心需求)**:飞霄从前排-1 drag→后排-1,2 件装备 icon **跟随**(VLM 确认)+ ``read_equipped_below`` 前排/后排都 = ``{步步生花, 折叠小刀}``**一致**(``test_read_equipped_front/back_feixiao_2`` PASS)。
- **遗留**:① mini 库仅 2 件(飞霄),其他装备(黑能导轨/治疗星徽等)用 98px fallback,实战遇时补 mini;② 1 件/3 件态 icon 尺寸(50px/28px)``mini_scales``(0.8-1.5)覆盖待 fixture 验;③ 备战席 below 区(y2=979→below cy=991 接近画面底,可能被金币 UI 干扰)待 fixture 验;④ mini 单尺寸(34px)对 1 件态(50px)放大匹配泛化待验。
- **状态**:**穿戴装备识别 mini-template + recognizer 集成 + 跨位置测试就绪**。①-a 重大进展(策略层有「谁穿了什么」地基)。`· D-45(识别缺口+路径)/ 用户(3 件识别+跨位置+测试)/ D-41(below-avatar SIFT 可行但 2-3 件失效)/ read_equips(owned 列,对比)`。

## D-47 (2026-08-10)【画面·装备详情子态建档】点角色详情装备槽 icon → 中部弹装备详情(名/类型/属性/效果/适配/合成);icon 精确定位(pi crop)

- **交互确认(用户指令)**:角色详情(点 deployed 角色→右侧面板)底部「区域-装备槽」[1400,712,1900,798] 有3个穿戴装备 icon。**点装备槽 icon → 中部(x977-1360)弹装备详情子态**(不盖父屏 id_mark 购买经验,故父屏子态非独立 screen)。
- **装备详情内容**(点 icon1 = 步步生花,OCR):装备名(步步生花)+ 类型(进阶装备)+ 属性(速度增幅10%/伤害增幅15%/生命增幅10%)+ 效果描述(前台生命>70%时伤害增幅+30%)+ 适配角色 + 合成公式。与 D-18 装备推荐列表点的装备详情**同画面**(D-18 入口=装备推荐列表;本条入口=角色详情装备槽)。
- **装备槽 icon 精确定位**(pi crop 装备槽区,聚焦少干扰):3 icon 中心 **(1633,780)/(1702,780)/(1774,780)**(y780 在区域-装备槽 712-798 内偏底)。SIFT 0 + 98px TM 低 val(0.25-0.38)+ MCP VLM grounding y 偏 —— 装备槽 icon 识别/定位难(渲染特殊),**pi crop 聚焦**才准。
- **教训(VLM 坐标)**:点装备槽反复开天赋(点 (1500,755)/(1633,755) 都开天赋详情)—— y755 在 icon 上方(天赋/技能区);pi crop 定位 y780 才是 icon。**装备槽 icon 位置待建 screen_info area**(pc_rect,坐标单一源),后续 op 点装备经 area,免硬编码。
- **状态**:**装备详情子态交互 + 内容确认**;fixture 归档 ``equip_detail_stepbystep.webp``。待:① 建 screen_info area(装备名/类型/属性/合成/关闭)+ id_mark;② doc 建档(父屏货币战争-备战子态);③ 装备槽 icon pc_rect 入 screen_info(op 点装备经 area)。`· 用户(点装备→装备详情)/ D-18(装备推荐列表同画面)/ D-46(穿戴装备识别)`。

## D-48 (2026-08-10)【证据·大图压缩 vs mini·分辨率墙】3件28px below:大图简易0.77/进阶0.36-0.38;mini(2件裁)0.33-0.49不比大图好 → 大图压缩可行不需大规模mini;进阶+3件borderline是28px分辨率墙

- **验证(用户问:大图压缩可行否?需建mini?)**:对3件态 below(140550,28px icon)宽 scale(0.2-0.7)+ 双算法(AREA/LINEAR):
  - 大图(98px):光能电池(简易)**0.77✅**,步步生花/极·白昼·武器大师(进阶)0.36-0.38 borderline
  - native mini(2件态34px裁):步步生花0.33,折叠小刀0.49 —— **不比大图好**
- **纠正 D-46「mini 可靠」**:mini 是**尺寸特化** —— 2件态裁的 mini 只匹配2件态 icon(34px,0.9+),对3件态(28px)暴跌(0.33)。即 mini 跨件数也 borderline(每件数 icon 渲染不同,非只尺寸)。
- **根因(分辨率墙)**:below-avatar mini icon 随装备数缩小(1件~50/2件~34/3件~28px),**3件28px太小,任何模板(大图压缩/mini)都 borderline** —— 细节不足(D-46 归因「UI 装饰」部分纠正:主因是分辨率,非装饰)。
- **结论**:**大图压缩可行**(简易可靠 0.77),**不需大规模建 mini 库**。进阶+3件态 borderline 是 28px 分辨率墙(大图/mini 都受,非模板问题)。
- **简化方向**:`read_equipped_below` 大图 98px multi-scale(主,简易可靠 + 进阶尽力),mini 库只保留已采(步步生花+折叠小刀,2件态进阶补充),**不为每装备每件数采 mini**(工程大 + 3件也 borderline)。进阶3件 borderline 接受(分辨率限制);策略层先用简易可靠识别,进阶识别作尽力。
- **状态**:**大图压缩可行,mini 不需大规模**;进阶+3件 borderline 是分辨率墙。`· D-46(mini 2件0.9 但3件0.33=尺寸特化,「可靠」结论纠正)/ 用户(大图压缩可行否)/ 光能电池(简易大图0.77 验)`。

## D-49 (2026-08-10)【证据·纠正 D-48·icon 固定尺寸】below-avatar 装备 icon 固定 ~32px(98px×0.33)不随装备数变;D-48「icon 缩/分辨率墙」错(根因=harvest 投影法裁切假象);3件全中;mini 库冗余删除

- **触发(用户质疑)**:用户指出「角色下方装备图标大小应该是一样的」,怀疑 D-48「建库按尺寸分好几套」+ below 区域取错。
- **验证(CV 大图模板 multi-scale TM,1件 vs 3件同图对比)**:备战 1-6 截图(150914),front-1(3件)/front-3(1件)/front-4(1件)各槽 top1 最佳 scale **都是 0.33(32px)**:
  - front-1(3件):光能电池 0.781@0.35(34px)、步步生花 0.750@0.33(32px)、武器大师 0.745@0.33(32px)—— **3件全中**(无分辨率墙)
  - front-3(1件):减益星徽 0.744@0.33(32px);front-4(1件):治疗星徽 0.771@0.33(32px)
  - icon y 中心 = 481(全一致);`avatar_to_below` cy=479(差 2px,区域未取错,完整覆盖)
  - pi(qwen3.7-plus)同结论:所有 icon 尺寸一致(但 pi 绝对坐标偏,只取其相对一致性;以 CV 数值为准)
- **根因(D-48 为何错)**:harvest 脚本用**投影峰值法 + 硬编码 half** 裁 mini —— 紧密横排 icon(3件间距 ~4px)上投影连段/失灵,裁出的「2件 34px / 3件 28px」是**裁切产物**(脚本人为 half + 投影失灵),非真实 icon 尺寸。D-48 拿假数据推出「icon 随数量缩 → 3件 28px 分辨率墙」,整条推导链建立在错误前提。
- **结论**:**icon 固定 ~32px,不随装备数变**;**无分辨率墙,3件态大图模板 scale 0.33 全中**(0.745-0.781);**mini 库(cw_equip_mini)冗余**(34px mini ≈ 大图缩放结果),删除;`_EQUIP_TM_SCALES` 从 (0.3-0.5,29-49px 基于错误假设)收窄到 ~0.33 附近(覆盖 27-38px 余量)。
- **状态**:**icon 固定 32px,大图 scale 0.33 全中(含 3件),mini 库删除,`read_equipped_below` 简化(去 mini 路径 + scales 收窄)**。`· D-48(整条推翻:icon 不缩 / 无分辨率墙 / 3件全中 / mini 非必需而是冗余)/ D-46(mini 优先同样作废:大图 scale0.33 直接覆盖)/ 用户(质疑 icon 应同尺寸,触发纠正)`。

## D-50 (2026-08-10)【证据·槽位动态 gap·后排 >6】read_row_equipped/recognizer 后排 count=6 硬编码 + screen_info 后排-1..6 固定 rect;实际后排槽位随投资环境/财富宝钻可达 7-10(cx 随 N 变)→ 7-10 漏检。待运行时 CV 检测 avatar 位置适配(D-19 同类)

- **触发(用户)**:后排可能 >6(7/8/9/10),是否记录待适配。
- **现状**:`read_row_equipped` count=6(recognizer 传)+ screen_info 后排-1..6 固定 rect(cx 605-1316);`avatar_to_below` 依赖固定 rect。
- **gap**:① count=6 → 7-10 漏;② 后排 cx 随团队规模 N 变(舞台铺满),固定 rect 对 N>6 不准。
- **适配方向(后续)**:运行时 CV 检测后排 avatar 位置(轮廓/投影)→ 动态 count + cx → `avatar_to_below`。与 D-19(deploy_bench 实测槽位)+ 权威源「槽位布局=投资环境决定+空板CV检测」同类。
- **状态**:**gap 已记,待运行时槽位检测适配**;当前 count=6 覆盖 6 内(主流场景)。前排恒 4(团队规模前排固定,不动态)。`· D-19(槽位动态同类)/ 权威源(槽位布局投资环境决定)/ 用户(指出 >6 需记录)`。

## D-51 (2026-08-10)【纠正·后排-6 漏检根因=scale 漏(非裁切)·已修】icon 尺寸随位置变(梯形视角:前排~32px/后排最右~34px),武器大师后排-6 best scale=0.35 val0.601,step 0.03 漏 0.35 致漏检;scales 加 0.35 后全中

- **触发**:采后排-6 飞霄3件,`read_equipped_below` 漏武器大师(val0.57)。
- **初判(错)**:猜「角色卡框裁切 icon」/「below 区裁剪」(用户质疑梯形致区域不准)。
- **根因(scale 扫描确认)**:icon 尺寸**随位置变**(梯形视角:前排~32px/scale0.33,后排最右~34px/scale0.35)。武器大师后排-6 best scale=0.35 val0.601>0.6,但 `_EQUIP_TM_SCALES` step 0.03 漏 0.35(0.36 val0.481)→ 漏检。**非裁切/遮挡**(pi + 用户确认 icon 完整无遮挡,装备顺序不变)。推翻初判「卡框裁切」。
- **修**:`_EQUIP_TM_SCALES` = (0.30,0.33,0.35,0.37) 含 0.35,后排-6 武器大师 0.601 命中,3件全中。
- **教训**:val 低先扫 scale(图标尺寸随位置/视角变),别急着归「裁切/遮挡/接受漏检」(我初判草率,用户坚持查根因才纠正)。D-49「icon 固定尺寸」需修正:32-34px 随位置变。
- **状态**:**已修(scales 加 0.35),后排 1-6 全 cx 3件全中**。`· D-49(icon 尺寸 32-34px 随位置变,非完全固定)/ 用户(坚持查根因 + 装备顺序没变,推翻我"接受漏检"草率结论)`。

## D-52 (2026-08-10)【bug·通道·read_equipped_below BGR2GRAY 误用】screen 是 RGB(sr_od cv2_utils.read_image 约定),read_equipped_below 却用 BGR2GRAY(假设 BGR)→ R/B 通道灰度错位 → TM val 降;临界 icon(武器大师后排-6 0.604)被推<0.6 漏。修 RGB2GRAY

- **触发**:back6 webp 测试 fail,但手动 PNG 跑过(cv2.imdecode 返 BGR,BGR2GRAY 对);测试 load_screen 返 RGB,BGR2GRAY 错。
- **根因**:`read_equipped_below` `COLOR_BGR2GRAY`,但 sr_od screen 是 RGB(`cv2_utils.read_image` 约定)。R/B 通道灰度权重换(0.299↔0.114)→ 灰度错 → TM val 降。
- **影响**:所有 `read_equipped_below` 调用(recognizer + 测试)。高 val(0.7+)未暴露,临界(0.6 边缘)漏(武器大师后排-6 双重临界:scale 0.35 + 通道)。
- **修**:`COLOR_BGR2GRAY → COLOR_RGB2GRAY`。模板 `load_equip_tm_grays`(cv2.imdecode BGR)BGR2GRAY 对;screen RGB2GRAY 对;两者灰度真值一致(0.299R+0.587G+0.114B)。
- **教训**:sr_od screen 统一 RGB,灰度转换注意通道(别无脑 BGR2GRAY)。memory `cv2-utils-rgb-convention` 已记,read_equipped_below 漏了。
- **状态**:**已修(RGB2GRAY),22 测试过**。`· memory cv2-utils-rgb-convention / D-51(scale 后又发现通道,back6 武器双重临界暴露)`。

## D-53 (2026-08-10)【纠正·cap=level 实测核正 + read_deploy_cap 全 None 根因=pc_rect 切在文字上方 + 3x 放大拆斜杠】用户质疑「cap=level」用的是全屏 OCR(噪声)非裁剪 reader;实测裁剪 reader 全 None —— pc_rect 终点 y240 切在文字 y244 上方 + 无 padding + 3x 放大把斜杠 det 拆碎。修:pc_rect 给足 padding(右留 'X/10')+ 原生 OCR(去放大)+ 斜杠 normalize + X>Y guard。5 fixture 核 cap=level

- **触发(用户)**:「13/4→Y=4 这种情况,是全屏 OCR 识别不准吗?还是你裁剪识别的?」—— 质疑我 cap=level 结论的依据。
- **查证**:我之前 cap=level 用的是 `analyze_screen` **全屏 OCR**(噪声:deployed "5/5" 被读成 "13/4","1" 是邻元素噪声)。跑裁剪 reader `read_deploy_cap` → **6 fixture 全 None**(完全读不到)。
- **根因(debug 逐层)**:
  1. **pc_rect 切在文字上方**:`区域-部署数` 旧 `[790,185,1060,240]` 终点 y240,实际 "X/Y" 文字中心 **y244** → crop 只读顶部残影('1')。
  2. **无 padding 致 paddle det 拆碎**:crop 太紧 → paddle det 把 "5/5" 拆成两框丢斜杠(读成 '5' / '5 | 5'),而非一个整体 box。
  3. **3x 放大帮倒忙**:我先前加的 3x 放大(仿 read_gold "破 det 天花板")反而让 det 更碎(放大后斜杠更易被当独立框)。
- **用户指点(关键)**:① 字体够大,**放大没必要**(去 3x);② **"X/Y" 整串识别再提取**,别拆;③ **"/" 易被识成 1/l/I/i/|**,需特殊处理。
- **修(`_read_deploy_paddle`)**:
  1. **pc_rect 给足 padding**:`区域-部署数` `[820,210,1150,280]`(覆盖文字 y244 + 右留余量容 "X/10"/"10/10")→ paddle det 把 "X/Y" 当一个整体 box 原生读出。
  2. **原生 OCR(去放大)**:用户对,字够大,放大反碎斜杠。
  3. **斜杠 normalize**:`re.sub(r'(?<=\d)\D(?=\d)', '/', blob)` 把数字间非数字单字符(/ 误识成 l/I/i/|)还原成 /,再正则 `\d+/\d+` 提取。
  4. **X>Y guard**:deployed 不可能 > cap;slash→1 致 X 虚高(如 a8_start "10/3" 真值 0/3)→ 返 (None, Y)(deployed 走 fallback,cap 仍准)。
- **结论**:**cap=level(无钻石/宝钻/诅咒时)** —— 5 fixture 跨 lv3/4/5/7 实测核正(5/5@lv5、4/4@lv4、3/4@lv4、0/3@lv3、6/7@lv7,Y 恒=level)。shop_open 不显示部署数 → None → fallback level(cap=level 故 fallback 准)。钻石/财富宝钻 +1 → cap=level+1(>level 触发 recognizer D-50 告警)。
- **教训**:① 用户质疑数据来源时要分清「全屏 OCR 噪声」vs「裁剪 reader 真值」—— 我之前混了;② 裁剪 reader 全 None 别归「字小/放弃」,先查 pc_rect 是否覆盖文字(D-53 是 pc_rect 切错位);③ paddle det 需 padding 把短文本当整体,放大不是万能(此例放大帮倒忙);④ 用户指点(整串识 + 斜杠处理 + 不放大)是正解,我最初 2x 放大是次优。
- **状态**:**已修 + 5/6 read_deploy_cap==level(shop_open None 正确)+ 回归测试 test_read_deploy_cap_equals_level**。`· D-50(后排>6 适配,本 D-53 的 cap 可读是 D-50 告警的前提)/ 用户(质疑数据来源 + 指点整串识/斜杠/不放大/右 padding 容 X/10,全程纠正方向)`。

## D-54 (2026-08-10)【纠正·共脸变体 SIFT 可区分(非无法区分)】用户质疑"共脸变体认不出"——半身立绘库含变体独立模板+SIFT 取最高分+歧义过滤,变体分数明显拉开可区分。fixture 实测 deployed_p1r9 后排-2 姬子·启行 inliers=38,基础姬子<7 连 top3 未进。修过时 docstring(resolve_char_name)

- **触发(用户)**:"共脸变体认不出 -> 我理解应该有置信度的高低吧，不可能两个分数一样"。
- **查证**:`identify_character`(currency_war_char_id.py:99-112)对**所有**模板算 inliers 取最高 + 歧义过滤(best<1.5×second→None)。半身立绘库(`character_cw_portrait`)含变体独立模板(姬子/姬子·启行、刃/千冶·刃、丹恒·腾荒/饮月)。fixture 实测:deployed_p1r9 后排-2 **姬子·启行=38**,基础**姬子<7(top3 未进)** → 共脸对分数轻松拉开,非无法区分。
- **备战栏低 ratio 槽(姬子·启行 10-12 / 2nd 8-10)**:非共脸混淆(2nd 是长夜月/忘归人非基础姬子),是小裁图低信号 + 多角色弱匹配 → 歧义过滤返 None(保守不瞎猜,正确)。
- **修**:`resolve_char_name` docstring(cw_identity_obs.py:43-52)旧写"变体共脸 SIFT 无法区分,需星级/阵营旁证"(脸库时代结论)→ 改"半身库含变体,SIFT 分数可区分(D-54 验)"。函数体不变(56-65 英文 id 消歧是 legacy 兜底,半身库走 54 行直接命中)。
- **教训**:旧 docstring 结论(脸库时代)没随库切换(D-22 脸库→半身库)更新 → 知识漂移。库/算法切换后,依赖它的结论要同步复核。
- **状态**:**docstring 已修**。`· D-22(脸库→半身库,结论没同步)/ 用户(质疑分数相同,触发验证)`。

## D-55 (2026-08-10)【重构·商店 read_shop_cards OCR→SIFT + 商店牌肖像区 VLM 定位】OCR 牌名对开拓者(玩家自定义名"Momojie")读不到/匹配错;且旧 SIFT 测试因我猜裁切(screen_info 牌中心≠肖像中心)误判"弱"。VLM 定位肖像区(pi qwen3.7-plus bbox_2d 0-1000)→ 客观 SIFT 复核 33-68 内点 5/5 → 改 SIFT

- **触发(用户)**:开拓者真实名是开拓者,游戏里显示玩家自定义名"Momojie" → OCR 牌名读不到;「商店识别改回 SIFT」。+ 质疑我"猜坐标而非 VLM 确定"(D-55 方法论)。
- **查证(关键纠错)**:我先猜裁切 `x_center±95`(基于 screen_info 牌中心 377/646/…)→ SIFT 内点仅 6-14,误判"商店 SIFT 弱"。**用户质疑 → VLM(pi qwen3.7-plus, bbox_2d 0-1000)定位肖像真实中心 501/754/1007/1260/1513 → 客观 SIFT 复核:内点 33-68、5/5 命中 GT(翡翠/丹恒·腾荒/不死途/飞霄/三月七)**。根因:screen_info 商店牌-N 是**文字带/点击点**(中心 377/…),**≠肖像中心**(501/…,差 60-124px)→ 我裁错位置。VLM 才对(详见 ui-region-detect skill「VLM 定位信任层级」+ ADR-0005)。
- **改**:
  1. **screen_info 商店牌-1..5 pc_rect** → 肖像区(VLM 定位 `[cx-109,70,cx+109,260]`;cx=501/754/1007/1260/1513),`upsert_screen_area`。
  2. **`read_shop_cards` OCR→SIFT**:裁 商店牌-N 肖像 → `identify_character`(SIFT 立绘库)→ `resolve_char_name` 规范名;faction/cost 从 roster 派生(`ch.factions[0]`/`ch.cost`)。未识别 → name='' faction='?' cost=0(仍占位保 5 张,len 不变)。删 OCR helper `_match_char` + `difflib`。
  3. **`ensure_portrait_templates(ctx)`**(cw_identity_obs,镜像 ensure_equip_tm_templates):按需加载 character_cw_portrait 缓存 `ctx.cw_portrait_templates`。buy 在 deploy 前(BattlePrepCycle: buy→deploy),故 shop 不依赖 deploy 才加载的缓存。
  4. **faction 语义变**:OCR 牌标签 → roster factions[0](SIFT 读不了文字标签;**board OCR 仍是阵营计数权威**)。
- **接口不变**:`list[ShopCard]`(x/faction/name/cost/star);shop.py(`_tracked_bench_chars` 用 buy 名 seed bench)+ plan 消费无感。`shop_card_click_points` 改从 cw_obs_core import(不再经 cw_observation re-export)。
- **教训**:① VLM 定位可信,别猜坐标 + 别拿未验证参照系(screen_info 点击点)否定 VLM(同 D-55 方法论);② "SIFT 弱"结论常是裁切错,先查裁切位置(VLM/CV 定)再下结论;③ qwen3 bbox_2d 归一化 **0-1000**(非 0-999,官方文档,差 0.1% 可忽略但已订正 CLAUDE.md)。
- **状态**:**已修 + test_read_shop_cards_sift 5/5 GT(shop_open.webp)+ 258 测试过(仅既有 comp pivot 失败)**。**待办**:① 开拓者 roster gap(Momojie 模板 → 开拓者·欢愉/记忆,需定命途);② live 验买牌点击落在牌上(肖像中心 501 vs 旧文字中心 377,差 124px,需实机 click 核)。`· D-54(VLM 坐标可信方法论同源)/ 用户(开拓者 OCR 失败 + 推 VLM 定位 + 质疑猜坐标,全程纠方向)`。

## D-56 (2026-08-10)【验证·equip_all CV-diff 验穿 offline 核 + 抽 _below_icon_diff 纯函数】equip_all dormant,live drag 验阻塞(备战 owned 仅工具无穿戴类);但验穿逻辑(R19 avatar-slot CV-diff)可 offline 验。用飞霄 0→1→2→3 件 fixture:连续态 below-icon diff 28-41(>>阈值 8.0)、同态 0.0 → 验穿 + 阈值/区域可靠。抽 _below_icon_diff 纯函数 + 回归测试

- **触发**:equip_all(R19 CV-diff 验穿)dormant 未 live 验;live 阻塞(备战 1-6 owned 仅「冶金炉」工具,无穿戴类 → drag 流程测不了)。但**验穿逻辑本身**(drag 前后 avatar below-icon 区像素差)可 offline 用 fixture 验。
- **验**:`equipped_front1_feixiao_0/1/2/3`(front-1 飞霄 0→1→2→3 件顺序态)。`_below_icon_diff`(front-1 x743, below_y479, ±35/30):
  - 连续态(加 icon):0→1=28.1、1→2=41.4、2→3=40.6(**>>阈值 8.0**)。
  - 同态:0.0(< 8.0)。
  - → R19 CV-diff 验穿 + `BELOW_DIFF_THRESHOLD=8.0` + below_y479 区域 **offline 可靠**(干净区分穿了/没穿)。robust 合成消耗/列reflow/read漏检(不依赖 owned count)。
- **改**:抽 `_below_icon_diff(screen_pre, screen_post, avatar_x, below_y=479, bx_half=35, by_half=30) -> float` 成**模块级纯函数**(equip_all.py),op 内联 diff 改调它(可离线 fixture 测,治本:可测设计)。回归测试 `test_below_icon_diff_detects_equip`(飞霄 fixture 锁阈值/区域)。
- **状态**:**offline 验证 + 抽函数 + 回归测试**。剩 **live drag 落地机制 + read_equips 跨局面** 需游戏条件(补给/奖励节点出穿戴装备)才能验。`· D-41(R19 CV-diff 替 count-verify,本 D-56 offline 核其可靠)/ R14 P0-1(count 验穿假成功,已由 R19 CV-diff 解决)`。

## D-57 (2026-08-10)【验证·equip_all 首次 live 跑(no-op 路径)】备战 1-6 owned 仅冶金炉(工具)→ equip_all run_operation 实跑:read_equips 读到冶金炉 → 工具过滤(_TOOL_CATEGORIES)→ 无穿戴候选 → 干净 break round_success「0 件」,1.97s,无 drag/crash/bug#2。验 read+filter+exit 在真实画面可靠;drag/CV-diff 路径仍待穿戴装备

- **触发**:equip_all dormant 从未 live 跑;备战略 owned 仅工具(冶金炉)无穿戴类 → 正好测 **no-op 路径**(无穿戴 → 干净退出),不需穿戴装备也能验一部分。
- **跑**:`run_operation(equip_all.EquipAll)`(MCP 后端,真实备战屏)。结果 state=success、duration=1.97s、last_status「装备 0 件到前排 avatar」、failed_node=null。游戏态不变(冶金炉还在,4/4 不变)。
- **验到**:① cw_equip SIFT 模板加载 OK;② read_equips 在 live 屏读到冶金炉;③ `_TOOL_CATEGORIES={'工具'}` 过滤冶金炉(category='工具')→ wearable=[];④ 无穿戴 → `break` → round_success(不 retry、不 crash);⑤ 无 bug#2(无条件 ESC)、无 bug#1(无 drag)。**read+filter+exit 路径 live 可靠**。
- **未验(仍阻塞)**:drag 穿戴类 → CV-diff 验穿(D-56 offline 核了 diff 逻辑,但 live drag 落地 + read_equips 跨局面 需 owned 穿戴装备 = 补给/奖励节点)。
- **状态**:**no-op 路径 live 验证**(+ D-56 offline 验穿逻辑)。equip_all 激活剩:① live drag 测(需穿戴 owned)② P0-2(drag 前 read_equipped_below 读槽空满)③ 接 BattlePrepCycle。`· D-56(offline CV-diff 核)/ R19(CV-diff 替 count-verify)/ D-53~D-55(同期 shop/identity 工作)`。

## D-58 (2026-08-11)【实现·equip_all P0-2 drag 前占位检测】原 `target=FRONT_AVATARS[equipped]` 按已穿计数索引 → 已穿槽被覆盖(前排部分角色 pre-equip 时 drag 会覆盖)。改:drag 前 read_row_equipped 读前排 avatar 已穿 → `_empty_slots` 算空槽 → 只往空槽 drag(target=FRONT_AVATARS[slot-1])

- **触发**:D-57 列 equip_all 激活剩项含「P0-2」。原循环 `while equipped < len(FRONT_AVATARS): target = FRONT_AVATARS[equipped]` —— `equipped` 只计本轮已穿,假设槽 0..equipped-1 顺次填;若某槽 pre-equip(已有装备)→ drag 覆盖它(游戏换装或拒)。
- **改**:① `_get_tm_grays`(load_equip_tm_grays 缓存 ctx,镜像 `_get_templates`);② drag 前 `read_row_equipped(ctx, screen, grays, '前排', 4)` 读已穿 → `_empty_slots(occupied, 4)`(纯函数,槽不在 dict=空)→ 只迭代空槽,`target = FRONT_AVATARS[slot_idx-1]`;③ 全已穿 → round_success「全已穿跳过」。
- **备选(否)**:① 不读占位、信任顺次填 —— 否(覆盖已穿);② CV 灰度 std 判占用(新函数)—— 否(read_row_equipped D-49 已 validated,复用优先,不造新)。
- **复用 + 风险**:read_row_equipped(D-49 below-avatar TM,threshold 0.6)判占用;`_below_icon_diff`(D-56)验穿不变。P0-2 只改目标选择(空槽),不改验穿。false-negative(read_equipped_below 漏已穿→误判空→drag 覆盖)bounded(0.6 validated)+ 验穿兜底。
- **测**:`test_empty_slots_skips_occupied`(纯函数:全空→全槽 / 部分→跳过 / 全已穿→空)。offline 验空槽选择逻辑。drag 占用读 + live 验仍待穿戴装备条件。
- **状态**:**P0-2 offline 实现完成**。equip_all 激活剩:① live drag 测(需穿戴 owned = 补给节点)② 接 BattlePrepCycle。`· D-57(列 P0-2 为剩项)/ D-49(read_equipped_below)/ D-56(_below_icon_diff 验穿)`。

## D-59 (2026-08-11)【数据·装备注册表 5 错位排查 + 1 修(管理员手套)】cw_equip 模板名(154 png,harvest OCR 命名)vs EQUIPMENTS 注册表(153 件,equipment.md 生成)5 处不匹配 → read_equips 把这 5 件当 unknown 过滤(漏识别 owned)。排查:1 确认 cropper 误名(管理员手套ProMax→管理员手套,已 git mv 修);4 是注册表数据缺(命运圣杯星徽 确认独立 web+CV,注册表错并;诅咒·干将莫邪/财富 待图鉴核),不猜,待数据银行图鉴验证后补 equipment.md + 重生成

- **触发**:equip_all read_equips 有 `unknown = [n for n, _, _ in hits if EQUIPMENTS.get(n) is None]` warning(R18 P1)。模板 stem ≠ 注册表 key → 漏识别 owned 装备。
- **排查(客观脚本)**:比 `assets/template/cw_equip/*.png` stem vs `EQUIPMENTS` keys → 5 不匹配:
  - **管理员手套ProMax**(模板)→ 注册表「管理员手套」(骇客 7891)。注册表无任何 "ProMax"(只 Max/Pro 后缀)→ cropper 误名。✅ **已修(git mv → 管理员手套.png)**;全仓 grep 无代码/测试引用 → 安全。
  - **列车同行星徽 + 命运圣杯星徽**(2 模板)→ 注册表仅 1 条「列车同行星徽(命运圣杯星徽)」。MSE=1378(两图不同,非 dup)。Web 核:命运圣杯星徽是 Fate 联动**独立星徽**(命运圣杯羁绊),列车同行是另一羁绊 → **注册表错并成 1 条,缺命运圣杯星徽 entry**。待图鉴核各自 content_id/effect 后拆 equipment.md + 重生成。
  - **诅咒·干将莫邪**(模板)→ 注册表只有 干将莫邪/极·干将莫邪(无诅咒版)。命运系有诅咒变体(诅咒·阿瓦隆等)→ 诅咒·干将莫邪 可能真品(equipment.md 漏)或误裁。待图鉴核。
  - **财富**(模板)→ 注册表 财富(基础)/财富(强化) 2 条。模板 bare「财富」→ 属基础 or 强化 待图鉴核。
- **不猜原则**:4 项均需数据银行图鉴(content_id/effect/变体存在性)权威核,不凭推断命名/重命名(治本非叠补丁)。命运圣杯星徽 虽 web 确认独立,但 content_id(7292)归属未定 → 不擅拆。
- **状态**:**1/5 修(管理员手套),4/5 图鉴待核**(分析完成,记此供后续图鉴 session 直接补)。影响:read_equips 漏识别这 4 件 owned(列车同行/命运圣杯星徽 常见=中;诅咒·干将莫邪 命运=低;财富 特殊无用=低)。`· R18 P1(unknown warning)/ 数据银行图鉴(权威源,待核 4 项)`。

## D-60 (2026-08-11)【验证·equip_all P0-2 live 跑(no-equip 路径)】server restart 加载 P0-2 代码后 run_operation equip_all 实跑(D-58 代码首次 live):_get_tm_grays 加载 154 TM grays ✓ / read_row_equipped 跑(前排全空 occupied={})/ _empty_slots → [1,2,3,4] ✓ / read_equips 读冶金炉(count=1 工具)→ 过滤 → 无穿戴 → 0 件退出。**P0-2 新代码(占位读 + 空槽选择)live 验证通过(no-equip 路径)**;drag + occupied-非空 路径仍待穿戴装备

- **触发**:D-58 P0-2 offline 实现后,首次 live 跑验新代码(占位读 read_row_equipped + _get_tm_grays + _empty_slots 在真实备战不崩 + 逻辑对)。
- **跑**:restart_sr_od_mcp_server(加载 P0-2)→ run_operation(EquipAll,备战 1-8)。log:
  - `[cw-equip] 加载 154 个 cw_equip 模板`(SIFT)+ `加载 154 个 cw_equip TM grays`(TM,新 `_get_tm_grays`)—— 两套模板库都加载(154,含重命名后管理员手套)。
  - read_row_equipped 跑(前排 4 槽 below-avatar TM)→ occupied={}(全空,无 pre-equip)→ 无「已穿槽」日志(空不记)。
  - `_empty_slots({}, 4)` = [1,2,3,4](全空)。
  - read_equips → count=1(冶金炉,工具)→ `_TOOL_CATEGORIES` 过滤 → wearable=[] → 「无穿戴候选 → 停」。
  - last_status「装备 0 件到前排 avatar(空槽 [1, 2, 3, 4])」,2.9s,success。
- **验到**:① `_get_tm_grays` 加载 154 TM grays(新加载器 live OK);② `read_row_equipped` 在 op 上下文跑(无崩,返 {});③ `_empty_slots` 逻辑 live 对([1,2,3,4]);④ read+filter+exit 路径(D-57 验过)再现。**P0-2 新代码 live 通过(no-equip 路径)**。
- **未验(仍阻塞)**:① drag 穿戴类→CV-diff 验穿(需 owned 穿戴装备 = 补给节点);② P0-2 occupied-非空 路径(前排有 pre-equip → 跳过那些槽,需角色已穿装备)。
- **状态**:**P0-2 live 验证(no-equip 路径)**。equip_all 激活剩:① live drag(需穿戴 owned)② occupied-非空 验(需 pre-equip)③ 接 BattlePrepCycle。`· D-58(P0-2 实现)/ D-57(no-op 路径 live)/ D-49(read_equipped_below)`。

## D-61 (2026-08-11)【发现·read_equipped_below 边缘假阳性(完美投影仪 0.62 空槽)】备战 1-9 extras.front_equips={2:[完美投影仪]}(recognizer),但同屏 equip_all read_row_equipped 返 occupied={}。log 揭:slot2 完美投影仪 val_top=0.62(≥thr0.6)+ 无完整1/2/3件布局 anomaly + MISS → 边缘假阳性(空槽误匹配工具模板 0.62,不稳:一帧命中一帧空)。recognizer 已 [cw!] 标 anomaly 但 val≥thr 仍计入。影响 P0-2(假 occupied→误跳槽)。修需:布局anomaly + 边缘val→判空/未知(待①-a 装备区画面模型)

- **触发**:equip_all run(1-9)read occupied={}(slots=[1,2,3,4]),但稍早 analyze extras.front_equips={2:[完美投影仪]}。同函数 read_equipped_below 不同结果 → 查 log。
- **log(recognizer 01:18:27)**:`[cw!][read_equipped][slot=2] anomaly=无完整1/2/3件布局(命中候选[21]) equips=['完美投影仪']` + `MISS=布局(-21,21)缺候选[-21]` + `equips=['完美投影仪'] val_top=0.62 MISS=[光能盾牌0.58,生命之花0.57,幸运星0.57]`。
- **判**:slot2 实为空(完美投影仪是工具不穿戴;equip_all 读空)。完美投影仪 val 0.62 刚过 thr0.6 + 无完整布局(单件工具不该在该位置)→ **边缘假阳性**,不稳(0.62 近阈值:一帧命中一帧空)。
- **影响**:① read_equipped_below 边缘假阳性(空槽误匹配工具);② 影响 P0-2(若 read_row_equipped 返假 occupied={2:...}→ `_empty_slots` 误跳槽2 → 空槽被当已穿 → 漏装);③ recognizer 已 [cw!] 标 anomaly 但 val≥thr 仍计入 → 需补「布局anomaly + 边缘val → 判空/未知」。
- **修(待①-a)**:read_equipped_below 增守卫:布局anomaly(无完整1/2/3件布局)+ 候选val 近阈值(<~0.65)→ 判未知/空(不计数)。需画面模型(空槽 below 区 vs 有 icon)支撑。**不擅改阈值**(0.6 是 D-49 validated,提高致真漏检;需布局守卫非裸阈值)。
- **状态**:**发现(记)**。装备库仍无穿戴(phase 1-9 level 6,仍冶金炉1件工具)→ ①-a drag 仍阻塞。read_equipped_below 边缘假阳列入①-a 装备区画面模型时修。`· D-49(read_equipped_below)/ D-58(P0-2)/ D-60(P0-2 live)`。

## D-62 (2026-08-11)【修·read_equipped_below 边缘假阳(D-61)】`_select_equipped_layout` 无完整1/2/3件布局时原返 fallback 全命中候选(致 D-61 完美投影仪 val0.62 单件落 +21 候选被当装备返 → 空槽假阳)。CW 每角色最多3件,1/2/3件布局覆盖全部合法配置 → 无完整布局 = 误检。改:无完整布局返 `[]`(不返 fallback),anomaly + MISS 日志保留(诊断)。单元测试 + D-49 既有测试过

- **触发**:D-61 发现 read_equipped_below 边缘假阳(完美投影仪 0.62 空槽误匹配)。
- **根因**:`_select_equipped_layout` 无完整布局的 fallback(返全命中候选,原 `return equipped`)—— 单件落 +21(2件布局右位缺 -21)无完整布局,仍被当装备返 → 假阳。
- **改**:无完整布局 → `return []`(非 fallback 候选)。CW 每角色最多3件,1/2/3件布局(cx±43/±21/0)覆盖全部合法配置;无完整布局 = 误检(非合法位置),返空。anomaly + MISS 日志保留(诊断漏检/误检)。
- **不擅改**:阈值(0.6 是 D-49 validated,提高致真漏检)—— 改的是**布局守卫**(无完整布局返空),非阈值。
- **测**:`test_select_layout_no_complete_returns_empty`(单件 +21 → [],单件 0 → [件])。D-49 既有测试(1/2/3件 valid + 0件 empty)17/17 过(合法路径不破坏)。
- **状态**:**修 + 单元测过**。read_equipped_below 边缘假阳(D-61)解决 —— recognizer/P0-2 不再把无完整布局的误检候选当 occupied。live 再验待同帧假阳重现(间歇,单元+逻辑验充分)。`· D-61(发现)/ D-49(read_equipped_below)/ D-58(P0-2 受益)`。

## D-63 (2026-08-11)【验证·D-62 fix live(完美投影仪假阳同帧重现→正确判空)】备战 1-9(首领局)equip_all run,log 显示 slot2 完美投影仪 val0.62 + 无完整布局 anomaly → **D-62 fix 生效**:anomaly msg 含「→判空(误检,不返)」,equip_all read occupied={}(slots=[1,2,3,4],slot2 未误计)。**D-61 同帧假阳重现 + D-62 fix 正确拒**;back_equips 真 已穿(步步生花+光能电池+武器大师 slot6 3件 valid 布局)仍正确读 → fix 不破坏合法读

- **触发**:D-62 fix(无完整布局返[])后 live 验。
- **log(01:38:45)**:`[cw!][read_equipped][slot=2] anomaly=无完整1/2/3件布局(命中候选[21])→判空(误检,不返) equips=['完美投影仪']` + MISS。**anomaly msg 含 D-62 新增「→判空(误检,不返)」** → fix 代码 live 生效。equip_all result `slots=[1,2,3,4]`(occupied={}) → slot2 未误计为 occupied(D-61 假阳被拒)。
- **对比 D-61**:D-61 同场景(完美投影仪0.62 slot2)→ 旧代码返 fallback [完美投影仪] → recognizer front_equips 假阳。D-62 fix → 返 [] → 不假阳。**同帧假阳重现 + fix 正确拒 = live 验证**。
- **合法读不破坏**:back_equips={6:[步步生花,光能电池,武器大师]}(3件 valid 布局)仍正确读 → fix 只拒无完整布局的误检,不破坏 valid 布局。
- **①-a drag 仍阻塞**:装备库 count=1(仅冶金炉工具,无穿戴 owned)→ equip_all 无穿戴候选(0 件)。穿戴装备都在 back-row 已穿(非 装备库 owned)。drag 全链 live 测待 owned 穿戴自然落 装备库(**不破坏 back-row 好装备用 冶金炉 强测** —— drag 已 D-36 验,破坏步步生花+光能电池+武器大师不值)。
- **server 观察**:本轮多次 sr_od「disconnected」通知,但 log 干净(startup complete + 处理请求),指令重显 → **客户端瞬断重连噪声,非 server 崩**(game op 正常)。
- **状态**:**D-62 fix live 验证通过**(D-61 假阳场景重现 + 正确拒)。read_equipped_below 边缘假阳闭环(发现 D-61 → 修 D-62 → live 验 D-63)。`· D-61(发现)/ D-62(修)/ D-49(read_equipped_below)`。

## D-64 (2026-08-11)【数据·装备注册表 命运圣杯星徽 图鉴验 + 拆分(D-59 2/4 修)】数据银行装备图鉴星徽类 21/22 解锁,列车同行星徽(unlocked,列车同行羁绊)在,命运圣杯星徽不在解锁列 = 第22 locked → 确认独立星徽(registry 错并为1条)。拆 equipment.md:列车同行星徽(7292)+ 命运圣杯星徽(效果按阵营星徽模式推断,source 待核图鉴locked)。重生成 → 注册表 154 件,2 模板(列车同行/命运圣杯)匹配。剩 诅咒·干将莫邪/财富 待核(图鉴分类导航坐标不稳,低价值 defer)

- **触发**:D-59 列 4/5 图鉴待核;命运圣杯星徽 web 确认独立(D-59)待图鉴坐实。
- **图鉴验(数据银行 → 装备图鉴 → 星徽类)**:星徽 21/22 解锁。列车同行星徽在(unlocked,效果「加入【列车同行】羁绊」)。命运圣杯星徽 **不在 21 解锁列 = 第22 locked**(本账号未解锁)→ 确认独立星徽(registry「列车同行星徽(命运圣杯星徽)」错并)。content_id 7292 属列车同行(unlocked 可见);命运圣杯 source 图鉴 locked 不可读。
- **修**:equipment.md 拆 line 154 → 「列车同行星徽(7292)」+ 「命运圣杯星徽(效果按阵营星徽模式「加入【命运圣杯】羁绊」推断,source 「待核(图鉴locked,D-64)」占位保 3-cell 格式,空 source 会被生成器当 2-cell 丢效果)」。重生成 `gen_equip_registry.py` → cw_equipment_data.py 154 件(153→154,+1 拆)。
- **验**:mismatch 脚本 templates NOT in registry 从 4→2(列车同行+命运圣杯 修;剩 诅咒·干将莫邪+财富)。17 测试过。模板 列车同行星徽.png + 命运圣杯星徽.png 现匹配 registry。
- **工具/消耗品 附带确认**:图鉴 7/7 消耗品(拆装扳手/精密拆装扳手/冶金炉/特权赋予卡/员工投影仪/完美投影仪/好运令牌)无 管理员手套ProMax → D-59 管理员手套 rename 正确(管理员手套是骇客非工具)。
- **不猜边界**:命运圣杯星徽 效果按星徽模式推断(高置信:阵营星徽统一「加入【X】羁绊」+ web 确认命运圣杯羁绊);source 待核(图鉴 locked 不可读,明标)。content_id 不擅填(7292 属列车同行)。
- **剩(D-59 2/4)**:诅咒·干将莫邪(命运系)/ 财富(特殊)待核 —— 图鉴分类导航 VLM 坐标不稳(点命运→误入工具),低价值 defer。
- **状态**:**命运圣杯星徽 拆分修(D-59 2/4)**。注册表 154 件。剩 2 低价值待核。`· D-59(5 错位排查)/ 数据银行装备图鉴(权威)/ gen_equip_registry.py(重生成)`。

## D-65 (2026-08-11)【发现·结算「挑战结束」标题变体 + is_failed LCS 误同】备战 1-9 首领局出战 → 结算标题「挑战结束」(非常规成功:挑战进度 14/20 + HP1 存活,继续按钮在对局继续,非 match-over)。同 结算布局(获得金币/继续挑战),继续挑战 id_mark 命中 is_precise。但 `标识-挑战成功` area(text「挑战成功」)LCS 匹配「挑战结束」0.998 → recognizer is_failed=false(挑战结束 被当成功)。fixture ended.webp 归档(id_mark 测试 +1 过)。is_failed 精确判据待攒齐 3 标题(成功/结束/失败)定

- **触发**:备战 1-9 首领局出战 → 结算标题「挑战结束」(非「挑战成功」)。
- **观察**:挑战结束 结算 = 同布局(获得金币总览/基础奖励/利息/连胜/继续挑战),挑战进度 14/20 + HP1(首领局存活)。「继续」在对局继续 → 非 match-over(回合结束态,非常规成功)。`按钮-继续挑战` id_mark 命中 → 货币战争-结算 `is_precise=true` ✓。
- **is_failed LCS 误同**:`标识-挑战成功` area text「挑战成功」LCS 匹配「挑战结束」0.998 → 两标题同 area 命中 → recognizer `is_failed=false`(挑战结束 被当成功读)。**若 挑战结束 语义 ≠ 成功**(平/首领存活/非常规),is_failed 需精确标题判(非 LCS area)。
- **fixture**:`ended.webp`(挑战结束)归档 `sr-od-test/screens/货币战争-结算/`(+ `win.webp` 挑战成功)。id_mark 测试 39 过(+1,ended 也命中 继续挑战 id_mark)。
- **状态**:**发现(记)+ fixture 归档**。结算 标题变体(成功/结束/失败):成功✓ 结束✓(D-65) 失败待。is_failed 精确判据待攒齐 3 标题 fixture 后定。`· 结算 onboarding(2026-08-11)/ D-122(结算 recognizer hp_after/is_failed)`。

## D-66 (2026-08-11)【修正·D-65 is_failed 误判纠正(recognizer 用 _FAIL_MARKER 非 area LCS)】查 settlement_recognizer.py:`is_failed = any(_FAIL_MARKER in t for t in ocr_texts)`,`_FAIL_MARKER='挑战失败'`(line 38/74),**非** `标识-挑战成功` area LCS。故 挑战结束 → `is_failed=false` **正确**(结束≠失败,非误读)。D-65「is_failed LCS 误同」推测**作废**(基于错误假设 is_failed 用 area)。area 命名瑕疵不影响(非 id_mark、不影响 is_failed)

- **触发**:D-65 推测 is_failed 用 area LCS(挑战结束→is_failed=false 疑误读)待核。
- **查**:`recognizers/settlement_recognizer.py` line 74 `is_failed = any(_FAIL_MARKER in (t or '') for t in ocr_texts)`,`_FAIL_MARKER='挑战失败'`(line 38)。**is_failed 用「挑战失败」substring on `ocr_texts`,非 `标识-挑战成功` area**。
- **结论**:挑战成功/结束(无「挑战失败」)→ is_failed=false ✓;挑战失败(有「挑战失败」)→ is_failed=true ✓。**挑战结束 → is_failed=false 正确**(结束≠失败)。D-65「is_failed LCS 误同」推测**作废**(基于错误假设 is_failed 用 area)。
- **次要**:`标识-挑战成功` area(text「挑战成功」)确 LCS 匹配「挑战结束」0.998 —— 仅 area 命名略不准(该 area **非 id_mark**[继续挑战才是],不影响 screen 识别,也不影响 is_failed[_FAIL_MARKER 判])。可不改(命名瑕疵,改名 churn 不值)。
- **状态**:**D-65 is_failed 误判纠正**。is_failed 逻辑正确(无需修)。结算 3 标题 is_failed 判据已明:**有「挑战失败」→ true,余 → false**。`· D-65(挑战结束变体+is_failed 推测)/ settlement_recognizer.py(_FAIL_MARKER)`。

## D-67 (2026-08-11)【发现·「挑战失败」是独立 match-over 屏(非 继续挑战 结算变体)+ A8 难度实锤】位面 2-1 出战 → 挑战失败(HP0 团灭)→ **独立屏**(挑战失败 + 小队生命值❤0 + 对局评价 + **「下一步」**,**非「继续挑战」**)→ 货币战争-结算 is_precise=FALSE(继续挑战 id_mark 缺)。下一步 → 对局评价页(标准博弈 **A8** + 积分 9600 + 阵容 + 投资环境/策略)。**挑战失败 ≠ 继续挑战 结算变体**(独立 match-over 屏,下一步按钮);D-65「结算 3 标题变体」需纠正(成功/结束 是 继续挑战 结算变体;失败 是独立 match-over 屏)

- **触发**:位面 2-1 出战(4/5 deploy)→ 挑战失败(HP 0 团灭)→ 看失败态屏。
- **观察**:挑战失败 屏 = `挑战失败` + `小队生命值❤0` + `对局评价` + **`下一步`**(非`继续挑战`)。**货币战争-结算 is_precise=FALSE**(继续挑战 id_mark 缺 → 不命中)→ **失败态是独立 match-over 屏,非 继续挑战 结算的标题变体**。下一步 → 对局评价页(`对局未完成 2-1X战斗` / `标准博弈 A8贝` / `财富造物主40` 对手 / `晋升等级170` / `积分9600` / 我的阵容/投资环境/策略 / 下一页)。
- **A8 实锤**:对局评价显示「标准博弈 **A8**」→ **本局是 A8 难度**(D-3 目标难度),位面 2-1 团灭(积分 9600)。验:bot 能进 A8 对局 + 推进到位面 2(位面1 boss 已过)。
- **纠正 D-65**:D-65 称「结算 3 标题变体(成功/结束/失败)」**部分错** —— 成功/结束 是 `继续挑战` 结算的标题变体(同布局同 id_mark);**失败 是独立 match-over 屏**(下一步按钮,继续挑战 id_mark 缺,is_precise=FALSE)。失败态 fixture 采(screenshot_20260811_020714_489077.png,**不归 货币战争-结算/**,独立屏待建档 货币战争-挑战失败/对局结束)。
- **状态**:**发现(记)+ fixture 采**。挑战失败 独立 match-over 屏(待建档,有别于 继续挑战 结算)。A8 难度实锤。bot 流程:备战→出战→…→(赢)继续挑战 结算 / (HP0 团灭)挑战失败 match-over→对局评价→(回大厅/新局)。`· D-65(结算变体,部分纠正)/ 结算 onboarding / D-3(A8 目标)`。

## D-68 (2026-08-11)【建档·货币战争-挑战失败 match-over 屏 + 双 id_mark 碰撞修】建 货币战争-挑战失败 screen_info(D-67 发现的团灭 match-over 屏):id_mark `标识-挑战失败` + `按钮-下一步`(**双 id_mark**,D-68 碰撞修)+ `文本-小队生命值`。fixture `failed.webp`(A8 位面2-1 团灭)。id_mark 测试 40 过(+1)。**碰撞修**:挑战失败 标题 LCS 高匹配 挑战成功(~0.99,同 D-65)→ 单 id_mark 致结算 fixture 误识为挑战失败;加 下一步 第2 id_mark(挑战失败屏有,结算无 继续挑战)→ 双命中防碰撞,20 fail baseline 恢复

- **建档**:货币战争-挑战失败(id_mark 挑战失败 + 下一步 + 小队生命值)。doc + README 索引。fixture `failed.webp`(A8 位面2-1 团灭,D-67)。id_mark 测试 PASSED。
- **碰撞问题**:挑战失败 标题 LCS 高匹配 挑战成功(conf~0.99,同 D-65 挑战结束 问题)→ 单 挑战失败 id_mark 致**结算 fixture(win/ended)误识为 挑战失败**(+2 测试 fail:结算 + 挑战失败 用例互串)。
- **修(双 id_mark)**:加 `按钮-下一步` 第2 id_mark(挑战失败屏有 下一步;结算屏有 继续挑战 无 下一步)→ 挑战失败 is_precise 需 挑战失败+下一步 双命中;结算 fixture 无 下一步 → 不误识为 挑战失败。碰撞解(20 fail baseline 恢复,40 过 +1)。
- **教训**:CW 结算类标题(成功/结束/失败)LCS 互相高匹(~0.99);用标题做 id_mark 易跨屏串。**双 id_mark(标题 + 屏独有按钮)**防串(成功/结束 共 继续挑战;失败 用 下一步)。
- **状态**:**挑战失败 建档 + 碰撞修**。bot 识别对局结束(挑战失败+下一步)vs 回合结算(继续挑战)。`· D-67(挑战失败发现)/ D-65(挑战结束 LCS)/ 结算 onboarding`。

<!-- 新 D-NN 条目加在这里(按时间倒序) -->
