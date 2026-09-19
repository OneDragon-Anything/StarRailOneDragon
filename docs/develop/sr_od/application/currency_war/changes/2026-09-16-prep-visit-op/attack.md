# 设计对抗报告:备战访问编排 op 化

> 审查依据:`docs/develop/harness/iteration-design.md` §7(攻击三核)+ §5(写作硬规则三条)。全部结论基于对被引文件与真实代码的逐处核对,非设计转述。

## 结论

**打回**——方案 4 的「行为等价」申报被 op 入口清场注册表自身声明与实测病例证伪(F1,致命),叠加跨帧发射活性未证(F2)、仲裁意图形态与判定单一源未钉死(F3)、遥测载体与正本清单不完备(F4);F1–F4 修订到位前未达定稿门槛,F5–F7 随批补齐。

## 发现清单

### F1 浮层闸退役的「行为等价」申报不成立
- **位置**:design.md §2 方案 4(L28)、行为变化申报 L33;landing.md 3.3(L32)。
- **问题**:三层矛盾。
  1. **清场覆盖面被注册表自身声明限死**:op 入口清场「只收无决策语义的弹窗/面板……投资环境/投资策略/选择伙伴/盛会之星/祈愿试炼等交互 overlay 同理,不进派生集」(cw_screen_prep.py:162-165,注册表本体 :166-168)——而旧闸锚表扫描恰恰覆盖投资策略浮层(第十五局实雷的当事浮层,cw_loop.py:1929-1934)。清场 ≠ 旧闸捕获面。
  2. **遭遇选择面板无任何承接路径**:切屏竞态实测病例,旧闸 OCR「遭遇其」兜底专用(cw_loop.py:1945-1954「双锚仍可见但板面槽区被面板覆盖 → 拖拽落进面板覆盖的中部槽区」);该面板非弹窗、无关闭钮、非独立建档屏,清场注册表管不到。新形态下 9 拖全空挥(placed=0)事故形态重新暴露。
  3. **「弹窗挡按钮 → 点击不落地」语义错误**:点击落在浮层上不是「未落地」,会误触浮层选项(与拖拽落空同机制);start-battle.md §3-3 零判效只覆盖「点击未落地/被拒不重发不计数」,不覆盖「落在错误目标上」。
  - **统一执行器「屏态复验」不构成旧闸保护载体**:双锚模板穿透命中是浮层在场的既证形态(cw_loop.py:1882-1884「单锚在 overlay 半开帧可从底层透出命中」、1929-1934「双锚模板穿透命中」)——纯双锚复核对浮层在场恒放行。设计未申报复验扩面(双锚 + 锚表扫描 + 遭遇 OCR)。
- **严重度**:致命(方案 4 的行为变化申报以「对外行为等价:弹窗帧不发射」为承重结论,与实证矛盾)。
- **建议**:二选一写入设计:①执行器屏态复验扩面为「双锚 + 0 系锚表扫描 + 遭遇 OCR」,失败语义沿 readiness_stale_screen 分支;②CwScreenPrep 入口(observe 前)保留浮层在场预检。同时修正行为申报表述。

### F2 跨帧形态的发射活性与「恰一次」等价未证
- **位置**:design.md §2 方案 3(L24)、行为变化申报 L32、关键取舍 3(L43)。
- **问题**:新形态发射条件 = 次帧 armed ∧ 金 ≤ 息线,引入旧形态没有的活性前提:
  1. **发射永不到来的形态存在**:预算闸拦截一切可购时(店无 1 费牌 ∧ 溢出金额 < 最低在售价等;闸拒 = 消费终止非跳过续试,cw_launch_arbitrage.py:107-120),金永不回落 g* → 每帧重发访问意图 → 无发射帧。旧形态仲裁后同帧照发(readiness_battle_launch 无金条件,cw_loop.py:1976),不依赖金回落。「发射恰一次」等价申报在此形态为假。
  2. **新通道无防重开节流**:run_mandate 的 OpenShop 发射节流与开店闩(mandate.py:725 `_emit_open_shop` 节流;:861 S1 闩挡重开;entry.py:922 OpenShop 计入消费面)不辖前置发射位;S1 闩清否 = route_tag 消费(cw_vocab.py:360-371,白名单锁 test_route_tag_whitelist),受限访问意图的 route_tag 值域未定。连访循环无任何节流面。
  3. **次帧 armed 破功未分析**:访问买牌改变承重/计划可用性 → `quality.defer_by_quality` 翻转(cw_launch_admission.py:211-212)→ 破功帧落常规三遍,发射推迟无界;设计「次帧复判再发射」未论证 armed 持续性。
