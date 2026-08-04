---
name: sr-od-dev-screen-onboarding
description: 当拿到一张待建档的游戏截图时用(画面建档 / screen_info area 维护 / 图标按钮模板建模;用 analyze_screen + upsert_screen_area)。英文:onboard a game screen, build screen_info areas, screenshot onboarding。
---

# 画面建档(analyze → 建档 → 建模)

拿到截图后按「客观识别 → 主观理解 → 建档 → 缺口分析 → 主动建模」推进,每步给判据。**先判建档规模**(单画面 vs 重 app,见下方「建档规模」节)。

## 守则(每步都守)
- **MCP 工具直调 + area 走 CRUD > 手编 yml**:用 `mcp__sr_od__analyze_screen` / `upsert_screen_area` / `delete_screen_area`,别写 HTTP 客户端脚本;area 改动经 `save_screen` 同步合并缓存,**禁止手编 screen_info yml 或手改模板目录**(手编不重算 `_od_merged.yml`,daemon 按旧缓存加载 → 找不到模板 / area)。
- **每张建档截图都要多模态 vision 看**:不只靠 MCP `analyze_screen` 的 OCR / area(OCR 看不见图形 / 布局 / 状态图标 / 模态性 / 朝向)。vision 失败必重试不跳过。
- **本 skill 只记建档方法论**:具体游戏知识(键位 / 流程 / 机制)归 doc(传送 / 键位见 `docs/game/screens/` 与 `docs/game/gameplay/`),不记具体键位 / 流程 / 机制。

## 建档规模:单画面 vs 重 app

**重 app 多子玩法**(1 app 调度多子 op、每子玩法独立画面 + `入口→子玩法→返回入口` 循环)→ 按 **app 维度**建档(不是逐画面零散):
1. **入口画面 + 各子玩法画面**各自建档(每画面独立 doc,或同 doc 多子态)。
2. **app 编排**(节点链 / 分支 / 入口循环)单独成 **develop doc**(`docs/develop/sr_od/application/<app>.md`),不进 screen doc。
3. **玩法机制**(目标 / 资源 / 循环)进 **gameplay doc** → 此时**触发 `sr-od-dev-gameplay-automation` skill 对游戏玩法进行建档**(不在本 skill 内直接写玩法,避免写成代码说明书)。
4. **跨画面 op 联动**(子 op 委托另一个 op,如缺料 → 跳补料):screen doc 记「跨画面流转入口」,develop doc 记编排。

判据:app 有 **≥3 子玩法、各独立画面** → 重 app 维度;单画面 / 独立 app 走下方 §1-§6 常规流程。

## 玩法画面:先搜攻略理解机制(再读代码 / 画面)

判据:画面属于**具体玩法**(有独立目标 / 资源 / 循环的 app,如周限 / 副本类)还是**通用流程**(大世界 / 菜单 / 任务 / 背包 / 战斗等基础 UI)。

- **玩法画面**:建档前先搜攻略 / wiki(`WebSearch` / web_reader)理解「这玩法是什么、目标 / 资源 / 循环、入口 / 走哪些画面」,再读 `application/<app>/` 代码 + `analyze_screen` 建档 —— 先有玩法理解,读代码 / 画面才高效,避免凭代码猜流程、漏画面。
- **通用流程**:直接走下方「信息源三层」+ analyze 建档,不必深搜。

玩法机制知识归 `docs/game/gameplay/`(本 skill 只记方法论,不记具体机制);重 app(多子玩法)触发 `sr-od-dev-gameplay-automation` skill 做玩法建档(见「建档规模」)。

