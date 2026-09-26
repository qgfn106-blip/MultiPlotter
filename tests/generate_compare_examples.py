# -*- coding: utf-8 -*-
"""生成 README 开篇“与普通 matplotlib 对比”章节引用的图片与动图。

用法（在本文件夹下运行）：

    python generate_compare_examples.py

生成：

    images/01_compare_matplotlib.png   版本 A：普通 matplotlib 四联图
    images/02_compare_multiplotter.png 版本 B：MultiPlotter 四联图
    images/03_compare_animated.gif     版本 C：AnimationPlotter 梯度下降动画
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource  # noqa: E402

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(TESTS_DIR, "images")
sys.path.insert(0, BASE_DIR)

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402

os.makedirs(IMAGES_DIR, exist_ok=True)


def out(name):
    return os.path.join(IMAGES_DIR, name)


def reset_style():
    plt.style.use("default")
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "SimHei",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


# ======================================================================
# 共用数据：二维二次损失函数 + 一条梯度下降轨迹
# ======================================================================

def loss_function(x, y):
    return 0.5 * x ** 2 + 2.0 * y ** 2


def gradient_descent(start, lr=0.32, steps=24):
    x, y = start
    path_x, path_y = [x], [y]

    for _ in range(steps):
        grad_x, grad_y = x, 4.0 * y
        x -= lr * grad_x
        y -= lr * grad_y
        path_x.append(x)
        path_y.append(y)

    return np.array(path_x), np.array(path_y)


GRID = np.linspace(-3, 3, 160)
GRID_X, GRID_Y = np.meshgrid(GRID, GRID)
GRID_Z = loss_function(GRID_X, GRID_Y)

PATH_X, PATH_Y = gradient_descent((2.6, 2.2))
PATH_Z = loss_function(PATH_X, PATH_Y)
CONVERGENCE = np.arange(PATH_Z.size)

_RNG = np.random.default_rng(7)
XS = np.linspace(0, 10, 40)
YS = 2.4 * XS + 1.6 + _RNG.normal(0, 1.8, XS.size)
SLOPE, INTERCEPT = np.polyfit(XS, YS, 1)
Y_FIT = SLOPE * XS + INTERCEPT
R2 = 1 - np.sum((YS - Y_FIT) ** 2) / np.sum((YS - YS.mean()) ** 2)


# ======================================================================
# 版本 A：普通 matplotlib
# ======================================================================

def version_a():
    reset_style()

    fig = plt.figure(figsize=(12, 9), dpi=90, constrained_layout=True)
    grid = fig.add_gridspec(2, 2)

    # 子图 1：三维曲面 + 轨迹 + 起止点
    ax1 = fig.add_subplot(grid[0, 0], projection="3d")
    light = LightSource(azdeg=315, altdeg=55)
    face_colors = light.shade(GRID_Z, cmap=plt.get_cmap("turbo"),
                              vert_exag=1.8, blend_mode="soft")
    ax1.plot_surface(GRID_X, GRID_Y, GRID_Z, facecolors=face_colors,
                     shade=False, edgecolor="none")
    ax1.plot(PATH_X, PATH_Y, PATH_Z, color="crimson", linewidth=2.5,
             marker="o", markersize=4, label="gradient descent")
    ax1.scatter(PATH_X[0], PATH_Y[0], PATH_Z[0], color="limegreen",
                s=90, marker="o", label="start", depthshade=False)
    ax1.scatter(PATH_X[-1], PATH_Y[-1], PATH_Z[-1], color="black",
                s=110, marker="*", label="end", depthshade=False)
    ax1.set_title("三维损失曲面与下降轨迹")
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    ax1.set_zlabel("f(x, y)")
    ax1.view_init(elev=32, azim=-60)
    ax1.set_box_aspect((1, 1, 0.8))
    ax1.set_xlim(-3, 3)
    ax1.set_ylim(-3, 3)
    ax1.set_zlim(0, 22)
    ax1.legend(loc="upper left")

    # 子图 2：等高线 + 轨迹
    ax2 = fig.add_subplot(grid[0, 1])
    filled = ax2.contourf(GRID_X, GRID_Y, GRID_Z, levels=30, cmap="viridis",
                          alpha=0.75)
    lines = ax2.contour(GRID_X, GRID_Y, GRID_Z, levels=15, colors="black",
                        linewidths=0.5, alpha=0.65)
    ax2.clabel(lines, inline=True, fontsize=8, fmt="%.1f")
    ax2.plot(PATH_X, PATH_Y, color="crimson", linewidth=2.2, marker="o",
             markersize=4, label="gradient descent", zorder=5)
    ax2.scatter(PATH_X[0], PATH_Y[0], color="limegreen", s=90,
                label="start", zorder=6)
    ax2.scatter(PATH_X[-1], PATH_Y[-1], color="black", s=110, marker="*",
                label="end", zorder=6)
    ax2.set_title("等高线与下降轨迹")
    ax2.set_xlabel("x")
    ax2.set_ylabel("y")
    ax2.set_aspect("equal")
    ax2.set_xlim(-3, 3)
    ax2.set_ylim(-3, 3)
    ax2.legend(loc="lower right")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    fig.colorbar(filled, ax=ax2, shrink=0.85, label="f(x, y)")

    # 子图 3：收敛柱状图（柱顶数值 + 对数轴）
    ax3 = fig.add_subplot(grid[1, 0])
    ax3.bar(CONVERGENCE, PATH_Z, color="#1976D2", edgecolor="black",
            linewidth=0.5, label="loss")
    ax3.bar_label(ax3.containers[0],
                  labels=[f"{value:.1f}" for value in PATH_Z],
                  padding=2, fontsize=7)
    ax3.set_yscale("log")
    ax3.set_title("每步损失（柱顶数值）")
    ax3.set_xlabel("step")
    ax3.set_ylabel("loss")
    ax3.set_xlim(-1, CONVERGENCE.size)
    ax3.set_ylim(1e-6, PATH_Z.max() * 3)
    ax3.legend(loc="upper right")
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    # 子图 4：散点 + 回归直线
    ax4 = fig.add_subplot(grid[1, 1])
    ax4.scatter(XS, YS, s=34, color="#E64A19", alpha=0.75, label="观测样本")
    ax4.plot(XS, Y_FIT, color="#1976D2", linewidth=2.4, label="回归直线")
    ax4.set_title(f"线性回归 R²={R2:.3f}")
    ax4.set_xlabel("x")
    ax4.set_ylabel("y")
    ax4.set_xlim(0, 10)
    ax4.set_ylim(YS.min() - 2, YS.max() + 2)
    ax4.legend(loc="upper left")
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)

    fig.suptitle("普通 matplotlib：四联图", fontsize=15, fontweight="bold")
    fig.savefig(out("01_compare_matplotlib.png"), dpi=90, bbox_inches="tight")
    plt.close(fig)


# ======================================================================
# 版本 B：MultiPlotter（同一张四联图）
# ======================================================================

def version_b():
    reset_style()

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6, 4.5), dpi=90)

    # 子图 0：三维曲面 + 轨迹 + 起止点
    plotter.add_surface(
        GRID_X, GRID_Y, GRID_Z, subplot=0,
        title="三维损失曲面与下降轨迹",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        cmap="turbo", edgecolor="none", alpha=0.9,
        light_enhance={"azdeg": 315, "altdeg": 55, "vert_exag": 1.8},
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8),
              "xlim": (-3, 3), "ylim": (-3, 3), "zlim": (0, 22)},
    )
    plotter.add_line3d(
        PATH_X, PATH_Y, PATH_Z, subplot=0,
        color="crimson", linewidth=2.5, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left"},
    )
    plotter.add_scatter3d(
        PATH_X[0], PATH_Y[0], PATH_Z[0], subplot=0,
        color="limegreen", s=90, marker="o", depthshade=False,
        label="start", legend=True,
    )
    plotter.add_scatter3d(
        PATH_X[-1], PATH_Y[-1], PATH_Z[-1], subplot=0,
        color="black", s=110, marker="*", depthshade=False,
        label="end", legend=True,
    )

    # 子图 1：等高线 + 轨迹
    plotter.add_contour(
        GRID_X, GRID_Y, GRID_Z, subplot=1,
        title="等高线与下降轨迹",
        xlabel="x", ylabel="y",
        levels=30, line_levels=15, cmap="viridis",
        contour_kwargs={"colors": "black", "linewidths": 0.5, "alpha": 0.65},
        clabel=True,
        colorbar=True,
        colorbar_kwargs={"shrink": 0.85, "label": "f(x, y)"},
        view={"aspect": "equal", "xlim": (-3, 3), "ylim": (-3, 3),
              "grid": True},
    )
    plotter.add_plot(
        kind="line", x=PATH_X, y=PATH_Y, subplot=1,
        color="crimson", linewidth=2.2, marker="o", markersize=4,
        label="gradient descent", legend=True, zorder=5,
    )
    plotter.add_plot(
        kind="scatter", x=PATH_X[0], y=PATH_Y[0], subplot=1,
        color="limegreen", s=90, label="start", legend=True, zorder=6,
    )
    plotter.add_plot(
        kind="scatter", x=PATH_X[-1], y=PATH_Y[-1], subplot=1,
        color="black", s=110, marker="*", label="end", legend=True, zorder=6,
        legend_kwargs={"loc": "lower right"},
    )

    # 子图 2：收敛柱状图（柱顶数值 + 对数轴）
    plotter.add_plot(
        kind="bar", x=CONVERGENCE, y=PATH_Z, subplot=2,
        title="每步损失（柱顶数值）",
        xlabel="step", ylabel="loss",
        color="#1976D2", edgecolor="black", linewidth=0.5,
        show_values=True, value_format=".1f", value_offset=2,
        value_kwargs={"fontsize": 7, "rotation": 90},
        label="loss", legend=True,
        view={"xlim": (-1, CONVERGENCE.size), "ylim": (1e-6, PATH_Z.max() * 3),
              "yscale": "log", "grid": True},
    )

    # 子图 3：散点 + 回归直线
    plotter.add_plot(
        kind="scatter", x=XS, y=YS, subplot=3,
        color="#E64A19", s=34, alpha=0.75, label="观测样本", legend=True,
    )
    plotter.add_plot(
        kind="line", x=XS, y=Y_FIT, subplot=3,
        title=f"线性回归 R²={R2:.3f}",
        xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.4, label="回归直线", legend=True,
        legend_kwargs={"loc": "upper left"},
        view={"xlim": (0, 10), "ylim": (YS.min() - 2, YS.max() + 2),
              "grid": True},
    )

    fig, axes = plotter.draw(show=False)
    fig.savefig(out("02_compare_multiplotter.png"), dpi=90, bbox_inches="tight")
    plt.close("all")


# ======================================================================
# 版本 C：AnimationPlotter（在版本 B 基础上加动画）
# ======================================================================

def version_c():
    reset_style()

    plotter = AnimationPlotter(ncols=2, figsize_per_plot=(6, 4.5), dpi=100)

    plotter.add_surface(
        GRID_X, GRID_Y, GRID_Z, subplot=0,
        title="三维损失曲面与下降轨迹",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        cmap="turbo", edgecolor="none", alpha=0.9,
        light_enhance={"azdeg": 315, "altdeg": 55, "vert_exag": 1.8},
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8),
              "xlim": (-3, 3), "ylim": (-3, 3), "zlim": (0, 22)},
    )
    plotter.add_line3d(
        PATH_X, PATH_Y, PATH_Z, subplot=0,
        color="crimson", linewidth=2.5, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left"},
        view={"xlim": (-3, 3), "ylim": (-3, 3), "zlim": (0, 22)},
    )
    plotter.add_contour(
        GRID_X, GRID_Y, GRID_Z, subplot=1,
        title="等高线与下降轨迹",
        xlabel="x", ylabel="y",
        levels=30, line_levels=15, cmap="viridis",
        contour_kwargs={"colors": "black", "linewidths": 0.5, "alpha": 0.65},
        clabel=True, colorbar=True,
        colorbar_kwargs={"shrink": 0.85, "label": "f(x, y)"},
        view={"aspect": "equal", "xlim": (-3, 3), "ylim": (-3, 3),
              "grid": True},
    )
    plotter.add_plot(
        kind="line", x=PATH_X, y=PATH_Y, subplot=1,
        color="crimson", linewidth=2.2, marker="o", markersize=4,
        label="gradient descent", legend=True, zorder=5,
        view={"xlim": (-3, 3), "ylim": (-3, 3)},
    )
    plotter.add_plot(
        kind="bar", x=CONVERGENCE, y=PATH_Z, subplot=2,
        title="每步损失",
        xlabel="step", ylabel="loss",
        color="#1976D2", edgecolor="black", linewidth=0.5,
        view={"xlim": (-1, CONVERGENCE.size), "ylim": (0, PATH_Z.max() * 1.2),
              "grid": True},
    )
    plotter.draw(show=False)

    ax3d = plotter.get_axes(0)
    ax2d = plotter.get_axes(1)
    axbar = plotter.get_axes(2)

    # 取已经画好的对象：
    # 三维子图的 line3d 和柱状图的 bar 都是第一个/唯一一个，
    # 等高线子图里的 ax.lines[0] 正好是后加的轨迹线
    # （等高线本身在 ax.collections 里，不在 ax.lines 里）。
    line_3d = ax3d.lines[0]
    line_2d = ax2d.lines[0]
    bars = axbar.patches

    for bar in bars:
        bar.set_height(0.0)

    def update(frame):
        steps = frame + 1
        line_3d.set_data_3d(PATH_X[:steps], PATH_Y[:steps], PATH_Z[:steps])
        line_2d.set_data(PATH_X[:steps], PATH_Y[:steps])

        for index, bar in enumerate(bars):
            bar.set_height(PATH_Z[index] if index < steps else 0.0)

        ax3d.set_title(f"三维损失曲面与下降轨迹（step {steps}）")
        return line_3d, line_2d, *bars

    target = out("03_compare_animated.gif")

    if os.path.exists(target):
        os.remove(target)

    plotter.animate(
        subplots=[0, 1, 2],
        frames=PATH_Z.size,
        interval=120,
        blit=False,
        update_mode="artists",
        update_func=update,
        save_path=target,
        fps=8,
        dpi=80,
    )
    plotter.stop_animation()
    plt.close("all")


def main():
    version_a()
    print("[ok] 01_compare_matplotlib.png")

    version_b()
    print("[ok] 02_compare_multiplotter.png")

    version_c()
    print("[ok] 03_compare_animated.gif")

    for name in ("01_compare_matplotlib.png", "02_compare_multiplotter.png",
                 "03_compare_animated.gif"):
        print(f"    {name}: {os.path.getsize(out(name)) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
