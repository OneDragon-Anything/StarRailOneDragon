# CW 动作 op 小修批(fix-1)迭代设计(总纲)

## 0. 元信息

- 迭代目标:修复实机验收期定谳的三件货币战争(CW)动作 op 小缺陷——①开拓商店收店 op 参数面缺口;②采集族画面守卫缺失(错屏空转假成功);③拖角色 op 槽位基声明缺失(AGENTS §9 违例)。
- 状态:定稿(设计对抗攻击收敛;三件方案骨架经实码对抗维持原案)
- 文档清单:无详设(单文档方案,本篇即完整设计,深度 = 实现者无需再设计)
- 实施纪律:一次实施一个小 commit 面(三件三 commit,互不依赖);run_operation 异步回执不带失败标记属框架级事项,已提请跨项目 skill 反馈通道处理,不入本批。

## 1. 问题与动机

### 1.1 件 1:CwToggleShopPanel 不认「货币战争-备战-开拓商店」画面值

**现状**(符号定位,行号从略——并行批会漂移):

- op:`src/sr_od/application/currency_war/operations/actions/cw_toggle_shop_panel.py` 的 `CwToggleShopPanel`(actions 包公用底层动作原语,MCP `run_operation` 可直调,支持类名短名)。
- 构造期校验:`screen_name` 只接受 `('货币战争-备战', SHOP_SCREEN_NAME)` 两值(`SHOP_SCREEN_NAME = '货币战争-备战-开商店'`,常量在 `kernel/cw_obs_core.py`);传其它值抛带可用值列表的 `ValueError`。「货币战争-备战-开拓商店」不在枚举内 → 收开拓商店时构造即拒。
- 动作机制:单节点,`area_center(ctx, '按钮-商店开关', screen_name=...)` 静态读矩形中心 → `controller.click`;area 缺失显式 `round_fail`。零识别(不模板匹配)、零判效(翻转结果归调用方下一帧 `analyze_screen` 对账)。
- 画面档:
  - 「货币战争-备战」(`currency_war_battle_prep.yml`):有「按钮-商店开关」(静态矩形 (1555,860)-(1690,1030))与「标识-银轨商店徽记」(带状搜索域 (230,220)-(310,580),模板 `cw_rail_shop_badge`,阈值 0.7,goto_list → 货币战争-备战-开拓商店)。
  - 「货币战争-备战-开商店」(`currency_war_battle_prep_shop_open.yml`):「按钮-商店开关」同矩形;另有 id_mark「按钮-收起」。
  - 「货币战争-备战-开拓商店」(`currency_war_battle_prep_pioneer_shop.yml`):仅 标识-开拓商店(id_mark)、备战标识-购买经验(id_mark)、读区-星穹列车币、区域-商品卡区、按钮-详情-1..4、读区-帕姆王进度。无任何开关/徽记/关闭 area,且全部 area `goto_list` 为空(零出边)。
- 玩法语义(`skills/sr-od-currency-war/references/screens/货币战争-备战-开拓商店.md` 实机实测建档):
  - 开拓商店是备战画面的浮层;入口/出口 = 左缘金菱形徽记,toggle 双向语义(关态点 = 开,开态点 = 收回备战)。
  - 无 × 钮,唯徽记可收;徽记 y 随羁绊面板布局浮动(实测中心 y=262/346/515,x 恒 ≈267)——浮动元素,静态矩形中心直点会点空,必须带内模板定位后点命中位置。
  - 徽记模板跨三态(备战态/面板开启态/消费回备战态)存档帧自帧 TM 命中 1.0(`obs/recognizers/battle_prep_recognizer.py` 分离度标定注释)——同一模板在开拓商店画面上可用,有实证。
- 文档口径缺口出处:上开画面卡第 5 步「关闭商店回备战:点左侧开拓银轨徽记;或收店操作同备战卡第 2 步(`CwToggleShopPanel`,静默失败重跑)」——文档承诺了 op 收店能力,op 参数面不认该画面值,承诺落空。

