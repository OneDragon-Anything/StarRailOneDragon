"""货币战争 按排羁绊聚合 API(契约包 C6 契约 1,冻结;2026-08-25 W38)。

**单一源**:全仓唯一「前后台×标签」羁绊计数聚合入口——消费方(C2 体系判定 /
白厄前排法则 / C3 演进引擎)不得自算按排聚合(契约冻结条款;验收 = grep 全仓
无第二处按排聚合实现)。

口径(契约 C6 + W21 #13):
- 输入 ``deployed``(已带 row = ``BenchChar.position_pref``),纯逻辑组装,无识别;
- 标签 = 角色羁绊全集(阵营 factions + 流派 flows,多羁绊角色每系都计——与
  board 左面板多阵营计数口径一致);
- **开拓者形态按当前排归一**(W21 #13 口径):char_id 是开拓者时按
  ``position_pref`` 取对应形态再取羁绊(前排=记忆/后排=欢愉);正常链路上
  ``_apply_row_to_char`` 已归一,此处再归一是防御(直构状态/重建路径未走归一时);
- 未识别角色(char_id 空)按 ``BenchChar.faction`` 兜底计一个标签(空/ '?' 不计,
  与 ``_recount_board`` 口径一致);
- 排归属:``position_pref == 'front'`` 计前排,其余计后排(total 恒等于两排之和,
  不丢计数;与 ``front_count()`` 的窄口径差异在 docstring 声明)。

契约签名(草案级细节,冻结的是单一源语义):
``board_by_row(deployed: list[BenchChar]) -> BoardByRow``,另给
``board_by_row_of(state)`` 便捷入口(消费方常持 GameState)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_chars import (
    CHARACTERS,
    is_trailblazer,
    trailblazer_form,
)
from sr_od.application.currency_war.cw_state import BenchChar


def _trait_tags(bc: BenchChar) -> tuple[str, ...]:
    """一个已上阵角色的羁绊标签全集(开拓者先按排归一形态)。

    char_id 识别 → CHARACTERS 注册表 factions+flows 全集(多羁绊每系都计);
    未识别 → ``(faction,)`` 兜底(空/'?' 不计,同 ``_recount_board`` 口径)。
    """
    char_id = getattr(bc, 'char_id', '') or ''
    row = getattr(bc, 'position_pref', 'back') or 'back'
    if char_id and is_trailblazer(char_id):
        char_id = trailblazer_form(char_id, row)
    if char_id:
        ch = CHARACTERS.get(char_id)
        if ch is not None:
            return tuple(ch.factions) + tuple(ch.flows)
    f = getattr(bc, 'faction', '') or ''
    return (f,) if f and f != '?' else ()


@dataclass(frozen=True)
class BoardByRow:
    """按排羁绊聚合结果(C6 契约形状):front/back 各自 标签→计数 + 全板合计视图。

    - ``front``/``back``:dict[标签, 计数](仅含计数 >0 的标签);
    - ``total()``:全板合计视图(两排之和;契约明示消费方可只看合计,
      如希儿判据「量子≥2 OR 贝≥2 不分排」);
    - ``count(tag, row=None)``:单标签计数(row=None = 全板)。
    """

    front: dict[str, int] = field(default_factory=dict)
    back: dict[str, int] = field(default_factory=dict)

    def row(self, row: str) -> dict[str, int]:
        """取单排视图('front'/'back';其余值按后排,同聚合口径)。"""
        return self.front if row == 'front' else self.back

    def total(self) -> dict[str, int]:
        """全板合计视图(两排逐标签求和)。"""
        out: dict[str, int] = dict(self.front)
        for k, v in self.back.items():
            out[k] = out.get(k, 0) + v
        return out

    def count(self, tag: str, row: str | None = None) -> int:
        """单标签计数;``row=None`` = 全板合计。"""
        if row is None:
            return self.total().get(tag, 0)
        return self.row(row).get(tag, 0)


def board_by_row(deployed: list[BenchChar]) -> BoardByRow:
    """按排羁绊聚合(C6 契约 1 冻结签名:纯逻辑组装,输入 deployed 已带 row)。"""
    front: dict[str, int] = {}
    back: dict[str, int] = {}
    for bc in deployed or []:
        if bc is None:   # ADR-0392 槽位表空槽
            continue
        tags = _trait_tags(bc)
        if not tags:
            continue
        bucket = front if (getattr(bc, 'position_pref', '') == 'front') else back
        for t in tags:
            bucket[t] = bucket.get(t, 0) + 1
    return BoardByRow(front=front, back=back)


def board_by_row_of(state) -> BoardByRow:
    """便捷入口:从 GameState 取 deployed 聚合(签名宽松 = duck-typing,
    测试/sim 的 state-like 视图同样可用)。"""
    return board_by_row(getattr(state, 'deployed', []) or [])