## 信息源:理解画面三层并用
截图只覆盖「当前帧看得到」的;画面背后的结构信息要另外拉。建档前并读三层:
1. **截图** → `analyze_screen`(客观 area/OCR,第 1 步)+ vision(主观布局/状态图标,第 2 步)。
2. **screen_info**(`assets/game_data/screen_info/<screen_id>.yml` 的 `area_list`)→ 该画面**全部已建模元素**,含当前帧未显示的子态 area(如弹窗按钮)。每个 area 的 `text`/`template_id`/`pc_rect`/`goto_list`/`pc_alt`/`gamepad_key` 直接说明它是啥、点后跳哪、PC 端怎么点。**analyze 只返回当前帧命中的 area,screen_info 才是全集**。
3. **application/operation 代码**(`src/sr_od/application/<app_id>/`)→ `@operation_node` 链 = 画面跳转与状态流转;`round_by_find_and_click_area` / `round_by_goto_screen` 调用 = 在哪画面点哪 area。

**对齐判据**:doc 的「可交互元素」「状态流转」要与 screen_info `area_list` + 代码**逐条对齐** —— screen_info 有、doc 无 = 建档漏,补上。截图没显示的子态 area,先按 screen_info + 代码记入流转、标「待现场快照」(第 3 步子态处理)。

**版本迁移核对(老 app / 大版本更新后必查)**:信息源三层之一是代码,但**代码可能落后于游戏版本**,故需核对 —— 游戏版本更新会改画面 / UI / 流程(如 tab / 按钮 / 流程移除 → op 点已移除元素的代码失效成死代码)。判据:**建档前核对 op 代码假设的画面元素(tab / 按钮 / 流程)在当前游戏版本还在吗** —— 不假设「代码 = 当前游戏」。发现不符:① doc 记版本差异 + 标「代码与当前版本不符」;② 搜官方更新说明确认改动版本;③ app 层若有占位短路(如 `handle_xxx` 直返「未开启」)说明已知情,标「待重写」。代码默认有效是建档盲区。

## 截图获取:手动分解动作,不靠跑 app 中途
跑 app(`run_standalone_app`)/ 跑单个 op(`run_operation`)中途 `capture` **抓不到中间态** —— op 执行快、且会**自动消费中间画面**(如确认弹窗被 op 自己点掉),sleep 完再 capture 只能看到 op 跑完的结果(如落地入口),抓不到中间弹窗(如传送后的「自动进入交互」确认)。判据:**app/op 内部连续动作(transport→move→interact→drag→…→各弹窗)产生的画面,按 op 的 `@operation_node` 节点逻辑手动分解成单步** —— 读 op 代码,每步一个 `click_game` / `key_tap` / `drag` + `capture`,逐步截图(在 op 会自动点的弹窗处**停下、手动不点、先 capture**)。跑 app / run_operation 只用于「验证流程通」或「到位」,不用于抓中间态画面。

### transport 复现
- **transport 后角色朝向**:传送后角色朝向**继承传送前**(若传送前已在同一地图)。app 常假设 transport 后固定朝向来 `move_w`+`interact`;手动复现时,先传送去**别的地图**、再传送回目标地图,朝向即重置到默认。
- **补档先读 app/operation 代码 + move 距离一致**:手动复现前**先读 `src/sr_od/application/<app>/` 的 `@operation_node` 链**,弄清 transport→move→interact 的具体动作(`move_w` `press_time`?`turn_to_angle`?interact 哪个 NPC?),按 app 的距离 / 对象复现 —— 别只靠 vision 推朝向 / 距离。判据:**手动 `key_tap w` 的 `press_time` 要和 app 的 `move_w` 一致**(app 无 move 就**不走**,传送点已在交互范围);走多了反而错过交互点(角色过头,提示消失)。
- **Transport 失败排查**:`run_operation Transport` 失败(尤其「执行传送」节点卡 OCR 地图、重试到超时),常见根因是**目标传送点未解锁 = 该地图未探索**(新版本玩法 / 新城区需先跑图解锁传送点;其他地图同理)。判据:Transport 打开了地图但选不中目标点 → 先确认目标地图已探索、传送点已解锁,否则换已解锁的 app 建档。

