# BOSS 头像模板库落位接入 × CW 模板根级上移设计（boss-avatar-library-integration）

> 状态：设计定稿 v2（v1 按「仅 boss 库落位」设计；v2 按用户裁定扩展为「currency_war 类目整体退役、全部 CW 模板上移根级」的落位口径重算，接入语义部分沿用 v1 结论）。本批只设计不实现，实现归后续批。
> 用户裁定（不可违背）：① 现役旧库 `assets/template/currency_war/boss_avatar/`（21 张平铺 PNG）沿用不改——识别现役不因本设计被破坏；② 新 boss 库落位 `assets/template/cw_boss_avatar/`（统一模板批 21 公司，见 §1.2）；③ 全部 CW 模板去掉 currency_war 这一层：`assets/template/currency_war/<模板名>/` 上移为 `assets/template/cw_<模板名>/`（根级、cw_ 前缀），currency_war 类目整体退役（boss 旧库按裁定①豁免留位，类目完全退役挂在旧库退役之后）；④ 先设计后实现。

## 1. 背景与现状

### 1.1 boss 头像识别链（接入设计的事实基础）

boss 头像识别链全貌（识别目标：认出「本位面 boss 是哪家公司」，公司名即 `cw_enemy_data.BOSS_MECHANICS` 规范名）：

| 环节 | 位置 | 语义 |
|---|---|---|
| 模板加载 | `cw_node_reader.py::load_boss_templates` | 自定义加载器：`glob('*.png')` 平铺扫描 → 灰度 → SIFT 特征预提取 → `{公司名: (keypoints, descriptors)}`，特征 <4 关键点丢弃 |
| 消费点 A（懒加载全局） | `cw_observation.py` 两处（各自懒加载模块级全局 `_BOSS_TEMPLATES`） | 路径硬编码旧库目录 |
| 消费点 B（节点条域） | `cw_node_reader.py::classify_node_row` boss 槽分支 | 备战节点条最右槽（首领=位面最后节点，位置先验）裁 ~56px patch 做 SIFT |
| 消费点 C（大图标域，主消费） | `cw_screen_plane_intel.py::_read_boss_big_icon` | 位面详情屏详情条「区域-boss大图标」~107px 裁片 SIFT，复用 `_cwo._BOSS_TEMPLATES`；前置「首领」标签验证 |
| 命中判据 | `cw_node_reader.py::match_boss_sift` | **断层门**：好匹配数第一名 ≥ `BOSS_SIFT_MIN_GOOD`(3) 且 ≥ `BOSS_SIFT_RATIO`(2.0)×第二名（含 tie 拦截）。**承重墙，零改动** |
| 测试面 | `sr-od-test/.../obs/test_cw_node_reader.py` | 4 帧归档 fixture（正：深渊育种科技/不死者联盟；负：棋盘格图标位、库外纹章变体），加载路径硬编码旧库目录 |

### 1.2 统一模板批（新 boss 库内容，已验证）

新库内容 = 「统一模板批」：21 家公司各一张 128×128 模板，官方美术原图统一重制，透明底按 alpha 合成实机大图标域底色 RGB(34,30,61)，文件名 = 官方中文公司名。验证结论（实验批报告，私有侧归档不入 git；实测跑批器与生产加载/判定口径逐位同构）：

- **正样本 22/22 命中**，断层余量 4.7×~10×（实机正帧仅覆盖 2/21 公司；其余 19 家 = 同美术同源逐家目检 + 负样本族零误报背书）；
- **负样本 38/38 拒判**（补给图标 ×31、战斗图标 ×5、纹章变体 ×1、节点条域对照 ×2），零误报；补给族出现过第一名 10:10 平分，靠断层门 tie 拦截拦下——门常量是负样本防线的承重机制；
- 另两候选方案被负样本否决禁用：**方案 B**（缩放到裁片尺度 94px）补给/战斗图标 26 帧误报——同尺度圆形模板与域内任意圆形图标环对环系统性碰撞；**方案 C**（合成非实机域底色）战斗图标 2 帧误报。固化为红线：禁止把模板缩放到裁片尺度；禁止用非实机域底色。
- 附带复现旧库历史故障（「混尺度病」，定义见 §3）：60px 不死者模板在实机大图标域被大尺度别家模板抢走次名余量（7 < 2×4 拒判）；同帧换统一模板批后 28 vs 6，余量健康。

