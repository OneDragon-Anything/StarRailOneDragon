# 测试体系(sr-od-test)

> 测试仓 `sr-od-test/` 独立维护(主 repo `.gitignore`),需 clone 到仓库根,IDE 设为 Test Sources Root。本文记录 SR 的测试模式与基础设施。

## 两类 op 测试

### 1. 单步 area 测试(SrTestBase,unittest 风格)

测某个 op 在**单张截图**上的 `round_by_find_area` 行为。适合验证 area 定位 / OCR 命中。

- 基类:`test/__init__.py` 的 `SrTestBase`(`MockController` + 每个 test 自建 `SrContext`)。
- fixture:测试同目录 `.png`(`get_test_image('x.png')`)。
- 范例:`test/sr_od/operations/enter_game/test_enter_game/test_enter_game.py`(测同意按钮 old/new_login)。

### 2. fixture-driven op 流程测试(端到端,从 ZZZ 同步)

测 op **完整 `execute()` 节点流转** —— 跑过多帧画面,验证到达预期 terminal + 关键 click 发生。适合验证 op 的多节点状态机(登录流程 / app 编排)。

- 基础设施(从 `zzz-od-test` 同步、SrContext 适配):
  - `test/conftest.py`:`MockController`(覆盖 `click`/`get_screenshot`)+ `SrTestContext`(`load_screen` 从 `screens/<name>/<state>.webp` 读存档、`has_screen`/`mock_screen`)+ `test_context` session fixture(复用 ctx,快)。
  - `test/harness/fixture_controller.py`:`FixtureController`(反应式假游戏:phases 剧本 + `on_click_in`/`on_polls`/`on_action` 推进 + `recorded_clicks`/`recorded_inputs`)+ `WatchdogOperationMixin`(覆盖 `_execute_one_round` 计总轮次,防 WAIT 段死循环)+ `enter_running_state`/`reset_running_state`(运行态前置 + 清 event_bus)。
- 核心思想:构造 phases 剧本(每 phase 一张存档截图 + exit 条件)→ op 的 `screenshot()` 返回当前 phase 帧 → op `click` 落在声明 area 内即推进 → 验证 op 跑完 `execute()` 到达 terminal。
- 范例:`test/sr_od/operations/enter_game/test_enter_game_flow.py`(EnterGame 点击进入 → 大世界 happy-path)。

## 怎么写 flow 测试

1. **采 fixture**:`screens/<screen_name>/<state>.webp`(webp q90,1080p 原生不缩放),每个 phase 一张。用 `skills/od-dev-screen-onboarding/convert_to_webp.py` 转换。
2. **构造 phases 剧本**:
   ```python
   [
       {'frame': (screen_name, state), 'exit': ('on_click_in', screen_name, area_name)},
       {'frame': (screen_name, state), 'exit': ('on_polls', n)},  # 游戏自动流转,n 次 screenshot 后推进
       {'frame': (terminal_screen, state)},  # terminal,无 exit
   ]
   ```
   - `on_click_in (screen, area)`:click 落在 area 的 `pc_rect` 内才推进(流程 click)。
   - `on_click_in ([x1,y1,x2,y2])`:显式坐标矩形。
   - `on_action`:任意 click/input 推进(仅无恢复 click 的 phase)。
   - `on_polls n`:screenshot 调用 n 次后推进(游戏自动流转的中间态)。
3. **跑 op + 断言**:`_WatchedOp(WatchdogOperationMixin, Op)` + `op._init_watchdog()` + `enter_running_state(ctx)` + `op.execute()`(包 try/finally `reset_running_state`)+ 断言 `result.success` / `click_hit_area(screen, area)` / `phase_idx` 到末。
4. **缺 fixture 时 skip**:开头 `has_screen` 检查 → `pytest.skip`(采到 fixture 后自动恢复运行,无需改代码)。
5. **隔离**:`fixture_controller` fixture 用 `monkeypatch.setattr` 替换 `ctx.controller`(不污染 session 级 `test_context`)。

## 何时用哪类

| | 单步(SrTestBase) | 流程(fixture-driven) |
|---|---|---|
| 验证 | 单 area 命中 / OCR | 多节点状态机 / 端到端 |
| 成本 | 低(一张图) | 中(多张图 + 剧本) |
| 适合 | area 定位回归 | 登录 / app 流程 |

两类并存:单步快验证 area,流程验完整 op。新 op(有状态机)优先补流程测试。

## 从 ZZZ 同步

fixture-driven 框架源自 `zzz-od-test`(SR/ZZZ 共享 `one_dragon` 框架,测试基础设施同构)。同步遵循 `docs/develop/one_dragon/common-package-sync.md`,适配点:

- `ZContext` → `SrContext`;`ctx.init()` → SR 分步(`init_by_config` + `load_instance_config` + `ocr.init_model`,对齐 `SrTestBase`)。
- `MockController` 适配 SR controller 接口;`keyboard_controller`/`btn_controller`/`game_win`(属 `SrPcController`,非 `ControllerBase`)在 `FixtureController` 补 stub。
- ZZZ 的 `EnterGame` 状态机复杂(资源下载 / 多次进入点击 / B服 / 国际服),SR 简单,phases 按 SR op 节点链设计(见范例)。

## 跑测试

```shell
PYTHONPATH=src uv run python -m pytest sr-od-test/ -v
PYTHONPATH=src uv run python -m pytest sr-od-test/test/sr_od/operations/enter_game/ -v  # 单目录
```