### 操作时序
- **操作后等动画再 capture**(否则截过渡帧):底层 `click_game` / `key_tap` / `drag` **无内置等待**(等待在框架 operation round 层 `success_wait`,MCP 不经 round)。操作后画面/角色变化需 sleep 再 `capture`。关键 sleep 点:move 后等角色到位(不等就紧接 interact 会失效);interact(F)长按(`press_time>0`)非短按 tap。**sleep 建议值**:click ~1s / move ~1s / interact 1-2s / esc ~0.5s / drag ~0.5s。

### 边缘状态态(依赖游戏条件 → 人机协作)
很多状态态会话内**创造不了** —— 需游戏特定条件(到期 / 材料不足 / 持有上限 / 刷新出稀有)。判据:**状态态依赖「资源消耗 / 时间 / 随机」而非「导航可达」 → 标「待条件」**,别硬刷(随机态如稀有掉落刷了空跑;消耗态如材料不足在资源充足时不出现)。处理:① doc 标「待条件」+ 已拍的核心态先归档;② **请用户帮切**(用户能调游戏状态造条件,比智能体盲操作高效);③ 后续会话条件出现时补。

## 1. 客观识别:跑 `analyze_screen`
`analyze_screen(screenshot=<绝对路径 或 .debug/images 图名>)`,取三样:
- **匹配画面** `screens[].screen_name` + `is_precise`(精准 / 模糊 / 无匹配)。
- **匹配 area** `screens[].areas`(area_name / 类型 `text`|`template` / 文本或 `template_id` / conf / 位置)。
- **全量 OCR** `ocr_texts`(全部文字,含噪声/动态值)。area 维护的文字可能不全 → 全量 OCR 是权威文本源,与匹配 area 的文字**重叠属正常,勿去重**。

## 2. 主观理解:多模态 vision 看图(必需,不只靠 MCP)
**必须用多模态大模型 / 工具看图**(`analyze_image` / vision),**不能只靠 MCP `analyze_screen` 的 OCR / area** —— OCR 看不见:图形 / 图标按钮、布局结构、状态图标(选中态 / 已读 / 可领)、模态性(遮罩)、角色朝向 / 场景类型。**每张建档截图都要 vision 看一遍**(漏看会导致元素、画面边界或状态判断不完整)。vision 调用失败(如 400)**必须重试**(换图重传 / 重新 capture),不能跳过。

若用户给了**画面相关提示**,向 vision 提**偏向该类画面典型元素**的问题:
- 判据:提示指向某类画面 → 问该类的**典型可交互元素 + 状态文本**(而非泛泛「描述画面」);无提示 → 通用问布局 / 可交互元素 / 文字 / 图标 / 当前状态 / 模态性。
- 明确区分**可交互元素**(按钮 / 输入 / 图标)与**展示信息**。

**vision 状态推理不可信,只信客观描述**(踩坑固化):vision 不懂游戏 —— 它「描述画面有什么」(元素 / 文字 / 标记 / 颜色 / 位置 / 布局)**可信**,但「判断状态 / 作用」(已派遣 / 未派遣、按钮作用、是否可点)**不可信**(会基于看到的文字瞎猜)。prompt 要**客观描述**(「有哪些文字 / 按钮 / 图标?各自位置(x,y)?哪个元素有三角形 / 高亮 / 颜色标记?」),**别问状态推理**(❌「是已派遣还是未派遣?按钮干嘛?」);**状态判断结合代码自己做**(看 op 代码里的判定 area / 返回标志,如检测「提前收获」按钮 = 已派遣 / 检测 duration = 选时间预览,而非靠 vision 看「剩余时间」猜已派遣 —— 那个时间可能只是选时预览,不是进行中倒计时)。