**根因**(约定层 + 参数面):参数面迁移把 `CwToggleShopPanel` 的枚举只盘了备战/开商店两档,漏了同族第三档开拓商店;深层原因是开拓商店收店控件与现有面板开关不同构(浮动模板徽记 vs 固定矩形按钮),不是加一个画面值就能机械平移,实施成本被低估后整项跳过,skill 画面卡文档口径未随之收敛,形成「文档承诺 − op 能力」缺口。

### 1.2 件 2:CollectOre 族无画面守卫,错屏空转返回「场上无晶矿」

**现状与全族盘点**(采集相关 op 全查):

| op | 层/包 | 参数面 | 读屏? | 现守卫? | 错屏失败形态 | 消费方 |
|---|---|---|---|---|---|---|
| `CwCollectRewardOres`(`operations/actions/cw_collect_reward_ores.py`) | actions 公用底层原语 | JSON 简单类型(`max_clicks`),MCP 可直调 | 有(晶矿识别 = 动作本体豁免) | 无(docstring 明写「无商店展开守卫(已按动作 op 契约拆除)……由调用方保证」) | 识别恒空 → `round_success('场上无晶矿')`,**成功假象** | 仅 MCP agent(src 零调用方) |
| `CwActionCollectOreOp`(`operations/cw_op/cw_collect_ore_action.py`) | cw_op 备战域动作 op(注册表 `cw_action_registry.py` 按 `CwActionCollectOreParam` 派发) | `param`(词表 dataclass)+ `env: PrepExecEnv`(运行时对象包) | 零读屏(契约见 `skills/sr-od-dev-currency-war/references/flow/action-op.md`) | 无;起点前置「货币战争-备战画面(动作执行时)」仅 docstring 声明 | 点的是决策侧给的显式坐标列,错屏 = 点到错位置(成功 detail「已点击 N 个」是真命题,不报假成功) | 仅 flow 内循环(`cw_screen_prep` → 注册表派发;`env` 非 JSON 型,MCP 反射面不可传参,实际不可直调) |
| (旁证)flow 侧晶矿观察消费 | `cw_screen_prep` 入口观察 / `obs/recognizers/battle_prep_recognizer.py` | — | 有 | 已有(画面 op 入口锚 + 观察边界) | — | flow 循环 |

假成功机制:`CwCollectRewardOres` 识别用的「区域-奖励」rect 从备战画面档静态解析(`obs/cw_identity_obs.py` `read_ore_sights` → `_area_rect(ctx, '区域-奖励')` 默认备战档),拿该 rect 裁任意屏的帧做模板匹配:错屏时大概率裁到无关内容 → 空表 → 报「场上无晶矿」成功。实机验收期两次定谳事故同此机制(错屏实况 = 主角选择画面,已注册、有识别器与 id_mark)。

**根因**(契约层为根,op 层为症状):`operations/actions/__init__.py` 包契约把晶矿例外写成「识别结果只决定点哪几个点,不做画面状态判断、不设前置守卫、不判动作生效」——入口画面锚(AGENTS §3 对所有 op 入口的硬性要求)被误并入「零判效」一并拆除。画面锚不是判效(不验证动作生效、不验证画面转移),是 CW 分层铁律明列的合法判断面「画面识别与路由、防 bug 守卫断言」;这是契约文本的口径错误,不止单个 op 漏写。

### 1.3 件 3:DragCwChar docstring 缺坐标系与基声明(AGENTS §9 违例)

**现状**:`src/sr_od/application/currency_war/operations/actions/drag_cw_char.py` 的 `DragCwChar`(actions 包,MCP 可直调,开发/测试用)+ 静态统一拖拽原语 `drag_char`(生产 deploy/sell 共用)。

