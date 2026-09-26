# -*- coding: utf-8 -*-
"""针对 README 中每个 add_* / animate 示例做一次可运行性检查。"""

import os
import sys
import shutil

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402

OUT = "_audit_out"
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

problems = []


def run(name, func):
    try:
        func()
        print(f"[OK]   {name}")
    except Exception as exc:
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        problems.append((name, repr(exc)))


x = np.linspace(0, 2 * np.pi, 80)
rng = np.random.default_rng(0)


# ---- 4.1 / 4.2 line, scatter ----
def t_line():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, title="line",
               xlabel="x", ylabel="y", color="crimson", linewidth=2.0,
               label="curve", legend=True)
    p.draw(show=False)
    plt.close("all")


def t_scatter():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="scatter", x=x, y=np.sin(x), subplot=0, title="scatter",
               xlabel="x", ylabel="y", color="darkorange", s=40, alpha=0.8,
               label="samples", legend=True)
    p.draw(show=False)
    plt.close("all")


# ---- 5 bar + values ----
def t_bar():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="bar", x=["一", "二", "三"], y=[12.4, 18.6, 9.8],
               subplot=0, title="bar", xlabel="月份", ylabel="数值",
               color="#1976D2", edgecolor="black", linewidth=0.6,
               show_values=True, value_format=".1f", value_offset=3,
               value_kwargs={"fontsize": 9})
    p.draw(show=False)
    plt.close("all")


# ---- 6 hist + density ----
def t_hist():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="hist", x=rng.normal(size=500), subplot=0,
               title="hist", xlabel="数值", ylabel="频数", bins=15,
               density=True, show_values=True, value_format=".3f",
               value_offset=2, value_kwargs={"fontsize": 6})
    p.draw(show=False)
    plt.close("all")


# ---- 7 pie ----
def t_pie():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_pie(labels=["a", "b", "c"], values=[3, 2, 5], subplot=0,
              title="pie", startangle=90, show_values=True,
              value_format=".1f", value_kwargs={"fontsize": 9},
              colors=["#1976D2", "#E64A19", "#388E3C"])
    p.draw(show=False)
    plt.close("all")


# ---- 8 correlation heatmap ----
def t_corr():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_correlation_heatmap(data=rng.normal(size=(50, 4)),
                              labels=["温度", "压力", "速度", "功率"],
                              subplot=0, title="corr", xlabel="变量",
                              ylabel="变量", cmap="coolwarm",
                              show_values=True, value_format=".2f",
                              colorbar=True,
                              colorbar_kwargs={"label": "相关系数"})
    p.draw(show=False)
    plt.close("all")


# ---- 9 heatmap with values + image with colorbar ----
def t_heatmap_values():
    p = MultiPlotter(ncols=2, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="heatmap", data=np.arange(16).reshape(4, 4), subplot=0,
               title="heatmap", xlabel="列", ylabel="行", cmap="viridis",
               show_heatmap_values=True, heatmap_value_format=".1f",
               tick_labels=["a", "b", "c", "d"], colorbar=True)
    p.add_plot(kind="image", image=np.random.rand(8, 8), subplot=1,
               title="image", cmap="gray", colorbar=True)
    p.draw(show=False)
    plt.close("all")


# ---- 10 contour 全参数 ----
def t_contour():
    X, Y = np.meshgrid(np.linspace(-3, 3, 60), np.linspace(-3, 3, 60))
    Z = X ** 2 + Y ** 2
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_contour(X, Y, Z, subplot=0, title="contour", xlabel="x", ylabel="y",
                  levels=30, line_levels=15, cmap="viridis", filled=True,
                  alpha=0.75,
                  contour_kwargs={"colors": "black", "linewidths": 0.5,
                                  "alpha": 0.65},
                  clabel=True,
                  clabel_kwargs={"inline": True, "fontsize": 8, "fmt": "%.1f"},
                  colorbar=True,
                  colorbar_kwargs={"shrink": 0.85, "aspect": 20,
                                   "label": "f(x, y)"},
                  view={"aspect": "equal", "xlim": (-3, 3), "ylim": (-3, 3),
                        "grid": True})
    p.draw(show=False)
    plt.close("all")


