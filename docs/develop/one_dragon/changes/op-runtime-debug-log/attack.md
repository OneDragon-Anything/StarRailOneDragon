# op-runtime-debug-log 对抗审查报告

## 结论：需修订后定稿

方向成立、源码功夫扎实：设计引用的全部行号与函数签名逐一核实为真（见各攻击点内证据），8 个日志点选位覆盖了 op 一轮执行流的主要决策环节，全 debug 级别 + 不混重构的边界自律合理。但存在 1 个程序性致命点（§2.3 开放问题实际已有现成答案，且规范禁止带开放问题定稿）与 5 个重要实质性缺陷（binary 系方案空洞、接口配套漏最高频调用方、A1/A2 落位未定义、H1 的 FAIL 语义未定义、量级未评估），实现者在 3.1/3.2 至少六处必须自行拍板——不满足「实现者无需再设计」的定稿门槛。修订量不大（补定义与调研，不动方案骨架），修完可定稿。

## 攻击点清单

### A1: §2.3 开放问题已有现成答案——is_debug 本就是日志级别开关，「落地前闭合」是把设计期调研外包给落地
- 位置：design.md §2.3、§2.5；landing.md 3.3；源码 `src/one_dragon/base/operation/one_dragon_context.py:269`、`src/one_dragon/utils/log_utils.py:448-459`、`src/one_dragon/envs/env_config.py:349-362`
- 攻击：§2.3 承认 is_debug 语义「未核实」并将其列为设计期开放问题、推迟到落地 3.3 闭合。实际源码已给出完整答案：`one_dragon_context.py:269` 在 `init()` 中执行 `log_utils.set_log_level(logging.DEBUG if self.env_config.is_debug else logging.INFO)`——is_debug 与日志级别**已经联动**，且 `log_utils.set_log_level`（448-459）同时设置 logger 与全部 handler，机制成熟；is_debug 有完整的落盘属性（env_config.py:349-362）。该项调研 grep 5 分钟可完成，属设计期工作。后果链：① 规范（iteration-design.md §6）明确「『带开放问题的定稿』不存在」——此问题不闭合本案停在草案，而闭合它根本不需要落地阶段；② §2.5 取舍「全 debug 级……代价是实测期需要确认级别开启方式」的前提失真——开关已存在，代价趋零；③ landing 3.3 的主体工作（「核实语义/无级别切换则补最小开关」）已坍缩，剩余价值只有「核实 MCP server 启动链路是否必经 context.init()」与写实测指引；④ 3.3 文件面「日志配置相关源码（核实后定）」是条件式文件面，违反 landing 七件套中「文件面=本阶段允许动的文件」的可派工性。
- 建议：定稿前在本审查已给出的答案基础上闭合 §2.3：写明「is_debug→set_log_level(DEBUG) 已联动（one_dragon_context.py:269），实测开启 = 配置 is_debug=true 后经 init() 生效」，并将 3.3 重定义为「核实 MCP server 启动是否经过 init() 链路 + skill 实测章操作指引 + ZZZ 同步」，文件面随之落定。

### A2: binary 系（find_area_binary / find_area_in_screen_binary）日志方案语义空洞；「两套并行实现」论断错误——实为三套
- 位置：design.md §2.1 B（接口配套、已知技术债）、§2.4；landing.md 3.1 范围与判据；源码 `screen_utils.py:66-92`（find_area_binary）、`95-148`（find_area_in_screen_binary）、`151-192`（find_area_in_screen）、`242-302`（find_and_click_area）
- 攻击：三处失实/空洞。① 调用关系错误：§2.1 B 接口配套称既有调用方「find_area / find_area_binary / 其他直接调用者透传」screen_name 给 find_area_in_screen——但 `find_area_binary`（66-92）调用的是 `find_area_in_screen_binary`（92 行），**根本不经过 find_area_in_screen**，「透传」无处发生。② 论断错误：「已知技术债」称 find_area_in_screen 与 find_and_click_area 是「两套并行重复实现（OCR 匹配 + 模板匹配逻辑各写一遍）」——漏了 `find_area_in_screen_binary`（95-148），它自带第三份 OCR+模板匹配实现；技术债清单失真会误导后续重构迭代的范围申报。③ 格式未定义：§2.4 说「find_area_binary 同构日志」但 §2.1 B 从未定义 binary 系的日志格式——B1 同构？B1a 同构？加在 find_area_binary 入口还是 find_area_in_screen_binary 匹配循环？landing 3.1 判据「每个日志点按 design.md §2.1 格式落位」对 binary 系指向空洞，该判据不可验收。另外 cw_observation.py:1974/1984 自行二值化后直接调 find_area_in_screen——binary 路径也有绕过入口的调用方，同构日志的覆盖边界更模糊。
- 建议：§2.1 B 补一小节 binary 系日志定义（建议：find_area_in_screen_binary 内加 B1a 同构详情行，格式与 B1a 完全一致；入口 find_area_binary 加 B1 同构行）；「已知技术债」改为三套并列（find_area_in_screen / find_and_click_area / find_area_in_screen_binary），为将来抽公共识别函数的重构留准确底账。

