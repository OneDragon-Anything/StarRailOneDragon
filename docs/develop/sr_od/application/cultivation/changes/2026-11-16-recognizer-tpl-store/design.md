# 识别器模板缓存 ctx 化（recognizer-tpl-store）迭代设计（总纲）

## 0. 元信息

- 迭代目标：用户裁定三点——①两域识别器的 9 个模块级进程缓存迁为「每域一个类型化 store」，挂 SrContext；②SIFT/BFMatcher 无状态单例留模块级（释义：不落实例/类状态；模块归属随单一源原则落 store 模块，见 §2.2）；③卡面库遍历（`iter_*_templates`，config 层）全收归 store。源起 = `test_superimpose_templates_exist` 冷缓存必炸被测试顺序掩盖（同一测试四种口径结果不一致的「flaky」假象）。
- 状态：定稿（三核对抗收敛，报告 = attack.md；修订稿已吸收全部攻击点）
- 文档清单：无详设——单文档即完整设计

## 1. 问题与动机

### 1.1 现状症状

- `test_superimpose_templates_exist`（[test_light_cone_list_recognizer.py:78](sr-od-test/test/sr_od/application/cultivation/light_cone/operations/test_light_cone_list_recognizer.py)）单跑必挂 `AttributeError: 'TemplateLoader' object has no attribute 'template_loader'`；文件内整跑则过（前序 `test_cone_recognizer` 走生产路径预热了模块级全局缓存）。
- 口径差：`-m "not slow"` 全量挂（两个预热者 `test_cone_recognizer` / `test_locate_on_fixtures` 均登记 `sr-od-test/slow_marks.txt:53-54` 被滤掉，本测试成为全局缓存首个触碰者）；全量含慢桶则过（`test_equip_light_cone.py` 字母序在前先预热）。同一测试四种口径（单跑/文件内/not-slow 全量/全量）结果不一致。
- 该测试把 `test_context.template_loader`（TemplateLoader 本身）传给签名要 ctx 的 `_superimpose_templates(ctx: SrContext)`（[light_cone_list_recognizer.py:459](src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py)）；测试仓考古：测试诞生（测试仓 4000456f）与生产引入全局缓存（主仓 fb0c1bb6c，`git log -S _superimpose_tpl_cache` 可核）同批，冷路径自出生即错——绿灯是假阳性，从未验证其声称锁的「TemplateLoader 规范加载」。
- 依据：四种口径实测（单跑挂/文件跑过/not-slow 全量挂/全量过）+ 上列 git 命令。

### 1.2 根因归层

- **表示层（主）**：9 个派生模板缓存的承载位置错——挂在模块级进程全局，而其语义作用域 = ctx（内容 = `ctx.template_loader` 与静态盘上资产的只读派生视图）。进程级 first-caller-wins 使「进程内谁先调用」成为语义，测试间状态泄漏由此可能。依据：全局清单 [light_cone_list_recognizer.py:346/456/634-636](src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py)、[relic_list_recognizer.py:329/606-608](src/sr_od/application/cultivation/relic/relic_list_recognizer.py)。
- **约定层（次）**：AGENTS.md「测试规范」§10.3 已要求「被测生产代码内部改模块级全局，setup 一并桩掉」，涉事测试未执行；且全局以下划线私有命名，复位没有正常入口。同款缓存由分家批次（2026-11-11-domain-restructure）在两域各复制一份，属系统性模式而非孤例。
- 修复语义区分（防记混两类修复）：传参错位 bug 本体（loader 当 ctx 传）由 §2.6 测试重写消灭；store 化消灭的是其**掩盖机制**（first-caller-wins 造成的口径依赖）与 config 层 `getattr(ctx, ..., None)` 动态属性的静默兼容（收归后缺 store 属性即 AttributeError 快速失败）。

### 1.3 解决到哪 / 明确不解决

解决（§2 全部）：缓存迁 store、卡面库遍历收归、破测试重写、config 层两模块退役、四口径一致性验收。

豁免判据（统一口径）：**内容确定性派生 + 函数不收 ctx（无调用者身份语义）** 的进程级缓存不迁。逐项：

