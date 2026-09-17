"""部署动作 op(DeployMoveOp)——备战域动作文件(统一动作工厂批3 体迁:
体自 ``prep_actions.py::PrepActionExecutor._deploy_move`` 逐字迁移,原
方法改薄委托保持替身缝,design.md unified-action-factory §2.4)。

bench → 上阵单步拖拽(腾席链专用;R2 原子通路发射形态 = 决策核逐帧
按 kernel 计划逐 move 发本动作)。非终结。

拖后落位像素验证(T-22):拖拽是 UI 动作,存在静默不生效形态(输入被
游戏吞;实机 run 20260918 02:40:20 实证同路径一次生效一次未落场)。投影
契约「发出即写」×静默未生效 = 逻辑态失真,下一备战帧 heavy 实读必失配
→ 安灯停机(board/bench/front_row 三行连发形态)。本 op 拖后对目标槽
区域做像素验证,零变化 = 未生效 → 置
``GameState.exec_books.deploy_miss_pending`` 申报闩(消费端 =
``cw_game_state.consume_deploy_miss_mark``,投影写端跳写),tracked 与
容器/黑板一致保持事实,重试 = 决策循环自然重派。验证只采集申报事实,
不做重试治理(B1 拆除裁定「落地判定归观察侧」的观察侧即本申报闩的消费
链,机械执行零回执语义不变)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_game_state import (
    DeployMissMark,
    game_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import DeployMove
from sr_od.application.currency_war.operations.cw_op.cw_action_base import (
    ActionOp,
)

if TYPE_CHECKING:
    import numpy as np

    from one_dragon.base.geometry.point import Point
    from sr_od.application.currency_war.prep_actions import PrepExecEnv

#: 落位像素验证阈值(区域均值绝对差;与 prep_actions._wait_stable_frame
#: 的「画面稳定」判据同量级——拖拽未生效时画面静止 diff≈0,生效时目标
#: 槽出现单位立绘 diff 远超阈值,中间态罕见)。阈值偏低取向:误判
#: 「生效→未生效」会让黑板滞后一帧由入口 heavy 纠正,误判反向则退回
#: 安灯停机形态,宁可漏报不可错报。
DEPLOY_LAND_DIFF_THRESHOLD: float = 2.0


def _region_changed_px(pre: np.ndarray, post: np.ndarray,
                       center: Point) -> bool:
    """目标槽区域像素变化判定(拖拽落地的可见性证据;纯函数)。

    区域 = 以落位中心为核的半槽矩形(1080p 槽位 ~128x138,固定偏移足够
    承载「区域是否出现大目标」判定);两帧形状不一致/区域越界退化 = 不
    判失败(返回 True 按已落地走现行为——验证只在两帧齐备时发声,缺证
    不改变既有语义)。
    """
    try:
        import numpy as np
        h, w = pre.shape[:2]
        if post.shape[:2] != (h, w):
            return True
        x1 = max(0, int(center.x) - 60)
        x2 = min(w, int(center.x) + 60)
        y1 = max(0, int(center.y) - 65)
        y2 = min(h, int(center.y) + 65)
        if x2 <= x1 or y2 <= y1:
            return True
        diff = float(np.abs(pre[y1:y2, x1:x2].astype('int16')
                            - post[y1:y2, x1:x2].astype('int16')).mean())
        return diff >= DEPLOY_LAND_DIFF_THRESHOLD
    except Exception:   # noqa: BLE001  验证失败不改变拖拽语义(保守放行)
        return True


class DeployMoveOp(ActionOp):
    """bench → 上阵单步拖拽(腾席链专用;统一词表 DeployMove)。非终结。"""

    def execute(self, env: PrepExecEnv) -> bool:
        """bench → 上阵单步拖拽(腾席链专用;统一词表 DeployMove)。

        执行坐标边:源拖点 = ``bench_idx`` 备战栏 area 序直取(容器下标 =
        area 序,零换算);落位排 = ``to_row``,落位物理槽 = tracked 占用
        现读首空位(kernel ``empty_deploy_slots`` 单一源,与发射位
        ``assign_deploy_slots`` 选排规则逐位同构——首选排满 fallback 另一排)。
        两排全满 = 未发出(False,观察重派);faction 字段不入执行(sim
        board 计数消费)。

        拖后落位像素验证(置位端;语义见模块头):未生效 → 置申报闩 +
        tracked 保持事实(不记上阵),容器/黑板投影由消费端跳写。
        """
        action: DeployMove = self.action
        ex = env.executor
        match = ex._ctx.cw_match
        session = match.session if match is not None else None
        if session is not None:
            # 旧闩清位:任何路径的部署动作都不消费上一动作的申报(闩 =
            # 单动作窗;陈旧闩另由消费端动作匹配校验双保险兜住)。
            game_state_of(session).exec_books.deploy_miss_pending = None
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            empty_deploy_slots,
        )
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_deployed,
        )
        tracked = (pad_deployed(list(
            game_state_of(session).tracked_books.deployed))
            if session is not None else [])
        front_empty, back_empty = empty_deploy_slots(
            tracked, front_total=len(ex._front_pts),
            back_total=max(1, len(ex._back_pts)))
        chosen, fallback = ((front_empty, back_empty)
                            if action.to_row == 'front'
                            else (back_empty, front_empty))
        if chosen:
            row, slot_no = action.to_row, chosen[0]
        elif fallback:
            row = 'back' if action.to_row == 'front' else 'front'
            slot_no = fallback[0]
        else:
            env.detail, env.emitted = \
                '部署落位无空槽(两排全满,观察重派)', False
            return True
        src = ex._bench_pts[action.bench_idx]
        dst = (ex._front_pts if row == 'front' else ex._back_pts)[slot_no - 1]
        # 拖前目标槽基线(拖后像素验证对照面;取帧异常由 _region_changed_px
        # 保守放行兜住,不影响拖拽本体)。
        _pre = ex._op.screenshot()
        ex._drag(src, dst)
        # 用户口述口径(screen_flow_timing.md #10,2026-09-02):拖动触发
        # 羁绊阶段变更时角色头顶徽章动画 ~2s——拖完立即返回会让批尾
        # heavy 观察打在徽章动画帧上(SIFT/对账读脏,「对账纠漂」日志
        # 噪声源之一)。按「都等 2s」简单方案落(批尾/中间的区分不做)。
        time.sleep(2.0)
        # 用户口述口径(#24,2026-09-02):羁绊达标触发的 overlay(盛会之星
        # 等)在徽章动画后再 ~2s 才弹出——固定等待覆盖不住。执行端等待后
        # 快查一次触发型 overlay 锚(模板毫秒级),命中 → detail 标注(拖拽
        # 本身已发出);批尾 heavy 的 event_overlay 检测将看到它并 bail 交
        # 外环 handler——防「decide 的下一步动作打在 overlay 上」。清单
        # 可扩(圣杯/银狼升星等实测出现时加锚)。
        _post = ex._op.screenshot()
        _overlay = ex._op.round_by_find_area(
            _post, '货币战争-盛会之星', '标识-盛会之星',
            crop_first=False).is_success
        if _overlay:
            log.info('[cw][deploy] 拖后检出盛会之星 overlay(羁绊达标触发)')
        # 落位判定:overlay 命中 = 羁绊由拖入触发的强正证据;像素验证采集
        # 「目标槽是否出现变化」的可见性事实。
        _landed = _overlay or _region_changed_px(_pre, _post, dst)
        if _landed:
            ex._track_move_deployed(action.bench_idx, row, slot_no)
        else:
            # 拖拽静默未生效(目标槽像素零变化 = 游戏侧无任何可见变化):
            # 置申报闩 + tracked 保持事实(单位仍记在备战席),容器/黑板
            # 投影由消费端跳写——逻辑态恒真,重试 = 决策循环自然重派。
            _cid = ''
            if session is not None:
                from sr_od.application.currency_war.kernel.cw_exec_state import (
                    pad_bench,
                )
                _gs = game_state_of(session)
                _bench = pad_bench(list(_gs.tracked_books.bench or []))
                _bc = (_bench[action.bench_idx]
                       if 0 <= action.bench_idx < len(_bench) else None)
                _cid = str(getattr(_bc, 'char_id', '') or '') \
                    if _bc is not None else ''
                _gs.exec_books.deploy_miss_pending = DeployMissMark(
                    bench_idx=int(action.bench_idx), to_row=row, char_id=_cid)
            log.warning('[cw!][deploy] 拖后目标槽像素零变化 → 判拖拽未生效'
                        '(单位 %s,申报闩已置,投影跳写,决策循环重派)', _cid)
        if _overlay:
            env.detail, env.emitted = \
                ('部署已发,盛会之星 overlay 弹出(外环接管)', True)
            return True
        env.detail = (f'部署槽{action.bench_idx + 1}→{row}{slot_no} ✓'
                      if _landed else
                      f'部署槽{action.bench_idx + 1}→{row}{slot_no} 未生效'
                      f'(投影跳写)')
        env.emitted = True
        return True
