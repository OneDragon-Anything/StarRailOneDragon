# MCP 适配器

> 把 `SrBackendContext`（见 [architecture.md](architecture.md)）以 **MCP** 暴露给 MCP 客户端（AI 编码工具等）。MCP 是两个并行适配器之一，另一个是 HTTP（见 [http.md](http.md)）；两者共享同一 backend。

## 工具

34 个 `@mcp.tool`，多数委托一个 backend 方法；自定义 op 工具另走 `operation_registry` + `run_slot._start`：

| MCP tool | 委托 | 返回 |
|---|---|---|
| `check_game_window` | `backend.check_window()` | `WindowStatus`（结构化 JSON；backend 抛错时返 `{'error': ...}`） |
| `capture_game_screen` | `backend.capture()` | `{success, path}`（截图落盘 `.debug/sr_od_mcp/screenshot/`，`path` 为绝对路径） |
| `analyze_screen(screenshot=None, save_image=False)` | `backend.analyze()` | `AnalyzeScreenResult`（结构化 JSON；实时 + `save_image=True` 多回传 `screenshot_path`；success 时带 `vision_hint` 能力边界提示；精准命中画面若注册了额外识别器,多回传 `extras` 该画面的结构化领域事实 + 平级 `extras_doc` 字段说明,见 [screen-recognizers.md](screen-recognizers.md)） |
| `upsert_screen_area(screen_name, area_name, pc_rect, ...)` | `backend.upsert_screen_area()` | `{success, action(inserted/updated), area_count, error}`（写 yml + reload） |
| `delete_screen_area(screen_name, area_name)` | `backend.delete_screen_area()` | `{success, action(deleted), area_count, error}`（写 yml + reload） |
| `open_game(enter=True, block=True)` | `backend.start_run('mcp', op_factory)`（`enter=False`→`OpenGame`，`enter=True`→`OpenAndEnterGame`） | `block=True`：终态 `{success, result}`；`block=False`：受理 `{started: True, ...}`；并发拒绝 `{started: False, error, source, hint}` |
| `click_game(x, y, press_time=0.1, pc_alt=False)` | `backend.click_game()` | `{success, x, y, in_window, pc_alt}`（坐标不在窗口内 → `in_window=False`；`pc_alt=True` 大世界等锁光标画面点击前需按 Alt 解锁） |
| `input_text(text, use_clipboard=None)` | `backend.input_text()` | `{success, method, masked_text}`（`use_clipboard=None` 跟 `game_config.type_input_way`） |
| `key_tap(key, press_time=0)` | `backend.key_tap()` | `{success, key, press_time}`（框架键名 `w`/`a`/`s`/`d`/`f`/`esc`/`space`；`press_time>0` 长按） |
| `drag(x1, y1, x2, y2, duration=1)` | `backend.drag()` | `{success, x1, y1, x2, y2, duration}`（`(x1,y1)→(x2,y2)` 1080p 游戏坐标拖拽，覆盖刮刮卡 / 收集来回拖等） |
| `list_applications` | `backend.list_applications()` | 当前实例可运行应用、独立应用列表和当前选中项（只读，不刷新配置） |
| `run_one_dragon(block=False)` | `backend.run_one_dragon('mcp')` | 默认立刻返回受理 `{started: True, ...}`；`block=True` 等结束返终态 `{success, result}` |
| `run_standalone_app(app_id=None, block=False)` | `backend.run_standalone_app('mcp', app_id)` | `app_id=None` 时使用 GUI「应用运行」当前选中项；返回形态同 `run_one_dragon` |
| `list_operations` | `operation_registry.scan_operations(ctx)` | 可运行自定义 op 列表（`op_id` + 参数 schema，纯反射不实例化） |
| `describe_operation(op_id)` | `operation_registry.describe_operation(ctx, op_id)` | 单个 op 参数 schema（每个参数标 `json_serializable` + `coercible` + 整体 `debuggable`） |
| `run_operation(op_id, args=None, block=False)` | `operation_registry` 校验 + 反序列化 + `run_slot._start`（op 路径） | 默认立刻返回受理；`block=True` 返终态 `{success, result}`；非 Operation / 缺参 / 不支持的数据类 / 并发拒绝返 `{started: False, error}`。`@dataclass`+`from_dict` 参数可从 dict 传入 |
| `get_config(app_id, key=None)` | `config_router` 路由 → 各 config 领域方法 | `{success, app_id, data|key,value}`（读配置字段/全 data；只读） |
| `set_config(app_id, key, value)` | `config_router` 路由 → 写穿 ctx + 校验只读 | `{success, app_id, key, value}`（写简单/enum 字段；只读字段拒绝） |
| `add_config_item(app_id, list_field, item_dict, idx=None)` | `config_router` 路由 → `item_from_dict` + 校验 + add | `{success, app_id, list_field, id}`（增改列表项，`idx` 控制有序列表插入位置；写入前校验） |
| `delete_config_item(app_id, list_field, item_id)` | `config_router` 路由 → delete | `{success, app_id, list_field, id}`（删列表项；可逆性低） |
| `update_config_item(app_id, list_field, item_id, item_dict)` | `config_router` 路由 → 按 item_id 原位替换 | `{success, app_id, list_field, id}`（全量补齐型列表改条目，顺序不变） |
| `describe_config(app_id, category=None)` | `config_router` 路由 → schema 组装 | `{success, set_fields, ro_fields, list_fields, ...}`（结构化 schema + add 示例；只读） |
| `list_app_configs()` | `config_router.all_entries()` | `{success, configs:[{app_id, description, supported_ops, item_kind, id_kind}]}`（可改配置目录；只读） |
| `get_run_status` | `backend.query_status()` | `RunStatusResult`（运行中返当前节点/重试；终态返结果/失败定位） |
| `stop_run` | `backend.stop()` | `{"stopped": bool, ...}`（仅表信号已发出，过渡期 `get_run_status` 仍显示 running） |
| `close_game` | `backend.close_game()` | `{success, result}`（信号已发，非已关闭；controller 吞异常，用 `check_game_window` 验证） |
| `list_mcp_usage_guides` | `mcp/prompts.py` | 可用操作指南目录，相当于帮助索引 |
| `get_mcp_usage_guide(name, app_id=None)` | `mcp/prompts.py` | 指定操作指南正文，相当于任务级 `--help` |
| `mys_login(username, password)` | `mys_tools.py` `MysAccessController` | 统一信封 `{status, message, data}`：`success` / `already_logged_in` / `verification_required`（含本地验证页 URL，人工过验后台自动续跑）/ `error`（-3208/-3235 即停）。⚠️ 知情声明（tool 描述含）：密码会作为工具参数传入大模型上下文，由使用者自行决定；成功仅落盘 cookie 会话（config/当前实例/mys/），密码不落盘 |
| `mys_logout()` | `mys_tools.py` | `{status: success}`（幂等；清 session.json 与 role.json、保留 device.json） |
| `mys_get_characters()` | `mys_tools.py` → `SrMysClient.get_characters()` | `success` + 崩铁角色数组（冻结字段集，含 element_cn/base_type_cn 中文名）／`session_expired`（提示重登，不清本机数据）／`error`（1034 → 专属文案） |
| `mys_get_roster_detail()` | `mys_tools.py` → `SrMysClient.get_characters_detail()` | `success` + 全角色明细数组（遗器六件套词条/位面饰品/星魂/行迹/属性面板，均中文名）／`session_expired`（提示重登，不清本机数据）／`error` |
| `mys_evaluate_relic_substats(criteria, roster_data?)` | `mys_tools.py` → `relic_eval_tools.evaluate()`（口径参数化纯计数，零 IO；roster_data 缺省自拉） | `success` + results/not_found/team_summary／`session_expired`/`verification_required`（自拉透传）／`error`（criteria 空或重名、roster_data 非法、1034 透传）。口径取自 sr-od-game-coach 角色档「有效口径」行，工具不内置默认口径 |
| `relic_lookup(query)` | `relic_tools.py` → `lookup_relic()`（直读 `sr_relic_sets` 常量，零 IO） | 统一信封：`success` + 套装静态定义（set_name/kind_cn/obtain/effects/pieces 含件名/部位/描述/图标相对路径）／`ambiguous`（模糊多命中，`candidates` 候选列表）／`not_found`。查询词按优先级：件名精确 → 套装全名 → 子串模糊。查账号穿戴数据走 `mys_get_roster_detail` |
| `cone_lookup(query, rarity=None, path_id=None, list_all=False, with_ascension=False)` | `light_cone_tools.py` → `lookup_light_cone()`（直读 `sr_light_cones` 常量，零 IO；`with_ascension=true` 另读 `light_cone_ascension_const`（BWIKI 逐光锥页生成，惊魂夜实机锚）+ `dungeon_drop_const` 反查） | 统一信封：`success` + 光锥静态定义（name/rarity/path_cn/obtain/skill 特效全文/icon 相对路径）；`with_ascension=true` 时单命中另附 `ascension` 晋阶材料块（分段需求 `stages`，段名「Y级」=突破段/「X～Y级」=经验段以稀薄以太计/满晋阶总量 `total`/材料→刷取副本反查 `dungeon_by_material` 分类级/`missions_by_material` 实例级/副本外途径 `extra_sources_by_material`；表未收录该光锥为 null）；`list_all=true` 按 rarity/path_id 过滤列全量（不带详情与 ascension）；`ambiguous` 候选列表／`not_found`。查询词：全名精确 → 子串模糊。查账号穿戴走 `mys_get_characters` |
| `character_lookup(query, rarity=None, path_cn=None, element_cn=None, list_all=False, with_ascension=False)` | `character_tools.py` → `lookup_character()`（直读 `character_const`+`sr_character_details` 常量，零 IO；`with_ascension=true` 另读 `character_ascension_const`/`dungeon_drop_const` 反查） | 统一信封：`success` + 角色静态基础信息（avatar_id/id/cn/path_cn/element_cn/rarity/technique_type/icon 相对路径），精确/模糊单命中另带 `traces`（行迹满级）与 `eidolons`（星魂全 6）；`with_ascension=true` 时另附 `ascension` 晋阶材料块（分段需求 `stages`/满晋阶总量 `total`/材料→刷取副本反查 `dungeon_by_material` 分类级（键=指南分类可路由导航）/`missions_by_material` 实例级（具体虚影·历战余响 boss·花萼区域，与指南 mission_name/region_name 同名对齐，可直接规划开拓力刷本）/副本外途径 `extra_sources_by_material`；表未收录该角色为 null，开拓者性别后缀由 `find_character_ascension` 归一化匹配）；`list_all=true` 按过滤列全量基础列表（不带 traces/eidolons/ascension）；`ambiguous` 候选列表／`not_found`。查询词：数字 id → 中文名/英文代号 → 子串模糊。查账号拥有与练度走 `mys_get_characters` |

