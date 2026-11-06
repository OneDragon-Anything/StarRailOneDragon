# 开件动作去识别化(机械执行回归)迭代设计(总纲)

## 0. 元信息

- 迭代目标:清除开件族三动作 op(开简易武装箱/开秘密典籍/开书册卡)执行前的画面识别读门,回归「动作 op = 机械执行器」的已登记裁定形态,顺带消灭 sim 局在该链路的必然判废。
- 状态:定稿(三轮对抗收敛,见 attack.md;直点形态方案 R2 起无高危,R3 语义本体零发现)
- 文档清单:无详设(单文档方案)
- 承接出处:局 g_20261101_125430 判废调研(报告 `.debug/temp/cw_openbox_fail_research.md`,临时区过程件不保证留存;机理结论已内联 §1);规范依据 = `flow/action_ops.md:15`(用户裁定 2026-09-21「动作 op 无论执行前还是执行后,都不做观察识别——这是规范,不是取舍」;裁定原文自带「唯一允许的查找 = 点击/拖拽目标定位所需的元素查找——瞄准,不是观察」)与 `:13`(用户裁定 2026-10-17 零防御条款)。

## 1. 问题与动机

- 现状症状:三 op 在点击前各有一段私有识别读门——`cw_open_box_action.py:84-94`(screenshot → `read_armory_boxes` 逐槽灰度模板匹配 → 判空 `round_fail('无简易武装箱')`)、`cw_open_tome_action.py:72-82`(`read_tomes` 同构)、`cw_open_bookcard_action.py:82-92`(`find_bookcards` 同构);开箱还带硬编码偏移 `BOX_OPEN_DY=41`(`cw_open_box_action.py:56/:96`,「图标中心+41px=开启按钮」的位置关系写成了代码魔法数)。sim 局实证:读门对 sim 哨兵帧做真识别恒空,连续 5 帧失败触发外循环连败网判废整局(g_20261101_125430,终结链 dseq 82-86);同局出战 op 执行成功——行为分裂实证。
- 根因归层:**约定层**——三 op 读门是存量实现,先于 2026-09-21「零新增读屏」裁定存在且一直未清;裁定登记在案(`action_ops.md:15`)但实现未回改,`action_ops.md:110-112` 动作表还把读门写成 as-built(文档背书了违规现状)。非代码 bug、非设计缺失,是「裁定已立、存量未清」。
- 解决到哪:三 op 删除执行前识别读门,回归**容器槽位直点**形态——op 对画面零识别,槽号(决策层从容器状态现算)→ per-slot 建档坐标 → 机械点击 → 自上报。
- 明确不解决:①观察层识别器(`cw_identity_obs` 的 `read_armory_boxes`/`find_bookcards`)——服务备战画面观察 extras(`battle_prep_recognizer.py:50/:123/:248`),识别器本职,不在「动作 op 禁识别」禁令内;其私有管线与「容器/观察对账」的口径关系挂账(§2.6);②出战 op 执行后单帧弹窗识别挂账(`action_ops.md:18` 在册,同类不在本批文件面);③金/彩箱模板扩档(`cw_identity_obs.py:1192-1195` 在册独立任务)。

## 2. 方案(单文档完整设计)

### 2.1 系统级变化:容器槽位直点形态

三 op 节点体重写为纯机械链:**参数校验 → 槽号解析 → 建档坐标直查 → mouse_move+click → 自上报 → round_success**。op 对画面零识别(无 screenshot、无模板匹配、无判空分支)——与 2026-09-21「零新增读屏」、2026-10-17「零防御」两条裁定自洽:容器状态是决策单一源(「件在不在」由观察层 extras 与容器对账回答,`action_ops.md:70` 治理链),动作 op 只负责「把决策指的槽点掉」。

逐段规格(三 op 同构,差异注记):

1. **参数校验(保留现状)**:`action.slot` 越界 `AssertionError`(`action_ops.md:60` 校验落点契约:参数违法由 op 自判、响亮暴露零点击);`slot=None` 缺省语义 = **从 game state 容器现算首件槽号**(消费决策数据,与决策层同源,非画面识别)。**现算双出口语义(守卫断言,与越界同款响亮暴露)**:`gs` 为 None,或容器(该 kind)无首件槽可算 → `AssertionError`(生产决策层恒发显式 slot,`entry.py:633-636`,None 分支 = 缺省/测试面)。**落地机制 = 以现算 resolved slot 重建 param**(journal/回执显影显式槽号;不改写入参对象),**双实现归属声明**:上报层(`open_tome.py:44-49` 等)已有同型「首 kind 槽」现算——两套现算语义必须一致(同容器同规则),后续如提取公共函数另批;本批 op 内现算后以显式 slot 走后续链。
2. **槽号 → 建档坐标直查(替代识别读门)**:
   - 武装箱:`武装箱开启位-{N}` area(per-slot,新建 9 个,§2.3)——「点哪能开」语义实测定准进建档,`BOX_OPEN_DY` 魔法数删除;
   - 典籍/书册卡:点击点 = 槽位本体中心,复用已建档 `备战栏-{N}` area(零新建);
   - 坐标读取走 screen_info 读口(area 单一事实源),禁止任何 fallback 推算。
