# AUTO-GENERATED — DO NOT EDIT
import sys
if not getattr(sys, 'frozen', False):
    import argparse
    import ast
    import atexit
    import base64
    import builtins
    import concurrent.futures
    import contextlib
    import copy
    import csv
    import ctypes
    import cv2
    import dataclasses
    import datetime
    import difflib
    import functools
    import gettext
    import glob
    import hashlib
    import hmac
    import html
    import importlib
    import importlib.util
    import inspect
    import io
    import itertools
    import joblib
    import json
    import locale
    import logging
    import math
    import matplotlib.font_manager
    import matplotlib.pyplot
    import msvcrt
    import numpy
    import onnxruntime
    import os
    import platform
    import polib
    import psutil
    import pyautogui
    import pyclipper
    import pyuac
    import pywintypes
    import random
    import re
    import requests
    import secrets
    import shutil
    import signal
    import smtplib
    import string
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import traceback
    import urllib.error
    import urllib.parse
    import urllib.request
    import uuid
    import vgamepad
    import weakref
    import webbrowser
    import win32api
    import win32clipboard
    import win32con
    import win32gui
    import win32ui
    import yaml
    import zipfile
    import zlib
    from PIL import Image, ImageDraw, ImageFont
    from PySide6 import QtCore
    from PySide6.QtCore import QEasingCurve, QEvent, QEventLoop, QMimeData, QObject, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QRegularExpression, QSize, QThread, QTimer, QUrl, Qt, Signal
    from PySide6.QtGui import QCloseEvent, QColor, QDesktopServices, QDrag, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QFont, QFontMetrics, QGuiApplication, QIcon, QImage, QKeyEvent, QKeySequence, QLinearGradient, QMouseEvent, QPaintEvent, QPainter, QPainterPath, QPen, QPixmap, QResizeEvent, QShowEvent, QSyntaxHighlighter, QTextCharFormat, QWheelEvent, Qt
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
    from PySide6.QtWidgets import QAbstractButton, QAbstractItemView, QAbstractScrollArea, QApplication, QCompleter, QDialog, QFileDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsEffect, QGraphicsOpacityEffect, QGraphicsScene, QGraphicsView, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListView, QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QStackedWidget, QStyle, QStyledItemDelegate, QTableWidgetItem, QTextEdit, QToolButton, QVBoxLayout, QWidget
    from abc import ABC, abstractmethod
    from basic import Point, Rect
    from basic.i18_utils import gt
    from basic.img import MatchResult, cv2_utils
    from collections import Counter, defaultdict, deque
    from collections.abc import Callable, Iterator, Mapping, Sequence
    from colorama import Fore, Style, init
    from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
    from contextlib import contextmanager, suppress
    from copy import deepcopy
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from ctypes import wintypes
    from ctypes.wintypes import DWORD, HANDLE, RECT, SHORT, UINT, WCHAR, WORD
    from cv2.typing import MatLike
    from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
    from datetime import datetime, timedelta
    from email.header import Header
    from email.mime.image import MIMEImage
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.utils import formataddr
    from enum import Enum, IntEnum, StrEnum
    from errno import EACCES, EBUSY
    from functools import cache, cached_property, lru_cache, partial, wraps
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from io import BytesIO
    from logging import DEBUG
    from logging.handlers import TimedRotatingFileHandler
    from mss import mss
    from mss.base import MSSBase
    from packaging import version
    from pathlib import Path
    from pyautogui import screenshot
    from pygetwindow import Win32Window
    from pygit2 import Blob, Oid, Remote, RemoteCallbacks, Repository, Walker, discover_repository, init_repository, settings
    from pygit2.enums import CheckoutStrategy, ConfigLevel, ResetMode, SortMode
    from pynput import keyboard, mouse
    from pynput.keyboard import Controller, Key
    from pypinyin import Style, lazy_pinyin, pinyin
    from qfluentwidgets import Action, BodyLabel, CaptionLabel, CardWidget, CheckBox, CheckableMenu, ColorDialog, ComboBox, Dialog, DisplayLabel, DoubleSpinBox, EditableComboBox, ExpandSettingCard, FlowLayout, FluentIcon, FluentIconBase, FluentStyleSheet, FluentThemeColor, FluentWindow, FlyoutViewBase, HorizontalFlipView, HyperlinkButton, HyperlinkCard, ImageLabel, IndeterminateProgressBar, IndicatorPosition, InfoBar, InfoBarIcon, InfoBarPosition, LargeTitleLabel, LineEdit, ListItemDelegate, ListWidget, MSFluentWindow, MaskDialogBase, MenuAnimationType, MessageBox, MessageBoxBase, NavigationBar, NavigationBarPushButton, NavigationItemPosition, PillPushButton, PipsPager, PipsScrollButtonDisplayMode, Pivot, PixmapLabel, PlainTextEdit, PopUpAniStackedWidget, PrimaryPushButton, ProgressBar, ProgressRing, PushButton, RoundMenu, ScrollArea, SegmentedWidget, SettingCard, SettingCardGroup, SimpleCardWidget, SpinBox, SplashScreen, SplitTitleBar, StrongBodyLabel, StyleSheetBase, SubtitleLabel, SwitchButton, TableWidget, TeachingTip, TeachingTipTailPosition, Theme, TitleLabel, ToolButton, ToolTip, ToolTipFilter, ToolTipPosition, TransparentPushButton, TransparentToolButton, VBoxLayout, drawIcon, getFont, isDarkTheme, qconfig, qrouter, setCustomStyleSheet, setFont, setTheme, setThemeColor, themeColor
    from qfluentwidgets.common.animation import BackgroundAnimationWidget, ScaleSlideAnimation
    from qfluentwidgets.common.overload import singledispatchmethod
    from qfluentwidgets.common.smooth_scroll import SmoothMode
    from qfluentwidgets.components.navigation.pivot import PivotItem
    from qfluentwidgets.components.settings.expand_setting_card import GroupSeparator
    from qfluentwidgets.components.settings.setting_card import SettingIconWidget
    from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
    from qfluentwidgets.components.widgets.teaching_tip import TeachTipBubble, TeachingTipManager
    from qfluentwidgets.window.stacked_widget import StackedWidget
    from qframelesswindow import FramelessDialog
    from random import random
    from scipy import signal
    from scipy.spatial import KDTree
    from shapely.geometry import Polygon
    from sklearn.linear_model import LogisticRegression
    from sr.context.context import Context
    from sr.operation import Operation
    from threading import Event, Lock
    from types import ModuleType, SimpleNamespace
    from typing import Any, Callable, ClassVar, Dict, Generic, IO, Iterable, List, Literal, NamedTuple, Optional, Protocol, Sequence, Set, TYPE_CHECKING, TextIO, Tuple, Type, TypeAlias, TypeVar, TypedDict, Union, cast
    from urllib.parse import urlsplit
    from yaml import CSafeLoader, SafeLoader