# ---- 11 surface 一维坐标 + 光照字典 + colorbar ----
def t_surface():
    xa = np.linspace(-3, 3, 40)
    ya = np.linspace(-3, 3, 40)
    X, Y = np.meshgrid(xa, ya)
    Z = X ** 2 + Y ** 2
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_surface(xa, ya, Z, subplot=0, title="surface", xlabel="X",
                  ylabel="Y", zlabel="f(X, Y)", cmap="turbo",
                  edgecolor="none", alpha=0.92,
                  light_enhance={"azdeg": 315, "altdeg": 55, "gamma": 0.65,
                                 "vert_exag": 1.8, "blend_mode": "soft",
                                 "vmin": np.percentile(Z, 2),
                                 "vmax": np.percentile(Z, 98),
                                 "cmap": "turbo"},
                  colorbar=True,
                  colorbar_kwargs={"shrink": 0.7, "pad": 0.1,
                                   "label": "f(X, Y)"},
                  view={"elev": 35, "azim": -55, "box_aspect": (1, 1, 0.65)})
    p.draw(show=False)
    plt.close("all")


def t_surface_light_true():
    X, Y = np.meshgrid(np.linspace(-3, 3, 30), np.linspace(-3, 3, 30))
    Z = np.sin(X) * np.cos(Y)
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_surface(X, Y, Z, subplot=0, cmap="turbo", light_enhance=True)
    p.draw(show=False)
    plt.close("all")


# ---- 12 line3d ----
def t_line3d():
    t_ = np.linspace(0, 4 * np.pi, 60)
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_line3d(np.cos(t_), np.sin(t_), t_, subplot=0, title="line3d",
                 xlabel="x", ylabel="y", zlabel="z", color="crimson",
                 linewidth=2.5, marker="o", markersize=4,
                 linestyle="--", alpha=0.9, label="helix", legend=True)
    p.draw(show=False)
    plt.close("all")


# ---- 13 scatter3d ----
def t_scatter3d():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_scatter3d([0, 1], [0, 1], [0, 1], subplot=0, title="scatter3d",
                    c=[0, 1], cmap="viridis", s=26, alpha=0.85,
                    depthshade=True, label="samples", legend=True)
    p.add_scatter3d(0, 0, 0, subplot=0, color="black", s=110, marker="*",
                    depthshade=False, label="end", legend=True)
    p.draw(show=False)
    plt.close("all")


# ---- 14 bar3d 标量 dx ----
def t_bar3d():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_bar3d(np.array([0, 1, 2]), np.zeros(3), np.zeros(3), dx=0.7, dy=0.7,
                dz=[12.0, 48.0, 21.0], subplot=0, title="bar3d", xlabel="x",
                ylabel="y", zlabel="value", color="steelblue",
                edgecolor="black", linewidth=0.5, alpha=0.88,
                show_values=True, value_selection="all", value_format=".0f",
                value_offset=0.02, value_kwargs={"fontsize": 8},
                view={"elev": 26, "azim": -58, "box_aspect": (1, 1, 0.85)})
    p.draw(show=False)
    plt.close("all")


# ---- 15 hist3d ----
def t_hist3d():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_hist3d(rng.normal(size=800), rng.normal(size=800), bins=(8, 8),
                 subplot=0, title="hist3d", xlabel="sample x",
                 ylabel="sample y", zlabel="count", cmap="viridis",
                 edgecolor="black", linewidth=0.2, alpha=0.9,
                 show_values=True, value_selection="auto",
                 max_value_labels=8, value_format=".0f", value_offset=0.04,
                 value_kwargs={"fontsize": 6},
                 view={"elev": 30, "azim": -60, "box_aspect": (1, 1, 0.7)})
    p.draw(show=False)
    plt.close("all")