**可交互对象判据(`>` 名字 `<`)**:星穹铁道 NPC / 交互对象进入可交互范围时,名字左右出现三角形标记,出现即在交互范围,`interact F` 即可(不需再走)。⚠️ OCR 常只识出名字漏了 `>` `<` 符号,vision 也不懂这约定 → 双双误判「没到,还要走」。判据:**画面出现 NPC 名字 + app 假设该位置可交互 → 直接试 `key_tap f`**,F 实际选中的对象看结果画面(F 提示文本未必是 F 实际交互对象);vision 提示词要明确「可交互对象名字左右有 `>` `<` 三角形,出现即已可交互,不要再走」。

**角色朝向/视角判据(vision 盲区)**:vision 对**朝向 / 视角**推断不可信 —— 不懂第 3 人称追尾语义(本游戏追尾视角下「看到角色背部 = 角色正对前方」,vision 会误判「背对」)。判据:**朝向以 OCR 交互提示(如「前往 XX」)+ 实际 interact 结果为最终判据**,别轻信 vision 的朝向推断。

## 3. 建档
先判:**独立画面**还是**已建档画面的子态**(模态/弹窗/状态,如对话框、loading/ready 子态)?
- **独立画面** → 新建 `docs/game/screens/<name>.md`(中文 `screen_name`;文件名英文 snake_case、不带冒号等特殊字符),登记进 `docs/game/screens/README.md` 索引(一行)。
- **子态** → 并进父画面 doc:「何时出现/状态流转」补该子态的**入口(从哪来)+ 出口(动作→下一态)**、「可交互元素」补该态元素、「识别快照」加该态子表;不另开文件、不登索引。

**建档文档 = 稳定的画面参考(事实),不是建档过程的日志**。描述类章节(何时出现/状态流转/识别特征/可交互元素/识别快照)只写**画面本身的事实**(长啥样/元素/识别/流转);建档/排查过程的产物不混入:
- **不进 doc**:① 测试结果(通过/失败 —— 测试归 `sr-od-test`,doc 不跟踪测试状态);② bug/修复历史(「原 bug...现已修」归 commit/PR,doc 只写现状)。
- **进「备注」并与事实分开**:开放问题(如某元素触发条件未知)、screen_info 现状缺口、易变点。
- **判据**:每句问「这是画面本身的事实,还是建档/排查过程的产物?」后者不进描述章节。

新画面 doc 结构:
- frontmatter:`screen_name` / `appears_in: [gameplay_name...]` / `last_updated`(核对日期)/ `source_image`(**归档后用测试仓相对路径 `screens/<screen>/<state>.webp`** —— 自描述可找,含 screen 目录无跨 screen 歧义;归档前可暂记 `.debug` 基线图名,**第 6 步归档后更新为完整路径,别留临时截图名 / 只写 state 名**)。
- **何时出现 + 状态流转**:出现条件 + 前后邻居;**多子态画面必须记状态流转**(每子态:入口 = 从哪来[动作/条件]、出口 = 动作→下一态),用表格或链式表达。
- **识别特征(稳定锚点)**:稳定文字 / 模板图标 / 固定图标;标注易变值(版本号 / 进度 / 公告)勿当特征。
- **可交互元素**:按钮 / 输入 / 图标;图形按钮注明「需模板/CV」。
- **识别快照** = ① 匹配画面(screen_name + is_precise);② 匹配 area 表(area_name / 类型 / 文本或 template_id / conf / 位置);③ 全量 OCR 文本。**多子态画面**的每子态快照用 `### N. 子态名(source_image)` 编号子标题(`## 识别快照` 下一级,符合 markdownlint MD001;加粗在多子态里不够显眼)。
- **备注 / 待查**(与事实分开标注):screen_info 现状(缺口 / 误匹配隐患)、开放问题(待查)、变更检测方法、易变点。**不写** bug/修复历史、不写测试状态(见上「建档文档 = 稳定参考」)。

## 3.5 screen_info 何时建 / 改 + id_mark 怎么定

