# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争**备战画面**额外识别器(per-screen recognizer)。

``analyze_screen`` 精准命中「货币战争-备战」后,框架按 ``screen_name`` 查表调用本识别器,把备战画面的
结构化领域事实(金币 / 阶段 / 血量 / 连胜 / 部署数 / 阵营在场人数)塞进返回的 ``extras``,供智能体 /
HTTP 消费方直接读用,不必自己 OCR / 看图。

**并发安全(关键)**:本 ``recognize`` 必须是**纯读** —— 不写 ``self.``、不写任何模块全局、不读写
``cw_match.session``。原因:``analyze_screen`` 是观察类 tool,可在某 CW operation **运行期间**被并发调用
(观察类不查 run_slot);若本识别器写了 operation 也在用的可变状态,会互相污染。故:
- gold / hp / streak / deploy / board 复用 ``cw_observation`` 的**纯 reader**(它们不写全局 / session);
- **phase 不复用 ``read_phase_round``**(它成功时写模块全局 ``_last_phase_round`` 的 last-known-good 兜底,
  会与 operation 竞争污染兜底值)→ 本模块自写 ``_read_phase_round_pure``(只 OCR + 正则,不缓存,读不到返 None);
- **不复用 ``read_game_state``**(它读写 ``cw_match.session.last_level_obs`` / ``tracked_deployed``,是 session 状态)。

**角色身份(前后台 / 备战席)**:用 ``cw_identity_obs.read_deployed_chars`` / ``read_bench_chars``
(纯 CV SIFT,**纯读** —— 只裁槽位 + SIFT + 返 BenchChar,不写 session / 全局,可安全并发)产
``front_line`` / ``back_line`` / ``bench``(角色规范名 list)。templates 从 ``ctx.cw_portrait_templates`` 取
(``deploy_bench`` 加载的立绘库 ``character_cw_portrait`` 缓存);**未加载(None)→ 不产角色**
(recognizer 不自己 load,守纯读原则),三字段返 None。

⚠️ **可靠性待实测**:立绘库 ``character_cw_portrait`` 实际识别效果从未实测(理论上比脸库可靠:域匹配 +
含服装,变体分开采),产出可能是部分命中 / 漏 / 误。消费方据该字段时知其 SIFT 来源 + 待实测(见
``currency_war_char_id`` docstring);**未实测前不据该字段做硬决策**(旧 docstring「不产角色」即此顾虑,
现改为产出但标注,供智能体交叉验证而非盲信)。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from one_dragon.base.screen.screen_recognizer import ScreenRecognizer
from sr_od.application.currency_war.cw_equipment import ensure_equip_tm_templates
from sr_od.application.currency_war.cw_identity_obs import (
    read_bench_chars,
    read_deployed_chars,
    read_row_equipped,
)
from sr_od.application.currency_war.cw_obs_core import (
    A_PHASE,
    SCREEN_NAME,
    _area_rect,
    _ocr,
)
from sr_od.application.currency_war.cw_observation import (
    read_board,
    read_deploy_cap,
    read_deployed_count,
    read_gold,
    read_hp,
    read_level,
    read_streak,
)
from sr_od.application.currency_war.cw_observe import cw_log, cw_shot

if TYPE_CHECKING:
    from cv2.typing import MatLike

    from one_dragon.base.screen.screen_info import ScreenInfo
    from sr_od.context.sr_context import SrContext


def _read_phase_round_pure(ctx: SrContext, screen: MatLike) -> tuple[int, int] | None:
    """位面 + 轮次(**纯读**):顶栏「X-Y」(如 "1-3" = 位面1 第3轮);读不到 → None。

    与 ``cw_observation.read_phase_round`` 同解析,但**去掉**模块全局 ``_last_phase_round`` 的写 / 读
    (并发安全:recognizer 不得与运行中 operation 竞争该全局)。读不到时返 None(不伪造 (1,1) 兜底)。

    Args:
        ctx: 运行上下文(经 ``cw_obs_core._area_rect`` / ``_ocr`` 读 ``区域-阶段`` area)。
        screen: 备战画面截图。

    Returns:
        ``(plane, round_num)``;OCR 读不到返 None。
    """
    blob = ''.join(r.data for r in _ocr(ctx, screen, _area_rect(ctx, A_PHASE)))
    m = re.search(r'(\d)\s*-\s*(\d)', blob)         # "1-3"
    if m:
        return int(m.group(1)), int(m.group(2))
    plane_m = re.search(r'第\s*(\d)\s*位面', blob)
    if plane_m:
        return int(plane_m.group(1)), int(plane_m.group(1))
    digits = re.findall(r'\d', blob)
    if digits:
        return int(digits[0]), int(digits[0])
    return None