1. 识别算法/匹配逻辑/阈值——生产行为零变化，改动面仅缓存承载位置与 §2.5 申报的 loader 实例身份统一（内容零变化）；
2. 头像小图标裸路径资产布局（`_MINI_DIR_REL` 指向的平铺 png 目录不走 TemplateLoader，现状保留）；
3. `build_info._fingerprint_cache` 豁免——单值 str memo，内容与环境无关；
4. CW 域 `_COST_DIGIT_TEMPLATES`（cw_observation）/`_ENV_PORTAL_EFFECTS`（cw_effect_inventory）——静态盘上资产/仓内表派生、函数不收 ctx，落豁免判据，不迁；
5. 两域 icons 数据重复（同目录各读一份，现状即如此）；
6. session 级 `test_context` 共享机制本身（conftest 纪律已有，本迭代不改）；
7. one_dragon 公共包同族（yaml_operator `cached_yaml_data` 带 `invalidate_cache` 入口、i18、`lru_cache` 路径 memo 族）——键控或确定性 memo，无「谁先建改变内容」语义，属公共包跨项目同步治理，另批走公共包同步流程，非本项目 changes/ 范围。

## 2. 方案（完整设计）

### 2.1 系统级变化一句话

两域识别器的派生模板缓存从「模块级进程全局 + config 层 ctx 动态属性」收敛为「每域一个类型化 store 实例，挂 SrContext `@cached_property`」；config 层两个卡面库模块退役，读盘与校验逻辑收归 store。

### 2.2 Store 结构（两域同构形状、各域复制）

| 域 | 文件（新建） | 类 | SrContext 挂载属性 |
|---|---|---|---|
| 光锥 | `src/sr_od/application/cultivation/light_cone/light_cone_tpl_store.py` | `LightConeTplStore` | `light_cone_tpl_store` |
| 遗器 | `src/sr_od/application/cultivation/relic/relic_tpl_store.py` | `RelicTplStore` | `relic_tpl_store` |

两域容器不共享基类（用户裁定①；依据 = cultivation 正本 README §2/§3「两域零共用」哲学，分家批次连算法底层都各域复制，共享容器恰恰构成波及面）。

**构造签名**：`__init__(self, template_loader: TemplateLoader)`——只注入 loader，不持 ctx。契约测试可零 ctx 自建实例。

**视图清单（原承载 → store 属性映射）**：

| 原承载 | 域 | store 属性（懒构建） | 类型 | 数据源 |
|---|---|---|---|---|
| `_tm_prep_cache` | 两域 | `tm_prep_tpls` | `dict[str, list[tuple[np.ndarray, np.ndarray]]]` | `card_faces` 派生（raw 缩放双档 + 前景 mask，键 = 光锥名/遗器件名，与现状一致） |
| `_superimpose_tpl_cache` | 仅光锥 | `superimpose_tpls` | `dict[str, np.ndarray]` | **原 `_superimpose_templates` 函数体迁入**：`template_loader.get_all_template_info_from_disk()` 过滤 `light_cone_superimpose`，盘上已是归一 26×26 紧圆灰度裁片，仅做 RGB→灰度转换，**无运行时缩放**（依据：现状函数体 [light_cone_list_recognizer.py:459-473](src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py) 无 resize，资产实测 26×26） |
| `ctx.light_cone_templates`（动态属性） | 光锥 | `card_faces` | `list[LightConeTemplate]` | `assets/template/light_cone_icon/` 读盘 + 命名校验（原 `iter_light_cone_templates` 函数体） |
| `ctx.relic_templates`（动态属性） | 遗器 | `card_faces` | `list[RelicTemplate]` | `assets/template/relic_icon/` 读盘 + 命名校验（原 `iter_relic_templates` 函数体） |
| `_tpl_cache` | 两域 | `icon_tpls` | `dict[str, np.ndarray]` | avatarminiicon 裸路径读盘（RGBA 取 RGB，现状保留） |
| `_feat_cache` | 两域 | `icon_feats` | `dict[str, dict[int, tuple[list, np.ndarray \| None]]]` | `icon_tpls` 派生（SIFT 多尺度） |
| `_hist_cache` | 两域 | `icon_hists` | `dict[str, np.ndarray]` | `icon_tpls` 派生（HSV 直方图） |