- 类 docstring:有效果一句话、起终点、run_operation 调用例、生产侧指针;无 `:param` 段——参数语义全在 `__init__` docstring 的 Args 块。MCP `describe_operation` 透传的是**类 docstring**,参数写 `__init__` 属存量过渡态(od-dev-write-operation §5.0);远程部署 agent 看 describe,看不到 `__init__` docstring。
- §9 三要素缺失实证:`from_idx`/`to_idx` 在类 docstring 与调用例中零「1 基」「下标 + 1」字样;基信息只散在 `__init__` 校验处行内注释与 Args 块——describe 透出面完全不含基声明。extras 侧(`bench.slots` 0 基)与 op 侧(1 基物理槽位)的换算关系无处声明;同域拖动动作族 `CwActionMoveUnitOp`(cw_op 域,bench 参数 0 基容器下标、front/back 排内 1 基画面槽号,实码核验)的基差异也无类头声明——§9「同名动作类须在类头声明双方坐标系差异」双双违例。
- 事故链:部署 agent 经 `describe_operation` 拿到的参数说明无基声明 → 按 extras 0 基下标直传 → 拖错槽。对照模板 `CwSellBenchBySlot`(`operations/actions/cw_sell_bench_by_slot.py`)的 `:param slot:` 已带完整三要素(「备战栏物理槽位号,1-9(= screen_info『备战栏-N』序号;extras.bench.slots 数组下标 + 1)」),且无 `__init__` docstring——本件照此同款补齐。

**根因**(文档面):该 op 成文早于参数面迁移的 docstring 契约收紧,类 docstring 停留在过渡态;§9 收紧后未回补,describe 透出面缺基声明。文档面缺陷,不是逻辑缺陷。

### 1.4 明确不解决(范围边界,防外溢)

- actions 原语族**固定坐标类**的入口锚全族推广:错屏 = 盲点矩形中心(可能落在扣费控件上),危害形态属实,但整族装锚涉热路径成本取舍与族面设计,另行立项评估,不入本批。
- cw_op 动作 op 族 MCP 豁免声明缺失:`env: PrepExecEnv/ShopExecEnv/...` 为运行时对象参数,按 od-dev-write-operation §5.0 应在构造 docstring 声明「非 MCP 传参单元,仅限代码内调用」,现全族无声明(反射面静默劣化);小改,归后续 CW 文档面批。
- 开拓商店画面 extras 结构化读数缺位:该画面无 extras 识别器注册;本批 op 运行面零 extras 消费,不受影响,归画面观察面增量。
- run_operation 异步回执失败标记:框架级事项,已提请跨项目 skill 反馈通道处理。

## 2. 方案

### 2.1 件 1:扩参数面支持开拓商店

**案定:扩参数面**(取舍见本节末「关键取舍」)。改动四点:

1. **画面档补 area(经 MCP 工具,禁手改 yml——运行时加载合并缓存)**:`upsert_screen_area` 给 `currency_war_battle_prep_pioneer_shop.yml` 加 area:
   - `area_name: 标识-银轨商店徽记`(与备战档同名)
   - `pc_rect: [230, 220, 310, 580]`(与备战档同带;实机核对若发现开拓态带不同,以实机为准回填。注:带下缘 580 与实测浮动上限(y=515 + 模板高 ≈564)余量约 16px,实机核对时留意带下缘)
   - `template_sub_dir: currency_war`,`template_id: cw_rail_shop_badge`,`template_match_threshold: 0.7`(与备战档逐字段同构)
   - `goto_list: [货币战争-备战]`——补开拓商店 → 备战导航边(该画面档当前零出边;附带收益:`round_by_goto_screen` 路由可达 + 点击乐观推断有源,方向与徽记 toggle 双向语义同构)。
   - 该 area 非 id_mark,不进画面精准判定面;备战识别器读徽记 rect 走 `_area_rect` 默认备战档,开拓档加同名 area 不影响识别器取值(无意外副作用)。