要点：

- **返回契约（跨工具统一）**：成功标志键一律 `success`（bool）；运行类受理语义用 `started`（≠完成）；`stop_run` 的 `stopped` 表信号已发、`/health` 的 `ok` 表健康探测，是各自语义惯例。裸字符串 + `错误:` 前缀的返回已全部结构化（`capture_game_screen`/`close_game`/block 终态），调用方判错不再靠字符串匹配。
- `app.py` 放 MCP server 创建、基础 game tool 和总注册入口；`service_app.py` 放应用运行 tool 与自定义 op tool 工厂。
- backend 实例通过闭包注入 tool，不使用全局单例，也不让 FastMCP lifespan 管 backend 生命周期。
- `capture_game_screen` 落盘返回路径；`analyze_screen` 返回结构化 dataclass，由 FastMCP 序列化。
- `analyze_screen` 是 **OCR + 传统 OpenCV 模板/颜色匹配，非视觉大模型(VLM)**：只做已建档 screen_info 的客观命中，无视觉理解；tool docstring 已显式标注，防智能体把「分析」误解为「看懂画面」（要看懂 → 视觉大模型工具 / 视觉子 agent）。
- `analyze_screen(save_image=True)`（实时模式）把已截的内存图顺手存盘 + 回传 `screenshot_path`，供调用方喂 视觉大模型 double-check；默认 `false` 不落盘，离线模式忽略。
- `analyze_screen` 成功时返回 `vision_hint`：提醒本结果仅含 OCR + 模板匹配的部分识别，不等同完整视觉理解，需要全面判断画面时配合视觉工具 / 多模态再看（能力边界提示，[design-principles.md](design-principles.md) P14；防智能体把部分识别当画面全貌）。失败时为 `null`。
- `analyze_screen` 精准命中画面时返回 `extras`：若该画面注册了**额外识别器（recognizer）**,带该画面的结构化领域事实（画面特定结构,如货币战争备战画面的金币 / 阶段 / 阵营在场人数）;无注册识别器的画面为 `null`。识别器异常不中断本结果（`extras=null`,详见日志）。这是 per-screen 注册机制,新增画面识别器见 [screen-recognizers.md](screen-recognizers.md)。MCP 侧 dataclass 由 FastMCP 序列化、加字段自动生效;但 `analyze_screen` 的 **tool docstring 属 tool 描述变更,需客户端 `/mcp` 重连**智能体才能看到 `extras` 字段描述（字段本身不重连也在返回 JSON 里）。
- 所有运行（`open_game` / 一条龙 / 独立应用 / 自定义 op）经**同一个 `RunSlot`** 派发：op 路径（`open_game` / `run_operation`）槽自管 `start_running/execute/finish_running`（自然完成收尾不置停机中断一次性标志位），app 路径（`run_one_dragon` / `run_standalone_app`）委托 `run_application`（复用 GUI/CLI 共享入口）。`block=True` 用 `asyncio.wrap_future(future)` 阻塞 await 取结果，`block=False` 立刻返回已启动状态，后续用 `get_run_status` 查进度。
- `run_operation` 是**通用 operation 运行入口**（不框死为调试）：`op_id` 格式 `<dotted module path>.<ClassName>`（可从 `list_operations` 获取）；`args` 传构造参数,以 `cls(ctx, **args)` 烤进闭包——JSON 标量/列表/字典直接传;`@dataclass`+`from_dict` 参数传 dict,实例化前用 `coerce_dataclass_params` 自动反序列化;其余复杂数据类拒绝(提示走 application);先用 `describe_operation` 看参数 schema(`coercible=True` 的可传 dict)。SR 当前业务 op 暂无 `@dataclass`+`from_dict` 参数,该能力前置就绪。
- 配置修改工具（`get/set/add/delete/update_config_item` + `describe_config` + `list_app_configs`）按 `app_id` 路由到各 config 领域方法（`config_router.py`），写穿 ctx 缓存实例、写入前校验；已接入路由：`standalone_app` / `_group`（通用）、`trailblaze_power`（开拓力体力计划：`plan_list` 计划项增删 + `loop` 开关，`add` 的 `idx` 插入位置即一条龙执行顺位）与 `echo_of_war`（历战余响周本计划：列表由全部周本关卡全量补齐，不支持增删条目，用 `update_config_item` 按 `mission_id` 原位改挑战次数）。两者 `add/delete/update` 写穿当前实例缓存，下一次一条龙 run 立即生效无需重启；`mission_id` 格式「生存索引 {分类} {关卡} {区域}」，材料→关卡反查用 `dungeon_drop_const.find_missions_by_material`；后续接入同类 `@dataclass`+`from_dict` 配置时在 `config_router._build_routes` 补 `RouterEntry`（`add` 支持传 None = 该 config 不支持增条目，`update` 可选按 item_id 原位替换）。
- 配置刷新：app 路径在 `run_application` 前（槽线程内、`_start` 已赢锁后）刷新当前进程的 YAML 配置缓存，对齐 GUI 已保存设置；`list_applications` 与 `list_operations` 是只读路径，不刷新。
- `get_run_status` / `stop_run` 是统一入口：无论最近一次运行来自 op 路径还是 app 路径，都通过同一组工具查询和停止。
- 单进程内已有运行时会返回并发拒绝，避免同一个 backend 内重复操作游戏资源。
- MCP tool 不返回运行日志正文；客户端需要用 `get_run_status` 轮询是否完成，GUI 服务页负责展示日志。
- `close_game` / `click_game` / `key_tap` / `drag` / `input_text` 是独立同步操作，不走运行槽；`click_game` / `drag` 使用 1080p 游戏空间坐标。底层 click / key_tap / drag **无内置等待**，连续操作或 `capture` 前建议 sleep 等动画（见各 tool 描述的 ⚠️ 提醒）。
- `list_mcp_usage_guides` / `get_mcp_usage_guide` 把 prompt 模板以普通 tool 暴露，方便不会主动消费 MCP prompts 的客户端发现。
- `mys_*` 三工具走 `mys_tools.py` 的 `MysAccessController` 状态机（idle/awaiting_ticket，验证循环上限 3）；会话失效只打标记不清任何本机数据；凭据纪律与协议规格见 [mys.md](mys.md)（⚠️ `mys_login` 的密码经 LLM 上下文，工具描述含知情声明）。
- 理念：MCP 只做感知 / 操作，编码 / 调试交给 AI（[design-principles.md](design-principles.md)）。

