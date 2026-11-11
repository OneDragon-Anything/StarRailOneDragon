# 账户养成域包（cultivation）结构重构 落地

## 完成前常规检查（各阶段完成判据引用本节，不复述）

- `uv run ruff check` 对本阶段改动文件全部通过（只对本阶段修改的文件跑，不跑全 src）;
- 本阶段直接受影响测试全量一次通过（`uv run pytest sr-od-test/ -m "not slow"` 相关子集）;
- 测试仓（sr-od-test，独立 git 仓）同步改动随本阶段提交;
- 提交：逐文件点名 `git add`（禁 `-A`/目录级），commit message 含阶段号与任务 id；提交后 `git show --stat` 复核入库面 = 申报面;
- 迁移类阶段（§3.1/§3.2）：迁移优先 PyCharm 方法——`rename_refactoring` 语义更新 import（适用处）、`get_file_problems` 逐文件验证 unresolved reference 归零收口、`search_text` 兜底穷尽（AGENTS.local §5；用户指示 2026-11-11）;
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 批次A：域包骨架 + 纯搬移（账本 T-2）

**范围**：建 `src/sr_od/application/cultivation/<character|light_cone|relic>/operations/` 骨架；git mv 迁移 design.md §2.1 结构树所列 12 个现有文件（遗器 4 op、光锥 5 件 = 4 op + farm_material、角色 3 件 = 2 op + 1 识别器）；更新全部 import 指向新路径；`FarmLightConeMaterialOp` 类改名 `FarmLightConeMaterialOp`；测试仓镜像文件同步移动；game-coach 3 文档的 op_id 与裸类名引用同步（design.md §2.5 清单）；复验 op/recognizer 注册。
**边界**：不含识别器分家（§3.2）、不含新 op 实现（§3.3/3.4）、不改任何运行行为；`equip_list_recognizer`/`grid_template_locate`/`equip_owner_match` 本阶段原位不动（仅 import 指向更新）。
**设计依据**：design.md §2.1（结构树/留守清单）、§2.3（改名）、§2.5（影响面/迁移方法）。
**文件面**：`src/sr_od/application/cultivation/**`（新建）、`src/sr_od/operations/`（迁出 12 文件 + 消费方 import 更新）、`sr-od-test/test/sr_od/**`（镜像移动）、`skills/sr-od-game-coach/references/**`（op_id 同步）。
**依赖**：设计定稿（本迭代 T-1）。
**优先级建议**：8。
**完成判据**：
- 搬移为纯移动：`git diff` 对每个迁移文件仅路径与 import/类名变更，零逻辑改动（design.md §2.1）;
- 注册复验（离线可执行，不依赖游戏窗口）：
  ```powershell
  $env:PYTHONPATH="src"; uv run python -c "from sr_od.backend.operation_registry import scan_operations; r = scan_operations(None, refresh=True); print('\n'.join(sorted(o.op_id for o in r.operations if 'cultivation' in o.op_id)))"
  ```
  输出须含全部迁移动作的新 op_id（scan_operations 的 ctx 参数为占位，`None` 可传；依据：operation_registry 纯反射实现，对抗审 A1 核验）;
- recognizer 注册复验：`from sr_od.backend.screen_recognizer_scan import scan_recognizers; r = scan_recognizers(None, refresh=True)` 后，`r.failures` 不含遗器/光锥/角色详情三识别器相关条目，registry 含「遗器-替换」「光锥-替换」「角色-详情」三个 screen 名;
- game-coach 文档同步归零（双 grep 均归零，design.md §2.5）：
  ```powershell
  Select-String -Path "skills/sr-od-game-coach/references/**/*.md" -Pattern 'sr_od\.operations\.(equip_|farm_|upgrade_|select_bag_|open_|superimpose_)'
  Select-String -Path "skills/sr-od-game-coach/references/basics/新手与日常决策.md" -Pattern 'FarmMaterialOp'
  ```
  （第一条覆盖旧 op_id 前缀，第二条覆盖改名类的裸类名引用——单靠第一条会假绿，对抗审 A2）;
