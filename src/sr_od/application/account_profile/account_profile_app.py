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
import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen.screen_utils import (
    OcrClickResultEnum,
    find_and_click_area,
    is_target_screen,
)
from one_dragon.utils.log_utils import log
from sr_od.application.account_profile import account_profile_const
from sr_od.application.account_profile.account_profile_core import (
    AvatarMatcher,
    normalize_cn_name,
    ocr_rect_texts,
)
from sr_od.application.sr_application import SrApplication
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus

OUTPUT_PATH: Path = Path('config') / 'idx' / 'account_profile_scan.json'

# 列表滚动等待:拖拽后等列表动画站稳
SCROLL_SETTLE_SEC: float = 2.5
# 滚顶判据:相邻两帧平均差低于该值即到顶。阈值针对详情页动态背景光效校准:
# 列表静止时背景粒子光效仍有 2-5 的帧间差异,滚动时差异远高于此,取 8 分开两态。
TOP_STABLE_DIFF: float = 8.0
# 终止判据:连续 N 屏无新增角色即认为已到列表底部(滚轮小步长屏数多,取 3 防提前停)
NO_NEW_SCREENS_TO_STOP: int = 3

# 详情页角色名 OCR 区域(兜底读名与档案录入共用,1080p)
NAME_X_RANGE: tuple[int, int] = (1450, 1800)
NAME_Y_RANGE: tuple[int, int] = (100, 175)