### A3: is_target_screen 是 find_area_in_screen 最高频调用方，却不在 screen_name 透传清单——画面判定路径的 B1a 全部退化为无画面上下文，恰好废掉 A2 的排查目标
- 位置：design.md §2.1 B 接口配套；源码 `screen_utils.py:479-488`（is_target_screen 的 id_mark 循环）、`350-448`（get_match_screen_name / from_last）
- 攻击：find_area_in_screen 的直接调用方共四处（grep 实证）：find_area 入口（63）、is_target_screen（484）、tl_as_team_recognizer.py:79/92、cw_observation.py:1974/1984。设计的接口配套只考虑了入口透传（find_area），is_target_screen 被归入「其余不传不受影响」——但它恰恰持有 screen_info（475、484 行），**明明可以传 screen_info.screen_name**。后果：画面判定（get_match_screen_name→is_target_screen→find_area_in_screen）每一次 id_mark 匹配都走 screen_name=None 退化路径，B1a 只打裸 area_name；而 area_name 跨画面不唯一（167 个画面的 area 各自命名，无全局唯一约束），排查「画面判定为什么没判成」时，A2 给出的试过画面名单与 B1a 的退化行**无法对上号**——本迭代的第一目标（§0「画面判定黑盒」）在自家最关键的路径上没有拿到完整证据链。这不是兼容性问题（不传确实不报错），是设计目标的自伤：加参数的动机就是给 B1a 补画面上下文，却放过了最需要上下文的调用方。
- 建议：is_target_screen 透传 screen_info.screen_name 给 find_area_in_screen（475 行 screen_info / 473 行 screen_name 均可得）；§2.1 B 的调用方清单改为枚举式（点名四处调用方各自的传参决定），替代现在的「其他直接调用者」一笔带过。

### A4: A1/A2 日志点的落位与「候选数/试过名单」口径未定义——get_match_screen_name 的真实结构比设计假设复杂
- 位置：design.md §2.1 A；源码 `screen_utils.py:368-379`（三分支）、`384-448`（get_match_screen_name_from_last：BFS 403-439、scope 跳过 417-426、补漏循环 441-446）
- 攻击：设计把 A1/A2 当作「get_match_screen_name 返回前」一个打点位可实现。实际该函数三分支：限定列表（368-373，命中即提前 return）、委托 from_last（374-375）、全量 active（376-379）；而 BFS 模式的候选信息全部在**子函数 from_last 内部**——bfs_list 从 current/last 起点展开（403-406）、scope 模式下非活跃画面跳过判定只展开邻居（417-426）、最后还有 bfs_list 之外的补漏循环（441-446）。实现者面对的选择设计均未回答：① 「候选 N」在限定列表模式 =「列表长度」——第 2 个就命中时后面 3 个根本没判定，报总数还是实际判定数？BFS 模式 =「实际展开判定过的画面数」——scope 跳过的画面不跑 is_target_screen，算「判定过」吗？两种模式口径已经不一致。② 「试过名单」需要收集 bfs 判定序 + 补漏循环的 active 画面，数据在子函数内——是改 from_last 返回值透传，还是在子函数内打点（那 A1 就不是「get_match_screen_name 返回前」一条了）？③ A2 只裁「前 10」，但 BFS 补漏循环的画面不在 bfs_list 序里，前 10 的取法未定义。④ 耗时（X.XXs）要覆盖子函数，计时起点在父函数——跨函数传递也未说。
- 建议：§2.1 A 补落位定义：明确「在 from_last 内记录判定序与计数、经返回值/参数聚合后在 get_match_screen_name 统一打点」的具体机制（或直接改从 from_last 打 A1/A2、父函数限定列表分支单独打），并统一定义「候选/试过」= 实际调用过 is_target_screen 的画面（scope 跳过与提前命中未判定的不计），写明两种模式的口径差。