2. **画面名常量**:`kernel/cw_obs_core.py` 增 `PIONEER_SHOP_SCREEN_NAME: str = '货币战争-备战-开拓商店'`(与 `SCREEN_NAME`/`SHOP_SCREEN_NAME` 并排;当前 src 零引用,此件引入首个代码引用,落常量免字符串散落)。
3. **op 扩参数面与分画面机制**(`cw_toggle_shop_panel.py`):
   - 构造期校验枚举扩为三值,`ValueError` 可用值列表同步。
   - 节点内按画面分支取控件:
     - **备战/开商店(固定矩形)**:维持现状 `area_center` 静态中心直点,机制零变化。
     - **开拓商店(浮动徽记)**:节点内直调底层助手 `screen_utils.find_and_click_area`(绕过 round 包装)——带内模板匹配达标才点击、点命中位置中心(非带中心,带中心在徽记 y 浮动时会点空);命中 → `round_success`(点击已由助手发出,零判效口径一致);**miss → 节点内立即显式 `round_fail(status='开拓商店徽记未识别(带内模板未命中;先核对开拓银轨≥2 开张)')`,零引擎重试**。定案依据:①徽记在已确认面板开启态下恒在场是识别器三态实证,瞬时 miss 概率低,放弃引擎级重试(瞬时遮挡自愈窗口归零)的代价可接受;②自定义失败 status 只有「miss 即 fail」写法能透出(框架 round 系 miss 返回 `round_retry`,由引擎按重试预算重跑节点、耗尽自动转 FAIL,status 为通用文案,节点函数拿不到「重试耗尽」事件);③显式 fail 让 MCP 调用方拿到可操作提示,重跑由调用方决定——与 op 既有「定位缺失显式 fail」分支(备战/开商店分支 area 缺失路径)同构。
   - 类 docstring 同步:`:param screen_name:` 三值 + 各画面收店控件语义(备战/开商店 = 固定面板开关静态中心;开拓商店 = 浮动徽记带内模板定位,点命中位,miss 显式失败);副作用行不变(零消耗承诺保留)。
4. **文档口径同步**(`skills/sr-od-currency-war/references/screens/货币战争-备战-开拓商店.md` 第 5 步):改为「收店:`CwToggleShopPanel {"screen_name":"货币战争-备战-开拓商店"}`(徽记带内模板定位;失败显式报错带原因);或点左侧徽记(toggle 开态点 = 关)」。备战/开商店两卡不动(两屏机制零变化,现有用法描述仍准确)。

**互洽声明**:本件开拓分支(miss 显式失败)不属于 2.2 节契约②「入口画面锚」的强制对象——该分支的模板定位 miss 直接显式失败,不产生「成功零效果」形态;op 亦不装入口画面锚(固定坐标 + 模板定位类,族内推广另行立项评估),两件口径互洽。

**涉及文件**:

| 文件 | 改动 |
|---|---|
| `assets/game_data/screen_info/currency_war_battle_prep_pioneer_shop.yml` | +1 area(经 MCP `upsert_screen_area`,不手改) |
| `src/sr_od/application/currency_war/kernel/cw_obs_core.py` | +1 常量 `PIONEER_SHOP_SCREEN_NAME` |
| `src/sr_od/application/currency_war/operations/actions/cw_toggle_shop_panel.py` | 枚举三值 + 分画面取控件分支 + docstring(≈ +25~35 行) |
| `skills/sr-od-currency-war/references/screens/货币战争-备战-开拓商店.md` | 第 5 步口径 1 行 |
| `sr-od-test/test/sr_od/application/currency_war/operations/actions/test_cw_toggle_shop_panel.py` | 新建(见测试点) |

**测试点**(镜像路径新建;harness = `sr-od-test/test/harness/fixture_controller.py`,流程测试不连真游戏,`fast_sleep` 包 `op.execute()`;测试断言前显式钉住/复位共享 `test_context` 的 screen_loader 画面状态——共享对象跨测试残留会造成单跑能过全量必挂):

1. 参数面:`screen_name='货币战争-备战-开拓商店'` 构造成功;非法值仍构造期 `ValueError` 且可用值列表含开拓商店。
2. 备战/开商店回归:静态中心点击坐标不变(断言点击记录 = 「按钮-商店开关」矩形中心)——存量行为零漂移。
3. 开拓商店命中分支:喂开拓商店展开帧(fixture `货币战争-备战-开拓商店/商店展开.webp`)→ 点击恰好一次,坐标 = 徽记命中位。**期望坐标口径 = fixture 真值标注**:该存档帧徽记中心的实测坐标,以探针读出、人工确认真值后以注释形式标注在测试内;禁用与被测同源的模板匹配实现现算期望(识别器 `find_rail_shop_badge` 与框架模板匹配是两条实现,用任一条现算 = 复刻被测逻辑,测试禁项)。
4. 开拓商店 miss 分支:喂徽记不在场帧(fixture `rail_badge_absent_r2.webp`)→ `round_fail`,status 含「徽记未识别」;点击记录为零;节点无引擎级重试(单次执行即 fail,断言运行记录节点执行一次)。
5. MCP 反射面:`describe_operation` 输出核对(三值口径 + 各画面控件语义 + miss 出口描述透出)。

