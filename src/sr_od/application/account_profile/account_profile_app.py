"""账号档案扫描:游戏内角色列表逐格点击,逐角色读取养成情况,产出 JSON。

扫描单元 = 列表里一个角色格:点击进该角色详情 → 读基础面板(名/等级/星魂/属性)
→ 依次切光锥 / 行迹 / 星魂 / 遗器 TAB 读取 → 进遗器替换页读 6 件词条 → 回列表下一格。
滚动重叠区的已扫角色由 SIFT 预判跳过;SIFT 无匹配格点击读名兜底(覆盖库外角色)。

数据落盘 config/idx/account_profile_scan.json;识别核心见 account_profile_core.py。
运行通路:MCP 重启后 run_standalone_app('account_profile');DEFAULT_GROUP=False 不进一条龙默认编排。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen.screen_utils import (
    find_and_click_area,
    get_match_screen_name,
    is_target_screen,
)
from one_dragon.utils.log_utils import log
from sr_od.application.account_profile import account_profile_const
from sr_od.application.account_profile.account_profile_config import (
    AccountProfileConfig,
    ScanModeEnum,
)
from sr_od.application.account_profile.account_profile_core import (
    AvatarMatcher,
    count_eidolon_locks,
    normalize_cn_name,
    ocr_rect_texts,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

OUTPUT_PATH: Path = Path('config') / 'idx' / 'account_profile_scan.json'

# 列表滚动等待:拖拽后等列表动画站稳
SCROLL_SETTLE_SEC: float = 1.5
# 列表静止时背景粒子光效仍有 2-5 的帧间差异,滚动时差异远高于此,取 8 分开两态。
TOP_STABLE_DIFF: float = 8.0
# 滚动条滑块轨道 x 中心与判定带(亮色滑块段),用于实测滑块真实位置
SCROLL_TRACK_X: int = 575
THUMB_DETECT_HALF_W: int = 10
THUMB_BRIGHT_MIN: int = 120
# 点格身份确认重试次数:点击落空/读名失败都重试;超限后按最后一次实测名归档(见 _scan_one_character)
CELL_CONFIRM_ATTEMPTS: int = 3
# 到底判定:滑块已到轨道底之后再空转 N 轮(每轮全屏重扫)确认无新格,才收尾落盘
BOTTOM_CONFIRM_ROUNDS: int = 2
# 每轮滚动步长(≈4 行,一屏 5 行留 1 行重叠防漏格);配合已归档名去重,重叠行快速跳过
SCROLL_STEP_PX: int = 160



class AccountProfileApp(SrApplication):
    """账号档案扫描:逐角色读取养成情况,产出 account_profile_scan.json。"""

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, account_profile_const.APP_ID, op_name=account_profile_const.APP_NAME,
                           node_max_retry_times=40)  # scan_loop 逐屏 retry 推进(约 30 屏),默认 1 次必中途夭折
        self._matcher: AvatarMatcher | None = None
        self._config = AccountProfileConfig(ctx.current_instance_idx)
        self._thumb_y: int = 250  # 滚动条滑块中心 y;滚顶后重置
        self._scrolled_to_top: bool = False  # 滚顶节点重入闸:retry 轮经 node_from 重入时跳过重复拖拽
        self._bottom_rounds: int = 0  # 滑块到底后的连续空转轮数(到底判定)
        self._done_names: set[str] = set()  # 本次运行已归档角色名(full 模式跨轮回去重,重叠行快速跳过)
        self._known_by_pos: dict[tuple[int, int], str] = {}  # 格子位置→角色名缓存(跨轮保留)
        # 产物基础:incremental=读旧档作增量底表;full=本轮画面实扫到的角色为唯一真相,
        # 不掺旧档(旧档可能是错位时代的脏数据,混入会永久化缺陷)——落在磁盘上的旧档
        # 会被首轮 _save_output 整体覆盖
        self.profiles: dict[str, dict] = (
            {} if self._config.scan_mode == ScanModeEnum.FULL.value else self._load_existing_profiles()
        )

    def _load_existing_profiles(self) -> dict[str, dict]:
        """读取上次扫描产物作已扫基础(点号变体在此合并,首见保留)。

        档案完整性过滤:遗器为空或星魂未读的条目视为未扫(早期版本读取失败时代的
        残留档案,直接作已扫基础会被增量跳过永久化缺陷),本轮强制重扫补全。
        """
        if not OUTPUT_PATH.exists():
            return {}
        try:
            with open(OUTPUT_PATH, encoding='utf-8') as f:
                data = json.load(f)
            profiles: dict[str, dict] = {}
            for c in data.get('characters', []):
                raw_cn = c.get('cn')
                if not raw_cn:
                    continue
                cn = normalize_cn_name(raw_cn)
                if cn is None or cn in profiles:
                    continue
                if c.get('eidolon_count', -1) < 0 or not c.get('relics'):
                    continue
                profiles[cn] = c
            return profiles
        except (json.JSONDecodeError, OSError):
            return {}

    @operation_node(name='回到大世界', is_start_node=True)
    def back_to_world(self) -> OperationRoundResult:
        back = BackToNormalWorldPlus(self.ctx)
        back_result = back.execute()
        if not back_result.success:
            return self.round_fail('无法回到大世界', wait=1)
        return self.round_success(wait=1)

    @node_from(from_name='回到大世界')
    @operation_node(name='进入角色详情页')
    def enter_character_page(self) -> OperationRoundResult:
        # 路由边已建档:大世界 → 菜单 → 角色详情(goto 自动寻路)。
        # goto 每跳一步重入本节点,回大世界已拆上一节点,否则死循环。
        return self.round_by_goto_screen(screen_name='角色-详情', success_wait=1.5, retry_wait=1.5)

    @node_from(from_name='进入角色详情页')
    @operation_node(name='打开角色列表侧栏')
    def open_sidebar(self) -> OperationRoundResult:
        """侧栏是格子遍历的载体:格子固定网格 + 滚动可计算(头像条视图漂移不可用固定坐标)。"""
        if self._set_sidebar(True):
            return self.round_success(wait=1)
        return self.round_retry('侧栏打开失败', wait=1.5)

    @node_from(from_name='打开角色列表侧栏')
    @operation_node(name='滚回列表顶部')
    def scroll_to_top(self) -> OperationRoundResult:
        """滚回列表顶部:实测滑块位置拖到轨道顶,帧差收敛(画面不动)即认定到顶。"""
        # 重入闸:round_retry 会经 node_from 重入本节点;滚顶只在首次进列表时做一次,
        # 之后每轮的向下滚动全权归 scan_loop 的 _scroll_down,否则每轮被拖回顶部永不推进
        if self._scrolled_to_top:
            return self.round_success(wait=1)
        # 拖拽可能被吞:实测-拖拽-帧差验证循环,画面不动(≤粒子噪声)即已到顶
        for _ in range(3):
            real = self._locate_thumb() or 820
            pre = self._frame_gray()
            self.ctx.controller.mouse_move(Point(SCROLL_TRACK_X, real))
            time.sleep(0.2)
            self.ctx.controller.drag_to(
                start=Point(SCROLL_TRACK_X, real), end=Point(SCROLL_TRACK_X, 130),
                duration=1.5, hold_time=0.0)
            self._thumb_y = 250
            time.sleep(2)
            if float(cv2.absdiff(pre, self._frame_gray()).mean()) <= TOP_STABLE_DIFF:
                break
        self._scrolled_to_top = True
        return self.round_success(wait=1)


    @node_from(from_name='滚回列表顶部')
    @operation_node(name='逐角色扫描养成数据')
    def scan_loop(self) -> OperationRoundResult:
        """侧栏格子遍历:每轮处理当前屏格子后滑块下拖一屏,retry 驱动推进。

        处理范围由配置 scan_mode 决定:full=全部识别格重读(覆盖旧档案,已归档名跳过);
        incremental=只读档案里没有的角色(已扫格无点击跳过)。
        到底判定:滑块已到轨道底(_scroll_down 返回 False)后再空转 BOTTOM_CONFIRM_ROUNDS 轮
        确认无新格,才收尾落盘。旧版用格子集合不变判定,OCR 抖动会让集合逐轮漂移、
        计数反复清零永不收尾(2026-10-22 首跑实证循环打转 1 小时);滑块状态是确定性的。
        """
        if self._matcher is None:
            self._matcher = AvatarMatcher()
        if self._matcher.template_count == 0:
            return self.round_fail('模板库为空:config/idx/avatar_scan/ 缺失', wait=1)
        mode_full = self._config.scan_mode == ScanModeEnum.FULL.value

        cells = self._matcher.detect_cells(self.screenshot(), self.ctx.ocr.ocr)
        for cell in cells:
            if not mode_full:
                # 增量:SIFT 命中且已扫的格子直接跳过(零点击)
                if not cell['miss'] and cell['cn'] in self.profiles:
                    continue
                known_cn = self._known_by_pos.get(cell['abs_key'])
                if cell['miss'] and known_cn is not None and known_cn in self.profiles:
                    continue
            self._scan_one_character(cell, cell['cn'] or '未知', mode_full)

        # 每轮落盘:运行被停(超时保险/手动)也不丢已扫数据
        self._save_output()

        moved = self._scroll_down()
        if moved:
            self._bottom_rounds = 0
            return self.round_retry(
                f'累计 {len(self.profiles)} 角色,继续滚动', wait=1)
        self._bottom_rounds += 1
        if self._bottom_rounds >= BOTTOM_CONFIRM_ROUNDS:
            self._save_output()
            return self.round_success(
                f'列表遍历完成,共 {len(self.profiles)} 个角色', wait=1)
        return self.round_retry(
            f'滑块已到底,复核第 {self._bottom_rounds}/{BOTTOM_CONFIRM_ROUNDS} 轮', wait=1)

    @node_from(from_name='逐角色扫描养成数据')
    @operation_node(name='关闭角色页回到大世界')
    def back_to_hub(self) -> OperationRoundResult:
        """收尾回 hub:关闭角色页(落菜单)→ 回大世界,保证 app 间在主界面交接。"""
        result = self.round_by_find_and_click_area(
            self.last_screenshot, '角色-详情', '按钮-关闭',
            pre_delay=0.3, success_wait=1.5, retry_wait=1.5,
        )
        if not result.is_success:
            return self.round_retry('未找到角色页关闭按钮', wait=1.5)
        back = BackToNormalWorldPlus(self.ctx)
        back_result = back.execute()
        if not back_result.success:
            return self.round_fail('关闭角色页后无法回到大世界', wait=1)
        return self.round_success(wait=1)

    def _sidebar_visible(self, shot: MatLike) -> bool:
        """侧栏是否展开:列表标题「角色列表」在左侧列表区可见。"""
        return any(
            (str(r.data or '')).find('角色列表') != -1 and int(r.x) < 600
            for r in self.ctx.ocr.ocr(shot)
        )

    def _set_sidebar(self, open_it: bool) -> bool:
        """开/关角色列表侧栏,操作后 OCR 验证标题出现/消失。

        开:详情页左下角「角色列表」开关(侧栏关闭时才可见;开着时该位置被侧栏覆盖)。
        关:点详情区空白(实机验证;子页顶部的关闭敏感区不可用)。
        """
        for _ in range(2):
            visible = self._sidebar_visible(self.screenshot())
            if visible == open_it:
                return True
            if open_it:
                self.ctx.controller.click(Point(68, 1002), press_time=0.1)
            else:
                blank = self._area_point('角色-详情', '点击区-详情空白')
                self.ctx.controller.click(blank, press_time=0.1)
            time.sleep(1.8)
        return self._sidebar_visible(self.screenshot()) == open_it

    def _frame_gray(self) -> MatLike:
        """当前画面灰度帧,只取列表区域(x<600)。

        右侧详情区是持续动画的角色立绘,整帧帧差恒大于阈值,到底判定会永假;
        列表区域静止时只有粒子光效噪声(2-5),拖动时格子在动,可分。"""
        frame = cv2.cvtColor(self.screenshot(), cv2.COLOR_RGB2GRAY)
        return frame[:, :600]

    def _locate_thumb(self) -> int | None:
        """实测滚动条滑块中心 y(轨道亮色段);找不到返回 None。

        滑块是轨道上的亮色段,跟踪值 _thumb_y 与真实位置可能脱节(拖拽被游戏吞掉时),
        此时以实测为准重拖。
        """
        img = self._frame_gray()
        band = img[110:950, SCROLL_TRACK_X - THUMB_DETECT_HALF_W:SCROLL_TRACK_X + THUMB_DETECT_HALF_W]
        rows = band.mean(axis=1)
        ys = [i + 110 for i, v in enumerate(rows) if v > THUMB_BRIGHT_MIN]
        if len(ys) < 20:
            return None
        return (ys[0] + ys[-1]) // 2

    def _drag_thumb(self, from_y: int) -> None:
        """按住滑块从 from_y 下拖 SCROLL_STEP_PX(拖拽必须按在滑块上,实测按别处全被吞)。"""
        target_y = min(from_y + SCROLL_STEP_PX, 820)
        self.ctx.controller.mouse_move(Point(SCROLL_TRACK_X, from_y))
        time.sleep(0.2)
        self.ctx.controller.drag_to(
            start=Point(SCROLL_TRACK_X, from_y), end=Point(SCROLL_TRACK_X, target_y),
            duration=1.0, hold_time=0.0)

    def _scroll_down(self) -> bool:
        """侧栏向下滚一步(SCROLL_STEP_PX)。返回列表是否真的前进了(帧差验证)。

        拖拽被游戏吞掉时帧差≈0(粒子光效噪声 2-5,滚动远高于此,阈值 TOP_STABLE_DIFF
        为该画面实测定标值),此时实测滑块真实位置重拖一次;仍不动 = 滑块已在轨道底。
        """
        pre = self._frame_gray()
        self._drag_thumb(self._thumb_y)
        time.sleep(SCROLL_SETTLE_SEC)
        post = self._frame_gray()
        if float(cv2.absdiff(pre, post).mean()) > TOP_STABLE_DIFF:
            return True
        real = self._locate_thumb()
        if real is None:
            return False
        self._thumb_y = real
        pre = post
        self._drag_thumb(real)
        time.sleep(SCROLL_SETTLE_SEC)
        post2 = self._frame_gray()
        return float(cv2.absdiff(pre, post2).mean()) > TOP_STABLE_DIFF

    def _scan_one_character(self, cell: dict, name_hint: str, mode_full: bool = False) -> None:
        """单角色完整流程:点格切角色 → 关侧栏 → 读名验证 → 读全档案 → 开侧栏。

        关侧栏是读档案的前提(TAB 与左上角色名都被侧栏覆盖);读名与档案共用关侧栏后的画面。
        增量模式下读名确认已扫的角色直接跳回(不读档案)。

        归因只认画面实测名(错位修复):旧版读名失败兜底 name_hint,点击落空停在上个角色时,
        上个角色的数据会记到本格预期名下(白露/飞霄星魂名重复、砂金 6 命的根因)。现读名失败
        或与格子 SIFT 预期不符都重试点格;超限后按最后一次实测名归档——重试后仍不符大概率是
        SIFT 映射错,画面名字才是 ground truth;实测名 None(读不出)才跳过该格。

        SIFT 预期与实测的比对:cell['cn'] 是模板目录名(中英混合,如 jingliu/万敌),
        须经 cn_name() 映射成中文名再比,否则英文代号格逐格假性不符。
        循环退出进扫描时侧栏必须已关闭(最后一次迭代不重开),否则 TAB 全被侧栏遮挡
        (2026-10-22 首跑实证:重试耗尽路径开着侧栏扫描,光锥/星魂/遗器全线读不到)。
        """
        expected: str | None = cell.get('cn')
        expected_set: set[str] = set()
        if expected:
            expected_set.add(expected)
            mapped = self._matcher.cn_name(expected) if self._matcher is not None else None
            if mapped:
                expected_set.add(mapped)
        name: str | None = None
        for attempt in range(CELL_CONFIRM_ATTEMPTS):
            self._click_point(Point(cell['cx'], cell['cy']))
            time.sleep(1.2)
            if not self._set_sidebar(False):
                # 关侧栏失败=侧栏状态未知,先拉回开启态再重试
                self._set_sidebar(True)
                continue
            measured = self._read_detail_name()
            if measured is not None:
                name = measured
            if measured is not None and (expected is None or measured in expected_set):
                break
            if attempt < CELL_CONFIRM_ATTEMPTS - 1:
                # 还要重试才重开侧栏;最后一次保持关闭,直接进扫描
                self._set_sidebar(True)
        if name is None:
            log.warning(f'[账号档案] {name_hint}: 点格 {CELL_CONFIRM_ATTEMPTS} 次未读出角色名,跳过该格')
            self._set_sidebar(True)
            return
        if expected is not None and name not in expected_set:
            log.warning(f'[账号档案] 格子 SIFT 预期 {name_hint} 实测 {name},按实测名归档')
        if name in self._done_names or (not mode_full and name in self.profiles):
            # full:本轮运行已归档过(相邻屏重叠行)快速跳过;incremental:旧档案已有即跳过
            self._set_sidebar(True)
            return
        try:
            self._scan_current_character(name)
            self._done_names.add(name)
        except RuntimeError as e:
            # 画面漂移(遗器返回误触关闭等):恢复到详情页+侧栏,继续下一角色
            # 替换页可能不在 goto 路由图上,先点按钮-返回回着装页再 goto;仍失败回大世界重进
            log.warning(f'[账号档案] {name}: {e},恢复画面')
            find_and_click_area(self.ctx, self.screenshot(), '遗器-替换', '按钮-返回')
            time.sleep(1.2)
            r = self.round_by_goto_screen(screen_name='角色-详情', success_wait=1.5, retry_wait=1.5)
            if not r.is_success:
                BackToNormalWorldPlus(self.ctx).execute()
                self.round_by_goto_screen(screen_name='角色-详情', success_wait=1.5, retry_wait=1.5)
        self._set_sidebar(True)

    def _scan_current_character(self, name: str) -> None:
        """当前已停在目标角色详情页,依次读各 TAB 的养成数据。"""
        # 读档案前验证:停在替换页等子页时 TAB 全部不可点,读出的全是错位文本(实测垃圾档案)
        cur = get_match_screen_name(self.ctx, self.screenshot())
        if cur is not None and cur != '角色-详情':
            raise RuntimeError(f'读档案前画面在 {cur}, 不是角色-详情')
        profile: dict = {'cn': name}

        self._switch_tab('角色-详情')
        screen = self.screenshot()
        t = self._read_areas_text('角色-详情', screen, [
            '读区-等级', '读区-生命值', '读区-攻击力', '读区-防御力',
            '读区-速度', '读区-暴击率', '读区-暴击伤害'])
        profile['level'] = t['读区-等级']
        profile['attrs'] = {
            'hp': t['读区-生命值'],
            'atk': t['读区-攻击力'],
            'def': t['读区-防御力'],
            'spd': t['读区-速度'],
            'crit_rate': t['读区-暴击率'],
            'crit_dmg': t['读区-暴击伤害'],
        }

        # 光锥(TAB 切换失败则宁缺毋滥,不读错位数据)
        if self._switch_tab('角色-光锥'):
            screen = self.screenshot()
            t = self._read_areas_text('角色-光锥', screen, ['读区-光锥名', '读区-等级', '读区-叠影'])
            profile['light_cone'] = {
                'name': t['读区-光锥名'],
                'level': t['读区-等级'],
                'rank': t['读区-叠影'],
            }
        else:
            profile['light_cone'] = {}
            log.warning(f'[账号档案] {name}: 光锥 TAB 切换失败,跳过')

        # 星魂:名字恒显示(两态都在),eidolon_count 由挂锁章计数得出
        if self._switch_tab('角色-星魂'):
            screen = self.screenshot()
            t = self._read_areas_text('角色-星魂', screen, [
                '读区-星魂1名', '读区-星魂2名', '读区-星魂3名',
                '读区-星魂4名', '读区-星魂5名', '读区-星魂6名'])
            eidolon_names = [
                txt for txt in (t['读区-星魂1名'], t['读区-星魂2名'], t['读区-星魂3名'],
                                t['读区-星魂4名'], t['读区-星魂5名'], t['读区-星魂6名']) if txt
            ]
            lock_rects = [
                r for r in (self._area_rect('角色-星魂', f'锁位-星魂{i}图标') for i in range(1, 7))
                if r is not None
            ]
            if len(lock_rects) == 6:
                profile['eidolon_count'] = 6 - count_eidolon_locks(self.ctx.tm, screen, lock_rects)
            else:
                # 建档缺锁位 area = 无法数锁,记 -1(宁缺毋滥,不猜)
                profile['eidolon_count'] = -1
                log.warning(f'[账号档案] {name}: 星魂锁位 area 不全({len(lock_rects)}/6),星魂数记 -1')
            profile['eidolon_names'] = eidolon_names
        else:
            profile['eidolon_count'] = -1
            profile['eidolon_names'] = []
            log.warning(f'[账号档案] {name}: 星魂 TAB 切换失败,跳过')

        # 遗器着装 + 逐件词条
        if self._switch_tab('角色-遗器'):
            screen = self.screenshot()
            profile['relic_sets'] = ' '.join(self._read_areas_text(
                '角色-遗器', screen, ['读区-套装效果'])['读区-套装效果'])
            profile['relics'] = self._read_all_relics()
        else:
            profile['relic_sets'] = ''
            profile['relics'] = []
            log.warning(f'[账号档案] {name}: 遗器 TAB 切换失败,跳过')

        # 回详情 TAB:离开遗器等子页(遗器页顶部 (1343,72) 点击会关闭整个角色页,实机复现),
        # 给下一角色的格子点击一个确定起点
        self._switch_tab('角色-详情')

        self.profiles[name] = profile
        log.info(f"[账号档案] {name}:等级 {profile.get('level')},星魂 {profile.get('eidolon_count')},"
                 f"光锥 {profile['light_cone'].get('name')},遗器 {len(profile['relics'])} 件")

    # 部位 TAB 名 → 替换页词条区的部位显示名(TAB「腿部」的详情显示「脚部」,实测)
    _PARTS: list[tuple[str, str, str]] = [
        # (部位TAB area 后缀, 词条区显示名, 着装页遗器位 area 名)
        ('头部', '头部', '遗器位-头部'),
        ('手部', '手部', '遗器位-手部'),
        ('躯干', '躯干', '遗器位-躯干'),
        ('腿部', '脚部', '遗器位-脚部'),
        ('位面球', '位面球', '遗器位-位面球'),
        ('连结绳', '连结绳', '遗器位-连结绳'),
    ]

    def _read_all_relics(self) -> list[dict]:
        """在替换页内用顶部部位 TAB 逐部位读词条。

        入口:着装页逐个点遗器位直到进入替换页(全失败 = 6 部位均未佩戴)。
        部位 TAB 切换后验证词条区部位名,失败重试(切 TAB 动画未完成时点击会落空,实测)。
        读不到遗器名 = 该部位未佩戴,记录 equipped=False。
        读完点「按钮-返回」回着装页;返回后画面漂移(误触关闭 X)则报错交由调用方恢复。
        """
        relics: list[dict] = []
        # 确认已到遗器页:切 TAB 点击成功不代表动画完成,未完成时后续点击全线落空(实测)
        for _ in range(2):
            cur = get_match_screen_name(self.ctx, self.screenshot())
            if cur == '角色-遗器':
                break
            time.sleep(1.5)
        else:
            raise RuntimeError('遗器 TAB 切换后未进入遗器页')

        # 找一个能进入替换页的遗器位(全部失败 = 全部位未佩戴)
        entered_part: str | None = None
        for _, display, equip_area in self._PARTS:
            rect = self._area_rect('角色-遗器', equip_area)
            if rect is None:
                continue
            self.ctx.controller.click(
                Point((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2), press_time=0.1)
            time.sleep(2)
            if get_match_screen_name(self.ctx, self.screenshot()) == '遗器-替换':
                entered_part = display
                break
        if entered_part is None:
            log.warning('[账号档案] 所有遗器位点击均未进入替换页,按全部位未佩戴记录')
            return [
                {'slot_hint': display, 'equipped': False, 'name': None}
                for _, display, _ in self._PARTS
            ]

        for tab_name, display, _ in self._PARTS:
            if display != entered_part:
                switched = False
                for _ in range(3):
                    # 部位 TAB 位置固定,直按建档坐标点击(OCR 匹配点击偶发 NOT_FOUND 不稳定)
                    self.ctx.controller.click(
                        self._area_point('遗器-替换', f'部位TAB-{tab_name}'), press_time=0.1)
                    time.sleep(1.5)
                    part_text = self._read_area_text(
                        '遗器-替换', '读区-部位等级', self.screenshot())
                    if display in (part_text or ''):
                        switched = True
                        break
                if not switched:
                    # 3 次重试全失败 = 页面已不在替换页(状态异常),继续只会产空数据,
                    # 报错交由调用方恢复画面、本角色遗器留待下轮补扫
                    raise RuntimeError(f'部位 TAB 切换失败: {tab_name}')
            relics.append(self._read_relic_detail(f'遗器位-{tab_name}', display))

        # 返回着装页:「按钮-返回」(1861,67) 与详情页关闭 X 几乎重合——若页面状态已错位,
        # 这一击会关闭整个角色页(实机复现),必须点击后验证画面,漂移则报错交由调用方恢复
        find_and_click_area(self.ctx, self.screenshot(), '遗器-替换', '按钮-返回')
        time.sleep(1.2)
        cur = get_match_screen_name(self.ctx, self.screenshot())
        if cur is not None and cur != '角色-遗器':
            log.warning(f'[账号档案] 遗器返回后画面漂移到 {cur} (疑似误触关闭)')
            raise RuntimeError(f'遗器替换页返回后画面漂移: {cur}')
        return relics

    def _read_relic_detail(self, slot_area: str, display: str = '') -> dict:
        """当前在遗器替换页,读右侧词条面板;读不到遗器名 = 该部位未佩戴。"""
        screen = self.screenshot()
        t = self._read_areas_text('遗器-替换', screen, [
            '读区-遗器名', '读区-部位等级', '读区-主词条', '读区-副词条', '读区-套装效果'])
        name = ' '.join(t['读区-遗器名']).strip() if t['读区-遗器名'] else ''
        if not name:
            return {'slot_hint': slot_area, 'equipped': False, 'name': None}
        main_raw = ' '.join(t['读区-主词条']).strip()
        subs_raw = t['读区-副词条']
        return {
            'slot_hint': slot_area,
            'equipped': True,
            'name': name,
            'level': self._read_area_text('遗器-替换', '读区-部位等级', screen),
            'main': main_raw,
            'subs': subs_raw,
            'set': ' '.join(t['读区-套装效果']),
        }

    def _switch_tab(self, target_screen: str) -> bool:
        """在角色页内切 TAB(列表侧栏保持);点击后验证目标画面 id_mark 出现才算切到。

        失败时调用方必须跳过该 TAB 的读取(宁缺毋滥,读错位数据比缺数据更糟)。
        """
        area_name = f'TAB-{target_screen.split("-")[1]}'
        # TAB 栏常驻详情页所有子页,统一用「角色-详情」屏的建档;
        # 各子屏 yml 缺自身 TAB(不存在"切到自己"的导航),按目标屏查会 AREA_NO_CONFIG
        # 点击前稳定:上一页动画未走完或光标乱动都会让 TAB 点击落空(实测)
        area = self._area_rect('角色-详情', area_name)
        if area is None:
            log.warning(f'[账号档案] TAB area 缺失: {area_name}')
            return False
        time.sleep(0.5)
        self._click_point(Point((area[0] + area[2]) // 2, (area[1] + area[3]) // 2))
        time.sleep(1.2)
        checked = is_target_screen(self.ctx, self.screenshot(), screen_name=target_screen)
        if not checked:
            log.warning(f'[账号档案] TAB 点击后画面未到达: {target_screen}')
        return checked

    def _read_detail_name(self) -> str | None:
        """读左上角「命途 / 角色名」取角色名;经 normalize_cn_name 清洗,噪声名视为未识别。

        左上角在详情页与全部子页恒定显示该格式(子页正文右上会变成光锥/遗器名,不可用);
        裁剪读名区后 OCR(比整页 OCR 快,且规避读区外同格式文本干扰)。
        """
        rect = self._area_rect('角色-详情', '读名区-左上')
        if rect is None:
            return None
        for raw in ocr_rect_texts(self.ctx.ocr.ocr, self.screenshot(), rect):
            if '/' not in raw and '／' not in raw:
                continue
            seg = raw.replace('／', '/').split('/')[-1].strip()
            parsed = normalize_cn_name(seg)
            if parsed is not None:
                return parsed
        return None

    def _read_areas_text(self, screen_name: str, screen: MatLike, area_names: list[str]) -> dict[str, list[str]]:
        """同屏多读区共用一次整页 OCR,按文本框中心归属读区,返回 {读区名: [文本片段]}。

        逐读区裁剪 OCR 每调用 ~0.5s,同屏重复调用是纯浪费;整页一次后按 rect 归属。
        读区重叠时文本归第一个命中的读区。"""
        regions: dict[str, tuple[int, int, int, int]] = {}
        for name in area_names:
            rect = self._area_rect(screen_name, name)
            if rect is not None:
                regions[name] = rect
        out: dict[str, list[str]] = {name: [] for name in regions}
        for r in self.ctx.ocr.ocr(screen):
            rcx = int(r.x) + int(r.w) // 2
            rcy = int(r.y) + int(r.h) // 2
            for name, (x0, y0, x1, y1) in regions.items():
                if x0 <= rcx <= x1 and y0 <= rcy <= y1:
                    text = str(r.data or '').strip()
                    if text:
                        out[name].append(text)
                    break
        return out

    def _read_area_text(self, screen_name: str, area_name: str, screen: MatLike) -> str:
        """按 screen_info 读区裁剪 OCR,拼接文本;读区不存在或无文本返回空串。"""
        rect = self._area_rect(screen_name, area_name)
        if rect is None:
            return ''
        texts = ocr_rect_texts(self.ctx.ocr.ocr, screen, rect)
        return ' '.join(texts).strip()

    def _click_point(self, pt: Point, settle: float = 0.15) -> None:
        """稳定点击:先把光标移到目标停 settle 再按(截图逻辑会挪光标,紧接点击会被游戏丢掉)。"""
        self.ctx.controller.mouse_move(pt)
        time.sleep(settle)
        self.ctx.controller.click(pt, press_time=0.1)

    def _area_point(self, screen_name: str, area_name: str) -> Point:
        """取 area pc_rect 中心点(头像条槽位等固定点击位;坐标单一真相源在 screen_info)。"""
        rect = self._area_rect(screen_name, area_name)
        if rect is None:
            raise ValueError(f'area 不存在: {screen_name}.{area_name}')
        return Point((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)

    def _area_rect(self, screen_name: str, area_name: str) -> tuple[int, int, int, int] | None:
        """从 screen_info 取读区矩形;坐标单一真相源。area.rect 是 Rect 对象(无 __len__),取四角属性。"""
        try:
            area = self.ctx.screen_loader.get_area(screen_name, area_name)
        except Exception:
            return None
        rect = getattr(area, 'rect', None)
        if rect is None:
            return None
        return int(rect.x1), int(rect.y1), int(rect.x2), int(rect.y2)

    def _save_output(self) -> None:
        """扫描结果落盘 config/idx/account_profile_scan.json。"""
        payload = {
            'count': len(self.profiles),
            'characters': [self.profiles[cn] for cn in sorted(self.profiles)],
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