**构建纪律**：

- 所有视图懒构建，构建后只读；store 不提供清缓存接口——静态资产派生无失效场景。
- **测试隔离两档**（session 级 test_context 下 ctx 级单例的 first-caller-wins 仍在，无害性依据在此）：
  - 契约类测试自建 store 实例（§2.6 重写测试、识别器测试 `_fake_ctx` 注入），零共享；
  - 走共享 `test_context` store 的测试（owner 基准、`test_pos_template_subset`）依赖**内容确定性**：各视图 = 静态盘上资产 + mys 常量表派生，构建与 ctx 实例无关，「谁先建」只影响构建时机、不影响内容。
  - 残余边界（显式申报）：store 构建期 bug 仍只由全进程首触测试暴露、首触者随口径漂移——与本案同形的掩盖结构收敛到构建期，因构建逻辑为确定性读盘 + 纯函数派生，判定可接受。
- `card_faces` 命名契约不变：目录名违例 raise、缺原图 raise，错误文案随原实现迁入（受控资产错误立即暴露，优于静默跳过）。
- `_fg_mask_from_rgb`（四角中位底色前景 mask，纯函数）随 `tm_prep_tpls` 构建迁入 store 模块。
- 构建期常量随构建迁 store：光锥 `_TM_TARGET_PX` / `_TM_TARGET_PX_SELECTED`（100/106 双档）、遗器 `_TM_TARGET_PX` / `_TM_TARGET_PX_SELECTED` / `_TM_TARGET_PX_ROPE` / `_TM_TARGET_PX_ROPE_SEL`（90/96 与连结绳 92/96，pos==6 分支保留在构建逻辑内）、`_MINI_DIR_REL`；匹配期常量（门槛/级联/直方图排名上限等）留识别器不动。光锥 `_SUPERIMPOSE_NORM_SIZE = (24, 24)` 为全仓零引用死常量（grep 证实），随迁**删除**。
- `_SIFT`（`cv2.SIFT_create(nfeatures=400)`）与 `_UPSAMPLE_SCALES` 定义迁到 store 模块（构建侧需要），识别器 import 使用——匹配侧 zone 特征提取与构建侧同参，单一源；`_MATCHER`（BFMatcher）仅匹配侧用，留识别器。用户裁定②「留模块级」释义 = 留模块级承载（不落实例/类状态），模块归属随单一源落 store 模块。

### 2.3 SrContext 挂载

- 两个 `@cached_property`（[sr_context.py](src/sr_od/context/sr_context.py) cached_property 区段），property 体 = `LightConeTplStore(self.template_loader)` / `RelicTplStore(self.template_loader)`。docstring 声明：静态资产派生懒构建、不进 `reload_instance_config()` 重置（那是 `cw_match` 类每局运行态的事）、ctx 亡则亡。
- store 模块惰性 import 于 property 体内（先例 = [sr_context.py](src/sr_od/context/sr_context.py) `__init__` 体内 import 与 `currency_war_strategy_plugin_dirs` cached_property 体内 import；`cw_match` 字符串注解为同向先例）——store 不 import SrContext，无依赖环。
- 可观测但无害的承载面变化（显式申报）：原 iter 用临时 `TemplateLoader()`，收归后 `get_template` 把卡面库 TemplateInfo 注册进共享 loader 字典——全仓无功能消费方枚举 `loader.template` 字典（grep 证实），同一批对象改由两处引用、总驻留面不变。

### 2.4 识别器侧改法

