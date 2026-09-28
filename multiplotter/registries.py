# -*- coding: utf-8 -*-
"""图层注册表：kind -> 维度 / 入口方法 / 绘制处理器 / 默认参数。

这是本项目的**单一事实来源**：新增一个图层只需要调用一次
:func:`register_layer`（或 :meth:`LayerRegistryMixin.register_layer`），
不用再分别去改 ``SUPPORTED_*`` / ``KIND_DEFAULTS`` / ``PASSTHROUGH_BY_KIND``
/ ``add_layer`` / ``_draw_layer`` 五个地方。

注册表一览
----------
``DRAW_REGISTRY``        ``kind`` -> ``handler(ax, config)``
``LAYER_SPECS``          ``kind`` -> :class:`LayerSpec`（完整契约）
``KIND_DEFAULTS``        ``kind`` -> ``(方法名, 默认参数字典)``（``init()`` 用）
``INIT_KIND_ALIASES``    ``init()`` 的 kind 别名
``PASSTHROUGH_KEYS``     所有图层通用的透传键
``PASSTHROUGH_BY_KIND``  各 kind 专属的透传键
``INIT_STYLE_DEFAULTS``  ``init()`` 认得的全局样式键
``ADD_DISPATCH``         ``kind`` -> ``add_*`` 方法名（``add_layer`` 用）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Sequence

from . import draw_2d, draw_3d, tables, vector_fields

# ----------------------------------------------------------------------
# 绘制注册表（对应重构要求第 2 条）
# ----------------------------------------------------------------------

#: ``kind`` -> 绘制处理器。处理器签名统一为 ``handler(ax, config)``。
DRAW_REGISTRY = {}
DRAW_REGISTRY.update(draw_2d.DRAW_HANDLERS)
DRAW_REGISTRY.update(draw_3d.DRAW_HANDLERS)
DRAW_REGISTRY.update(vector_fields.DRAW_HANDLERS)
DRAW_REGISTRY.update(tables.DRAW_HANDLERS)

#: 二维 / 三维 kind 集合（保留旧名字，供子类覆盖）。
SUPPORTED_2D_KINDS = frozenset({
    "line",
    "scatter",
    "bar",
    "hist",
    "pie",
    "heatmap",
    "image",
    "contour",      # 等高线
    "quiver",       # 矢量场箭头
    "streamplot",   # 矢量场流线
    "table",        # 表格
})

SUPPORTED_3D_KINDS = frozenset({
    "surface",
    "line3d",
    "scatter3d",
    "bar3d",
    "hist3d",
    "quiver3d",     # 三维矢量场箭头
    "stream3d",     # 三维矢量场流线
})

SUPPORTED_KINDS = SUPPORTED_2D_KINDS | SUPPORTED_3D_KINDS


# ----------------------------------------------------------------------
# init() 用的预设
# ----------------------------------------------------------------------

#: 图层级默认参数：``{kind: (方法名, 默认关键字参数)}``。
#:
#: ``init()`` 里不写任何绘图参数时就用这里的预设，
#: 例如 surface 默认开启光照增强、柱状图默认标注数值。
KIND_DEFAULTS = {
    "line": ("add_plot", {
        "linewidth": 2.5,
        "xlabel": "x",
        "ylabel": "y",
    }),
    "scatter": ("add_plot", {
        "s": 42,
        "alpha": 0.85,
        "edgecolors": "none",
        "xlabel": "x",
        "ylabel": "y",
    }),
    "bar": ("add_plot", {
        "edgecolor": "black",
        "linewidth": 0.6,
        "show_values": True,
        "value_format": ".2f",
        "value_offset": 3,
        "value_kwargs": {"fontsize": 9},
        "xlabel": "x",
        "ylabel": "y",
        "view": {"grid": True},
    }),
    "hist": ("add_plot", {
        "bins": 30,
        "edgecolor": "white",
        "linewidth": 0.8,
        "show_values": True,
        "value_format": ".0f",
        "value_offset": 2,
        "value_kwargs": {"fontsize": 7},
        "xlabel": "x",
        "ylabel": "count",
        "view": {"grid": True},
    }),
    "pie": ("add_pie", {
        "show_values": True,
        "value_format": ".1f",
        "value_kwargs": {"fontsize": 9},
        "startangle": 90,
        "wedgeprops": {"linewidth": 1.0, "edgecolor": "white"},
    }),
    "heatmap": ("add_plot", {
        "cmap": "viridis",
        "show_heatmap_values": True,
        "heatmap_value_format": ".2f",
        "heatmap_text_size": 8,
        "colorbar": True,
    }),
    "correlation": ("add_correlation_heatmap", {
        # 相关性矩阵默认显示每个单元格的数值
        "show_values": True,
        "value_format": ".2f",
        "cmap": "coolwarm",
        "colorbar": True,
        "text_size": 9,
        "tick_rotation": 45,
        "view": {"aspect": "equal", "grid": False},
    }),
    "image": ("add_plot", {
        "cmap": "viridis",
        "interpolation": "nearest",
        "colorbar": True,
    }),
    "contour": ("add_contour", {
        "levels": 30,
        "line_levels": 15,
        "cmap": "viridis",
        "filled": True,
        "alpha": 0.75,
        "clabel": True,
        "clabel_kwargs": {"inline": True, "fontsize": 8, "fmt": "%.1f"},
        "colorbar": True,
        "colorbar_kwargs": {"shrink": 0.85, "aspect": 20},
        "view": {"aspect": "equal", "grid": True},
    }),
    "surface": ("add_surface", {
        "cmap": "turbo",
        "edgecolor": "none",
        "alpha": 0.92,
        # 光照增强默认开启
        "light_enhance": {
            "azdeg": 315,
            "altdeg": 55,
            "gamma": 0.65,
            "vert_exag": 1.8,
            "blend_mode": "soft",
        },
        "colorbar": True,
        "colorbar_kwargs": {"shrink": 0.7, "pad": 0.1},
        "view": {
            "elev": 30,
            "azim": -60,
            "box_aspect": (1, 1, 0.7),
            "grid": True,
        },
    }),
    "line3d": ("add_line3d", {
        "linewidth": 3.0,
        "marker": "o",
        "markersize": 4,
        "highlight_zorder": 100,
        "view": {
            "elev": 28,
            "azim": -60,
            "box_aspect": (1, 1, 0.7),
            "grid": True,
        },
    }),
    "scatter3d": ("add_scatter3d", {
        "s": 40,
        "alpha": 0.85,
        "depthshade": True,
        "highlight_zorder": 101,
        "view": {
            "elev": 28,
            "azim": -60,
            "box_aspect": (1, 1, 0.7),
            "grid": True,
        },
    }),
    "bar3d": ("add_bar3d", {
        "color": "steelblue",
        "edgecolor": "black",
        "linewidth": 0.5,
        "alpha": 0.9,
        "show_values": True,
        "value_selection": "auto",
        "max_value_labels": 12,
        "value_format": ".2f",
        "value_offset": 0.03,
        "value_kwargs": {"fontsize": 8},
        "view": {
            "elev": 26,
            "azim": -58,
            "box_aspect": (1, 1, 0.85),
            "grid": True,
        },
    }),
    "hist3d": ("add_hist3d", {
        "bins": (18, 18),
        "cmap": "viridis",
        "edgecolor": "black",
        "linewidth": 0.2,
        "alpha": 0.9,
        "show_values": True,
        "value_selection": "auto",
        "max_value_labels": 12,
        "value_format": ".0f",
        "value_offset": 0.04,
        "value_kwargs": {"fontsize": 7},
        "view": {
            "elev": 30,
            "azim": -60,
            "box_aspect": (1, 1, 0.7),
            "grid": True,
        },
    }),
    "quiver": ("add_quiver", {
        "cmap": "turbo",
        "colorbar": True,
        "colorbar_kwargs": {"shrink": 0.85, "label": "|V|"},
        "width": 0.004,
        "view": {"aspect": "equal", "grid": True},
    }),
    "streamplot": ("add_streamplot", {
        "density": 1.4,
        "line_width": 1.3,
        "cmap": "turbo",
        "arrowsize": 1.2,
        "colorbar": True,
        "colorbar_kwargs": {"shrink": 0.85, "label": "|V|"},
        "view": {"aspect": "equal", "grid": True},
    }),
    "quiver3d": ("add_quiver3d", {
        "density": 11,
        "length": 0.5,
        "cmap": "turbo",
        "colorbar": True,
        "colorbar_kwargs": {"shrink": 0.7, "label": "|V|"},
        "view": {
            "elev": 22,
            "azim": -58,
            "box_aspect": (1, 1, 0.65),
            "grid": True,
        },
    }),
    "stream3d": ("add_stream3d", {
        "line_width": 2.2,
        "n_seeds": 9,
        "seed_radius": 0.55,
        "step_size": 0.05,
        "max_steps": 500,
        "color_by_speed": False,
        "color": "#C62828",
        "view": {
            "elev": 22,
            "azim": -58,
            "box_aspect": (1, 1, 0.65),
            "grid": True,
        },
    }),
    "table": ("add_table", {
        "cell_align": "center",
        "cell_fontsize": 11,
        "cell_height": 0.115,
        "background_color": "#FFFFFF",
        "text_color": "#263238",
        "edge_color": "#B0BEC5",
        "edge_width": 0.9,
        "header_background": "#1976D2",
        "header_text_color": "#FFFFFF",
        "header_bold": True,
        "row_label_background": "#ECEFF1",
        "row_label_text_color": "#263238",
        "row_label_bold": True,
        "zebra_color": "#F5F7F9",
        "highlight_color": "#FFE082",
        "highlight_text_color": "#263238",
        "highlight_bold": True,
        "bbox": [0.02, 0.06, 0.96, 0.82],
        "view": {"xlim": (0.0, 1.0), "ylim": (0.0, 1.0)},
    }),
}

#: ``init()`` 支持的一级 kind 别名 -> 实际绘图 kind。
INIT_KIND_ALIASES = {
    "corr": "correlation",
    "correlation_matrix": "correlation",
    "correlation_heatmap": "correlation",
    "streamline": "streamplot",
    "flow": "streamplot",
    "vector": "quiver",
    "vector3d": "quiver3d",
    "streamline3d": "stream3d",
}

#: 只在 ``init()`` 里存在的「聚合 kind」。
#:
#: 这些名字不是一个真正的图层：它们只是 ``init()`` 的语法糖，
#: 最终会转发到别的 ``add_*`` 方法（例如 ``correlation`` 会调用
#: ``add_correlation_heatmap()``，内部再走 ``add_plot(kind="heatmap")``）。
#: 因此它们**没有**自己的绘制处理器，也不会出现在 ``plot_configs`` 里，
#: 所以 ``validate_layer_config()`` 不适用于它们。
INIT_ONLY_KINDS = frozenset({"correlation"})

# ----------------------------------------------------------------------
# 透传白名单
# ----------------------------------------------------------------------

#: 所有图层都通用的 artist 样式键（会透传给底层 matplotlib 调用）。
PASSTHROUGH_KEYS = {
    "color",
    "alpha",
    "linewidth",
    "linestyle",
    "marker",
    "markersize",
    "markerfacecolor",
    "markeredgecolor",
    "markeredgewidth",
    "cmap",
    "norm",
    "vmin",
    "vmax",
    "zorder",
    "label",
    "visible",
    "rasterized",
    "clip_on",
    "antialiased",
    "hatch",
    "fill",
}

#: 各 kind 专属的透传键（目标是 ``ax.xxx()`` 的真实参数）。
PASSTHROUGH_BY_KIND = {
    "line": {
        "drawstyle", "dashes", "solid_capstyle", "solid_joinstyle",
        "dash_capstyle", "dash_joinstyle", "markevery", "animated",
    },
    "scatter": {
        "s", "c", "edgecolors", "linewidths", "plotnonfinite",
    },
    "bar": {
        "width", "bottom", "align", "edgecolor", "tick_label",
        "log", "orientation", "error_kw",
    },
    "hist": {
        "bins", "range", "density", "weights", "cumulative",
        "histtype", "orientation", "rwidth", "log", "edgecolor",
        "stacked", "align",
    },
    "pie": {
        "explode", "autopct", "startangle", "radius", "counterclock",
        "frame", "rotatelabels", "normalize", "wedgeprops",
        "textprops", "center",
    },
    "image": {
        "interpolation", "origin", "extent", "filternorm",
        "filterrad", "resample", "aspect", "colorbar", "colorbar_kwargs",
    },
    "heatmap": {
        "interpolation", "origin", "extent", "colorbar",
        "colorbar_kwargs", "heatmap_text_size",
    },
    "surface": {
        "rstride", "cstride", "rcount", "ccount", "shade",
        "facecolors", "antialiased", "edgecolor",
    },
    "line3d": {"solid_capstyle", "dashes"},
    "scatter3d": {"s", "depthshade", "edgecolors", "linewidths"},
    "bar3d": {"shade", "lightsource", "edgecolor"},
    "hist3d": {"edgecolor"},
    "quiver": {
        "width", "headwidth", "headlength", "headaxislength",
        "minshaft", "minlength", "units", "angles", "scale_units",
        "scale", "pivot",
    },
    "streamplot": {
        "density", "linewidth", "arrowsize", "arrowstyle",
    },
    "quiver3d": {
        "arrow_length_ratio", "pivot", "normalize", "length",
    },
    "stream3d": {"step_size", "max_steps", "seeds"},
    "table": {
        "cellLoc", "colWidths", "rowHeight", "colColours",
        "rowColours", "colLabels", "rowLabels", "edges",
    },
}

#: ``init()`` 的全局样式键表（字体、网格、轴、图例等）。
#:
#: 这张表是「已声明的样式键」清单：
#:
#: * 键名 -> 这是一个 ``init()`` 认得的全局样式键
#: * 取值 -> 仅作为文档参考，不参与合并
#:
#: 真正的取值来自 ``init(...)`` 里显式传入的参数。
#: 也就是说「值为 ``None`` 的键不会覆盖图层预设」，这是刻意的设计。
#:
#: 它的作用是尽早发现拼写错误：用 ``init()`` 传了一个不在这张表里、
#: 也不在目标方法签名里的键，``add()`` 会打印警告并把它丢掉。
INIT_STYLE_DEFAULTS = {
    # 字体
    "cell_fontsize": None,
    "header_fontsize": 11.5,
    "text_fontsize": None,
    "fontsize": None,
    # 网格
    "grid": True,
    "grid_linestyle": "--",
    "grid_alpha": 0.45,
    "grid_color": "#CFD8DC",
    # 轴
    "axis": None,
    "scale": None,
    "aspect": None,
    "xscale": None,
    "yscale": None,
    "axis_off": None,
    "ticks_rotation": None,
    # 图例
    "legend": None,
    "legend_kwargs": None,
    "label": None,
    # 通用样式
    "cmap": None,
    "color": None,
    "alpha": None,
    "linewidth": None,
    "marker": None,
    "markersize": None,
    "linestyle": None,
    "edgecolor": None,
    "s": None,
    "zorder": None,
    # 数值标注
    "show_values": None,
    "value_format": None,
    "value_offset": None,
    "value_kwargs": None,
    "value_selection": None,
    "max_value_labels": None,
    "value_threshold": None,
    # 颜色条
    "colorbar": None,
    "colorbar_kwargs": None,
    # 数据范围
    "vmin": None,
    "vmax": None,
}

# ----------------------------------------------------------------------
# 图层契约
# ----------------------------------------------------------------------

#: ``add_layer`` 里「用 labels/values 而不是 x/y」的 kind。
LABELS_VALUES_KINDS = frozenset({"pie"})

#: ``add_layer`` 直接转发给 ``add_plot`` 的 kind。
ADD_PLOT_FORWARD_KINDS = frozenset({
    "line", "scatter", "bar", "hist", "pie", "heatmap", "image",
})

#: ``add_layer`` 用 ``add_*`` 方法名分派的 kind -> 方法名。
#:
#: 这张表由 :func:`build_add_dispatch` 从 ``KIND_DEFAULTS`` 生成，
#: 所以新增图层只要注册一次就会自动进入 ``add_layer``。
def build_add_dispatch(kind_defaults=None):
    """从 ``KIND_DEFAULTS`` 生成 ``add_layer`` 的分派表。"""

    defaults = kind_defaults if kind_defaults is not None else KIND_DEFAULTS

    return {
        kind: method_name
        for kind, (method_name, _) in defaults.items()
        if method_name != "add_plot"
    }


ADD_DISPATCH = build_add_dispatch()


@dataclass(frozen=True)
class LayerSpec:
    """一个图层的完整契约。

    属性
    ----
    kind
        图层类型名。
    dimension
        ``2`` 或 ``3``。
    add_method
        ``add_*`` 方法名（``add_layer`` / ``init()`` 靠它找到入口）。
    draw_handler
        ``(ax, config) -> None`` 的绘制处理器。
    defaults
        ``init()`` 用的默认参数。
    passthrough
        该 kind 专属的透传键。
    aliases
        ``init()`` 里指向本 kind 的别名。
    animatable
        是否声明支持动画（默认支持，因为动画复用 ``draw()``）。
    description
        一句话说明，供文档/调试使用。
    init_only
        是否是「只在 ``init()`` 里存在的聚合 kind」。

        这类 kind 不是一个真正的图层：它只是 ``init()`` 的语法糖，
        最终会转发到别的 ``add_*`` 方法，因此没有自己的绘制处理器，
        也不会出现在 ``plot_configs`` 里。
        对应的检查见 :data:`INIT_ONLY_KINDS`。
    """

    kind: str
    dimension: int
    add_method: str
    draw_handler: Callable
    defaults: Mapping = field(default_factory=dict)
    passthrough: Sequence = field(default_factory=tuple)
    aliases: Sequence = field(default_factory=tuple)
    animatable: bool = True
    description: str = ""
    init_only: bool = False

    def validate(self):
        """校验契约本身是否自洽；不自洽就抛 ``ValueError``。

        检查项（对应重构要求里的「扩展契约可执行校验」）：

        * ``kind`` 是非空字符串；
        * ``dimension`` 是 2 或 3；
        * ``add_method`` 是非空字符串且看起来像方法名；
        * ``draw_handler`` 可调用（``init_only`` 的聚合 kind 除外）；
        * ``defaults`` 是字典；
        * ``passthrough`` / ``aliases`` 是字符串序列；
        * ``animatable`` / ``init_only`` 是布尔值。
        """

        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("register_layer: kind 必须是非空字符串")

        if int(self.dimension) not in (2, 3):
            raise ValueError(
                f"register_layer: dimension 必须是 2 或 3，"
                f"当前为{self.dimension!r}"
            )

        if not isinstance(self.add_method, str) or not self.add_method.strip():
            raise ValueError(
                "register_layer: add_method 必须是非空字符串，"
                "例如 'add_step'"
            )

        if not callable(self.draw_handler) and not self.init_only:
            raise ValueError(
                "register_layer: draw_handler 必须是可调用对象，"
                "签名形如 handler(ax, config)"
            )

        if not isinstance(self.defaults, Mapping):
            raise ValueError(
                "register_layer: defaults 必须是字典，"
                f"当前为{type(self.defaults).__name__}"
            )

        for name, values in (
            ("passthrough", self.passthrough),
            ("aliases", self.aliases),
        ):
            if isinstance(values, str):
                raise ValueError(
                    f"register_layer: {name} 必须是字符串序列，"
                    "单个键也要写成 {'key'} 或 ('key',)"
                )

            if not all(isinstance(item, str) for item in values):
                raise ValueError(
                    f"register_layer: {name} 里必须全是字符串"
                )

        if not isinstance(self.animatable, bool):
            raise ValueError("register_layer: animatable 必须是布尔值")

        if not isinstance(self.init_only, bool):
            raise ValueError("register_layer: init_only 必须是布尔值")

        return self


def make_layer_spec(kind, dimension, add_method, draw_handler,
                    defaults=None, passthrough=(), aliases=(),
                    animatable=True, description="", init_only=False):
    """构造并校验一个 :class:`LayerSpec`。"""

    return LayerSpec(
        kind=kind,
        dimension=int(dimension),
        add_method=add_method,
        draw_handler=draw_handler,
        defaults=dict(defaults or {}),
        passthrough=tuple(passthrough),
        aliases=tuple(aliases),
        animatable=animatable,
        description=description,
        init_only=init_only,
    ).validate()


def _dimension_of(kind, supported_2d=None, supported_3d=None):
    """根据 kind 返回维度，未知 kind 返回 ``None``。"""

    two_d = SUPPORTED_2D_KINDS if supported_2d is None else supported_2d
    three_d = SUPPORTED_3D_KINDS if supported_3d is None else supported_3d

    if kind in two_d:
        return 2

    if kind in three_d:
        return 3

    return None


def build_layer_specs(kind_defaults=None, draw_registry=None,
                      passthrough_by_kind=None, aliases=None,
                      supported_2d=None, supported_3d=None):
    """从内置注册表推导出 ``LAYER_SPECS``。

    这样内置图层也走同一套契约，测试与文档可以统一处理；
    同时保持了「``KIND_DEFAULTS`` 里写了什么就有什么」的旧行为。
    """

    defaults_table = KIND_DEFAULTS if kind_defaults is None else kind_defaults
    handlers = DRAW_REGISTRY if draw_registry is None else draw_registry
    passthrough_table = (
        PASSTHROUGH_BY_KIND if passthrough_by_kind is None
        else passthrough_by_kind
    )
    alias_table = INIT_KIND_ALIASES if aliases is None else aliases

    reverse_aliases = {}

    for alias, target in alias_table.items():
        reverse_aliases.setdefault(target, []).append(alias)

    specs = {}

    for kind, (method_name, preset) in defaults_table.items():
        dimension = _dimension_of(kind, supported_2d, supported_3d)

        if dimension is None:
            # 只在 init() 里存在的聚合 kind（例如 correlation 走 add_plot）
            dimension = 2

        specs[kind] = LayerSpec(
            kind=kind,
            dimension=dimension,
            add_method=method_name,
            draw_handler=handlers.get(kind),
            defaults=dict(preset),
            passthrough=tuple(sorted(passthrough_table.get(kind, ()))),
            aliases=tuple(reverse_aliases.get(kind, ())),
            animatable=True,
            init_only=kind in INIT_ONLY_KINDS,
        )

    return specs


#: ``kind`` -> :class:`LayerSpec`。
LAYER_SPECS = build_layer_specs()


def validate_layer_config(kind, config, registry=None, specs=None):
    """校验一份图层 ``config`` 是否满足框架契约。

    检查项（对应重构要求第 11 条）：

    * 有 ``kind`` 且与传入的 ``kind`` 一致；
    * 有 ``dimension`` 且为 2 或 3；
    * 有 ``subplot`` 且为整数；
    * 有 ``view``（可以是空字典）；
    * ``dimension`` 与注册表里该 kind 的维度一致（如果注册过）；
    * 该 kind 有绘制处理器（如果注册过）。

    返回 ``config`` 本身，方便链式使用。
    """

    registry = DRAW_REGISTRY if registry is None else registry
    specs = LAYER_SPECS if specs is None else specs

    if not isinstance(config, dict):
        raise TypeError(
            f"图层配置必须是字典，当前为{type(config).__name__}"
        )

    if "kind" not in config:
        raise ValueError("图层配置缺少必需字段：kind")

    if config["kind"] != kind:
        raise ValueError(
            f"图层配置的 kind={config['kind']!r} 与注册的 kind={kind!r} 不一致"
        )

    if "dimension" not in config:
        raise ValueError(
            f"kind={kind} 的图层配置缺少必需字段：dimension"
        )

    if int(config["dimension"]) not in (2, 3):
        raise ValueError(
            f"kind={kind} 的 dimension 必须是 2 或 3，"
            f"当前为{config['dimension']!r}"
        )

    if "subplot" not in config:
        raise ValueError(
            f"kind={kind} 的图层配置缺少必需字段：subplot"
        )

    if not isinstance(config["subplot"], (int,)):
        try:
            int(config["subplot"])
        except (TypeError, ValueError):
            raise ValueError(
                f"kind={kind} 的 subplot 必须是整数，"
                f"当前为{config['subplot']!r}"
            ) from None

    spec = specs.get(kind)

    if spec is not None:
        if int(spec.dimension) != int(config["dimension"]):
            raise ValueError(
                f"kind={kind} 注册的维度是 {spec.dimension}，"
                f"但配置里写的是 {config['dimension']}"
            )

        if spec.draw_handler is None and not spec.init_only:
            raise ValueError(
                f"kind={kind} 没有注册绘制处理器；"
                "请用 register_layer(draw_handler=...) 注册，"
                "或在子类里覆盖 _draw_layer()。"
            )

    return config


def describe_layers(specs=None):
    """返回所有已注册图层的可读描述（供文档与调试使用）。"""

    specs = LAYER_SPECS if specs is None else specs

    rows = []

    for kind in sorted(specs):
        spec = specs[kind]
        rows.append({
            "kind": kind,
            "dimension": spec.dimension,
            "add_method": spec.add_method,
            "defaults": dict(spec.defaults),
            "passthrough": sorted(spec.passthrough),
            "aliases": sorted(spec.aliases),
            "animatable": spec.animatable,
            "init_only": spec.init_only,
        })

    return rows


__all__ = [
    "DRAW_REGISTRY",
    "SUPPORTED_2D_KINDS",
    "SUPPORTED_3D_KINDS",
    "SUPPORTED_KINDS",
    "KIND_DEFAULTS",
    "INIT_KIND_ALIASES",
    "INIT_ONLY_KINDS",
    "PASSTHROUGH_KEYS",
    "PASSTHROUGH_BY_KIND",
    "INIT_STYLE_DEFAULTS",
    "LABELS_VALUES_KINDS",
    "ADD_PLOT_FORWARD_KINDS",
    "ADD_DISPATCH",
    "LayerSpec",
    "LAYER_SPECS",
    "make_layer_spec",
    "build_layer_specs",
    "build_add_dispatch",
    "validate_layer_config",
    "describe_layers",
]