## Instructions

`FastMCP(name, instructions=...)` 传 server 级 `instructions`，握手时返回；客户端**通常注入** system prompt（协议 Optional/MAY，Claude Code 会注入；非协议强制）。放两边共通的操作哲学（保持精炼）：工具分类（观察/操作）、操作三件套（`analyze_screen` → 操作 → 等 ~1s 后验）、实机约束（`pc_alt`）、出错查 log、安全边界。

## 引导内容三通道

引导内容分三条通道，分工互补（可见性均为客户端行为，非协议强制——spec 用 Optional/MAY）：

| 通道 | 智能体可见性 | 内容 |
|---|---|---|
| `instructions` | 客户端**通常注入** system prompt（协议 Optional/MAY；Claude Code 会） | 共通操作哲学（上节） |
| `prompts`（`@mcp.prompt()`） | 由客户端决定；Claude Code 是 slash 命令，智能体平时不自动看到 | 按场景剧本（见下） |
| help tool（`list_mcp_usage_guides` / `get_mcp_usage_guide`） | 通常可见（客户端一般暴露 tools） | 同 prompts 模板，给智能体 `--help` 入口 |

`prompts` 协议设计给人手动选，智能体平时不自动看到 → 同份模板再做成 tool 镜像补；但 tool 要智能体「想到去调」，故核心操作哲学放 `instructions`（通常注入，最贴近常驻）。guide item 带 `mode`（`user`/`dev`）：user 项（跑龙/独立应用）也有对应 prompt，dev 项（`sr_dev_validate_op`：op 实操验证 / 战斗 op 边界）只走 tool。模式差异不进 instructions（server 级全局、不支持运行时切；且两套会膨胀违背精炼）。