- 完成前常规检查（本文首节）。
**验收凭据形式**：`git show --stat` 移动对账 + list_operations 扫描输出 + 测试全绿记录 + 文档 grep 归零记录。

## 3.2 批次B：识别器分家（账本 T-3）

**范围**：`equip_list_recognizer.py` 拆为 `light_cone/light_cone_list_recognizer.py` 与 `relic/relic_list_recognizer.py` 两份自含实现（定位/识别/角标/兜底全内联，两域零 import，design.md §2.2）；`grid_template_locate.py`、`equip_owner_match.py` 内全部可复用函数两域各复制一份（design.md §2.2 写死的复制口径）后原文件删除；`LightConeReplaceRecognizer`/`RelicReplaceRecognizer` 类名保持（screen_name 不变，识别器注册兼容）；消费方（equip_light_cone/equip_relic/open_relic_replace）改引新位置；**隐性连带**（对抗审 A6）：`test_equip_relic.py` L30-33 / `test_equip_light_cone.py` L37-40 直接 import `grid_template_locate` 的 `load_template_gray`/`locate_cells_by_votes`，随域改引各自识别器模块内同名函数；`equip_relic.py` L4 与 `equip_light_cone.py` L57/L211 注释中提及的 grid_template_locate 路径同步改指新位置；测试镜像拆分（test_equip_list_recognizer 拆两域、test_equip_owner_match 按光锥组 48 用例/遗器组 33 用例拆两文件）。
**边界**：行为锁定——识别逻辑/阈值/标定值逐行保持现值，禁止顺手调参；兜底策略重做归 §3.5；光锥侧兜底不动。
**设计依据**：design.md §2.2（分家口径/复制边界/测试拆分）、§2.1（退役清单）、§2.6 取舍三。
**文件面**：`src/sr_od/application/cultivation/{light_cone,relic}/**`、`src/sr_od/operations/{equip_list_recognizer,grid_template_locate,equip_owner_match}.py`（删除）、消费方 op 文件（import 与注释）、`sr-od-test/test/sr_od/**`（镜像拆分 + 两测试文件的 grid 依赖改引）。
**依赖**：§3.1。
**优先级建议**：6。
**完成判据**：
- 两域识别器文件互不 import（grep 验证 `from sr_od.application.cultivation.<对方域>` 零命中）、不 import `sr_od.operations` 残留模块（design.md §2.2 零共用）;
- 退役三文件删除后全仓 grep 消费方归零;
- 现有识别/owner 测试用例拆分迁移后全量绿（行为锁定，不允许删用例——确属跨域重复用例拆归各自域）;
- 完成前常规检查（本文首节）。
**验收凭据形式**：grep 归零记录 + 测试全绿记录 + 拆分前后用例计数对账。

## 3.3 新 op：角色突破缺料刷取（账本 T-4）

**范围**：实机摸底角色晋阶画面缺料栏形态（槽位数/缺料判定/获取途径弹窗与光锥线同构性，按 od-dev-screen-onboarding 建档）→ 实现 `FarmCharacterAscensionMaterialOp`（起点=角色晋阶画面，流程形态参照光锥线：缺料格→弹窗→途径跳转→UseTrailblazePower 委托）。
**边界**：不改动光锥线 op；通用材料补全/快速刷取不在本 op（那是升级 op 的 auto_farm/fill_generic 既有能力）。
**设计依据**：design.md §2.3。
**文件面**：`src/sr_od/application/cultivation/character/**`、`assets/game_data/screen_info/**`（摸底建档）、`sr-od-test/test/sr_od/application/cultivation/character/**`。
**依赖**：§3.1；cond = 实机窗（摸底前置，复查 = 下次开游戏实机窗，与遗器验证族攒批同窗）。
**优先级建议**：4。
**完成判据**：
- 角色晋阶缺料栏画面建档 + 实机样本锚;
- op `run_operation` 实机跑通一次跳转刷取（真实开拓力消耗须用户同意）;
- 完成前常规检查（本文首节）。
**验收凭据形式**：run_operation 实机 SUCCESS 记录 + 画面建档 fixture。