### A5: H1 的「FAIL 存图」语义与量级未定义——FAIL 在本框架是控制流，不是异常
- 位置：design.md §2.1 H；landing.md 3.2 判据；源码 `operation.py:474`（retry 耗尽转 FAIL）、`487-497`（终态消费）、`544-582`（_get_next_node 按 success/fail 分流出边）、`562`
- 攻击：_get_next_node（562 行 `edge.success != (result == SUCCESS)`）显示 FAIL 有出边时 op 继续跑——round_fail 是节点间的正常分支手段（如 fail→else 兜底转移），并非都意味着事故。设计 H1 只说「主循环 round_result 转 FAIL 处 save_screenshot()」，未回答：① 落在哪一处？474（retry 耗尽转换）与 487-497（op 终结）语义不同——474 转换后节点可能仍有 fail 出边继续执行，此时存图是节点级证据；487 是 op 终结。两处都存？只存终结？② 量级：fail 作常规转移的 op（一次一条龙中不少见）每轮 FAIL 都落一张图 + 一条日志，实测期磁盘量与「FAIL=出了事」的暗示效应未评估；③ save_screenshot 有 prefix 参数（658），H1 未定前缀（默认类名——同类多节点 FAIL 无法区分）。landing 3.2 判据「FAIL 存图各日志点按 §2.1 格式落位」因此不可验收。
- 建议：明确定义：建议仅在「op 终结为 FAIL」处存图（487-497 块），节点级 fail→转移不存（转移本身有 432 行 INFO 与 D2/D3 尾缀可查；真要节点级证据可限定 retry 耗尽转 FAIL 的 474 处），并定义 prefix（如 f'{类名}_fail_{节点名}'）；§2.1 H 写明量级预估与取舍。

### A6: B1a 日志量级未评估——167 个建档画面下画面判定路径的详情行可达万级
- 位置：design.md §2.1 B1a、§2.5 取舍三；源码 `screen_utils.py:479-488`（id_mark 循环）、`assets/game_data/screen_info/`（实测 167 个 yml，不含 merged）
- 攻击：§2.5 的量级论证只有一句「未命中时同一区域可能出两条（入口结果 + 详情过程）——接受冗余」，算的是单区域，没算总量。实际链路：get_match_screen_name 无历史记录或 BFS 模式下逐画面 is_target_screen，每画面每个 id_mark area 调一次 find_area_in_screen → 每次一条 B1a（未命中画面首个 id_mark 即断，约 1-2 条/画面）。167 个建档画面、goto 图连通分量占大半时，**单次全量判定最坏 100-300 条 B1a**；一个实测时段含数十至数百次画面判定（每轮 check_and_update + until 验证 + goto），debug 期日志总量轻松过万行。「grep 友好优先」的主张在万级行下需要结构性对策支撑（如 B1a 仅画面判定失败时输出该画面全部 id_mark 明细、或按 (画面,轮次) 聚合），设计没有这笔账。debug 级别确实挡住了正常运行，但「实测期可读性」正是本迭代的交付物本身。
- 建议：§2.5 补量级预估（按 167 画面 × id_mark 均值 × 判定频次给出数量级），并择一：接受万行（写明 grep 模式建议）；或 B1a 在 is_target_screen 路径默认静默、仅 A2 触发时回放该次判定的 id_mark 明细。