## Prompts

| MCP prompt | 用途 |
|---|---|
| `sr_check_status` | 引导 AI 查询运行状态、窗口状态与当前画面分析结果。 |
| `sr_run_one_dragon` | 引导 AI 按当前配置启动一条龙，并轮询 `get_run_status`。 |
| `sr_run_standalone_app(app_id=None)` | 引导 AI 列出应用、选择独立应用并启动运行。 |

要点：

- prompt 只描述调用顺序，不直接执行工具；实际执行仍由 MCP 客户端选择 tool。
- `sr_run_standalone_app` 支持传入 `app_id`，为空时提示使用 GUI「应用运行」当前选中项。
- 运行类 prompt 默认使用 `block=False` 启动，再轮询 `get_run_status`，便于客户端在长耗时任务中持续反馈状态。
- 部分 MCP 客户端不会主动展示 prompts；这时可让 agent 先调用 `list_mcp_usage_guides`，再调用 `get_mcp_usage_guide` 读取同一份模板。

## 传输与端口

- 传输：streamable-http。
- MCP 端点：`/mcp`。
- 默认本机端口：`24001`。
- MCP URL：`http://127.0.0.1:24001/mcp`。
- 健康检查：`http://127.0.0.1:24001/health`。

## 接入 MCP 客户端