### 1.3 现役旧库的已知缺陷（为什么要有新库）

旧库 21 张文件是三种来源混装：19 张 60px 图鉴小图 + 2 张实机大裁片（深渊育种科技 111×110、不死者联盟 94×96）。由此：19 家图鉴公司的实机大图标域得分从未统一验证，负样本族余量很薄（补给帧 4:3、战斗帧 6:5）；混尺度竞争会让别家大裁片吃掉小图公司的次名余量（§1.2 历史故障即此机理）；节点条 boss 域（~40px 锁态小图）两库都过不了门（小图 SIFT 特征坍缩），生产行为 = 保守拒判 `NodeSlot.boss=None`，本设计不改变该预期。

### 1.4 currency_war 模板类目全量盘点（上移设计的事实基础）

`assets/template/currency_war/` 下 24 个模板目录（任务书口径 23 + 在飞批新增 `cw_aura_marker`），按**消费方式**分两类——这决定了上移的形态分支：

**框架链（12 目录，被 screen_info 建档 area 引用，走框架模板匹配栈）**：目录形态 = `config.yml + raw.webp/png + mask.png`（条目目录制）。引用面 = 10 个分 yml 共 17 处 area（另 1 处 `cw_aura_marker` 在飞）：

| 目录 | yml 引用（area 数） | 引用文件 |
|---|---|---|
| cw_adv_layout_back | 1 | cw_advantage_layout.yml |
| cw_adventure_dialog_arrow | 1 | cw_adventure_dialog.yml |
| cw_boss_brief_emblem | 1 | currency_war_boss_briefing.yml |
| cw_lobby_close | 2 | currency_war_lobby.yml + currency_war_shop_card_detail.yml |
| cw_rail_shop_badge | 1 | currency_war_battle_prep_pioneer_shop.yml |
| cw_rail_shop_train | 1 | currency_war_battle_prep.yml（该文件在飞改动中，见 §8 波次） |
| cw_shop_card_locked | 1 | currency_war_battle_prep_shop_open.yml |
| cw_shop_lock_unlocked | 1 | currency_war_battle_prep_shop_open.yml |
| plane_card_current_ring | 3 | currency_war_plane_detail.yml |
| plane_card_viewed_ring | 3 | currency_war_plane_detail.yml |
| synthesis_confirm_ok | 1 | currency_war_prep_synthesis_confirm.yml |
| synthesis_confirm_cancel | 1 | currency_war_prep_synthesis_confirm.yml |

**自定义链（11 目录，代码硬编码路径自读，不走框架匹配栈）**：

| 目录 | 形态 | 消费点 |
|---|---|---|
| boss_avatar | 21 张平铺 PNG | 代码 4（`cw_node_reader`/`cw_observation` ×2/`cw_screen_plane_intel` 经全局）+ 测试 1 + 工具脚本 1（`cw_asset_sentinel.py` 监视项）+ 文档 1 —— **用户裁定豁免留位** |
| character_avatar | 88 角色子目录（raw+mask+src） | 代码 5（`cw_identity_obs`/`currency_war_char_id`/`cw_screen_partner`/`cw_match_recorder` ×2）+ 测试 3 + 工具脚本 2（`cw_asset_sentinel.py`/`gen_plaza_chars.py`） |
| equip_legacy | 平铺 PNG（旧手工装备库，plaza 主库的回退） | 代码 2（`cw_equipment.py`）+ 工具脚本 4（`gen_plaza_chars`/`extract_equip_data`/`harvest_equip_codex`/`harvest_equip_icons`） |
| equip_plaza | 平铺 PNG（官方装备模板库） | 代码 2（`cw_equipment.py`）+ 工具脚本 1（`gen_plaza_chars.py`）—— **并行批在飞，排除候批** |
| loot | 单 webp | 代码 1（`cw_identity_obs.py`） |
| reward_ore | 5 webp + README | 代码 2 + 测试 1 |
| shop_cost | 4 png（费用数字） | 代码 1（`cw_observation._SHOP_COST_TMPL_DIR`） |
| star | 单 png（金星模板） | 代码 1（`cw_identity_obs.py`） |
| star_assets | png + 说明 md（重标定种子档案件） | 0 |
| supply | 4 png（补给事件图标） | 代码 3（`cw_identity_obs.py`） |
| cw_shop_trial_badge | 单 raw.webp（无 config） | 代码 1（`cw_observation._TRIAL_BADGE_TM_PATH` 三元组路径） |