# ---- 20 add_layer 全部 kind ----
def t_add_layer():
    X, Y = np.meshgrid(np.linspace(-2, 2, 20), np.linspace(-2, 2, 20))
    Z = X + Y
    t_ = np.linspace(0, 1, 20)
    p = MultiPlotter(ncols=3, figsize_per_plot=(3, 3), dpi=50)
    p.add_layer(kind="surface", x=X, y=Y, z=Z, subplot=0)
    p.add_layer(kind="contour", x=X, y=Y, z=Z, subplot=1)
    p.add_layer(kind="line3d", x=t_, y=t_, z=t_, subplot=0)
    p.add_layer(kind="scatter3d", x=t_, y=t_, z=t_, subplot=0)
    p.add_layer(kind="bar3d", x=t_, y=t_, z=t_, dx=0.1, dy=0.1, dz=t_,
                subplot=0)
    p.add_layer(kind="hist3d", x=t_, y=t_, bins=4, subplot=0)
    p.add_layer(kind="line", x=t_, y=t_, subplot=1)
    p.add_layer(kind="scatter", x=t_, y=t_, subplot=1)
    p.add_layer(kind="bar", x=t_, y=t_, subplot=1)
    p.add_layer(kind="hist", x=t_, subplot=1)
    p.add_layer(kind="pie", labels=["a", "b"], values=[1, 2], subplot=2)
    p.add_layer(kind="heatmap", data=Z, subplot=2)
    p.add_layer(kind="image", image=np.random.rand(4, 4), subplot=2)
    p.draw(show=False)
    plt.close("all")


def t_subplot_missing():
    """给一个有空缺的 subplot 编号，检查空槽位处理。"""
    p = MultiPlotter(ncols=3, figsize_per_plot=(3, 3), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0)
    p.add_plot(kind="line", x=x, y=np.cos(x), subplot=4)
    fig, axes = p.draw(show=False)
    visible = [bool(a.get_visible()) for a in axes]
    assert visible == [True, False, False, False, True, False], visible
    plt.close("all")


def t_axis_equal():
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 4), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, axis="equal")
    p.draw(show=False)
    plt.close("all")


def t_view_only_xlim():
    """view 只给 xlim 时不应报错（回归：空 axis 曾导致 set_aspect 崩）。"""
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3)})
    p.draw(show=False)
    plt.close("all")


def t_reuse_player():
    """同一个对象 clear 后重画。"""
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0)
    p.draw(show=False)
    plt.close("all")
    p.clear()
    p.add_plot(kind="scatter", x=x, y=np.cos(x), subplot=0)
    p.draw(show=False)
    plt.close("all")


# ---------------- AnimationPlotter ----------------
def t_anim_simple_artists():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6), "grid": True})
    p.draw(show=False)
    ax = p.get_axes(0)
    line, = ax.plot([], [], lw=2)
    p.animate(frames=10, interval=40, blit=True, update_mode="artists",
              update_func=lambda f: (line.set_data(x, np.sin(x - f / 5)), line)[1],
              save_path=os.path.join(OUT, "simple.gif"), fps=10, dpi=60)
    assert os.path.isfile(os.path.join(OUT, "simple.gif"))
    p.stop_animation()
    plt.close("all")


def t_anim_fourier():
    def partial(xx, harmonics):
        total = np.zeros_like(xx)
        for k in range(1, harmonics + 1, 2):
            total += np.sin(k * xx) / k
        return 4.0 / np.pi * total

    xx = np.linspace(0, 2 * np.pi, 120)
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=xx, y=partial(xx, 1), subplot=0,
               title="fourier", xlabel="x", ylabel="y",
               view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)})
    p.add_plot(kind="line", x=xx, y=np.sign(np.sin(xx)), subplot=0,
               color="#B0BEC5", linestyle="--", label="理想方波",
               legend=True)
    p.draw(show=False)
    ax = p.get_axes(0)
    line = ax.lines[0]

    def update(frame):
        h = 2 * frame + 1
        line.set_data(xx, partial(xx, h))
        ax.set_title(f"叠加 {h} 项")
        return line, ax.title

    p.animate(frames=8, interval=100, blit=True, update_mode="artists",
              update_func=update,
              save_path=os.path.join(OUT, "fourier.gif"), fps=5, dpi=60)
    assert os.path.isfile(os.path.join(OUT, "fourier.gif"))
    plt.close("all")


def t_anim_reset_mode():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)

    def update(ax, frame):
        ax.plot(x, np.sin(x - frame / 5), color="#1976D2")
        return ax,

    p.animate(frames=6, update_mode="reset", update_func=update, blit=False,
              save_path=os.path.join(OUT, "reset.gif"), fps=6, dpi=60)
    plt.close("all")


def t_anim_append_mode():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)

    def update(ax, frame):
        return ax.plot([frame / 5], [0.0], "o", color="#E64A19")

    p.animate(frames=6, update_mode="append", update_func=update, blit=False,
              save_path=os.path.join(OUT, "append.gif"), fps=6, dpi=60)
    plt.close("all")