主 server 是标准 streamable-http,任何 MCP 客户端都可挂载。
先通过 GUI「开发工具 -> MCP 服务」或命令行启动本机 server，再在你的 MCP 客户端新增服务器（按所用工具，见下）。

### DSH MCP 配置

项目根 `.dsh/mcp.servers.yml`（workspace-mcp 插件按 cwd 自动加载，保存热生效；不入库，每人本地建）：

```yaml
servers:
  sr_od:
    transport: streamable-http
    url: http://127.0.0.1:24001/mcp
```

### Claude Code MCP 配置

```shell
claude mcp add --transport http sr_od http://127.0.0.1:24001/mcp
```

### Codex GUI MCP 配置

| 字段 | 填写 |
|---|---|
| 名称 | `sr_od` |
| 类型 | `Streamable HTTP` |
| Bearer 令牌环境变量 | 留空 |
| URL | `http://127.0.0.1:24001/mcp` |
| 标头 | 留空；如果界面要求 JSON，填 `{}` |
| 启动命令 | 留空 |
| 参数 | 留空 |

要点：

- 当前服务只实现 streamable HTTP，不是 STDIO server；Codex 中不要选 STDIO。
- 本机接口默认无鉴权，因此不需要 Bearer token 或额外 headers。
- MCP 客户端只负责连接已启动的 HTTP MCP server；启动 / 停止 / 重启由 GUI「MCP 服务」页或命令行负责。
- 命令行启动可用 `uv run python -m sr_od.backend.entry.server --host 127.0.0.1 --port 24001`；如果项目根目录存在 `.env`，也可使用 `uv run --env-file .env python -m sr_od.backend.entry.server --host 127.0.0.1 --port 24001`。