**何时建 screen_info**(画面建档时按 bot 需要**增量**加 area,不是每屏都建):
- **检测要精准** → 加 **id_mark area**(画面独有稳定锚点)。框架 screen_info 匹配语义:某画面所有 `id_mark=True` 的 area **全命中 → `is_precise=True`**(精准匹配 + 早停);无 id_mark → 只按命中数模糊 top_n。
- **要点固定按钮 / 读固定区域 → 加 pc_rect area(固定坐标的单一真相源,通用规范)**。判据:**op 代码里出现硬编码 `Point(x,y)` / `Rect(...)` 去点 / 读某个固定 UI 元素(按钮、卡牌槽、选项卡、确认弹窗按钮)→ 该坐标必须进 screen_info 作 pc_rect area,op 经 `area_center(ctx, '<area_name>')` 读中心**,不能留魔法常量散在代码里。理由:screen_info 是坐标的**单一真相源**(可视化、可校验、跨 op 复用、改一处传导);魔法 `Point` 在代码里不可维护(无源、漂移无人知、多处重复硬编码易打架)。
  - **检测用 OCR ≠ 坐标可硬编码**:即使**检测**用 `round_by_ocr`(如检测"未达上限"),只要**点击目标不是 OCR 命中的文字本身**(如检测"未达上限"但点的是旁边的"确认"按钮、检测某对象但点的是第 N 张卡的卡底),**点击坐标就要进 screen_info**。只有「`round_by_ocr_and_click_area` 点的就是 OCR 命中的文字」(命中即给坐标)才不需单独建 area。
  - **area 命名**:用功能名(中文,如 `按钮-确认`、`事件卡-中`),别用坐标(如 `按钮-960x898`)。
- 增量:bot 用到哪个元素才加哪个 area,别一次堆全。

**id_mark 怎么定**(画面唯一标识,贵精不贵多):
- 选 **稳定**(每次必现)+ **画面独有**(别的画面不出现)+ **可靠检测**(OCR 高 conf / 模板高匹配)的 area,标 `id_mark=True`。
- 典型:画面独有按钮文字、独有模板图标。
- 数量:够唯一识别即可(通常 1-2 个),**别把所有 area 都标 id_mark**(要求全中才精准 → 易漏检)。
- 改 area 一律走 CRUD 工具(`upsert_screen_area`),别手编 yml(见「守则」)。

## 4. 缺口分析
对照「匹配 area」与「可交互元素 / 识别特征」:
- 命中且 conf 高 → 已建模。
- 模糊误匹配(`is_precise=False` 且命中无关 area)→ 记隐患(screen_info 该收紧 / 加精准特征)。
- 无匹配(`screens=[]`)→ 先想**兜底画面**(loading / 对话 等通用画面,无固定文字特征但结构固定):截图符合兜底结构(loading 黑屏 + lore tip / 对话下方对话框 + `好感度标题` area)→ 按兜底画面识别 + 建档(不必精准 screen 匹配);否则 screen_info 缺口,画面未收录。
- 可交互元素无对应 area → 进第 5 步建模。

## 5. 主动建模:图形 / 图标按钮(何时截模板 + 怎么截)

**何时截模板 / 识别方式决策**(对每个 bot 要识别 / 交互的元素,按性质选):
> **大原则:优先"建档时一次识别 → 存 screen_info → 自动化复用固定坐标 / 模板";运行时动态识别(CV / vision)只用于真的运行时变化的元素。** 固定 UI(按钮 / 槽位 / 区域)一次测准存 screen_info 即可,别每轮重检测。

