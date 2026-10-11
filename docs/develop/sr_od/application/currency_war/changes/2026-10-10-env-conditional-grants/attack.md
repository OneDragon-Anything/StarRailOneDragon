# 环境条件发放 迭代设计·对抗审查报告(第三轮·定点复核)

> 审查对象:本目录 README.md / design.md / landing.md / details/env-conditional-grant.md 当前修订稿(按第二轮报告修法修订后)。
> 核验基准:第二轮报告(本文件上一版)指认的 N1–N4 逐处;范围 = 四处定点闭合核验 + 修订交互快攻(仅第二轮触碰段),不重攻全篇。代码按符号直查,本轮新核验 9 组代码事实,出处逐条内嵌。

## 一、结论

**有条件通过(第三轮)——距定稿差 2 处一句话级微修,修后免审定稿**。

第二轮指认的 N1–N4 **四处全部闭合**(逐处对文对码见 §二):N1 三处旧口径按修法逐字落地且无第四处残留;N2 披露段重写后与代码链三环逐点吻合(后果/频率/告警条件均如实);N3 回调签名三方一致、先例属实;N4 过程号与本地路径指针零残留。但修订交互快攻在触碰面内发现 **2 处【低】级 N3 修订传播尾巴**:

- **N5【低】**:design §2 第 5 条(系统级变化,design:34)调用形态仍写三参 `on_diamond_acquired(gs, 装备名, sig)`,与同节契约「回调写法」(design:44「入参不传 sig」)及 details §4 两参签名(design:69 对应的 details:69)直接矛盾——R2 N3 修法清单只点名 design:44 与 landing 3.3,design:34 成漏网(与 N1 同性质的「修订传播不全」,且 :34 所在的 §2 正是本轮触碰面);
- **N6【低】**:landing 3.3 行为对照判据(landing:44)枚举「sig 写死 logic_sig('sim:env') 单形态」未带「触发函数」限定词、回调 sig 形态零明文——R2 N3 修法「design:44 与 landing 3.3 同步一句」的 design 侧已落完整句,landing 侧未落(判据头「行为对照 details §5 sim 部分」间接覆盖,非矛盾,但落地者只读括号枚举时对回调写无 sig 判据,存在把单形态误推广到回调三写的误读面)。

两处均为定点文本微修、修法唯一无歧义(见 §三),修订后**免审定稿**(无需第四轮;本报告即为 R2 预告的定点复核轮,复核结论 = 修复合格 + 附 2 个尾巴)。

## 二、N1–N4 闭合核验表