## 开机自启(主 server)

主 server 可在登录后自动启动（Session 1 内直接拉起，**不经 daemon 派生**），与 [daemon 开机自启](remote-ssh.md#开机自启) 相互独立、可共存：

- 启动脚本：`tools/mcp/start_mcp_server.ps1`（默认 host 127.0.0.1 / port 24001，日志写 `.debug/sr_od_mcp/main_server.log`，与 GUI / daemon start tool 同路径）。
- 装自启快捷方式：`.\tools\mcp\create_mcp_server_startup_shortcut.ps1` —— 在 Startup 文件夹建 `SR OD MCP Server.lnk`，登录后自动调上面脚本（隐藏窗口）。卸载即删该 `.lnk`。
- 幂等说明：本快捷方式与 daemon 自启快捷方式各管各的；daemon 的 `start_sr_od_mcp_server` 先按命令行检测进程已存在则跳过，不会重复拉起 / 端口冲突。

## 路线图（尚未实现）

- 更多 game 感知 / 交互 tool：原 `identify_current_screen` → `analyze_screen`、`click_at_position` → `click_game`、`press_key` → `key_tap`、`drag_to` → `drag` 均已实现；后续按需补 `scroll` 等。
- 更完整的 AI 操作范式，例如失败恢复、实例切换与多步巡检。

## 相关文档

- [architecture.md](architecture.md) - backend 方法定义
- [http.md](http.md) - 并行的 HTTP 适配器
- [design-principles.md](design-principles.md) - MCP tool 设计规范
- [entry.md](entry.md) - 服务入口