- **改一行委托**（签名不变、函数体读 `ctx.<store>.<视图>`、`global` 删除）的仅三处：`_superimpose_templates(ctx)`（光锥）、`_tm_templates_all(ctx)`（两域）——它们是仅有的读全局函数。
- **纯组合 helper 不动**（不读 global、签名不变、函数体不变）：`_tm_template_lists(ctx)`（光锥）、`_tm_templates_all_lists(ctx)` / `_tm_templates_for_pos(ctx, pos)`（遗器，后者 PIECE_TO_SET 过滤逻辑留识别器）。
- icons 三件套（`_templates()` / `_tpl_features()` / `_tpl_hists()`，无 ctx 签名）**整体删除**，构建迁 store；唯一下游 `match_owner` 增加 `ctx` 参数（`match_owner(screen_rgb, badge_rect, min_inliers, ctx)`），函数体改读 `ctx.<store>.icon_feats` / `icon_hists`。
- 调用点全清单（全部零改动，除 match_owner 见下）：
  - 改委托函数的被调点：light `_superimpose_templates`@[274](src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py)（`_read_superimpose` 体内）、`_tm_templates_all`@[393](src/sr_od/application/cultivation/light_cone/light_cone_list_recognizer.py)（`_tm_template_lists` 体内）；relic `_tm_templates_all`@[377/392](src/sr_od/application/cultivation/relic/relic_list_recognizer.py)（`_tm_templates_all_lists` / `_tm_templates_for_pos` 体内）。
  - 组合 helper 的被调点：light `_tm_template_lists`@300（`recognize` 体内）；relic `_tm_templates_all_lists`@228（`_recognize` 体内）、`_tm_templates_for_pos`@227/257（`recognize` / `recognize_for_pos` 体内）。
  - icons 三件套被调点（随三件套删除/迁建）：light 663/681/742/751、relic 633/651/710/719。
- `match_owner` 调用点：light `recognize` 内 1 处（304）、relic `_recognize` 内 1 处（270）——传 ctx；测试 4 处（见 §2.6）。
- docstring「进程级缓存/常驻」措辞改「ctx 级（store）」。识别算法/阈值/调用结构零变化。

### 2.5 config 层收归与退役

- `src/sr_od/config/light_cone_templates.py`、`src/sr_od/config/relic_templates.py` **全文件退役**：模块 docstring 契约（命名约定即注册表）、`LightConeTemplate` / `RelicTemplate` dataclass、`LIGHT_CONE_TEMPLATE_SUB_DIR` / `RELIC_TEMPLATE_SUB_DIR` 常量、`relic_template_id()` 公式函数、读盘校验逻辑——全部迁入对应 store 模块。
- `LIGHT_CONES` / `RELIC_SETS` / `RELIC_POS_EN` 权威表留 mys 模块不动（store import 之）；`sr_relic_sets.py` 模块 docstring 中指向 config 模块的持久指针改指 store（遗器侧，[sr_relic_sets.py:16](src/sr_od/mys/sr_relic_sets.py)）。
- 原先经 `getattr(ctx, 'light_cone_templates', None)` / `getattr(ctx, 'relic_templates', None)` 的动态属性缓存消失（无类型注解的 loose 模式一并清除）。
- loader 实例身份统一（行为零变化申报）：原 iter 函数体内新建临时 `TemplateLoader()`，收归后统一用注入的 `self.template_loader`——TemplateLoader 无实例语义（无参构造 + 磁盘扫描实例无关），内容零变化，仅实例身份与生命周期归 ctx（见 §2.3 第三条）。
- 依据：src 全仓 grep——`iter_*_templates` / 两个 dataclass / 两个 SUB_DIR / `relic_template_id` 除识别器与 config 模块自身外零消费方（含 devtools、MCP、backend、tools）；测试仓消费面见 §2.6。

### 2.6 测试迁移与修复

| 测试文件 | 动作 |
|---|---|
| `test_light_cone_list_recognizer.py::test_superimpose_templates_exist` | **重写**：`LightConeTplStore(TemplateLoader()).superimpose_tpls` 断言含 `'1'/'2'/'5'`——无 ctx、无 monkeypatch、无全局复位，四口径天然一致 |
| `test_light_cone_list_recognizer.py::_fake_ctx` | SimpleNamespace 增加 `light_cone_tpl_store` 字段（自建 store 实例注入） |
| `test_relic_list_recognizer.py::_fake_ctx` | 同上增加 `relic_tpl_store` 字段（现状靠 `getattr(ctx, 'relic_templates', None)` 动态挂缓存的副作用工作，收归后不补属性即 AttributeError） |
| `test_light_cone_owner_match.py` / `test_relic_owner_match.py` | `match_owner` 4 处调用补传 ctx（测试函数加 `test_context` fixture 参数） |
| `test/sr_od/config/test_light_cone_templates.py` / `test_relic_templates.py` | **迁移**为 `test/sr_od/application/cultivation/light_cone/test_light_cone_tpl_store.py` / `.../relic/test_relic_tpl_store.py`（文件镜像规范：src store 在域根，测试同域根）；断言契约不变——库 == 常量表集合、条目自洽、`relic_template_id` 公式锚；原文件退役（删除前做 src 指针对账） |