| 编号 | R2 指认 | 核验结果 | 核验依据(文本/代码定位) |
|---|---|---|---|
| **N1**【中】 | F1 修复传播不全:三处旧「两调用点/补给缺口顺手闭合」口径残留 | ✅ **闭合,无第四处残留**。①②③ 均按修法逐字落地,且与「supply 零改动」契约面全面互洽(详见下三行) | 修法原文 = R2 N1 修法①②③ |
| N1-① | design:5(§0 迭代目标)补后注 | ✅ 现文:「(sim 侧补给宝钻的既有上限缺口顺手闭合——**修订后调整:补给不采纳回调,该缺口不在本迭代闭合,见 §2 第 5 条**)」——裁定原文保留 + 修订后注,先读到裁定即读到推翻,读序风险消除;同行 T-5 与 `.debug/progress` 路径指针已删(N4 联动,见 N4 行) | design:5 |
| N1-② | design:17(§1 解决到哪)改「唯一调用点」 | ✅ 现文:「宝钻回调 = kernel 函数(唯一调用点 = sim 深井发放路径;supply 不采纳,见 §2 第 5 条)」——与修法②逐字同义 | design:17 |
| N1-③ | details:8(问题与约束·回调边界)改「唯一调用点」 | ✅ 现文:「回调 = sim 专用,唯一调用点 = 深井发放后(supply 不采纳回调,见 §5)」——与修法③逐字同义 | details:8 |
| N1-互洽 | 与 design §2 第 5 条 / 契约·回调边界 / details §5 / landing 3.3 互洽 | ✅ 六方互证:design:34「supply 路径零改动,钻类型建模另批」、design:43「回调 = sim 专用,仅深井发放路径调用」、details:83「supply 路径零改动」、landing:12(3.1 边界「不含 supply 采纳」)/:38(「补给宝钻不采纳回调……supply 路径零改动」)/:46(「supply 路径零行为变化……不采纳回调」)。grep「顺手闭合/两处调用/两个调用点/补给宝钻采纳」全目录:设计文档仅剩 design:5 带后注的裁定原文与各处「不采纳回调」否定形态,肯定形态零残留(attack.md 历史叙述不算) | grep 全量;design:5/17/34/43;details:8/83;landing:12/38/46 |
| **N2**【中】 | F2 披露段后果失真:洗白实为 logic 源真失配 → 安灯停机,非「临时缺口自愈」;频率低估 | ✅ **闭合,披露如实**。details:60 按修法①重写(标题即「同窗洗白形态披露(后果 = 安灯停机,显式接受)」),逐点对照代码链三环全吻合(见下) | details:60;代码链三环 |
| N2-披露与代码链环1 | 「同窗确定性 equips 写会把字段来源翻 logic——典型 = 补给装备腿(**任意补给选定都走此腿,不限带钻**)」 | ✅ 属实。装备腿 = `owned = list(gs.equips.value or []); owned.append(item); gs.write_logic(gs.equips, owned, produced_by=_PRODUCER, evidence=f'owned[{item}] +1', sig=sig)`(pick_supply.py:101-104)——读现值追加回写、`write_logic`(非 logic_rand),norm_item 非空即走,零钻类型判别;洗白后字段 evidence 前缀 = `owned[...`(与 R2 附带裁定「豁免查表第三维用字段现 evidence、env_grant 前缀永不命中」一致) | kernel/cw_action_report/pick_supply.py:98-104 |
| N2-环2 | 「下一 heavy 帧观察对 logic 源**真失配**:缺陷行 + `[cw!]` 告警 + 安灯停机 flag(生产 = 截图留证 + 停机),值由观察采新」 | ✅ 属实。`observe()` 对 `source == 'logic_rand'` 差异只落 `logic_rand_outcome` 台账行静默采新(cw_game_state.py:2794-2802);对 `source == 'logic'` 差异经 deployed/board 吸收器(equips 均不命中)→ `_route_logic_mismatch`(:2803-2814,传 `logic_evidence=target.evidence` = 洗白写端前缀);豁免查表为**字段现 evidence** 前缀比对(cw_mismatch_policy.py:66-91),注册表 `EXEMPT_REGISTRY: dict = {}` **为空**(:63)→ 真失配;安灯钩子生产装配 = 截图留证 + 停机 flag(cw_mismatch_policy.py:15-16、:94-97);覆盖照常采新与安灯同时发生(cw_game_state.py:2815) | cw_game_state.py:2792-2817;cw_mismatch_policy.py:15-16/63/66-91/94-97 |
| N2-环3 | 「深井 5 连胜结算的**下一节点凡为补给即触发**洗白,频率不低」 | ✅ 属实。结算完成判据白名单 `SETTLE_COMPLETION_ANCHORS` 含 `('货币战争-补给', '标识-补给阶段')`(cw_screen_battle_wait.py:86-92,:88)——结算完成后到达补给节点即选卡,装备腿必写 equips → 洗白触发,不限带钻 | operations/cw_screen/cw_screen_battle_wait.py:82-92 |
| N2-告警条件 | 「**告警仅在猜值与实读不符时发生**(OCR 假阳等),猜值正确则观察值与逻辑值一致、无失配」 | ✅ 属实。三分流入口条件 = `target.value != value`(cw_game_state.py:2794-2804),等值不进任何失配分支;接受条款「续跑即愈(done 已标记不重发,幻影值已被观察覆盖)」与 done 同窗先行追加(details §3 第 6 序)+ 观察赢覆盖(:2815)一致 | cw_game_state.py:2794-2804/2815;details:55 |
| N2-失真词清除 | 修法要求删「临时缺口/整表覆盖恢复/需带钻补给」三处失真表述 | ✅ 零残留。grep 三词组:设计文档全净(仅 attack.md 历史叙述)。附带确认:details:5/:62 与 design:22 保留的「整表覆盖纠偏」均为 **logic_rand 发放情形**(恢复局/随机态发放)的准确表述,非洗白段残留,与 :2794-2802 的静默采新行为一致 | grep 全量;details:5/60/62/64;design:22 |
| **N3**【中】 | 回调三写 observe 的 sig 形态与 sim 单 sig 接线矛盾 | ✅ **闭合(触发面/dtl 面);残留尾巴 → N5/N6**。回调签名三方一致、先例属实、触发函数不受影响(见下);design:34 三参残留与 landing 判据缺限定分列 §三 N5/N6 | details:69/73/82;design:44 |
| N3-签名 | 修法推荐形态 `on_diamond_acquired(gs, equip_name: str) -> None`(无 sig 参) | ✅ details:69 签名两参带返回注解,与先例同形 | details:69 |
| N3-三方一致 | design 契约 / details §4 / §5 sim 调用一致 | ✅ 三方逐字一致:「sig 由回调内部自构 obs 族(如 `obs_sig(group_id='sim:env-diamond')`),入参不传 sig」(design:44 = details:73,连示例 group_id 都相同);details:82 调用两参「`on_diamond_acquired(gs, 返回名)`(回调内构 obs 族 sig,见 §4)」 | design:44;details:73/82 |
| N3-先例 | `_on_supply_picked` 内构 obs 族 sig | ✅ 属实。`def _on_supply_picked(self) -> None`(无 sig 参)→ `self.gs.observe(self.gs.diamond_count, cur + 1, ..., sig=obs_sig(group_id='sim:diamond'))`(cw_sim_backend.py:1093-1101) | cw_sim_backend.py:1093-1103 |
| N3-渠道校验 | 「observe 渠道校验只收 obs 族,复用调用方 logic 族入参首笔即炸」 | ✅ 属实。`observe()` 首行校验 `_validate_sig(sig, ('obs',))`(cw_game_state.py:2792) | cw_game_state.py:2792 |
| N3-触发函数不受影响 | 触发函数两写 sig 写死单形态(live = logic_hook 族 / sim = `logic_sig('sim:env')`)保留 | ✅ 保留且三方一致:live = logic_hook 族 group `'battle-wait:env-grant'` actor `CwScreenBattleWait`(design:42/details:81/landing:25);sim = `logic_sig('sim:env')`(design:42/details:82/landing:44);`write_logic`/`write_logic_rand` 渠道校验收 logic_action/logic_hook 族(R2 F5 已核,cw_game_state.py:3058/3095,未变) | design:42;details:81-82;landing:25/44 |
| **N4**【低】 | 跨迭代过程号残留(R5×1、T-1×3、T-5+`.debug` 路径×1) | ✅ **闭合,全净**。grep「T-1/T-5/R5/.debug/ore-conditional」设计文档零残留(仅 attack.md 历史叙述):details:7「晶矿通道 done 域同形先例 = kernel/cw_ore_channel.py」(R5 字样清除,修法给的持久指针选项落地);design:40「投影审计行(完备性锁强制,晶矿迭代同款先例)」、details:22「沿晶矿通道先例 = kernel/cw_ore_channel.py 与 cw_game_state.py 三域落地形态」、details:27「先例 = cw_game_state.py 晶矿三域审计行」(T-1×3 全改持久指针);design:5「源迭代(invest-effects-calc)深井角斗场机制接入外溢」(T-5 与 `.debug/progress` 路径已删,「外溢」语义自足;迭代名保留属 R2 修法未要求清除的范围,且为 changes/ 平级目录名引用,非过程号) | grep 全量;details:7/22/27;design:5/40 |

