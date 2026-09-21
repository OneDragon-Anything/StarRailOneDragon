# 设计对抗审查报告——银狼升星记账迭代（核一·无前提攻击）

- **审查对象**：`design.md`（银狼升星记账迭代设计·总纲，单文档方案，状态：草案）
- **审查标准**：`docs/develop/harness/iteration-design.md` §5 写作硬规则、§7 核一（无前提攻击：符号/路径存在性全量核验、边界完整性、试读、依据标注逐条攻、接口契约明确性）
- **方法**：只读核验。设计引用的每个符号/路径/行号逐一对照代码与文档现值；关键主张对照权威源原文；以实现者视角逐节试读。

---

## 发现

**F1. [major] | design.md §1.2 | 「同名即同档定谳」的依据标注与所引权威源冲突：被引文档把同一问题列为「待实测」，且该口径在 docs/game/ 全域零登记。**
设计 §1.2 称：「同名即同档定谳（口述·权威 2026-09-18，equipment_mechanics §7）：升费后商店只出新费用档、赠送单位只给该档，容器内费用档不同时存在」。核对该权威源：
- `equipment_mechanics.md:157-161` 的 2026-09-18 口述定谳只覆盖一件事——升费腿结果 =「变为下一个费用档的 1 星银狼LV.999」，不含上述三条；
- `equipment_mechanics.md:162-163` 明确把「升费后牌池费用档归属（原档还是新档）」列为**待实测边角**——与设计声称的「商店只出新费用档」方向相反（一个是悬案、一个是定谳）；
- 「同名即同档」「不同时存在」「赠送单位只给该档」「只出新费用档」在 `docs/game/` 全目录检索零命中；该口径目前只存在于代码注释（`cw_screen_yinlang.py:338-339`、`deploy_move.py:13-14`，同样标「口述·权威 2026-09-18」），从未按注释规范登记进被声明为机制单一源的研究文档（`cw_screen_yinlang.py:9-10` 自declared「机制单一源 = equipment_mechanics.md §7」）。
这是 hard rule 1（依据就地标注）要防的事故本体：下游实现批会把「待实测」当「已定谳」消费。设计 §2.0 已有证伪升级路径（「定谳若被实机证伪→升级 per-unit」），说明设计自己也把它当可错假设——但可错假设不能标注成权威源定谳。此口径承重面大：merge 级联分组键 (char_id, star) 无跨档歧义（`deploy_move.py:13-15`）与 §2.1「match 级单字段」粒度决策都压在它上面。
**修正方向**：二选一——①按知识归位纪律把该口径作为独立口述裁定补录进 `equipment_mechanics.md` §7（收编 :162 的待实测行，写明口述日期与边界），设计照常引用；②设计改标「机制推断·实机候证」，如实写明权威源现状为「§7 挂待实测」，保留 §2.0 证伪路径。不建议维持现状。

**F2. [major] | design.md §2.3 | 观察调用点改传 `effective_cost(gs, 卡名)`，但该调用点作用域内没有 `gs`——穿线方式与无局回退语义都未定。**
设计 §2.3 称「调用点（cw_observation.py:1988）由 `ch.cost` 改传 `effective_cost(gs, 卡名)`」。实况：`:1988` 位于 `read_shop_cards(ctx, screen, full_ocr)`（`:1857-1859`）的内嵌函数 `_read_once`（`:1924`）里，整条调用链无 `gs`、无 `session` 参数。实现者面临两个设计文档没回答的选择：
1. `gs` 从哪来——模块内现役有两种模式：`game_state_from_ctx(ctx)`（`cw_game_state.py:1133`，返回 `GameState | None`）与 `getattr(ctx,'cw_match').gs`（`cw_observation.py:2483` 同文件先例）；扩 `read_shop_cards` 签名传参是第三种（该函数已有签名演进先例，测试桩随签名对齐，`sr-od-test/test_cw_game_state.py:712-714`）。
2. `gs is None`（局外/无局路径）怎么办——继续用 `ch.cost` 兜底？还是整段跳过？`effective_cost` 签名要求非 None `gs`。
这构成试读卡点（hard rule 2）：实现者必须自行拍板穿线方案与回退语义。**修正方向**：§2.3 补一句定点——获取口用 `game_state_from_ctx(ctx)`（同文件 `cw_overlay_pick_action.py:409` 先例），`None` 时维持现役 `ch.cost` 兜底（行为与迁移前逐位一致）；或显式选择扩参方案并同步申报测试桩对齐面。

**F3. [minor] | design.md §1.4 | `sell_refund` 行号锚差一行。**
设计引「cw_economy.py::sell_refund:129」，实际 def 在 `cw_economy.py:128`（:129 是 docstring 首行）；同条引的 `bench_char_cost:147` 准确。语义核对通过：卖退款调用面确实按注册表起始费算（`sell_bench.py:100`、`sell_deployed.py:66`、`cw_effect_inventory.py:797` 均为 `sell_refund(star, bench_char_cost(u))` 配对）。**修正方向**：锚改 :128。

