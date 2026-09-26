# -*- coding: utf-8 -*-
"""坐标轴布局：范围、比例、网格、三维视角。

这里的函数都只依赖传进来的 ``ax`` 与 ``view`` 字典，
不读实例状态，方便单独测试。

``view`` 支持的全部键
---------------------
范围
    ``xlim`` / ``ylim`` / ``zlim``
比例与刻度
    ``aspect`` / ``xscale`` / ``yscale``
网格
    ``grid`` / ``grid_color`` / ``grid_linestyle`` / ``grid_alpha``
    / ``grid_linewidth``
三维视角
    ``elev`` / ``azim`` / ``roll`` / ``box_aspect`` / ``proj_type``

公开 API
--------
``apply_2d_view(ax, view, axis)``     应用二维设置，返回写死的范围
``apply_3d_view(ax, view)``           应用三维设置，返回写死的范围
``apply_view(ax, view, dimension, axis)``  按维度分派
``apply_grid_style(ax, view)``        只应用网格细分样式
``normalize_axis_limit(...)``         把 animate() 的范围参数标准化
``as_limit_dict(limits, name)``       把范围参数统一成 ``{subplot: 范围}``
``resolve_subplots(subplots, available)``
"""

from __future__ import annotations

import numpy as np

from .compat import call_with_supported

#: ``view`` 里属于「网格细分样式」的键 -> ``ax.grid()`` 的参数名。
GRID_STYLE_KEYS = (
    ("grid_color", "color"),
    ("grid_linestyle", "linestyle"),
    ("grid_alpha", "alpha"),
    ("grid_linewidth", "linewidth"),
)

#: ``view`` 里所有被坐标轴层面消费的键。
VIEW_KEYS = frozenset({
    "xlim", "ylim", "zlim",
    "aspect", "xscale", "yscale",
    "grid", "grid_color", "grid_linestyle", "grid_alpha",
    "grid_linewidth",
    "elev", "azim", "roll", "box_aspect", "proj_type",
})


def apply_grid_style(ax, view):
    """应用网格的细分样式。

    这些键只在 ``view`` 里显式给出时才生效。
    """

    grid_kwargs = {}

    for key, target in GRID_STYLE_KEYS:
        if key in view and view[key] is not None:
            grid_kwargs[target] = view[key]

    if grid_kwargs:
        ax.grid(True, **grid_kwargs)


def apply_3d_view(ax, view):
    """应用三维坐标轴设置。

    返回本次真正写死的坐标轴范围，例如 ``{"xlim": (-3, 3)}``。
    没有写范围的项目不会出现在返回值里，
    :class:`~multiplotter.animation.AnimationPlotter` 依赖它判断
    动画的坐标轴范围是否固定。
    """

    view = view or {}

    elev = view.get("elev")
    azim = view.get("azim")
    roll = view.get("roll")

    if elev is not None or azim is not None or roll is not None:
        view_kwargs = {"elev": elev, "azim": azim}

        if roll is not None:
            view_kwargs["roll"] = roll

        # 旧版本 Matplotlib 的 view_init 不接受 roll
        call_with_supported(ax.view_init, **view_kwargs)

    if "box_aspect" in view:
        ax.set_box_aspect(view["box_aspect"])

    if "proj_type" in view:
        ax.set_proj_type(view["proj_type"])

    explicit_limits = {}

    if "xlim" in view:
        ax.set_xlim(view["xlim"])
        explicit_limits["xlim"] = view["xlim"]

    if "ylim" in view:
        ax.set_ylim(view["ylim"])
        explicit_limits["ylim"] = view["ylim"]

    if "zlim" in view:
        ax.set_zlim(view["zlim"])
        explicit_limits["zlim"] = view["zlim"]

    if "grid" in view:
        ax.grid(view["grid"])

    apply_grid_style(ax, view)

    return explicit_limits