## 三、新发现(仅限第二轮触碰面)

### N5【低】design §2 第 5 条调用形态三参残留(N3 修订传播尾巴)

- **位置与原文**(design:34,系统级变化第 5 条):「返回非 None 且装备为宝钻 → 调 **宝钻获得回调** `on_diamond_acquired(gs, 装备名, sig)`(diamond_count +1、deploy_cap = level + 拥有财富宝钻数、back_layout = min(9, 现值+1),observe 写 = sim 世界事实)。」
- **矛盾对象**:同节契约「回调写法」(design:44「**sig 由回调内部自构 obs 族**……**入参不传 sig**」)、details §4 签名 `on_diamond_acquired(gs, equip_name: str) -> None`(details:69)、details §5 两参调用(details:82)。括号内三域公式(F1-③ 核过)仍与 details §4 一致,唯独调用形态带 sig 参。
- **成因**:R2 N3 修法清单 = details §4(主体)+「design:44 与 landing 3.3 同步一句」;design:34 不在清单内,修订改签名契约时未回扫 §2 第 5 条——与 N1 同性质的传播不全(且 R2 触碰面含 design §2,本轮快攻面内)。
- **危害**:实现者按总纲「系统级变化(读一遍知全貌)」照 :34 传三参 → 撞 details 两参定义 TypeError;或反向给回调加回 sig 参 → 复活 R2 N3 的「照字面复用 logic 族 sig 首笔 observe 即炸」。契约层(:44)按「总纲定死,各详设不得另行演化」优先,危害止于读者困惑,故定【低】。
- **修法**(一处):design:34 调用形态改「`on_diamond_acquired(gs, 装备名)`(sig 由回调内构 obs 族,见本节契约『回调写法』)」,删「, sig」。