### A7: 治本核验——overlay 遥测体系已存在，D2 与 _emit_overlay_round_perf 功能重叠，「与既有观测通道的关系」零论证
- 位置：design.md §1（「中间环节全黑盒」）、§2.1 D2、§2.5（三条取舍均未提 overlay）；源码 `operation.py:433`（_emit_overlay_round_trace 节点流转）、`459/696`（_emit_overlay_timeline）、`466`（_emit_overlay_round_perf 轮次耗时毫秒）
- 攻击：框架在主循环已有成体系的运行时事件通道：节点流转明细（433 round_trace）、异常与 op 完成事件（459/696 timeline）、**每轮耗时**（466 round_perf，与 D2 数据同源同口径）。§1 的现状描述「框架日志只有链路两端……中间环节全黑盒」就日志文件成立，就可观测性整体不成立——「从未承担运行时可观测职责」的根因归层（§1）过重，忽略了自己身边已有的半个观测体系。D2（轮次耗时入 INFO 行）与 _emit_overlay_round_perf 是同一数据的第二个出口，设计未提后者存在、未做「为什么不用/不扩 overlay 通道」的取舍。治本层面：本案不是纯症状修法（8 点选位本身合理、日志持久可 grep 是 overlay 不具备的能力），但「log 与 overlay 双通道各自为政、缺统一运行事件模型」这层更深的根未触及——下一次再要观测点，仍会在两套通道间重复建设（D2 已经是第一例）。
- 建议：§1 现状补 overlay 体系一段；§2.5 补第四条取舍「log.debug vs 扩展 overlay 事件通道」（互补边界：overlay=实时浮层不落盘、log=持久可 grep；D2 借 round_perf 同源数据）；「统一运行事件模型」作为长期方向登记（可入正本更新清单的技术债指针，不必本迭代做）。

### A8: D2/D3「尾缀追加不改语义」是未核实的乐观主张；D3 计数口径未定义
- 位置：design.md §2.1 D、§1「不改 INFO 存量语义」；源码 `operation.py:432`（INFO 行）、`469-476`（retry 递增发生在打日志之后）
- 攻击：① 「不改语义」的前提是无消费者解析该行文本。设计未标注任何核实依据（硬规则 1：无依据必攻）。本审查代查：节点通知走 round_result 对象（485 send_node_notify）、overlay 走对象字段（433-437），grep「返回状态」未见文本解析消费方——主张**大概率成立**，但这应当是设计期查证并就地标注的事实，而非审查者代劳。② D3 口径：432 行打日志发生在 469-470 node_retry_times 递增**之前**，RETRY 轮显示的 retry=N 是递增前值（首次 retry 显示 0）还是 +1 后值？实现者必须拍板，设计未定义。
- 建议：§2.1 D 补一句消费方核实结论（对象通道、无文本解析）；D3 明确计数口径（建议显示递增后值，即本节点第 N 次重试）。

### A9: C1 的「逐锚各一条」未定义 break 语义——两种 until 的锚覆盖集不同
- 位置：design.md §2.1 C；源码 `operation.py:977-989`（until_find_all 首个未中即 break）、`994-1006`（until_not_find_all 首个命中即 break）
- 攻击：until_find_all 循环遇第一个未命中即 break（987-989）——break 之后的锚**根本没有被验证**，无日志；日志读者会把「无该锚日志」误读为「该锚已验证且出现/未出现」吗？until_not_find_all 相反：首个命中即 break（1004-1006），只有全部未中才走完循环。两种 until 下「逐锚各一条」实际覆盖的锚集与顺序都不同，「总结论一条」也未定义打点位（991-992 return 前？1011 继续点击前？）。属可实现但语义需拍板的空洞。
- 建议：§2.1 C 补：逐锚行仅覆盖实际验证过的锚（break 即止），总结论行打在 return/继续点击之前，写明 until_find_all 与 until_not_find_all 两式的行序示例各一条。

### A10: 决策链覆盖缺口——screen_loader 画面状态转移（update_current_screen_name）全程无日志
- 位置：design.md §0/§2.1（8 点清单）；源码 `operation.py:1470`（goto 判定后更新）、`1483`（goto 跳转后乐观更新）、`1497`（点击后乐观取 goto_list[0] 更新）、`1524`（check_and_update 更新）；`screen_utils.py:403-406`（current/last 作为 BFS 起点）
- 攻击：按「op 一轮执行流」走查 8 个日志点的覆盖：点击后 1497 行的乐观更新（取 area.goto_list[0]，无任何验证）直接改写 screen_loader 的 current_screen_name，而它是下一次 BFS 判定的起点（from_last 403-406）——「为什么这次判定从错误画面展开搜索」的答案藏在这类状态转移里，A1 只报判定结果、不报起点从哪来。goto 路径同理（1470/1483）。这是 8 点清单之外的真实黑盒环节，与 §0「完整决策链」的目标有缺口。
- 建议：增补一个 debug 点（update_current_screen_name 调用处或 screen_loader.update_current_screen_name 内统一打 `画面状态: <旧>→<新> (来源: 判定/点击乐观/goto跳转)`），成本极低（一处函数内打点覆盖全部四个调用位）。

