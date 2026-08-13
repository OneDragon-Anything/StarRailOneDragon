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

**角色身份 + 星级 + 装备(前后台 / 备战席)**:用 ``cw_identity_obs.read_deployed_chars`` / ``read_bench_chars``
(纯 CV SIFT,**纯读** —— 只裁槽位 + SIFT + 返 BenchChar,不写 session / 全局,可安全并发)产
``front_line`` / ``back_line`` / ``bench``(BenchChar list,含 char_id/star/equips)。立绘库经
``ensure_portrait_templates`` **幂等加载缓存**(只读资源,并发安全,同 ``ensure_equip_tm_templates``);
库缺失→三字段 None。装备经 ``read_row_equipped`` 读 below-avatar icon,按 slot 注入 BenchChar.equips
(备战席无 below icon→equips 恒 [])。

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
from sr_od.application.currency_war.cw_equipment import (
    ensure_equip_sift_templates,
    ensure_equip_tm_templates,
    read_equips,
)
from sr_od.application.currency_war.cw_equipment_data import get_equip
from sr_od.application.currency_war.cw_identity_obs import (
    ensure_portrait_templates,
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
from sr_od.application.currency_war.cw_state import BenchChar

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
    角色槽位复用 ``BenchChar``(cw_state;含 slot/char_id/faction/star/position_pref/equips),不另建模型。
    """

    gold: int                       # 当前金币(read_gold,读不到→0,安全保守)
    phase: tuple[int, int] | None   # (位面, 轮次);读不到→None(不伪造)
    hp: int                         # 小队剩余血量(read_hp,读不到→100 健康先验)
    streak: int | None              # 连胜/连败 magnitude(read_streak,读不到→None)
    deploy_count: int | None        # 已部署角色数(read_deployed_count,读不到→None)
    deploy_cap: int | None          # deploy cap 真值(read_deploy_cap,读不到→None)
    level: int                      # 团队规模等级(read_level,Lv.N;cap>level=钻石/宝钻加成)
    board: dict[str, int]           # {阵营名: 在场人数}(read_board)
    front_line: list[BenchChar] | None  # 前排角色(SIFT 身份 + read_star 星级 + read_row_equipped 装备注入 equips;templates 未加载→None)
    back_line: list[BenchChar] | None   # 后排角色(同上)
    bench: list[BenchChar] | None       # 备战栏角色(read_bench_chars SIFT + read_star;备战席无 below icon→equips 恒 [])
    owned_equips: list[dict] | None      # 右侧 owned 装备栏(read_equips SIFT;元素 {name,category,cx,cy,inliers};category 工具/特殊=消耗品,其余简易/进阶/...=装备;空→None;templates 未加载→None)


class BattlePrepRecognizer(ScreenRecognizer):
    """货币战争备战画面额外识别器(首个 per-screen recognizer 消费者)。"""

    screen_name: str = SCREEN_NAME   # '货币战争-备战'

    # extras 字段说明(随 analyze 响应平级返回 extras_doc;键集与 _BattlePrepState 一致)
    extras_doc: dict[str, str] = {
        'gold': '当前金币(int;读不到→0,安全保守默认)',
        'phase': '(位面, 轮次) 二元组,如 [1,3] = 位面1 第3轮;读不到→None(不伪造)',
        'hp': '小队剩余血量(int,0-100;读不到→100 健康先验)',
        'streak': '连胜/连败 magnitude(int;读不到→None)',
        'deploy_count': '已部署角色数(int;读不到→None)',
        'deploy_cap': '部署上限真值(int;>level 表示钻石/财富宝钻加成 +1 团队槽;读不到→None)',
        'level': '团队规模等级 Lv.N(int;cap>level=钻石/宝钻加成)',
        'board': '{阵营名: 在场人数} dict(OCR 左面板)',
        'front_line': '前排角色 list(元素 BenchChar dict: slot/char_id/faction/star/position_pref/equips;'
                      'char_id 空串=未知;equips=装备名 list)。SIFT 立绘识别可靠性待实测,别单独据它做硬决策;'
                      'templates 未加载→None',
        'back_line': '后排角色 list(同 front_line 结构;SIFT 待实测;templates 未加载→None)',
        'bench': '备战栏角色 list(同上;备战席无 below icon→equips 恒 [];空→None)',
        'owned_equips': '右侧 owned 装备栏 list(read_equips SIFT;元素 {name,category,cx,cy,inliers};'
                        'category 工具/特殊=消耗品,其余简易/进阶/特权/星徽/白昼/命运/骇客=装备;'
                        'cx/cy=1080p 原图绝对坐标(点该坐标开对应物品详情);空→None;templates 未加载→None)',
    }

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
        # 装备(slot_idx → 装备名;先读,再注入 BenchChar.equips)。备战栏 below 不读(未上阵无 icon,机制恒空,
        # 读只产假 MISS 噪声 — 某模板 val 0.55-0.56,shot miss_slot5 实证无 icon)。
        equip_grays = ensure_equip_tm_templates(ctx)
        front_equips = read_row_equipped(ctx, image, equip_grays, '前排', 4) if equip_grays is not None else {}
        back_equips = read_row_equipped(ctx, image, equip_grays, '后排', 6) if equip_grays is not None else {}
        # 角色复用 BenchChar(read_deployed_chars 已返,含 star);只补 equips(按 slot 对齐注入)
        templates = ensure_portrait_templates(ctx)  # 幂等加载缓存(并发安全,同 ensure_equip_tm_templates);保证 analyze 产角色
        front_line: list[BenchChar] | None = None
        back_line: list[BenchChar] | None = None
        bench: list[BenchChar] | None = None
        if templates is not None:
            deployed = read_deployed_chars(ctx, image, templates)
            bench_chars = read_bench_chars(ctx, image, templates)
            for c in deployed:
                c.equips = (front_equips if c.position_pref == 'front' else back_equips).get(c.slot, [])
            front_line = [c for c in deployed if c.position_pref == 'front'] or None
            back_line = [c for c in deployed if c.position_pref == 'back'] or None
            bench = bench_chars or None  # 备战席无 below icon → equips 保持默认 []
        # owned 装备栏(右侧 区域-道具装备,read_equips SIFT;装备+消耗品混排,返名+位置,category 区分装备 vs 消耗品)
        sift_templates = ensure_equip_sift_templates(ctx)
        owned_equips: list[dict] | None = None
        if sift_templates is not None:
            _owned: list[dict] = []
            for eq_name, eq_pos, eq_inliers in read_equips(image, sift_templates):
                eq_info = get_equip(eq_name)
                _owned.append({
                    'name': eq_name,
                    'category': eq_info.category if eq_info is not None else '',
                    'cx': eq_pos[0],
                    'cy': eq_pos[1],
                    'inliers': eq_inliers,
                })
            owned_equips = _owned or None
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
            owned_equips=owned_equips,
        )
        # D-50:deploy_cap > level = 钻石/财富宝钻加成(+1 团队槽)→ 后排可能>6(read_equipped count=6 漏)
        if state.deploy_cap is not None and state.deploy_cap > state.level:
            cw_log('recognize', step='team_size', target='后排', attn=True,
                   anomaly=f'deploy_cap={state.deploy_cap}>level={state.level}(钻石/宝钻加成)→后排可能>6(read_equipped count=6 漏,D-50)',
                   level=state.level, deploy_cap=state.deploy_cap,
                   shot=cw_shot(image, f'team_cap{state.deploy_cap}_lv{state.level}'))
        return asdict(state)
