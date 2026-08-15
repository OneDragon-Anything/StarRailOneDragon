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
| [0100](0100-deploy-avatar-mousedown.md) | deploy mouseDown 角色头像 avatar(推翻 D-118b drag 假设;5.1.9) | ↺ 推翻0120 | 2026-08-12 | mouseDown 立绘不拾取(click 开详情);改 avatar 左上 drag → placed=3/5(D-118b 未 live 验是根因) |
| [0101](0101-equip-wear-comp-key-equips.md) | EquipAll 穿戴接 comp.key_equips 优先(替 naive wearable[0]) | accepted | 2026-08-12 | 穿戴按 target_comp 命脉件优先(equip_fit/decide_supply 已 comp 驱动,动作层补接);不改角色级分配 |
| 0124 | 买牌 tempo 例外:未成型 commit 放行板直接增强散牌 | [0124-buy-tempo-exception.md](0124-buy-tempo-exception.md) |
| 0125 | 板上同角色重复买入禁令(死钱防沉) | [0125-no-dead-money-duplicate-buys.md](0125-no-dead-money-duplicate-buys.md) |
| 0126 | 节点等级计划 live 校准(A8 更高人口) | [0126-level-plan-live-calibration.md](0126-level-plan-live-calibration.md) |
| 0127 | 策略 review round-3 修订:H1-H4 | [0127-strategy-review-h1-h4.md](0127-strategy-review-h1-h4.md) |
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
| [0114](0114-read-star-tm-v-filter.md) | read_star TM模板匹配+V>150滤暗金衣服(迭代0113;纠正0112/0113五角星→四角星) | accepted | 2026-08-13 | 轮廓法对2星紧贴(连通a>600漏)+前排衣服淹没(area1279)结构性失效;V>150滤暗金衣服(金星自发光高V vs 衣服古铜金暗)+单尺度TM四角星模板各星独立(治紧贴);立绘库0/71+各位置2星(前/后排/备战栏)读2(thresh0.50:原0.55漏后排-3第2星val0.511);无已知2星局限(3星待live样本) |
| [0115](0115-read-star-circ-relax-bench9.md) | read_star circ 阈值放宽 0.35→0.25(备战-9 边槽假阴;迭代0114) | accepted | 2026-08-13 | 备战每槽覆盖发现备战-9 边槽飞霄2星读1(备战-4 读2);根因 circ>0.35 切在真金星 circ 分布内(实测0.34-0.50,备战-9 渲染到0.34被误拒);放宽到0.25(立绘库0/71不靠circ+全fixture无新FP+备战-9读回2);立绘库0/71守卫升级回归测试 |
| [0116](0116-read-star-thresh-back6-edge.md) | read_star TM thresh 0.50→0.45 解后排-6 边槽第2星漏(迭代0114;真因=紧贴遮挡非缩放,多模板实测无用) | accepted | 2026-08-13 | 各槽覆盖发现后排-6 椒丘2星读1;第2星TM val~0.45-0.50被thresh0.50滤。初稿猜缩放失配→多模板per排根治,**实测推翻**(各排星bbox 17-19px相同,非缩放);真因=2星紧贴遮挡致第2星mask不完整val偏低(第1 0.62-0.69/第2 0.45-0.58)。thresh0.45=真第2星(≥0.45)与噪声(<0.40)分界(立绘库0/71+全fixture无新FP+后排-6读回2) |
| [0117](0117-streak-direction-win-streak-break-interest.md) | streak 方向驱 plan —— 连胜≥2破息保连胜(C 杠杆 3 winning half,R2-4b) | accepted | 2026-08-13 | 连胜≥WIN_STREAK_BREAK_INTEREST(2)→_should_save_for_interest 破息(保连胜>吃息,断连胜亏>利息亏);连败 fold 半已由 HP-gating 覆盖;抽 helper(_saving_for_interest 内联条件)+单测;streak 默认0向后兼容 |
| [0118](0118-buyshopcards-supply-bail-area.md) | BuyShopCards 补给 overlay bail 改 screen_info area(治备战「返回补给阶段」假阳→死循环) | accepted | 2026-08-13 | 全屏 OCR「补给阶段」匹配备战返回按钮文本子串→假阳 bail→Loop 死循环;补给建档后有 标识-补给阶段 area → 移到 round_by_find_area(位置判 [893,120,1027,230]≠按钮[1716,51]);与 Loop 0e dispatch 同源;live 验死循环解除(BuyShopCards 正常 plan) |
| [0119](0119-loop-supply-node-flow.md) | Loop 补给节点流程 —— 点返回补给阶段进补给屏(替 supply 停机 hook) | accepted | 2026-08-13 | 补给节点备战走 BattlePrepCycle→出战 但出战不推进(补给节点无出战打怪,确认补给即完成节点);旧 Loop 无"备战→补给屏"导航。修:备战分支检测按钮-返回补给阶段→点它→下轮 0e RunSupplyNode 选+确认推进(复用已建 RunSupplyNode,只补导航)。替掉 supply 停机 hook(让 bot 真过补给节点);live 验待下补给节点 |
| [0120](0120-deploy-center-drag-unified.md) | deploy 中心拖+hold0 推翻 avatar 假设(DragCwChar 统一拖拽;5.1.9 重诊) | accepted | 2026-08-13 | ↺ 推翻0100:avatar=星标误识(左上小圆非头像)+ 详情=click(mouseUp)非 mouseDown + drag=按下+移动;avatar 偏移+hold1s 正是 ~50% 失败根因(被判长按/click 开详情)。实测中心拖+hold0 即拾取(飞霄✓)。统一抽 DragCwChar.drag_char(中心拖+hold0+验源槽变+retry),deploy/sell/op 全走它;删 4 死方法;后排 back_centers/读全 不硬编码6 |
| [0121](0121-sell-refund-fee-cost-dependent.md) | sell_refund 手续费 cost 相关(1费 exempt;2费+ star≥2 才减1) | accepted | 2026-08-13 | live 实测 2★1费 万敌出售=+3(cost×3,无−1;VLM 读「金币+3」)。用户:1费不减、2费开始减1 → 手续费 cost 相关非纯 star。改 −1 条件 star≥2→star≥2 且 cost≥2(旧一刀切把1费也−1了,错)。1费各星全额退;cost≥2 star≥2 −1。economy §2 矛盾消解(1费免费对)。删 sell-star 停机钩子(售价已验) |
| [0122](0122-battle-prep-idmark-overlay-substate.md) | 备战 id_mark + overlay/子态区分(前台区域被盖;子态独立屏) | accepted | 2
| [0123](0123-prep-director-observation-loop.md) | 备战编排固定序列 → 观察驱动决策环 PrepDirector(decide_prep_action 单步;腾席优先级;P1-P3 迁移) | accepted | 2026-08-14 |026-08-13 | 备战旧只购买经验→overlay 帧透出购买经验也命中备战→撞车。改:备战=购买经验+前台区域+后台区域(前台区域=棋盘前排标签,被中心 overlay 盖→overlay 帧备战缺它不 is_precise);overlay=购买经验+标题(组合);备战-开商店=购买经验+收起;备战-装备详情=无 id_mark(子态)。删测试豁免,测试+live 双确认。crop-OCR 坑:前台区域紧框漏检→放宽给上下文 |
| [0128](0128-user-rhythm-batch1.md) | 用户人玩节奏批次1(连胜不对称/1费集星免费/boss前花完/comp停留D) | accepted | 2026-08-15 | 攻略复查11项小修4项+comp停留语义:streak只计连胜(无连败补偿);cost==1集2★免费(净0);node_type=boss→不攒息+刷cap4;comp显式roll压过node地板(列车停7级D3星姬子,旧冲8) |
| [0129](0129-xp-click-model-and-level-from-xp.md) | 购买经验单击模型(+4XP/击,门槛自动升级溢出结转)+XP分母反推真等级 | accepted | 2026-08-15 | 用户门槛表4/6/20/40/52/72/84+telemetry对拍;LevelUp=单击非整级大金(旧模型高估成本→升级滞后,M15进P2真lv5);read_level启发兜底污染观测→XP反查覆盖+[cw!]留证 |