- **严重度**:重要。
- **建议**:补活性论证,或给显式兜底判据(如连续 N 次零消费访问帧后的带内发射条件,零自由参数口径);申报受限访问意图与节流/开店闩/route_tag 的关系。

### F3 仲裁意图的词表形态与判定单一源未钉死
- **位置**:design.md §2 方案 3(L24)、接口契约 L39;landing.md 3.2(L26)。
- **问题**:
  1. **意图形态未定**:「OpenShop 意图携带预算闸」(方案 3)与「携带受限标记」(接口契约)措辞不一;新字段/消歧子类/新类型三形态未选。词表两先例并存:OpenShop.read_only 字段形态(cw_vocab.py:807-817——**带参意图并非首例**,前提修正)、LevelUpShop 消歧子类形态(cw_vocab.py:513-529)。若走子类形态,漏登记 CW_ACTION_TYPES = 在册事故形态「执行面 validate 拒未知类型,动作从未真正执行」(cw_vocab.py:825-829 OpenTome 教训)。sim 适配器映射义务(op-layer.md §2.5 两适配器同批给映射)与 action_key 幂等粒度影响(闸值入键,cw_vocab.py:842-860)均未提。
  2. **「金 > 息线」未钉判定单一源**:kernel 明令「两面直调 in_launch_spend_zone,禁各自内联 `gold > g*` 字面量式」「新增消费点须回金出口族 DESIGN §5 对账表」(cw_economy.py:315-320)。设计措辞诱导内联实现;landing 3.2「断言经 cw_economy 读口」未区分 in_launch_spend_zone(正解)与 saturation_line 手拼(违禁形态)。
  3. **预算闸判定核未点名**:闸语义(花后金位 ≥ g*、P70 Δ息=0 形、拒因恒 GATE_BLOCKED_REASON)单一源 = kernel `launch_arbitration_gate`(cw_launch_arbitrage.py:107-120;模块头 :19-24「判定语义单一源……两面直调禁字面量散写」)。设计只写「预算闸 = 息线」,第二实现风险在册(金出口族红线 1/5)。
- **严重度**:重要。
- **建议**:接口契约钉死四项:意图形态(选型 + CW_ACTION_TYPES 登记面核查)、域判定 = in_launch_spend_zone 直调、闸 = launch_arbitration_gate 复用、route_tag 值域。

### F4 遥测载体与正本更新清单不完备
- **位置**:design.md §2 方案 4/5;landing.md 3.3 + 正本更新清单(L54-59)。
- **问题**:
  1. **[cw-op] 第三载体行去向未定**:outer_loop.md:112 明文「仲裁触发商店访问为包装外唯一补行点(op='发射帧仲裁商店访问',三载体口径见 session.md 载体表)」。新形态访问在 CwScreenPrep act 内执行、无 dispatch 包装 → 零行,复盘按行重建误归——正是 ADR-0584 §5.1 立行要治的病灶(cw_loop.py:559-562)。该行保留(改由 op 内落,行契约是什么)还是退役(误归口径申报)未定。
  2. **正本清单缺两处现役载体正本**:`flow/session.md` 载体表(三载体口径);`screens/shop.md` 的「发射帧仲裁受限访问」与 spend_gate 行(shop.md:10,45)。
  3. **cw4_counters 分键族新写点未申报**:launch_arbitrage_* 7 键(cw_launch_arbitrage.py:62-81)+ readiness_stale_screen/overlay_hold/launch_fail/giveup(cw_loop.py:1955-2044)+ 质量闸分键实机 sink(LAUNCH_QUALITY_* 键「写点 = engine_p1 + cw_loop 达标臂判定位」,达标臂写点随臂退役,cw_launch_admission.py:49-55)+ abandoned_launch defect。分键零静默是全仓纪律,宿主迁移后写点归属不申报 = 判读面静默失明。
