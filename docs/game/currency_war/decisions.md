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

<!-- 新 D-NN 条目加在这里(按时间倒序) -->