**F4. [minor] | design.md §1.2 | 「费用消费面 44 读点」无出处锚，不可复核。**
「44 读点四族（2026-09-20 审查清点）」——仓库内不存在该清点工件，§2.6 裁决表只有 8 行，44 无法对账。范围决策（「本批只做账实一致族」）不依赖精确数，但硬规则 1 要求依据可对。**修正方向**：附清点口径（如 grep 命令与命中数）或降格为「40+ 量级」并注明为审查期估算。

**F5. [minor] | design.md §2.5 | 「现档」读源未点名。**
§2.5 两处用「现档」（`现档 < 5` 判定、`write_logic(lv999_cost_tier, 现档+1)`）但未写从哪读。按 §2.7「`effective_cost` = 唯一读口，禁散查 gs」可推导出应为 `effective_cost(gs, '银狼LV.999')`（None 归约 3），推导链存在但跨了两节，实现者也可能直读 `gs.lv999_cost_tier.value` 自写 None 分支。**修正方向**：§2.5 显式写「现档 = `effective_cost(gs, _TRANSFORM_CHAR_ID)`」。

**F6. [minor] | design.md §2.2 | 升费腿「恰一枚分支成功后写档」留有两个未闭合边界。**
①写档时点相对 `merge_cascade_write` 的先后未定（只影响遥测行序，影响小，但顺手可定）；②现档=5 时若因 OCR 误识仍走 upgrade 腿，`现档+1=6` 越出 §2.1 声明的值域 {3,4,5}，越界写行为（钳制 / defect 留证 / 照写）未定义。正常局不可达（`gameplay/currency_war.md:77`：5 费两选项都是装备），但误识路径存在，按本项目「禁猜+留证」纪律应有定义。**修正方向**：§2.2 补一句——写档置于级联之后（或之前，定一个即可）；现档=5 进入 upgrade 腿 = 不写档 + `planner_upgrade_tier_out_of_range` 留证行。

**F7. [minor] | design.md §2.2 | 测试迁移面申报不完整（不止「消费测试改走 report 落地相」一处）。**
实际消费面：`sr-od-test/test_cw_yinlang_phase32.py` 有 8+ 处 `apply_pick_planner_landing` 直调（:173-:283）、两相 report 对照测试（:302-:320）、**上阵变换窗三测**（:325-:384）。其中变换窗测试在 §2.5 落地后会多出一条档行写（写端从 bench/front/back 三行变四行），断言面（行数/来源锁）需逐条复核；设计一句话申报未覆盖 §2.5 的测试面。反向核验：`resolve_cost_star`、`CARD_TEXT_Y_LO/HI` 的测试消费为零（grep 无命中）——§2.3/§2.4 零测试影响，可在落地文档如实申报零。**修正方向**：landing 阶段拆申报——§2.2 = `test_cw_yinlang_phase32.py` 迁移；§2.5 = 变换窗三测复核；§2.3/§2.4 = 零影响申报。

**F8. [minor] | design.md §2.1 | 「未注册名 → 0（沿用查表空值口径）」的「口径」归属模糊，且与并排双口的另一口口径相反。**
库内存在两种空值口径：`bench_char_cost` 未知 → 3（`cw_economy.py:155`，中费保守估）；观察/算术面 `cost or 0`（`cw_game_state.py:1120`、`cw_intention.py:2600`）。设计选 0（行为本身明确，契约闭合），但「沿用查表空值口径」没说沿用哪个；且双口并排后，同一「查不到名字」问题 `bench_char_cost` 答 3、`effective_cost` 答 0——这个语义差值得在 docstring 边界声明里点明，防后续消费点选错口。**修正方向**：§2.1 把依据写成具体先例（`cw_game_state.py:1120` 的 `or 0` 形态），并在 docstring 边界声明中写明与 `bench_char_cost`（未知→3）的口径分野。

---

## 锚点核验清单（核验通过项）

以下设计引用经逐一对照现值，全部存在且语义相符：

