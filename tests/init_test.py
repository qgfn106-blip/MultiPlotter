# -*- coding: utf-8 -*-
"""MultiPlotter.init() / PlotBuilder 的测试。

用法：

    python init_test.py

全部通过时退出码为 0。
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from Multiplotter import AnimationPlotter, MultiPlotter, PlotBuilder  # noqa: E402
from _test_paths import output_dir  # noqa: E402

OUT = output_dir("init")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

passed = 0
failed = 0


def check(name, condition, extra=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[PASS] {name} {extra}")
    else:
        failed += 1
        print(f"[FAIL] {name} {extra}")


def expect_error(name, exc_type, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exc_type as exc:
        check(name, True, f"-> {type(exc).__name__}")
    except Exception as exc:
        check(name, False, f"-> 抛出了 {type(exc).__name__}: {exc}")
    else:
        check(name, False, "-> 没有报错")


# ======================================================================
# 数据
# ======================================================================

X1 = np.linspace(0, 2 * np.pi, 80)
Y1 = np.sin(X1)

G = np.linspace(-2, 2, 30)
GX, GY = np.meshgrid(G, G)
GZ = GX ** 2 + GY ** 2

SAMPLES = np.random.default_rng(0).normal(size=(60, 4))

UX, UY = np.meshgrid(np.linspace(-2, 2, 20), np.linspace(-2, 2, 20))
UU = -UY
UV = UX

G3 = np.linspace(-1.5, 1.5, 12)
M3X, M3Y, M3Z = np.meshgrid(G, G, G3, indexing="ij")
M3U, M3V = -M3Y, M3X
M3W = 0.4 * np.ones_like(M3Z)

TABLE = [["0.812", "0.883"], ["0.774", "0.856"]]

T = np.linspace(0, 1, 12)


def vortex(x, y, z):
    return (-y, x, 0.4)


# ======================================================================
# 1. init() 基本行为
# ======================================================================

def test_init_returns_builder():
    session = MultiPlotter.init(ncols=2, dpi=60)
    check("init() 返回 PlotBuilder", isinstance(session, PlotBuilder))
    check("init() 参数正确传递",
          session.ncols == 2 and session.dpi == 60)
    check("init() 内部持有 MultiPlotter",
          isinstance(session.plotter, MultiPlotter))
    plt.close("all")


def test_add_only_kind_and_data():
    """只给 kind 和数据就能出图。"""
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    session.add("line", {"x": X1, "y": Y1})
    fig, axes = session.draw(show=False)
    check("只给 kind + 数据可以出图", len(fig.axes) >= 1)
    plt.close("all")


def test_kind_positional_with_kwargs():
    """同时也支持 add("line", x=..., y=...) 的写法。"""
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", x=X1, y=Y1, title="关键字写法")
    check("add() 支持关键字传数据", len(session) == 1)
    plt.close("all")


def test_chaining():
    session = MultiPlotter.init(ncols=2, figsize_per_plot=(4, 3), dpi=60)
    result = (session
              .add("line", x=X1, y=Y1, subplot=0)
              .add("scatter", x=X1[::5], y=Y1[::5], subplot=1))
    check("add() 支持链式调用", result is session and len(session) == 2)
    plt.close("all")


def test_defaults_applied():
    """init() 的全局默认值应当生效。"""
    session = MultiPlotter.init(
        ncols=1, figsize_per_plot=(4, 3), dpi=60,
        title="全局标题", xlabel="时间", ylabel="幅值",
        legend=True, xlim=(0, 6.3), ylim=(-1.5, 1.5),
    )
    session.add("line", x=X1, y=Y1, label="sin", color="crimson")
    fig, axes = session.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]

    check("title 默认值生效", ax.get_title() == "全局标题",
          f"-> {ax.get_title()!r}")
    check("xlabel 默认值生效", ax.get_xlabel() == "时间")
    check("ylabel 默认值生效", ax.get_ylabel() == "幅值")
    check("xlim 默认值生效", np.allclose(ax.get_xlim(), (0, 6.3)),
          f"-> {ax.get_xlim()}")
    check("ylim 默认值生效", np.allclose(ax.get_ylim(), (-1.5, 1.5)))
    check("legend 默认值生效", ax.get_legend() is not None)
    check("label 生效", ax.get_legend().get_texts()[0].get_text() == "sin")
    plt.close("all")


def test_add_overrides_defaults():
    """add() 的参数优先级高于 init() 的默认值。"""
    session = MultiPlotter.init(
        ncols=1, figsize_per_plot=(4, 3), dpi=60,
        title="全局标题", xlim=(0, 10),
    )
    session.add("line", x=X1, y=Y1, title="局部标题", xlim=(0, 1))
    fig, axes = session.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]
    check("add() 的 title 覆盖 init()",
          ax.get_title() == "局部标题", f"-> {ax.get_title()!r}")
    check("add() 的 xlim 覆盖 init()",
          np.allclose(ax.get_xlim(), (0, 1)), f"-> {ax.get_xlim()}")
    plt.close("all")


def test_style_dict():
    """style 字典形式与关键字形式等价。"""
    session = MultiPlotter.init(
        ncols=1, figsize_per_plot=(4, 3), dpi=60,
        style={"legend": True, "xlim": (0, 3), "cell_fontsize": 12},
    )
    check("style 字典被解析", session.style.get("legend") is True)
    check("style 里的范围被解析", session.limits.get("xlim") == (0, 3))
    check("style 里的字体被解析", session.style.get("cell_fontsize") == 12)
    plt.close("all")


def test_configure_and_for_subplot():
    session = MultiPlotter.init(ncols=2, figsize_per_plot=(4, 3), dpi=60)
    session.configure(legend=True, grid=False)
    session.for_subplot(1, aspect="equal", title="子图1")

    check("configure 生效", session.style.get("legend") is True)
    check("for_subplot 生效",
          session.subplot_styles[1].get("title") == "子图1")
    plt.close("all")


def test_lims_shorthand():
    """lims=(xlim, ylim) 简写。"""
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", x=X1, y=Y1, lims=((0, 1), (-2, 2)))
    record = session.get_records()[0]
    check("lims 写入 view",
          record["params"]["view"].get("xlim") == (0, 1)
          and record["params"]["view"].get("ylim") == (-2, 2),
          f"-> {record['params']['view']}")
    plt.close("all")


# ======================================================================
# 2. 各 kind 的预设
# ======================================================================

def test_surface_light_enhance_default():
    """surface 的光照增强默认开启。"""
    method, defaults = MultiPlotter.kind_presets("surface")
    check("surface 预设方法名正确", method == "add_surface")
    check("surface 默认开启光照增强",
          defaults.get("light_enhance") not in (None, False),
          f"-> {defaults.get('light_enhance')}")
    check("surface 默认开启颜色条", defaults.get("colorbar") is True)
    check("surface 默认有 view 视角", "elev" in defaults.get("view", {}))
    check("surface 默认 box_aspect",
          "box_aspect" in defaults.get("view", {}))

    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 4), dpi=60)
    session.add("surface", x=GX, y=GY, z=GZ)
    fig, axes = session.draw(show=False)
    check("surface 用预设可以直接出图（含颜色条）",
          len(fig.axes) == 2, f"fig.axes={len(fig.axes)}")
    plt.close("all")


def test_correlation_values_default():
    """相关性矩阵默认显示数值。"""
    method, defaults = MultiPlotter.kind_presets("correlation")
    check("correlation 预设方法名正确",
          method == "add_correlation_heatmap")
    check("correlation 默认显示数值",
          defaults.get("show_values") is True)

    session = MultiPlotter.init(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    session.add("correlation", data=SAMPLES)
    fig, axes = session.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]
    # heatmap 的数值是 text 对象
    check("相关性矩阵图上确实有数值文本", len(ax.texts) >= 16,
          f"-> {len(ax.texts)} 个文本")
    plt.close("all")


def test_bar_values_default():
    method, defaults = MultiPlotter.kind_presets("bar")
    check("bar 默认标注数值", defaults.get("show_values") is True)

    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("bar", {"x": ["A", "B", "C"], "y": [1.0, 2.0, 3.0]})
    fig, axes = session.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]
    check("柱状图上有数值文本", len(ax.texts) >= 3,
          f"-> {len(ax.texts)} 个文本")
    plt.close("all")


def test_table_preset():
    method, defaults = MultiPlotter.kind_presets("table")
    check("table 预设方法名正确", method == "add_table")
    check("table 默认有斑马纹", defaults.get("zebra_color") is not None)
    check("table 默认固定 view",
          defaults.get("view", {}).get("xlim") == (0.0, 1.0))

    session = MultiPlotter.init(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    session.add("table", {"cell_text": TABLE},
                col_labels=["基线", "量化"], row_labels=["准确率", "召回率"])
    fig, axes = session.draw(show=False)
    check("table 用预设可以直接出图", len(fig.axes) >= 1)
    plt.close("all")


def test_all_kinds_drawable():
    """所有 kind 都能只给数据就出图。"""
    cases = [
        ("line", {"x": X1, "y": Y1}),
        ("scatter", {"x": X1, "y": Y1}),
        ("bar", {"x": ["A", "B"], "y": [1.0, 2.0]}),
        ("hist", {"x": np.random.default_rng(1).normal(size=200)}),
        ("pie", {"labels": ["A", "B", "C"], "values": [3, 2, 5]}),
        ("heatmap", {"data": np.arange(25).reshape(5, 5)}),
        ("correlation", {"data": SAMPLES}),
        ("image", {"image": np.random.default_rng(2).random((10, 10))}),
        ("contour", {"x": GX, "y": GY, "z": GZ}),
        ("surface", {"x": GX, "y": GY, "z": GZ}),
        ("line3d", {"x": T, "y": T, "z": T ** 2}),
        ("scatter3d", {"x": T, "y": T, "z": T ** 2}),
        ("bar3d", {"x": T, "y": T, "z": np.zeros_like(T),
                   "dx": 0.1, "dy": 0.1, "dz": T}),
        ("hist3d", {"x": np.random.default_rng(3).normal(size=200),
                    "y": np.random.default_rng(4).normal(size=200)}),
        ("quiver", {"x": UX, "y": UY, "u": UU, "v": UV}),
        ("streamplot", {"x": UX, "y": UY, "u": UU, "v": UV}),
        ("quiver3d", {"x": M3X, "y": M3Y, "z": M3Z,
                      "u": M3U, "v": M3V, "w": M3W}),
        ("stream3d", {"x": M3X, "y": M3Y, "z": M3Z,
                      "u": M3U, "v": M3V, "w": M3W,
                      "field_func": vortex}),
        ("table", {"cell_text": TABLE}),
    ]

    for kind, data in cases:
        try:
            session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3),
                                        dpi=50)
            session.add(kind, data)
            fig, axes = session.draw(show=False)
            dropped = session.get_dropped_keys()
            check(f"kind={kind} 只给数据即可出图", True,
                  f"被丢弃的键={dropped.get(kind, [])}" if dropped else "")
        except Exception as exc:
            check(f"kind={kind} 只给数据即可出图", False,
                  f"-> {type(exc).__name__}: {exc}")
        finally:
            plt.close("all")


def test_kind_alias():
    method, _ = MultiPlotter.kind_presets("corr")
    check("kind 别名 corr -> correlation",
          method == "add_correlation_heatmap")

    method, _ = MultiPlotter.kind_presets("vector")
    check("kind 别名 vector -> quiver", method == "add_quiver")

    method, _ = MultiPlotter.kind_presets("streamline3d")
    check("kind 别名 streamline3d -> stream3d", method == "add_stream3d")

    expect_error(
        "未知 kind 报错",
        ValueError,
        MultiPlotter.kind_presets,
        "不存在的图层",
    )


def test_global_style_applies_across_kinds():
    """全局样式会作用到每个图层。"""
    session = MultiPlotter.init(
        ncols=2, figsize_per_plot=(4, 3), dpi=60,
        grid=True, grid_linestyle=":", grid_alpha=0.8,
        xlabel="统一X", ylabel="统一Y", legend=True,
    )
    session.add("line", x=X1, y=Y1, subplot=0, label="a")
    session.add("scatter", x=X1, y=Y1, subplot=1, label="b")
    fig, axes = session.draw(show=False)

    for index, ax in enumerate(np.asarray(axes, dtype=object).ravel()):
        if ax.get_visible():
            check(f"子图{index} 继承 xlabel", ax.get_xlabel() == "统一X")

    plt.close("all")


def test_overrides_for_numeric_labels():
    session = MultiPlotter.init(
        ncols=1, figsize_per_plot=(5, 3), dpi=60,
        show_values=True, value_format=".1f",
    )
    session.add("bar", {"x": ["A", "B"], "y": [1.25, 2.5]})
    fig, axes = session.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]
    labels = [text.get_text() for text in ax.texts]
    check("value_format 覆盖生效", any("1.2" in item or "1.3" in item
                                       for item in labels),
          f"-> {labels}")
    plt.close("all")


# ======================================================================
# 3. 记录与容错
# ======================================================================

def test_records():
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", {"x": X1, "y": Y1})
    records = session.get_records()
    check("get_records 返回记录", len(records) == 1)
    check("记录里有方法名", records[0]["method"] == "add_plot")
    check("记录里有最终参数", "x" in records[0]["params"])
    plt.close("all")


def test_dropped_keys_reported():
    """给不适用的图层写了样式键时，不报错但要能查到。"""
    session = MultiPlotter.init(
        ncols=1, figsize_per_plot=(4, 3), dpi=60,
        # cell_fontsize 只有 table 用得到
        cell_fontsize=12,
    )
    session.add("line", x=X1, y=Y1)
    session.add("table", cell_text=TABLE)
    dropped = session.get_dropped_keys()

    check("不适用的键被记录在 line 上",
          "cell_fontsize" in dropped.get("line", []),
          f"-> {dropped}")
    check("table 没有丢弃 cell_fontsize",
          "cell_fontsize" not in dropped.get("table", []))
    plt.close("all")


def test_clear():
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", x=X1, y=Y1)
    session.clear()
    check("clear() 清空图层与记录", len(session) == 0)
    check("clear() 保留初始化设置", session.dpi == 60)
    plt.close("all")


def test_add_many():
    session = MultiPlotter.init(ncols=2, figsize_per_plot=(4, 3), dpi=60)
    session.add_many(
        ("line", {"x": X1, "y": Y1}),
        ("scatter", {"x": X1, "y": Y1}),
    )
    check("add_many 添加两个图层", len(session) == 2)
    plt.close("all")


def test_attribute_forwarding():
    """老写法（get_axes / add_layer）依然可以用。"""
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", x=X1, y=Y1)
    fig, axes = session.draw(show=False)
    ax = session.get_axes(0)
    check("属性转发到内部 MultiPlotter", ax is not None)

    session.add_layer(kind="scatter", x=X1, y=Y1, subplot=0)
    check("add_layer 也能用", len(session.plotter.plot_configs) == 2)
    plt.close("all")


def test_repr():
    session = MultiPlotter.init(ncols=2, dpi=90)
    session.add("line", x=X1, y=Y1)
    text = repr(session)
    check("repr 可读", "PlotBuilder" in text and "layers=1" in text, f"-> {text}")
    plt.close("all")


# ======================================================================
# 4. 保存与动画
# ======================================================================

def test_draw_save_path():
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    session.add("line", x=X1, y=Y1, title="保存测试")
    target = os.path.join(OUT, "init_save.png")
    session.draw(show=False, save_path=target)
    check("init() 的画布可以 save_path 保存", os.path.isfile(target))
    plt.close("all")


def test_animation_with_init():
    """init() 出来的对象可以配合 AnimationPlotter 的动画流程。"""
    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    plotter.add_plot(kind="line", x=X1, y=Y1, subplot=0,
                     label="sin", legend=True,
                     view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
    plotter.draw(show=False)

    line = plotter.get_axes(0).lines[0]

    def update(frame):
        line.set_data(X1, np.sin(X1 - frame / 5))
        return line,

    target = os.path.join(OUT, "init_anim.gif")
    plotter.animate(frames=5, update_mode="artists", blit=True,
                    update_func=update, save_path=target, fps=5, dpi=50)
    check("动画流程不受影响", os.path.isfile(target))
    plt.close("all")


# ======================================================================
# 5. AnimationPlotter.init()
# ======================================================================

def test_animation_init_uses_animation_plotter():
    """AnimationPlotter.init() 应当构建出带 animate() 的会话。"""
    session = AnimationPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=60)
    check("AnimationPlotter.init 返回 PlotBuilder",
          isinstance(session, PlotBuilder))
    check("内部实例是 AnimationPlotter",
          isinstance(session.plotter, AnimationPlotter))
    check("可以通过会话直接调用 animate",
          callable(getattr(session, "animate", None)))
    plt.close("all")


def test_animation_init_end_to_end():
    session = AnimationPlotter.init(
        ncols=1, figsize_per_plot=(4, 3), dpi=60, legend=True,
    )
    session.add("line", x=X1, y=Y1, label="sin",
                view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
    session.draw(show=False)

    line = session.get_axes(0).lines[0]

    def update(frame):
        line.set_data(X1, np.sin(X1 - frame / 5))
        return line,

    target = os.path.join(OUT, "init_animation.gif")
    session.animate(frames=5, update_mode="artists", blit=True,
                    update_func=update, save_path=target, fps=5, dpi=50)
    check("AnimationPlotter.init 可以出动画", os.path.isfile(target))
    plt.close("all")


# ======================================================================
# 运行
# ======================================================================

def main():
    tests = [
        ("init 返回 PlotBuilder", test_init_returns_builder),
        ("只给 kind + 数据", test_add_only_kind_and_data),
        ("关键字传数据", test_kind_positional_with_kwargs),
        ("链式调用", test_chaining),
        ("默认值生效", test_defaults_applied),
        ("add 覆盖默认值", test_add_overrides_defaults),
        ("style 字典", test_style_dict),
        ("configure/for_subplot", test_configure_and_for_subplot),
        ("lims 简写", test_lims_shorthand),
        ("surface 预设", test_surface_light_enhance_default),
        ("correlation 预设", test_correlation_values_default),
        ("bar 预设", test_bar_values_default),
        ("table 预设", test_table_preset),
        ("全部 kind 可出图", test_all_kinds_drawable),
        ("kind 别名", test_kind_alias),
        ("全局样式", test_global_style_applies_across_kinds),
        ("数值格式覆盖", test_overrides_for_numeric_labels),
        ("记录", test_records),
        ("丢弃键报告", test_dropped_keys_reported),
        ("clear", test_clear),
        ("add_many", test_add_many),
        ("属性转发", test_attribute_forwarding),
        ("repr", test_repr),
        ("保存", test_draw_save_path),
        ("动画兼容", test_animation_with_init),
        ("AnimationPlotter.init", test_animation_init_uses_animation_plotter),
        ("AnimationPlotter.init 出动画", test_animation_init_end_to_end),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as exc:
            check(name, False, f"-> 异常 {type(exc).__name__}: {exc}")

    print()
    print(f"通过 {passed} 项，失败 {failed} 项")

    shutil.rmtree(OUT, ignore_errors=True)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