1. **有稳定文字** → OCR(不截模板);文字独有且作画面锚点 → 设 `id_mark`(OCR area)。
2. **固定图形(图标按钮 / 状态指示 / 徽章),每次长得一样** → **截模板**(template match);该图形独有 → 可作 id_mark 模板。状态指示(radio 选中/未选中、下拉 ▽/△、勾选框)→ **每态一个模板**(如 ▽ 收起 / △ 展开)+ 高阈值(0.9)区分。
3. **变化的多实例(角色立绘 / 头像 / 商店牌)** → **模板库 + 特征匹配(SIFT)**,非单模板(逐角色截**同来源**立绘建库;脸近景 ≠ 半身,来源不一 conf 崩)。**模板库来源优先游戏内图鉴**(完整立绘 + 名 + 数据,canonical;如图鉴 / 教学目录 / 攻略大全),非从游戏画面裁(部分 / 变 / 缺名);图鉴需解锁先找解锁途径。**图鉴未解锁项**(暗色 / 阴影 /「未解锁」文字 / 不显示)要跳过,只采已解锁(亮)项 —— 锁定项需先解锁或从别的源(米游社)补;采模板时按"有规范名 + 已解锁"过滤。⚠️ **采全(通用经验)**:建库 / 采集要**穷尽所有实例**(滚动 / 翻页 / 切分类),别只取首屏样本就停 —— 否则库残缺,运行时遇未采实例就识别不了。**判据:新一屏去重后 0 新增 = 采全**;没到判据就继续翻。同样适用于**游戏数据采集**(全角色 / 全装备 / 全羁绊,别采样)。
4. **要计数 / 定位(槽位数 / 头像位置)** → 多为**建档时一次 CV 检测**(轮廓 / 颜色阈值 / HoughCircles),把结果(坐标 / 计数)**存 screen_info**(pc_rect),自动化用固定坐标 —— **很少需运行时动态 CV**(仅布局运行时真变化才动态,如槽位数随状态变)。
5. **稀有 / 多类多实例(杂乱场景目标)** → YOLO。

> 坐标怎么找见 skill `sr-od-dev-ui-region-detect`(稀疏独特找 vision、密集网格投影找 CV、带框图标/卡牌阵列找形状轮廓 CV、文字找 OCR)。注:从图鉴裁卡牌立绘建模板库时(本节情形 3),用形状轮廓法自动定位卡牌,别硬编码坐标(单图推断易截断)。

文字按钮 OCR 多已覆盖,无需此步。**图形 / 图标按钮**(OCR 看不见)按下面流程。**状态指示图标**(radio 选中/未选中、下拉 ▽/△、勾选框)同属此类 —— OCR 读不准状态,用**每态一个模板**(如 ▽ 收起 / △ 展开)+ 适高阈值(如 0.9)区分状态。
1. **定位**:圆形 → `cv2.HoughCircles`(扫 param2 / 半径,取稳定命中数);其它形状 → 轮廓 + 圆度 `4πA/P² > 0.7` 或颜色阈值。两法互相印证。
2. **裁模板**:用项目 `TemplateInfo` 生成(结构对齐既有模板:`raw.png` + `mask.png` + `config.yml`,`template_shape: circle` / `auto_mask: true` / `point_list: [圆心, 边缘点]`)。⚠️ `screen_image` 必须用**原始截图**(PNG / 未压缩),不要用 webp 归档版(lossy → 小区域裁剪放大 artifacts → 模板 conf 降)。
3. **入 screen_info**:`upsert_screen_area(screen_name, area_name, pc_rect=[x1,y1,x2,y2], template_sub_dir, template_id, ...)`。area_name 用功能名(中文),template_id 用英文 snake_case;`pc_rect` = 模板 bbox **每边 +10px** 再**夹到画面边界**(`max(0,·)` / `min(1920,·)` / `min(1080,·)`,贴边时余量自动收窄;项目编辑器约定「稍微比模板大一点」),防匹配大小/位移偏差;且不重叠邻接按钮。
4. **回验**:再跑 `analyze_screen`,确认新 area 命中、conf 高。

## 6. 归档代表截图
onboarding 的画面都要归档一张代表截图(多子态画面每子态一张)到测试仓 `screens/<screen_name>/<state>.webp`,供后续测试 fixture + 文档溯源。