| 设计引用 | 现值 | 判定 |
|---|---|---|
| `apply_pick_planner_landing` @ cw_screen_yinlang.py:273 | :273 def | ✓ |
| 落地记账块 :263–419 | :263 注释横幅起、文件恰 419 行止 | ✓ |
| CARD_TEXT_Y_LO/HI = 300/420 | :105-106 | ✓ |
| `_LEGACY_CARD_RECTS` 在册且被 `_card_point` 消费 | :102-103、:142-143 | ✓ |
| observe 全图 OCR + y 带 + x<960 二分 | :160-171 | ✓ |
| CONFIRM 兜底常量先例 | :107-111 | ✓ |
| `EVIDENCE_OVERLAY_CLOSED` 在库（pick_invest） | pick_invest.py:51，值 'overlay_closed' | ✓ |
| pick_invest 两相形态（发射相零写/落地相证据应用一次） | :10-17、:242-249 | ✓ |
| `report_action_pick_planner_param` @ zero_writes.py:127 | :127 | ✓ |
| 发射上报调用点 @ cw_overlay_pick_action.py:411 | :411-415（leg_type/norm_item 经 env 透传） | ✓ |
| `resolve_cost_star` @ cw_observation.py:1806，倍数∈{1,3,9} 否则兜底 | :1806-1823，行为与 §1.1-4 症状描述一致（badge=4,费=3 → 记 3费1★） | ✓ |
| 调用点 @ :1988 | :1988 | ✓（但 gs 可得性见 F2） |
| `bench_char_cost` @ :147 起始费语义 | :147-155 | ✓ |
| deploy_move 变换窗「只变星级、无 5 费分支」 | deploy_move.py:44-49、:102-107（设计对现状描述准确） | ✓ |
| `DEFAULT_GS_SCHEMA` 域映射、match_facts 域版本机制 | cw_game_state.py:158-164（match_facts: 2）、:2170 扩展先例 | ✓ |
| Field 默认 None 归约可行 | Field.value 默认 None（:449）；`Field[int] = field(default_factory=Field)` 现役形态（:2150、:2203） | ✓ |
| §8.2 头注（Unit 静态属性查注册表派生/禁另存） | :454-464 | ✓ |
| `classify_planner_leg` / PLANNER_LEG_* | cw_events.py:944 / :904-907 | ✓ |
| `cw_projection_audit.py` 登记行机制 | :26、:164、:342（新字段不登记会红完备性锁——设计已申报登记） | ✓ |
| yml `cw_yinlang_star_up.yml`：画面名/5 area/两卡 rect | 左卡 (560,180,1030,455)、右卡 (1065,180,1545,455)，逐字一致 | ✓ |
| actor 遥测身份 'CwScreenYinLang' | planner.py:46（测试 test_cw_screen_report_ports.py:470 同锁） | ✓ |
| `POOL_COPIES_PER_CARD` @ cw_shop_odds.py:33（1/2费27、3/4/5费9） | :33 | ✓ |
| `drawable_names` 档过滤 = 注册表 cost | cw_sim_pool.py:100-109 | ✓ |
| `SILVER_WOLF_COST_BY_STAR` {1:3,2:4,3:5}（旧口径） | cw_sim_special.py:39 | ✓ |
| `cw_effect_inventory.py:727`/:736 随机分支零写 | :727、:736 | ✓ |
| `refresh_prob(level, cost)` 形态 | cw_shop_odds.py:56 | ✓ |
| commit 4b57b9f3b / 测试仓 cfc656a7 | 两仓 git log 均在，主题相符 | ✓ |
| gameplay「银狼我来当策划」节 :76-79 | :76-79，且 :77「5费升2星两选项都是装备」、:78「新费用银狼刷进商店」有原文 | ✓ |
| action_ops.md §1 引文（直调自己的上报函数） | :21 逐字一致 | ✓ |
| action_ops.md §2.3（落地由下一轮重入入口观察裁决） | :41 | ✓ |
| 承接出处 2026-09-18 design §2.1⑤ | :84，内容与引用相符 | ✓ |
| `EVIDENCE_OVERLAY_CLOSED` 单一定义、写端恰两个、池升格批前置契约 | §2.2/§2.5/§2.7 互相咬合，无歧义 | ✓ |
| pick_planner.py 新建后包级 `__getattr__` 解析 | cw_action_report/__init__.py:48-62（具名模块先于 zero_writes），契约测试兼容 | ✓ |

## 边界完整性

§1 五条症状 ↔ §2 方案逐一对应：症状1→§2.2、症状2→§2.2（档行兼任）、症状3→§2.4、症状4→§2.1+§2.3、症状5→§2.5；反向无孤儿方案（§2.6/§2.7 为治理面与契约面，服务于前五项）。§1.4 排除表逐项给理由，范围无外溢。根因归层（§1.3）与修法对位：语义层缺位补容器字段、架构层宿主错位迁 kernel、约定层坐标回收建档——修根非修症状。

## 总结论

**需修订后收敛。**

发现计数：**8 条 = major 2（F1 依据标注与权威源冲突、F2 调用点 gs 可得性未决）+ minor 6**。锚点核验 30+ 项中仅 1 处行号差一行（F3），符号存在性纪律整体良好；两处 major 都是「设计说了、代码/文档接不住」的形态，修订量小（各补一段定点文字 + 一处文档补录），不涉方案结构改动。修订后建议按 iteration-design §5 硬规则 4 做全量同步复查再定稿。
