# -*- coding: utf-8 -*-
"""主题、rcParams 与坐标轴样式。

设计原则（对应重构要求第 4 条）
------------------------------

1. **默认不动全局状态**。``MultiPlotter.draw()`` 默认把主题放进
   ``matplotlib.rc_context()`` 里临时生效，画完自动恢复，
   所以同一个进程里的其它代码、其它 ``MultiPlotter`` 对象都不受影响。
2. **样式是实例级配置**。主题随对象保存（``plotter.theme``），
   而不是写死在模块里。
3. **优先直接设置 Figure / Axes 属性**。例如二维/三维坐标轴背景色是
   直接 ``ax.set_facecolor(...)``，不依赖 rcParams。
4. **不再无条件调用** ``plt.style.use("default")``。想恢复默认外观，
   显式传 ``theme="default"``。

为了兼容旧代码，``matplotlib_option()`` 与 ``matplotlib_surface_option()``
仍然保留，它们会**显式地**修改全局 ``plt.rcParams``（旧行为）。
只有在 ``draw(style_scope="global")`` 时才会走这条路径。

公开 API
--------
``Theme``                        主题对象（rcParams + 坐标轴背景色）
``TWO_D_THEME`` / ``SURFACE_THEME``
``resolve_theme(theme)``         把 str / dict / Theme / None 统一成 Theme
``pick_chinese_fonts()``         挑选系统中真实存在的中文字体
``matplotlib_option()``          旧接口：二维全局样式（显式副作用）
``matplotlib_surface_option()``  旧接口：三维全局样式（显式副作用）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import matplotlib.pyplot as plt
from cycler import cycler

# ----------------------------------------------------------------------
# 中文字体
# ----------------------------------------------------------------------

#: 候选中文字体，按优先级排列。
#: 前面的字体缺失时会自动往后找，保证中文标题不会显示成方框。
CHINESE_FONT_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "WenQuanYi Zen Hei",
    "Noto Sans CJK TC",
    "Arial Unicode MS",
]

#: 没有中文字体时的兜底字体。
FALLBACK_FONTS = ["DejaVu Sans", "Arial"]

_FONT_CACHE = []


def pick_chinese_fonts(refresh=False):
    """返回当前系统中真实存在的中文字体名称列表（按优先级排列）。

    前面是已经安装的候选中文字体，后面补充 DejaVu Sans 等兜底字体；
    如果系统中一个中文字体都没有，则返回完整的候选列表。
    结果会缓存，``refresh=True`` 可强制重新扫描。
    """

    if _FONT_CACHE and not refresh:
        return list(_FONT_CACHE)

    from matplotlib import font_manager

    installed = {font.name for font in font_manager.fontManager.ttflist}

    available = [name for name in CHINESE_FONT_CANDIDATES if name in installed]

    fonts = (
        available + FALLBACK_FONTS
        if available
        else CHINESE_FONT_CANDIDATES + FALLBACK_FONTS
    )

    _FONT_CACHE[:] = fonts

    return list(fonts)


# ----------------------------------------------------------------------
# rcParams
# ----------------------------------------------------------------------

#: 二维与三维共用的 rcParams（除坐标轴背景色外完全一致）。
BASE_RC = {
    # ---- 画布大小与分辨率 ----
    "figure.figsize": (9, 6),
    "figure.dpi": 120,
    # 显示时的画布背景
    "figure.facecolor": "#F7F8FA",
    # 保存图片时的画布背景与边界
    "savefig.facecolor": "#F7F8FA",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
    # ---- 坐标轴边框 ----
    "axes.edgecolor": "#90A4AE",
    "axes.linewidth": 1.0,
    # ---- 标题与坐标轴标签 ----
    "axes.titlesize": 16,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "axes.labelweight": "normal",
    "axes.labelcolor": "#263238",
    # ---- 坐标轴刻度 ----
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "xtick.color": "#455A64",
    "ytick.color": "#455A64",
    # ---- 网格 ----
    "axes.grid": True,
    "grid.color": "#CFD8DC",
    "grid.linestyle": "--",
    "grid.linewidth": 0.8,
    "grid.alpha": 0.65,
    # ---- 默认曲线颜色 ----
    "axes.prop_cycle": cycler(
        color=[
            "#1976D2",  # 蓝色
            "#E64A19",  # 橙红色
            "#388E3C",  # 绿色
            "#7B1FA2",  # 紫色
            "#F57C00",  # 橙色
            "#00796B",  # 青绿色
        ]
    ),
    # ---- 图例 ----
    "legend.fontsize": 10,
    "legend.frameon": True,
    "legend.framealpha": 0.95,
    "legend.facecolor": "#FFFFFF",
    "legend.edgecolor": "#B0BEC5",
    # ---- 负号与字体 ----
    "axes.unicode_minus": False,
}

#: 二维样式：浅色坐标轴面板。
TWO_D_RC = dict(BASE_RC, **{"axes.facecolor": "#FFFFFF"})

#: 三维样式：深色坐标轴面板。
#:
#: 曲面/矢量场本身颜色较深，深色面板在三维里对比更明显；
#: 同时也保留旧版本里的 ``font.size`` 与 ``figure.autolayout``。
SURFACE_RC = dict(
    BASE_RC,
    **{
        "axes.facecolor": "#000000",
        "font.size": 11,
        "figure.autolayout": False,
    },
)

#: 二维 / 三维坐标轴面板颜色（直接设在 Axes 上，不经过 rcParams）。
TWO_D_FACE_COLOR = "#FFFFFF"
SURFACE_FACE_COLOR = "#000000"


@dataclass(frozen=True)
class Theme:
    """一个绘图主题。

    属性
    ----
    name
        主题名称，仅用于报错与调试。
    rc
        临时生效的 rcParams 字典（通过 ``matplotlib.rc_context``）。
    facecolor
        坐标轴面板颜色。二维与三维用不同颜色，所以它单独存放，
        绘制时直接 ``ax.set_facecolor(theme.facecolor)``。
    fonts
        字体列表，单独保存便于查看与覆盖。
    """

    name: str = "default"
    rc: Mapping = field(default_factory=dict)
    facecolor: str = TWO_D_FACE_COLOR
    fonts: tuple = ()

    def rc_context(self, **overrides):
        """返回一个把本主题临时应用上去的上下文管理器。

        用法::

            with theme.rc_context():
                fig = plt.figure()

        退出上下文后全局 ``plt.rcParams`` 自动恢复。
        """

        rc = dict(self.rc)

        if overrides:
            rc.update(overrides)

        return plt.rc_context(rc)

    def with_overrides(self, rc_overrides=None, **kwargs):
        """基于本主题派生一个新主题（不修改原对象）。"""

        rc = dict(self.rc)

        if rc_overrides:
            rc.update(rc_overrides)

        return Theme(
            name=kwargs.get("name", self.name),
            rc=rc,
            facecolor=kwargs.get("facecolor", self.facecolor),
            fonts=tuple(kwargs.get("fonts", self.fonts)),
        )

    def rc_snapshot(self):
        """返回本主题会改动的 rcParams 键值（便于文档与测试使用）。"""

        return dict(self.rc)


def _build_theme(name, rc, facecolor):
    """把 rcParams 与字体组装成 Theme。"""

    rc = dict(rc)
    fonts = tuple(rc.get("font.sans-serif") or pick_chinese_fonts())
    rc["font.sans-serif"] = list(fonts)

    return Theme(name=name, rc=rc, facecolor=facecolor, fonts=fonts)


#: 默认（二维浅色）主题。
TWO_D_THEME = _build_theme("default", TWO_D_RC, TWO_D_FACE_COLOR)

#: 三维深色面板主题。
SURFACE_THEME = _build_theme("surface", SURFACE_RC, SURFACE_FACE_COLOR)

#: 主题名称别名表。
THEME_ALIASES = {
    "default": TWO_D_THEME,
    "2d": TWO_D_THEME,
    "light": TWO_D_THEME,
    "surface": SURFACE_THEME,
    "3d": SURFACE_THEME,
    "dark": SURFACE_THEME,
}

#: ``draw()`` 用的默认主题（图级别 rcParams 只应用一次）。
DEFAULT_THEME = TWO_D_THEME


def resolve_theme(theme):
    """把用户传入的 ``theme`` 统一成 :class:`Theme`。

    支持：

    ==========================  =====================================
    ``None``                    使用 :data:`DEFAULT_THEME`
    ``"default"`` / ``"surface"`` 等名称
    :class:`Theme`              原样返回
    ``dict``                    作为 rcParams 覆盖叠加在默认主题上
    ==========================  =====================================
    """

    if theme is None:
        return DEFAULT_THEME

    if isinstance(theme, Theme):
        return theme

    if isinstance(theme, str):
        resolved = THEME_ALIASES.get(theme.strip().lower())

        if resolved is None:
            raise ValueError(
                "未知的 theme："
                f"{theme!r}；可用名称：{sorted(THEME_ALIASES)}，"
                "也可以直接传 Theme 对象或 rcParams 字典"
            )

        return resolved

    if isinstance(theme, Mapping):
        return DEFAULT_THEME.with_overrides(theme, name="custom")

    raise TypeError(
        "theme 必须是 None、名称字符串、Theme 对象或 rcParams 字典，"
        f"当前为{type(theme).__name__}"
    )


def facecolor_for(dimension, theme=None):
    """返回某个维度应该使用的坐标轴面板颜色。

    没有显式指定主题时，二维用白色、三维用黑色（与旧版本一致）。
    """

    if theme is not None:
        return resolve_theme(theme).facecolor

    return SURFACE_FACE_COLOR if int(dimension) == 3 else TWO_D_FACE_COLOR


def apply_theme_to_axes(ax, dimension=2, theme=None):
    """把主题里与坐标轴相关的属性直接设置到 ``ax`` 上。

    只设置「必须按维度区分」的部分：坐标轴面板颜色。
    其余样式由 ``rc_context`` 在创建 Figure/Axes 时统一生效。
    """

    ax.set_facecolor(facecolor_for(dimension, theme))

    return ax


# ----------------------------------------------------------------------
# 旧接口：显式修改全局 rcParams
# ----------------------------------------------------------------------

def matplotlib_option():
    """旧接口：把二维样式写入全局 ``plt.rcParams``。

    .. deprecated::
       优先使用 ``draw(theme=...)``。本函数会修改整个 Python 进程的
       全局绘图配置，并且会重置 ``plt.style.use("default")``，
       覆盖用户自己的风格。保留它是为了兼容旧代码与显式选择
       全局样式的场景（``draw(style_scope="global")``）。
    """

    plt.style.use("default")
    plt.rcParams.update(TWO_D_RC)
    plt.rcParams["font.sans-serif"] = pick_chinese_fonts()


def matplotlib_surface_option():
    """旧接口：把三维样式写入全局 ``plt.rcParams``。

    .. deprecated::
       语义同 :func:`matplotlib_option`，只是坐标轴面板为深色。
    """

    plt.style.use("default")
    plt.rcParams.update(SURFACE_RC)
    plt.rcParams["font.sans-serif"] = pick_chinese_fonts()


#: ``dimension`` -> 该维度使用的全局样式函数名。
GLOBAL_STYLE_FUNCTIONS = {
    2: "matplotlib_option",
    3: "matplotlib_surface_option",
}


def apply_global_style(dimension):
    """按维度调用全局样式函数（``style_scope="global"`` 时使用）。

    这里刻意通过**模块属性查找**来取函数，而不是直接引用函数对象：

    * 调用方可以 monkeypatch ``multiplotter.styles.matplotlib_option``
      来替换二维样式（旧代码里 ``module.matplotlib_option = patched``
      的等价写法，见 EXTENDING.md 第 13 章）；
    * 子类/插件可以整体换掉全局样式，而不必改本包源码。

    返回被调用的函数名。
    """

    name = GLOBAL_STYLE_FUNCTIONS[3 if int(dimension) == 3 else 2]
    func = globals().get(name)

    if callable(func):
        func()

    return name


__all__ = [
    "CHINESE_FONT_CANDIDATES",
    "FALLBACK_FONTS",
    "BASE_RC",
    "TWO_D_RC",
    "SURFACE_RC",
    "TWO_D_FACE_COLOR",
    "SURFACE_FACE_COLOR",
    "Theme",
    "TWO_D_THEME",
    "SURFACE_THEME",
    "DEFAULT_THEME",
    "THEME_ALIASES",
    "pick_chinese_fonts",
    "resolve_theme",
    "facecolor_for",
    "apply_theme_to_axes",
    "matplotlib_option",
    "matplotlib_surface_option",
    "GLOBAL_STYLE_FUNCTIONS",
    "apply_global_style",
]