**框架模板体系的扫描与下游**（上移形态裁决的事实）：

- 框架模板体系（`one_dragon/base/screen/template_loader.py` + `template_info.py`）按**两级扫描**工作：`assets/template/<一级类目>/<二级条目>/`，条目目录含 `raw.webp`/`raw.png`/`mask.png`/`config.yml` 任一即被 `get_all_template_info_from_disk` 收录；运行时读取走 `TemplateInfo(sub_dir, template_id)` 硬两级路径。
- screen_info 建档 area 的模板匹配（`template_sub_dir` + `template_id` 两字段）走该框架栈——这是框架链 12 目录的唯一消费方式；src 中无任何 `get_template('currency_war', ...)` 直调。
- `get_all_template_info_from_disk` 下游 3 处：`one_dragon_qt` 开发工具·图像分析（`image_analysis_logic.py`）、开发工具·模板助手（`devtools_template_helper_interface.py`）、`cultivation/light_cone_tpl_store.py`（全盘扫描）——都只做「列举/加载」，上移后对形态的要求 = 仍是合法两级结构。

## 2. 问题一：boss 新库落位形态 —— 结论：平铺 `<公司名>.png`（v1 结论不变）

新库 `assets/template/cw_boss_avatar/` 平铺 21 张，原样复制统一模板批文件（字节级一致），不做目录制、不转 webp。根级 cw_ 前缀路径本就符合新约束，落位节无需重算。理由（v1 已论证，摘要）：

1. 消费方唯一 = SIFT 自定义加载器（`glob('*.png')` + stem 命名），平铺零改动兼容；
2. 验证按这 21 个文件的字节跑，任何重编码（目录制需要转 webp）都是未验证变量；
3. boss 库是自定义链（§1.4 分类），不进 screen_info、不走框架匹配栈，无框架可见性需求；平铺目录对框架两级扫描是空气（L2 扫描 `isdir` 过滤跳过）；
4. 自定义识别链库形态有先例（`character_avatar` 同为框架外读链），平铺不违反「模板读取优先走框架服务」规范——该规范管 screen_info 消费的框架链模板。

## 3. 问题二：接入语义（核心）—— 结论：案①新库主匹配 + 旧库兜底（匹配域隔离；v1 结论不变，上移不影响）

**术语**：「匹配域」= 一次 `match_boss_sift` 调用里参与排序的一组模板。「混尺度病」= 同一匹配域混入多种渲染来源/尺度的模板后，尺度接近识别域的模板分数系统性偏高（别家抢次名余量致拒判真命中，或自身自匹配垄断）。

三案裁优（摘要，详见 v1 论证，结论不变）：

