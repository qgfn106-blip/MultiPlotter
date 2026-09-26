# -*- coding: utf-8 -*-
"""兼容入口：保留旧的 ``from Multiplotter import ...`` 写法。

重构后代码已经拆到 :mod:`multiplotter` 包里，本模块只是转发，
**没有自己的实现**。推荐新代码直接::

    from multiplotter import MultiPlotter, AnimationPlotter, PlotBuilder

但为了不破坏已有的外部引用（``from Multiplotter import AnimationPlotter``
以及 ``import Multiplotter as module`` 后替换 ``module.matplotlib_option``），
这里把包里的公开名字原样再导出一次。

注意：``extension_test.py`` 里那种

    import Multiplotter as module
    module.matplotlib_option = patched

的写法在重构后**仍然有效**，因为 ``MultiPlotter.draw()`` 内部是通过
``multiplotter.core`` 里导入的名字调用 option 函数的；本模块的
``matplotlib_option`` 只是同一个函数对象的另一个引用。
如果你需要 monkeypatch 生效于全局样式路径，请打补丁到
``multiplotter.core.matplotlib_option``（见 EXTENDING.md）。
"""

from multiplotter import *          # noqa: F401,F403
from multiplotter import __version__  # noqa: F401
from multiplotter import (          # noqa: F401
    # 主要类
    MultiPlotter,
    AnimationPlotter,
    PlotBuilder,
    SciencePlotter,
    ScienceResult,
    convective_heat_transfer,
    # 主题与样式
    Theme,
    TWO_D_THEME,
    SURFACE_THEME,
    THEME_ALIASES,
    resolve_theme,
    pick_chinese_fonts,
    CHINESE_FONT_CANDIDATES,
    matplotlib_option,
    matplotlib_surface_option,
    # 注册表
    DRAW_REGISTRY,
    LAYER_SPECS,
    LayerSpec,
    KIND_DEFAULTS,
    INIT_KIND_ALIASES,
    INIT_STYLE_DEFAULTS,
    PASSTHROUGH_KEYS,
    PASSTHROUGH_BY_KIND,
    SUPPORTED_2D_KINDS,
    SUPPORTED_3D_KINDS,
    SUPPORTED_KINDS,
    ADD_DISPATCH,
    describe_layers,
    make_layer_spec,
    validate_layer_config,
    # 保存
    get_unique_filename,
    resolve_save_path,
    save_figure,
    resolve_animation_writer,
    # 版本兼容
    MATPLOTLIB_MIN,
    MATPLOTLIB_TESTED,
    mpl_version,
    mpl_at_least,
)

#: 旧名字别名（重构前是模块级私有函数，现在在 multiplotter.styles 里）。
_pick_chinese_fonts = pick_chinese_fonts


# 测试与旧文档里用到的子模块名，一并暴露出来，方便按需 import。
from multiplotter import (          # noqa: E402,F401
    animation,
    builder,
    compat,
    core,
    draw_2d,
    draw_3d,
    layout,
    registries,
    saving,
    science,
    styles,
    tables,
    validation,
    vector_fields,
)

__all__ = [
    "MultiPlotter",
    "AnimationPlotter",
    "PlotBuilder",
    "SciencePlotter",
    "ScienceResult",
    "convective_heat_transfer",
    "Theme",
    "TWO_D_THEME",
    "SURFACE_THEME",
    "THEME_ALIASES",
    "resolve_theme",
    "pick_chinese_fonts",
    "CHINESE_FONT_CANDIDATES",
    "matplotlib_option",
    "matplotlib_surface_option",
    "DRAW_REGISTRY",
    "LAYER_SPECS",
    "LayerSpec",
    "KIND_DEFAULTS",
    "INIT_KIND_ALIASES",
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
    "get_unique_filename",
    "resolve_save_path",
    "save_figure",
    "resolve_animation_writer",
    "MATPLOTLIB_MIN",
    "MATPLOTLIB_TESTED",
    "mpl_version",
    "mpl_at_least",
    "__version__",
]


if __name__ == "__main__":
    pass
