"""货币战争 **后排槽位布局**(可变槽位;2026-08-19 用户口述 + 狸猫局实拍)。

机制:后排槽数 = **max(6, deploy_cap)**(五组实测:cap5→后6[lv4+1宝钻,暗框格点=
基线 585-1174+花火/姬子命中]/cap8→后8/cap9→后9/cap10→后10/cap11→后11;后排基础
6 槽,cap≤6 钳制 6,cap>6 跟 cap 走 —— r81 裁定)。cap = level+宝钻(部署上限)。
布局 = 固定坐标格点(间距 142)上按槽数开窗;**狸猫兄弟等固定召唤单位是固定坐标
(1316/1458),不随槽数移动**(9/11 槽局其右侧有空槽实证)。

**单一真相源 = screen_info**(用户 2026-08-19 定调:槽位都记录到 screen_info):
- 基准 6 槽:``货币战争-备战`` 的 ``后排-1..6``(基线,多局验证)。
- 8 槽:``后排8槽-1..8``(狸猫局实拍,qwen grounding + 交互定名:位1藿藿/位2爻光/
  位7蓝狸小虎/位8红狸猫;2026-08-19 23:31)。
- 7 槽:**待实拍**(遇到按同法采:upsert ``后排7槽-1..7``)。

选档:运行时按 ``deploy_cap``(OCR 部署数 X/Y 的 Y,含宝钻加成)取布局前缀;查无该档
→ 退 6 槽基线 + ``[cw!]`` 告警(遇该局实拍补档)。**别在 6 槽坐标上外插**(重排机制下
等间距假设不成立)。
"""
from __future__ import annotations

from one_dragon.base.geometry.rectangle import Rect

#: deploy_cap → screen_info 布局前缀(6 槽 = 基线「后排-N」;其余 = 「后排N槽-N」)
#: 全档闭环(r84,6-11):格点模型 = 固定坐标格点(间距 142)上**交替右左扩窗**(从 6 槽
#: [606..1316] 起:7=右+1458/8=左+464/9=右+1600/10=左+322/11=右+1742 —— 六档窗口
#: 全部与格点吻合,7 槽右+1 由「464 处无暗框无占用 + 1458 附近空槽」双证据裁定)。
#: 狸猫兄弟等固定召唤单位 = 固定坐标(1316/1458),不随槽数移动。
_LAYOUT_PREFIX: dict[int, str] = {
    6: '后排',
    7: '后排7槽',
    8: '后排8槽',
    9: '后排9槽',
    10: '后排10槽',
    11: '后排11槽',
}

#: 未实拍档(用户口径 2026-08-22:只有 8 后台做过狸猫局实拍级建档——qwen
#: grounding+交互定名;6=多局基线;**7/9/10/11 系格点推导/暗框级,遇到该档
#: 局需留证采集实拍验证**)。消费方:prep_director 的 cap 域检查分支——
#: cap 落入未实拍档时 obs_conflict 留证(处理步骤见 verdict),供判读人
#: 顺带实拍(upsert 校正后从此集合移除)。
_UNVERIFIED_BACK_SLOTS: frozenset[int] = frozenset({7, 9, 10, 11})

#: 后排 y 带(所有布局共用;槽 rect 高约 600-739)
_BACK_Y1, _BACK_Y2 = 600, 739


def _layout_prefixes() -> dict[int, str]:
    """screen_info 里实际存在哪些布局档(动态发现:「后排N槽-」前缀扫描)。"""
    # 静态表为主;动态发现由消费方 ctx 驱动(此处保持纯函数,screen_info 变更走 CRUD 后
    # _LAYOUT_PREFIX 需同步登记——7 槽补档时加一行)
    return dict(_LAYOUT_PREFIX)


def effective_back_slots(cap: int) -> int:
    """后排实际槽数(r81 裁定):``max(6, cap)``。

    五组实测:cap5→后6(lv4+1宝钻,暗框格点=基线+花火/姬子SIFT命中)/cap8→8/cap9→9/
    cap10→10/cap11→11 —— 后排基础 6 槽,cap≤6 钳制 6(P1 低等级局基线恒对的原因),
    cap>6 跟 cap 走。消费方(选档/停机守卫)统一过此函数。
    """
    return max(6, cap)


def back_row_slot_rects_ctx(ctx, cap: int) -> list[tuple[int, Rect]] | None:
    """按 deploy_cap 从 screen_info 取 ``[(slot_idx, rect), ...]``;无档 → None(调用方退基线)。

    ctx: ``SrContext``(screen_info 已加载)。cap = 部署上限真值(read_deploy_cap);
    槽数 = ``effective_back_slots(cap)``(max(6,cap),r81)。
    """
    prefix = _layout_prefixes().get(effective_back_slots(cap))
    if prefix is not None:
        from sr_od.application.currency_war.cw_identity_obs import _area_rect
        out: list[tuple[int, Rect]] = []
        i = 1
        while True:
            rect = _area_rect(ctx, f'{prefix}-{i}')
            if rect is None:
                break
            out.append((i, rect))
            i += 1
        if out:
            return out
    # 无档:[cw!] 告警(可检索);停机钩子在调用方 read_deployed_chars(r77d:存帧+flag+
    # stop_running,现场拖角色逐位验证后补档 —— 真值坐标必须现场交互闭环,离线暗框检测
    # 有 grounding 误换算教训)。本函数只返 None 退基线。⚠️ cap≤6 → 恒基线(r81),无告警。
    try:
        if cap and effective_back_slots(cap) not in _layout_prefixes():
            from one_dragon.utils.log_utils import log
            log.warning('[cw!][layout] 后排 %d 槽布局未建档(退 6 槽基线,识别/拖拽将错位;'
                        '停机钩子将触发现场验证;补档:拖角色逐位验 → upsert 后排%d槽-1..%d'
                        ' → _LAYOUT_PREFIX 登记)', cap, effective_back_slots(cap),
                        effective_back_slots(cap))
    except Exception:   # noqa: BLE001
        pass
    return None


def fallback_back_slots() -> list[tuple[int, Rect]]:
    """无 ctx/无档时的兜底:静态 6 槽基线(与 screen_info 基线一致的硬拷贝;仅测试用)。"""
    xs = (604, 746, 888, 1032, 1173, 1315)
    half = 71
    return [(i + 1, Rect(x - half, _BACK_Y1, x + half, _BACK_Y2)) for i, x in enumerate(xs)]