不加新 store 单测：幂等/实例隔离由「构造注入 + property 一行缓存」结构保证，属语言自带保证，不测（测试纪律「测试要少」）。

### 2.7 验收口径（终验）

- **直接判据**：重写后的 `test_superimpose_templates_exist` 单跑（单用例选择器直跑，冷路径）必过——自建 store 零全局依赖，冷路径执行是结构保证，直接钉死本案回归形态。
- **口径一致判据**：双口径（`-m "not slow"` 与全量）全量各跑一次，失败集合逐条 diff：**两口径失败集合一致**。
- **基线口径**：基线 = 3.1 开工前、当次工作区 HEAD 上双口径各跑一次的**新鲜失败清单**（各留档一份）；本节所列既有失败清单仅作漂移参考。判据 = 相对新鲜基线无新增失败文件。
- 既有失败参考清单（均与本迭代无关、确定性复现，不在本迭代修复范围。依据 = 迁移前双口径实测）：id_mark 参数化 32 条（[test_id_mark.py](sr-od-test/test/sr_od/screen_state/test_get_match_screen_name/test_id_mark.py)）；`test_fh_from_world`（[test_goto_treasures_lightward.py](sr-od-test/test/sr_od/application/treasures_lightward/operations/test_goto_treasures_lightward.py)，看门狗 60 轮超限）；`test_anchor_acheron_and_bailu`（[test_sr_character_details.py](sr-od-test/test/sr_od/mys/test_sr_character_details.py)）；`test_read_warp_status.py` 收集错误（导入 src 已改名退役的 `POOL_TYPE_STANDARD`，[read_warp_status.py](src/sr_od/application/cultivation/account/operations/read_warp_status.py) 现名 `POOL_TYPE_REGULAR`）。

### 2.8 关键取舍

1. **WeakKeyDictionary 按 loader 键控的全局**——能测试隔离，但仍是进程级全局：可发现性/生命周期/复位入口皆劣于 ctx 持有的类型化 service，放弃。
2. **归一化缓存下推公共包 TemplateLoader/TemplateMatcher**——24×24 灰度盘/SIFT 特征/直方图是 SR 业务语义，违反「SR 业务不污染公共框架」架构约定，放弃。
3. **recognizer 实例缓存**——生产侧 7 处调用点（5 文件）每次现建实例（[equip_light_cone.py:235](src/sr_od/application/cultivation/light_cone/operations/equip_light_cone.py)、[open_relic_replace.py:66](src/sr_od/application/cultivation/relic/operations/open_relic_replace.py)、[equip_relic.py:193/348](src/sr_od/application/cultivation/relic/operations/equip_relic.py)、[scan_relic_candidates.py:108/134](src/sr_od/application/cultivation/relic/operations/scan_relic_candidates.py)、[filter_relic_replace.py:170](src/sr_od/application/cultivation/relic/operations/filter_relic_replace.py)），实例缓存 = 每帧重载全库模板，性能回退，放弃。
4. **共享容器基类**——icons/feats/hists 形状同构可抽基类省约 40 行，但域自含哲学（cultivation README §2/§3）要求「一个域的改动不波及另一个域」，共享基类恰恰构成波及面；用户裁定①各域复制。
5. **iter 留 config 薄委托（初案）**——缓存职责与读盘校验同生命周期，拆 config/store 两处 = 两处漂移面；用户裁定③全收归 store，config 模块退役。
6. **SIFT/BFMatcher 留模块级**——无状态工具对象，不构成跨测试状态泄漏，不进 store 类（用户裁定②；「模块级」释义见 §2.2 构建纪律末条）。