**风险**:

- 徽记带位在开拓态可能与备战档不同(y 浮动同因:羁绊面板布局)——实机核对一次,不符以实机回填该档 pc_rect(设计已留「以实机为准」口径,含带下缘余量检查点)。
- 模板 `cw_rail_shop_badge` 在开拓态的视觉变体(如高亮态)未单独取证——识别器三态 1.0 已覆盖「面板开启态」,风险低;实施期实机单跑验证兜底。
- 开拓分支直调底层助手绕过 sim 端口覆写:sim 未建模开拓商店,哨兵帧恒 miss → 显式 fail(干净失败形态);本 op 属实机 MCP 原语,sim 路径不在消费面,不为此扩 sim 端口(注释声明即可)。

**关键取舍**:

- **扩参数面 vs 文档口径修正**:选扩参数面。判据:①语义同构——op 名/语义 =「切换商店面板开/收」,徽记 toggle 双向开关面板同构,只是控件形态不同;②文档已承诺该能力,撤承诺 = 对外能力倒退;③文档口径修正案留下能力空洞(agent 无任何 op 可收开拓商店,项目未暴露通用点坐标 op),补齐仍需新增专用 op,改动面反大。文档口径修正案仅在实施期实机核发现「徽记模板在开拓态不可命中」时降级启用(届时按 od-dev-screen-onboarding 重新取证再裁)。
- **miss 即显式 fail vs 引擎重试透传**:选前者(依据见修法第 3 点定案依据①②③);放弃的是引擎级重试的自愈窗口,换取可操作的失败信息与调用方自主重跑决策权。
- **框架助手 vs 手拼 CV 定位**:选框架底层助手 `screen_utils.find_and_click_area`(命中位点击语义已核实与设计一致);手拼模板匹配取峰(复用识别器 `find_rail_shop_badge` 同款带内匹配)作为该助手返回结构不符预期时的等价实现,不引入识别器第二消费面。

### 2.2 件 2:采集族逐 op 守卫 + actions 包读屏契约修订

**逐 op 定案**:

**A. `CwCollectRewardOres`——装入口画面锚(账本同族口径全量适用)**

入口节点 `collect` 头部、晶矿识别之前(复用同帧 `last_screenshot`,不二次截图):

```python
current = self.check_and_update_current_screen(
    screen, screen_name_list=[SCREEN_NAME])   # SCREEN_NAME 取 cw_obs_core('货币战争-备战')
if current != SCREEN_NAME:
    # 防错屏守卫(非判效):错屏显式失败带画面名,禁「识别空=无晶矿」假成功
    actual = self.check_and_update_current_screen(screen)   # 二次识别取真名,仅供报错
    return self.round_fail(
        status=f'非备战画面:{actual or "未识别"}(晶矿识别只对备战画面有效;'
               f'商店开着先收店,其它画面先导航回备战)', wait=0.5)
```

要点:

- 守卫集 = 只认「货币战争-备战」。开商店态不放宽:晶矿在面板展开时不可见,docstring 既有机「只应在备战画面(收店后)调用」口径不变。
- 失败路径二次识别只为把真实画面名带进 status(错屏报真名才可操作——定谳事故的错屏实况 = 主角选择画面,已注册有识别器,报真名可直达处置);成功路径只付单画面判定的便宜钱,fail 一次性,成本可接受。
- 二次识别的取名路径按框架实码语义:`get_match_screen_name` 无画面名单时**不是全量扫描**,而是从 current/last 已知画面出发 BFS 扩展邻居;真正的全量扫描只在无任何已知画面时走 `active_screen_info_list`。第一次窄判定会经 `update_current_screen_name` 向共享 ctx 写入结果,影响二次调用 BFS 起点——实施时实码验证该时序下二次调用的真实行为,取不全则直扫 `active_screen_info_list` 兜底(要求不变:报错信息能对上实际画面)。
- `check_and_update_current_screen` 签名标注返回 `str` 但底层可返 `None`(集合内全未中),None 分支必须接住(报「未识别」),禁裸比较。
- docstring 改写:删「本 op 无商店展开守卫(已按动作 op 契约拆除)……」整段,换「入口画面锚(防错屏守卫,AGENTS §3):非备战画面显式失败带画面名;识别空且已确认在备战画面才报『场上无晶矿』」。起终点/零判效口径其余不动,并补一句:守卫判的是「我在哪屏」,不判「点完生效没」——判效仍归调用方下一帧对账。

