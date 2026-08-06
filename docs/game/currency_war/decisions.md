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

## D-79 (2026-08-06) 弱阵 fix:commitment prefilter 不再豁免 character_priority 的 off-target 角色(comp-aware)· cw_decisions · task#88
- **决策**:`cw_decisions._best_improving_action` 的 commitment prefilter(target 设定时跳过 off-target 散牌)off-target 测试**去掉 `card.name not in character_priority` 豁免** —— off-target = `阵营∉target.factions 且非 core`,与 priority 无关。priority 仍享 buy-delta 加成(`CHAR_PRIORITY_BONUS×2`)+ 未 commit 时(`target=None`)prefilter 不跑 → 早期 stopgap 保留;只堵「已 commit + shop 有 target 卡可买时,off-target priority 角色仍被买」这个洞。
- **为什么(D-56 live log 实证,非盲调)**:resume plane1-9 死局跑 bot 采 D-56 决策迹 → `target='DOT队'` 全程稳定(D-40 防振荡生效),但 gold=8 时买 **藿藿+阿格莱雅(能量,纯 off-target for DOT)** 填充 → board 7 阵营零成型(能量/仙舟/群攻/贝洛伯格/列车同行/银河学者都非 DOT)→ plane1 boss 战 **hp 60→26 重伤**;plane2 r1 仍 8 阵营 spread。根因:`DEFAULT_CHARACTER_PRIORITY` 含「藿藿/阿格莱雅」(1-2 费前期基石),prefilter 第三条件 `name not in character_priority` 把它们豁免 → commitment 名存实亡。违反 CLAUDE.md 铁律「**一切评分 comp 相关**」(装备/巨星/词缀都挂钩 target_comp,priority 不该绝对豁免 commitment)。
- **备选**:① 改 `DEFAULT_CHARACTER_PRIORITY` 删 藿藿/阿格莱雅 —— 推翻:治标(用户自定义 priority 会再撞)+ 这些角色对能量队等仍是有效 early stopgap;根因是 priority 绝对豁免,该治本(prefilter)。② priority 完全 comp-aware(连 eval 加成也去)—— 推翻过激:priority 的 eval 加成是用户 steer(未 commit / shop 无 target 卡时该 grab 强角色),只需堵 committed 态。③ 同步改 `_saving` gate 的 priority 豁免 —— 推迟:`_saving` 是经济维度,prefilter 已在 committed+target-可买 态拦住 off-target priority buy(saving 放行→prefilter 拦),功能够;若 `_saving` 豁免也致 spread 待后续数据。
- **状态**:采用。1 新测试绿(`gold=3 + [阿格莱雅(能量,off-target priority), 黄泉(减益,target core)]` → 买黄泉、不买阿格莱雅;旧码 priority 豁免 + buy-delta `+16` → 先买阿格莱雅→gold 剩 2 买不起黄泉→漏 target);全 currency_war **199 绿**;ruff 净。**待验证**:restart server(载 fix)+ 新局跑,看 committed 态 board 是否聚焦 target faction(不再 spread);旧码 bot 实跑已确认 bug(hp 60→26)。· task#88 / strategy/02 commitment / CLAUDE.md「一切评分 comp 相关」

---

## D-78 (2026-08-06) GameState 加法建模块:strategy/13 §13.2 补字段 + NodeInfo + BenchChar.equips + current_boss 派生(零行为变化)· strategy/13 §13.10 step1
- **决策**:`cw_state.py` 落 strategy/13 §13.10 step1 的**安全加法子集** —— ① 新 `NodeInfo` 类型(node_path 元素);② `BenchChar`(= §13.2 `Unit`)加 `equips: list[str]`(身上装备,有序);③ `GameState` 加 7 个 §13.2 新字段(`node_path`/`match_type`/`plane_modifiers`/`shop_locked`/`active_strategies`/`megastar_char`/`partner_char`,**均 None/空兜底**,OCR 未接→安全降级);④ `current_boss` 派生属性(= `bosses[plane-1]`,越界/空→None)。**零行为变化**:不 rename、不删字段、不改默认值、不 rewiring 策略层。
- **为什么(PROGRESS 顶优先 + 风险分层)**:strategy/13 §13.10 step1「建模」是纯逻辑、不需游戏的头号待办;GameState 经前期补全已较完整(node_type/enemy_difficulty/xp_progress/level_up_cost/shop_refresh_cost/streak/board_next_tier 等已加),本次补剩余 §13.2 新字段让后续 OCR 接线可填(接一个填一个)。**加法子集先落地** = 零风险(长上下文 / post-compact 不宜一次做大行为变化);**行为变化部分(rename `round_num→node_index`/`difficulty→selected_difficulty`/`bosses→plane_bosses`/`equips→inventory` 拆 + 去谎言默认 `hp→None`/`board` 编 + 策略层 `None` 降级 + 测试调绿)留后续统一迁移块**(§13.8),避免半截迁移破坏策略层。
- **备选**:① 一次性做全部(renames + 去谎言 + 策略层 None 降级 + 测试)—— 推翻:行为变化大 + 长上下文易错,分块更稳且可独立验证;② 加 `inventory` 字段(§13.2 G,equips 拆 available_equips + diamonds)—— **推迟**:与现有 `equips: list[str]` 双源(违反 CLAUDE.md 单一真相源),留「equips→inventory」统一迁移时一起做,避免过渡期双写漂移;③ 不加 `current_boss` 派生 —— 保留:派生属性无副作用,boss_fit/策略可直接用,免去各处重算 `bosses[plane-1]`;④ 加 `NodeRecord`(§13.3 观测日志)—— 推迟:属 `PerformanceTracker.history`(cw_performance),与 GameState 分离,不在本块。
- **状态**:采用。5 测试绿(新字段默认 + BenchChar.equips + NodeInfo + current_boss 派生 + 既有字段/方法零回归);全 currency_war **193 绿**;ruff 净。§13.2 字段补到剩:rename/去谎言默认/inventory 拆/NodeRecord/FactionState(board 重构)—— 后续迁移块(§13.8,需同步改策略层 + 测试)。· strategy/13 §13.10 step1 / §13.2

---

## D-77 (2026-08-06) 装备合成图谱:7 标准基础件完整 K7 两两合成图(28 进阶,逻辑闭合)+ 光能电池孤立节点(待核实)· cw_synthesis
- **决策**:建 `cw_synthesis.py` 合成图谱 —— **7 件标准基础件(以太钻头/和平手枪/幸运星/折叠小刀/生命之花/轮滑鞋/量产型装甲)构成完整 K7 两两合成图**:C(7,2)=**21 交叉配方**(每两件不同基础件→1 进阶,**双组件经图鉴「合成公式」列表交集核实 = 确证**)+ **7 自配配方**(每件×2→1 进阶;反重力皮靴=2×轮滑鞋 攻略确证,余 6 由 K7 闭合逻辑确证 —— 每件列表恰 7 项,6 项交叉用尽,第 7 项无其他件可配→只能自配)= **28 进阶,合成图完整闭合**。光能电池 7 进阶与标准 7 零交叉(孤立节点,机理不同)→ `GUANGNENG_ONLY` 标注,**待游戏内人工核实**后另建。
- **为什么(D-73⑤ 装备合成配方 + 证据纪律)**:`extract_synthesis.py` OCR 数据银行图鉴「合成公式」区(每基础件→可合成进阶名单)派生图谱;进阶名出现在 2 件基础件列表交集 = 那两件即组件。**OCR↔米游社 equipment.md 双源对拍**:42 个名字(7 基础件+28 结果+7 光能)全在 `EQUIPMENT_ROSTER`,无缺。**视觉大模型读图标配对被否** —— GLM-4.5V 对光能电池页编造自相矛盾链(战场进化手册既是结果又被当组件,7 结果漏 1),印证 CLAUDE.md VLM 边界(计数/对齐/状态推理不可信);故光能电池不靠 VLM,标待游戏内核实,不强入码(拿假设当论据=违反证据纪律)。
- **备选**:① VLM 读图标配对(推翻:幻觉自相矛盾链);② 28+光能7 全当确证入码(推翻:光能机理不明,与标准 K7 零交叉,强入=假设当论据)→ 只入确证的 28,光能另列待核;③ 入 `cw_equipment.py`(推翻:那是 `gen_equip_registry.py` 产物,合成不在 equipment.md → regen 丢失)→ 独立 `cw_synthesis.py` 手维护(28 配方稳定游戏数据);④ 全靠 bot-tracking 不建合成图(保留:ComposeEquip 接线时 bot 跟踪作运行时主路径,本图谱作静态可达性参考/成型评估)。
- **状态**:采用。**6 测试绿**(K7 完整闭合 + 度数全 6 + 无重复对 + 三组结果无重叠 + 名字双源对拍 + 可达性函数 `synthesize_target`/`self_advance`/`cross_components`/`self_base`);ruff 净。`以太钻头` 类别怪癖(图鉴归简易 tab 作基础件,米游社归进阶)—— 按图鉴事实作基础件处理,docstring 标注。**光能电池机理 + ComposeEquip op 接线待后续**(游戏内核实机理后)。· D-73⑤ / strategy/03 装备合成 / `tools/cw/extract_synthesis.py`

---

