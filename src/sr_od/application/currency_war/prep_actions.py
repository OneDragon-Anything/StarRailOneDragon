"""货币战争 备战决策环 执行器 + 出战发出链(P1;strategy/03 §13)。

**住址申报**:本模块 = 出战域执行臂——备战原子动作执行器(PrepActionExecutor
runner 包络)与出战发出链(``launch_battle_unified`` 统一执行器 +
``launch_prepared_battle`` 发出核 + ``locked_resume_sync_and_battle`` resume
面封装 + ``_battle_chain_deploy_moves`` 计划装配件)同居;发出链消费方 =
画面 op armed 面(CwScreenPrep)与 loop resume 面(CwLoop)。
**防线边界申报**:执行前守卫现役 = drag 类浮层守卫(``prep_drag_overlay_gate``,
拦截错误画面上的机械拖拽)+ 出战前置席满守卫(``guard_bench_overflow_for_battle``,
告警横幅在场时先卖一个备战席角色腾位再放行出战——席满态出战会被游戏静默
忽略)+ 出战前团队规模超限守卫(``guard_team_size_over_cap_for_battle``,
「X/Y」双帧确认占用 > 上限时**不发点击**带受阻码交回外循环——超限态出战
同样被游戏静默忽略;解除〔撤/卖场上单位或升上限〕归策略侧,守卫零策略
语义),非动作后判效——动作落地判定仍归观察侧
reconcile 对账,与「机械执行、不含玩法判断」申报不抵。出战链两道执行前
防线(屏态复验/浮层闸门)已退役(2026-11-19 用户裁定)——
错屏/浮层下的误发出由阶段一身份分发(每帧)+ drag 浮层守卫 + 调用方
retry 网承接。

框架层:本模块**不含玩法判断**(何时收晶矿/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_screen),
只负责「机械执行一个动作」(用户裁定:动作 op 只管机械执行,
禁止做任何验证——点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧
reconcile 对账;执行回执 ``(progressed, detail)`` 已停用,
``execute`` 无返回,发出即职责完成)。失败路径(修订):
- 参数非法 → 对应动作 op 内守卫断言 AssertionError(集中式 validate
  已退役进各 op,flow/action_ops.md §1 决策侧参数现算契约;异常上抛
  通道 = 执行异常同款);
- 执行前输入契约拒绝(晶矿/箱/按钮等目标不在,执行前观察,M6 边界面)→
  本动作未发出,机械部分完成后返回主循环重观察重决策;
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。

slot 语义(unified-action-factory 统一后):席位域动作(CwActionSellBenchParam/
CwActionSellDeployedParam/CwActionMoveUnitParam)携**状态容器槽位表下标**(0 基,词表单一源 =
kernel/cw_vocab,坐标系裁定见其模块头)。执行坐标边:MoveUnit 已随其
参数面迁移批改 op 自持(op 内经模块级原语现读点位表——bench 侧 =
备战栏-N area 序直取;deployed 侧 = 下标→(排,排内槽号)固定双射内联
算术,0-3=前排 1-4 / 4+=后排 1-N 动态,后排拖点按 back_slot_count 布局
档静态解析);SellBench 已随其参数面迁移批改 op 自持(bench 侧 =
备战栏-N area 序直取);SellDeployed 已随其参数面迁移批改 op 自持
(deployed 侧 = 下标→(排,排内槽号)固定双射内联算术,0-3=前排 1-4 /
4+=后排 1-N 动态,后排拖点按 back_slot_count 布局档静态解析;tracked
第二账停用后旧换算族已删)。坐标参数化
机械动作(开件三类 CwActionOpenBoxParam/CwActionOpenTomeParam/
CwActionOpenBookcardParam)的 row/slot 字段 = 画面物理排槽位 1 基
(动作参数定义,拖点直取 area,不经换算);穿装与工具原子两类已升级
「动态坐标显式传 + row/slot 半固定」形态(起点 = 1080p 显式坐标,
槽位拖点经模块级 row_drag_points 静态解析,op 自持零读屏)。
统一动作工厂并入:动作级
机械执行体已逐字迁入 ``operations/cw_op/`` 备战 op 类(一 op 一文件),
分派改查单一注册表 ``action_op_for``(_dispatch_action);本模块保留
runner 包络(刹车/回执登记与机械原语)与薄委托族(替身函数的接缝(stub seam):九桩零调用
已删,``_open_bookcard`` 随其参数面迁移批删除——其保留理由所引单帧测试已
不存在,全仓零消费)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionLevelUpParam,
    CwActionSellBenchParam,
    CwActionStartBattleParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: overlay 弹出/关闭的固定动画等待(等待归产生动画的操作)。
#: 值依据:单局耗时审计报告
#: .debug/temp/currency_war/w417_duration_audit/REPORT.md
#: 「需验证·出战链」的最坏耗时上界(判效已拆,用户裁定动作 op 只机械
#: 执行);弹窗就位与否交下一帧观察。
_OVERLAY_ANIM_WAIT_S: float = 1.8

#: 商店收起动画时长(操作完成自等动画;实测口径 screen_flow_timing
#: #15「收起过场动画 ~1s 即备战画面稳定」,用户口述。op 完成后显式等待,替代
#: 测量驱动 gate——画面状态判断已外移建档识别层,等待时长归产生动画的操作声明)。
SHOP_CLOSE_ANIM_S: float = 1.0
#: 商店打开动画时长(固定时长自等;用户口述定值 2026-09-02「干净的备战
#: 里打开商店,只要等 1 秒就够了」。开态判定由下一帧观察侧 0n 三个识别标志承载。
#: 自动开店场景不经此处——cw_loop 备战分支按「备战阶段」识别)。
SHOP_OPEN_ANIM_S: float = 1.0
#: 穿戴拖前固定等待(等备战面板/上件 reflow 动画收尾,非判效)。取值 =
#: 被替换的稳帧轮询典型检测档 0.3s 向上取整(与 pick 确认 0.6-1.2s 固定
#: 等待族同量级);后随动作的动画由拖后固定等待覆盖,极端 reflow 未收尾
#: 致按压抓空 = 未发出形态,由下一入口观察对账暴露 + 决策环自然重派
#: (按「不存在偶发丢失」纪律查根因调常量,禁恢复轮询)。
PREP_DRAG_SETTLE_WAIT_S: float = 0.5


# ============================================================ 回执受阻码(统一口 round_fail status 闭集映射)

#: round_fail status 前缀 → 回执受阻码(闭集映射;词表暂住本表,回执契约
#: 权威版本 = cw_game_state.note_action_receipt docstring)。表项 = (status 前缀, 受阻码):
#: 受阻码自带族前缀——``未执行:`` = 点击前失败(定位缺失/无对象/
#: 输入契约拒绝,动作没发出)。映射键 = 各动作 op round_fail status 的
#: 首段字面前缀(status 由 op 固定字面量产出);**新 round_fail status
#: 必须同步登记本表**——漏登走 :func:`_prep_receipt_block_code` 原文
#: 兜底(受阻事实不静默,复盘以原样 status 在日志里暴露促登记)。特定前缀先于
#: 泛化前缀(表序 = 匹配序,首中即返)。
#: (terminal-fail-status 迭代收缩:参数违法类三个登记入口(BuyCard 槽解析/槽号
#: 越界、DeployMove 落位越界)改 op 内守卫断言、建档缺失类检查段
#: (LevelUp/StartBattle 主口与弹窗/WearEquip 槽位坐标)删除 = 自然
#: 异常报错——上述形态零 round_fail 供给,对应映射行随批退役;
#: ``未生效:*`` 族(StartBattle 弹窗收尾)随之零供给退役。开件三动作
#: (箱/典籍/书册卡)执行前识别读门随状态容器槽位直点形态拆除:判空 fail
#: (无简易武装箱/无秘密典籍/无书册卡)零 round_fail 供给,映射行退役
#: ——状态容器陈旧「件不在」的治理归观察对账域,非动作 op 失败分支。
#: 「owned 网格未定位」三行(工具/目标件/泛化)随工具原子族坐标显式化
#: 退役(两供给方 = 穿装批退 WearEquip、本批退工具,全仓零 round_fail
#: 供给;定位落空治理 = 发出面坐标缺席跳过 + 记账拒单通道)。)
_PREP_RECEIPT_BLOCK_CODES: tuple[tuple[str, str], ...] = (
    # —— 出战(点击前):按钮定位失败 = 动作没发出 ——
    ('未执行:找不到按钮', '未执行:定位缺失(按钮-出战)'),
    ('area 缺失:按钮-出战', '未执行:定位缺失(按钮-出战)'),
    ('area 缺失:按钮-跳过', '未执行:定位缺失(按钮-跳过)'),
    # —— 出战前团队规模超限守卫(guard_team_size_over_cap_for_battle;执行前
    #     防 bug 守卫,动作没发出。词表登记 = cw_game_state.note_action_receipt
    #     docstring 同名条)——
    ('未执行:团队规模超限', '未执行:团队规模超限(规模占用>上限)'),
    # —— drag 类动作浮层守卫(prep_drag_overlay_gate;执行前输入契约
    #     拒绝,动作没发出。括号族 = 守卫检查清单两族并集,标识细节
    #     以原样 status 的「(标识)」段在日志里暴露)——
    ('未执行:浮层在场', '未执行:浮层在场(合成确认/角色详情)'),
)


def _prep_receipt_block_code(status: str) -> str:
    """round_fail status → 回执受阻码(闭集映射单一源
    = :data:`_PREP_RECEIPT_BLOCK_CODES`)。

    未登记 status = 原文兜底(``未执行:<status>``):机械事实
    「没发出」由 round_fail 通道保证,受阻细节以原样 status 进子码槽
    不丢真;出现兜底形态 = 词表漏登,登记义务见词表注释。
    """
    for prefix, code in _PREP_RECEIPT_BLOCK_CODES:
        if status.startswith(prefix):
            return code
    return f'未执行:{status}'


class StopBrakeShortCircuit(RuntimeError):
    """停机短路异常(纵深防御第二层)。

    语义 = 运行中被停 → 拒绝执行任何动作(run 27 实证:director 环在
    Deploy 钩子 stop_running 后仍发 CwActionStartBattleParam 点出战——环顶检查(第一层)
    之外,本入口兜底覆盖绕环路径)。表达 = 本异常:执行器抛出,
    调用方(cw_screen_prep 决策环 / 本模块出战发出核 launch_prepared_battle)
    捕获后返回主循环,
    下轮 loop 顶见 STOP 退出。判据 = last_run_result 非空(start 清
    None/stop 写入;run_state STOP 是 idle 初始态不能直接用)。
    """


def row_area_centers(ctx: SrContext, prefix: str,
                     screen_name: str = SCREEN_NAME) -> list[Point]:
    """从 screen_info 读全部 prefix-N 区域中心(N 升序)。

    逐区现读、不硬编码(后排 >6 时 screen_info 补区后自动跟上);
    prep_actions 执行器 / cw_screen_prep 观察共用。``screen_name`` =
    坐标权威画面(缺省备战画面;商店域传商店开画面——底栏 area
    商店画面档自备,跨屏坐标不共用文件)。

    [拖点权威分域(角色拖动族)]:本函数裸中心(rect 中心)= 角色拖动族
    (MoveUnit/SellDeployed/SellBench 阵型操作)的拖点权威派生式——该族
    交互 = 整卡可拖、卡中心拖 + hold0(实测背书,机制单一源 =
    operations/actions/drag_cw_char.py 模块头);装备 icon→角色卡族
    (WearEquip/工具 char 模式)的权威派生式 = ``row_drag_points`` +21
    (D-36 校准,落点须命中卡内头像区)。两族交互机制不同,派生式按交互族
    分域,互不外溢。
    """
    si = ctx.screen_loader.get_screen(screen_name)
    if si is None:
        return []
    pts: list[tuple[int, Point]] = []
    pfx = f'{prefix}-'
    for a in si.area_list:
        if a.area_name.startswith(pfx) and a.pc_rect is not None:
            try:
                n = int(a.area_name[len(pfx):])
            except ValueError:
                continue
            pts.append((n, a.pc_rect.center))
    pts.sort(key=lambda t: t[0])
    return [p for _, p in pts]


def row_drag_points(ctx: SrContext, prefix: str,
                    screen_name: str = SCREEN_NAME) -> list[Point]:
    """prefix-N 全排 avatar 拖点列(rect 中心 x + y1+21)。

    [拖点派生权威裁定(装备 icon→角色卡族)]:+21(D-36 校准)= 穿戴域实机
    校准背书的权威派生式;工具 char 模式拖点已随坐标参数面迁移统一按本式
    (同一「拖到角色卡」交互同一拖点;旧裸中心派生经 executor 点表的历史
    形态已退役)。⚠️ 辖域 = 装备 icon→角色卡交互族——角色拖动族
    (MoveUnit/SellDeployed/SellBench)拖点 = ``row_area_centers`` 裸中心
    (该族权威式,整卡可拖中心拖 + hold0,交互族不同不外溢,分域申报见
    其 docstring)。后排档前缀由调用方按 back_slot_count →
    ``cw_back_layout._layout_prefixes()`` 静态解析后传入,本函数零识别
    零截图。区域缺失 = 该排空列,调用方守卫断言越界自然暴露,禁兜底
    坐标。
    """
    si = ctx.screen_loader.get_screen(screen_name)
    if si is None:
        return []
    pts: list[tuple[int, Point]] = []
    pfx = f'{prefix}-'
    for a in si.area_list:
        if a.area_name.startswith(pfx) and a.pc_rect is not None:
            try:
                n = int(a.area_name[len(pfx):])
            except ValueError:
                continue
            pts.append((n, Point((a.pc_rect.x1 + a.pc_rect.x2) // 2,
                                 a.pc_rect.y1 + 21)))
    pts.sort(key=lambda t: t[0])
    return [p for _, p in pts]


def sell_point(ctx: SrContext, screen_name: str = SCREEN_NAME) -> Point:
    """出售区落点(单一源):screen_info「区域-出售区」中心
    (游戏机制 = 拖到左下区域即出售,无按钮)。

    ``screen_name`` = 坐标权威画面(缺省备战画面;商店域传商店开画面)。
    area 缺失 = 建档漂移/档案损坏 → RuntimeError 显式上抛(信息带 area
    名),禁回退硬编码坐标静默点击(坐标单一真相源)。消费面含
    卖上阵 off-target 拖拽,落点直入 drag 原语 → None 不可流入,
    直取 + 上抛是唯一兼容形态。
    """
    pt = area_center(ctx, '区域-出售区', screen_name=screen_name)
    if pt is None:
        raise RuntimeError(
            f'area 缺失:区域-出售区({screen_name}),出售区落点不可派生,禁兜底坐标')
    return pt


def drag_char_guarded(op: SrOperation, ctx: SrContext,
                      src: Point, dst: Point) -> None:
    """角色拖拽机械原语(失焦守卫 + 统一拖拽原语;sim 分支静默)。

    构成:sim 模式(``sim_backend_installed``)整段静默返回(机械执行分支
    静默成功,自上报照走——直连旁路 port 检查)→ 失焦守卫(窗口后台化时
    拖拽输入静默丢,拖前验焦点先激活)→ ``DragCwChar.drag_char``(统一
    角色拖拽原语:中心拖 + hold0,机械执行零判效,发出即职责完成)。

    阵型拖动动作(MoveUnit)与卖出共享原语 ``drag_bench_to_sell`` 共用
    本函数 = 失焦守卫单一宿主(原散落 executor._drag 与
    drag_bench_to_sell 两份内联副本收敛至此;executor._drag 已随开件族
    收官批物理退役,全部拖拽消费 op 均走本宿主)。
    """
    from sr_od.application.currency_war.sim.cw_sim_ports import (
        sim_backend_installed,
    )
    if sim_backend_installed():
        return
    try:
        gw = ctx.controller.game_win
        if not gw.is_win_active:
            log.warning('[cw!][drag] 窗口失焦(拖拽输入将静默丢)→ 先激活')
            gw.active()
            time.sleep(0.3)
    except Exception:   # noqa: BLE001  焦点守卫 best-effort
        pass
    from sr_od.application.currency_war.operations.actions.drag_cw_char import (
        DragCwChar,
    )
    DragCwChar.drag_char(op, src, dst)


# ============================================================ drag 类动作浮层守卫(执行前输入契约拒绝)

#: drag 类动作发出前的浮层检查清单(轻检查,非全量浮层扫描——每动作付
#: 逐锚 find 成本;全量身份扫描 = 阶段一身份分发每帧现役,本表 = drag 类
#: 动作侧轻守卫,取舍见 ``prep_drag_overlay_gate`` docstring)。
#: 表项 = (画面名, 识别标志 area, 在场标识, 失败指引)。初版两项实证吞面:
#: 合成确认浮层(全局模态阻断,浮层外拖拽全吞,r9 局实证)+ 角色详情面板
#: (拖拽退化成点卡后面板继续吞后续输入,001156 帧物证)。判定口径 =
#: 单锚命中即拦(比分发双锚全中宽一档)——守卫要「宁可误拦」,与分发
#: 「宁可漏派不误派」方向相反,不对称申报见消费方 docstring。
_DRAG_BLOCK_OVERLAYS: tuple[tuple[str, str, str, str], ...] = (
    ('货币战争-备战-合成确认', '按钮-合成浮层通过', '合成确认浮层',
     '先收尾合成确认浮层(点 ✓;可调 CwScreenSynthesisConfirm)'),
    ('货币战争-备战-合成确认', '按钮-合成浮层取消', '合成确认浮层',
     '先收尾合成确认浮层(点 ✓;可调 CwScreenSynthesisConfirm)'),
    ('货币战争-备战-角色详情', '按钮-装备推荐', '角色详情面板',
     '先关闭角色详情面板(点面板外空白)'),
    ('货币战争-备战-角色详情', '装备详情-合成公式', '角色详情面板',
     '先关闭角色详情面板(点面板外空白)'),
)


def prep_drag_overlay_gate(op: SrOperation) -> str | None:
    """drag 类动作发出前的浮层守卫(执行前输入契约拒绝)——
    prep_actions 模块头「防线边界申报」现役辖面:拦截错误画面上的机械
    发出,非动作后判效。

    检查清单 = :data:`_DRAG_BLOCK_OVERLAYS`(轻检查,非全量
    ``CW_DISPATCH_SCREENS`` 身份分发扫描——每拖付逐锚 find 成本,量级可接受;
    框架环已有 bail 面承接全量,本门只兜「动作直调面零防线」的洞)。命中
    返回在场标识(供 round_fail 文案与受阻码映射),``None`` = 无浮层放行。
    帧 = 复用 ``op.last_screenshot``(当轮已截免重截;无则截一帧)。
    调用方须置于 ``mechanical_io_allowed()`` 分支内(sim 零触及)。
    """
    screen = getattr(op, 'last_screenshot', None)
    if screen is None:
        screen = op.screenshot()
    for screen_name, area_name, label, _hint in _DRAG_BLOCK_OVERLAYS:
        if op.round_by_find_area(screen, screen_name, area_name,
                                 crop_first=False).is_success:
            return label
    return None


def drag_overlay_block_status(hit: str) -> str:
    """守卫命中标识 → round_fail status(带家族指引;前缀恒
    ``未执行:浮层在场`` = 受阻码映射表登记键)。安装点共用格式化单一源,
    禁各 op 手拼文案(指引随清单表演进)。"""
    for _screen, _area, label, hint in _DRAG_BLOCK_OVERLAYS:
        if label == hit:
            return f'未执行:浮层在场({label})——{hint}'
    return f'未执行:浮层在场({hit})'


def drag_bench_to_sell(op: SrOperation, ctx: SrContext, bench_idx: int,
                       screen_name: str = SCREEN_NAME) -> None:
    """拖备战槽(槽位下标 0-8)→ 出售区(共享卖原语,设计章 2.10)。

    现役消费者 = MCP 动作原语 ``CwSellBenchBySlot`` 单一(备战域 op
    CwActionSellBenchOp 已随其参数面迁移批改 op 内自持现读,不再经本
    helper):「拖→出售区」机械一段(发出即职责完成,落地事实归观察侧
    reconcile 对账);内置点表越界守卫 = MCP 直调原语面兜底。拖拽机械半
    = ``drag_char_guarded``(失焦守卫单一宿主)。浮层守卫面 = 调用方节点
    自装(``CwSellBenchBySlot.drag_sell`` 先例):守卫受阻需 round_fail
    通道(受阻码闭集),本 helper 为 void 机械原语不承载;新调用方接入须
    自带同款守卫(``prep_drag_overlay_gate`` 置 sim 门内),禁沿用裸拖。

    Args:
        op: 调用方 op(取 ctx.controller 操作)。
        ctx: SrContext。
        bench_idx: 槽位下标 0-8(列表下标 = 物理备战栏槽位 1-9 减一);
            越界 = 调用方 bug,响亮上抛(守卫非判效)。
        screen_name: 拖拽两端的坐标权威画面(缺省备战画面;商店域
            传商店开画面——该画面档自备 备战栏/出售区 area)。
    """
    pts = row_area_centers(ctx, '备战栏', screen_name=screen_name)
    if not (0 <= bench_idx < len(pts)):
        raise AssertionError(
            f'[cw][guard] 卖出拖拽槽位越界:bench_idx={bench_idx}'
            f'(备战栏 area 数={len(pts)};调用方 bug 响亮暴露)')
    drag_char_guarded(op, ctx, pts[bench_idx],
                      sell_point(ctx, screen_name=screen_name))


# (装备穿戴计划构造单一源 = kernel/cw_equip_wear_plan(原子通路);
#  动作发出点(mandate M7)直接消费同一构造函数,无第二源。)
# (tracked 写点槽号健康暴露 _expose_unhealthy_tracked_slots 已随
#  tracked 第二账停用而删除:其两个调用点均为 tracked 摘除分支,分支删则
#  helper 无消费面;状态容器形槽号 = 下标权威结构性健康。)


@dataclass
class PrepExecEnv:
    """备战动作 op 执行环境(域依赖结构化包)。

    域依赖结构化包,op 构造时传入(原 execute 时刻注入改为构造时)。
    ``executor`` = 备战 runner 包络引用(坐标槽位表/机械原语/tracked 账
    同步的单一宿主;op 体经此消费,执行包络留在 runner)。``detail`` =
    prep 域遗留旁路字段(机械执行摘要,字段值不再被包络消费);发出
    事实归 round 结果成功态(executor 局部派生,不经 env 字段承载);
    ``skip_substate`` 仍被包络消费(回执 extra 保留证据)。
    """

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None    # 协议公共面(备战动作执行面零 config 消费)
    executor: PrepActionExecutor | None = None
    detail: str = ''
    # 免战跳过子态标记(StartBattleOp 上报通道;op 写、runner 包络
    # _dispatch_action 读一次转发 game state 上报路径。False = 常规出战)
    skip_substate: bool = False


class PrepActionExecutor:
    """备战原子动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定)。角色拖拽统一拖拽原语 = 模块级
    ``drag_char_guarded``(失焦守卫 + DragCwChar.drag_char 中心拖 + hold0,
    2026-08-13 实测验证);机械动作执行体已逐个迁 ``operations/cw_op/``
    各 op 文件(点表属性与 ``_drag`` 方法已随开件族收官批物理退役——
    全部消费 op 已随各自参数面迁移批改 op 内现读 ``row_area_centers``
    /消费模块级拖拽原语)。
    """

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 机械执行摘要(最近一次 execute 的 detail;登记件解析输入,非成败
        # 回执——端口无返回,摘经由本属性旁路供 on_outcome detail)。
        self.last_detail: str = ''
        # 出战点击事实(出战域重设计收缩语义):True = StartBattleOp
        # 点击已执行(单击原子,op 内零弹窗收尾);False = 找不到按钮/area
        # 缺失等未执行形态。消费方 = 出战发出核 launch_prepared_battle
        # (本模块,返回值旁路)。getattr 容缺(__new__ 桩形态)。
        self.last_launch_ok: bool | None = None
        # 最近一次分派的动作 op round 结果(QC 终结口失败透传的取数口;
        # 逐分派覆盖 = 恒本拍动作,防上拍残留误透传)。消费方 =
        # cw_screen_prep._act_execute_default 终结口入参;非终结动作
        # 零消费。getattr 容缺(__new__ 桩形态)。
        self.last_round_result: OperationRoundResult | None = None
        # StartBattleOp 上报的免战跳过子态标记(op 写 env.skip_substate,
        # dispatch 后由本 runner 读取一次,只进回执 extra 保留证据——递减本体
        # = op 自上报)。getattr 容缺(__new__ 桩形态)。
        self._last_skip_substate: bool = False

    # ===== 执行入口(机械执行,无返回;参数守卫已收拢各动作 op 内
    #       守卫断言,flow/action_ops.md §1 决策侧参数现算契约)=====

    def execute(self, action: CwAction) -> None:
        """机械执行一个动作(无返回;发出即职责完成,落地判定归
        观察侧 reconcile)。

        ⚠️ 停机刹车(纵深防御第二层):运行中被停 → 拒绝
        执行任何动作(点击/拖拽/出战),抛 :class:`StopBrakeShortCircuit`
        停机短路(语义与触发判据见类 docstring;run 27 实证覆盖绕环路径)。
        调用方捕获后返回主循环,下轮 loop 顶见 STOP 退出。

        发出即登记(期望态推进门/标志/清键门 = 发出即登记 + 对账纠偏,
        不按回执门控;执行前输入契约拒绝 = 动作未发出,不登记)。
        """
        _rc = getattr(self._ctx, 'run_context', None)
        if _rc is not None and getattr(_rc, 'last_run_result', None) is not None:
            log.info('[cw][battle] 停机标志已设 → 拒绝执行 %s'
                     '(W209j 刹车)', type(action).__name__)
            raise StopBrakeShortCircuit('已停止[W209j刹车]')
        # 免战跳过子态标记每动作复位(上动作残留禁跨动作流入;op 上报经
        # _dispatch_action 写入,回执 extra 消费)。
        self._last_skip_substate = False
        detail, op_success = self._dispatch_action(action)
        self.last_detail = detail
        _extra = None
        if isinstance(action, CwActionStartBattleParam) and self._last_skip_substate:
            # 跳过子态标记进回执 extra(上报动作事实的遥测面;递减本体 =
            # op 自上报,回执只保留证据)。
            _extra = {'skip_substate': True}
        self._note_action_receipt(action, op_success, detail, extra=_extra)
        if isinstance(action, CwActionStartBattleParam):
            # 出战点击事实(出战域重设计):真执行链 = 注册表分派
            # CwActionStartBattleOp 单击(单击原子,op 内零收尾零验证),
            # round 结果成功态即发出事实
            # (round_fail = 找不到按钮/area 缺失,已登记例外 =
            # action_ops.md §2.3);
            # 执行缝(假环境)不经真分派 = round 成功态原值透传。
            self.last_launch_ok = op_success
        # (S1 清键执行侧落地门已停用删除
        # 备战期开店标志废止,清键门无对象。)]
        # (动作逻辑效果推进已并入各 op 自上报
        #  (op 内直调自己的上报函数,op-layer.md §1.2):原执行器
        #  apply_op_effect 调用删除 = 双记防线——op 已写,本处再写即双记。)
        log.info('[cw][exec] %s → %s', type(action).__name__,
                 detail or '(无摘要)')

    def _note_action_receipt(self, action: CwAction, op_success: bool,
                             detail: str,
                             extra: dict | None = None) -> None:
        """动作执行回执 → GameState receipts 域
        (渠道② logic_action,唯一写点 = kernel note_action_receipt)。

        - **纯动作事实簿记,不是验证**(R2 报告重构期的『发出即簿记非
          验证』裁定):本写点零成败判定——不读屏、不做落地推断
          (「拖3次源槽未变」类像素验回执已停用),落地判定归观察侧
          reconcile;
        - reason = 动作事实码:op_success(round 结果成功态,局部派生事实)
          为真 = ``''``(已正常发出);为假 = round_fail status 经
          :func:`_prep_receipt_block_code` 闭集映射取受阻码
          (收缩后词表 = ``未执行:*`` 现读落空族,词表见映射表注释;
          异常终止的分派在本口之前抛出 = 不产行)。
          op_success 的在役消费两管道 = ①锁定恢复局守卫
          (``last_launch_ok``)②本口受阻码供给;
        - 回执行以分派为单位:每分派恰一条 logic_action 行(受阻
          动作也产行 = reason 非空受阻码;停机短路在分派之前抛出 =
          执行被拒不产行——停机非动作);
        - ``extra`` = 执行面结构化字段透传(质量词表执行面;
          现役唯一项 = 免战跳过子态 ``skip_substate``);
        - journal 常开(影子闸折叠)回执写入无条件;无局
          (session 缺)跳过;best-effort 不阻塞动作链。
        """
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_from_ctx,
                note_action_receipt,
            )
            gs = game_state_from_ctx(self._ctx)
            if gs is None:
                return
            note_action_receipt(
                gs, op=type(action).__name__,
                reason='' if op_success else _prep_receipt_block_code(detail),
                detail=detail,
                screen=SCREEN_NAME, actor=type(self).__name__, extra=extra)
        except Exception as e:  # noqa: BLE001  回执失败不阻塞执行
            log.warning('[cw][receipt] 动作回执写入失败(不阻塞): %s', e)

    def note_blocked(self, action: CwAction, detail: str,
                     extra: dict | None = None) -> None:
        """执行前守卫拦截的披露行:动作未发出也落一条**受阻回执**
        (reason = ``_prep_receipt_block_code(detail)`` 受阻码,detail/extra
        透传)——「受阻动作也产行」契约对守卫拦截路径的同款兑现,让拦截
        事实进 receipts 域(遥测 / 判读可数),不只剩日志行与 round_fail
        status。现役调用方 = 出战前团队规模超限守卫。"""
        self._note_action_receipt(action, False, detail, extra=extra)

    def _dispatch_action(self, action: CwAction) -> tuple[str, bool]:
        """动作分派(经注册表类级解析 + (ctx, param,
        env) 组装新壳 op ``CwActionXxxOp(SrOperation)``,执行取 round
        结果;op 形态权威版本 = flow/action_ops.md §1)。

        返回 ``(机械执行摘要, 是否实际发出)``。op_success = round 结果成功态
        (``round_success`` = 已发出;``round_fail`` = 定位失败等未发出
        通道,零重试即失败结束本次访问)。机械摘要 = round 结果 status。词表外
        类型 = 注册表 AssertionError 响亮暴露(参数守卫单一形态 =
        守卫断言,op 内/注册表两静态域同款)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_class_for,
        )
        env = PrepExecEnv(op=self._op, match=self._ctx.cw_match, config=None,
                          executor=self)
        op = action_op_class_for(action)(self._ctx, action, env=env)
        # 直调节点函数(单节点 op;不走 Operation.execute() 循环:重试/
        # 超时/停机查归本 runner 包络与结束本次访问的出口面所有,动作层零重试语义——
        # 节点异常原样上抛 = 执行异常通道不变)
        result = op.run()
        # op round 结果留档(QC 终结口失败透传取数口;逐分派覆盖)
        self.last_round_result = result
        if isinstance(action, CwActionStartBattleParam):
            # 免战跳过子态标记转发(op 写 env.skip_substate;递减本体 =
            # op 自上报,回执 extra 保留证据消费;getattr 容缺 = 桩 env 形态)
            self._last_skip_substate = bool(getattr(env, 'skip_substate',
                                                    False))
        return (result.status or ''), bool(result.is_success)

    # ===== 装备/工具原子域(工具按消耗品各立类;机械原语
    #       _owned_grid_locate 已随工具原子族坐标显式化退役:全仓零消费
    #       ——穿装批退 WearEquip 消费、工具迁移批退工具 op 消费,发出面
    #       坐标源 = 坐标伴随域 gs.owned_equip_xy。WearEquip/工具两 op 均
    #       改显式坐标 + 记账拒单;拖点权威派生式 = 模块级
    #       row_drag_points,穿装 op 与工具 char 模式自持消费。MoveUnit
    #       已随其参数面迁移改 op 内自持消费模块级 drag_char_guarded;
    #       _drag 方法已随开件族收官批物理退役——全部拖拽消费 op = 模块级
    #       drag_char_guarded 单一宿主)=====

    # (tracked 随动同步三条分支(备战摘除/场上摘除/上阵落位)已随
    #tracked 第二账停用删除:动作写主域(逻辑
    #  通道)即同步,第二账无可同步;落地事实归观察边界 reconcile 对账。)

    # ===== 商店域 =====

    def _level_up(self, action: CwActionLevelUpParam | None = None) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_level_up_action.CwActionLevelUpOp``;替身函数的接缝(stub seam)保留)。

        ``action`` 形参 = 注册表分派载体(原签名无参——单击体不读动作
        字段;缺省补零价占位实例仅作类型解析,行为零变化)。"""
        return self._dispatch_action(
            action if action is not None else CwActionLevelUpParam(cost=0))

    # ===== 战斗域 =====
    # StartBattleOp 现体 = 出战单击(零判效,点击已执行语义,op 内零弹窗
    # 收尾——点击后弹窗归主循环弹窗 op 接管);
    # 本入口保留薄委托替身函数的接缝(stub seam),返回序 (ok, detail)。

    def _start_battle(self) -> tuple[bool, str]:
        """薄委托(体已迁 ``cw_start_battle_action.CwActionStartBattleOp``;替身函数的接缝(stub seam)保留)。"""
        detail, op_success = self._dispatch_action(CwActionStartBattleParam())
        return op_success, detail


# ============================================================ 出战发出链(armed/resume 两调用面共用;住址申报见模块头)


def locked_resume_sync_and_battle(op, ctx):
    """恢复局锁定直出战+ **首战前备战同步步**(裁定出处 =
    策略审查报告 .debug/temp/currency_war/20260905-093104-strategy-review/
    策略审查-第十二跳.md #7):恢复局分支原样跳过全部备战交互直接
    CwActionStartBattleParam,板面调整被跳过(实证:恢复局首战快照 board_before 为空
    ——部署面零执行)。本函数在 CwActionStartBattleParam 前插一次 **部署原子序同步步**
    (按策略层部署计划现算逐 move 发统一拖动/换星直卖原子——阶段 5/6 丁
    起计划 = 统一部署搜索定型 + 差分执行器;板空时计划恒空,与零商店交互形态同构;锁定
    局「商店探针零响应」禁令只覆盖商店域,部署面不受覆盖)。

    证据位语义(最严读法申报「发出即写」):同步步
    **发出后立即置位** ``ctx.cw_match.locked_sync_done``——原「ok=True
    才置位 + 失败重试(上限 3)」消费执行器成败回执,回执已停用,
    失败概念在发出型下消解,重试/放弃治理结构随之停用(发出次数预算
    承载归 J2 形态,同源重推);「部署是否真落地」由下一帧观察侧
    reconcile 对账暴露(与既有 token 门「发出即写」同款裁定)。锁定
    确认分支复位证据位。

    隐藏前提声明:同步步的「不误卖」依赖接管局 session 必新鲜——
    接管路径(探针门/同步步仅经锁定面可达,锁定局必为接管局)的 Match
    容器均为本次运行新建(establish_new_match 每次新建 StrategySession
    与 GameState;跨 run 残留由 loop handle_init 重建判据弃旧重建,
    判据 = 2026-11-19-resume-rebuild design §2.4),新容器未观察
    ⇒ deploy-swap 卖出通道整体跳过(board 未观察不可判),同步步实际
    只做确定性部署;若未来放开 mid-run 复用旧 session,stale board
    会让同步步按旧目标线卖新局板面——届时须先加卖出输入守卫。

    **无条件插入,零血线判据**:hp 入参合规口径 = λ 表血带维或已确认
    硬地板授权(00_framework §3)——「hp≤阈值则强制同步」形态不实现,
    登记待办:待玩家确认。与「达标即出战」分支(skill strategy/14_p1_consume_arms.md §9.6)的关系按 C1 规格:本函数
    = 恢复局面调用面(标志覆盖),底层动作发出核 = ``launch_prepared_battle``
    单一函数,达标分支经策略层前置动作发出点(bridge._launch_front_check)调用
    面共用动作发出核、**不过本标志**(旧「须经本函数单一动作发出点,禁旁路」话术
    与 C1 矛盾,按规格改写)。
    """
    return launch_battle_unified(op, ctx, face='resume')


def _battle_chain_deploy_moves(session) -> list:
    """出战链部署计划(策略层部署计划单一源;R2 原子通路)。

    计划单一源 = mandate_v1 ``deploy_plan.battle_chain_deploy_params``
    (frame 状态容器现读装配 + 选人 + 落位策略全在策略层;design
   -benchchar-retirement §2.2「出战链不再装配选人输入」)。
    与 mandate 动作发出点同一计划函数,禁第二套计划语义。恢复局同步步/
    达标分支共用;空板面/计划空 = 空 move 序(CwActionStartBattleParam
    照发)。"""
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        battle_chain_deploy_params,
    )
    if session is None:
        return []
    return list(battle_chain_deploy_params(session))


# ============================================================ 出战前置席满守卫(执行前输入契约守卫)

#: 席满腾位守卫卖出后的告警复查等待(固定时长,等待归产生动画的操作:
#: 卖出动作 op 内已含卖出动画固定等待,本等待覆盖告警横幅消失的过场窗;
#: 横幅消失依据 = 游戏机制(告警 = 有未安置单位,卖 1 腾 1 → 溢出件
#: 入位 → 无未安置;实机人工验证「卖 1 个后台角色腾位 → 出战生效」
#: 流程),值取卖出动画之外的保守整档余量)。
_BENCH_OVERFLOW_SETTLE_S: float = 0.8


def _bench_overflow_banner_present(op: SrOperation) -> bool:
    """「备战席已满」告警横幅画面现读(与观察链写端同源同口径:
    同 area 同查法,观察链 = cw_screen_prep._observe 溢出告警段)。
    OCR 区单锚在场判定,真值 = 游戏侧权威信号(横幅在场 = 出战被忽略
    的处理门,见 screen_info 备战画面档告警 area 建档)。"""
    screen = op.screenshot()
    return op.round_by_find_area(screen, SCREEN_NAME,
                                 '告警-备战席已满',
                                 crop_first=False).is_success


def guard_bench_overflow_for_battle(op: SrOperation, ctx: SrContext,
                                    ex: PrepActionExecutor
                                    ) -> tuple[bool, str]:
    """出战前置席满守卫(执行前输入契约守卫,防线边界申报见模块头)。

    游戏侧事实(实机实证 + prep.md 告警节建档):「备战席已满」告警
    横幅在场时出战会被游戏**静默忽略**(无战斗无结算金币不变),bot
    侧无感知继续跑。守卫 = 该缺口的流程侧兜底(防 bug 守卫族,合法
    判断面——不改出战意图本身,只保证出战动作物理有效):
    告警在场 → 卖一个备战席角色腾位(机械必要操作,零策略语义——
    选槽 = 槽位表第一个 kind='unit' 槽的确定性规则;卖出经 runner
    包络正常记账,上报溢出分支当帧记溢出件入位并投影告警清零)→
    复查告警消失再放行出战。

    - 告警不在场 → ``(True, '')`` 放行,零行为变化(仅付一帧告警
      area 识别成本);
    - 告警在场但选不出槽(无局状态/备战席槽表未观察/无 unit 槽)→
      ``(False, detail)`` 出战未发出,交回外循环重观察重决策(下一帧
      heavy 观察重建真值,策略对账后自然重派,守卫不自旋);
    - 卖出后复查告警仍在场(拖拽被吞等机械落空)→ ``(False, detail)``
      出战未发出(发了必被忽略);单次卖出 + 单次复查,重试治理交
      外循环(卖出的逻辑态已按「点完即写」契约落账,真值纠偏归下一帧
      观察对账——守卫内不做二次选槽,防基于失真逻辑态误卖)。

    sim 布局零触及(机械 IO 门内才检查;sim 的 overflow_warning 真值
    由获得链维护、卖出上报溢出分支投影清零,无画面守卫需求)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_from_ctx,
    )
    from sr_od.application.currency_war.sim import cw_sim_ports
    if not cw_sim_ports.mechanical_io_allowed():
        return True, ''
    if not _bench_overflow_banner_present(op):
        return True, ''
    gs = game_state_from_ctx(ctx)
    _bview = gs.bench.value if gs is not None else None
    slots = list(_bview.slots) if _bview is not None else None
    if not slots:
        log.warning('[cw!][battle] 席满守卫:告警在场但备战席槽表不可用'
                    '(无局状态/未观察)→ 出战未发出,交回外循环重观察')
        return False, '未执行:席满腾位失败(告警在场但备战席槽表不可用)'
    # [索引定义] idx = BenchView.slots 列表下标(0 基,物理槽 = idx+1);
    #             取值时机 = 守卫执行期现读状态容器逻辑态,立即用于卖出。
    idx = next((i for i, s in enumerate(slots)
                if s.kind == 'unit' and s.unit is not None), None)
    if idx is None:
        log.warning('[cw!][battle] 席满守卫:告警在场但槽表无角色可卖'
                    '→ 出战未发出,交回外循环重观察')
        return False, '未执行:席满腾位失败(告警在场但无角色可卖)'
    param = CwActionSellBenchParam(bench_idx=idx,
                                   expect=slots[idx].unit.char_id,
                                   reason='self_rescue_sell')
    ex.execute(param)
    _sold_detail = getattr(ex, 'last_detail', '')
    _sold_rr = getattr(ex, 'last_round_result', None)
    _sold_ok = bool(_sold_rr is not None and _sold_rr.is_success)
    log.info('[cw][battle] 席满守卫:告警在场 → 卖备战栏%d 腾位(%s;round=%s)',
             idx + 1, _sold_detail, '成功' if _sold_ok else '受阻')
    time.sleep(_BENCH_OVERFLOW_SETTLE_S)
    if _bench_overflow_banner_present(op):
        log.warning('[cw!][battle] 席满守卫:卖出后告警仍在场(卖出未生效'
                    '或仍席满)→ 出战未发出,交回外循环重观察')
        return False, (f'未执行:席满腾位失败(卖出后告警仍在场:'
                       f'卖备战栏{idx + 1} {_sold_detail})')
    log.info('[cw][battle] 席满守卫:腾位生效(告警消失)→ 放行出战')
    return True, f'席满腾位守卫:已卖备战栏{idx + 1}腾位'


