"""observe_full:一次全面识别的组装层(ADR-0213 批次1)。

设计定案(方案 v4,五轮对抗 review 收敛):
- 签名 ``observe_full(ctx, frame, *, tier, source)``——tier=
  heavy/light;source='director'/'deploy_bench'(reconcile
  审计归因保留);
- **替换范围=_observe 的 heavy 段(cw_screen_prep L209-277)**;
  轻字段读留 _observe(每步现读);
- 副作用归属:session 写留 director;MED-2 gold==0 重读进
  本层(帧稳定≠OCR 稳定);_cached_* 回填留 director;
  reconcile/star 防抖/obs_conflict 进本层(source 保归因);
- 「按子态尽力读」:shop 开态时 node_reader 返 None(圆数
  门)、关态时 shop_cards 返 []——substate 字段显式标注
  读了哪些,全面性由决策环跨步拼装(A5)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from cv2.typing import MatLike

from one_dragon.utils.log_utils import log

if TYPE_CHECKING:
    from sr_od.context.sr_context import SrContext


from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    _area_rect,
)
from sr_od.application.currency_war.obs.cw_back_layout import (
    select_back_layout,
)
from sr_od.application.currency_war.obs.cw_equipment import (
    ensure_equip_sift_templates,
    ensure_equip_tm_templates,
    read_equips,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    ensure_portrait_templates,
    read_bench_view,
    read_deployed_rows,
    read_row_equipped,
)
from sr_od.application.currency_war.obs.cw_observation import (
    read_game_state,
    read_node_sequence,
    read_shop_cards,
)


def _bench_occ_n(view) -> int:
    """日志计数:容器视图占用槽数(与旧 len(bench_chars) 同口径:占用条目数)。"""
    if view is None:
        return 0
    return sum(1 for s in view.slots if s.kind != 'empty')


def _rows_n(rows) -> int:
    """日志计数:上场位两行合计条目数(与旧 len(deployed_chars) 同口径)。"""
    if rows is None:
        return 0
    return len(rows[0] or []) + len(rows[1] or [])


def observe_full(ctx: SrContext, frame: MatLike, *, tier: str,
                 source: str, op=None, shop_open: bool = False,
                 session=None) -> dict:
    """对已稳定 frame 做全面识别(heavy 段组装;dict 形态过渡)。

    返回字段(对齐 _observe heavy 段产出,消费方=director 回填):
    - bench_view/deployed_rows:备战席容器视图(BenchView,空读/未加载模板
      → None)+ 上场位 (前排, 后排) Unit 行(P6 观察链直产,无中间形;
      调用方按 None/空读走 carried);
    - read_receipt::class:`GameStateReadReceipt`(read_game_state 轻量
      回执;逐帧读数消费面——节点类型/level 审计/raw 牌缓存——改走本回执);
    - gold_reread:bool——是否走了 MED-2 gold==0 重读
      (**重新截图**重读——同帧重读结果恒同,无意义;
      op 可传则用 op.screenshot(),不可传(离线)跳过重读);
    - substate:dict 标注各模块可读性(node_seq/shop_cards);
    - owned_equips/occupied_equips/back_layout_slots:装备域三路
      采集(P4 观察接线;None = 识别域资源未就绪,语义见
      kernel/cw_prep_actions.PrepObservation 装备域字段块)。

    本函数纯组装:session 写/缓存回填由 director 做(单写者
    原则,批次3 收敛);reconcile 经 director 的既有回调链
    (source 已传入,star 防抖/obs_conflict 由 director 在回填
    时调用——避免组装层持 session 双写)。
    (r331:import 提模块级——测试 monkeypatch 按模块属性打桩。)
    session(P4R4 漏斗批):传入局 session 时 bench/deployed 身份识别
    走三层漏斗(session 优先匹配;状态挂 session,不引入全局);
    None = 旧全库路径(离线/测试零变化)。
    """
    out: dict = {'tier': tier, 'source': source, 'gold_reread': False}
    if tier == 'heavy':
        # 装备域 owned/occupied 采集结果先置缺省:键恒在场(契约稳定,
        # 消费方按 None 判读识别域未就绪),采到再覆盖。
        out['owned_equips'] = None
        out['occupied_equips'] = None
        out['back_layout_slots'] = None
        templates = ensure_portrait_templates(ctx)
        if templates is not None:
            if session is not None:
                from sr_od.application.currency_war.obs.cw_identity_obs import (
                    read_bench_view_tiered,
                    read_deployed_rows_tiered,
                )
                out['bench_view'] = read_bench_view_tiered(
                    session, ctx, frame, templates)
                out['deployed_rows'] = read_deployed_rows_tiered(
                    session, ctx, frame, templates)
            else:
                out['bench_view'] = read_bench_view(ctx, frame, templates)
                out['deployed_rows'] = read_deployed_rows(ctx, frame, templates)
        else:
            out['bench_view'] = None
            out['deployed_rows'] = None
        # screen_name = 备战画面建档名(heavy 段宿主 = 备战画面 op 入口;
        # 店开子态帧传开商店建档名,失配豁免精确键观察侧维度)
        _st = read_game_state(ctx, frame,
                              screen_name=(SHOP_SCREEN_NAME if shop_open
                                           else SCREEN_NAME))
        # MED-2 gold==0 重读(OCR 弱点;帧稳定≠OCR 稳定——
        # stylized 间歇漏与帧稳定正交,重读是第二道)。
        # ⚠ 重读=**重新截图**(同帧重读结果恒同);
        # op 不可用(离线)时跳过(返原值)。
        # r334(review 第5条:恢复 F2 门)——gold 仅 shop 开态
        # 可信(关态读空恒 0):重读也只在开态做,否则每个
        # 关态 heavy 白付 3×0.3s+3 次全量 OCR(系统性变慢)
        # 且换入的帧来自 0.3-0.9s 后异帧(轮转窗内 board
        # 可回退)。shop_open 由调用方传(它有帧上下文)。
        import time
        if _st.gold == 0 and op is not None and shop_open:
            for _ in range(3):
                time.sleep(0.3)
                try:
                    _st2 = read_game_state(ctx, op.screenshot(),
                                           screen_name=SHOP_SCREEN_NAME)
                except Exception:   # noqa: BLE001  离线契约
                    break
                if _st2.gold > 0:
                    _st = _st2
                    out['gold_reread'] = True
                    break
        out['read_receipt'] = _st
        _node_slots = read_node_sequence(ctx, frame)
        # 链观察落地批:slots 回传 director 写现行链(原读完即弃;组装层
        # 单写者原则,写容器归 director 侧)。
        out['node_slots'] = _node_slots
        out['substate'] = {
            'node_seq': _node_slots is not None,
            'shop_cards': read_shop_cards(ctx, frame) is not None,
        }
        # ===== 装备域 owned/occupied 采集(P4 观察接线)=====
        # 归位备战画面 op 入口观察链(heavy = 唯一读屏点):原分发段
        # prep_actions._build_equip_wear_plan 现读三路退役,识别函数本体
        # (read_equips/read_row_equipped)复用,迁移的是调用位置;deployed
        # 名单已由上方身份半采集,此处补 owned/occupied 两路。None = 识别
        # 域资源未就绪(原因 log 留证),消费方(计划产出位)按 None 走
        # fail 通道;[]/{} = 真读到空。后排布局未知态(select_back_layout
        # 双弃权帧)→ 后排不采集,宁缺勿造(同读侧 read_deployed_rows
        # 单帧未知只返前排的跳过先例)。
        _eq_sift = ensure_equip_sift_templates(ctx)
        # rect 读取须 ctx.screen_loader 在场(资源缺省帧跳过,防误触)
        _eq_rect = (_area_rect(ctx, '区域-道具装备', SCREEN_NAME)
                    if _eq_sift is not None else None)
        if _eq_sift is None:
            log.warning('[cw][observe_full] 装备观察域未就绪:'
                        'cw_equip 模板库未加载(owned 不采集)')
        elif _eq_rect is None:
            log.warning('[cw][observe_full] 装备观察域未就绪:'
                        'screen_info 区域-道具装备 缺失(owned 不采集)')
        else:
            _eq_rect4 = (_eq_rect.x1, _eq_rect.y1, _eq_rect.x2, _eq_rect.y2)
            out['owned_equips'] = [
                n for n, _p, _s in read_equips(frame, _eq_sift,
                                               equip_rect=_eq_rect4)]
        _eq_grays = ensure_equip_tm_templates(ctx)
        if _eq_grays is None:
            log.warning('[cw][observe_full] 装备观察域未就绪:'
                        'cw_equip TM grays 未加载(occupied 不采集)')
        else:
            _bk_n, _bk_pfx = select_back_layout(ctx, frame)
            out['back_layout_slots'] = _bk_n
            _occ: dict = {}
            for _row, _pfx, _n in (('front', '前排', 4),
                                   ('back', _bk_pfx, _bk_n)):
                if not _pfx or not _n:
                    continue   # 布局未知态:该排不采集(见上方块注)
                for _slot, _names in read_row_equipped(
                        ctx, frame, _eq_grays, _pfx, _n).items():
                    _occ[(_row, int(_slot))] = list(_names)
            out['occupied_equips'] = _occ
        log.info('[cw][observe_full] tier=%s source=%s '
                 'bench=%s deployed=%s gold=%d substate=%s '
                 'owned=%s occupied=%s',
                 tier, source,
                 _bench_occ_n(out['bench_view']),
                 _rows_n(out['deployed_rows']),
                 _st.gold, out['substate'],
                 len(out['owned_equips'] or []),
                 len(out['occupied_equips'] or {}))
    else:
        out['read_receipt'] = read_game_state(
            ctx, frame, screen_name=SCREEN_NAME)   # 容器直写即产物
        out['substate'] = {}
    return out
