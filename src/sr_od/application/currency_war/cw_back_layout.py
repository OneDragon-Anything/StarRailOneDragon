"""货币战争 **后排槽位布局**(可变槽位;2026-08-19 用户口述 + 狸猫局实拍)。

机制:后排槽位数 = 基准 6 + 财富宝钻(+1 团队规模,可叠加宝钻数)/ 诅咒·宝石剑泽尔里奇(−1);
**槽位增减时旧槽物理位置不动、新槽加在两端、编号平移**(2026-08-19 狸猫局暗框检测核实:
8 槽 = [464,606,748,889,1031,1174,1316,1458],其中位2-7 ≈ 6 槽基线的位1-6 同位;
**早前"整体重排"结论是 grounding 换算错误的误判,已纠正**——但「不能在 6 槽坐标上
外插/硬编码」的结论不变:编号平移本身就会让「后排-N」语义错位)。

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
#: 8 槽(2026-08-19 狸猫局交互实锤)/9 槽(2026-08-20 双宝钻局实锤)/10 槽(2026-08-20
#: lv8+双宝钻局实锤:拖藿藿 2→4 验证布局假设 + 狸猫最右两位 8/9);等差 142,两端扩
_LAYOUT_PREFIX: dict[int, str] = {
    6: '后排',
    8: '后排8槽',
    9: '后排9槽',
    10: '后排10槽',
}

#: 后排 y 带(所有布局共用;槽 rect 高约 600-739)
_BACK_Y1, _BACK_Y2 = 600, 739


def _layout_prefixes() -> dict[int, str]:
    """screen_info 里实际存在哪些布局档(动态发现:「后排N槽-」前缀扫描)。"""
    # 静态表为主;动态发现由消费方 ctx 驱动(此处保持纯函数,screen_info 变更走 CRUD 后
    # _LAYOUT_PREFIX 需同步登记——7 槽补档时加一行)
    return dict(_LAYOUT_PREFIX)


def back_row_slot_rects_ctx(ctx, cap: int) -> list[tuple[int, Rect]] | None:
    """按 deploy_cap 从 screen_info 取 ``[(slot_idx, rect), ...]``;无档 → None(调用方退基线)。

    ctx: ``SrContext``(screen_info 已加载)。cap = 部署上限真值(read_deploy_cap)。

    r77c 采集钩子:cap 无档(如 7/9 槽,宝钻叠加局)→ 存帧到 shots/(内容哈希去重)+
    进度记一笔,**不停机**(布局坐标离线可测,暗框法即可,无需保画面交互);下次遇该
    布局 AI 离线 upsert 后排N槽-1..N + 本表登记即闭环。
    """
    prefix = _layout_prefixes().get(cap)
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
    # 有 grounding 误换算教训)。本函数只返 None 退基线。
    try:
        if cap and cap > 4:
            from one_dragon.utils.log_utils import log
            log.warning('[cw!][layout] 后排 %d 槽布局未建档(退 6 槽基线,识别/拖拽将错位;'
                        '停机钩子将触发现场验证;补档:拖角色逐位验 → upsert 后排%d槽-1..%d'
                        ' → _LAYOUT_PREFIX 登记)', cap, cap, cap)
    except Exception:   # noqa: BLE001
        pass
    return None


def fallback_back_slots() -> list[tuple[int, Rect]]:
    """无 ctx/无档时的兜底:静态 6 槽基线(与 screen_info 基线一致的硬拷贝;仅测试用)。"""
    xs = (604, 746, 888, 1032, 1173, 1315)
    half = 71
    return [(i + 1, Rect(x - half, _BACK_Y1, x + half, _BACK_Y2)) for i, x in enumerate(xs)]