## D-76 (2026-08-06) 装备图标库:CV 形状检测裁切工具(tools/cw/harvest_equip_icons.py,可复用)+ 位置对齐法· task#87
- **决策**:数据银行装备图鉴采图标库,建**可复用裁剪工具** `tools/cw/harvest_equip_icons.py`(CV 形状检测定位紫色边框方块 → 紧贴裁 → 按规范名存 `assets/template/cw_equip/`),版本更新重跑补采。方法(od-dev-ui-region-detect §形状轮廓法 squares):灰度多阈值扫描 + 填洞(`drawContours FILLED`)+ 4 顶点凸 + 面积/长宽比 + IoU 去重 → 检出图标方块(精度完美);召回 ~50%(图标内容差异大)→ 聚类检出锚点推全 7×3 网格(列中心 + 尺寸)。**标签↔图标位置对齐**(OCR 名 top-y + CV 校准偏移 + CV 列中心;顶/底行图标越出面板自动跳过)。
- **为什么(用户「去数据银行」+ 教方法,2026-08-06)**:建 icon/立绘库(任务#87);用户逐点纠方法:① **别用名字中心推坐标**(名字长短不一→偏心)→ CV 形状检测判几何;② **别按行索引对齐**(滚动后顶行图标被面板裁切→CV 漏检顶行→索引整行错位贴错,实测 page-2 错标一整行已删)→ **位置对齐**(OCR 名 y + 偏移);③ **裁剪脚本存可复用工具**(版本更新补采,别扔 .debug/temp);④ Windows 中文路径 `cv2.imwrite` 挂 → `imencode+tofile`。
- **备选**:① 硬编码名字中心 + 固定 116 框(推翻:外围背景 + 偏心,用户首否);② 检测行索引 ↔ 名行索引对齐(推翻:滚动裁切→错位);③ 一次性脚本扔 .debug(推翻:版本更新要重写 → 存 `tools/cw/` 复用);④ 完全不建库走 bot-tracking(保留:装备身份默认 bot 跟踪,视觉库作恢复/校验旁路,同 D-75 角色身份设计)。
- **状态**:采用。工具 ruff 净;page-1(21)+ page-2 干净行(14)= **35/125 初始入库**(动能激发剑行被裁切跳过,待他处补);squares 精度完美(21/21 紧贴居中,vision 校验)。**采全待续**(滚动 + OCR 名 y 流程,~4-5 页;含 ·特权 变体需选读全名)。**skill 反馈已写**(「采库裁剪脚本存复用工具 + 位置对齐法」→ skill-improver 后台处理中)。· 任务#87 / strategy/13 `inventory.available_equips`·`Unit.equips`

---

## D-75 (2026-08-06) 角色立绘库:脸近景库对备战半身立绘强命中(免采半身模板)+ identity reader 接线· cw_identity_obs/currency_war_char_id
- **决策**:备战角色身份识别**复用现有 `character_avatar` 脸近景库(88)**(推翻 char_id.py / D-73 旧结论"脸近景≠备战半身,需货币战争专属半身模板")。新建 `cw_identity_obs`:`identify_slots`(纯 CV 核心,裁 screen_info 槽位 → SIFT → `resolve_char_name` → 规范名,离线可测)+ `read_deployed_chars` / `read_bench_chars`(ctx 薄包装,从 screen_info 取 `前排-1..4`/`后排-1..6`/`备战栏-1..9` rect)。`resolve_char_name`:`avatar_id` → `get_character_by_id().cn` → `CHARACTER_ROSTER`(变体子串消歧)。
- **为什么(用户「建 icon/立绘库」+ 实证优先)**:用实机 P1R9 截图实测 SIFT,脸库对备战半身立绘**强命中** —— 前排 4/4(佩拉/黑塔/Saber/藿藿,inliers 23-30 vs 第二名 3-4,巨大间隔)、备战栏 8/9(inliers 21-36)、后排空(正确返空;VLM 曾幻觉"1 个后排",印证 VLM 计数不可信)。旧"配饰角色不可靠"基于不同/旧样本,**过于悲观**。用户要建库 → 实证发现**库已存在且对面部独特角色够用,免从零采 74 张半身模板**的大工程。
- **备选**:① 从零采货币战争专属半身模板(推翻:实测脸库够用;且备战/商店槽位 RNG 累积采全 74 张慢、数据银行图鉴采有跨视图风险 + 用户对局中不能导航)。② 接进 `read_game_state`(推翻:每帧 SIFT 慢 + 与 bot 跟踪 deployed/bench 双写冲突);**保留 bot 跟踪为默认**(deployed/bench 由 buy/deploy 推演,plan-time 快),视觉 reads 作**离线重建 / 漂移恢复旁路**(不进 read_game_state)。③ 完全不建视觉身份(推翻:离线从截图重建 GameState 对测试/replay 有值 + 漂移恢复)。
- **状态**:采用。4 测试绿(`resolve_char_name` 单元 + `identify_slots` 纯 CV + `read_deployed_chars` 经 ctx 集成,fixture `deployed_p1r9.webp`);全 currency_war **187 绿**;ruff 净。**待多样本核**:配饰/帽子重角色(黑天鹅等)、货币战争变体(姬子·启行/千冶·刃/丹恒·腾荒 共脸异名 → SIFT 归一基础名,子串消歧对"基础+变体并存"roster 可能不准,需星级/阵营旁证)。**部分解决 D-73 备战字段全图 🟡 deployed/bench 身份**;余 `Unit.equips`/`active_strategies`/`inventory`/`node_path` 仍需图标库(任务#87)。· strategy/13 §13.2 deployed/bench 身份

---

## D-73 (2026-08-06) 第二轮攻略调研驱动策略更新计划(V4.4 meta + 概念股送件 + 词缀对策 + 商店保底)· strategy/03 round5 + research/
- **决策**:第二轮 V4.4/V4.5 深度调研完成(知识库 `.debug/temp/currency_war/strategy_research/`,9 文件分主题),据此定策略更新方向,记入 strategy/03 round5:**① COMP_LIBRARY** —— 「列车同行」= **姬子·启行护盾反震流(V4.4 meta 顶层,用户确认)**(core 姬子启行+三月七,key_equips 反震四件套,**boss_weakness 加「正当防卫」**);补 命运圣杯流/欢愉队/万敌单C/减益黄泉。**② 新角色+命运圣杯阵营**(CHARACTER_ROSTER/FACTIONS 补)。**③ 词缀对策表**(正当防卫克反震/反甲/高频;同步行动克拉条利DOT;沉重脚步刚需护盾…)。**④ 概念股送装备件 = decide_invest(env) 新维度**(选与 target_comp 核心装备合成件匹配的概念股)。**⑤ 装备合成配方**(cw_equipment 基础件×2→进阶)。**⑥ 商店保底**(每5刷出5张同费,建模进 D牌逻辑)。**⑦ 姬子启行选择伙伴按最缺羁绊选**(升级 decide_partner,随 read_partner OCR)。
- **为什么(用户 2026-08-06「重新调研 + 总结优化策略」)**:第一轮(research round1,V4.4 基线)后实机推进到 V4.4/V4.5,meta 已演进(姬子·启行反震=顶层、Fate 联动命运圣杯),需新一轮调研校准策略方向 + 补 V4.4 新内容。用户定调「调研越多越好」,2 个研究子 agent 并发(≤2 上限内)分头深挖阵容/角色/装备/经济/投资/boss/节点,NGA 403、米游社 JS-only 靠搜索摘要+其它源交叉,每条标来源+版本+置信度。
- **用户澄清(2026-08-06,定方向)**:① **刷新费默认 2 金**(备战画面识别;部分条件触发后变 → 读 `state.shop_refresh_cost`;bwiki "4金"疑混淆,代码 `SHOP_REFRESH_COST=2` 对);② 升级金价表/连胜阶梯 → 实机采集(非设计问题);③ **列车同行 = 姬子·启行**(确认);④ 角色图鉴补全(任务)。
- **备选**:① 直接改代码实现上述(推翻:用户明确「只更新设计方法 + 进度待办,之后有人跟进」,本轮不改代码);② 只写 PROGRESS 待办不更新设计 doc(推翻:研究对 strategy/03 阵容规划层有实质设计影响,需 round5 补充落 doc 才不漂);③ 把装备/词缀细节也全写进 strategy/07、10(推迟:03 是战略核心先落,07/10 细节在 research dir,跟进人按 round5 + research 执行即可,避免本轮盲目改未读 doc)。
- **状态**:**计划(待跟进人实现)**。strategy/03 round5 已落;research/ 9 文件已落;PROGRESS_autonomous 已加待办。实现优先级(跟进人参考):COMP_LIBRARY 扩 + 词缀对策表 + 新角色/阵营注册表(纯逻辑、影响识别+选comp)→ 概念股送件决策(纯逻辑)→ 数值实机校准 → 装备配方/商店保底/选择伙伴(部分需OCR)。· strategy/03 round5 + research/(用户「调研越多越好 + 只更设计/待办」)

---

## D-74 (2026-08-06) 备战字段采集收尾批:enemy_difficulty/level_up_cost/shop_refresh_cost/streak + xp 改用 screen_info area(用户纠误判)· cw_state/cw_observation
- **决策**:接 4 个备战字段(各用 screen_info area,单一源坐标):`enemy_difficulty`(文本-难度,左上角)、`level_up_cost`(文本-购买经验金币数)、`shop_refresh_cost`(文本-刷新金币数,默认 2)、`streak`(文本-连胜数);+ `read_xp_progress` 改用 `文本-升级所需经验` area(去掉 D-72 的硬编码 Rect);`read_game_state` 接线。
- **为什么(用户 2026-08-06 纠正)**:我 D-73 误判"level_up_cost/enemy_difficulty 不在备战屏"——**它们在 screen_info 有 area**(文本-难度/购买经验金币数/刷新金币数/连胜数/升级所需经验),我漏 grep area 名了。用户:"升级所需金币在 screen_info 应该有;敌人难度在左上角"。核实后全在 → 按用户「完成备战」全接。
- **备选**:① enemy_difficulty stylized OCR 常空 → 不接(推翻:area + scaffold 就位,OCR 能读到即生效,stylized 留 vision/digit-CV 后续);② 保 xp 硬编码 Rect(推翻:screen_info area 是单一源,改用它)。
- **状态**:采用。65 测试绿(+1 numeric batch);ruff 净。**caveat**:enemy_difficulty 数字 stylized,OCR 常空(可靠读待 vision/digit-CV);level_up_cost/streak/refresh_cost shop-态相关(读到填真值,读不到 None/2 兜底)。**子agent 确认**:base64 vision 脚本是官方 harness 特性(GH #36511,harness 拦截 `data:image/` stdout→图片块),非 hack;Read 的 CDN 反斜杠 key 是**定制环境 bug**(报环境维护者:上传 key 该用 hash 如 data-URL 路,非 raw 路径)。· 用户纠误判 + 「完成备战」

## D-73 (2026-08-06) 备战字段采集:node_type(当前节点类型,顶部标签 OCR)+ vision 修复(img_to_vision_url 脚本)· cw_state/cw_observation
- **决策**:① **node_type 字段**(`str | None`)+ `read_node_type`(顶部节点行标签带 OCR → 关键词 map:首领→boss/补给→supply/遭遇→encounter/巨星→megastar/战斗/精英/奖励/投资);`read_game_state` 接线。② **vision 修复**(本条前置):新建 `.claude/scripts/img_to_vision_url.py`(本地路径[+crop]→base64→print→harness 拦截上传 CDN 用 hash key→干净 URL→喂 analyze_image);CLAUDE.md 记「用 analyze_image 前必跑此脚本」+「项目用 uv run python 不用 python」;memory 更新(旧 Read→CDN 路径已失效)。
- **为什么(用户 2026-08-06「完成备战」+ vision 修复诉求)**:node_type(当前)驱动节点前决策(boss 前保战力/补给前无战)。vision 400(Read 的 CDN URL 带反斜杠)卡了 icon 字段 + 整个 screen-onboarding 主线无数次,用户要脚本一劳永逸。
- **备选**:① 全节点类型 node_path(图标→类型)需建节点图标模板库(本条只当前节点 + 文字标签);② vision 修法用 file:// / 编码 URL(都实测 400,推翻;只有 base64→harness 上传干净 key 通)。
- **状态**:采用。64 测试绿(+1 node_type);ruff 净。**仅 boss(首领)实机核实**;其它节点类型标签措辞待多态实机补全(map 已覆盖常见词)。· 备战可采字段到顶(见下)。
- **备战字段全图(D-73 收尾)**:✅ 可采全接 —— gold/hp/level/plane/round/shop/bench_full + board tier(D-69)+ xp_progress(D-72)+ node_type(本条);❌ **不在备战屏** —— level_up_cost(购买经验区"5"是**等级**非 cost,实据;cost 不显示)、enemy_difficulty(是简报/结算"敌人难度 108",非备战);🟡 **需图标/立绘库**(下步大方向)—— active_strategies(右面板图标列,vision 探到但 identity 要策略图标库)、inventory equips(未持有/要装备图标库)、deployed/bench 身份(SIFT 立绘库)、node_path 全节点类型(节点图标库)。**备战"完成"= 建 icon/立绘库**(identity 类),非更多 OCR。

## D-72 (2026-08-06) 备战字段采集:xp_progress(购买经验 "X/Y"→cur/next;文本字段到顶)· cw_state/cw_observation
- **决策**:备战文本字段采集第二切片 = `xp_progress: tuple[int,int] | None`(``cur_xp, xp_to_next_level``),购买经验按钮下方 "X/Y"(如 "4/20"→(4,20))。`read_xp_progress`(硬编码 Rect,同 read_bench_full,后续移 screen_info area)+ `read_game_state` 接线。
- **为什么(用户 2026-08-06「继续备战文本字段采集」)**:xp_progress 是 level 升级时机决策的输入(cur 接近 next → 即将升级,影响 level_plan/买经验优先级),替代纯 `_expected_level` 估。
- **备选**:① 同切片接 `level_up_cost`(推翻:购买经验的 "5" OCR 不稳,cost 还是 level 不清,需 vision 核实,暂不接);② 用 screen_info area(推迟:先硬编码验稳再移,同 read_bench_full 先例)。
- **状态**:采用。63 cw_observation+decisions 测试绿(+1 xp_progress);ruff 净。**备战文本字段采集到顶**:干净文本字段 = board tier(D-69)+ xp_progress(本条);**余皆阻塞** —— active_strategies/inventory 图标、node 行图标、deployed/bench 身份 = vision(400)/SIFT 立绘库;enemy_difficulty 备战屏未见(可能在节点子态)。下一解锁靠修 vision / 建 SIFT 库。· D-70 备战字段采集 + 用户「继续文本字段」

## D-71 (2026-08-06) 拆分 cw_observation(备战/简报/结算/core;D-70 备战字段采集铺路)· cw_obs_*
- **决策**:`cw_observation.py` 558 行混了备战/简报/结算三类 reads。按**画面**拆成 4 文件:`cw_obs_core.py`(共享 helper `_ocr`/`_area_rect`/`area_center`/`shop_card_click_points`/`_first_int` + 常量,无兄弟依赖断循环)+ `cw_briefing_obs.py`(简报 reads + 词缀文件操作)+ `cw_settlement_obs.py`(结算 reads)+ `cw_observation.py`(只留备战 reads + `read_game_state` + **re-export** 简报/结算)。
- **为什么(用户 2026-08-06)**:「cw_observation 太大就拆」。备战字段采集(D-69/D-70)会让它涨到 750+,趁早拆、新 reads 直接进对模块。**零 importer churn**:所有 `from cw_observation import X`(8 处:shop/deploy_bench/battle_prep/handle_*/battle_loop)经 re-export 仍可用。
- **备选**:① 4 文件全平铺无 core(推翻:briefing/settlement 需 `_ocr`/`_area_rect` → 循环导入;必须抽 core);② importer 改从子模块 import(推翻:8 处 churn,re-export 更省);③ 暂不拆(推翻:备战字段会让它更大,越拖越难)。
- **状态**:采用。180 currency_war 测试全绿(含 entry_flow 全 handler 链);ruff 净。**1 测试触点**:`test_cw_observation` 的 affix-effects 测试 monkeypatch `_AFFIX_EFFECTS_PATH`(随 file-ops 挪到 `cw_briefing_obs`,测试改用 `cw_briefing_obs._AFFIX_EFFECTS_PATH`)。`area_center` 在 observation 内不用、只 re-export → `# noqa: F401`(防 ruff 删)。· 用户「太大就拆」+ D-70 备战字段采集铺路

## D-70 (2026-08-06) 策略入参 = 完整局内信息(GameState 重做:全量字段 + 整局固定归位 + None 不说谎) · strategy/13
- **决策**:`GameState` 重做成**完整的局内信息单一入口** —— ① 把一局货币战争所有可能有用的信息全建字段(进度/节点/经济/棋盘/商店/投资/装备/资源/生命 + 整局固定事实 + 节点观测日志 + 游戏参考数据注册表);② 开局读一次、整局不变的事实(3 boss/敌人词缀/投资环境/位面修正/难度)从 `session` 迁入 `state`(修「同一信息两个家」);③ **`None` = 未观测,不用 plausible 默认值说谎**(hp=100/count=1/level 兜底 → 全改 None);④ 节点序列(备战顶部图标行)、已持投资策略、持有装备+钻等之前漏读的信息补建。详 strategy/13。
- **为什么(用户 2026-08-06 定调)**:**「要完成决策,提供的信息越多越好;是否使用是策略决策的事」**。现状 `GameState` 是「策略现在用到啥才补啥」,大量有用信息没字段(`active_strategies`/`streak`/`node_type`/`node_path`/`inventory`...)或读默认值说谎(策略分不清真值 vs 没读到,「完整提供」是空话)。信息层与决策层解耦:信息层只管完整准确提供,字段先全建,接不接 OCR 是画面建档的事(接了填真值,没接 None)。另:难度两阶(职级 A8-1..A8-50 决定起始敌难 + 节点递增的 enemy_difficulty,boss 血量 base×1.052^难度)记进 gameplay。
- **备选**:① 在现状 GameState 上零散补字段(推翻:现状「plausible 默认说谎」+「session/state 双家」是结构性缺陷,打补丁不治本,违背「完整 + 诚实」原则);② 顺手改 hook 签名/给自定义策略建参数家(推翻:另一件事,本文聚焦信息内容,不混;hook 签名后续单独做);③ 把节点序列/装备等 OCR 接完再建模(推翻:字段先建不阻塞,接线是画面建档独立任务,不该耦合)。
- **状态**:**设计(待实现)**。strategy/13 已写(字段全集 + 接线状态表 + 待核实项 + 实施顺序)。建模纯逻辑不需游戏;接线需游戏(画面建档)。**行为变化点**:去谎言默认 → 策略层(`cw_decisions`)需对 None 安全降级 + 测试调。· strategy/13(用户「完整提供信息」定调)

---

## D-69 (2026-08-06) 备战字段采集启动(doc 13):board tier(X/Y → count + next_tier)· cw_state/cw_observation
- **决策**:备战屏信息密度高但 `GameState` 只填 8 字段(用户:备战还没处理完,很多信息没采)。按 doc 13(`strategy/13_input_model.md`)启动备战字段采集,**第一切片 = board tier**:左面板 "X/Y" → `count=X`(已有)+ `next_tier=Y`(新增 `board_next_tier` 字段)。`read_board` 重构出 `_board_pairs`(同时取 X+Y)+ `read_board_next_tier`;`read_game_state` 单次 OCR 填两者。
- **为什么(用户 2026-08-06)**:① 「每屏做完」——备战 "done" 不止 area/id_mark,要采全它提供的 `GameState` 字段(doc 13 §13.2);② 全屏 OCR 把 "2/3" 误读 "213" 让 `read_board` 显脆,实为**全屏密度问题**(聚焦裁切读对)——`next_tier` 阈值是 comp/progress 评分「距下个 tier 几人」要的。
- **备选**:① `board: dict[str,FactionState]` 改类型(doc 13 目标,推翻:破所有 `state.board[f]` int 用法,留 §13.8 一轮聚焦改;现**加itive 加字段**,不破行为);② 只读 count 不扩(推翻:next_tier 干净可读 + 有价值)。
- **状态**:采用。18 cw_observation 测试绿(+1 board X/Y);ruff 净;`read_board` 行为不变(回归)。**保守**:新字段默认空、无策略消费方(暂),策略接法后续。· doc 13 §13.2D/§13.6 + 用户「每屏做完」
- **备战字段全图(余待采)**:✅ board tier(本条);🟡 待探区域(active_strategies 右面板空需别的子态/enemy_difficulty/level_up_cost/xp_progress);❌ 阻塞(node row 图标/inventory 图标=vision 400 挂;deployed/bench 身份=SIFT 立绘库未建)。逐簇推进。

## D-68 (2026-08-06) 投资环境数据银行核对 → INVESTMENT_ENVS 全量 + 删冗余 doc + 未建模项 log warn(代码单一源) · cw_investments/handle_invest_env
- **决策**:① **INVESTMENT_ENVS 全量扩**(36→~82,7 类齐全:概念股15/邀请20/契约7/时代6/经济15/规则10/专家9),数据银行 OCR 核对游戏内总 83/解锁 68;② **删 `docs/game/currency_war/data/investment_envs.md`**(代码已全量建模,doc 数据表是冗余副本);③ **handle_invest_env 加 log warn**:OCR 命中注册表外的环境名 → 报警(未建模项不静默 fallback,防假绿);④ 修正:删 2 个不存在的概念股(持续伤害/量子同频概念股,数据银行无此卡)、确认战技点概念股(实存)、新增 4 个米游社漏收(红钻/蓝钻贵族、命运圣杯邀请/契约)。
- **为什么(用户 2026-08-06 指导)**:① 「每屏处理完再下一屏」——投资环境屏的完整范畴 = 认全所有环境(数据全集是识别地基,非后置美化);② **数据银行是权威源**(83 总,米游社 77 漏 4 + 2 个概念股不存在);③ **「代码已建模的游戏数据不存 doc」(用户原则,单一真相源延伸)**——注册表有 name/category/effect/faction/source 全字段,doc 同内容是重复源 → 漂移风险(CLAUDE.md「单一真相源」的具体化)。非数据信息(D-68 发现/缺口/Fate 阵营)进本日志 + 代码注释,不进数据 doc。
- **备选**:① 保留 doc 双源(推翻:漂移,用户明确要代码单一源);② 只加 log warn 不扩注册表(推翻:注册表是识别基础,log warn 只兜底,两者都要);③ 把全量数据留 doc、代码只收策略用的(推翻:OCR 识别全集都要,且违背单一源)。
- **状态**:采用。49 investments+comps 测试绿(10 新 D-68);ruff 净。**缺口**:5 个 `???` 锁定未命名环境🔴无法收(数据银行未解锁);命运圣杯 = **Fate 联动阵营**(角色 远坂凛/吉尔伽美什/Archer),factions doc 未收,待补。**下一步 D-69**:运行时采集仿词缀(锁定环境玩家解锁后出现在对局里自动采)。· CLAUDE.md 工程化质量/单一真相源 + 用户「每屏做完」+ 「代码已建模不存 doc」

---

## D-67 (2026-08-06) 经济统一论接线 + bench 空间检查(用户反馈:没早凑 50 金 + 没判断备战席满 + 无脑填备战席) · cw_decisions
- **决策**:① **_saving_for_interest**:gold<INTEREST_THRESHOLD(50) + 板位满(deployed≥max_units,非战力断档)+ 健康(hp≥threshold,非 tempo)→ 攒息(抑 off-target 买 + 阻 roll),并入 `_saving`(同 _saving_for_level 抑散牌);② **bench 空间检查**:buy loop 里 deploy 满 + bench 满(≥BENCH_CAPACITY 9)→ skip 买(防 overfill)。
- **为什么(用户 2026-08-06 看对局反馈)**:①「没早凑 50 金拿满利息」—— bot greedy buy-delta 见 synergy(+10/牌)> interest(4/tier,**单轮视图低估复利**)→ 买空金到 0 → 无息引擎(每回合白拿5)→ 弱死。CLAUDE.md「经济统一论:维持≥50,超出才花;tempo(HP危险/战力断档)破息」是设计但**未接线强制**。②「没判断备战席满 + 无脑填备战席」—— buy loop 无 bench 空间检查,deploy 满时买的牌堆 bench → overfill;off-target 散牌买致 spread。
- **备选**:① 提 INTEREST_WEIGHT(4→8,推翻:单轮 eval 仍会买,synergy>interest;hard floor 才根治);② off-target cap(推翻:D-67 初版试过,破坏 synergy push,已撤);③ 全阻 target 买也(推翻:target 深化 + level_plan 该花,只阻 off-target + roll)。
- **状态**:采用。44 decisions 测试绿;ruff 净。**tempo 例外**:hp<threshold 或板位未满(战力断档)→ 不攒息(可买保命/填板)。**待新局验**:bot 是否早达 ≥50 金(息引擎)+ bench 不 overfill + 少 spread。· CLAUDE.md 经济统一论 + 用户反馈

## D-66 (2026-08-06) P2/F1:maybe_pivot commit 阈值(target form_progress≥0.4 → 强粘,不弃成型 comp) · cw_comps
- **决策**:信号1 pivot 阈值加 commit 层 —— `target` 的 `form_progress ≥ COMMIT_FRAC(0.4)` = 已 commit → 阈值 ×`COMMIT_STICK_FACTOR(1.5)`(0.10→0.15,强粘)。**优先于 D-59 easier**(已 commit 不因易 comp 降阈被弃)。未 commit + best 易 → D-59 降阈(0.07);已 commit → 强粘(0.15);else 正常(0.10)。
- **为什么(strategy/12 F1 + 2026-08-06 实跑 spread)**:bot board spread + 低 hp 弃正在成型的 comp → 弱死。F2(roll)让 bot roll 找 target,但 target flit(微 score 波动切走)→ 深堆被打断。F1 让已 commit(40%+ 成型)的 target 强粘,best 需大幅优于(0.15)才转 → bot 深堆一个 comp 不轻易弃。语义:「已在堆 X,继续堆,别因 shop 这轮波动弃」。
- **备选**:① 不加 F1 靠 D-40/D-59 稳(推翻:实跑仍 flit/spread,F1 显式 commit 阈值更稳);② COMMIT_FRAC 调高(0.6,推翻:0.4 已能防弃 1 阵营过半的 comp,0.6 太晚);③ commit 也阻信号3(推翻:信号3 保命该能切,D-65 已让保命 board-align,F1 只管信号1 涌现)。
- **状态**:**实验**(COMMIT_FRAC 0.4 / STICK_FACTOR 1.5 待多局校准)。40 cw_comps 测试绿;ruff 净。log 加 `[commit强粘]` 标记。**待新局验**:已 commit 的 target 是否不被微波动弃 → 深堆成型 → 存活久。· strategy/12 F1(P2 comp 成型)

## D-65 (2026-08-06) 弱阵:信号3 保命优先 board 有 progress 的 easy comp(防切 board 不支持的 fast-easy) · cw_comps
- **决策**:信号3(保命,hp<0.75×threshold)选最快 easy comp 时,**优先 board 有 form_progress>0 的 easy comp**(无则 fallback 全 easy)。log 加 `[board有progress优先]` 标记。
- **为什么(2026-08-06 实跑 plane1 r8 死)**:hp 流血到 1(hp<30 保命触发)→ 信号3 切 **DOT队**(fast easy,form_round 4),但 board 是 追击/群攻(**无 DOT队 的 持续伤害/减益**)→ DOT队 无法成型 → 仍死。切到一个 board 不支持的 fast-easy = 无效保命(成型不了还是死)。该优先 board 已有 progress 的 easy comp(如 列车同行,board 有 列车同行:1 → 能继续堆成型)。
- **备选**:① 保命切当前 target 若正在成型(推翻:target 可能 medium/hard,保命该偏 easy 快成型;D-65 在 easy 池内筛 progress 更稳);② 完全弃保命切换(推翻:D-40 实跑证明低 hp 不稳 churn 死亡螺旋,保命切稳定 easy 是对的,D-65 只加 board-progress 约束);③ 信号3 也看 comp_viability 观测(将来,P2)。
- **状态**:采用。40 cw_comps 测试绿(改 test_maybe_pivot_low_hp_signal3:board full 成型 easy → 保命选它,非弃成型);ruff 净。**关联**:F1(commit 阈值)尚未做(strategy/12);D-65 是保命的 board-alignment 细化。· 弱阵(D-40 保命 + D-59 易comp + strategy/12)

## D-64 (2026-08-06) choose_partner confirm mouse_move + 验 overlay 关(bug#1 + ADR-0009) · handle_select_partner
- **决策**:candidate + confirm click 前 `mouse_move`(bug#1 缓解);confirm 改 OCR 定位(`_find_text_center`)+ mouse_move + click(弃 `round_by_ocr_and_click` 裸 click);confirm 后验 overlay 关(选择伙伴 消失),没关 `round_retry`(ADR-0009 兜底)。
- **为什么(2026-08-06 r6 stall)**:choose_partner iter102+ flat-loop:`已选择→直接确认` round_success 但 overlay 不关。**probe 实测**:手动 click candidate(945,301)→已选择→手动 click 确认(1441,582)→**overlay 关回备战**。bot 的 `round_by_ocr_and_click` confirm 被 bug#1 吞(before_screenshot 移光标→click 落空)→ overlay 持留 → flat-loop。r9 同型(手动 click 即关)。
- **备选**:① 保留 round_by_ocr_and_click 只加 verify(推翻:click 仍 bug#1 吞,verify 只能 retry 不能让 click 落地;mouse_move 治本);② 弃 confirm 改 ESC(推翻:probe 验 confirm 关 overlay 是正解,ESC 行为未验);③ 两步事件假说(推翻:probe 验 confirm 直接关 overlay,非两步)。
- **状态**:采用。ruff 净。**同 D-62(出战)模式:关键 click 前 mouse_move 缓解 bug#1**。待新局验 choose_partner 不再 flat-loop。· bug#1 + ADR-0009(三层完成验证,就地用)

## D-63 (2026-08-06) P2/F2:plan roll 找 target(_sample_shop 加 target 权重 + 攒金期 shop 无 target 时允许 roll) · cw_decisions
- **决策**:① `_sample_shop` 加 `target_comp` 参,target 阵营采样权重 2×(同 user priority);② `_best_improving_action` roll gate:攒金期(`_saving_for_level`)shop **无 target 卡**时允许 roll 找 target(原 `not _saving_for_level` 一刀切阻 roll)。
- **为什么(2026-08-06 plane2 r1 秒死暴露)**:bot 存活过 plane1 但 plane2 r1 hp100→0 一回合死。根因:shop 无 target(击破流萤)阵营卡 + gold44<升7级48 → `_saving_for_level` 阻 roll + plan 不买 off-target(攒金)→ `plan=[]` 带 spread board 进 plane2(高伤)→ 秒死。**蒙特卡洛 `_sample_shop` 只按 user faction_priority 加权,target 阵营不在 priority 时 roll 估值偏低 → bot 永不 roll 找 target → target 永不深成型**。
- **备选**:① 纯 directive roll(不评 delta,推翻:浪费 gold,target 真不供时白刷;蒙特卡洛估值 + target 权重更稳);② 不改采样只放宽 gate(推翻:采样不加权时 roll delta 仍低 → 放宽也不 roll,无效);③ F1 先(commit  supplied comp,推翻:F1 设计更大,F2 小步可独立验证 + 直接解 plane2 攒金不 roll)。
- **关联**:F1(track board commit)/ F3(深 stack 接线)/ comp_viability 是后续 P2 步(strategy/12)。本步(F2)是 P2 第一小步,实机验证。
- **状态**:**实验**(target 采样权重 2× + roll 放宽,待新局验证 roll 行为是否让 target 更深成型)。44 decisions 测试绿(+1 _sample_shop target 加权);ruff 净。· strategy/12 F2(P2 comp 成型)

## D-62 (2026-08-06) bug#1 缓解:出战 click 前 mouse_move(r9 出战 click ×4 未落地) · battle_prep
- **决策**:`BattlePrepCycle.battle` 点出战前加 `controller.mouse_move(_btn)`(零移动 click),同 `buy_store_item` 的 bug#1 缓解。
- **为什么(2026-08-06 r9 实跑)**:r9 boss prep 出战 click ×4「未落地」→ 备战单轮 fail → 循环。**手动 click(1784,731)即开战** → bot click 系统性落空,非按钮不存在。根因 = bug#1(`SrPcController.before_screenshot` 截图前移光标到角落 → op 截图后紧接 click,光标移动中落下,被游戏判拖拽落空)。出战 click 直接 `controller.click` 无 mouse_move → bug#1 裸露。r1-8 出战正常 = 间歇(bug#1 偶发),r9 连发(运气/时机)。
- **备选**:① 不改,靠 verify+retry(下行 round_retry 已有 ADR-0009 verify)兜底(部分:retry 的 click 也 bug#1 裸露 → 连发时 retry 也落空,mouse_move 治本);② 每 op 铺 mouse_move(推翻:CLAUDE.md「多数 click 正常,只间歇落空处加」,出战是已观察落空点);③ 改 before_screenshot 不移光标(推翻:框架级,跨项目,非本仓范围)。
- **状态**:采用。ruff 净。**待新局验**:出战 click 不再连发落空。· bug#1(`SrPcController.before_screenshot` 移光标)+ CLAUDE.md 缓解惯例

## D-60 (2026-08-06) 事件长尾:HandleSelectPartner 硬编码立绘坐标落候选间隙 → flat-loop · handle_select_partner
- **决策**:`HandleSelectPartner` 弃硬编码 `STAGE_PORTRAIT=(1048,299)` → OCR 候选阵营标签(label 行 y~362,2-4 字过滤)定位候选 → 点最左候选立绘 `(label_x, label_y-60)`(立绘在 label 上方~60px)→ 确认选择(OCR click,原已工作)。无候选兜底 (960,300)。
- **为什么(2026-08-06 实跑 flat-loop)**:08:36 局 1-7 节点 choose_partner iter131+ 反复「成功」画面不变(31 snap)。**probe 实测**(游戏 parked 在该屏):2 候选 护盾(label x890)/能量(label x1127),立绘 y~300;硬编码 (1048,299) **x=1048 落两候选间隙** → 点不中 → 确认选择无效 → flat-loop。点 (1127,300) 命中 能量 候选(高亮选中)→ 点 确认选择(1441,582)→ overlay 关闭回备战。**根因 = 硬编码 x 不随候选数/位置变**(2/3 候选间隙不同)。
- **备选**:① 改硬编码 x 到某候选(推翻:候选数/位置随事件变,硬编码必再间隙);② screen_info 建候选区(task#20,推翻:候选是动态横排,label OCR 更自适应,同 invest_env/card 模式);③ 点 label(card)而非立绘(推翻:probe 点立绘 y300 选中,label 362 未验证;立绘(label_y-60)自适应布局位移)。
- **状态**:采用。173 cw 测试绿;ruff 净。**待新局验**:choose_partner 是否一次过(不再 flat-loop)。TODO:策略化选伙伴(按 target_comp.core_chars,现取最左)。· 事件长尾(D-39 encounter 同类 flat-loop)

## D-59 (2026-08-06) 弱阵:maybe_pivot 信号1 倾向易成型 comp(best 易 + target 未成型 → 阈值降) · cw_comps
- **决策**:信号1 pivot 阈值随 best vs target 成型难度调节 —— `best.form_difficulty` 比 target 低(easy<medium<hard)**且 target 未成型**(form_progress<1)→ 阈值 ×`PIVOT_EASIER_FACTOR`(0.7,0.10→0.07),倾向转易 comp。target 已成型不降(不弃已完成 comp)。
- **为什么(2026-08-06 实跑弱阵深化)**:08:36 局 target=巡击青雀[medium,仙舟5+追击3=8卡],r3 列车同行[easy,S,4卡] gap **+0.097 卡 0.10 没转** → 巡击青雀 慢成型(shop 不供 仙舟/追击)+ board 散(买 off-target 能量:3)+ hp 持续掉(82→58→45)。列车同行 fewer 卡 + S 强 + bot 默认首选(挂机流)→ 转了成型更快更强、少掉血。**根因 = pivot 阈值对易/难 comp 一视同仁,没偏好易成型**(慢 comp 拖死)。
- **备选**:① 调 PIVOT_SCORE_GAP 整体(推翻:会影响所有 pivot,误伤;D-59 只对易 comp 降,精准);② commitment prefilter 收紧(已有 prefilter,shop 无 target 卡时允许 off-target 填充防饿死,收紧风险饿死/弱战力);③ 升 W_PROG 让 select_comp 偏易成型(部分,但 pivot 阈值才是 r3 没转的直接因);④ off-target filler cap(能量:3,推翻:off-target stack 也有 synergy 值,cap 未必更好;根因是慢 comp 不是 filler)。
- **关联坑**:OFF_TARGET_DISCOUNT 曾 0.3→致卖 off-target 深堆 churn→revert 1.0(见 cw_decisions 注释);D-59 不动 board eval(只调 pivot 阈值),无 churn 风险。
- **状态**:**实验**(PIVOT_EASIER_FACTOR 0.7 待多局校准)。40 测试绿(既有 maybe_pivot 无回归);ruff 净。log 加 `[易comp降阈]` 标记便于实机核实。**待新局验**:r3 类场景是否转 列车同行 + 存活更久。· 弱阵(D-53/56/58)+ task#16 commitment

## D-58 (2026-08-06) env_fit 接线 bug:已选投资环境从不存 state.active_env → T0 env 硬绑静默失效 · cw_strategy/handle_invest_env/default_strategy
- **决策**:`StrategySession` 加 `active_env: str`;`HandleInvestEnv` 选后写 `session.active_env = chosen`;`update_target` copy 到 `state.active_env`(make_score_context 前,同 briefing_affixes 模式)。
- **为什么(2026-08-06 实跑 + 代码核实)**:T0 env「昼之半神概念股」选了(score=100),board 已 昼之半神:2(向 昼神阿雅 成型),但 target=巡击青雀(0 仙舟/追击)。grep 证实 **`active_env` 只读(cw_comps:391)从不赋值** —— HandleInvestEnv 点了 chosen 卡却不存名 → state.active_env 恒空 → `env_fit` 全返 0.5 → ENV_COMP_AFFINITY(T0 env 近乎硬绑)静默失效。修后:昼神阿雅 env_fit=1.0(+board form_progress 0.5)→ comp_score ~0.375 >> 巡击青雀 ~0.075 → 会选/转向 env + board 支持的 comp。
- **备选**:① OCR 读 active_env(推翻:env 名屏上不常驻,选中后不可读;session 存是正解,同 briefing);② 只在 select_comp 用 env(推翻:update_target/maybe_pivot 都经 make_score_context,pivot 也要 env 信号);③ 存 active_strategy 投资策略(暂不:comp_score 不用投资策略,留 P2+ 视需要)。
- **状态**:采用。60 测试绿(env_fit 逻辑既有覆盖);ruff 净。**待新局验证**:T0 env 下是否选/转向 昼神阿雅(env+board 支持)而非 env-blind 选 巡击青雀。· 弱阵(D-53/56)+ ENV_COMP_AFFINITY

## D-57 (2026-08-06) app 起局 bug:_in_match 大厅误判「已在对局」(短词 lcs 0.5 误匹配)→ 跳过 start 空跑 · currency_war_app
- **决策**:`_in_match` 加 `_at_lobby` 短路(大厅≠对局中)+ `_IN_MATCH_KEYWORDS` 的 `round_by_ocr` 收紧 lcs 0.5→0.8。
- **为什么(2026-08-06 实跑)**:从大厅 run_standalone_app → 2.4s 空跑「对局结束,回大厅」。日志:`_start_match` 报「已在对局中,跳过 start 交 loop」→ loop 见大厅「创业指南」→ 3c 误「对局结束」。根因 = `_in_match` 用默认 lcs 0.5 全屏 OCR 短词:「出战」(2 字)匹配大厅「货币战争」(含「战」,1/2=0.5≥0.5 命中)→ 误判对局中 → 跳过 start。**同 D-37/D-50/D-54 round_by_ocr 默认 lcs 坑第 N 次**(短词 + 全屏 LCS = 误匹配高发)。
- **备选**:① 只收紧 lcs 不加 _at_lobby 短路(部分:其他大厅词可能仍误匹配,短路根治「大厅≠对局」语义);② 删「出战」短词(推翻:真对局时「出战」是有效锚点,收紧 lcs 即可);③ _in_match 也用 screen_info area(推翻:对局中态多(备战/事件/战斗/结算),建全 area 成本高,lobby 短路 + lcs 0.8 够)。
- **状态**:采用。ruff 净。验证:restart server → run_standalone_app → **正常起局**(点开始→简报→投资环境选 昼之半神概念股→备战→loop running)。· D-26 中间态接手

## D-56 (2026-08-06) 决策迹:maybe_pivot 加 log(弱阵诊断要数据,非猜) · cw_comps
- **决策**:`maybe_pivot` 3 信号(保命/涌现/ceiling)各加 INFO log —— 评估点 log 当前/最佳 comp、score、gap、决策(pivot X / 保持)。`select_comp` 暂不 log(每轮调用,select_comp top 已由 maybe_pivot 内部用)。
- **为什么(弱阵诊断)**:2026-08-06 整跑 bot round7 巡击青雀→DOT队 pivot 后 plane2 r2 战死。**根因代码级定位** = 信号1 用 `comp_score(best) > comp_score(target)+0.10`,而 comp_score 含 shop_supply 乘数(0.3+0.7×shop_supply,可达 ~3.3×)→ shop RNG 刷出他阵营牌 → 该 comp score 暴涨 → 误涌现 pivot → 永不深 commit → 弱阵死。但**修法值(PIVOT_SCORE_GAP / commitment 权重)需实跑 score/gap 数据校准**(原 match 日志 server 重启被截断丢失 → 无数据)→ 先加 log 采数据,再据数据调(D-57),**不凭猜定值**(D-35 教训:猜值误判)。log 亦永久 telemetry(决策迹复盘 + 未来 ML side door,§11.5)。
- **备选**:① 凭代码级根因直接调 PIVOT_SCORE_GAP/加 commitment(推翻:无 score 数据猜值,D-35 风险);② select_comp 也 log top3(推翻:每轮 noisy,maybe_pivot 已覆盖决策点);③ log 打 DEBUG(推翻:server 跑 INFO,DEBUG 不见 → 采不到)。
- **状态**:采用。66 pivot/comp 测试绿(log 行为中性);ruff 净。**next**:起干净对局采 pivot log → 据 gap 分布调 PIVOT_SCORE_GAP / 加 commitment hysteresis(D-57)。· 弱阵(D-53)

## D-55 (2026-08-06) task#73 续:AFFIX_MECHANIC_MAP 补 忍无可忍/沉重脚步(灼热轰炸 纯数值不入表) · cw_comps
- **决策**:MECHANIC_COUNTERS 补「多段惩罚」→[高频低单次]、「行动延后」→[速度依赖];AFFIX_MECHANIC_MAP 补 忍无可忍→多段惩罚、沉重脚步→行动延后。灼热轰炸**不入表**(纯数值)。
- **为什么(task#73 余词缀)**:① 忍无可忍(敌受 7 击提前 100%)→ 克高频多段(反甲白厄 高频低单次 多打→频触→敌频动),方向强,入表;② 沉重脚步(受击延后 8%)→ 克速度依赖(鞋队 tuning 被打乱),方向性入表;③ 灼热轰炸(前排受击+火 DoT)均匀影响所有 comp(无 comp flip;治疗护盾只是"抗"非"被利"),按「纯数值怪强化无 comp 交互不入表」原则(同 首领强化)**不入表**,mechanics_fit 中性 0.5 正确。
- **备选**:① 灼热轰炸 synergy 反甲白厄(推翻:反甲白厄 attr=高频低单次 非"受击反击",无 synergy attr 可挂;强挂伪造);② 忍无可忍 reuse「反伤」tag(推翻:机制不同 反伤=反伤 vs 多段=敌提前,语义混);③ 沉重脚步 reuse「速度抑制」tag(推翻:速度抑制=极端高速被抑 vs 行动延后=受击延后,语义混,用独立 tag「行动延后」清晰)。
- **状态**:采用。cw_comps test +3(忍无可忍/沉重脚步 behavioral + AFFIX_MECHANIC_MAP integration),40 绿;ruff 净。**task#73 剩余**:comp.boss_weakness 俗称→规范公司名对齐(boss_fit 永不命中,需游戏数据银行 boss 图鉴核对,游戏忙暂阻)。· task#73(D-49)

## D-54 (2026-08-06) 事件长尾:battle_loop 加 0f 消耗品详情浮层 → ESC 关(plane2 supply 后 modal 遮屏死循环) · battle_loop
- **决策**:battle_loop 加 0f 分支(0e 后、备战前):OCR 同时命中「消耗品」AND「拖动到」(均 lcs 0.9)→ `btn_tap('esc')` 关浮层 → round_wait 1.5。
- **为什么(2026-08-06 整跑暴露,plane2 新地)**:plane2 round1 hp=1 存活(DOT队)→ 补给节点 → 投资策略「星星相印」奖励【员工投影仪】消耗品 → 游戏自动弹消耗品**介绍 modal**(「员工投影仪/消耗品/拖动到...使用/道具使用后消失」)→ modal 遮挡备战/投资策略屏 → 上面 0-6 分支全不命中 → `round_retry` flat loop ~19min → 失败。**非策略死,UI 弹窗卡死**。前三局死 plane1 从未到 plane2,故未暴露。
- **验证(实机 probe,游戏 parked 在 modal)**:`analyze_screen` 仅抓到 modal 文字(无备战元素)= modal 全遮挡;`key_tap esc` → modal 关,露出「请选择投资策略」屏(分类器能识别)→ ESC 是有效 dismiss。视觉大模型确认 modal 右上有 X 关闭键 + 是模态遮挡。
- **备选**:① 点 X 关闭键(推翻:需稳定坐标,modal 居中但 X 坐标会随物品变;ESC 非定位无漂移,且 1b 详情弹窗已用 ESC 建惯例);② 建模 screen_info + close button area(推翻:transient dismiss overlay 非常驻屏,1b/2 已确立 OCR-dismiss 惯例,screen_info 过重;长尾若 item modal 繁多再升级);③ 只「消耗品」单条件(推翻:备战底部消耗品栏可能也有「消耗品」label → 误匹配备战 → ESC 打断备战;加「拖动到」(拖动使用说明只出现在详情 modal)双条件精确)。
- **状态**:采用。170 cw 测试绿;ruff 净。**装备类详情 modal**(无「拖动到」,如星星相印 也给简易装备)是长尾,观察到再补签名。验证待新局到 plane2 supply + modal → 0f ESC → 续跑。· §11 事件长尾 · insights(I21 待补:transient dismiss overlay 归类)

## D-53 (2026-08-06) 弱阵实验:comp early_power 早期战力先验 + _difficulty_phase_factor 早期偏 · cw_comps
- **决策**:Comp 加 `early_power`("高"/"中"/"低" 早期 plane1 战力先验)+ `_difficulty_phase_factor` 早期(round≤3 or gold<30)= `form_fac * power_fac`(偏 form_difficulty easy **且** early_power 高)。9 comp 标先验:列车同行=高 / 命运圣杯=中 / 击破流萤=中 / 贝洛伯格=中 / 万敌=中 / 巡击青雀=低 / 昼神阿雅=低 / DOT队=低 / 反甲白厄=低。
- **为什么(2026-08-06 整局暴露弱阵)**:DOT队(form_difficulty easy + B 级)plane1 r9 boss 战死(HP 62→0)。原 `_difficulty_phase_factor` 只偏 easy 成型 → DOT队 易成型被选,但 **DoT 慢热 plane1 弱**。加 early_power 维度(列车同行 A850 挂机=高 / DOT队=低)→ 早期偏易成型 **且** 早期战力强。
- **备选**:① 调 W_STR 偏 S 级(推翻:strength S/A/B 太粗,列车同行 S 但 progress 0 仍不选;early_power 直接标早期战力);② comp_viability 观测 blend(推翻:candidate 无观测未 commit,只 current comp 用;early_power 静态先验可立即用);③ 只 form_difficulty 不加 early_power(推翻:DOT队 easy 弱,没区分早期战力)。
- **状态**:**实验**(先验待多局实玩校准)。cw_comps + cw_decisions 80 测试绿。**下局验证**:早期是否选 early_power 高(列车同行)而非 DOT队 + 存活更久。若无效调权重/先验。· 整局弱阵(D-50 整跑)

## D-52 (2026-08-06) P1.5 refine:node_type 推断(结算屏「首领」→ boss) · battle_loop
- **决策**:`_record_round_outcome` node_type 从固定「普通战斗」→ 推断:结算屏 OCR 含「首领」(如「1-9首领」)→ `'boss'`,否则「普通战斗」。log 加 node 字段。
- **为什么**:P1.5 观测回路 node_type 原 all「普通战斗」(粗),boss/普通不区分 → PerformanceTracker trend 不能按节点类型分(boss 掉血 vs 普通)。2026-08-06 整跑 log:round9 结算屏「1-9首领」(boss 标签)可区分。词缀「首领强化」在简报不在结算屏 → 不误匹配。
- **状态**:采用。node_type 推断 + log node。实机验证待下局 boss 结算(node=boss)。· P1.5(D-48)

## D-51 (2026-08-06) P1.5 refine:失败结算屏「挑战失败」→ hp_after=0 conf=1.0(团灭确定) · cw_observation
- **决策**:`read_round_outcome` 加判:OCR 含「挑战失败」且 `parse_settlement_hp` None → `hp_after=0 conf=1.0`(团灭确定)。
- **为什么(2026-08-06 整跑暴露)**:plane1 round9 boss 战死 → 失败结算屏 OCR「挑战失败/小队生命值❤!/对局评价/下一步」。`parse_settlement_hp` 正则 `生命值\s*(\d+)` 不匹配「生命值❤!」(❤!非数字)→ None → hp_after=0 conf=0.0。但**失败 = hp 0 是 ground truth**(团灭),该 conf=1.0 进 PerformanceTracker trend(死信号,策略学)。
- **备选**:① 失败屏不记 conf=0(推翻:死是重要信号,该进 trend);② OCR「生命值」后取任意(推翻:❤!非数字,取 0 因「挑战失败」判,非解析)。
- **状态**:采用。失败屏 hp 0 conf 1.0。test_cw_observation +1,16 绿。**boss 结算屏「挑战结束」无「生命值」前缀**(只裸数字如「70」)→ 暂 conf=0,后续实机核实 boss 结算屏 hp 位置 refine。· P1.5(D-48)

## D-50 (2026-08-06) ↺ D-37 复发:0e 投资策略/环境 改用 id_mark area(全屏 LCS 误匹配失败结算屏) · battle_loop
- **决策**:battle_loop 0e 投资策略/环境检测 `round_by_ocr('投资策略/环境', lcs=0.8)` → 改 `round_by_find_area('标识-请选择投资策略'/'标识-投资环境', id_mark)`。补给阶段暂留(失败结算屏没「补给阶段」)。
- **为什么(2026-08-06 实跑暴露)**:loop plane1 round9 boss 战死 → 失败结算屏(对局未完成)OCR 含「投资策略/投资环境」(对局信息)+「标准博弈」(A8 标签)→ 0e 全屏 LCS「投资策略」命中 → 派 HandleInvestStrategy → handle 卡名行 OCR「标准博弈/试用」→ 点标准博弈@(423,477) → 没推进 → loop 反复(iter 340+)卡死。D-37(投资策略 LCS 误匹配「能量上限」)同类复发,这次是失败结算屏的「投资策略」对局信息。
- **备选**:① LCS 改「请选择投资策略」(推翻:子序列匹配,失败结算屏「投资策略」仍是「请选择投资策略」子序列 → LCS 高 → 误命中);② 先排失败结算屏「对局未完成」(推翻:多一分支,id_mark area 更根治);③ HandleInvestStrategy 入口核对 id_mark(部分,但 0e 派发就该准,handle 不该兜底 0e 误派)。
- **状态**:采用。0e 用 id_mark area(固定位置全等;失败结算「投资策略」在对局信息区,不在真屏 id_mark pc_rect → 不命中)→ 落 3b「下一页」回大厅。验证:loop 从失败结算 10.9s 回大厅(下一页 → 返回货币战争 → 创业指南 round_success)。方法论印证 screen-onboarding「固定位置用 area 非全屏 LCS」+ write-operation「LCS 子序列匹配是误匹配高发,独有长关键词 + area 才稳」。· insights I20

## D-49 (2026-08-06) mechanics_fit 数据对齐 + 补全:comp 属性对齐 MECHANIC 表 + 补皮糙肉厚/榜样激励 · cw_comps(task#73)
- **决策**:`mechanics_fit` 已接 `comp_score`(W_MECH),但 comp 属性 tag 跟 MECHANIC 表不对齐 → 命中少。对齐 + 补:① 列车同行 `[护盾]→[治疗护盾]`(对齐 counter 治疗削弱→治疗护盾);② `MECHANIC_SYNERGIES` 补「皮糙肉厚→[击破]」(利击破 comp);③ `MECHANIC_COUNTERS` 补「榜样激励→[高倍率单核]」(克单核);④ `AFFIX_MECHANIC_MAP` 补皮糙肉厚/榜样激励。
- **为什么**:`mechanics_fit(comp, mechanics)` 经 `comp.mechanic_attributes` 查 MECHANIC_COUNTERS/SYNERGIES。comp 标的属性必须 = MECHANIC 表属性 tag 才命中。原 列车同行[护盾] ≠ counter[治疗护盾] → 不命中(重症难题不克它);击破流萤[击破]/命运圣杯[高倍率单核] 无 MECHANIC 条目 → 永不命中。对齐后真生效(皮糙肉厚利击破、榜样激励克单核、重症难题克列车同行)。
- **备选**:① 不对齐维持现状(mechanics_fit 大半中性,词缀克制没生效 → 策略不适配词缀);② comp 逐词缀列举克制(推翻:数据驱动,comp 标属性 tag + MECHANIC 表查,不必逐词缀)。
- **状态**:采用。comp 属性对齐 + MECHANIC 补 2 条 + AFFIX_MECHANIC_MAP 补 2 词缀。test_cw_comps +3(击破+皮糙肉厚 synergy / 命运圣杯+榜样激励 counter / 列车+治疗削弱 counter),37 绿。**剩余**:召唤[召唤]无明确词缀交互暂不补;AFFIX_MECHANIC_MAP 仍部分(沉重脚步/忍无可忍/灼热轰炸 等待游戏知识);**comp.boss_weakness 名对齐 bosses.md/read_bosses OCR 名**(boss_fit 已接,但 comp 标的红绿灯/电视机/琥珀王/死龙 是简称,要核对 bosses.md 规范名)留。· competitors.md 策略映射

## D-48 (2026-08-05) P1.5 观测回路接线:battle_loop 结算屏 → read_round_outcome → on_round_end · battle_loop
- **决策**:CurrencyWarRunLoop「继续挑战」检测处加 P1.5 观测回路:结算屏(「挑战结束」)→ `read_round_outcome`(OCR hp_after,组件 D-38)→ `strategy.on_round_end`(默认实现 `performance.record(obs)`,记掉血 trend)。非结算屏跳过;失败不阻塞对局。plane/round 用 last-known(`read_phase_round` 结算屏不显);node_type 暂粗(普通战斗,boss/elite 后续)。
- **为什么(用户 2026-08-03 定调:观测驱动非预测)**:read_round_outcome(D-38 组件)+ on_round_end 钩子(D-34)+ PerformanceTracker 都就位,只缺 battle_loop caller。接上后 PerformanceTracker 记每回合 hp_after → 掉血 trend → 策略可据**观测结果**调 comp/mechanics 评分(而非盲预测赢率;版本鲁棒 —— V4.5 改数值,掉血照样掉)。
- **备选**:① 结算屏 read_game_state 拿 state 传 on_round_end(推翻:on_round_end default 只用 obs + session.performance,不用 state 其他字段;read_game_state 结算屏 OCR 多区域开销大,传 `GameState()` 空);② 每屏调 on_round_end(推翻:非结算屏无 hp_after,只「挑战结束」结算屏调,免误记)。
- **状态**:采用。battle_loop 接线(`_record_round_outcome` + 「继续挑战」前调);cw_strategy 15 测试绿(on_round_end default 不破坏)。实机验证待跑局(看 `[cw-loop] on_round_end` log hp_after 记录)。node_type 推断(boss/elite 节点追踪)+ on_match_end 真实 outcome 填充留后续。· strategy/11 §11.7(P1.5)

## D-47 (2026-08-05) 词缀效果采集:注册表单独 py(affix_effects_data) + 运行时自动写 + 固定采集对比 + 截图对账 · cw_observation/handle_briefing
- **决策**:敌人词缀效果(游戏原文 ground truth)用单独 py 注册表 `affix_effects_data.py`(`AFFIX_EFFECTS: dict[str,str]`,从 cw_comps 迁出,cw_comps 重导出不变)。HandleBriefing **固定采集**每词缀(点词缀弹 tooltip → `read_affix_effect` OCR 效果,纯解析找标题→取下方紧邻连续行 dy≤45)→ 对比注册表**文件最新**(`load_affix_effects_from_file`,exec 读)→ 新名/描述不一致 → 截图(`affix_shots/<词缀>.png`)+ `write_affix_effects` 写回注册表(`json.dumps` 合法 py);一致→跳过。**本轮下游不生效**(mechanics_fit 用内存 import 旧值),**下轮启动重新 import 生效**。
- **为什么(用户 2026-08-05)**:① 词缀效果要游戏原文(简报词缀只显示名字,点词缀弹 tooltip 才显效果;游戏内无词缀图鉴,网络无权威完整列表,competitors.md 攻略统计 ~50);② 注册表作"最后使用"权威源,运行时自动写(采到新/不准就校准)省人工 yml→py 同步;③ 对比跟注册表**文件最新**(非内存)→ 本轮内不重复写;④ 截图对账回查 OCR 没采错;⑤ 本轮不生效下轮生效可接受(用户明确)。
- **备选**:① yml 缓冲 + 人工同步进 py(推翻:多一步人工同步,用户要自动);② 对比跟内存 import(推翻:本轮写后内存不更新 → 本轮内重复采重复写);③ 只采注册表缺的(推翻:用户要固定采集校准,描述不一致也记录);④ read_affix_effect 限 y<960(推翻:硬编码不鲁棒,改标题下方紧邻连续行 dy≤45)。
- **状态**:采用。实机验证通过(HandleBriefing 采 4 词缀:软弱无力注册表故意改错→采到原文→写回正确+截图,其他 3 一致跳过;点下一步+自检离开简报)。15 测试绿。`load_affix_effects_from_file` exec 解析(**TODO 后续换 importlib.reload/ast**,不优雅)。mechanics_fit 接线留 task#73(注册表 effect 原文不喂策略,tag 走 `AFFIX_MECHANIC_MAP`)。· docs/game/screens/currency_war_briefing.md

## D-46 (2026-08-05) ↺ 推翻 I16「卡底 820 选中」:投资策略点卡名(y≈474)选中(白边+确认亮) · handle_invest_strategy
- **决策**:投资策略 3 选 1 点卡选中位置 = **卡名行(y≈474)**,非 I16 的「卡底 820」。`CARD_CLICK_Y` 820→474;screen_info「区域-卡牌描述行」(卡底)→「区域-卡名行」[200,455,1720,505];handle 改读 `area_center('区域-卡名行')`。
- **为什么(2026-08-05 实跑暴露 + 实机点验)**:loop 卡投资策略 ~4min(整局阻塞)。stop 后实机点验:点中产阶级卡名(461,474)→ 视觉白边选中 → 点确认(951,967)→ 推进备战 1-3(链路通)。**卡名 y474 选中**,非 I16「卡底 820」—— I16 凭「820 高亮+刷新次数变 0」误判(实际是刷新反馈,非选中)。点卡底 820 没选中 → handle 点 820 → loop 反复卡死投资策略。
- **备选**:① 维持 I16 卡底 820(推翻:实机点验不选中,loop 卡死);② 点描述区 545(推翻:旧 doc「描述区选中」,实为开角色详情,非选中;投资环境才用描述区选中,两 screen 选中位不同)。
- **状态**:采用。投资策略选中 = 卡名 y474(白边选中态)。实跑验证:修后 restart loop 推进 1-3→1-6 顺畅(投资策略过 ✓)。教训:选中位置必须实机点验 + 视觉确认选中态(白边)+ 链路验证(选中→确认→推进),别凭单次观察下结论。详见 insights I18(推翻 I16)。· screen_info `currency_war_invest_strategy`

## D-45 (2026-08-05) ↺ 修正 D-43:bug#1 机制真(before_screenshot 移鼠标→click 判拖拽),关键 click 前 mouse_move 缓解有效(非全删) · currency_war/框架
- **决策**:修正 D-43 对 bug#1 的过激判断。bug#1(op click 偶发不落地)**机制真**:框架 `before_screenshot` 每轮截图前移光标到角落(截图卫生)→ 紧接 click 光标移动中落下,偶被游戏判拖拽落空(间歇吞过渡按钮/结算翻页)。缓解:关键过渡 click 前 `mouse_move(target)` 再 click(零移动=不被判拖拽)。**不是 D-43 说的「根因纯抢鼠标 + 全删 mouse_move」**。
- **为什么(用户 2026-08-05 CLAUDE.md 修正)**:D-43 把 bug#1 全归「开发时抢鼠标」并删全部 mouse_move 缓解,过激。真相:① before_screenshot 移鼠标机制真(框架行为,**自动运行也在**,非纯抢鼠标),间歇吞 click;② 多数自动运行 click 正常,只在间歇落空处加 mouse_move,别每 op 铺;③ 手动测不稳定先怀疑**自己在抢鼠标**,别急着归框架 bug。
- **备选**:① 维持 D-43(全删 mouse_move,推翻:间歇落空处无缓解会吞 click);② 每 op 铺 mouse_move(推翻:多数正常不需,污染)。
- **状态**:采用。bug#1 缓解策略 = 关键过渡 click 前 mouse_move(按需,非全铺)+ 手动测不稳先怀疑抢鼠标。**D-43「全删」部分推翻**(间歇落空处该保留 mouse_move;此前删的若实跑暴露间歇吞 click 再按需加回)。详见 insights I17(修正 I15)。

## D-44 (2026-08-05) 简报首领识别链路 —— read_bosses → state.bosses → boss_fit(对称 affix 链路)· start_currency_war_match/cw_observation
- **决策**:简报屏加读 3 位面 boss 名(`read_bosses`,OCR「区域-首领行」area)→ `ctx.cw_briefing_bosses` → `session.briefing_bosses` → `state.bosses` → `boss_fit(comp, bosses)`。对称 D-43 之前的 affix 链路(read_affixes → state.enemy_affixes → mechanics_fit)。
- **为什么(用户 2026-08-05 指出)**:简报层 review 时只识别了敌人词缀,漏了首领。简报屏 3 boss 横排卡片(立绘 + 红色阵营标签 + 名字),开局预览 3 boss 是规划投资策略的关键(攻略共识「刷开局看 boss 选投资环境」)。**3 位面是玩法结构,所有难度(A5/A8/A850)固定 3 个 boss,不随难度变**(2026-08-05 攻略 + 官方确认;难度只改敌人强度/词缀,不改位面数)。
- **备选**:① 连阵营标签一起 OCR(推翻:红色背景白字 OCR 干扰大,阵营价值低于名字;先采名字,阵营待视觉核实后再定);② 采 boss 机制/克制(推翻:简报屏不显示 boss 机制,要查图鉴,属数据层后续浏览器补,同 competitors.md 待确定);③ 只存 boss 数量不存名字(推翻:`boss_fit` 用名字匹配 `comp.boss_weakness`,要名字非数量)。
- **状态**:采用。识别链路通(`read_bosses` → ctx → session → `state.bosses` → `boss_fit`)。**数据层待补**:`comp.boss_weakness` 当前多为空 → `boss_fit` 暂中性 0.5;boss 机制 + 哪些 comp 怕哪个 boss 待图鉴采集(同 competitors.md,后续浏览器/实玩)。测试 `test_read_bosses_briefing`(3 boss)+ entry_flow a8 assert 3 boss,绿。· docs/game/screens/currency_war_briefing.md

## D-43 (2026-08-05) ↺ 推翻 bug#1:根因是开发时用户抢鼠标,非框架 bug → 删全部 active_window/mouse_move 缓解 · currency_war 全域
- **决策**:撤销 bug#1 的全部缓解代码 —— 删 currency_war 10 文件的 `active_window()` + `mouse_move()` + 配套 `time.sleep(0.3)`(mouse_move→click 之间)+ bug#1 注释;删 memory `before-screenshot-moves-mouse-breaks-clicks`。
- **为什么(用户 2026-08-05 澄清)**:bug#1(op `controller.click` 偶发不落地,手动 click_game 同坐标有效)的根因是**开发/调试时用户手动抢鼠标**干扰,非框架自动化运行问题。实际 bot 自动运行时无人抢鼠标,click 正常落地。之前三次根因判断全是误判 —— I11(失焦)/续7(server 长跑退化)/续11(pre_delay 间隙抢焦)/memory(before_screenshot 移鼠标判拖拽)都把「用户抢鼠标」的人为干扰误当框架 bug,铺了 10 文件过度防御(active_window/mouse_move 散布),污染代码且不可维护。
- **备选**:① 保留缓解(推翻:基于错误根因,active_window 散布每个 op 不可维护);② 只删 active_window 保留 mouse_move(推翻:mouse_move 同基于 bug#1「判拖拽」误判,一并删);③ 保留作「防御性」(推翻:用户立场「自动化运行不该考虑窗口被抢,否则到处 active_window」)。
- **状态**:采用。删 2 active_window + 14 mouse_move + 15 sleep + bug#1 注释(battle_loop/battle_prep/handle_invest_env/strategy/deploy_not_full/select_partner/encounter/run_supply/megastar + enter_currency_war 注释);ruff 全净;grep 无残留;memory 删。**注:op 残留的 verify-retry(battle_prep 出战后检测仍在备战→retry)保留 —— 那是「等动画/加载」的安全网,非 bug#1 缓解。** 详见 insights I15(推翻 I11/续7/续11)。

## D-42 (2026-08-05) 「开始对局/返回最高职级」检测 area 化 —— 根治「开局不利」LCS 误匹配 · start_currency_war_match
- **决策**:`advance_to_prep` 的「返回最高职级」「开始对局」检测从全屏 `round_by_ocr` 改 `round_by_find_and_click_area`(crop 难度确认 area),删手动 `area_center`+click(改用 helper 一体)。
- **为什么**:全屏 `round_by_ocr`(lcs 0.5)误匹配 —— 「开始对局」与简报 boss 词缀「开局不利」共享「开局」(2/4=0.5=默认阈值)→ **简报屏误触发难度确认的「开始对局」分支** → click 开始对局 area(1691,965)60 次死循环超时(行为测试 recorded_clicks 暴露)。方向 1(area 化)根治:crop 难度确认 area 限定位置,简报上该 area 无「开始对局」→ 不误命中。
- **备选**:① 收紧 lcs 0.8(D-37 惯例,治标);② area 化(采用,方法论首选,根治)。crop area OCR 对小 area 有漏字风险(见测试 refine)。
- **状态**:采用。ruff 净。行为测试验证中(mock 暴露 crop OCR 漏字新问题,refine)。· `start_currency_war_match.py:advance_to_prep`。

## D-41 (2026-08-05) shop_supply:shop presence 主导,board-only 降为弱信号(0.3)—— 修 comp 成型弱 · cw_comps
- **决策**:`shop_supply(comp)` 改判可成型 = **shop 出现该 comp 阵营 → 1.0;仅 board 有、shop 无 → 0.3**(旧 1.0);都无 → 0.0。
- **为什么(I14)**:2026-08-05 P1 验证 match 全程 board **多样不收敛**(7+ 阵营×1),comp 永不深堆成型 → 弱阵 → HP 持续掉 → 死。根因:旧 `shop_supply` 把「board 持有 1 张」当「可成型」(1.0)→ select_comp 不降权「board 有但 shop 供不上核心」的 comp(如 board 昼之半神:1 + shop 无 昼之半神 → 仍选昼神阿雅)→ 选了成型不了的 target → shop 买不到核心 → 永不成型。**「board 已有 1 张 ≠ 能成型」,可成型必须看 shop 能否买到更多核心**。
- **备选**:① shop_supply 只看 shop、board 不计(推翻:board 已有也是信号,完全不计太激进,可能频繁切 target);② 维持旧 1.0(推翻:win-rate 核心阻塞,实测致死);③ 按需求数加权(shop 有 N 张/comp 需 M 张 → M/N;更精但需牌池计数,留 refine)。
- **状态**:采用。74 既有 cw 测试全绿(相对排序保持:成型 comp 即便 ×0.51 仍胜 unsupplied)+ 3 新 shop_supply 测试锁定(shop=1.0 / board-only=0.3 / 都无=0.0)。配合 D-40(保命优先),target 选择现在既看 shop 供给(早选可成型)又低 HP 稳定(不 churn)。next 实跑验证:下局 board 应更聚焦(target 与 shop 供得上对齐)、HP 掉得更慢。· `cw_comps.py:shop_supply` / strategy/03。

## D-40 (2026-08-05) maybe_pivot 信号3(保命)优先于 1/2 —— 防低 HP target 振荡 churn · cw_comps
- **决策**:`maybe_pivot` 把**信号3(保命转型)提到信号1/2 之前**;hp 危险(< 0.75×effective_hp_threshold)时**独占** —— 返回最快成型的 easy comp(typical_form_round 最小,稳定不 churn),信号1/2 不参与。
- **为什么**:2026-08-05 实跑,P1 验证 match 在 plane1 末期 HP 低时,**target 振荡 churn**:列车同行→巡击青雀→DOT队→昼神阿雅(几轮内 4 次换)→ board 跟着 churn → 永不深堆成型 → HP 耗尽死亡螺旋。根因:低 HP 时**信号1(更优涌现)先于信号3 触发** —— 信号1 选 select_comp 的 best(随 board/shop 每轮变 → 振荡)+ 会选到**高难度 comp(昼神阿雅 hard)**;信号3(选最快 easy,稳定)被抢占。保命语义下,该切**稳定的最快成型 comp**,不该每轮追 volatile best。
- **备选**:① 信号1 加 hysteresis(要求新 comp 连续 N 轮更优才切)—— 推翻:保命时根本不该追更优,该直接独占信号3;② 增大 PIVOT_SCORE_GAP —— 推翻:治标,board 波动大时仍会振;③ 信号3 仍放后面但加「hp 危险时跳过信号1」守卫 —— 等价于提前,不如直接重排清晰。
- **状态**:采用。30 既有 cw_comps 测试全绿(5 maybe_pivot 测试兼容:低 hp 测试 hp=20 仍信号3,健康测试 hp=100 跳过信号3 走 1/2)+ 新测试 `test_maybe_pivot_low_hp_signal3_preempts_signal1` 锁定(低 HP 即使更优 comp 涌现,也只切最快 easy,非高难度 comp)。next 实跑验证:下局低 HP 时 target 应稳定(不再 churn)。· `cw_comps.py:maybe_pivot` / strategy/03 信号3。

## D-39 (2026-08-05) ↺ 修正 D-35:遭遇节点**有** 3 难度选择 UI → re-activate HandleEncounter dispatch(lcs 0.9)· battle_loop 0c / handle_encounter
- **决策**:撤销 D-35 的「移除遭遇 dispatch」—— 在 `battle_loop` 0c **重新**派发遭遇节点屏到 `HandleEncounter`,检测关键词 `'遭遇其一'` 用 **lcs_percent=0.9**(非 D-35 时的默认 0.5)。
- **为什么(D-35 是误判)**:D-35 称「遭遇 round = 普通战斗,无选项选择 UI」并删了 dispatch。**2026-08-05 实跑再证实**:遭遇节点**有** 3 难度选择 UI —— 屏「遭遇节点」+「遭遇其一/其二/其三」(难度递增)+ 奖励(金币/幸运星)+「选择」按钮。loop 删了 dispatch 后到该屏死 retry(iter75+,卡 plane1→plane2 间的遭遇节点)。D-35 删 dispatch 的**真实根因**是旧 0c 用默认 lcs 0.5 把**备战屏「遭遇」标签**误匹配(LCS 2/4=0.5)→ 备战屏瞎点 CARD_LEFT 卡死;**正解 = 收紧 lcs(到 0.9),非 removal**。`HandleEncounter` 自身检测本就 0.9(handler 2026-08-04 实测交互:点卡身选中 → 点选择确认),且 D-35 只删了 loop dispatch、handler 一直留着 —— 故 re-activate dispatch 即恢复。
- **备选**:① 维持 D-35 removal(推翻:遭遇屏实有选择 UI,不处理必卡死);② 给遭遇屏建 screen_info area 用区域识别(方法论首选,留 refine —— 现沿用 handler 既有兜底坐标 CARD_LEFT/SELECT + lcs 0.9 OCR 检测即解)。
- **状态**:采用。`HandleEncounter` 暂用启发式默认选**左卡 = 遭遇其一 = 最易**(金币×2;低风险,适合未成型 comp);`decide_encounter` 策略化(按 comp 成型度 + 词缀选难度)留 follow-up(handler TODO)。影响 strategy/11 §11.3.4⑤:`decide_encounter` 钩子**不再因「无 UI」dormant**,而是「handler 暂用启发式,OCR 选项 + 钩子接线留 refine」。· `battle_loop.py:146-156` / `handle_encounter.py`。

## D-38 (2026-08-05) P1.5 观测回路 OCR 组件:结算屏 hp_after 解析 · cw_observation
- **决策**:P1.5(观测回路,D-36 列为 next)的第一块零件:``cw_observation.parse_settlement_hp``(纯函数)+ ``read_round_outcome``(OCR 全屏 → ``RoundOutcome``)。**组件就位 + 单测,``battle_loop`` 的 ``on_round_end`` 接线留下局**(避免杀当前验证 match;留下局部署)。
- **结算屏形态(2026-08-05 实跑 OCR 确认)**:战斗后「挑战结束/数据统计/继续挑战」屏,展示「小队生命值<N>」(战后 HP)+ 总伤害 + 连胜。实测 OCR:`['挑战结束','战斗','小队生命值71i','数据统计','连胜×0','继续挑战',...]`(战前 84 → 战后 71,本战损 13)。
- **为什么(解析用「紧邻数字」)**:``parse_settlement_hp`` 用 ``re.search(r'生命值\\s*(\\d+)', t)`` 取「生命值」**紧邻后方**数字,而非首部/尾部 —— 防投资策略描述「每损失20点小队生命值获得5」(偶同屏/同 OCR)误取 20/5。「紧邻」语义:数字紧跟「生命值」(允空格),隔汉字即不算。越界(HP_MIN..HP_MAX)丢弃。
- **备选**:① 区域 OCR(给结算屏建 screen_info area for 小队生命值)—— 方法论首选,但需结算屏建档(本次用全屏 OCR 解析即解,区域留 refine);② 尾部数字 ``(\d+)\D*$`` —— 推翻:「每损失...生命值获得5」尾部是 5,误取;紧邻数字才区分得开。
- **状态**:采用。6 单测全绿(``test_cw_observation.py``:结算 71、无噪声 84、拒非紧邻、无文本 None、越界丢弃、0 允许)。next:``battle_loop`` 接 on_round_end(结算检测 → read_round_outcome → ``strategy.on_round_end``)+ node_type 推断(boss/elite 节点追踪)。· strategy/11 §11.7/§11.12 P1.5。

## D-37 (2026-08-05) loop 0d「未达上限」LCS 误匹配「能量上限」→ 收紧 lcs 0.5→0.8 · battle_loop 0d / handle_deploy_not_full
- **决策**:`battle_loop` branch 0d(未达上限弹窗 dispatch)+ `HandleDeployNotFull` 的检测关键词 `'未达上限'` 收紧 `lcs_percent` 默认 0.5 → 0.8。
- **为什么**:投资策略屏的策略描述含「能量上限」(如"同于能量上限20%的能量"),与「未达上限」共享子序列「上限」(LCS 2/4 = **0.5 = 默认阈值**)→ branch 0d 误匹配 → 投资策略屏被吞,反复触发 `HandleDeployNotFull`(其点击落在错误坐标,不消 overlay)→ 对局卡死(2026-08-05 实跑,P1 验证时暴露)。真「未达上限」弹窗 4/4 命中,0.8 不影响;「能量上限」2/4=0.5 < 0.8 不再误匹配。同 loop 其他分支(0a/0b/0e)早就在 0.7-0.9,唯独 0d 漏在默认 0.5。
- **备选**:**区域识别**(给 `currency_war_deploy_not_full` screen_info 加「未达上限」text area,loop 用 `round_by_find_area` 检测 —— 方法论首选,用户立场「round_by_ocr 全屏=偷懒」)—— 留待 deploy 弹窗建档补 text area 后改;本次最小止血用 lcs 收紧(与 loop 既有惯例一致,即解)。
- **状态**:采用。实机验证:修复后 loop 正确走 0e → `HandleInvestStrategy`(`decide_invest` 选「正能量」)+ 继续 prep(`update_target` 列车同行 + `decide_prep` Buy/Deploy),不再卡 `HandleDeployNotFull`。· `battle_loop.py:155-159` / `handle_deploy_not_full.py:36`。

## D-36 (2026-08-05) 策略插件 P1 落地(接口 + 接线,零行为变化)· strategy/11 §11.7/§11.12
- **决策**:D-34 设计的 **P1** 落地 —— 新建 `cw_strategy.py`(`CwStrategy` ABC 全 abstract 钩子 + `StrategySession` + `CurrencyWarMatch`)+ `cw_strategy_manager.py`(`StrategyManager` 发现,仿 `ApplicationFactoryManager` 但省 factory/const 配对)+ `strategies/default_strategy.py`(`DefaultCwStrategy` 薄委托既有 `cw_decisions`/`cw_comps`);`CurrencyWarConfig` +`strategy_id`/`strategy_seed`;`SrContext` +`cw_match`(显式声明 + reload 重置,字符串注解免运行时 import)+ `currency_war_strategy_plugin_dirs`;`battle_loop` 每局建/毁 match + `on_match_start`(_iter==1)/`on_match_end`(桩 `MatchOutcome()`);`shop` 走 `strategy.update_target`+`decide_prep`(删 `BuyShopCards._target_comp` class-attr hack);`handle_invest_*` 走 `decide_invest`。
- **为什么**:把"散落模块函数 + `_target_comp` class-attr hack"换成"单一 strategy 对象 + session",**不动战术层逻辑**(默认策略薄委托既有函数 = 今天打法)。P1 = 零行为变化,让插件替换口子立即可用(用户/参赛者可写策略);P2 地道化(逻辑迁进方法、删模块函数)后续。
- **备选 / 行为等价说明**:
  - **rng 合并**:`decide_prep` 用 `session.rng` 替代 `plan` 每调用新建 `random.Random()`。旧 = per-call 真随机,新 = per-session 真随机(未种子时)。两者都真随机、**分布同(均匀)、用户不可观测差异**;合并后**可种子化**(比赛公平 / replay 复现)= P1 目标之一(§11.4),非 bug。
  - **观测回路(`on_round_end`/真实 `on_match_end` outcome)留 P1.5**:P1 框架不构造 `RoundOutcome`/真实 `MatchOutcome`(需结算屏 OCR 探查,未做)→ 这两钩子 P1 无 caller;默认方法体就位(`record`/no-op),随阶段5 OCR 落地才接。
  - **supply/megastar/partner/boss 钩子 ABC 里就位 + 默认委托,但 handler 不 rewire**(OCR 缺 / dispatch 已删),随阶段5。
- **状态**:采用。**验证**:130 既有 cw 测试 + 15 新 plugin 测试(`test_cw_strategy.py`:发现/去重/THIRD_PARTY/default 委托/session+rng)全绿;ruff 净(sr_context 剩 11 错误全为既有 `Optional`/`List` 旧式风格,非本次引入);实机端到端确认(`[cw-strategy] 发现 1 个策略 default` + `[cw-env] decide_invest` + `[cw] target=击破流萤 decide_prep`,新 strategy 对象经全链路执行)。· strategy/11 §11.7/§11.12;P1.5 观测回路 / P2 地道化 待续。

## D-35 (2026-08-05) 遭遇 round = 普通战斗,移除 HandleEncounter 2选1 dispatch · battle_loop / handle_encounter
- **决策**:遭遇节点 round 改判为**普通战斗**(无选项选择 UI,只有难度标签 + 出战),走正常 prep→出战→战斗(`battle_loop.py` branch 1 `BattlePrepCycle`);移除原 `HandleEncounter`(2选1)dispatch。
- **为什么**:`doc(currency_war_encounter.md)` + 实机 + verifier 三方确认:遭遇 round **没有选项选择 UI**(原 2选1 是误判)。原 `HandleEncounter`(点卡身选难度档 + 选择)对着不存在的 UI 操作 → stall。
- **备选**:保留 `HandleEncounter`(推翻:无选项 UI,2选1 前提不成立)。
- **状态**:采用。`battle_loop.py` 删 `HandleEncounter` import + 0c dispatch(改注释);`HandleEncounter` op + `cw_decisions.decide_encounter` 纯逻辑 + 测试**暂留**(待确认全代码库无他用再删)。⚠️ **本条后补**(代码先改、决策日志漏记,违反「实跑演进当场记 D-NN」;strategy/11 review r2 发现此缺口 → 现补)。影响 strategy/11:`decide_encounter` 钩子按本条 dormant(见 strategy/11 §11.3.4⑤)。· `battle_loop.py:124-131` / §08。

## D-34 (2026-08-05) 策略插件机制:`CwStrategy` ABC + `StrategySession` + `StrategyManager`(对标 app 插件)· strategy/11
- **决策**:把货币战争的「决策大脑」抽象成**可替换的 `CwStrategy`**(无状态 + 模板方法全默认)+ **每局内存态 `StrategySession`**(持 target_comp/rng/performance/memory,替代 `BuyShopCards._target_comp` class-attr hack)+ **`StrategyManager`**(对标 `ApplicationFactoryManager` 的约定式文件扫描 + BUILTIN/THIRD_PARTY 双源,但无 factory 间接 —— 策略 `cls()` 即实例化,元数据走类属性)。覆盖**全部局内决策**(备战 plan + 投资策略/环境 + 补给 + 遭遇 + 巨星 + 选伙伴 + boss 克制 + target_comp 选择/转型)。内置 `DefaultCwStrategy` 分两阶段:P1 薄封装委托现有 `cw_decisions`/`cw_comps`(零行为变化),P2 地道重构(逻辑迁进方法、删模块函数)。服务「用户自写策略」+「社区策略比赛」。详 strategy/11。
- **为什么**:用户要「封装一个基类,接收完整局面、出下一步决策、留临时数据口、为插件机制/策略比赛留缺口」。现有决策是**散落的模块函数**(`plan`/`decide_event`/`select_comp`… 各处直调)+ **跨步状态 ad-hoc**(`_target_comp` class-attr),无单一替换切口 → 换打法得 monkey-patch 多处。三大设计选择:
  - **范围 = 全部局内决策(非仅备战)**:一个 strategy 对象 = 一整套打法,最契合「用自己的策略玩」+ 比赛(比拼完整打法)。备战只是举例。
  - **无状态策略 + 显式 session(非有状态实例)**:策略实例不持每局可变状态,全进 `StrategySession`(框架每局新建/局终销毁)。收益:可重入、可并行(比赛批量跑 1000 局)、可种子化(`session.rng`)、可离线测、无隐藏状态跨局泄漏。这是服务比赛的关键杠杆。
  - **发现机制 = 对标 app 插件(非 entry-points / 非 dotted-path)**:用户明问「现在的 application 怎么做」→ 照 `ApplicationFactoryManager`(文件扫描 + BUILTIN `src/.../strategies/` + THIRD_PARTY `plugins/currency_war_strategies/` + 复用 `plugin_module_loader` + 去重 + 热重载),体验与 app 插件一致;参赛者丢文件即进 GUI 下拉。省 factory 间接(策略无 config/run_record 机制)。
- **备选**:① **entry-points**(推翻:更重、需参赛者会打包,且背离框架既有文件扫描模式);② **有状态策略实例**(推翻:隐藏状态、难重置、不能并行、跨局泄漏风险 —— 不服务比赛批量评分);③ **纯抽象 ABC 强制实现全部钩子**(推翻:参赛门槛过高;模板方法全默认让「只换个买牌策略」低门槛);④ **范围仅备战 shop**(推翻:用户「之类的」暗示不止;仅备战换不了选事件/boss,比赛维度窄);⑤ **跨局持久化 session**(推翻:YAGNI + D-04「持久化默认不碰」;跨局采集走既有 telemetry,不造第二套);⑥ **沙箱隔离第三方策略**(推翻:与第三方 app 插件同威胁模型,`plugins/` 已自动 import 执行,本机制不引入新威胁面;诚实记录「进程内全信任」,比赛在受信任环境跑)。
- **状态**:采用(设计定案,设计文档 strategy/11 已写,经 r1 双 reviewer 审过;实现待跟进)。交付:P1 接口+接线+薄委托默认(**战术层**零行为变化,低风险)→ **P1.5 观测回路接线**(结算屏 OCR → `RoundOutcome`/`MatchOutcome`,需游戏)→ P2 内置地道化(中风险,测试保绿)→ P3 比赛基建(replay/batch_score + 参赛骨架)。**接口在 P1 冻结**,P1.5/P2/P3 不破坏它。向後兼容:`strategy_id` 默认 `"default"` = 今天战术层打法(观测钩子 P1 期 no-op,不影响行为)。· strategy/11(what)/ 落点:`cw_strategy.CwStrategy`/`StrategySession`/`CurrencyWarMatch`、`cw_strategy_manager.StrategyManager`、`strategies/default_strategy.DefaultCwStrategy`、`shop.BuyShopCards.buy`(删 `_target_comp`)+ `battle_loop.__init__`(建/毁 match)、`sr_context.cw_match`/`currency_war_strategy_plugin_dirs`、删 dead code `handle_megastar.py`、`cw_decisions`+`cw_comps` 迁进 `DefaultCwStrategy`(P2)。· §01/05/06/10。

## D-33 (2026-08-05) maybe_pivot 信号2 加「已成型守卫」(不放弃已完成 comp)· cw_comps
- **决策**:`maybe_pivot` 信号2(ceiling 不可达 → 切 easy)加守卫 `form_progress(target, state) < 1.0` —— target 已成型(board 全 tier 达成)时**豁免**信号2,不因 `typical_form_round > remaining` 切走已完成的 comp。
- **为什么**:原逻辑 `if target.typical_form_round > remaining:` 无视成型度 → 已成型的 target(plane3 后期 remaining 小)会被误判"来不及成型"切走 → 放弃已完成的强 comp 转切 easy,反而变弱。**正确性 bug**(不该放弃已完成 comp),非调参。补 maybe_pivot 信号1+2 测试时发现。
- **备选**:① 不修(推翻:已成型 comp 是最强态,切走=自毁);② 守卫用 `< 0.9` 而非 `< 1.0`(推翻:0.9 近成型仍可能来不及,该让 `form_round>remaining` 判定;只有全成型 1.0 才确定不该切)。
- **状态**:采用。+ 1 测试(`test_maybe_pivot_formed_target_no_ceiling_pivot`:阿雅成型 board={昼之半神:4}+ plane3 round5 remaining≈1 → 不切);cw_comps 30 测试绿。· `cw_comps.maybe_pivot` 信号2。· §03。

## D-32 (2026-08-05) difficulty → hp_safe_threshold 派生(向后兼容,A8 高难保血地基)· cw_state / cw_decisions / config
- **决策**:加 `GameState.difficulty`(A1..A8,匹配开始从难度确认屏检测)+ `CurrencyWarConfig.difficulty_hp_override`(难度→保血阈值映射,默认 A1-A4=40 不变 / A5+ 升阶)+ `effective_hp_threshold(state, config)`(cw_state)。3 处阈值读取统一走它:evaluate → `_phase_weights`、plan → `_refresh_cap`、`maybe_pivot`(0.75×)。**向后兼容**:difficulty 未检测("")或 override 无对应键 → 回退 `hp_safe_threshold`(默认 40 = `HP_DANGER`),行为与加 difficulty 前**完全一致**(detection 未接线时零变化)。
- **为什么**:cw_decisions 长期 TODO(:194「待 difficulty 字段」、:206「待补 A8 difficulty 信号」)—— A8 高难敌人更凶,固定 threshold=40 偏低(过晚弃息保血 → 失血过多);高难应更早保血。**离线地基**:detection(难度确认屏 OCR → `state.difficulty`)是后续 game 接线任务;本改动先把「阈值随难度变」的 plumbing + 派生函数 + GameState 字段就位,detection 落地即生效(不再动决策代码)。关 D-18(hp 阈值统一)的 difficulty 维度。
- **备选**:① 直接改死 `HP_DANGER` 常量(推翻:全局生效、低难也变、不向后兼容,A8/低难该不同阈值);② 加 difficulty 字段但不派生、等 detection 全做完再接(推翻:detection 时要同时改字段+函数+3 处位点,更碎;先做离线地基更稳,且向后兼容不破坏当前未验证跑)。
- **状态**:采用。代码 + 5 新测试绿(`test_effective_hp_threshold_*` ×4 + `test_eval_difficulty_aware_hp_threshold` 集成证 difficulty 改变 eval 行为);现有 cw_decisions/cw_comps 测试向后兼容通过。`DEFAULT_DIFFICULTY_HP`(A5+ 升阶)是**保守起步,待实机校准**(detection 接线后看 A8 实际失血曲线调)。· `cw_state.effective_hp_threshold` / `currency_war_config.DEFAULT_DIFFICULTY_HP` / `cw_decisions` evaluate+plan / `cw_comps.maybe_pivot`。· §02A3。

## D-31 (2026-08-04) 巨星卡死真根因 = bug#1(↺ 推翻 D-30 的"2 步缺 step2")· run_megastar_node
- **决策**:巨星节点卡死 6min 的真根因是 **bug#1**(确认 click 走 `round_by_ocr_and_click`,其 `before_screenshot` 把鼠标移到角 → click 判 drag 被吞 → 确认永不落地 → flat loop 无限 `round_wait` 烧预算),**不是**漏选强化角色。强化角色**可选**(不选也能确认推进)。修 = `RunMegastarNode`:`mouse_move`+`click`(bug#1 零移动缓解,同 invest handler)+ RunNode 验证(overlay 消失=完成)+ 节点预算(点不动 bail,不再 2.5h 烧)。
- **为什么(实机,MCP + VLM 结合)**:① OCR ground truth ——「强化角色未选择」持续在,点确认(MCP `click_game` 直连、无 before_screenshot)后该字消失、overlay 关 = **节点推进了**;② open-prompt VLM —— 看到花火有**金色发光边框 = 已选中**(窄 prompt 之前漏看、误报"没选中"→ 误判缺 step);③ 综上:花火早被 bot 的候选 click 选中,唯一卡点是确认 click 被 bug#1 吞,我直连点确认一发即中。
- **备选**:D-30 的"补选强化角色 step2 / 候选选中机制不明"(↺ 推翻:强化角色可选非卡点;候选早选好了,D-30 的"选中机制不明"是窄-prompt 视觉大模型 漏看金边造成的误判)。
- **状态**:采用。`RunMegastarNode` 代码完成(ruff 净 + 导入/结构验);**行为验证待下次巨星节点**(bug#1 缓解后应一发推进;现游戏已过我手动推进的巨星、在备战 1-6)。· `run_nodes/run_megastar_node.py` / `battle_loop` 0b。
- **方法论(回应用户"prompt 限制 VLM" + "MCP 和 VLM 都用")**:① **VLM 探索未知画面先 OPEN prompt**(描述全部),窄/leading 问法**压制题外输出** —— 我窄 prompt 漏看金边 → 误判"没选中" → 误以为缺 step → 跑去问用户;open prompt 一眼看到金边。② **MCP(OCR ground truth)+ VLM(open 枚举/选中态)+ click(验证交互)三结合** —— 各取所长:OCR 可信、VLM 看非文本元素/状态、click 验行为。③ **这条经验 → `od-dev-screen-onboarding`(open 枚举)+ 视觉大模型 用法 memory(open prompt 先)**。

## D-30 (2026-08-04) 巨星节点机制缺口 + 早期恶性循环(实机发现,待解)· handle_megastar / 策略
- **决策(发现,非定案)**:① 巨星(位面首领,每位面第 6 关)是**2 步节点**(选候选成巨星 + 选强化角色 + 确认),`HandleMegastar` 只做第 1 步 → 确认被拒(「强化角色未选择」)→ 节点永不完成;② 但"候选怎么选中"**机制不明**(点卡片本体 (925,240) / 名字条 (820,333)/(920,343) 均不选;点「详情」能开浮层=点击落地✓;视觉大模型 状态推理不可信;web 搜索无果)→ 需用户/人肉实机观察;③ 更深:bot 早期战力弱 → 输回合 → 穷 → 升不起级 → 弱 comp → 继续输(**恶性循环**),level gate+saving(D-24/D-28)必要非充分。
- **为什么**:实机迭代(plane1 round6)暴露 —— 卡巨星 6min(75+ retry 屏完全不变,会转到 MAX_ITER 2000 ~2.5h);round6 gold=17 lv=4 付不起升级费 30,hp 100→58 在掉血。纯代码永远看不出。
- **备选**:① 凭 视觉大模型 猜巨星选中目标(推翻:视觉大模型 状态/交互推理不可信,memory `onboard-vision-required` 已记);② 跳过巨星(推翻:首领节点不可跳,必打)。
- **状态**:**待解**。巨星选中机制 = 知识缺口(问用户 / 看攻略视频);恶性循环 = 早期战力 + 经济策略问题(需策略迭代)。`RunMegastarNode` 待机制明后建(预算至少 fail-fast 不再 2.5h 烧)。· `handle_megastar` / 策略早期经济。

## D-29 (2026-08-04) RunNode 重构:对局内 op 按节点生命周期划分 · battle_loop / run_nodes
- **决策**:对局内主循环从「flat loop 逐帧重新发现」重构为「外层分类+委派 + RunNode 按节点生命周期 owner」。`RunNode` 基类(**committed-but-verifying + 节点作用域预算**):每轮验证"还在本节点?"(`_in_node`)→ 否=节点完成 `round_success`;是→`_do_action` 做一动作→`round_retry`(计 `node_max_retry_times` 预算;超→FAIL bail,不无限烧)。pilot = `RunSupplyNode`(从 `HandleSupply` 升级,动作不变只套验证+预算)。
- **为什么**:旧 `Handle*` 全是**盲单发**(做一次动作就无条件 `round_success`,从不验证节点真完成 / overlay 消失)→ 动作失败也回 success → 外层 flat loop `round_wait`(**不计 retry**)无限重派 → 卡死烧预算(巨星 6min / invest_strategy 18min / invest_env 卡死,**全这一个模式**)。flat loop 还把"我在哪种节点"和"节点哪一步"两条正交问题塞进一条优先级阶梯 → LCS 噪音 / precedence 脆弱。RunNode 分开:外层只分类(小集合稳定),RunNode 管节点内多阶段 + 验证完成 + 预算。
- **备选**:① 保留 flat loop 只加全局超时(推翻:治标,优先级阶梯/LCS 噪音/无节点作用域卡死判据的根因没解);② 大改成显式状态机(推翻:OneDragon 节点图 + committed-but-verifying 已够,无需另造)。
- **状态**:采用。基类 + `RunSupplyNode` pilot 代码完成(ruff 净 + 导入/结构验),**行为验证待补给屏**(被巨星 D-30 卡,推进不到补给);其余节点(encounter/partner/invest_strategy/invest_env/megastar/combat)待逐个迁移(先零件后整体)。方法论 + 完整设计:`.debug/temp/currency_war/runnode_decomposition.md`(**后续提炼进 od-dev skills** —— op 划分通用方法论)。· `battle_loop` 0e supply 分支 / `run_nodes/run_node.py` / `run_supply_node.py`。

## D-28 (2026-08-04) `_saving_for_level` 对齐 D-24 gate · cw_decisions
- **决策**:`_saving_for_level` = 想升(`level<10 AND (goal=level_up OR level<_expected_level)`)AND `gold<升级费` → 抑制散牌买/刷,攒钱升等级。
- **为什么**:D-24 gate 已按"落后期望也升"(修 chicken-egg:`_DEFAULT_LEVEL_GOAL[4]=roll` → lv4 不升 → 永远到不了 lv5),但 saving 仍按旧"goal=level_up"→ lv4 不攒 → gate 想升却付不起。saving 须与 gate **同口径**。
- **备选**:saving 按 goal=level_up(推翻:与 D-24 gate 不一致,lv4 永远不攒,gate 形同虚设)。
- **状态**:采用(代码 `d5e0aea7`)。· `cw_decisions._saving_for_level`/`_want_level`。**注:必要非充分** —— 实跑 round6 gold=17 仍升 0(太穷付不起 30,见 D-30 恶性循环)。

## D-27 (2026-08-04) RunLoop 事件 overlay 前置检测 + BuyShopCards 兜底 · battle_loop / shop
- **决策**:① RunLoop 把 投资策略/投资环境/补给 检测**移到备战前**(原 step 4 → 0e,与 选择伙伴/巨星/遭遇/未达上限 同列前置);② BuyShopCards guard 加事件 overlay 兜底(检测 投资策略/环境/补给/遭遇/伙伴/确认选择 → fail 交主循环)。
- **为什么**:实跑发现**投资策略屏被误派 BuyShopCards**(「购买经验」从 overlay 后透出 → 备战分支 step1 先命中 → BuyShopCards → overlay 遮商店 → "找不到商店"死循环)。根因:事件 overlay 叠备战、购买经验透出,但事件检测在备战后。事件必须前置(overlay 在就不进备战)。BuyShopCards 兜底防 loop 漏检/其他调用路径。
- **备选**:① 只移 precedence(推翻:BuyShopCards 单查购买经验不够,需 overlay 兜底防其他路径);② BuyShopCards 单查 overlay(推翻:loop 是主路由,precedence 是主修)。两者互补。
- **状态**:采用(纯代码,需游戏验证 —— 下次投资策略屏应路由 HandleInvestStrategy 非 BuyShopCards)。`· battle_loop / shop`。**通用**:overlay 态检测必须在 base 态前(overlay 会让 base 锚点透出)。

## D-26 (2026-08-04) app 中间态接手(state-aware resume)· currency_war_app
- **决策**:`CurrencyWarApp` 各入口 op(`_enter_lobby`/`_start_match`)先检测当前态,已在 CW(大厅「创业指南」或对局中态)就跳过、直接进 `_run_loop`。新 `_in_match` helper(OCR 锚点:购买经验/备战阶段/投资策略/投资环境/补给/遭遇/盛会之星/出战/挑战结束/请选择投资)。
- **为什么**:用户洞见 —— app 原线性流(EnterCurrencyWar→Start→Loop)只认大世界起点,从对局中态(投资策略/备战/战斗)重跑会卡 entry(EnterCurrencyWar 找不到 guide)。实测从投资策略跑 app 失败、只能直接跑 RunLoop 接管。bot crash/重启/手动接管后需从任意态 resume。各 op「已过就 skip」= 幂等 resume。
- **备选**:① app 开头一个 detection node 路由(推翻:每 op 自检更模块化,符既有 node_from 流);② 总从大世界重新进(推翻:丢对局进度 + entry 卡)。
- **状态**:采用(纯代码,需游戏验证 —— 下次从对局中态跑 app 应直接 resume 进 loop)。`· currency_war_app`。**通用洞见**:长流程 app(模拟宇宙/忘却之庭/历战等)都该支持中间态接手(crash/重启后可 resume,非总从头)。

## D-25 (2026-08-04) exit op 事件屏 escape(返回备战界面/Esc 关 overlay)· 入口 op
- **决策**:`exit_currency_war_match` 加事件 overlay escape 分支 —— 「返回备战界面」(投资策略/环境)→ 点回备战;其他事件(补给/遭遇/巨星/详情/可合成列表)→ Esc 关。放备战分支后、retry 前。
- **为什么**:实测从投资策略屏跑 exit → 卡 210s+(事件屏无「放弃并结算」/备战文本 → 全分支不命中 → retry 死循环)。修后:事件屏先 escape 回备战 → 走原 Esc→放弃→结算→大厅。
- **备选**:① exit op 开头无脑 Esc 到备战(推翻:可能误关结算页);② 每事件单独 handler(推翻:exit 只需 escape,不必理解事件)。按文本检测 escape 最小可靠。
- **状态**:采用(纯代码,需游戏验证)。`· 入口 op`

## D-24 (2026-08-04) level gate chicken-egg 修:落后期望等级也升(非仅 goal=level_up)· strategy/02 plan / 03 level_plan
- **决策**:`plan()` 升级 gate 条件从「goal=level_up + 够钱」扩为「够钱 + (goal=level_up **或** 落后期望等级 `_expected_level`)」。
- **为什么**:telemetry 6 局**全「升0次」**(gold 到 74 也不升)。根因:task#18(D-14)gate 只在 goal=level_up 时升,但 `_DEFAULT_LEVEL_GOAL[2,3,4]=roll`(非 level_up)→ gate 在这些等级不触发 → 永远到不了 5+(level_up 等级)→ **chicken-egg 卡低等级** → 弱 comp → 输。CW 起步 lv4 + goal[4]=roll → 永卡 4。「落后期望等级」兜底:不管 goal,等级跟不上节奏 + 够钱 → 升(经济统一论:落后该升)。
- **备选**:① 改 `_DEFAULT_LEVEL_GOAL[3,4]=level_up`(推翻:rigid,只解 lv4;「落后期望」更通用,适用任何掉队);② LevelUp 回归 eval 候选(推翻:task#18 D-14 已证 eval 短视永不选;gate 更稳)。
- **状态**:采用(7 level-up 测试绿,含新 D-24 测试)。**待干净对局验证**:下局应能看到升级(chicken-egg 解)。`· §02 plan / §03 level_plan`

## D-23 (2026-08-04) EnterCurrencyWar wait_lobby 防御性加固(前往参与仍在→重点击)· 入口 op
- **决策**:`wait_lobby` 加分支 —— `前往参与` 仍在(transport click 没落地)→ `round_by_ocr_and_click` 重点击。放「创业指南」(大厅)之后、弹窗/F 分支之前。
- **为什么**:全流程跑卡 `wait_lobby` 重试 37x 失败,根因:停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ F 分支(`货币战争 AND NOT 前往参与`)被跳过 → 无分支命中 → 死循环。上个节点(前往参与)的 transport click 没落地(bug#1)→ 角色没传送 → 停指南页。重点击兜底。
- **备选**:① 提 node_max_retry(推翻:不解决根因,仍死循环);② 改 F 分支条件(推翻:不该在指南页按 F)。防御性重点击 = happy path 不受影响(传送成功则前往参与消失,分支不触发)。
- **状态**:采用(防御性加固;**需游戏验证** —— 下个干净对局跑 EnterCurrencyWar 看是否还卡)。`· 入口 op`

## D-22 (2026-08-04) hp 阈值统一 config.hp_safe_threshold(D-18 unification 落地)· strategy/02 §A3
- **决策**:加 `config.hp_safe_threshold`(默认 40 = HP_DANGER);`_phase_weights(plane,hp,hp_threshold=HP_DANGER)`、`_refresh_cap(state,hp_threshold)`、`maybe_pivot`(`0.75×threshold`)签名加参数带默认。evaluate/plan 经 `getattr(config,'hp_safe_threshold',HP_DANGER)` 传入。
- **为什么**:02 §A3 要求 hp 阈值单一源(原散落 `HP_DANGER=40` + `maybe_pivot hp<30` 硬编码);A8 高难需调高阈值(difficulty 派生)。**默认 = HP_DANGER → 行为不变**(64 测试绿),但单一源 + difficulty 可调 + 偏移系数集中(转型 0.75×;死局 0.5× / 连败 1.5× 待相应函数实现时补)。
- **备选**:① 直接删 HP_DANGER 全走 config(推翻:默认值仍 40,保留常量作 default + 测试引用更稳);② 不做(推翻:design 02 §A3 指示 + 审计标的 divergence)。
- **状态**:采用(D-18 hp 项落地;64+1 测试绿)。`· §02 §A3`

## D-21 (2026-08-04) optionality_score + α(t) 纯函数(承诺-期权)· strategy/02/03 P1-1+F-3
- **决策**:实现 `optionality_score(state)`(bench 角色属 **≥2 COMP_LIBRARY comp**[``shared_chars ∪ core_chars``]→ 加分,保期权/容错)+ `alpha_t(state)`(总回合 <R_OPEN→0 纯期权 / >R_CLOSE→1 纯承诺,线性)。R_OPEN/R_CLOSE/OPTIONALITY_WEIGHT **值在代码**(阶段 6 实玩校准)。
- **为什么**:A8 方差生存战,过早 commit 单一 comp 遇克/缺牌即死(plane2 死因之一);保 ≥2 comp 可行 → 容错。design P1-1/F-3 标 high。
- **备选**:① 直接集成进 evaluate(推迟:改核心 eval 行为需 P0 游戏验证才稳,先做零件);② 不做(推翻:high 优先 + 直接关系 plane2 生存)。
- **状态**:采用(纯函数 + 2 测试绿;**evaluate 集成延后** —— ``α·target_progress + (1-α)·optionality`` 混合,待 P0 解阻后集成 + 游戏验证)。`· §02/03 P1-1/F-3`

## D-20 (2026-08-04) decide_supply 纯逻辑骨架实现 · strategy/07/08
- **决策**:实现 `decide_supply(options, state, target_comp, config, refresh_used) → SupplyPick`(纯函数,design 07/08 骨架)。规则:带钻(红/蓝)→ 选(基本赢,碾压);全无钻 + 刷新未用 → 刷新找钻;刷新已用 → ``key_equips`` 契合(+10 命脉级)+ 通用装备价值(鞋>电池>花,``_EQUIP_VALUE`` 代码表)。新 ``SupplyOption``(idx/角色/装备/带钻)+ ``SupplyPick``。
- **为什么**:补给节点 naive「选中牌」(``handle_supply``)无视钻/key_equips;design 07/08。钻 = 拿到基本赢(用户),碾压;key_equips comp 相关(D-07)。先纯逻辑(可独立测),handler 接线(``read_supply_options`` OCR + 钻视觉判定)待阶段 5。
- **备选**:① 通用 equip_score(推翻:脱 comp 无意义,D-07);② 等阶段 5 OCR 一起(推翻:纯逻辑可独立测,符合先零件后整体)。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 待 ``read_supply_options`` 阶段 5)。`· §07/08 补给`

## D-19 (2026-08-04) decide_encounter 纯逻辑骨架实现 · strategy/08
- **决策**:实现 `decide_encounter(options, state, target_comp, config, refresh_used) → EncounterPick`(纯函数,design 08 骨架)。规则:未成型→低难度;全分支词缀克 comp(``mechanics_fit``<0.4)+ 刷新未用→刷新换批;成型 + 词缀利 comp(debuff=buff)→高难度拿奖励;刷新已用→按最优选。新 ``EncounterOption``(idx/难度/词缀/奖励)+ ``EncounterPick``(idx/refresh/reason)数据类。
- **为什么**:遭遇节点 naive「选左」(``handle_encounter``)无法表达难度/词缀决策;design 08 标 high。词缀用 ``mechanics_fit``(debuff=buff,D-05)判克/利 comp。先做纯逻辑(阶段 2 骨架,可独立测),handler 接线(OCR ``read_encounter_options``)待阶段 5。
- **备选**:① 扩 ``decide_event`` 白名单(推翻:遭遇是难度档非白名单项,decide_event 表达不了);② 等阶段 5 OCR 一起做(推翻:纯逻辑可独立测 + 早发现 bug,符合"先零件后整体")。
- **状态**:采用(纯逻辑 + 4 测试绿;handler 接线待 ``read_encounter_options`` 阶段 5)。`· §08 遭遇`

## D-18 (2026-08-04) 配置层对齐:经济统一论落地后的取舍 · strategy/02 §A3 + README §A/D
- **决策**:① `economy_mode` **保留**(作 eval 权重微调:interest_first/rush_level 调利息/等级项),不按原 README §D 删除;② `aggression` **删除**(死字段,cw_decisions 不用);③ hp 阈值统一走 `config.hp_safe_threshold`(02 §A3)+ config 重写(forbid/build_around/handoff/difficulty/manage_meta_run)**缓做**(deferred)。
- **为什么**:① level_plan 是**硬 gate**(D-14,主导花费指令),economy_mode 只调 eval 权重(非花费决策)→ 二者**不冲突**(原 README "和 level_plan 打架"的删除理由在 hard-gate 落地后不成立);且 economy_mode 有测试锁定(test_economy_mode_effects),删 = 行为变更 + 破测试,无收益。② aggression 全代码不用,设计早判"虚"已删,代码残留。③ hp 统一 / config 重写是干净但触及 `_phase_weights` 签名 + 测试 + GUI 的重构,非"修漂移",单列任务。
- **备选**:按原 README §A/D 全删 economy_mode/aggression + 一次重写 config(推翻:① economy_mode 删除理由失效;② config 重写大,且 cw_comps 已 `getattr` 防御读取新字段,可增量加不必一次重写)。
- **状态**:采用(①② 已做;③ deferred,见 process_log/insights)。`· §02 §A3 / README §A/D`

## D-17 (2026-08-04) eval / comp_score 权重实跑校准 · strategy/02 §A3 + 03 comp_score
- **决策**:V4.4 research 先验权重经 2026-08-04 实跑(replay 32 局 + bot)校准:`INTEREST_WEIGHT 2→4`、`LEVEL_WEIGHT 3→6`、`SYNERGY_TIER_EXPONENT=1.5`(收敛:深化 delta>散新)、`OFF_TARGET_DISCOUNT 0.3→1.0`(revert,改用 commitment prefilter D-15)、`W_PROG 0.35→0.45` / `W_STR 0.10→0.05`(select_comp 偏好可成型而非纯高强度)、`TARGET_PROGRESS_WEIGHT=15`。
- **为什么**:实跑发现原值致 bot 不攒金(息 delta = 牌 synergy → 无差别买)、不升等级(level benefit < interest loss)、select_comp 锁高强度但不可成型 comp(列车同行 S 但商店没牌 → 不收敛)。提权后 bot 攒到 50 + 升级 + 选可成型 comp。
- **备选**:维持 research 先验占位值(推翻:实跑证明不收敛)。阶段 6 再用 replay 精调最敏感 3-5 维。
- **状态**:采用(实跑驱动,待阶段 6 replay 精调)。`· §02 §A3 / §03`

## D-16 (2026-08-04) shop_supply:select_comp 降权不可得 comp(task#25)· strategy/03
- **决策**:`select_comp` 对核心阵营在当前 shop/board **不可得**的 comp ×0.3 降权(新 helper `shop_supply`)。
- **为什么**:实跑发现 select_comp 锁高强度 comp(列车同行 S=1.0)但商店刷不出其牌 → board 散、永不成型 → plane1 重伤。降权使 select 偏好**可得** comp(万敌 燃血:1 > 列车同行 0 可得)。
- **备选**:① 纯按 comp_score 不考虑可得性(推翻:锁死不可成型 comp);② P1-2 `ENV_COMP_AFFINITY` 硬绑(更强形式,待实玩补全 T0 env 表)。
- **状态**:采用。`· §03 select_comp`

## D-15 (2026-08-04) commitment prefilter + OFF_TARGET_DISCOUNT revert(task#16)· strategy/02
- **决策**:target_comp 设定时,`_best_improving_action` 用 **prefilter** —— shop 有 target 卡(阵营∈target.factions / ∈core_chars)可买时,跳过纯 off-target 散牌(**只 gate 新 buys,不动已持有 board 的 eval**);`OFF_TARGET_DISCOUNT` revert 0.3→1.0(不打折 board synergy)。
- **为什么**:原 OFF_TARGET_DISCOUNT=0.3 打折 board synergy 致 bot 卖成型 off-target 深堆(churn)= regression。prefilter 只影响"买什么新牌"不影响"已堆的怎么评分"→ 聚焦深化 target 且不破坏现有 board。target_comp 参数保留(prefilter 复用,OFF_TARGET_DISCOUNT effect 暂关)。
- **备选**:① OFF_TARGET_DISCOUNT 打折 board(↺ 推翻,致 churn);② 无 commitment(纯 reactive,不聚焦)。
- **状态**:采用。`· §02 commitment`

## D-14 (2026-08-04) level_plan 从"导向"升级为"硬 gate"(task#18)· strategy/03 经济统一论
- **决策**:`plan()` 中 level_plan `action="level_up"` + 够钱 → **直接执行 LevelUp**(每轮 ≤1 级),不进贪心 eval 候选。语义从 D-08 的"导向(eval 权重)"升级为"**花费指令(directive)**"。comp 无 level_plan 时退回通用曲线 `_DEFAULT_LEVEL_GOAL`。
- **为什么**:replay 32 局「升 0 次」根因 —— 贪心 eval 对"花大金升级"的利息损失短视:LevelUp 候选 delta 永负(花 48 金 → 利息档 5→0 损 -20,level_val 仅 +6)→ 永不选中 → bot 卡 lv5-6 → 弱 comp → plane2 死。level_plan 说升 + afford → 信任计划而非短视 eval。tempo 破息在所不惜(升级 = 解锁高费刷新率 + 出战位,关键长期投资)。
- **备选**:① 仅提 LEVEL_WEIGHT 让 eval 自发选升级(部分采用 D-17 提 3→6,但单靠 eval 权重不够稳,hard gate 兜底);② 每 comp 手填 level_plan(保留:comp 有则优先,无则通用曲线兜底,保证所有 comp 有合理经济行为)。
- **状态**:采用。`· §03 经济统一论 / §02 plan`

## D-13 (2026-08-03) 击破 tiers V4.4 修正 2/4/6/9 · data/factions
- **决策**:`击破` FactionInfo tiers 用 `(2,4,6,9)`(原 `(2,4,6,8,10)`)。
- **为什么**:官方赛季文 76641553,V4.4 姬子成专家顾问,tiers 下调。
- **备选**:无(实据,非权衡)。
- **状态**:采用。

## D-12 (2026-08-03) 领域模型注册表 + 单一真相源派生 · 工程化
- **决策**:核心实体建正规 model 类 + 注册表(Character / Faction / Equipment / InvestmentEnv+Strategy);派生关系而非硬编码 —— `ENV_FACTION_MAP`←`INVESTMENT_ENVS.faction`、`DISTINCT_CARDS_PER_COST`←`chars_by_cost`、`Faction.members()`←`CHARACTERS` 反查。
- **为什么**:用户定调工程化质量,别写屎山;单一真相源改一处自动传导(否则多处硬编码易脱节)。
- **备选**:裸 dict + 散字符串(推翻:重复硬编码,改一处要同步多处)。
- **状态**:采用。

## D-11 (2026-08-03) 观测 trend 归一化而非完全划分 · strategy/10
- **决策**:`recent_hp_loss_trend` 用 `hp_delta / expected_drop[node_type]` 归一化,全部样本进**同一条** trend(不按 node_type 完全划分);boss 另留短 trend。
- **为什么**:review r5 的"完全划分"致 boss 观测永久 None + obs 随节点类型震荡;归一化既消除"打 boss 掉得多=我弱"偏差,又不丢样本。
- **备选**:按 node_type 完全划分(↺ 推翻 r5 过度修正;boss 稀疏 + 震荡)。
- **状态**:采用(r6 修 r5)。

## D-10 (2026-08-03) comp_viability 冷启动早返回纯先验 · strategy/10
- **决策**:obs=None(无观测)时直接返回纯先验,不 blend。
- **为什么**:`obs_weight × obs`(0×None)会 TypeError 崩溃;且无观测时纯先验就是最佳估计。
- **备选**:用先验填 None 再 blend(多余,先验已在公式里)。
- **状态**:采用(bug-driven,测试发现)。

## D-09 (2026-08-03) 列车同行(姬子·启行)= bot 默认首选 comp · data/comp_library
- **决策**:V4.4 列车同行 comp 作 bot 默认首选(strength S)。
- **为什么**:A850 挂机流攻略(76824096):"全程自动、不凹开局、适应任何负面环境" —— 完美适配 bot。V4.4 评级真神。
- **备选**:昼神阿雅(已降 B)/命运圣杯红A(S 但联动获取门槛)。
- **状态**:采用。

## D-08 (2026-08-03) 经济统一论:level_plan 驱动超额金 · strategy/03
- **决策**:D牌/买牌/买经验是"花钱的一环",非三件事。维持 ≥50 金(息引擎),**超额(>50 不生息,免费)该花**,花哪由 `target_comp.level_plan[当前等级]` 决定(level_up/roll/stable);tempo(连胜连败/HP危险/战力断档)例外破息。
- **为什么**:用户框架 —— 超额的钱白该花,花哪由成型路线导向。
- **备选**:D牌/买牌/买经验三件独立决策(推翻:割裂,忽略超额金的"免费"性)。
- **状态**:采用。**接法已落地**(`plan` level_plan 硬 gate[D-14] + `select_comp`/`maybe_pivot`[cw_comps] + shop.py 接线;2026-08-04)。

## D-07 (2026-08-03) 一切评分 comp 相关 · strategy/03/07/10
- **决策**:装备/巨星/词缀好坏都挂钩 `target_comp`(`equip_fit`/`mechanics_fit`/`select_megastar`),不设独立绝对评分项。
- **为什么**:反重力皮靴对昼神阿雅(需2靴)是命脉、对别 comp 不一定;知更鸟幸运一击只对暴击队值钱;正当防卫对阿雅是克、对万敌燃血是利。
- **备选**:通用 equip_score + 通用词缀表(推翻:脱离 comp 的绝对评分无意义)。
- **状态**:采用。

## D-06 (2026-08-03) V4.4 阿雅 strength S→B · data/comp_library
- **决策**:V4.4 昼神阿雅 comp strength B(V3.8 曾标 S "最轮椅")。
- **为什么**:米游社合集 76807134 V4.4 评级(试用+0命),阿雅降 B —— 需反重力皮靴×2+速度投资,试用/0命下难成型。
- **备选**:保留 S(与 V4.4 实测 meta 矛盾)。
- **状态**:采用。↺ 推翻 V3.8 "最轮椅 S" 先验。

## D-05 (2026-08-03) debuff 可能是 buff(mechanics_fit 双向)· strategy/10
- **决策**:敌人词缀对 comp 是 counter 还是 synergy,**双向判**(同一词缀对不同 comp 方向相反)。`comp.mechanic_attributes` + 全局 `MECHANIC_COUNTERS`/`MECHANIC_SYNERGIES`。
- **为什么**:正当防卫(反伤)对高频队是克、对燃血队(万敌)是利(反伤让燃血掉血→角斗场记录→伤害更高)。但**永久创伤**(掉血减上限)**克**燃血 —— 反例,故燃血非"所有掉血都利"。
- **备选**:通用高危词缀表(推翻:同词缀不同 comp 方向相反,通用表错)。
- **状态**:采用。

## D-04 (2026-08-03) 持久化/跨局状态默认不碰 · strategy/09
- **决策**:bot 默认**不动**玩家跨局继承(优势布局/钻钞);`manage_meta_run=false`。仅**局内**状态(买/deploy/升/D牌)默认自动。
- **为什么**:防打乱玩家长期投入(优势布局是玩家自己攒的 buff);持久化破坏性操作 opt-in。
- **备选**:默认自动激活最优布局(推翻:风险大,可能毁玩家投入)。
- **状态**:采用。

## D-03 (2026-08-03) 不凹开局重开 · strategy/09
- **决策**:策略**不依赖重开**找好开局;够好就该能"理智"克服任何开局。
- **为什么**:重开是玩家行为不是策略;策略鲁棒性应内含,不该靠重开掩盖。
- **备选**:opening reroll(推翻)。
- **状态**:采用。仅 `handoff=true + 好开局`用例保留"刷好开局交手玩家"。

## D-02 (2026-08-03) 邪道非必需(通关=成型度+装备)· strategy/02/03
- **决策**:不把"邪道装备/特殊 win-con"(物质分解液/反甲/仙舟神君邪道)当 comp 强度关键项;通关能力 = f(成型度 + 装备质量 + 阵型),差别在**成型难度**。
- **为什么**:用户实战 —— 好好构筑阵容+找装备,很多阵容都能通 A8;被攻略带偏("A8 80亿血必须靠邪道")。
- **备选**:标"邪道 A8 专项 S"(↺ 推翻;与实战矛盾)。删 `a8_wincon_holdings`。
- **状态**:采用。

## D-01 (2026-08-03) 砍精确战斗模拟器 + ML,改观测驱动 · strategy/01/10
- **决策**:**不建**战斗模拟器(打前预测赢率/掉血),**不建** ML 训练管线;改用 OCR **观测结果**(每回合掉血/胜负/boss血条)当反馈信号。
- **为什么**:星铁战斗太复杂(回合序/弱点/击破/能量/战技点)OCR 反推不出可信模型;且版本迭代改数值,预测模型会废、维护不起。结果信号扎根在结果上,版本鲁棒。用户定调"像人一样玩"(人看掉血,不算赢率)。
- **备选**:① 精确 sim(推翻:维护成本极高 + 版本废);② ML 训练(推翻:训练价值版本短命,V4.4 训的 V4.5 废);③ 粗可行性启发式(**保留**为 comp_viability 先验,非预测)。
- **状态**:采用。ML 只采集(debug telemetry 序列化决策迹),**不主依赖**。