class AccountProfileApp(SrApplication):
    """账号档案扫描:逐角色读取养成情况,产出 account_profile_scan.json。"""

    def __init__(self, ctx: SrContext):
        SrApplication.__init__(self, ctx, account_profile_const.APP_ID, op_name=account_profile_const.APP_NAME)
        self._matcher: AvatarMatcher | None = None
        # 跨运行去重:启动时读已有产物作已扫基础,本运行只扫增量(减少重复点击)
        self.profiles: dict[str, dict] = self._load_existing_profiles()

    def _load_existing_profiles(self) -> dict[str, dict]:
        """读取上次扫描产物;名字归一化后作已扫基础(点号变体在此合并,首见保留)。"""
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
                if cn is not None and cn not in profiles:
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
    def open_roster_list(self) -> OperationRoundResult:
        # 列表已开(侧栏标题「角色列表」可见)则不点按钮——再点会把列表关掉
        screen = self.screenshot()
        title_found = any(
            (str(r.data or '')).find('角色列表') != -1 and int(r.x) < 600
            for r in self.ctx.ocr.ocr(screen)
        )
        if title_found:
            return self.round_success(wait=1)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, '角色-详情', '按钮-角色列表',
            pre_delay=0.3, success_wait=2, retry_wait=1.5,
        )
        if result.is_success:
            # success_wait=2 已覆盖侧栏展开动画;沿边进「滚回列表顶部」。
            # 这里不能 round_wait——round_wait 重跑本节点会再点一次按钮,把刚展开的侧栏点关。
            return self.round_success(wait=1)
        return self.round_retry('未找到角色列表按钮', wait=1.5)

    @node_from(from_name='打开角色列表侧栏')
    @operation_node(name='滚回列表顶部')
    def scroll_to_top(self) -> OperationRoundResult:
        """向上拖动直到画面不再变化(相邻两帧平均差低于阈值即到顶)。"""
        prev: MatLike = self.screenshot()
        for _ in range(12):
            self.ctx.controller.drag_to(Point(280, 800), start=Point(280, 300), duration=0.4)
            time.sleep(1.2)
            shot = self.screenshot()
            diff = float(np.mean(cv2.absdiff(
                np.asarray(prev, dtype=np.int16), np.asarray(shot, dtype=np.int16),
            )))
            if diff < TOP_STABLE_DIFF:
                return self.round_success(wait=1)
            prev = shot
        return self.round_fail('滚顶未收敛(12 轮仍有画面变化)', wait=1)

    @node_from(from_name='滚回列表顶部')
    @operation_node(name='逐角色扫描养成数据')
    def scan_loop(self) -> OperationRoundResult:
        if self._matcher is None:
            self._matcher = AvatarMatcher()
        if self._matcher.template_count == 0:
            return self.round_fail('模板库为空:config/idx/avatar_scan/ 缺失', wait=1)

        no_new_screens = 0
        prev_names: set[str] = set()
        # 格身份表:abs_key(滚动无关的格锚定坐标) → 角色名。滚动后同一格 abs_key 不变,
        # 重叠区已知格直接跳过,不做任何点击。
        known_by_pos: dict[tuple[int, int], str] = {}
        for screen_idx in range(1, 40):
            shot = self.screenshot()
            cells = self._matcher.detect_cells(shot, self.ctx.ocr.ocr)

            for cell in cells:
                abs_key = cell['abs_key']
                # SIFT 已认出且已扫过:跳过,不点击
                if not cell['miss'] and cell['cn'] in self.profiles:
                    continue
                # SIFT 未认出但位置已知:直接用记忆身份
                known_cn = known_by_pos.get(abs_key)
                if cell['miss'] and known_cn is not None:
                    if known_cn not in self.profiles:
                        self.ctx.controller.click(Point(cell['cx'], cell['cy']), press_time=0.1)
                        time.sleep(1.2)
                        self._scan_current_character(known_cn)
                    continue
                # 未扫过:点击进角色读档案
                name = cell['cn'] if not cell['miss'] else None
                if name is None:
                    name = self._click_and_read_name(cell['cx'], cell['cy'])
                    if name is None:
                        continue
                known_by_pos[abs_key] = name
                if name in self.profiles:
                    continue
                self._scan_current_character(name)

            names_now = set(self.profiles.keys())
            new_count = len(names_now - prev_names)
            log.info(f'[账号档案] 第 {screen_idx} 屏:识别 {len(cells)} 格,新增 {new_count},累计 {len(self.profiles)} 个角色')
            if new_count == 0:
                no_new_screens += 1
                if no_new_screens >= NO_NEW_SCREENS_TO_STOP:
                    break
            else:
                no_new_screens = 0
            prev_names = names_now

            self._scroll_down()

        self._save_output()
        return self.round_success(f'共扫描 {len(self.profiles)} 个角色', wait=1)

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

    def _scan_one_character(self, cx: int, cy: int, known_cn: str) -> None:
        """点击列表格进入该角色并读取全档案;SIFT 已给出名字时兜底读名仅作校验。"""
        self.ctx.controller.click(Point(cx, cy), press_time=0.1)
        time.sleep(1.2)
        name = self._read_detail_name() or known_cn
        self._scan_current_character(name)

    def _scan_current_character(self, name: str) -> None:
        """当前已停在目标角色详情页,依次读各 TAB 的养成数据。"""
        profile: dict = {'cn': name}

        self._switch_tab('角色-详情')
        screen = self.screenshot()
        profile['level'] = self._read_area_text('角色-详情', '读区-等级', screen)
        profile['attrs'] = {
            'hp': self._read_area_text('角色-详情', '读区-生命值', screen),
            'atk': self._read_area_text('角色-详情', '读区-攻击力', screen),
            'def': self._read_area_text('角色-详情', '读区-防御力', screen),
            'spd': self._read_area_text('角色-详情', '读区-速度', screen),
            'crit_rate': self._read_area_text('角色-详情', '读区-暴击率', screen),
            'crit_dmg': self._read_area_text('角色-详情', '读区-暴击伤害', screen),
        }

        # 光锥(TAB 切换失败则宁缺毋滥,不读错位数据)
        if self._switch_tab('角色-光锥'):
            screen = self.screenshot()
            profile['light_cone'] = {
                'name': self._read_area_text('角色-光锥', '读区-光锥名', screen),
                'level': self._read_area_text('角色-光锥', '读区-等级', screen),
                'rank': self._read_area_text('角色-光锥', '读区-叠影', screen),
            }
        else:
            profile['light_cone'] = {}
            log.warning(f'[账号档案] {name}: 光锥 TAB 切换失败,跳过')

        # 行迹
        if self._switch_tab('角色-行迹'):
            screen = self.screenshot()
            profile['traces'] = [
                t for t in (
                    self._read_area_text('角色-行迹', '读区-节点-顶', screen),
                    self._read_area_text('角色-行迹', '读区-节点-左', screen),
                    self._read_area_text('角色-行迹', '读区-节点-右', screen),
                    self._read_area_text('角色-行迹', '读区-节点-中下', screen),
                    self._read_area_text('角色-行迹', '读区-节点-底', screen),
                ) if t
            ]
        else:
            profile['traces'] = []
            log.warning(f'[账号档案] {name}: 行迹 TAB 切换失败,跳过')

        # 星魂
        if self._switch_tab('角色-星魂'):
            screen = self.screenshot()
            eidolon_names = [
                n for n in (
                    self._read_area_text('角色-星魂', '读区-星魂1名', screen),
                    self._read_area_text('角色-星魂', '读区-星魂2名', screen),
                    self._read_area_text('角色-星魂', '读区-星魂3名', screen),
                    self._read_area_text('角色-星魂', '读区-星魂4名', screen),
                    self._read_area_text('角色-星魂', '读区-星魂5名', screen),
                    self._read_area_text('角色-星魂', '读区-星魂6名', screen),
                ) if n
            ]
            profile['eidolon_count'] = len(eidolon_names)
            profile['eidolon_names'] = eidolon_names
        else:
            profile['eidolon_count'] = -1
            profile['eidolon_names'] = []
            log.warning(f'[账号档案] {name}: 星魂 TAB 切换失败,跳过')

        # 遗器着装 + 逐件词条
        if self._switch_tab('角色-遗器'):
            screen = self.screenshot()
            profile['relic_sets'] = ' '.join(ocr_rect_texts(
                self.ctx.ocr.ocr, screen, self._area_rect('角色-遗器', '读区-套装效果'),
            ))
            profile['relics'] = self._read_all_relics()
        else:
            profile['relic_sets'] = ''
            profile['relics'] = []
            log.warning(f'[账号档案] {name}: 遗器 TAB 切换失败,跳过')

        # 回详情 TAB,给下一角色的读取一个确定起点
        self._switch_tab('角色-详情')

        self.profiles[name] = profile
        log.info(f"[账号档案] {name}:等级 {profile.get('level')},星魂 {profile.get('eidolon_count')},"
                 f"光锥 {profile['light_cone'].get('name')},遗器 {len(profile['relics'])} 件")

    def _read_all_relics(self) -> list[dict]:
        """在遗器着装页逐件点击进替换页读词条,读完回着装页。

        遗器位是纯 pc_rect 定位格(无文字/模板),直接按 screen_info rect 中心点击,
        不走 find_area(其识别面对无文字区域不可判)。
        """
        relics: list[dict] = []
        slot_areas = ['遗器位-上', '遗器位-右上', '遗器位-中绳', '遗器位-左下', '遗器位-下中', '遗器位-右下']
        for slot_area in slot_areas:
            rect = self._area_rect('角色-遗器', slot_area)
            if rect is None:
                log.warning(f'[账号档案] 遗器位 area 缺失: {slot_area}')
                continue
            center_x = (rect[0] + rect[2]) // 2
            center_y = (rect[1] + rect[3]) // 2
            self.ctx.controller.click(Point(center_x, center_y), press_time=0.1)
            time.sleep(1.5)
            relic = self._read_relic_detail(slot_area)
            relics.append(relic)
            # 返回着装页(替换页右上返回按钮)
            find_and_click_area(self.ctx, self.screenshot(), '遗器-替换', '按钮-返回')
            time.sleep(1.2)
        return relics

    def _read_relic_detail(self, slot_area: str) -> dict:
        """当前在遗器替换页,读右侧词条面板。"""
        screen = self.screenshot()
        main_raw = self._read_area_text('遗器-替换', '读区-主词条', screen)
        subs_raw = [
            s for s in ocr_rect_texts(
                self.ctx.ocr.ocr, screen, self._area_rect('遗器-替换', '读区-副词条'),
            ) if s
        ]
        return {
            'slot_hint': slot_area,
            'name': self._read_area_text('遗器-替换', '读区-遗器名', screen),
            'level': self._read_area_text('遗器-替换', '读区-部位等级', screen),
            'main': main_raw,
            'subs': subs_raw,
            'set': ' '.join(ocr_rect_texts(
                self.ctx.ocr.ocr, screen, self._area_rect('遗器-替换', '读区-套装效果'),
            )),
        }

    def _switch_tab(self, target_screen: str) -> bool:
        """在角色页内切 TAB(列表侧栏保持);点击后验证目标画面 id_mark 出现才算切到。

        失败时调用方必须跳过该 TAB 的读取(宁缺毋滥,读错位数据比缺数据更糟)。
        """
        area_name = f'TAB-{target_screen.split("-")[1]}'
        click_result = find_and_click_area(self.ctx, self.screenshot(), target_screen, area_name)
        if click_result != OcrClickResultEnum.OCR_CLICK_SUCCESS:
            log.warning(f'[账号档案] TAB 点击失败: {target_screen}')
            return False
        time.sleep(1.2)
        return is_target_screen(self.ctx, self.screenshot(), screen_name=target_screen)

    def _click_and_read_name(self, cx: int, cy: int) -> str | None:
        """点击列表格,读右侧详情的角色名(过滤星标/玩家名/非名字文本)。"""
        self.ctx.controller.click(Point(cx, cy), press_time=0.1)
        time.sleep(1.3)
        return self._read_detail_name()

    def _read_detail_name(self) -> str | None:
        log.info('[档案诊断] _read_detail_name 被调用')
        """读详情页角色名;经 normalize_cn_name 清洗,噪声名视为未识别。"""
        shot = self.screenshot()
        for r in self.ctx.ocr.ocr(shot):
            x, y = int(r.x), int(r.y)
            if NAME_X_RANGE[0] <= x <= NAME_X_RANGE[1] and NAME_Y_RANGE[0] <= y <= NAME_Y_RANGE[1]:
                raw = str(r.data or '')
                if '等级' in raw or '属性' in raw:
                    continue
                return normalize_cn_name(raw)
        return None

    def _read_area_text(self, screen_name: str, area_name: str, screen: MatLike) -> str:
        """按 screen_info 读区裁剪 OCR,拼接文本;读区不存在或无文本返回空串。"""
        rect = self._area_rect(screen_name, area_name)
        if rect is None:
            return ''
        texts = ocr_rect_texts(self.ctx.ocr.ocr, screen, rect)
        return ' '.join(texts).strip()

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

    def _scroll_down(self) -> None:
        """列表向下滚一屏。

        实测(角色列表侧栏):拖 300px = 内容滚 2 行,屏间重叠 ~4 行不漏格;
        滚轮在本列表推进量不稳定,已弃用。
        """
        self.ctx.controller.drag_to(Point(280, 500), start=Point(280, 800), duration=0.4)
        time.sleep(SCROLL_SETTLE_SEC)

    def _save_output(self) -> None:
        """扫描结果落盘 config/idx/account_profile_scan.json。"""
        payload = {
            'count': len(self.profiles),
            'characters': [self.profiles[cn] for cn in sorted(self.profiles)],
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