- **严重度**:重要。
- **建议**:正本清单补 session.md/shop.md 两行;设计补「遥测载体迁移对照表」(旧分键 → 新写点/显式退役申报);[cw-op] 行去向写入 3.3 判据。

### F5 交回契约两处实现者需拍板
- **位置**:design.md §2 方案 1(L20)、接口契约 L37;landing.md 3.3(L39)。
- **问题**:
  1. **outcome=fail 而发射已置位的形态未定**:op 内节点重试中发射成功、后续失败 → execute 返回 fail;现行战斗窗置位在 on_result 的 ok 分支(cw_loop.py:2160-2172),契约读点照搬现结构会漏置窗。帧锚 `_frame_in_battle_window` 第二入口可兜底(cw_loop.py:2193),但该层依赖未申报;连续失败 round_fail 路径同问。
  2. **launch_fired 置位机制与「执行无返回」规范的接口未定**:动作 op「机械执行无成败回执」(op-layer.md §1.2);统一执行器返回 (ok, detail),五段 act 段如何取得该 bool 并置位(StartBattle 经注册表 `action_op_class_for` 分派 vs 特判路径,cw_screen_prep.py:2303,2334)未定。
- **非问题部分**:CwScreenPrep 每次派发新实例(cw_loop.py:1461,2183),`launch_fired` 实例属性无跨帧残留——攻击方向 1 的「新实例」子问不成立。
- **严重度**:次要。
- **建议**:契约补两句:置位读点 = on_result 内、先于 ok/fail 分支(fail 且 fired 仍置窗);置位载体 = 执行器返回经 act 的 StartBattle 特判段写入。

### F6 统一执行器契约把三套异宿主语义捏合未拆
- **位置**:design.md 接口契约 L38;landing.md 3.1(L6,L12)。
- **问题**:「内部承载屏态复验/重发/失败计数/连败停机全语义」未拆解:①屏态复验与部署原子序的执行序(现序 = 复验 → G1 显影 → 部署 → 出战,cw_loop.py:346-411;复验内迁执行器后序变,未申报);②「失败计数」是两个东西——C1 三振弃短路计数 `_cw_readiness_fail_n`(loop 侧状态;op 面已无「短路可弃」语义,活/死未定)与 `_start_battle` 连败停机(start-battle.md §1);③调用面标记的值域与逐面行为差矩阵(复验/部署序/闩/计数/停机 × op 面/恢复局面面/策略终点面)未列。
- **严重度**:次要。
- **建议**:3.1 开工前,设计先给逐面行为差表,替代「全语义」一句概括。

### F7 前置发射位插入位次与实体面优先级未定
- **位置**:landing.md 3.2(L19「骨架 pass 之前」;L21 文件面「entry/mandate 任一契合位」)。
- **问题**:①「任一契合位」= 酌情措辞,违写作硬规则 2(实现者无需再设计);②emit 编排 ① 实体面「控制流与 overlay 切换优先于三遍」(entry.py:437-441)——armed 帧恰逢 obs.boxes/spheres 时,前置位在实体面前(不收箱/晶矿直接发射/访问)还是之后(先收晶矿)是行为语义选择,未定且未进行为变化申报;③「骨架 pass 之前」在 ①′/②/③ 之间仍有多个可插槽,§9.6 位次「动作链之前」不足以唯一定位。
- **严重度**:次要。
- **建议**:钉死为 emit 入口(① 之前)或 ① 之后,行为变化申报表加一行。

## 依据核验表