def apply_2d_view(ax, view, axis=None):
    """应用二维坐标轴设置。

    返回本次真正写死的坐标轴范围，
    例如 ``{"xlim": (-3, 3), "ylim": (-3, 3)}``。
    """

    view = view or {}

    aspect = view.get("aspect", axis)

    # add_plot() 的 axis 默认值是空字符串，
    # 空字符串不能传给 set_aspect()，这里统一按“不设置比例”处理。
    if isinstance(aspect, str) and not aspect.strip():
        aspect = None

    if aspect is not None:
        ax.set_aspect(aspect)

    # 坐标轴级别的比例设置（注意：不能通过 **kwargs 传给 ax.bar/ax.imshow）
    if "xscale" in view:
        ax.set_xscale(view["xscale"])

    if "yscale" in view:
        ax.set_yscale(view["yscale"])

    explicit_limits = {}

    if "xlim" in view:
        ax.set_xlim(view["xlim"])
        explicit_limits["xlim"] = view["xlim"]

    if "ylim" in view:
        ax.set_ylim(view["ylim"])
        explicit_limits["ylim"] = view["ylim"]

    if "grid" in view:
        ax.grid(view["grid"])
    else:
        ax.grid(True, linestyle="--", alpha=0.3)

    apply_grid_style(ax, view)

    return explicit_limits


def apply_view(ax, view, dimension=2, axis=None):
    """按维度分派到 :func:`apply_3d_view` 或 :func:`apply_2d_view`。"""

    if int(dimension) == 3:
        return apply_3d_view(ax, view)

    return apply_2d_view(ax, view, axis=axis)


# ----------------------------------------------------------------------
# animate() 的范围参数
# ----------------------------------------------------------------------


def as_limit_dict(limits, name):
    """把用户传入的范围参数统一成 ``{subplot序号: 范围}`` 的形式。

    支持三种写法：

    ================================  ==============================
    ``(0, 10)``                       所有子图都用这一个范围
    ``{0: (0, 10), 1: (-1, 1)}``      每个子图分别指定
    ``{0: ((0, 10), (-1, 1))}``       同一个子图同时指定 x、y
    ================================  ==============================
    """

    if limits is None:
        return {}

    if isinstance(limits, dict):
        return {int(subplot): value for subplot, value in limits.items()}

    # 元组 / 列表形式视为“同一个范围”，后面统一套给所有子图
    return {"__all__": limits}


def normalize_axis_limit(value, dimension, axis_name):
    """把单个范围参数标准化成 ``(轴名称, 范围)`` 的列表。

    例::

        (0, 10)      + dimension=2 -> [("xlim", (0, 10)), ("ylim", (0, 10))]
        ((0, 1), (-1, 1))          -> [("xlim", (0, 1)), ("ylim", (-1, 1))]
        5                          -> [("xlim", (5, 5)), ("ylim", (5, 5))]
    """

    if value is None:
        return []

    names = ["xlim", "ylim"]

    if int(dimension) == 3:
        names.append("zlim")

    # 显式按轴分别指定：((xlo, xhi), (ylo, yhi), (zlo, zhi))
    if (
        isinstance(value, (tuple, list))
        and len(value) in (2, 3)
        and all(isinstance(item, (tuple, list, np.ndarray)) for item in value)
    ):
        if len(value) > len(names):
            raise ValueError(
                f"{axis_name}最多只能给出{len(names)}组范围，"
                f"当前得到{len(value)}组"
            )

        return list(zip(names, value))

    # 单个数值：左右端点相同
    if isinstance(value, (int, float, np.integer, np.floating)):
        value = (value, value)

    return [(name, value) for name in names]


def resolve_subplots(subplots, available):
    """把 ``subplots`` 参数解析成一个有序的 subplot 序号列表。

    支持：

    * ``None`` / ``"all"`` -> 所有可动画的子图
    * ``0`` -> 单个子图
    * ``(0, 1)`` / ``[0, 1, 2]`` -> 多个子图
    """

    if subplots is None or subplots == "all":
        return sorted(available)

    if isinstance(subplots, (int, np.integer)):
        return [int(subplots)]

    if isinstance(subplots, (list, tuple, set, np.ndarray)):
        return [int(item) for item in subplots]

    raise TypeError(
        "subplots 必须是 None、'all'、整数或整数序列，"
        f"当前得到{type(subplots).__name__}"
    )


__all__ = [
    "GRID_STYLE_KEYS",
    "VIEW_KEYS",
    "apply_grid_style",
    "apply_3d_view",
    "apply_2d_view",
    "apply_view",
    "as_limit_dict",
    "normalize_axis_limit",
    "resolve_subplots",
]