3. **机械点击(保留现状形态,出战同款)**:`mechanical_io_allowed()` 分支内 `mouse_move` + `click`(mouse_move 防吞点击语义保留,`action_ops.md` §4.2 采晶矿同口径在册);sim 下分支旁路、静默成功 + 自上报(出战 op 同款,`cw_start_battle_action.py:124-126`;sim 点击受理正本依据 = `action_ops.md` §4.7「sim 机械 IO 关闭下点击经端口 click_answer 受理」,既有先例 = 开店/确认钮 `cw_op_open_shop.py:61`/`cw_pick_invest_action.py:86`)。
4. **自上报(保留现状)**:`report_action_open_*` 链原样;sim 后端 `_on_open_box` 世界建模(`cw_sim_backend.py:2407`,trigger 分派 :2036-2037)由此真正收到上报。
5. **round 语义**:参数合法即机械执行成功 → `round_success`(failure 分支只剩参数 AssertionError);「点了≠成了」的治理 = 按成功上报 → 外循环重观察对账兜底(`action_ops.md:70` 治理链;零防御哲学:op 不做成功性识别)。终结/非终结语义与 `terminal_wait`/`_OVERLAY_ANIM_WAIT_S` 等待常量不变(`action_ops.md:75`)。

### 2.2 依据链

- 「动作 op 不做观察识别」= `action_ops.md:15`(2026-09-21 用户裁定;裁定原文自带「瞄准豁免 = 点击/拖拽目标定位所需的元素查找」——本方案连瞄准都不做,直接槽号→建档坐标,严于豁免线);「零防御」= `:13`(2026-10-17:取值直接使用、自然异常,不做防御性识别);容器↔画面不一致的治理归观察侧对账 = `:70` 治理链。
- 全族参照:出战 op 的 `mechanical_io_allowed` 点击旁路(`cw_start_battle_action.py:124-126`)与「按成功上报」语义;开店/确认钮的 sim click_answer 先例(`cw_op_open_shop.py:61`)。
- 坐标单一真相源 = 项目 AGENTS.md §5;校验落点契约 = `action_ops.md:60`。

### 2.3 建档(od-dev-screen-onboarding)

新建 per-slot area `武装箱开启位-1..9`(画面 = 货币战争-备战,9 个):
- rect = 现档 `备战栏-{N}` area 中心 + 垂直偏移 41px 的「开启按钮」位置(现码 `BOX_OPEN_DY` 语义的建档化;初值从现档推导,**实机实测校准回补**,「点哪能开」以实测为准);
- 纯 rect area,无模板(直点形态不认样子,「件在不在」归容器/观察);
- 经 MCP `upsert_screen_area` 写入(同步合并缓存)。
典籍/书册卡零新建(复用 `备战栏-{N}`)。

### 2.4 失败语义与行为变化申报(全量)

