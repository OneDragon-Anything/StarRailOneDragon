from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from pathlib import Path

import requests
from PySide6.QtCore import QSize, Qt, QThread, QUrl, QTimer, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    FluentIcon,
    PillPushButton,
    setCustomStyleSheet,
)

from one_dragon.base.config.custom_config import BackgroundTypeEnum
from one_dragon.utils import os_utils
from one_dragon.utils.log_utils import log
from one_dragon_qt.services.theme_manager import ThemeManager
from one_dragon_qt.utils.color_utils import get_foreground_color
from one_dragon_qt.utils.layout_utils import apply_shadow
from one_dragon_qt.widgets.banner import Banner
from one_dragon_qt.widgets.base_interface import BaseInterface
from one_dragon_qt.widgets.icon_button import IconButton
from one_dragon_qt.widgets.notice_card import NoticeCard
from sr_od.context.sr_context import SrContext
from sr_od.gui.dialog.pre_flight_check_dialog import (
    PreFlightCheckDialog,
    check_pre_flight,
)


class ButtonGroup(QWidget):

    def __init__(self, ctx: SrContext, parent=None):
        QWidget.__init__(self, parent=parent)
        self.ctx = ctx
        self.buttons: list[IconButton] = []

        self.setFixedWidth(70)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(24)
        layout.setContentsMargins(8, 8, 8, 8)

        self._add_button(
            layout,
            FluentIcon.HOME,
            '官网',
            '使用说明 · 功能介绍',
            self.open_home,
            bool(self.ctx.project_config.home_page_link),
        )
        self._add_button(
            layout,
            FluentIcon.GITHUB,
            'GitHub',
            '源码 · 反馈 · Star',
            self.open_github,
            bool(self.ctx.project_config.github_homepage),
        )
        self._add_button(
            layout,
            FluentIcon.LIBRARY,
            '帮助文档',
            '遇到问题？点这里找答案',
            self.open_doc,
            bool(self.ctx.project_config.doc_link or self.ctx.project_config.quick_start_link),
        )
        self._add_button(
            layout,
            FluentIcon.CHAT,
            '官方频道',
            '加入官方交流频道',
            self.open_chat,
            bool(self.ctx.project_config.qq_link),
        )

    def _add_button(self, layout: QVBoxLayout, icon: FluentIcon, tip_title: str,
                    tip_content: str, callback, visible: bool) -> None:
        if not visible:
            return
        button = IconButton(
            icon.icon(color=QColor('#fff')),
            tip_title=tip_title,
            tip_content=tip_content,
            isTooltip=True,
        )
        button.setIconSize(QSize(30, 30))
        button.clicked.connect(callback)
        layout.addWidget(button)
        self.buttons.append(button)

    def open_home(self) -> None:
        url = self.ctx.project_config.home_page_link or self.ctx.project_config.github_homepage
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def open_github(self) -> None:
        if self.ctx.project_config.github_homepage:
            QDesktopServices.openUrl(QUrl(self.ctx.project_config.github_homepage))

    def open_chat(self) -> None:
        if self.ctx.project_config.qq_link:
            QDesktopServices.openUrl(QUrl(self.ctx.project_config.qq_link))

    def open_doc(self) -> None:
        url = self.ctx.project_config.doc_link or self.ctx.project_config.quick_start_link
        if url:
            QDesktopServices.openUrl(QUrl(url))


class BaseThread(QThread):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            self._run_impl()
        finally:
            self._is_running = False

    def _run_impl(self):
        raise NotImplementedError

    def stop(self) -> None:
        self._is_running = False
        if self.isRunning():
            self.quit()
            self.wait(3000)
            if self.isRunning():
                self.terminate()
                self.wait()