def guard_team_size_over_cap_for_battle(op: SrOperation, ctx: SrContext,
                                        ex: PrepActionExecutor
                                        ) -> tuple[bool, str]:
    """出战前团队规模超限守卫(执行前防 bug 守卫;防线边界申报见模块头)。

    游戏侧事实(实机核正):团队规模上限约束的是**各单位占用之和**;主角光环
    可让持有者占 2 点(「上阵该角色占用2团队规模」),板满后再选即超限——
    画面「X/Y」变红色 X > Y,此时点「出战」被游戏**静默拒绝**(无横幅无弹窗、
    按钮仍亮),bot 侧点完即写逻辑态「已出战」假前进。守卫 = 该缺口的流程侧
    兜底:现读「X/Y」(经 ``cw_observation.read_paddle_pair_confirmed``,超限
    读数须双帧一致才采信——超限是持续态、误读是瞬态),占用 > 上限 →
    ``(False, detail)`` 出战未发出 + 受阻回执行(披露行),交回外循环重观察
    重决策(连续失败由外循环重派上限治理)。

    - 不超限 / X 或 cap 任一不可读 → ``(True, '')`` 放行(不可判 ≠ 超限;
      不因读链抖动拦合法出战);
    - **零策略语义**:只回答「此刻能不能点」;撤谁 / 卖谁 / 是否升上限解限
      = 「该做哪个动作」归策略层(铁律 §1.3 决策控制分层),守卫不发任何
      解限动作——超限态在策略侧解限动作落地前表现为停在备战(每帧
      round_fail 交回),如实申报;
    - sim 零触及(机械 IO 门内才检查;sim 画面无「X/Y」计数,读即假拦)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        game_state_from_ctx,
    )
    from sr_od.application.currency_war.obs.cw_observation import (
        read_paddle_pair_confirmed,
    )
    from sr_od.application.currency_war.sim import cw_sim_ports
    if not cw_sim_ports.mechanical_io_allowed():
        return True, ''
    screen = op.screenshot()
    if screen is None:
        return True, ''   # 截图不可得 = 不可判,同失读放行
    size_used, cap = read_paddle_pair_confirmed(ctx, screen)
    if size_used is None or cap is None or size_used <= cap:
        return True, ''
    gs = game_state_from_ctx(ctx)
    _aura = gs.chosen_aura.value if gs is not None else None
    detail = (f'未执行:团队规模超限(规模占用 {size_used} > 上限 {cap};'
              f'此时出战被游戏静默拒绝,须先让占用 ≤ 上限〔撤/卖场上单位或'
              f'升上限,归策略侧〕)')
    log.warning('[cw!][battle] 规模超限守卫:占用 %d > 上限 %d(双帧确认;'
                '光环=%s)→ 出战未发出,交回外循环(解除归策略侧)',
                size_used, cap, _aura)
    ex.note_blocked(CwActionStartBattleParam(), detail, extra={
        'blocked': 'team_size_over_cap',
        'team_size_used': int(size_used),
        'deploy_cap': int(cap),
        'chosen_aura': _aura,
    })
    return False, detail


def launch_prepared_battle(op, ctx, *, sync_once: bool = False):
    """出战底层动作发出核(C1 单一发出函数,skill strategy/14_p1_consume_arms.md §9.6):部署原子序 +
    CwActionStartBattleParam 的执行核,恢复局面与达标分支两调用面共用,禁各写一套
    CwActionStartBattleParam 动作发出点。

    - ``sync_once=True``(恢复局面面,调用面 = locked_resume_sync_and_
      battle):首战前插备战同步步,**发出即置位**证据位
      ``ctx.cw_match.locked_sync_done``(回执已停用,失败概念随之消解);
      锁定确认分支复位证据位。同步步载体 = 统一拖动/换星直卖原子序
      (按策略层部署计划现算逐 move 发;恢复局卖出通道整体跳过语义
      不变——board 未观察时计划恒空)。
    - ``sync_once=False``(达标分支面,调用面 = 策略层前置动作发出点):
      **不过标志**——每达标帧都部署原子序 + CwActionStartBattleParam(部署面现读重建,
      已同步形态下零 move 即零待部署;标志只覆盖恢复局面,达标分支第二次发出
      被「每局恰一次」标志拦截 = C1 明令防的双源病)。

    返回 ``(launch_ok, detail)`` = 出战**点击已执行**(出战域重设计
     收缩语义,单击原子;执行器 last_launch_ok 旁路;False = 找不到按钮/area
    缺失/席满腾位守卫失败等未执行形态——旧「动作发出点内部事实」判效面
    随 op 重写停用,结束后画面状态由外循环下一帧重判)。
    刹车短路(停机标志
    已设)→ 返回 (False, '已停止[W209j刹车]'),返回主循环由 loop 顶退出。

    执行序 = 部署原子序 → 席满守卫(:func:`guard_bench_overflow_for_battle`,
    两 face 共同生效;失败 = ``(False, detail)`` 零出战交回外循环)→ 团队
    规模超限守卫(:func:`guard_team_size_over_cap_for_battle`,同上)→ 出战单击。
    """
    ex = PrepActionExecutor(op, ctx)
    try:
        _moves = []
        if sync_once:
            # 证据位宿主 = Match.locked_sync_done(备战交互链迁移):读侧
            # Match 缺席/字段缺按 False 容缺(同旧 op 属性 getattr 容缺语义)。
            _m_lpb = getattr(ctx, 'cw_match', None)
            if not getattr(_m_lpb, 'locked_sync_done', False):
                _sess_lpb = getattr(_m_lpb, 'session', None) \
                    if _m_lpb is not None else None
                _moves = (_battle_chain_deploy_moves(_sess_lpb)
                          if _sess_lpb is not None else [])
                for _mv in _moves:
                    ex.execute(_mv)   # 机械执行无返回
                # 发出即写(申报;回执已停用,失败概念消解)。写侧 Match 缺席
                # 结构性不可达:本入口仅经 locked_resume=True 门可达,该置位
                # 蕴含 Match 在场。
                _m_lpb.locked_sync_done = True
                log.info('[cw-loop] 恢复局备战同步步(部署原子×%d)已发出: %s',
                         len(_moves), getattr(ex, 'last_detail', ''))
            else:
                log.debug('[cw-loop] 恢复局同步步已置位,跳过部署原子序')
        else:
            # 达标分支面:每帧部署原子序(部署面现读重建;已同步形态零 move)
            _m_lpb = getattr(ctx, 'cw_match', None)
            _sess_lpb = getattr(_m_lpb, 'session', None) \
                if _m_lpb is not None else None
            _moves = (_battle_chain_deploy_moves(_sess_lpb)
                      if _sess_lpb is not None else [])
            for _mv in _moves:
                ex.execute(_mv)
            log.info('[cw-loop] 达标臂部署原子序 ×%d: %s',
                     len(_moves), getattr(ex, 'last_detail', ''))
        # —— 出战前置席满守卫(两 face 汇合点;部署原子序先行,部署可能
        #      移动 bench 单位改变席位占用,守卫按部署后的画面现读判定):
        #      告警在场 → 先卖腾位再出战;守卫失败 = 出战未发出交回外循环
        #      (发了必被游戏静默忽略,伪装成功会让外循环白等战斗窗)。
        _guard_ok, _guard_detail = guard_bench_overflow_for_battle(op, ctx,
                                                                   ex)
        if not _guard_ok:
            return False, _guard_detail
        # —— 出战前团队规模超限守卫(同汇合点,席满守卫之后:两守卫互斥于
        #      画面形态——席满横幅在场时先腾位;超限态无横幅,由「X/Y」
        #      双帧确认判定):占用 > 上限 → 出战未发出(发了必被游戏静默
        #      拒绝且逻辑态假前进)+ 受阻回执披露行,解除归策略侧。
        _size_ok, _size_detail = guard_team_size_over_cap_for_battle(op, ctx,
                                                                     ex)
        if not _size_ok:
            return False, _size_detail
        ex.execute(CwActionStartBattleParam())
    except StopBrakeShortCircuit as e:
        log.info('[cw-loop] 停机刹车(%s)→ 出战链动作未发出,交回外循环', e)
        return False, '已停止[W209j刹车]'
    # CwActionStartBattleParam 出战点击事实(出战域重设计收缩语义,单击原子;
    # getattr 容缺 = __new__/桩形态兼容)
    return bool(getattr(ex, 'last_launch_ok', False) or False), \
        getattr(ex, 'last_detail', '')


# (达标分支 G1 准入预估 readiness_admission_report 与 deploy_swap_no_victim
#  计数位已随部署统一批丁并入统一结构而删除:统一部署搜索下板满帧经交换交互上场,
#  「无合格 victim → 出战无腾位」形态结构性不存在——unified-deploy-order
# M4 姊妹出口行;victim 资格判据面的纳入统一管理随 kernel swap 机器批)


def launch_battle_unified(op, ctx, *, face: str) -> tuple[bool, str]:
    """出战统一执行器(armed/resume 两调用面共用)。

    内部序 = face 分轨(部署原子序)→ CwActionStartBattleParam 执行。
    失败语义按调用面分轨:本函数只返回事实 ``(launch_ok, detail)``,
    计数与复位归调用方(禁调用面私有记账入本函数)。

    :param face: ``'armed'``(达标分支面:G1 准入预估暴露 + 部署原子序每帧
        现算不过标志)| ``'resume'``(恢复局面面:标志覆盖部署原子序一次)。
    执行前屏态复验/浮层闸门已退役(2026-11-19 用户裁定,待跟进事项 §二.7⑤):
    错屏/浮层下的误发出由阶段一身份分发(每帧)+ drag 浮层守卫 + 调用方
    retry 网承接;动作落地判定归观察侧 reconcile(既有)。
    """
    if face not in ('armed', 'resume'):
        raise ValueError(f'未知调用面: {face!r}(合法 = armed/resume)')
    if face == 'armed':
        return launch_prepared_battle(op, ctx, sync_once=False)
    return launch_prepared_battle(op, ctx, sync_once=True)