- **案②（旧库主+新库补充）否决**：两库公司集全同（各 21 家同名），「补充未暴露公司」无增益对象，病留主路。
- **案③（双库合并统一断层门）否决**：朴素合并（42 条同域排序）必复发抢分病——SIFT 对尺度鲁棒，同公司旧模板对真帧同样得分并常驻次名（某图鉴公司 X 真帧：新 X≈28、旧 X≈15~20，28 < 2×15 拒判——要修的故障以新形态复发）；按公司取 max 去重可修该形态，但匹配域保持混尺度（旧库薄余量负样本条目持续侵蚀边缘帧余量）+ 匹配热路径新增聚合逻辑 + 回退只有整体粒度。
- **案①（新库主匹配 + 旧库兜底）推荐**：每次 SIFT 按域序跑两遍断层门——先新库（主匹配域）过门即返回；新库拒判再问旧库（兜底域）；两域皆拒 → None（现状失败语义）。**推荐理由一句话：域隔离让每次匹配都是单一尺度域，混尺度抢分与同公司双模板占次名在结构上不可能发生，且兜底命中集严格 ⊆ 现役命中集**（兜底计算与今日现役链逐位相同，只是从无条件跑变为主域拒判后才跑；新链结果 = 主域命中 ∪ 主域拒判后的今日结果，不存在第三种新误报来源）。断层门常量零改动；节点条域两库都拒判 → 行为不变。

## 4. 新解问题：框架两级扫描 vs 根级一级模板目录 —— 结论：案③惯例层同名嵌套（框架链目录），自定义链目录平铺上移

上移后 `cw_<模板名>/` 直接含模板文件 = 只有一级——两级扫描扫不到（L2 必须是目录）。三案裁决：

### 4.1 案①（改框架扫描器，支持根级单层类目）—— 不采纳，登记长期项

框架两级语义是**全项目既有契约**：21 个根级类目、GUI 开发工具、screen_info 全部模板 area 都靠它工作，框架本身无缺陷。根源两问：现象的根不在框架，在 CW 的命名治理诉求与既有布局不匹配——为 CW 局部治理改全局契约，代价 = 公共包 `one_dragon`（SR/ZZZ 共享）改动 + SR→ZZZ 同步流程 + 全项目模板面回归 + 发布打包验收，且产出「全项目两级、CW 独单层」的异构形态。判据（半年后回看）：不值得。**登记**：若未来「根级单层模板」成为跨项目普遍诉求，再立项改框架（走 SR→ZZZ 同步），本设计不预支。

### 4.2 案②（消费端适配）—— 对框架链不成立

框架链消费端 = screen_info yml + 框架 screen 匹配栈，二者一体：yml 的 `template_sub_dir`/`template_id` 就是框架语义，消费端能「适配」的只有改这两个字段的值（这正是案③做的事）或绕开框架匹配栈自实现模板匹配——后者破坏「screen_info 是画面识别唯一事实源」架构，否决。自定义链 11 目录本就不经框架，上移只是路径字符串替换，不存在此问题。

### 4.3 案③（惯例层：框架链目录同名嵌套 `cw_<名>/cw_<名>/raw.webp`）—— 推荐

**形态**：
- 框架链 12 目录（+ 在飞 `cw_aura_marker`）：`assets/template/cw_rail_shop_train/cw_rail_shop_train/raw.webp`——L1=类目、L2=条目同名。框架语义 `TemplateInfo('cw_rail_shop_train', 'cw_rail_shop_train')` 完全合法；yml 两字段同值（`template_sub_dir: cw_rail_shop_train` + `template_id: cw_rail_shop_train`），机械、可 grep。
- 自定义链 10 个上移目录（豁免与在飞除外）：**平铺**上移 `assets/template/cw_supply/专家邀请函.png`——加载器语义是「目录内语义文件名」（stem=公司名/道具名/数字），嵌套会破坏 `glob('*.png')` 契约；且自定义链无框架可见性需求。
- 非 cw_ 前缀目录上移时**同时补 cw_ 前缀**（`plane_card_current_ring` → `cw_plane_card_current_ring` 等 4 个）：命名治理与上移一次完成（v1 的 cw_ 前缀整改判定在此吸收落地）。

**推荐理由一句话：两级扫描是全项目既有契约而非缺陷，CW 治理诉求在惯例层内即可全额满足，零公共包改动、零下游工具改动、完全可逆；双层同名的丑限于一处且形态机械一致。**