**测试可用性**(归档 webp = mock 测试 fixture,见 `docs/develop/testing/`):截图要让 mock 测试能稳定用 ——
- **稳定态**(非过渡/动画帧):操作后 sleep 等动画完再截(底层 click/key_tap/drag 无内置等待,截过渡帧 → mock 不稳定)。
- **覆盖该 screen 关键 area**:测试断言依赖的 id_mark / 文字 area 要在帧内 + 命中(截完用 `analyze_screen` 回验目标 area 命中再归档)。
- **多子态每态一张**:测不同分支(如游历的收获 / 派遣、入口的自动托管中 / 关闭)。
- **文件名 = 可读 state**:fixture 引用(如 `游历-派遣中.webp`,非截图时间戳)。
- **写 mock 断言前先读 node 返回类型**(踩坑固化):`round_success` / `round_by_find_area` 命中判 `is_success`;`round_wait` / `round_retry` 判 `status`(匹配词)—— 先读 node 代码确认返回类型再写断言,别照搬别的 app(不同 app 主态返不同 `OperationRoundResult` 类型)。详见 `docs/develop/testing/`。

**格式 + 路径**:webp q90(**有损压缩**,但整屏 OCR / 模板匹配实测**识别无损效**;省空间)/ 1080p 原生不缩放(同 screen_info 坐标)/ 文件名用可读 state 名(如 `ready.webp`)/ screen_name 含冒号用下划线(如 `警告_游戏前详阅`)。⚠️ webp 归档版**不能当模板裁剪源**(小区域裁剪放大 artifacts → conf 降),模板裁剪用原 PNG(见第 5 步)。⚠️ **路径是 `sr-od-test/screens/<screen_name>/<state>.webp`**(测试仓**根** `screens/`,**非** `test/screens/` —— mock 测试从测试仓根 `screens/` 加载 fixture)。归档到 `test/screens/` → mock 测试找不到 fixture。

**doc 不写具体 webp 数**(如「22 张」)—— 建档频繁加截图,数字易过时不一致(README / doc / screen 数处打架)。写「实拍归档(测试仓 `screens/<name>/`)」即可。

**归档后更新 doc `source_image`**:归档完把 frontmatter + 各子态标题的 `source_image` 改成测试仓相对路径 `screens/<screen>/<state>.webp`(自描述可找,含 screen 目录)—— 不用临时截图名(`.debug/screenshot_xxx.png` 会被清)、也不只写 state 名(无 screen 目录、跨 screen 同名歧义)。

**转换**:**用本 skill 目录的 `convert_to_webp.py`**(`python skills/sr-od-dev-screen-onboarding/convert_to_webp.py <图片.png | 目录>`,单张或目录批量),**不要手写转换逻辑**(易重复造轮子 + 漏 Windows 中文路径坑)。webp q90,保留原 PNG 作模板裁剪源;底层 `cv2.imencode` + `ndarray.tofile`(**非 `cv2.imwrite`** —— Windows 中文路径会挂)。skill 自带工具属自包含资源,可在 SKILL.md 直接引用。

**覆盖检查(防断测试,踩坑固化)**:归档时若目标 `screens/<screen>/<state>.webp` **会被覆盖**(已存在)/ 要删旧图,**覆盖前先查该图是否被测试 fixture 引用** —— 测试靠归档图做 mock 输入,覆盖/删了会让 fixture 内容变(断言失配)或文件没(测试找不到)。
- **判据**:覆盖/删/重命名 webp 前,查测试仓里加载该 screen 归档图的位置(测试代码读 fixture 的调用 —— **具体 API 不在此固化,易变**);无引用 → 可覆盖/删;有引用 → 用**不同 state 名**区分(多态同 screen 各一张),旧图确需替换则先改测试引用。

## 收尾判据
- 改动经工具(MCP 直调 > 脚本;CRUD > 手编 yml);稳定特征 > 易变值;图形按钮 CV/模板 > OCR。
- 模板改名 / 加 area 涉及多文件(目录、config、yml、合并缓存)→ 一律经工具或同步合并缓存,别只改一处。
- 每张建档截图都过了 vision;信息源三层对齐;doc 只写画面事实。