class BackgroundImageDownloader(BaseThread):

    image_downloaded = Signal(bool)
    download_starting = Signal()

    def __init__(self, ctx: SrContext, download_type: str, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.download_type = download_type

        ui_dir = Path(os_utils.get_path_under_work_dir('assets', 'ui'))
        self.config_key = f'last_{download_type}_fetch_time'

        if download_type == 'version_poster':
            self.save_path = ui_dir / 'version_poster.webp'
            self.endpoint = 'getGames'
            self.error_msg = '版本海报异步获取失败'
        elif download_type == 'static_background':
            self.save_path = ui_dir / 'static_background.webp'
            self.endpoint = 'getAllGameBasicInfo'
            self.error_msg = '静态背景异步获取失败'
        elif download_type == 'dynamic_background':
            self.save_path = ui_dir / 'dynamic_background.webm'
            self.endpoint = 'getAllGameBasicInfo'
            self.error_msg = '动态背景异步获取失败'
        else:
            raise ValueError(f'Unsupported download type: {download_type}')

    def _run_impl(self):
        if not self.save_path.exists():
            self.get()

        last_fetch_time_str = getattr(self.ctx.custom_config, self.config_key)
        if last_fetch_time_str:
            try:
                last_fetch_time = datetime.strptime(last_fetch_time_str, '%Y-%m-%d %H:%M:%S')
                if datetime.now() - last_fetch_time >= timedelta(days=1):
                    self.get()
            except ValueError:
                self.get()
        else:
            self.get()

    def get(self) -> None:
        if not self._is_running:
            return

        success = False
        try:
            with requests.get(self._build_request_url(), timeout=5) as resp:
                data = resp.json()

            media_url = self._extract_media_url(data)
            if not media_url:
                return

            if self.download_type == 'dynamic_background':
                success = self._download_dynamic_background_video(media_url)
            else:
                with requests.get(media_url, timeout=5) as media_resp:
                    if media_resp.status_code == 200:
                        self._save_media(media_resp.content)
                        success = True

            if success:
                setattr(
                    self.ctx.custom_config,
                    self.config_key,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                self.image_downloaded.emit(True)
        except Exception as exc:
            log.error(f'{self.error_msg}: {exc}')

    def _build_request_url(self) -> str:
        return f'https://hyp-api.mihoyo.com/hyp/hyp-connect/api/{self.endpoint}?launcher_id=jGHBHlcOq1&language=zh-cn'

    def _get_target_game_biz(self) -> set[str]:
        return {'hkrpg_cn'}

    def _extract_media_url(self, data: dict) -> str | None:
        game_biz_set = self._get_target_game_biz()

        if self.download_type == 'version_poster':
            for game in data.get('data', {}).get('games', []):
                if game.get('biz') not in game_biz_set:
                    continue
                return game.get('display', {}).get('background', {}).get('url')

        elif self.download_type == 'static_background':
            for game in data.get('data', {}).get('game_info_list', []):
                if game.get('game', {}).get('biz') not in game_biz_set:
                    continue
                backgrounds = game.get('backgrounds', [])
                if backgrounds:
                    return backgrounds[0].get('background', {}).get('url')

        elif self.download_type == 'dynamic_background':
            for game in data.get('data', {}).get('game_info_list', []):
                if game.get('game', {}).get('biz') not in game_biz_set:
                    continue
                for background in game.get('backgrounds', []):
                    if background.get('type') != 'BACKGROUND_TYPE_VIDEO':
                        continue
                    video_url = background.get('video', {}).get('url')
                    if video_url:
                        return video_url

        return None

    def _save_media(self, content: bytes) -> None:
        temp_path = self.save_path.with_suffix(self.save_path.suffix + '.tmp')
        try:
            with temp_path.open('wb') as file_obj:
                file_obj.write(content)
                file_obj.flush()
            temp_path.replace(self.save_path)
        except Exception:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as cleanup_err:
                    log.warning(f'清理临时文件失败: {cleanup_err}')
            raise

    def _download_dynamic_background_video(self, video_url: str) -> bool:
        self.download_starting.emit()

        temp_path = self.save_path.with_suffix(self.save_path.suffix + '.tmp')
        download_success = False
        cancelled = False
        status_ok = False

        try:
            with requests.get(video_url, stream=True, timeout=30) as resp:
                try:
                    resp.raise_for_status()
                    status_ok = True
                except Exception:
                    status_ok = False

                if status_ok:
                    with temp_path.open('wb') as file_obj:
                        for chunk in resp.iter_content(chunk_size=256 * 1024):
                            if not self._is_running:
                                cancelled = True
                                break
                            if chunk:
                                file_obj.write(chunk)
                        if not cancelled:
                            file_obj.flush()
                            download_success = True
        finally:
            if temp_path.exists() and not download_success:
                with contextlib.suppress(Exception):
                    temp_path.unlink()

        if not status_ok or cancelled or not download_success:
            return False

        try:
            temp_path.replace(self.save_path)
        except Exception:
            if temp_path.exists():
                with contextlib.suppress(Exception):
                    temp_path.unlink()
            raise

        return True


class HomeInterface(BaseInterface):

    def __init__(self, ctx: SrContext, parent=None):
        BaseInterface.__init__(
            self,
            object_name='home_interface',
            nav_text_cn='仪表盘',
            nav_icon=FluentIcon.HOME,
            parent=parent,
        )
        self.ctx: SrContext = ctx
        self.main_window = parent
        self._saved_area_margins = None
        self._ready: bool = False
        self._last_applied_theme_color: tuple[int, int, int] | None = None

        self._init_background_downloaders()
        self._init_ui()

    def _init_background_downloaders(self) -> None:
        self._version_poster_downloader = BackgroundImageDownloader(self.ctx, 'version_poster', self)
        self._version_poster_downloader.image_downloaded.connect(self.reload_banner)

        self._static_background_downloader = BackgroundImageDownloader(self.ctx, 'static_background', self)
        self._static_background_downloader.image_downloaded.connect(self.reload_banner)

        self._dynamic_background_downloader = BackgroundImageDownloader(self.ctx, 'dynamic_background', self)
        self._dynamic_background_downloader.image_downloaded.connect(self.reload_banner)
        self._dynamic_background_downloader.download_starting.connect(
            self._on_dynamic_background_download_start,
            Qt.ConnectionType.BlockingQueuedConnection,
        )

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._banner_widget = Banner(self.choose_banner_media())
        main_layout.addWidget(self._banner_widget)

        v_layout = QVBoxLayout(self._banner_widget)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(5)
        v_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignJustify)
        v_layout.addItem(QSpacerItem(10, 64, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        bottom_bar = QWidget()
        bottom_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        h_layout = QHBoxLayout(bottom_bar)
        h_layout.setContentsMargins(32, 32, 0, 32)

        self.notice_container: NoticeCard | None = None
        if self.ctx.project_config.notice_url:
            self.notice_container = NoticeCard(self.ctx.project_config.notice_url)
            apply_shadow(self.notice_container, blur=28, offset_x=0, offset_y=8, alpha=150)
            h_layout.addWidget(self.notice_container, alignment=Qt.AlignmentFlag.AlignBottom)

        h_layout.addStretch()

        self.start_button = PillPushButton(FluentIcon.PLAY_SOLID, '启动一条龙')
        self.start_button.setObjectName('start_button')
        self.start_button.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        self.start_button.setFixedHeight(48)
        self.start_button.setMinimumWidth(180)
        self.start_button.clicked.connect(self._on_start_game)
        apply_shadow(self.start_button, blur=24, offset_x=0, offset_y=6, alpha=140)

        self._black_icon = FluentIcon.PLAY_SOLID.icon(color=QColor('#000000'))
        self._yellow_icon = FluentIcon.PLAY_SOLID.icon(color=QColor('#FFDB29'))
        self.start_button.enterEvent = self._on_button_enter
        self.start_button.leaveEvent = self._on_button_leave
        h_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignBottom)

        self.button_group = ButtonGroup(self.ctx)
        if self.button_group.buttons:
            self.button_group.setMaximumHeight(320)
            for button in self.button_group.buttons:
                apply_shadow(button)
            h_layout.addWidget(self.button_group, alignment=Qt.AlignmentFlag.AlignVCenter)

        v_layout.addWidget(bottom_bar)
        QTimer.singleShot(0, self._update_start_button_style_from_banner)

    def showEvent(self, event) -> None:
        QWidget.showEvent(self, event)
        self._set_title_bar_home_mode(True)

    def on_interface_shown(self) -> None:
        super().on_interface_shown()

        self._banner_widget.resume_media()

        if self.main_window:
            if self._saved_area_margins is None:
                self._saved_area_margins = self.main_window.areaLayout.contentsMargins()
            self.main_window.areaLayout.setContentsMargins(0, 0, 0, 0)
            self._set_title_bar_home_mode(True)

        if self.ctx.signal.reload_banner:
            self.reload_banner()

        background_type = self.ctx.custom_config.background_type
        if background_type == BackgroundTypeEnum.VERSION_POSTER.value.value:
            if not self._version_poster_downloader.isRunning():
                self._version_poster_downloader.start()
        elif background_type == BackgroundTypeEnum.STATIC.value.value:
            if not self._static_background_downloader.isRunning():
                self._static_background_downloader.start()
        elif background_type == BackgroundTypeEnum.DYNAMIC.value.value:
            if not self._dynamic_background_downloader.isRunning():
                self._dynamic_background_downloader.start()

        self._update_start_button_style_from_banner()
        self._refresh_ready_state()

    def on_interface_leave(self) -> None:
        if self.main_window and self._saved_area_margins is not None:
            self.main_window.areaLayout.setContentsMargins(self._saved_area_margins)
            self._saved_area_margins = None
            self._set_title_bar_home_mode(False)

    def on_interface_hidden(self) -> None:
        super().on_interface_hidden()
        self._banner_widget.pause_media()

        if self._version_poster_downloader.isRunning():
            self._version_poster_downloader.stop()
        if self._static_background_downloader.isRunning():
            self._static_background_downloader.stop()
        if self._dynamic_background_downloader.isRunning():
            self._dynamic_background_downloader.stop()

    def _on_dynamic_background_download_start(self) -> None:
        if self.ctx.custom_config.background_type != BackgroundTypeEnum.DYNAMIC.value.value:
            return
        if hasattr(self._banner_widget, 'release_media'):
            self._banner_widget.release_media()

    def _refresh_ready_state(self) -> None:
        issues = check_pre_flight(self.ctx)
        self._ready = len(issues) == 0
        self._apply_button_icon()
        if self._ready:
            self.start_button.setText('启动一条龙')
        else:
            self.start_button.setText(f'{len(issues)} 项待配置 ')

    def _find_widget_by_name(self, name: str) -> QWidget | None:
        stacked = self.main_window.stackedWidget
        for i in range(stacked.count()):
            widget = stacked.widget(i)
            if widget.objectName() == name:
                return widget
        return None

    @staticmethod
    def _find_sub_widget(stacked: QStackedWidget, name: str) -> QWidget | None:
        for i in range(stacked.count()):
            widget = stacked.widget(i)
            if widget.objectName() == name:
                return widget
        return None

    def _on_start_game(self) -> None:
        self._refresh_ready_state()
        issues = check_pre_flight(self.ctx)
        if issues:
            messages = [msg for msg, _, _ in issues]
            dialog = PreFlightCheckDialog(messages, self)
            if dialog.exec():
                _, target_name, sub_name = issues[0]
                target = self._find_widget_by_name(target_name)
                if target is not None:
                    self.main_window.switchTo(target)
                    if sub_name is not None and hasattr(target, 'stacked_widget'):
                        sub = self._find_sub_widget(target.stacked_widget, sub_name)
                        if sub is not None:
                            target.stacked_widget.setCurrentWidget(sub)
                return

        self.ctx.signal.start_onedragon = True
        target = self._find_widget_by_name('one_dragon_interface')
        if target is not None:
            self.main_window.switchTo(target)

    def _on_button_enter(self, event) -> None:
        self.start_button.setIcon(self._yellow_icon)
        PillPushButton.enterEvent(self.start_button, event)

    def _on_button_leave(self, event) -> None:
        self.start_button.setIcon(self._black_icon)
        PillPushButton.leaveEvent(self.start_button, event)

    def reload_banner(self) -> None:
        self._banner_widget.set_media(self.choose_banner_media())
        self._update_start_button_style_from_banner()
        self.ctx.signal.reload_banner = False

    def choose_banner_media(self) -> str:
        custom_banner_path = Path(os_utils.get_path_under_work_dir('custom', 'assets', 'ui')) / 'banner'
        ui_dir = Path(os_utils.get_path_under_work_dir('assets', 'ui'))
        version_poster_path = ui_dir / 'version_poster.webp'
        static_background_path = ui_dir / 'static_background.webp'
        dynamic_background_path = ui_dir / 'dynamic_background.webm'
        index_banner_path = ui_dir / 'index.png'

        if self.ctx.custom_config.custom_banner and custom_banner_path.exists() and custom_banner_path.is_file():
            return str(custom_banner_path)

        background_type = self.ctx.custom_config.background_type
        if background_type == BackgroundTypeEnum.VERSION_POSTER.value.value and version_poster_path.exists():
            return str(version_poster_path)
        if background_type == BackgroundTypeEnum.STATIC.value.value and static_background_path.exists():
            return str(static_background_path)
        if background_type == BackgroundTypeEnum.DYNAMIC.value.value and dynamic_background_path.exists():
            return str(dynamic_background_path)
        return str(index_banner_path)

    def _update_start_button_style_from_banner(self) -> None:
        if not hasattr(self, 'start_button'):
            return

        theme_color = self._get_theme_color()
        if theme_color == self._last_applied_theme_color:
            return
        self._last_applied_theme_color = theme_color

        self.ctx.custom_config.theme_color = theme_color
        ThemeManager.set_theme_color(theme_color)
        self._apply_button_style(theme_color)

    def _set_title_bar_home_mode(self, enable: bool) -> None:
        if not self.main_window or not hasattr(self.main_window, 'titleBar'):
            return
        if enable and self.main_window.stackedWidget.currentWidget() is not self:
            return
        self.main_window.titleBar.set_home_mode(enable)

    def _get_theme_color(self) -> tuple[int, int, int]:
        if self.ctx.custom_config.custom_theme_color:
            return self.ctx.custom_config.theme_color
        return self._banner_widget.theme_color

    def _apply_button_style(self, theme_color: tuple[int, int, int]) -> None:
        r, g, b = theme_color
        foreground = get_foreground_color(r, g, b)
        theme_bg = f'rgb({r}, {g}, {b})'
        hover_bg = foreground

        self._apply_button_icon()

        qss = f"""
        PillPushButton#start_button {{
            background-color: {theme_bg};
            color: {foreground};
            border-radius: 28px;
            height: 48px;
            min-height: 48px;
            padding-top: 2px;
        }}
        PillPushButton#start_button:hover {{
            background-color: {hover_bg};
            color: {theme_bg};
            padding-top: 2px;
        }}
        """
        setCustomStyleSheet(self.start_button, qss, qss)

    def _apply_button_icon(self) -> None:
        if not hasattr(self, 'start_button'):
            return
        icon = FluentIcon.PLAY_SOLID if self._ready else FluentIcon.SETTING
        r, g, b = self._get_theme_color()
        foreground = get_foreground_color(r, g, b)
        self._black_icon = icon.icon(color=QColor(foreground))
        self._yellow_icon = icon.icon(color=QColor(r, g, b))
        self.start_button.setIcon(self._black_icon)