## 3.4 新 op：行迹缺料刷取（账本 T-5）

**范围**：实机摸底行迹画面缺料形态（与 §3.3 同窗）→ 实现 `FarmTraceMaterialOp`（起点=行迹画面）。
**边界**：同 §3.3；行迹多技能各自缺口不在本 op（入口按当前打开技能）。
**设计依据**：design.md §2.3。
**文件面**：同 §3.3（character 域）。
**依赖**：§3.1；cond = 实机窗（与 §3.3 同窗摸底）。
**优先级建议**：4。
**完成判据**：同 §3.3 口径（行迹画面锚）。
**验收凭据形式**：run_operation 实机 SUCCESS 记录 + 画面建档 fixture。

## 3.5 遗器兜底识别根治（账本 T-6，承接原遗器批 T-19）

**范围**：在 §3.2 分家后的 `relic_list_recognizer.py` 上根治兜底漏检错认——三路线选型（低置信门槛/失败卡重试标记/卡面图像哈希对照，依据原遗器批 T-19 登记方向）先离线样本诊断（现场截图 `screenshot_20261111_020229_129273.png` + 怪盗假面错认样本）定路线，再实现。
**边界**：只动遗器域识别器兜底路径；光锥域不跟随；整屏主匹配路径不动。
**设计依据**：design.md §2.2（兜底独立演进）、§2.6 取舍三。
**文件面**：`src/sr_od/application/cultivation/relic/relic_list_recognizer.py`、其测试。
**依赖**：§3.2；cond = 实机窗（实机验收段，与遗器验证族攒批同窗）。
**优先级建议**：5。
**完成判据**：
- 快枪手野穗毡帽类卡实机识别正确（继承原遗器批 T-19 criteria ①）;
- EquipRelicOp 实机找到穿着中目标件（criteria ②）;
- 离线样本回归：怪盗假面不再错认翔鹰头盔;
- 完成前常规检查（本文首节）。
**验收凭据形式**：实机 run SUCCESS 记录 + 离线样本回归测试。

## 末阶段：正本更新（账本 T-7）

**范围**：按「正本更新清单」逐条更新正本。
**设计依据**：本文件「正本更新清单」节。
**文件面**：清单所列正本文档。
**依赖**：§3.1、§3.2（实机批 §3.3/§3.4/§3.5 **不阻塞**本阶段——正本内容只涉结构与口径，与实机批交付无耦合；账本 T-7 deps=[T-2,T-3] 与此口径一致，对抗审 A7）。
**优先级建议**：0。
**完成判据**：清单清零；正本与实现一致。
**验收凭据形式**：文档对照 review。

## 正本更新清单

- `docs/develop/sr_od/application/cultivation/` 正本区（域设计文档：域结构/识别器自含口径/材料三线接口契约/**域归位组织约定**——后续域（如 tl_* 归位）照此办理的通用约定，对抗审 A8）← 批次A/批次B 落地后从 design.md 正本化;
- `AGENTS.md` §1.1 目录结构树 ← 批次A（加 cultivation 行）;
- `docs/game/screens/光锥-替换.md` L4 识别器路径死链 ← 批次B 导致（对抗审 A3）;
- `docs/game/screens/遗器-排序规则.md` L54 equip_relic.py 路径死链 ← 批次A 导致（对抗审 A3）;
- `docs/game/screens/遗器-替换.md` L56/L61 equip_owner_match 与 test_equip_owner_match 路径死链 ← 批次B 导致（对抗审 A3）;
- `skills/sr-od-game-coach/references/mechanics/relic-enhancement.md` §5「与光锥养成的机制差异」若引用共用识别器实现细节 ← 批次B;
- `.debug/temp/TODO.md` 遗器相关条目中的 operations 路径引用（如 SelectBagRelicOp 条）← 批次A（随路径变更顺手核对）。