def t_anim_frame_data_list():
    data = [np.sin(x - k / 5) for k in range(8)]
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)

    def update(ax, y):
        ax.clear()
        ax.plot(x, y)
        return ax,

    p.animate(frame_data=data, update_func=update, update_mode="reset",
              blit=False, save_path=os.path.join(OUT, "flist.gif"), fps=6,
              dpi=60)
    plt.close("all")


def t_anim_3d():
    X, Y = np.meshgrid(np.linspace(-3, 3, 30), np.linspace(-3, 3, 30))
    Z = np.sin(X) * np.cos(Y)
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    p.add_surface(X, Y, Z, subplot=0,
                  view={"xlim": (-3, 3), "ylim": (-3, 3), "zlim": (-1, 1),
                        "elev": 30, "azim": -60})
    p.draw(show=False)

    def update(ax, frame):
        ax.clear()
        ax.plot_surface(X, Y, Z * np.sin(frame / 5), cmap="turbo",
                        edgecolor="none")
        ax.set_zlim(-1, 1)
        return ax,

    p.animate(frames=5, blit=True, update_func=update,
              save_path=os.path.join(OUT, "surface.gif"), fps=5, dpi=60)
    plt.close("all")


def t_anim_default_update():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)
    p.animate(frames=5, save_path=os.path.join(OUT, "default.gif"), fps=5,
              dpi=60)
    plt.close("all")


def t_anim_html():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)
    p.animate(frames=4, update_func=lambda ax, f: ax.plot(x, np.sin(x - f)),
              save_path=os.path.join(OUT, "page.html"), fps=4, dpi=60)
    plt.close("all")


def t_anim_save_true():
    p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
               view={"xlim": (0, 6.3), "ylim": (-1.6, 1.6)})
    p.draw(show=False)
    shutil.rmtree("audit_results", ignore_errors=True)
    p.animate(frames=4, update_func=lambda ax, f: ax.plot(x, np.sin(x - f)),
              save=True, save_path_name="audit_results", fps=4, dpi=60)
    assert os.path.isfile(os.path.join("audit_results",
                                       "MultiPlotter_animation.gif"))
    shutil.rmtree("audit_results", ignore_errors=True)
    plt.close("all")


def t_draw_save_path_gif_name():
    """draw() 的 save_path 不应该生成 .gif（那是 animate 的行为）。"""
    p = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0)
    p.draw(show=False, save_path=os.path.join(OUT, "static.png"))
    assert os.path.isfile(os.path.join(OUT, "static.png"))
    plt.close("all")


tests = [
    ("4.1 line", t_line),
    ("4.2 scatter", t_scatter),
    ("5 bar+values", t_bar),
    ("6 hist density", t_hist),
    ("7 pie", t_pie),
    ("8 correlation heatmap", t_corr),
    ("9 heatmap/image", t_heatmap_values),
    ("10 contour", t_contour),
    ("11 surface", t_surface),
    ("11 surface light_enhance=True", t_surface_light_true),
    ("12 line3d", t_line3d),
    ("13 scatter3d", t_scatter3d),
    ("14 bar3d", t_bar3d),
    ("15 hist3d", t_hist3d),
    ("20 add_layer 全部 kind", t_add_layer),
    ("21 空缺 subplot", t_subplot_missing),
    ("21 axis=equal", t_axis_equal),
    ("21 view 只给 xlim", t_view_only_xlim),
    ("21 clear 后复用对象", t_reuse_player),
    ("21 draw(save_path=png)", t_draw_save_path_gif_name),
    ("22.8 动画 简单(artists)", t_anim_simple_artists),
    ("22.9 动画 傅里叶方波", t_anim_fourier),
    ("22.10 动画 reset 模式", t_anim_reset_mode),
    ("22.10 动画 append 模式", t_anim_append_mode),
    ("22.10 动画 frame_data 列表", t_anim_frame_data_list),
    ("22.11 动画 3D", t_anim_3d),
    ("22.5 动画 默认 update", t_anim_default_update),
    ("22.6 动画 保存 HTML", t_anim_html),
    ("22.6 动画 save=True", t_anim_save_true),
]

for name, func in tests:
    run(name, func)

print()
print(f"失败 {len(problems)} 项")
for name, err in problems:
    print(" -", name, err)
shutil.rmtree(OUT, ignore_errors=True)