代价如实陈述：`cw_x/cw_x/` 双层同名目录有认知成本（打开目录看到同名嵌套）；缓解 = 本设计文档 + 每个此类目录内不再有其他文件（形态自解释）+ yml 两字段同值的强规律（grep 一个名字即得全部面）。

**下游影响核对（全绿）**：`get_all_template_info_from_disk` 照常收录（`cw_x/cw_x/` 是合法两级）；GUI 开发工具（模板助手/图像分析）列表从「1 个 currency_war 类目 × 24 条目」变为「N 个 cw_ 类目 × 各 1 条目」——呈现变化、行为零改动；`cultivation/light_cone_tpl_store` 全盘扫描不受影响；`cw_shop_trial_badge` 平铺后从「框架可见（旧位置含 raw.webp 即收录）」变为不可见——它无任何框架消费（代码三元组自读），无功能影响。

**备选注记（供编排侧转用户，非本设计主案）**：若用户可接受「currency_war 类目改名保留层级」（如整体改名 `cw_templates/`，内部目录名不动），则框架链只需改 yml 的 `template_sub_dir` 一个字段值（17 处机械替换），自定义链只改路径前缀字符串，无嵌套、无改名、改动面约为本案一半——但它不满足「根级 cw_<模板名>」的字面约束，仅在用户松绑该约束时启用。

## 5. 问题三：加载器与消费点改动面

### 5.1 boss 接线（v1 结论不变）

1. `load_boss_templates(templates_dir)` 原样保留（单域加载器），docstring 过时描述顺带修正；
2. 新增域列表装载函数（建议名 `load_boss_template_domains(template_root: Path) -> list[dict[str, tuple]]`）：按序装载 `template_root/cw_boss_avatar`（主域）与 `template_root/currency_war/boss_avatar`（兜底域），空/缺失目录跳过，返回非空域有序列表。**优先级 = 列表序；无跨域去重**；
3. 同名公司裁决：主域先答（主域过门即返回），主域全域拒判才问兜底域——谁先过门谁赢，命中来源恒为单一库，可回溯；
4. `match_boss_sift(patch_gray, boss_templates)` 签名扩 `dict | list[dict]`（dict=单域向后兼容；list=按序逐域，首个过门即返回）；建议抽单域匹配为内部纯函数供域序逻辑单测；
5. `_BOSS_TEMPLATES` → `_BOSS_TEMPLATE_DOMAINS`（`cw_observation` 两处懒加载点 + `_read_boss_big_icon` 同步）；漏改 = AttributeError 响亮暴露；
6. `classify_node_row` 的 `boss_templates` 参数类型放宽为 `dict | list[dict] | None`；
7. 日志带域来源标记（主域/兜底域）——实机期「兜底是否被走到」的唯一观察窗；
8. 测试 fixture `_boss_templates()` 换装域列表（保持 skip-if-missing 纪律）。

### 5.2 上移路径替换面（与 §7 清单一一对应）

- 自定义链代码引用：全是路径构造字符串/常量（`get_project_root() / 'assets' / 'template' / 'currency_war' / 'xxx'` 形态、`_SHOP_COST_TMPL_DIR`、`_TRIAL_BADGE_TM_PATH` 三元组、`Path('assets/template/currency_war/...')`）——逐处替换 `'currency_war'` 层为根级 cw_ 目录名；
- 测试 fixture 路径：`test_identity_obs.py`（reward_ore、character_avatar ×2）、`test_cw_observation.py`（character_avatar）；
- 工具脚本路径：`cw_asset_sentinel.py`（character_avatar 监视项；boss_avatar 项豁免不动）、`gen_plaza_chars.py`（character_avatar/equip_plaza/equip_legacy）、`extract_equip_data.py`/`harvest_equip_codex.py`/`harvest_equip_icons.py`（equip_legacy）；
- 文档性提及（`plane_intel.md` 等 docstring/md）跟随改，非功能面。

## 6. 全量迁移清单（24 目录逐个：旧路径 → 新路径 + 消费点数）