@dataclass
class _BattlePrepState:
    """备战画面领域事实(组装后 ``asdict()`` 转 dict 回传;类型化单一真相源)。

    字段类型对齐各 reader 的返回类型(gold/hp 有安全默认故非 Optional;phase/deploy/streak 读不到为 None)。
    """

    gold: int                       # 当前金币(read_gold,读不到→0,安全保守)
    phase: tuple[int, int] | None   # (位面, 轮次);读不到→None(不伪造)
    hp: int                         # 小队剩余血量(read_hp,读不到→100 健康先验)
    streak: int | None              # 连胜/连败 magnitude(read_streak,读不到→None)
    deploy_count: int | None        # 已部署角色数(read_deployed_count,读不到→None)
    deploy_cap: int | None          # deploy cap 真值(read_deploy_cap,读不到→None)
    level: int                      # 团队规模等级(read_level,Lv.N;cap>level=钻石/宝钻加成)
    board: dict[str, int]           # {阵营名: 在场人数}(read_board)
    front_line: list[str] | None    # 前排角色规范名(read_deployed_chars SIFT;templates 未加载/空→None)
    back_line: list[str] | None     # 后排角色规范名(同上)
    bench: list[str] | None         # 备战栏角色规范名(read_bench_chars SIFT;同上)
    front_equips: dict[int, list[str]] | None  # 前排每槽已穿装备名(read_row_equipped TM;templates 未加载/空→None)
    back_equips: dict[int, list[str]] | None   # 后排每槽已穿装备名(同上)
    bench_equips: dict[int, list[str]] | None  # 备战栏每槽已穿装备名(同上)


class BattlePrepRecognizer(ScreenRecognizer):
    """货币战争备战画面额外识别器(首个 per-screen recognizer 消费者)。"""

    screen_name: str = SCREEN_NAME   # '货币战争-备战'

    def recognize(
        self,
        ctx: SrContext,
        image: MatLike,
        screen_info: ScreenInfo,   # noqa: ARG002  命中画面 ScreenInfo;本识别器经 cw_obs_core 读 area,暂未直接用
    ) -> dict | None:
        """读备战画面的经济 / 阵营领域事实 → dict(纯读,见模块 docstring 并发安全说明)。

        Args:
            ctx: 运行上下文。
            image: 备战画面截图(analyze 已截,复用)。
            screen_info: 命中画面的 ScreenInfo(经 ``cw_obs_core._area_rect`` 读 area pc_rect)。

        Returns:
            ``_BattlePrepState`` 的 dict 视图;字段含义见 ``_BattlePrepState``。
        """
        # 角色身份(立绘库 SIFT 纯读;templates 未加载→三字段 None,不自己 load)
        templates = getattr(ctx, 'cw_portrait_templates', None)
        front_line: list[str] | None = None
        back_line: list[str] | None = None
        bench: list[str] | None = None
        if templates is not None:
            deployed = read_deployed_chars(ctx, image, templates)
            bench_list = read_bench_chars(ctx, image, templates)
            front_line = [c.char_id for c in deployed if c.position_pref == 'front'] or None
            back_line = [c.char_id for c in deployed if c.position_pref == 'back'] or None
            bench = [c.char_id for c in bench_list] or None
        # 穿戴装备(read_row_equipped TM below-avatar mini icon;ensure_equip_tm_templates 加载缓存,纯读;
        # 产出「谁穿了什么」给策略层 — 与 front_line/back_line/bench 角色身份互补,完整槽位态)
        front_equips: dict[int, list[str]] | None = None
        back_equips: dict[int, list[str]] | None = None
        bench_equips: dict[int, list[str]] | None = None
        equip_grays = ensure_equip_tm_templates(ctx)
        if equip_grays is not None:
            front_equips = read_row_equipped(ctx, image, equip_grays, '前排', 4) or None
            back_equips = read_row_equipped(ctx, image, equip_grays, '后排', 6) or None
            # 备战栏 below 不读:未上阵角色无 below-avatar icon(机制恒空,见 cw_dev 权威源映射),
            # 读它只在空背景产假 MISS 噪声(某模板 val 0.55-0.56,shot miss_slot5 实证无 icon)。
            # bench_equips 保持 None(无消费方,字段留接口兼容)。
            # bench_equips = read_row_equipped(ctx, image, equip_grays, '备战栏', 9) or None
        phase = _read_phase_round_pure(ctx, image)
        level = read_level(ctx, image, phase[0], phase[1]) if phase else read_level(ctx, image, 0, 0)
        state = _BattlePrepState(
            gold=read_gold(ctx, image),
            phase=phase,
            hp=read_hp(ctx, image),
            streak=read_streak(ctx, image),
            deploy_count=read_deployed_count(ctx, image),
            deploy_cap=read_deploy_cap(ctx, image),
            level=level,
            board=read_board(ctx, image),
            front_line=front_line,
            back_line=back_line,
            bench=bench,
            front_equips=front_equips,
            back_equips=back_equips,
            bench_equips=bench_equips,
        )
        # D-50:deploy_cap > level = 钻石/财富宝钻加成(+1 团队槽)→ 后排可能>6(read_equipped count=6 漏)
        if state.deploy_cap is not None and state.deploy_cap > state.level:
            cw_log('recognize', step='team_size', target='后排', attn=True,
                   anomaly=f'deploy_cap={state.deploy_cap}>level={state.level}(钻石/宝钻加成)→后排可能>6(read_equipped count=6 漏,D-50)',
                   level=state.level, deploy_cap=state.deploy_cap,
                   shot=cw_shot(image, f'team_cap{state.deploy_cap}_lv{state.level}'))
        return asdict(state)