**守卫判别力依据**(浮层改版后此依据即排查起点,同步写进测试 docstring):框架画面判定对 id_mark 组合要求全中才算命中(`screen_utils.is_target_screen` 实码);备战档 id_mark 四件 = 备战标识-购买经验、按钮-出战、标识-前台区域(850,275,1070,340)、标识-后台区域(905,525,1060,630)。开拓商店帧下「前台区域」矩形完全落于商品卡区 (430,145,1415,418) 内(几何已核),板面文本被浮层内容覆盖 → id_mark 不全中 → 备战不命中;开商店帧同理被商店浮层覆盖。fixture 测试(喂开商店帧断 fail)实证锁定该判别力,浮层改版若致判别失效,该测试先红。

**B. `CwActionCollectOreOp`——不加截图守卫,契约内处置(与 A 不同案)**

不装 `check_and_update_current_screen`,三条硬理由:

1. 违反 cw_op 动作 op 契约「零读屏」(该契约分工 = 画面锚归画面 op 观察侧,动作 op 只消费决策载荷;契约出处 `skills/sr-od-dev-currency-war/references/flow/action-op.md`);
2. sim 互锁:CwOperation 的 sim 分支 `screenshot()` 返回模块级缓存的 1080p 纯零哨兵帧,真识别恒空 → retry 耗尽 fail;该 op 是注册表派发的 sim/实机共跑路径,装锚即 sim 全挂;
3. 热路径成本:备战循环一拍可派发多动作,每动作一次全屏识别是数量级浪费;上游 `cw_screen_prep` 入口锚 + 观察边界对账已把错屏拦在派发之前。

补强 = docstring 前置声明显式化(零逻辑改动):类 docstring 在「起点:货币战争-备战画面(动作执行时)」后补「入口画面锚归画面 op 观察侧(cw_op 零读屏契约);错屏防线 = `cw_screen_prep` 入口判定 + 下一帧观察对账,本 op 不自判」。

**C. actions 包读屏契约修订**(`operations/actions/__init__.py`,治根)

包 docstring「三条纪律边界」的第三条整段替换为(零判效/零决策两条纪律不动):

> - **读屏受限(合法读屏面仅下列两类,其余读屏一律禁止;读 screen_info 档非读屏,不受此限)**:
>   ① **动作本体的目标定位**:坐标默认从画面档静态解析;例外 `cw_collect_reward_ores` 的晶矿识别(识别球→点球,识别即动作本体的一部分)——识别结果只决定点哪几个点,不判动作生效;
>   ② **入口画面锚(防 bug 守卫,非判效;AGENTS §3 对 op 入口的硬性要求)**:识别结果可空、可能以「成功零效果」返回的识别类原语,入口做画面级判定(`check_and_update_current_screen`),非预期画面显式失败带画面名,禁静默空转;固定坐标类原语暂不强制,族内推广另行立项评估。

修订语义:入口画面锚是「读屏受限」纪律的**第二合法读屏面**(锚判定对帧跑画面识别,是读屏非读档)——与①并列列举,消除「第一条标题绝对化、第二条强制锚」的字面冲突;原晶矿例外行的「不做画面状态判断、不设前置守卫」两短语删除(口径错误根源),「不判动作生效」保留,零判效/零决策两条纪律未放开任何禁拆项。

**涉及文件**:

