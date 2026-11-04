"""货币战争 按排羁绊聚合 API(契约包 C6 契约 1,冻结)。

**单一源**:全仓唯一「前后台×标签」羁绊计数聚合入口——消费方(C2 体系判定 /
白厄前排法则 / C3 演进引擎)不得自算按排聚合(契约冻结条款;验收 = grep 全仓
无第二处按排聚合实现)。

口径(契约 C6;benchchar-retirement P4 状态容器行输入重写,design §2.1/§2.4):
- 输入 = 状态容器行域 ``(front_row, back_row)``,元素 = 状态容器 ``Unit``(§2.1
  deployed 计算形状),纯逻辑组装,无识别;排归属由行入参原生承载
  (§2.1「排归属由下标派生」的行域形态,不再读 position_pref 信息位);
- 标签 = 角色羁绊全集(阵营 factions + 流派 flows,多羁绊角色每系都计——与
  board 左面板多阵营计数口径一致);**例外 = 选边型双羁绊角色**(布洛
  尼娅,SIDE_PICK_DUAL_BONDS)按图鉴逻辑选边单边计入(其余单位注册表
  出身计数,不分排,peers = 全板其余单位——图鉴「小队中」= 全队);
- **开拓者形态按当前排归一**(契约 C6 口径):char_id 是开拓者时按所在行
  取对应形态再取羁绊(前排=记忆/后排=欢愉);正常链路上行写端归一口
  (trailblazer_row_unit)已归一,此处再归一是防御(直构状态/重建路径
  未走归一时);
- 未识别角色(空名/未注册名):注册表派生不可得 = 不可判标签,不计
  (§2.1 faction 类3 口径「未知名 = '?'」——'?' 不入标签计数,与停用
  换形层 faction='?' 兜底不计同值);
- 排合计:``total()`` 恒等于两行之和,不丢计数。

契约签名(冻结的是单一源语义):
``board_by_row(front_row, back_row) -> BoardByRow``,另给
``board_by_row_of(state)`` 便捷入口(消费方持状态容器 GameState)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import (
    CHARACTERS,
    is_trailblazer,
    side_pick_bond,
    trailblazer_form,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
        Unit,
    )


def _trait_tags(unit: Unit, row: str,
                peers: list[Unit] | None = None) -> tuple[str, ...]:
    """一个已上阵单位的羁绊标签全集(开拓者先按排归一形态)。

    char_id 识别 → CHARACTERS 注册表 factions+flows 全集(多羁绊每系都计);
    未识别/未注册 → 空元组(不可判标签不计,口径见模块头)。
    选边型双羁绊角色(布洛妮娅,cw_chars.SIDE_PICK_DUAL_BONDS)在 peers
    非 None 时按 cw_chars.side_pick_bond 选边单边计入(基数 = peers 各
    单位注册表出身;选边不分排,peers 须 = 全板其余单位——图鉴「小队
    中」= 全队);peers None = 现行全集行为(双边照出)。
    """
    char_id = str(getattr(unit, 'char_id', '') or '')
    if char_id and is_trailblazer(char_id):
        char_id = trailblazer_form(char_id, row)
    ch = CHARACTERS.get(char_id) if char_id else None
    if ch is None:
        return ()
    if peers is not None:
        side = side_pick_bond(char_id, [str(getattr(p, 'char_id', '') or '')
                                        for p in peers])
        if side is not None:
            return (side,)
    return tuple(ch.factions) + tuple(ch.flows)


@dataclass(frozen=True)
class BoardByRow:
    """按排羁绊聚合结果(C6 契约形状):front/back 各自 标签→计数 + 全板合计视图。

    - ``front``/``back``:dict[标签,计数](仅含计数 >0 的标签);
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


def board_by_row(front_row: list[Unit] | None,
                 back_row: list[Unit] | None) -> BoardByRow:
    """按排羁绊聚合(C6 契约 1 冻结语义;状态容器行域输入,排归属 = 行入参)。

    选边型双羁绊角色(布洛妮娅)经 _trait_tags peers 透传单边计入:
    选边不分排(图鉴「小队中」= 全队),peers = 全板其余单位。"""
    front: dict[str, int] = {}
    back: dict[str, int] = {}
    all_units = [u for u in ([*(front_row or []), *(back_row or [])])
                 if u is not None]
    for row, units, bucket in (('front', front_row, front),
                               ('back', back_row, back)):
        for unit in (units or []):
            if unit is None:
                continue
            tags = _trait_tags(unit, row,
                               peers=[u for u in all_units if u is not unit])
            for t in tags:
                bucket[t] = bucket.get(t, 0) + 1
    return BoardByRow(front=front, back=back)


def board_by_row_of(gs: GameState) -> BoardByRow:
    """便捷入口(消费方持状态容器 GameState):行域经状态容器读口
    :func:`cw_game_state.deployed_rows_of` 现读后聚合。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
    )
    front, back = deployed_rows_of(gs)
    return board_by_row(front, back)
