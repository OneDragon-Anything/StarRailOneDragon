# 货币战争 · 决策索引(ADR)

> 原 `docs/game/currency_war/decisions.md`(D-NN append-only,92 条)已转为 ADR(一决策一文件)。
> **废弃条目(bug 修 / 诊断叙事 / 一次性验证 / 被 later D-NN 取代 / 数据进代码 / 过程记录 / 调参实验)未转入** —— git 可查:`git show HEAD:docs/game/currency_war/decisions.md`。
> 文件名 `00NN-<slug>.md`,NN = 原 D-NN 号(保留可追溯,代码/文档里的 D-NN 引用据此映射)。
> D-15/D-16 自主推进期已删(不可信);D-77 源文件缺(引用存在,条目未写)。

| 编号 | 标题 | Status | 日期 | 一句话 |
|------|------|--------|------|--------|
| [0007](0007-deploy-deterministic-cv-verify.md) | deploy 确定性部署(CV 占用→拖空槽→CV 验源空) | accepted | 2026-08-09 | 替 trial-and-error,CV 确定性部署只拖空槽 + 验源槽空 |
| [0012](0012-observation-loop-sift-reconcile.md) | 观测回路:deploy 后 SIFT 纠 tracking 漂移 | accepted | 2026-08-09 | deploy 后 SIFT 真实身份重置 tracking,闭合观测回路(解锁核心锁②) |
| [0014](0014-economy-leveling-remove-board-strong-gate.md) | 经济 leveling:`_saving_for_level` 去 `_board_strong` 门 | accepted | 2026-08-09 | 弱板也攒级(破 chicken-egg),leveling 修对 |
| [0017](0017-research-evidence-base.md) | 货币战争机制研究证据基 | accepted | 2026-08-09 | 多源交叉 + 证据等级,经济/装备/A8 阵容权威地基 |
| [0019](0019-max-units-dynamic-back-row.md) | 团队规模上限 = level + 财富宝钻/诅咒;后排非固定 6 | accepted | 2026-08-09 | cap 动态(宝钻+1/诅咒-1),后排须运行时实测 |
| [0021](0021-phase-skeleton-faction-agnostic.md) | 阶段节奏骨架 = 阵容无关骨架 × 阵容参数 | accepted | 2026-08-09 | 不为每阵容写流程,统一骨架 + level_plan 接缝参数化 |
| [0027](0027-equip-owned-sift-template-detection.md) | 装备 owned icon 检测用 cw_equip SIFT(推翻 VLM 球体误判) | accepted | 2026-08-10 | owned icon 用 SIFT 模板库检测,非亮度/VLM;小 icon 必裁切放大 |
| [0044](0044-equip-verify-avatar-slot-cv-diff.md) | equip_all 验穿用 avatar-slot CV-diff(替 count-verify) | accepted | 2026-08-10 | drag 前后对比 avatar 下方 icon 区,robust 合成/reflow/漏检 |
| [0049](0049-below-avatar-icon-fixed-32px.md) | below-avatar 装备 icon 固定 ~32px(98px 模板 scale 0.33) | accepted | 2026-08-10 | icon 不随装备数变(纠正 mini-template/分辨率墙误判) |
| [0055](0055-shop-cards-sift-vlm-locate.md) | 商店牌识别 OCR→SIFT + 肖像区 VLM 定位 | accepted | 2026-08-10 | 开拓者自定义名破 OCR,改 SIFT;VLM 定位可信别猜坐标 |
| [0081](0081-static-data-auto-write-guard.md) | 静态游戏数据 auto-write 守卫:garbage 拒 + existing 不覆盖 | accepted | 2026-08-11 | 防 OCR 污染写回 ground truth(词缀/装备效果类静态数据) |
| [0091](0091-refresh-prob-live-ocr-authoritative.md) | 商店刷新概率表 REFRESH_PROB 实机 OCR 落地 | accepted | 2026-08-11 | 弹窗表权威(非底部条/placeholder),基础表 + 效果修正待 A4.7 |
| [0092](0092-acquirability-theoretical-not-observed.md) | select_comp 可得性用理论概率非观察 | accepted | 2026-08-11 | 刷新独立→观察无预测力,改 min(refresh_prob) 理论法 |
| [0094](0094-strategy-merge-single-source.md) | 策略三轴重设计与 14 重复 → 合并入 14 + 删 15 | accepted | 2026-08-11 | 单一源(防双源漂移),重设计前先 grep 现有文档 |
| [0095](0095-strategy-design-round1-av-correction.md) | 策略方案定型轮 1(限时 AV / 掉血归因 / commit 渐进 / COMP 扩充) | accepted | 2026-08-11 | review HIGH + 用户玩法修正折进设计;限时=行动值 AV |
| [0096](0096-optionality-vs-commit-reconciliation.md) | optionality/α(t) 与 commit 不矛盾(管不同决策:eval vs pivot) | accepted | 2026-08-11 | optionality 限定通用角色(≥2 comp);α 在 eval、commit 在 pivot,正交 |
| [0097](0097-strategy-impl-wiring-nodeplan-transition-streak.md) | 策略实现接线轮(node_plan / evaluate α-blend 接法 / transition_tempo / streak 杠杆 / A4.3 牌池) | accepted | 2026-08-11 | 14 §2 node_plan 落地 + 0096 α-blend 接 evaluate + round-4 过渡羁绊 + 结算 streak magnitude 进 economy + 0091 表采 D 牌 |
| [0098](0098-comp-viability-star-dimension.md) | comp_viability 加 star 维度(star_achievement;review HIGH-1) | accepted | 2026-08-11 | 核心角色 bot 跟踪 star 归一化进先验(0.40/0.25/0.20/0.15);限时 AV 星级=输出;用 bot 跟踪 star 非 read_star 旁路 |
| [0099](0099-deploy-position-pref.md) | deploy 按角色前后台属性选排(替 0007「前排优先」;5.1.6) | accepted | 2026-08-12 | 角色 position_pref 选排(前→前/后→后),对应排满 fallback;修放错排无效(live 观察 2) |
| [0100](0100-deploy-avatar-mousedown.md) | deploy mouseDown 角色头像 avatar(推翻 D-118b drag 假设;5.1.9) | accepted | 2026-08-12 | mouseDown 立绘不拾取(click 开详情);改 avatar 左上 drag → placed=3/5(D-118b 未 live 验是根因) |
| [0101](0101-equip-wear-comp-key-equips.md) | EquipAll 穿戴接 comp.key_equips 优先(替 naive wearable[0]) | accepted | 2026-08-12 | 穿戴按 target_comp 命脉件优先(equip_fit/decide_supply 已 comp 驱动,动作层补接);不改角色级分配 |
| [0102](0102-spend-mode-drives-economy-score.md) | spend_mode 驱动 economy_score(节点节奏→经济档位;补 0097 剩余) | accepted | 2026-08-12 | _economy_mode_for 映射(saving→interest_first/level→rush_level/allin→adaptive);与 _phase_weights 正交;allin economy-low 由 plane3 we=0.3 处理 |
| [0103](0103-target-matching-full-synergies.md) | target comp 牌归属用全羁绊匹配(治本流派/阵营断裂) | accepted | 2026-08-12 | _card_hits_target(全羁绊∩comp.factions)替 card.faction in target.factions(只阵营);流派角色(艾丝妲/椒丘)commit 后不再被误跳 → DOT 凑得出 2DOT;8 处统一 |
| [0104](0104-strategy-review-fixes-batch1.md) | 策略 review 修复批次1(反甲白厄死comp/蒙特卡洛concentration/卖路径护target) | accepted | 2026-08-12 | 反甲白厄 factions 空(白厄无阵营,毁灭是命途非阵营)+防回归测试;蒙特卡洛补_concentration_delta(口径统一);卖路径加target_comp护核心(commitment贯穿) |
| [0105](0105-select-comp-acq-narrow-board-penalty.md) | select_comp acq 收窄 + board penalty 加重(治 acq 主导 spread;P1 弱根因 part1) | accepted | 2026-08-12 | acq 乘子 0.15+0.85p→0.5+0.5p(方差减半);board 全不匹配 ×0.7→×0.3(重罚);减 acq 主导选 board 不支持 comp;part2(board梯度+form加法)ADR-0106 |
| [0106](0106-strategy-review-fixes-batch2.md) | 策略 review 修复批次2(W_BOSS死重/character_priority三重/star钩子漏bench) | accepted | 2026-08-12 | W_BOSS 0.10→0(死重让W_PROG,boss机制未接通);character_priority 去买候选*2(char_quality一处计);star钩子查session.tracked_bench_chars(修漏bench 2星);#5动态权重+#6牌池acq下批 |
| [0107](0107-comp-score-dynamic-weight.md) | comp_score 动态权重(*_fit无数据返None+归一;治死重常量地板;review#5) | accepted | 2026-08-12 | *_fit无数据返None+weighted_mean动态归一(权重重分配给有数据项);W_BOSS复位0.10(撤销0106 stopgap,无数据自动剔除);附带修maybe_pivot target=None误用gap检查;#6牌池acq仍留 |
| [0108](0108-strategy-review-fixes-batch3.md) | 策略 review 修复批次3(shop_faction_seen死数据/difficulty_phase per-plane bug/target_committed *9) | accepted | 2026-08-12 | 删shop_faction_seen(0092改理论概率后的尸体,无评分读);difficulty_phase用全局elapsed判早期(位面内round_num循环致plane2/3误判);target_committed轮次*9→*6(与_elapsed_rounds一致);#6+次优剩余仍留 |
| [0109](0109-pool-copies-canonical-27-9.md) | 牌池副本数定案(1/2费=27可升4星/3/4/5费=9;弃V4.2银狼档) | accepted | 2026-08-12 | POOL_COPIES placeholder9→27/27/9/9/9(3合1决定,均3倍数;27=可升4星;V3.7必修二+用户确认);弃V4.2银狼档30/25/18/10/9(含非3倍数,搜索摘要编造);doc牌库有限升确定机制;解锁#6牌池acq数据 |
| [0110](0110-acquirability-pool-aware.md) | acquirability 牌池感知(P(≥1张)扣1/v+held副本消耗;review#6) | accepted | 2026-08-12 | acq=min核心[1-_refresh_dist超几何P(0)];修漏÷v(特定角色<该费用)+扣held副本(牌库有限,用户根因);_held_base_copies从bench+deployed折基础副本(3合1);NPC消耗c=0保守待核;select_comp乘子0.5+0.5acq不变 |
| [0111](0111-sell-refund-cost-based.md) | sell_refund cost-based(1星cost/2星3c−1/3星9c−1;用户提醒卖出金币重要) | accepted | 2026-08-12 | 旧SELL_VALUE占位连1星都没按cost→弃;sell_refund(star,cost)=cost×合成倍数,star≥2再−1手续费;1星cost🟢权威/2星3c−1用户印象+修§2矛盾/3星9c−1推测待hook核;_bench_char_cost查CHARACTERS.cost;hook验证法=拖起来看出售区价格(无损) |
| [0112](0112-read-star-shape-circularity.md) | read_star 形状过滤(area100+圆度>0.55;治装饰误判,对新角色鲁棒) | accepted | 2026-08-12 | read_star 装饰误判(立绘库6/71+丹恒1读2);area100修小装饰(6→3)剩3大装饰area重叠金星;加圆度>0.55(金星五角星0.57-0.65 vs 装饰<0.55)→立绘库0误判;形状过滤对新角色鲁棒;hook/_reconcile/star_achievement/acq全受益 |
| [0113](0113-read-star-triple-criteria.md) | read_star 三联判据(a>120+circ>0.45+aspect0.85-1.15;迭代0112治实战金星漏检) | accepted | 2026-08-12 | 0112纯circ0.55漏实战金星(circ实测0.52-0.65非0.57-0.65;备战栏-2 a142 circ0.52被误漏→2星读少→hook采不到2星死锁);多槽形状分析:金星aspect0.89-1.06近方vs装饰aspect>1.15/<0.85;三联判据替纯circ(area滤赛飞儿a108+aspect滤长条+circ放金星0.52);立绘库0误判+实战金星全过+合成多星gap≥3读对(紧贴gap<3连通局限待2星样本) |
| [0114](0114-read-star-tm-v-filter.md) | read_star TM模板匹配+V>150滤暗金衣服(迭代0113;纠正0112/0113五角星→四角星) | accepted | 2026-08-13 | 轮廓法对2星紧贴(连通a>600漏)+前排衣服淹没(area1279)结构性失效;V>150滤暗金衣服(金星自发光高V vs 衣服古铜金暗)+单尺度TM四角星模板各星独立(治紧贴);立绘库0/71+前排-3/备战-4 2星读2;后排-3 gap特小NMS合并读1=已知局限(offline旁路,xfail跟踪,live走bot tracking不受影响) |