| 文件 | 改动 |
|---|---|
| `src/sr_od/application/currency_war/operations/actions/cw_collect_reward_ores.py` | 入口锚 + docstring 改写(≈ +15~25 行) |
| `src/sr_od/application/currency_war/operations/actions/__init__.py` | 读屏契约第三条整段替换(≈ +10/-5 行) |
| `src/sr_od/application/currency_war/operations/cw_op/cw_collect_ore_action.py` | 仅 docstring 前置声明(≈ +3 行) |
| `sr-od-test/test/sr_od/application/currency_war/operations/actions/test_cw_collect_reward_ores.py` | 新建(见测试点) |

**测试点**(镜像路径新建;harness 同件 1;测试前后显式复位共享 `test_context` 的 screen_loader 画面状态,两件测试互不残留):

1. 错屏显式失败(本件核心):喂开商店 fixture 帧(如 `货币战争-备战-开商店/shop_open.webp`)→ `round_fail`,status 含实际画面名「货币战争-备战-开商店」;喂无关画面帧 → fail,status 含「未识别」或真名;两种情况点击记录为零(守卫拦在识别与点击之前)。测试 docstring 承载守卫判别力依据(见上)。
2. 备战画面回归:喂带晶矿备战 fixture 帧(`reward_spheres_4/5/8/11_sparse/15` 系列按需)→ 识别 + 逐点点击与现口径一致(点击数 = min(球数, max_clicks),坐标 = 球心);喂无晶矿备战帧(`reward_panel_empty`)→ 仍 `round_success('场上无晶矿')`——备战屏的空读成功语义保留,只有错屏才转 fail。
3. 参数校验:`max_clicks` 越界 `ValueError` 不受影响(锁 op 契约完整面;属边缘保留项,实施者可裁)。

`CwActionCollectOreOp` 无行为改动,不新增测试(注册完备测试 `test_action_registry` 已覆盖派发面)。

**风险**:

- 识别帧时序:守卫用入口帧判定,点击前画面若瞬变仍可能错点——与现状同险,不在本件扩大;零判效对账兜底。
- `check_and_update_current_screen` 在 sim 哨兵帧下恒未命中:该 op 是实机 MCP 原语、sim 不消费(src 零调用方),若未来 sim 要跑它,须先给 sim 装画面应答(实施注记,不阻塞本件)。
- 契约文本修订后,实施须 grep「不设前置守卫」全库消费点防口径双源残留(现存量 = 包契约一处 + `cw_collect_reward_ores.py` docstring 引述,本件同步删,消费面干净)。

### 2.3 件 3:DragCwChar 类 docstring 按 §9 三要素补齐(纯注释,零逻辑)

类 docstring 重写为两段式,`:param` 段逐参数带坐标系 / 基 / 与 extras 的换算关系 + 取值时机,定稿文本:

```python
"""货币战争 拖动角色(通用,槽位输入;开发 / 测试用)+ 统一拖拽原语 ``drag_char``。
起点:货币战争-备战画面;终点:原画面(角色已拖到目标槽位)。
消耗:零(纯界面拖拽;落地事实归调用方下一帧 analyze_screen 对账)。

槽位坐标系(本 op 恒 1 基画面物理槽位):from_idx / to_idx = 「货币战争-备战」
画面物理槽位号 = screen_info「前排-N / 后排-N / 备战栏-N」area 序号,1 基,
构造期校验 1-99;取值时机 = 调用方按当帧读数传参(本 op 零读屏不现读,坐标
新鲜度纪律归调用方)。与 extras 换算:extras.bench.slots 数组为 0 基下标,
备战栏槽位号 = 数组下标 + 1(同 CwSellBenchBySlot.slot 口径)。
与 CwActionMoveUnitOp(cw_op 域)基差异:其 bench 参数为 0 基状态容器
下标、front/back 为排内 1 基画面槽号——同族拖动动作两类基不同,跨类传参
前先对表,勿以本 op 口径直填其参数(反之亦然)。

``run_operation`` 调用例::

    run_operation('...drag_cw_char.DragCwChar',
                  args={'from_row': 'bench', 'from_idx': 9, 'to_row': 'bench', 'to_idx': 1})
    # from_idx/to_idx 均 1 基画面物理槽位:bench 9 = 备战栏第 9 槽(extras 下标 8)

生产侧(deploy / sell)直接调 ``DragCwChar.drag_char(op, src, dst)`` 静态原语(坐标输入,不走节点图)。

:param from_row: 源行:``"front"`` / ``"back"`` / ``"bench"``。
:param from_idx: 源槽位号,1 基画面物理槽位(前排 1-4 / 后排 1-6 基准 / 备战栏 1-9;
    = screen_info 对应 area 序号);越界构造期拒绝。
:param to_row: 目标行(同 ``from_row``)。
:param to_idx: 目标槽位号(同 ``from_idx`` 口径)。
:param back_centers: 后排实际槽位中心 ``[[x, y], ...]``,1080p 画面像素坐标;
    数组 0 基,第 N 项 = 后排物理槽位 N+1。后排 >6(财富宝钻扩容)时由调用方
    按当帧读数传入运行时检测值;``None`` = 用 screen_info「后排-N」基准档。
"""
```

