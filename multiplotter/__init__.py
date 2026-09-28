# -*- coding: utf-8 -*-
"""MultiPlotter：统一的二维 / 三维科研绘图包。

快速开始::

    from multiplotter import MultiPlotter

    plotter = MultiPlotter(ncols=2)
    plotter.add_plot(kind="line", x=[0, 1, 2], y=[0, 1, 4], subplot=0)
    plotter.add_surface(X, Y, Z, subplot=1)
    fig, axes = plotter.draw(show=False)

动画::

    from multiplotter import AnimationPlotter

包结构
------
======================  ==========================================
``multiplotter.core``   ``MultiPlotter`` 基础状态与公共接口
``multiplotter.builder````PlotBuilder`` 会话式绘图
``multiplotter.styles`` 主题与 rcParams
``multiplotter.layout`` 坐标轴范围 / 比例 / 网格 / 三维视角
``multiplotter.validation`` 参数校验与规格化
``multiplotter.draw_2d`` 二维图层
``multiplotter.draw_3d`` 三维图层
``multiplotter.vector_fields`` 矢量场（quiver / streamplot / stream3d）
``multiplotter.tables`` 表格与单元格样式
``multiplotter.animation`` ``AnimationPlotter``
``multiplotter.saving`` 保存路径与 writer
``multiplotter.registries`` 图层注册表（单一事实来源）
``multiplotter.science`` 科研算法与绘图的组合接口
======================  ==========================================
"""

from .animation import AnimationPlotter
from .builder import PlotBuilder
from .compat import (
    MATPLOTLIB_MIN,
    MATPLOTLIB_TESTED,
    call_with_supported,
    filter_kwargs,
    mpl_at_least,
    mpl_version,
    supports_parameter,
    warn_version,
)
from .core import MultiPlotter
from .registries import (
    ADD_DISPATCH,
    DRAW_REGISTRY,
    INIT_KIND_ALIASES,
    INIT_ONLY_KINDS,
    INIT_STYLE_DEFAULTS,
    KIND_DEFAULTS,
    LAYER_SPECS,
    PASSTHROUGH_BY_KIND,
    PASSTHROUGH_KEYS,
    SUPPORTED_2D_KINDS,
    SUPPORTED_3D_KINDS,
    SUPPORTED_KINDS,
    LayerSpec,
    describe_layers,
    make_layer_spec,
    validate_layer_config,
)
from .science import (
    SciencePlotter,
    ScienceResult,
    convective_heat_transfer,
)
from .saving import (
    get_unique_filename,
    resolve_animation_writer,
    resolve_save_path,
    save_figure,
)
from .styles import (
    CHINESE_FONT_CANDIDATES,
    SANS_FONT_CANDIDATES,
    SURFACE_THEME,
    THEME_ALIASES,
    TWO_D_THEME,
    Theme,
    bind_theme_to_figure,
    matplotlib_option,
    matplotlib_surface_option,
    pick_chinese_fonts,
    pick_sans_fonts,
    resolve_theme,
)

#: 版本号（与 pyproject.toml 保持一致）。
__version__ = "0.3.0"

__all__ = [
    # 主要类
    "MultiPlotter",
    "AnimationPlotter",
    "PlotBuilder",
    "SciencePlotter",
    "ScienceResult",
    # 科研组合
    "convective_heat_transfer",
    # 主题
    "Theme",
    "bind_theme_to_figure",
    "TWO_D_THEME",
    "SURFACE_THEME",
    "THEME_ALIASES",
    "resolve_theme",
    "pick_sans_fonts",
    "pick_chinese_fonts",
    "CHINESE_FONT_CANDIDATES",
    "SANS_FONT_CANDIDATES",
    "matplotlib_option",
    "matplotlib_surface_option",
    # 注册表与扩展
    "DRAW_REGISTRY",
    "LAYER_SPECS",
    "LayerSpec",
    "KIND_DEFAULTS",
    "INIT_KIND_ALIASES",
    "INIT_ONLY_KINDS",
    "INIT_STYLE_DEFAULTS",
    "PASSTHROUGH_KEYS",
    "PASSTHROUGH_BY_KIND",
    "SUPPORTED_2D_KINDS",
    "SUPPORTED_3D_KINDS",
    "SUPPORTED_KINDS",
    "ADD_DISPATCH",
    "describe_layers",
    "make_layer_spec",
    "validate_layer_config",
    # 保存
    "get_unique_filename",
    "resolve_save_path",
    "save_figure",
    "resolve_animation_writer",
    # 版本兼容
    "MATPLOTLIB_MIN",
    "MATPLOTLIB_TESTED",
    "mpl_version",
    "mpl_at_least",
    "supports_parameter",
    "filter_kwargs",
    "call_with_supported",
    "warn_version",
    "__version__",
]