| 旧路径（currency_war/ 下） | 新路径（assets/template/ 下） | 链 | 消费点数 | 迁移波 |
|---|---|---|---|---|
| boss_avatar | **不动**（用户豁免） | 自定义 | 代码4+测试1+脚本1+文档1 | —（随旧库退役批消失） |
| character_avatar | cw_character_avatar/（88 子目录原样） | 自定义 | 5+3+2 | 波1 |
| equip_legacy | cw_equip_legacy/ | 自定义 | 2+4 | 波3 |
| equip_plaza | cw_equip_plaza/ | 自定义 | 2+1 | 波3（**在飞排除**） |
| loot | cw_loot/ | 自定义 | 1 | 波1 |
| reward_ore | cw_reward_ore/ | 自定义 | 3 | 波1 |
| shop_cost | cw_shop_cost/ | 自定义 | 1 | 波1 |
| star | cw_star/ | 自定义 | 1 | 波1 |
| star_assets | cw_star_assets/ | 自定义 | 0 | 波1 |
| supply | cw_supply/ | 自定义 | 3 | 波1 |
| cw_shop_trial_badge | cw_shop_trial_badge/（平铺原样） | 自定义 | 1 | 波1 |
| cw_adv_layout_back | cw_adv_layout_back/cw_adv_layout_back/ | 框架 | yml 1 | 波2 |
| cw_adventure_dialog_arrow | cw_adventure_dialog_arrow/同名嵌套 | 框架 | yml 1 | 波2 |
| cw_boss_brief_emblem | cw_boss_brief_emblem/同名嵌套 | 框架 | yml 1 | 波2 |
| cw_lobby_close | cw_lobby_close/同名嵌套 | 框架 | yml 2 | 波2 |
| cw_rail_shop_badge | cw_rail_shop_badge/同名嵌套 | 框架 | yml 1 | 波2 |
| cw_rail_shop_train | cw_rail_shop_train/同名嵌套 | 框架 | yml 1 | 波2b（在飞文件顺延） |
| cw_shop_card_locked | cw_shop_card_locked/同名嵌套 | 框架 | yml 1 | 波2 |
| cw_shop_lock_unlocked | cw_shop_lock_unlocked/同名嵌套 | 框架 | yml 1 | 波2 |
| plane_card_current_ring | cw_plane_card_current_ring/同名嵌套 | 框架 | yml 3 | 波2 |
| plane_card_viewed_ring | cw_plane_card_viewed_ring/同名嵌套 | 框架 | yml 3 | 波2 |
| synthesis_confirm_cancel | cw_synthesis_confirm_cancel/同名嵌套 | 框架 | yml 1 | 波2 |
| synthesis_confirm_ok | cw_synthesis_confirm_ok/同名嵌套 | 框架 | yml 1 | 波2 |
| cw_aura_marker | cw_aura_marker/同名嵌套 | 框架 | yml 1 | 波2b（**在飞排除**） |

合计：上移 22 目录（平铺 10 + 同名嵌套 12），豁免 1（boss_avatar），波1 承载 7 目录 + boss 新库落位 + `cw_shop_trial_badge`。

## 7. 问题四：迁移分步与回退

### 7.1 分批裁决：分三波 + 一个顺延位（不做一次性大迁移）

一次性迁移把「资产 git mv + 自定义链代码 + 框架链 yml/merged + 在飞协调」压进单 commit——验证面互相纠缠、回退粒度全有全无，且 equip_plaza/cw_aura_marker/battle_prep.yml 的在飞面本来就不允许一次动。分波原则：**同一消费链的资产与引用同波同 commit（不留断链中间态）；不同链之间互不阻塞**。

### 7.2 波次定义

**波1（自定义链，纯机械替换）**：7+1 目录 git mv 平铺上移（§6 波1 列）+ boss 新库落位（21 张 PNG 原样复制到 `cw_boss_avatar/`，禁重编码）+ boss 接线四文件（§5.1）+ 自定义链代码/测试/脚本路径替换 + 受影响 T1。资产与代码同 commit。落位与接线可拆两个 commit（落位独立安全）。