| 设计声称的出处 | 核验 | 备注 |
|---|---|---|
| op-layer.md §2.4 五段生命周期 | ✓ | L94-111;CwScreenPrep = 生命周期原型 |
| op-layer.md §2.6 判据在策略器 | ✓ | L124「判据在策略器」 |
| op-layer.md §2.5 词表两适配器同批 | ✓ | L115;设计未处理该义务(见 F3) |
| start-battle.md §3 执行器语义/零重试零判效 | ✓ | §3-3;「零判效不覆盖误触」构成 F1 依据 |
| start-battle.md 战斗窗置位归外循环 | ✓ | §3-1 |
| start-battle.md 免战子态 | ✓ | §3-4,landing 3.1 审计清单含 |
| 14_p1 §9.6 发射位规格/位次/C1 | ✓ | L375-396;armed 当前语义权威 = §11.10(设计引用与增注声明一致,L398) |
| cw_loop.py readiness_battle_launch(屏态复验/失败计数复位) | ✓ | L346-411 |
| cw_loop.py _prep_anchors_hit | ✓ | L414-419;另有仲裁预检调用点 L511 |
| cw_loop.py 发射帧仲裁 | ✓ | L468-650;闸/带内/abort/第三载体行全在 |
| cw_loop.py 交回处理(战斗窗分支内副作用) | ✓ | L2165-2172(ok 分支)/L2104-2105(锁定分支) |
| cw_launch_admission.readiness_launch_decision 签名与语义 | ✓ | L215-271;(bs, comp, *, line_members) → dict(armed/auth_basis/admission/quality/quality_eval_error);kernel 不动可行 |
| cw_vocab.py CW_ACTION_TYPES 闭集 | ✓ | L830-839 |
| StartBattle 无字段 dataclass(词表现成) | ✓ | L820-822;entry.py 终点 L205-206, L944 |
| OpenShop 形态 | ✓(前提修正) | **已带 read_only 字段**(L807-817),「带参意图 = 无先例下的契约变更」前提不成立;契约变更面未处理仍成立(F3) |
| entry.py decide 三遍编排/前置位可行 | ✓ | L432-443 编排①-⑥;L454 emit 内已有 bs = board_state_of(session),金/判定材料齐备 |
| cw_economy 息线 g* 派生存在 | ✓ | saturation_line L283-285 / cap_resolved_of_session L253-280 / in_launch_spend_zone L306-325;附禁内联条款(设计未引用,F3) |
| 「两套点出战执行并存」 | ✓ | cw_loop 面 vs prep_actions._start_battle + StartBattleOp(start-battle.md §1/§6) |
| 「达标臂四段 ≈150 行」 | ✓ | L1887-2045 ≈ 160 行,量级成立 |
| 「仲裁切屏后复验弃射落守卫链,次帧发射」 | ✓ | outer_loop.md:90 与 cw_loop.py:1976-2012 一致 |
| 「Op 清场 = CwScreenPrep 既有职责」 | ✓(覆盖面存疑) | _clear_entry_overlays/_clear_prep_cards 在(cw_screen_prep.py:2478-2524),但注册表显式排除交互 overlay(F1) |

## 攻击方向判定表

| # | 攻击方向 | 判定 | 一行理由 |
|---|---|---|---|
| 1 | 交回契约生命周期 | **是问题(收窄)** | 新实例语义无残留(非问题);fail-形态置窗与置位机制未定 = F5,真实但非致命 |
| 2 | 仲裁意图的词表形态 | **是问题** | 形态三选一未钉 + 域判定/闸单一源未点名(F3);前提修正:OpenShop 已带字段,带参非首例 |
| 3 | 浮层闸退役等价性 | **是问题(致命)** | 清场覆盖面被注册表自身声明限死、遭遇面板零承接、「点击不落地」语义与实测矛盾(F1);屏态复验对穿透浮层恒放行,非保护载体 |
| 4 | 次帧持续性 | **是问题** | 闸拦一切时发射永不到来 + 新通道无节流/闩 + armed 破功未分析(F2) |
| 5 | 载体行去向 | **是问题** | 第三载体行去向未定,正本清单缺 session.md/shop.md,cw4_counters 分键族写点未申报(F4) |
| 6 | 试读 landing 3.1/3.2/3.3 | **是问题** | 拍板点:F5(置窗时机/置位载体)、F6(复验序/两套计数归属/逐面矩阵)、F7(插入位次/实体面优先/「任一契合位」措辞)、F3(意图形态与闸源) |
