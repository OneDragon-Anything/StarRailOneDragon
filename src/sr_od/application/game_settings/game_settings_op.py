"""切换游戏内文本语言的 operation(简体中文 ↔ English)。

用途:快速切换游戏显示语言(如切 English 读官方英文名做数据回填),完成后
游戏与 ``game_config.lang`` 保持一致。经 MCP ``run_operation`` 运行:

    op_id = 'sr_od.application.game_settings.game_settings_op.SwitchLanguageOp'
    args  = {'target_lang': 'en'}   # 或 'cn'

完成时同步两件事:
- ``game_config.lang`` 更新为目标语言(项目多语言状态源:i18 默认语言、
  OCR 阈值表、窗口标题都按它取值);同时兼作「配置与实际漂移」的校正入口
  —— 配置说已是目标语言时仍会进语言页读实际值,漂移则照常切换;
- 控制器窗口标题刷新 —— 游戏切文本语言会连窗口标题一起改
  (cn=崩坏：星穹铁道 / en=Honkai: Star Rail),控制器按标题查找窗口,
  不同步刷新 = 本次运行结束后窗口失明。

导航复用现成件:``OpenPhoneMenu``(ESC 开菜单 + BackToNormalWorldPlus 兜底,
任何画面可达)、``ClickPhoneMenuItem(SETTINGS)``(模板匹配设置图标,语言
无关)。语言页内的判定走框架 gt 翻译:screen_info 文本 area 的 text 写中文,
``find_area`` 匹配时经 ``gt(text, 'game')`` 按当前 i18 语言翻译(en 词条在
``assets/text/game/en.po`` → 编译进 game.mo)。点击目标全是固定位置控件;
弹窗(资源下载确认/使用确认)文案随发起时界面语言,与 gt 方向自洽。

边界:op 的 gt 翻译方向 = 配置语言 —— 「界面英文 + 配置 cn」的漂移态下
文本锚匹配会失效,先用 MCP ``update_game_config(lang='en')`` 校正配置再跑
本 op(target='cn')。切换到 en 且英文文本资源未下载时,游戏弹资源下载确认
+ 使用确认两个弹窗,本 op 自动逐个点确认。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from one_dragon.utils.i18_utils import gt, update_default_lang
from one_dragon.utils.str_utils import find_in_list_with_fuzzy
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.menu import phone_menu_const, phone_menu_utils
from sr_od.operations.sr_operation import SrOperation

_WORLD_SCREEN: str = '大世界'
_MENU_SCREEN: str = '菜单'
_IMAGE_SCREEN: str = '设置-图像'
_LANG_SCREEN: str = '设置-语言'

_CN_VALUE: str = '简体中文'
_EN_VALUE: str = 'English'

#: 文本语言下拉当前值的判定词(OCR 相似匹配目标;下拉当前值是「值域解析」,
#: 不走 area.text 翻译 —— 同一值区在两种界面语言下显示不同语言名)
_LANG_VALUE_WORDS: dict[str, str] = {'cn': _CN_VALUE, 'en': _EN_VALUE}


class SwitchLanguageOp(SrOperation):
    """切换游戏内文本语言到目标语言,终点 = 语言已切换且配置已同步。

    参数:
        target_lang: 目标文本语言,取 ``GameLanguageEnum`` 的 value('cn'/'en')。

    失败:语言页读区持续读不出值 / 弹窗处理超限。
    """

    def __init__(self, ctx: SrContext, target_lang: str = 'cn'):
        self.target_lang: str = target_lang
        self.target_value: str = _LANG_VALUE_WORDS.get(target_lang, _CN_VALUE)
        SrOperation.__init__(self, ctx, op_name=gt('切换游戏语言'),
                             node_max_retry_times=40)

    @operation_node(name='打开菜单', is_start_node=True)
    def open_menu(self) -> OperationRoundResult:
        """自判定循环:
        - 菜单已开(开拓等级锚,gt 按 i18 翻译双语可用)→ success;
        - 大世界(角色图标模板锚命中)→ 点击手机图标本体展开菜单;点击
          自带把游戏带到前台+键盘焦点的效果,后续 ESC 类键盘操作才有焦点;
        - 两者都不命中 → 纯等待重试,**不在状态不明时点击**(点击菜单已开
          时的同位置会命中左上角活动入口 UI,误开别的界面)。
        大世界是锁光标画面(screen 级 pc_alt=true),area 级 pc_alt 默认
        False,取中心显式 pc_alt=True 点击(先例 back_to_normal_world_plus)。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _MENU_SCREEN, '开拓等级') == FindAreaResultEnum.TRUE:
            return self.round_success()
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _WORLD_SCREEN, '角色图标') == FindAreaResultEnum.TRUE:
            menu_area = self.ctx.screen_loader.get_area(_WORLD_SCREEN, '按钮-手机菜单')
            self.ctx.controller.click(menu_area.rect.center, pc_alt=True)
            # wait ≥ 菜单展开动画实测时长,判定跑在动画里会失败
            return self.round_retry('已点击手机菜单,等待菜单展开', wait=3)
        # 其它画面(设置页/菜单残留页等):标准兜底回到大世界,下轮循环点击图标
        op = BackToNormalWorldPlus(self.ctx)
        return self.round_retry(op.execute().status, wait=2)

    @node_from(from_name='打开菜单')
    @operation_node(name='打开设置')
    def open_settings(self) -> OperationRoundResult:
        """自判定循环:已在设置页(标题锚 语言/图像,游戏会记忆上次页签)
        → success 带 status;仍在菜单 → 点右侧竖栏「设置」齿轮后重试。

        设置齿轮模板匹配(phone_menu_item_26_settings,语言无关)只在菜单态
        做 —— 点击生效后菜单关闭,再匹配侧栏必然失败,会误报「找不到」。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '标题-语言') == FindAreaResultEnum.TRUE:
            return self.round_success(status='ON_LANGUAGE')
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _IMAGE_SCREEN, '标题-图像') == FindAreaResultEnum.TRUE:
            return self.round_success(status='ON_IMAGE')
        result = phone_menu_utils.get_phone_menu_item_pos_at_right(
            self.ctx, self.last_screenshot, phone_menu_const.SETTINGS)
        if result is None:
            return self.round_retry('菜单侧栏未找到设置图标', wait=1.5)
        self.ctx.controller.click(result.center)
        return self.round_retry('已点击设置,等待设置页打开', wait=2.5)

    @node_from(from_name='打开设置')
    @operation_node(name='切到语言页签')
    def open_lang_tab(self) -> OperationRoundResult:
        """自判定循环:已在语言页 → success;图像页 → 点语言页签后重试;
        两页标题都未命中 → 设置页尚未打开/加载中,等待重试。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '标题-语言') == FindAreaResultEnum.TRUE:
            return self.round_success()
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _IMAGE_SCREEN, '标题-图像') == FindAreaResultEnum.TRUE:
            tab_area = self.ctx.screen_loader.get_area(_IMAGE_SCREEN, '页签-语言')
            self.ctx.controller.click(tab_area.rect.center)
            return self.round_retry('已点击语言页签,等待切换', wait=1.5)
        return self.round_retry('设置页标题未命中,等待页面打开', wait=2)

    @node_from(from_name='切到语言页签')
    @node_from(from_name='等待切换生效', status='NOT_SWITCHED')
    @operation_node(name='展开选项列表')
    def expand_options(self) -> OperationRoundResult:
        """展开文本语言下拉(单职责:只保证列表展开,不碰选项)。

        已是目标语言(幂等短路)→ SWITCHED;列表已展开(「文本资源管理」
        是列表底部独有锚,未展开时该位置是第二个下拉框区域)→ 进入选择;
        未展开 → 点下拉后重试(下拉展开动画 ~1.5-1.8s,动画未结束时点击
        列表项会被忽略,wait 须覆盖)。"""
        value = self._read_lang_value()
        if value == self.target_lang:
            return self.round_success(status='SWITCHED')
        if value is None:
            return self.round_retry('读区读不出语言值,等待界面稳定', wait=4)
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '锚-列表展开') == FindAreaResultEnum.TRUE:
            return self.round_success(status='EXPANDED')
        dropdown_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '下拉-文本语言')
        self.ctx.controller.click(dropdown_area.rect.center)
        return self.round_retry('已点开文本语言下拉,等待列表展开', wait=3)

    @node_from(from_name='展开选项列表', status='EXPANDED')
    @operation_node(name='选择目标语言')
    def select_language(self) -> OperationRoundResult:
        """列表展开态下点击目标语言项。判项区域 (1405,278)-(1830,345) 在
        展开态覆盖列表第一行;未展开态该位置是第二个下拉框 —— en 界面下
        Voice 行显示 'Chinese' 与 gt('简体中文')='Chinese' 同词,不先锚定
        「列表已展开」就会误判并点开 Voice 下拉(en→cn 反复失败实测根因)。"""
        item_area_name = '项-简体中文' if self.target_lang == 'cn' else '项-English'
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, item_area_name) != FindAreaResultEnum.TRUE:
            return self.round_retry('目标语言项未可见,等待列表稳定', wait=1.5)
        item_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, item_area_name)
        self.ctx.controller.click(item_area.rect.center)
        return self.round_success(status='CLICKED')

    @node_from(from_name='选择目标语言', status='CLICKED')
    @operation_node(name='等待切换生效')
    def wait_switch_applied(self) -> OperationRoundResult:
        """点击选项后的纯等待:游戏重载整包文本资源(en↔cn 实测 >10s),
        期间读区可能读不出值。任何后续点击都会干扰(点下拉=再展开、点选项
        =反向切换),本节点零点击,以「读值 = 目标」为出口。

        首次切换到 en 时游戏弹资源下载确认 + 使用确认两个弹窗(发起时界面
        为中文,弹窗文案为中文,gt 方向自洽),自动逐个点确认。"""
        if screen_utils.find_area(self.ctx, self.last_screenshot,
                                  _LANG_SCREEN, '弹窗-标题资源下载') == FindAreaResultEnum.TRUE:
            confirm_area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '弹窗-确认按钮')
            self.ctx.controller.click(confirm_area.rect.center)
            return self.round_retry('弹窗已确认,等待下一状态(下载/应用)', wait=3)

        value = self._read_lang_value()
        if value == self.target_lang:
            return self.round_success(status='SWITCHED')
        if value is None:
            return self.round_retry('界面重载中,读区暂不可读', wait=4)
        # 读值仍是旧语言:点击未生效(如落在展开动画中),回展开节点重走
        return self.round_retry(status='NOT_SWITCHED', wait=2)

    @node_from(from_name='展开选项列表', status='SWITCHED')
    @node_from(from_name='等待切换生效', status='SWITCHED')
    @operation_node(name='同步配置')
    def save_config(self) -> OperationRoundResult:
        """语言已切换:更新 game_config.lang + 刷新控制器窗口标题 + i18 默认语言。"""
        self.ctx.game_config.lang = self.target_lang
        self.ctx.controller.set_window_title(self.ctx.game_config.win_title)
        update_default_lang(self.ctx.game_config.lang)
        return self.round_success(
            f'游戏语言已切换为 {self.target_value},配置与窗口标题已同步')

    def _read_lang_value(self) -> str | None:
        """OCR 读「文本语言」下拉当前值,返回 cn/en/None(读不出)。

        值域解析不走 area.text 翻译:同一值区在两种界面语言下显示不同语言名
        (cn 界面显示「简体中文」,en 界面显示 'English'),双语词表直判。"""
        area = self.ctx.screen_loader.get_area(_LANG_SCREEN, '读区-文本语言值')
        results = self.ctx.ocr_service.get_ocr_result_list(
            self.last_screenshot, rect=area.rect)
        texts = [r.data for r in results]
        for lang_code, word in _LANG_VALUE_WORDS.items():
            if find_in_list_with_fuzzy(word, texts) is not None:
                return lang_code
        return None


def __debug():
    ctx = SrContext()
    ctx.init_by_config()
    op = SwitchLanguageOp(ctx, target_lang='en')
    op.execute()


if __name__ == '__main__':
    __debug()