### A11: 判据引用的测试面为空集——「直接受影响测试全量通过」无信息量，新增行为无可执行断言
- 位置：landing.md 3.1/3.2 完成判据、首节常规检查；`sr-od-test/`（实测：无 screen_utils 测试文件；operation 仅 test_operation_registry.py，与主循环无关）
- 攻击：本迭代改动两个核心文件，但 sr-od-test 中不存在覆盖 screen_utils 识别链路或 operation 主循环/until 循环的既有测试——「本阶段直接受影响测试全量一次通过」实际是空集通过，验收凭据「测试全量通过输出」不携带信息。新增的日志行为（含 find_area_in_screen 参数退化、行为零变化承诺）没有一条可执行断言，全部依赖「日志样例对照」人工验收。设计未申报这一现状，也未决定是否借 fixture_controller 补最小断言（如 B1a 在 mock 画面下触发 caplog 断言）。
- 建议：landing 3.1/3.2 判据中如实标注测试面现状；至少为「行为零变化」补一条烟囱断言（现有 fixture_controller 可驱动 find_area 路径），或显式声明「纯日志行为以人工样例对照验收、不加测试」的取舍。

### A12: design §0 状态与 README 进度失同步
- 位置：design.md §0「状态：草案」；README.md「迭代设计:对抗审中」；规范 iteration-design.md §5 硬规则 4（全量同步复查）
- 攻击：README 进度已写「对抗审中」，design §0 状态仍为「草案」。规范（§6）明确状态由总纲 §0 表达，两处应同步流转。轻微，但硬规则 4 的卡点就是防这种局部改动后的残留。
- 建议：对抗审启动时同步 §0 为「对抗审中」（或收敛后直接「定稿」）。

### A13: 个别主张缺就地依据标注
- 位置：design.md §1（read_warp_status 例子）
- 攻击：§1 称「read_warp_status 读数后即一条未打」但未标路径，读者无法按图索骥。本审查代为核实：`src/sr_od/application/cultivation/account/operations/read_warp_status.py` read_status 节点（181-221 行）读数仅入 data、round_success 不落日志——**主张属实**，但按硬规则 1（依据就地标注）应写明出处。另 §2.1 A 引用 goto 内重复 debug 的格式串写作 `'当前识别画面 %s'`，源码 1473 行实为 f-string（`log.debug(f'当前识别画面 {current_screen_name}')`）——引文与原文有微小出入，不影响结论。
- 建议：补路径标注；引文按原文。

## 定稿试读结果

以实现者身份逐阶段走查「凭这份能开工吗」：

- **3.1 screen_utils 识别层（A/B 组）**：**不能直接开工**。三处必须自行拍板：① binary 系日志加在哪、什么格式（A2——§2.1 无定义）；② is_target_screen 传不传 screen_name（A3——不传则画面判定路径全退化，传则超出设计书面范围）；③ A1/A2 打点位与候选口径（A4——需自行改 from_last 签名或打点位，属设计决策）。find_area/B1/B1a/B2 主路径可开工。
- **3.2 operation 运行层（C/D/F/H 组）**：**C1/F2/D2 可开工**；D3 需拍计数口径（A8）、C1 需拍 break 语义（A9）、H1 需拍插入点与 prefix（A5）——三处设计未答。
- **3.3 debug 开启方式闭合**：**阶段内容已失真**（A1）——级别开关已存在（is_debug→set_log_level），「核实语义/补开关」大半坍缩；按现状执行该阶段，实现者会发现设计前提错误而触发停手令回提修订。应先修订阶段定义再派工。
- **末阶段正本更新**：可用。清单两条均为条件式（「若存在……核实后定」），核实成本低，可接受；但按 A7 建议补 overlay 关系后清单应增加对应正本条目。

综合：修订集中在 §2.1（A2/A3/A4/A5/A9 补定义）、§2.3（A1 闭合）、§2.5（A6/A7 补论证）与 landing 3.1/3.3 判据同步——均为补定义与调研性质，不动 8 点方案骨架。修订完成后可定稿。
