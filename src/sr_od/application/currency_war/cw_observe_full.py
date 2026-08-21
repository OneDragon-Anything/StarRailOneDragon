"""observe_full:一次全面识别的组装层(ADR-0213 批次1)。

设计定案(方案 v4,五轮对抗 review 收敛):
- 签名 ``observe_full(ctx, frame, *, tier, source)``——tier=
  heavy/light;source='director'/'deploy_bench'(reconcile
  审计归因保留);
- **替换范围=_observe 的 heavy 段(prep_director L209-277)**;
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


from sr_od.application.currency_war.cw_identity_obs import (
    ensure_portrait_templates,
    read_bench_chars,
    read_deployed_chars,
)
from sr_od.application.currency_war.cw_observation import (
    read_game_state,
    read_node_sequence,
    read_shop_cards,
)


def observe_full(ctx: SrContext, frame: MatLike, *, tier: str,
                 source: str, op=None) -> dict:
    """对已稳定 frame 做全面识别(heavy 段组装;dict 形态过渡)。

    返回字段(对齐 _observe heavy 段产出,消费方=director 回填):
    - bench_chars/deployed_chars:SIFT 身份(templates 未加载
      → None,调用方沿用缓存);
    - state:GameState(read_game_state);
    - gold_reread:bool——是否走了 MED-2 gold==0 重读
      (**重新截图**重读——同帧重读结果恒同,无意义;
      op 可传则用 op.screenshot(),不可传(离线)跳过重读);
    - substate:dict 标注各模块可读性(node_seq/shop_cards)。

    本函数纯组装:session 写/缓存回填由 director 做(单写者
    原则,批次3 收敛);reconcile 经 director 的既有回调链
    (source 已传入,star 防抖/obs_conflict 由 director 在回填
    时调用——避免组装层持 session 双写)。
    (r331:import 提模块级——测试 monkeypatch 按模块属性打桩。)
    """
    out: dict = {'tier': tier, 'source': source, 'gold_reread': False}
    if tier == 'heavy':
        templates = ensure_portrait_templates(ctx)
        if templates is not None:
            out['bench_chars'] = read_bench_chars(ctx, frame, templates)
            out['deployed_chars'] = read_deployed_chars(ctx, frame, templates)
        else:
            out['bench_chars'] = None
            out['deployed_chars'] = None
        st = read_game_state(ctx, frame)
        # MED-2 gold==0 重读(OCR 弱点;帧稳定≠OCR 稳定——
        # stylized 间歇漏与帧稳定正交,重读是第二道)。
        # ⚠ 重读=**重新截图**(同帧重读结果恒同);
        # op 不可用(离线)时跳过(返原值)。
        import time
        if st.gold == 0 and op is not None:
            for _ in range(3):
                time.sleep(0.3)
                try:
                    st2 = read_game_state(ctx, op.screenshot())
                except Exception:   # noqa: BLE001  离线契约
                    break
                if st2.gold > 0:
                    st = st2
                    out['gold_reread'] = True
                    break
        out['state'] = st
        # 子态尽力读(A5:标注可读性,不强行全读)
        out['substate'] = {
            'node_seq': read_node_sequence(ctx, frame) is not None,
            'shop_cards': read_shop_cards(ctx, frame) != [],
        }
        log.info('[cw][observe_full] tier=%s source=%s '
                 'bench=%s deployed=%s gold=%d substate=%s',
                 tier, source,
                 len(out['bench_chars'] or []),
                 len(out['deployed_chars'] or []),
                 st.gold, out['substate'])
    else:
        out['state'] = read_game_state(ctx, frame)
        out['substate'] = {}
    return out