### N6【低】landing 3.3 判据缺回调 sig 语义(N3 修法「同步一句」landing 侧未落)

- **位置与原文**(landing:44,3.3 完成判据):「行为对照 details/env-conditional-grant.md §5 sim 部分(触发在 streak observe 后;**sig 写死 logic_sig('sim:env') 单形态**;回调三写 diamond_count/deploy_cap/back_layout;宝钻裁决只认财富宝钻)」——「sig 写死」项无「触发函数」限定,回调 sig 形态在 3.3 全节零明文。
- **判定**:非矛盾——判据头「行为对照 details §5 sim 部分」可解析,而修订后的 details:82 已含「(回调内构 obs 族 sig,见 §4)」指针,按判据执行不会漏。但 R2 N3 修法明写「design:44 与 landing 3.3 同步一句」,design 侧落了完整句、landing 侧未落任何回调 sig 句;括号枚举是落地者的重点抽查面,单形态枚举项在回调 sig 形态反转为内构 obs 族后产生误读面(把「单形态」推广到回调三写 → observe 渠道炸,落地测试即暴露,危害自愈但返工一轮)。
- **修法**(半句):landing:44 枚举项改「触发函数两写 sig 写死 logic_sig('sim:env') 单形态(回调三写内构 obs 族 sig,见 details §4)」。

**快攻确认(无新矛盾,记录备查)**:①design §0 后注 + T-5/.debug 清除、「零回调」尾句与 :43 一致;②design §1 唯一调用点句;③details 问题与约束回调边界(:8)、§3 披露三段(:60 重写如实;:62 恢复局/:64 OCR 段未被本轮破坏,其「整表覆盖纠偏」属 logic_rand 情形准确表述)、§4 签名、§5 sim 两参调用;④landing 3.3 :38「返回非 None 且装备为宝钻 → 宝钻回调」与 details:82「返回非 None → 调回调(内早退兜底)」在现登记表(唯一装备名 = 财富宝钻)下行为等价,非矛盾;⑤「宝钻裁决只认财富宝钻」的证伪路径仍靠回调直调负例单测(R2 F3 附注维持,不重复展开)。

## 四、定稿试读(修 N5/N6 后逐阶段)

- **3.1 kernel 条件发放与登记表——可开工**。回调签名两参定型(N3)、done 四件套持久指针齐(N4)、条件矩阵七序与登记表三校验不变(R2 已核);N5/N6 不涉 3.1 文件面。
- **3.2 live 接线——可开工**(本轮修订未触碰;sig = logic_hook 族、streak_after None 口径、调用点次序三方一致维持)。
- **3.3 sim 接线——N5/N6 微修后可开工**。数值对照判据(diamond_count +1、cap = level+1、back_layout +1 min9、同 seed 重放)现模可达(R2 F1-③ 维持);supply 零行为变化判据与 `_on_supply_picked` 零改动现状对齐;N6 修后判据枚举对回调写有明确 sig 口径。
- **末阶段正本更新——可执行**(五路径清单未动)。

**总结论**:N1–N4 闭合成立,第二轮修法合格;N5/N6 为同一根(N3 修订传播清单外回扫缺失)的两个一句话级尾巴,修法唯一无歧义——**按 N5/N6 修法改完即定稿,免第四轮审查**(本轮即为 R2 预告的定点复核轮,此结论即终审结论,修订方按 §三修法执行后无需再送审)。