1. **sim 整局判废链消灭**(端到端目标):读门对哨兵帧恒空的失败路径不复存在;sim 下机械分支旁路 + 静默成功 + 自上报,后端世界状态推进。
2. **实机误派场景治理归宿变化(按 op 分形,如实申报)**:改后三 op 失败分支只剩参数 AssertionError,外循环连败网对本族**结构性零触发**(其旧燃料恰是被删的识别 fail)——误派(容器陈旧点空/点不响)的真实归宿:
   - **OpenTome/OpenBookcard**(腾位写 + 点空):下一 heavy 帧 bench 实读 vs 容器失配 → 失配告警**停机**(观察三分流 + `currency_war_app.py` stop_running 钩子,生产在装)——维护者介入追根因;
   - **OpenBox**(零写上报,`action_ops.md` §4.8#5):无失配面,异常滞留靠 NODE-DWELL 900s 系统哨兵留证停机(`cw_loop.py:442/:487`)。
   即实机误派语义从「连败网 5 帧响亮判废」变「慢速留证停机」——守卫换位,申报于案,防事后找错守卫。
3. **`read_tomes` 随批删除**:全仓唯一消费 = `cw_open_tome_action.py:68/:73`(执行器),框架化/直点化后成零消费死码;`read_armory_boxes`/`find_bookcards` 保留(观察层另有消费:`battle_prep_recognizer.py:50/:248` 与 `read_bench_view` 链),其私有管线与观察对账的口径关系挂账声明(§1「不解决」①)。
4. **`BOX_OPEN_DY` 删除**(语义迁入 §2.3 建档);`mechanical_io_allowed` 分支**保留**——出战合规参照即此形态,点击面沿用既有 sim 旁路机制(正本依据 = `action_ops.md` §4.7),不迁移到框架 click_answer。
5. 终结/非终结语义、`terminal_wait`/动画等待常量、slot 越界 AssertionError、`slot=None` 决策层契约(语义微调:现实现 `boxes[0]`=识别首件,新形态 = gs 容器现算首件,决策数据同源;`cw_vocab.py` 三个 param 类 slot 字段的 [索引定义] 注释取值时机同步更新)不变或如上注记。
6. **回执词表收缩**:三 op 判空 fail 码(`无简易武装箱/无秘密典籍/无书册卡`)零供给退役——`prep_actions.py` 回执映射表三行删除,正本词表(`action_ops.md:225`/`game_state/fields.md:2763`)随正本更新收缩。

### 2.5 消费面清单

**代码**(本批文件面):
- `src/sr_od/application/currency_war/operations/cw_op/cw_open_box_action.py`、`cw_open_tome_action.py`、`cw_open_bookcard_action.py`:读门删除、直点形态重写(§2.1);`read_tomes` 符号删除(§2.4-3,`cw_identity_obs.py` 内)。
- `src/sr_od/application/currency_war/prep_actions.py`:回执映射表三行退役(§2.4-6)。
- `src/sr_od/application/currency_war/kernel/cw_vocab.py`:三个 param 类 slot 字段 [索引定义] 注释取值时机同步(§2.4-5)。
- `assets/game_data/screen_info/`(经 MCP upsert):`武装箱开启位-1..9`(§2.3)。

**测试**(grep 三 op 现有测试定位:含 `test_prep_action_ops`/`test_open_tome_single_click` 等;改测试 = 重推语义引本篇节号):
- 单帧测试:slot 显式/None 现算两态 → 建档坐标点击 + 自上报 + success;slot 越界 AssertionError;**None 现算双出口(gs 为 None / 容器无该 kind 首槽)各一条 AssertionError 断言**;sim 形态(旁路静默成功 + 后端世界推进断言);既有无 gs 装配的用例(如 `test_open_bookcard_executor_mechanical`)重写时补 gs 装配(新守卫需要);
- 「无箱」态在 op 内不可测(零识别,无该分支)——容器陈旧治理的测试归观察对账域(不在本批,声明)。

**正本文档**:落点 = landing 正本更新清单(六行:action_ops.md 动作表/词表、projection_contract.md G5、game_state fields 与 logic-updates 三篇)。

### 2.6 验证法

1. 单帧测试(§2.5,回归资产)。
2. **同 seed 复跑**:`cw_sim_match_drive.py --seed 20261101` 整局复跑,断言 P1-R8 判废链消灭(abnormal 链消灭,武装箱开箱链走通)——端到端验收。
3. 实机 `run_operation` 三 op 单跑(od-dev-write-operation §主线 5):`武装箱开启位-N` 坐标实测校准(偏差回补 3.1 建档)。
4. CW L1 全量一次通过(三 op 旧测试含读门断言的随 §2.5 随改;红面须与清单吻合)。

### 2.7 关键取舍

- **容器槽位直点(本篇)vs 框架 area 定位查找**:框架 `find_area` 取全搜索域首命中、无搜索域参数(operation.py:937-1034),slot>1 同 kind 多件时恒命中首件 → 死循环判废(与要消灭的病同构);典籍互斥判定与双渲染模板亦无法迁入单模板 area。直点形态下「件在不在」归容器/观察(op 零识别),两问题消解,且与「零新增读屏」「零防御」两裁定最自洽——op 连「瞄准」都不需要(容器已给槽号,槽号→坐标是建档查询不是画面查找)。
- **观察器双轨挂账 vs 同批统一口径**:统一口径更纯但动观察层 extras 数值兼容面,风险大于收益;挂账(§1「不解决」①)。
- **「sim 跳过读门」(调研原选项 A)作废**:在违规实现上分叉打补丁,实机违规形态原样保留——治本 = 删违规形态本身。
- **`mechanical_io_allowed` 分支保留 vs 框架 click_answer 接管**:出战 op(合规参照)即保留旁路形态;分支是既有 sim 机械旁路机制(正本依据 = `action_ops.md` §4.7),保留 = 最小行为面变化。