**波2（框架链主体）**：11 目录 git mv 同名嵌套（§6 波2 列）+ 16 处 area 经 MCP `upsert_screen_area` 改 `template_sub_dir`/`template_id` 两字段（合并缓存随写再生；禁手改分 yml）+ GUI 开发工具列表核对 + 相关屏 area 命中验证（`get_screen_detail`/`analyze_screen`）+ T1 全量。资产与 yml 同 commit。

**波2b（在飞收口后顺延）**：`cw_rail_shop_train`（git mv + `currency_war_battle_prep.yml` 1 处 upsert）、`cw_aura_marker`（在飞批新增目录+引用，随其收口按同形态迁移）。

**波3（equip 家族，在飞收口后顺延）**：`equip_plaza`、`equip_legacy` git mv + `cw_equipment.py` 4 处 + 4 个工具脚本一次改净——两目录绑同一代码文件，合并一波避免两次抢改。

**currency_war 类目终态**：波1/2/2b/3 完成后类目内只剩 `boss_avatar`（豁免）；类目完全退役 = 旧库退役批（§7.3）删除 boss_avatar 后清空目录。

### 7.3 旧库退役（独立批，须用户裁定）

判据建议：boss 接线后累计实机局中主域全覆盖三位面 boss 命中、零兜底命中、零误报，持续 N 局（N≥3 起议）→ 删除 `currency_war/boss_avatar` 目录 + 兜底域装载 + 相关测试/脚本监视项。本设计只给判据不执行。

### 7.4 回退开关

| 层 | 开关 | 操作 | 效果 |
|---|---|---|---|
| boss 主域 | A | 删/改名 `cw_boss_avatar/` 目录 | 域列表只剩兜底域 = 今日现役行为，零代码 |
| boss 兜底域 | B | `cw_node_reader.BOSS_TEMPLATE_FALLBACK_ENABLED: bool = True` 置 False | 纯新库链 |
| boss 接线 | C | revert 接线 commit | 回今日链 |
| 上移各波 | D | revert 该波 commit（git mv 双向可逆；yml 经 MCP 重写旧值；merged 随写再生） | 该波消费链回旧路径，其他波不受影响 |

## 8. 验证设计

1. **boss 语料复放（一次性，波1 验收）**：私有侧实验语料 60 帧（22 正 + 38 负，真值表随实验批归档）对接线后链路复放：22 正全命中且断层余量与实验报告一致、38 负两域皆拒、无「主域拒→兜底过」实例。复放脚本与结果归迭代目录（易失区），不入 git。
2. **boss 负语料持久化（波1 内做）**：从私有语料挑代表性负帧（补给 2~3 帧 + 战斗 1 帧）复制进 `sr-od-test/screens/货币战争-位面详情/`（测试仓本地私有，既有 4 帧 fixture 同库）；私有语料本体（私有侧临时目录，易失）不得作为任何测试的依赖。
3. **T1**（`uv run pytest sr-od-test/test/sr_od/application/currency_war -m "not slow"`）：
   - 现有 4 帧 fixture 测试换装域列表链路（断言不变：命中公司名/门通过/负帧不命中）；
   - 新增：新库装载完整性（21 文件可加载且特征 ≥4；新库目录缺失 → 域列表只剩兜底域的退化语义）；
   - 新增：域序逻辑单测（主域过门 → 返回主域且不问兜底；主域拒 → 兜底过 → 返回兜底；两域皆拒 → None）；
   - 波1/2/3 各波后全量 T1（`test_identity_obs`/`test_cw_observation` 直接受上移影响）。
4. **上移验证点**：
   - 波2 后：GUI 开发工具模板列表核对（新类目可见、`currency_war` 只剩 boss_avatar 条目）；波2 涉及屏的 area 经 `get_screen_detail`/`analyze_screen` 核对命中（位面详情/大厅/商店开卡/简报/优势布局/奇遇对话/合成确认）；
   - 波次通用：`git status` 无残留旧目录、`grep -r "currency_war'" src` 仅剩 boss_avatar 豁免面与包路径（`sr_od.application.currency_war` 不受影响）。
