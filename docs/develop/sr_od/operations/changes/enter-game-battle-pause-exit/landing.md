# 进入游戏恢复战斗退出链 落地

## 完成前常规检查(各阶段完成判据引用本节,不复述)

- `uv run ruff check` 对本阶段改动文件全部通过;
- 本阶段直接受影响测试全量一次通过(`uv run pytest sr-od-test/test/sr_od/operations/ -m "not slow"` 相关子集);
- 测试仓(sr-od-test,独立 git 仓)同步改动随本阶段提交;
- 提交:逐文件点名 `git add`(禁 `-A`/目录级),commit message 含阶段号;提交后 `git show --stat` 复核入库面 = 申报面。
- 检查项来源 = 项目 AGENTS.md「测试规范」「提交流程与协作边界」节。

## 3.1 确认弹窗建档与回验

**范围**:经 MCP CRUD 工具新建屏「战斗-退出确认弹窗」(area:标识-提示 id_mark / 按钮-确认 id_mark,pc_rect 依据设计 §2.3 与 AS 弹窗实测帧 `screenshot_20261116_120047_412159.png`);`analyze_screen(screenshot=fixture)` 回验三帧互不误配;归档 fixture `sr-od-test/screens/战斗-退出确认弹窗/末日幻影形态.webp`;写 doc `docs/game/screens/battle_exit_confirm.md` 并登记 README 索引。边界:不含代码改动。
**设计依据**:design.md §2.3 分支B、§2.1 系统级变化表
**文件面**:`assets/game_data/screen_info`(仅经 MCP 工具)、`sr-od-test/screens/战斗-退出确认弹窗/`、`docs/game/screens/battle_exit_confirm.md`、`docs/game/screens/README.md`
**依赖**:无(「战斗-暂停面板」档已由探索期落地)
**优先级建议**:1
**完成判据**:
- 暂停面板帧命中「战斗-暂停面板」is_precise、不命中「战斗-退出确认弹窗」;弹窗帧反之(design §2.4 第 2 条)
- 完成前常规检查(本文首节;测试仓 fixture 变更随阶段提交)
**验收凭据形式**:analyze_screen 画面对照输出

## 3.2 EnterGame 三分支实现

**范围**:`enter_game.py` `check_screen` 按设计 §2.3 加三分支(插入位置:大世界角色图标判断后、未知兜底计数前;分支序:确认弹窗→暂停面板→结算页)+ 模块级常量 `BATTLE_SETTLE_PAGE_WORD`。边界:不动既有登录/交互/大世界分支与未知兜底三道闸;不动 HTTP/GUI。
**设计依据**:design.md §2.3(分支识别/动作/出口逐条)、§2.1
**文件面**:`src/sr_od/operations/enter_game/enter_game.py`
**依赖**:3.1(识别依赖「战斗-退出确认弹窗」档存在)
**优先级建议**:2
**完成判据**:
- 三分支行为与 design §2.3 一致(识别→动作→出口;round_retry 带 status 与显式 wait)
- describe_operation_flow 无新增 error 级诊断;节点图原路由不变
- 完成前常规检查(本文首节)
**验收凭据形式**:代码 review + describe_operation_flow 输出

## 3.3 mock 测试

**范围**:`sr-od-test/test/sr_od/operations/`(镜像规范文件,如 `test_enter_game.py` 若已存在则扩充)加分支路由测试:①暂停面板帧→命中分支A、点击落退出位 area 中心、round_retry 带 status;②确认弹窗帧→分支B 双锚命中、点击落确认按钮;③结算页帧→分支C、「退出」文字中心点击;④大世界帧/普通登录帧→不触发新分支、原路由成功;⑤弹窗+面板同帧(弹窗盖面板)→B 优先于 A(不重复点退出位)。fixture 从探索存证挑进测试仓。
**设计依据**:design.md §2.4 第 1 条、§2.3
**文件面**:`sr-od-test/test/sr_od/operations/`、`sr-od-test/screens/战斗-暂停面板/`(已有)、`sr-od-test/screens/战斗-退出确认弹窗/`
**依赖**:3.2
**优先级建议**:3
**完成判据**:
- 上述 5 类用例全绿;测试零真实副作用(落盘仅 tmp_path)
- 完成前常规检查(本文首节)
**验收凭据形式**:pytest 测试名清单 + 全绿输出

## 3.4 实机回归验证

**范围**:重启 MCP server(载新码)后实机跑 `EnterGame`(游戏在大世界/选关等正常态)验证正常路径不误触发、登录成功不回归;经 MCP `analyze_screen` 对三张 fixture 帧离线复核识别结论。边界:不做真实杀进程恢复场景(mock+离线帧已覆盖,design §2.4)。
**设计依据**:design.md §2.4 第 3 条
**文件面**:无代码改动(验证阶段)
**依赖**:3.3
**优先级建议**:4
**完成判据**:
- EnterGame 实机单跑成功收敛到大世界;新分支零误触发
- 完成前常规检查(本文首节;无文件变更则只验证不提交)
**验收凭据形式**:run 返回 success 状态 + 日志段

## 末阶段:正本更新

**范围**:按「正本更新清单」逐条更新正本
**设计依据**:本文件「正本更新清单」节
**文件面**:清单所列正本文档
**依赖**:全部落地阶段
**优先级建议**:0
**完成判据**:清单清零;正本与实现一致
**验收凭据形式**:文档对照 review

## 正本更新清单

- `docs/game/screens/battle_pause.md`:「备注」节 CW 形态行 ← 3.1/3.2(补充 EnterGame 兜底对 CW 形态的有界失败语义)
- `docs/game/screens/enter_game.md`:恢复链画面族(暂停面板/确认弹窗/结算页)与三分支语义 ← 3.2
- `docs/game/screens/README.md`:战斗-退出确认弹窗行(3.1 已建,复核描述与实现一致)