配套:

- `__init__` docstring Args 块删除(内容上移类 docstring;对照模板 `CwSellBenchBySlot` 无 `__init__` docstring,单一源防双头漂移);构造期校验的行内注释保留并核对口径一致;`back_centers` 转换处行内注释补「数组 0 基 ↔ 槽位 1 基(idx-1 取用)」。
- 逻辑、签名、校验、节点图一律不动。

**涉及文件**:`src/sr_od/application/currency_war/operations/actions/drag_cw_char.py`(≈ +35/-15 行,全注释)。

**测试点**:无逻辑改动,不新建行为测试。验证面 = `describe_operation` 实际输出核对(`:param` 段透出、三要素齐、调用例带基注释——部署事故的回归判据就在这一步)+ `ruff check` 该文件 + CW 快速集跑一遍确认零行为漂移。

**风险**:几乎零风险;唯一注意点:`__init__` docstring 删除后 IDE 悬浮提示退化到类 docstring,信息无损(内容上移)。

### 2.4 硬约束核对(逐件实施自查)

- 类型注解齐全(本批不新增/不改签名);中文注释写「为什么」;引用持久索引(文件路径/符号名)或纯语义描述,禁会话局部标识符与 gitignored 本机文件路径进代码注释与本设计正文。
- round 系 wait 一律显式(件 1 开拓分支、件 2 守卫 fail 均显式填,禁默认值)。
- op docstring 契约:类 docstring 两段式(效果 + 起终点 + 副作用行 / `:param` 段),describe 透出为准。
- screen_info 改动必须走 MCP 工具(`upsert_screen_area`),禁手改 yml(合并缓存)。
- 坐标单一真相源:件 1 徽记定位读画面档 area,零硬编码坐标。
- 文档同步(skill 画面卡、actions 包契约)随各自 commit 走,不留尾。
- 测试纪律:harness 剧本演、零真实副作用、fixture 进测试仓、`fast_sleep` 包 `execute()`、新测试子目录不带 `__init__.py`、识别单帧秒级预期不触慢线(实施后按实测登记)。

### 2.5 改动面与实施顺序

| 件 | 文件数 | 行数量级 | commit 面建议 |
|---|---|---|---|
| 件 1 | 5(含 1 画面档经 MCP + 1 测试新建) | ≈ +160 / -15 | 单独一 commit |
| 件 2 | 4(含 1 测试新建) | ≈ +130 / -20 | 单独一 commit(契约行与 op 守卫同 commit,治根与治症不拆) |
| 件 3 | 1 | ≈ +35 / -15(全注释) | 单独一 commit |
| 合计 | 10 | ≈ +325 / -50 | 三件三 commit,互不依赖可并行实施 |

实施顺序建议:件 3 最小先行(纯注释,零风险热身)→ 件 2(守卫 + 契约)→ 件 1(需实机窗口核徽记带位)。每件实施后按 od-dev-write-operation 验收三连(`list_operations` / `describe_operation` / `run_operation` 单跑)+ 对应新测试过绿再 commit;`git add` 逐文件点名(并行批卫生),提交后 `git show --stat` 复核入库面 = 申报面。