5. **实机回归（至少一局完整对局，波1 后）**：位面情报采集三位面 boss 全命中（日志含命中名、好匹配数、域来源）；备战节点条 boss 槽无回归（`boss=None` 保守语义不变）；全局无 boss 识别响亮失败；波2 后跑一局覆盖框架链屏（商店开卡/合成确认/位面详情均会走到）。

## 9. 风险清单

| # | 风险 | 缓解 |
|---|---|---|
| R1 | 主域 19/21 公司无实机正帧背书 | 兜底域在（退化=现役行为）；实机回归点；拒判=响亮失败不静默 |
| R2 | 主域语料外负样本族理论误报空间 | 门零改动（tie 拦截实证承重）；负语料持久化扩族；日志域标记归因 |
| R3 | 兜底路径「主域拒→兜底过」边缘帧不确定性 | 语料无实例；日志监控；开关 B |
| R4 | 节点条 boss 域误以为会改善 | 显式预期：两库都拒判，行为不变 |
| R5 | 全局缓存改名漏改消费点 | AttributeError 响亮；T1 覆盖四文件 |
| R6 | 落位文件被重编码致验证失效 | 波1 铁律：纯复制 + commit 二进制核对 |
| R7 | 目录缺失退化语义被误读为故障 | 装载函数 docstring 写明：新库缺失=纯旧库（回退 A 正规用法）；双库全空=boss 识别关闭（现状同） |
| R8 | 新库目录进打包分发面未确认 | 波1 验收确认安装包含新目录 |
| R9 | 惯例层双层同名目录认知成本 | 本文档 + 形态自解释（目录内无其他文件）+ yml 两字段同值强规律 |
| R10 | 在飞面冲突（equip_plaza/cw_aura_marker/battle_prep.yml） | 波次隔离：在飞目录/文件全部顺延波2b/波3，迁移批不碰在飞文件 |
| R11 | GUI 工具列表形态变化（1 类目→N 类目） | 行为零改动仅呈现；波2 验证点核对 |
| R12 | merged 合并缓存未再生导致 yml 白改 | 只走 MCP `upsert_screen_area` 正规通道（随写再生）+ area 命中验证 |
| R13 | `cw_shop_trial_badge` 平铺后框架可见性变化 | 无框架消费（代码自读），无功能影响；文档注记 |
| R14 | 路径替换漏网（`'currency_war'` 与包路径/本地遥测路径同名词） | 替换纪律：只动 `assets/template` 语境的引用；§8.4 的 grep 复核口径（剩余命中应仅 boss_avatar 豁免面 + `sr_od.application.currency_war` 包路径 + 本地遥测目录） |

## 10. 设计裁决记录（why 收敛）

- 落位平铺不目录制：字节一致性即验证继承；框架可见性零收益（§2）。
- 案①域隔离不合并：混尺度病与同公司双模板抢分的根都在「两库同场」，隔离是治本，按公司 max 合并是带新代码的缓解（§3）。
- 兜底而非替换：旧库 2 张实机大裁片是现役唯一实机强验证模板，保留为兜底以最小代价继承其能力，同时不放弃「识别现役不破坏」约束；退役另走用户裁定（§7.3）。
- 门零改动：门常量是正负两侧实证承重墙（正样本最小余量 4.7×、负样本 10:10 靠 tie 拦截），任何调整同时动摇两侧已验证结论（§1.2）。
- 框架链惯例层嵌套、自定义链平铺：两级扫描是全项目既有契约而非缺陷，为 CW 局部治理改公共包是全局担局部成本；两种形态各自贴合消费方的读取语义（§4）。
- 分波不一次性：消费链异质（代码替换/yml+merged/在飞协调），同链同波同 commit 保断链不出现，异链解耦可独立回退（§7.1）。
- character_avatar 上移即撞名治理：根级已有助战选人框架库 `character_avatar`，CW 库上移为 `cw_character_avatar` 顺带消解长期撞名歧义（§6）。
