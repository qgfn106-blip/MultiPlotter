# -*- coding: utf-8 -*-
"""重新生成 README.md 中引用的全部示例图片。

用法（在本文件夹下运行）：

    python generate_examples.py

只需要 numpy 和 matplotlib。脚本会覆盖 ``images/`` 中同名的 png，
并在 ``example_output/`` 下生成一个用于验证 ``draw(save_path=...)`` 的文件。
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(TESTS_DIR, "images")
sys.path.insert(0, BASE_DIR)

from Multiplotter import MultiPlotter  # noqa: E402

os.makedirs(IMAGES_DIR, exist_ok=True)


def out(name):
    """返回 images/ 下的绝对路径。"""
    return os.path.join(IMAGES_DIR, name)


def reset_style():
    """每个示例开始前统一中文字体，避免示例之间互相影响。"""
    plt.style.use("default")
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "SimHei",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def save_current(name):
    plt.gcf().savefig(out(name), bbox_inches="tight")
    plt.close("all")


def surface_function(x, y):
    return 0.5 * x ** 2 + 2.0 * y ** 2


def gradient_descent_path(steps=26):
    """构造一条单调收敛到原点的下降轨迹。"""
    t = np.linspace(0.0, 1.0, steps)
    return 2.5 * (1.0 - t) ** 2, 2.0 * (1.0 - t) ** 3


# ======================================================================
# 0. init() 快速绘图示例（README 第 3 章）
# ======================================================================

def example_init_demo():
    """只写一次初始化设置，之后每个图层只给 kind + 数据。"""
    reset_style()

    x = np.linspace(0, 2 * np.pi, 200)
    y = np.sin(x)

    grid = np.linspace(-3, 3, 160)
    X, Y = np.meshgrid(grid, grid)
    Z = 0.5 * X ** 2 + 2.0 * Y ** 2

    rng = np.random.default_rng(7)
    samples = np.column_stack([
        rng.normal(25, 4, 200),
        rng.normal(0, 1, 200),
        rng.normal(0, 1, 200),
        rng.normal(0, 1, 200),
    ])

    plotter = MultiPlotter.init(
        ncols=2,
        figsize_per_plot=(6, 4.5),
        dpi=80,
        legend=True,
        grid=True,
        grid_linestyle="--",
        grid_alpha=0.45,
        cell_fontsize=11,
    )

    plotter.add(
        "line", {"x": x, "y": y},
        subplot=0, title="正弦曲线",
        xlabel="x", ylabel="y", color="#1976D2", label="sin(x)",
    )
    plotter.add(
        "surface", {"x": X, "y": Y, "z": Z},
        subplot=1, title="二次曲面（光照增强默认开启）",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
    )
    plotter.add(
        "correlation", {"data": samples},
        subplot=2, title="特征相关性（数值默认显示）",
        labels=["温度", "压力", "速度", "功率"],
        xlabel="变量", ylabel="变量",
        view={"aspect": "equal", "grid": False},
    )
    plotter.add(
        "bar", {"x": ["甲", "乙", "丙", "丁"], "y": [12.4, 18.6, 9.8, 15.2]},
        subplot=3, title="分组结果（柱顶数值默认标注）",
        xlabel="分组", ylabel="数值",
    )

    plotter.draw(show=False)
    save_current("04_init_quickstart.png")


# ======================================================================
# 1. 基础二维图：line / scatter / bar / hist / heatmap / image
# ======================================================================

def example_2d_layers():
    rng = np.random.default_rng(7)
    x_line = np.linspace(0, 10, 120)
    y_line = np.sin(x_line) + 0.15 * x_line

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.4, 4.4), dpi=120)
    plotter.add_plot(
        kind="line", x=x_line, y=y_line, subplot=0,
        title="line", xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.0,
        label="sin(x)+0.15x", legend=True,
    )
    plotter.add_plot(
        kind="scatter", x=x_line[::5],
        y=y_line[::5] + rng.normal(0, 0.12, 24), subplot=1,
        title="scatter", xlabel="x", ylabel="y",
        color="#E64A19", s=34, alpha=0.85, label="samples", legend=True,
    )
    categories = ["A", "B", "C", "D", "E"]
    values = np.array([12.5, 18.2, 9.4, 15.1, 11.3])
    plotter.add_plot(
        kind="bar", x=categories, y=values, subplot=2,
        title="bar（show_values=True）", xlabel="类别", ylabel="数值",
        color="#388E3C", edgecolor="black", linewidth=0.6,
        show_values=True, value_format=".1f", value_offset=3,
        value_kwargs={"fontsize": 9},
    )
    plotter.add_plot(
        kind="hist", x=rng.normal(0, 1, 1200), subplot=3,
        title="hist", xlabel="数值", ylabel="频数",
        bins=28, color="#7B1FA2", alpha=0.8,
        label="distribution", legend=True,
    )
    plotter.add_plot(
        kind="heatmap", data=np.arange(1, 101).reshape(10, 10), subplot=4,
        title="heatmap", xlabel="列", ylabel="行", cmap="viridis",
    )
    image = np.zeros((80, 120, 3))
    image[..., 0] = np.linspace(0, 1, 120)
    image[..., 1] = np.linspace(0, 1, 80)[:, None]
    image[..., 2] = 0.4
    plotter.add_plot(
        kind="image", image=image, subplot=5, title="image",
        xlabel="列", ylabel="行",
    )
    plotter.draw(show=False)
    save_current("05_multiplotter_2d_examples.png")


# ======================================================================
# 2. 二维柱状图 / 直方图的柱顶数值
# ======================================================================

def example_bar_values():
    categories = ["一月", "二月", "三月", "四月", "五月", "六月"]
    values = np.array([12.4, 18.6, 9.8, 15.2, 21.7, 11.5])

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.6, 4.6), dpi=120)
    plotter.add_plot(
        kind="bar", x=categories, y=values, subplot=0,
        title="柱顶数值：show_values=True",
        xlabel="月份", ylabel="数值",
        color="#1976D2", edgecolor="black", linewidth=0.6,
        show_values=True, value_format=".1f", value_offset=3,
        value_kwargs={"fontsize": 9},
    )
    plotter.add_plot(
        kind="bar", x=categories, y=values, subplot=1,
        title="不显示数值：show_values=False（默认）",
        xlabel="月份", ylabel="数值",
        color="#90A4AE", edgecolor="black", linewidth=0.6,
    )
    plotter.draw(show=False)
    save_current("06_bar_values_example.png")


def example_hist_values():
    rng = np.random.default_rng(3)
    samples = np.concatenate([
        rng.normal(-1.0, 0.6, 800),
        rng.normal(1.6, 0.8, 600),
    ])

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.6, 4.6), dpi=120)
    plotter.add_plot(
        kind="hist", x=samples, subplot=0,
        title="频数直方图 + 柱顶频数",
        xlabel="数值", ylabel="频数",
        bins=24, color="#1976D2", edgecolor="white", linewidth=0.8,
        show_values=True, value_format=".0f", value_offset=2,
        value_kwargs={"fontsize": 7},
    )
    plotter.add_plot(
        kind="hist", x=samples, subplot=1,
        title="密度直方图（density=True）",
        xlabel="数值", ylabel="密度",
        bins=24, density=True, color="#7B1FA2",
        edgecolor="white", linewidth=0.8,
        show_values=True, value_format=".3f", value_offset=2,
        value_kwargs={"fontsize": 6, "rotation": 90},
    )
    plotter.draw(show=False)
    save_current("07_hist_values_example.png")


# ======================================================================
# 3. 二维饼图
# ======================================================================

def example_pie():
    industry = ["制造业", "信息技术", "金融", "医疗", "教育"]
    share = np.array([32.5, 24.0, 18.5, 14.0, 11.0])
    palette = ["#1976D2", "#E64A19", "#388E3C", "#7B1FA2", "#F57C00"]

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.6, 5.0), dpi=120)
    plotter.add_pie(
        labels=industry, values=share, subplot=0,
        title="show_values=True：扇区显示百分比",
        startangle=90, show_values=True, value_format=".1f",
        value_kwargs={"fontsize": 9, "color": "#263238"},
        colors=palette,
    )
    plotter.add_pie(
        labels=industry, values=share, subplot=1,
        title="show_values=False：只显示扇区名称",
        startangle=140, show_values=False,
        colors=palette,
        wedgeprops={"linewidth": 1.0, "edgecolor": "white"},
    )
    fig, axes = plotter.draw(show=False)
    assert axes[0].get_xlabel() == "" and axes[0].get_ylabel() == "", "饼图不应出现 X/Y 轴标签"
    save_current("08_pie_example.png")


# ======================================================================
# 4. 相关性矩阵热力图
# ======================================================================

def example_correlation_heatmap():
    rng = np.random.default_rng(11)
    temperature = rng.normal(25, 4, 300)
    pressure = 0.7 * temperature + rng.normal(0, 2.0, 300)
    speed = -0.45 * temperature + rng.normal(0, 3.0, 300)
    power = 0.85 * pressure - 0.3 * speed + rng.normal(0, 1.5, 300)
    samples = np.column_stack([temperature, pressure, speed, power])

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(7.2, 6.0), dpi=120)
    plotter.add_correlation_heatmap(
        data=samples,
        labels=["温度", "压力", "速度", "功率"],
        subplot=0,
        title="特征相关性矩阵",
        xlabel="变量", ylabel="变量",
        cmap="coolwarm", show_values=True, value_format=".2f",
        colorbar_kwargs={"label": "相关系数"},
    )
    plotter.draw(show=False)
    save_current("09_correlation_heatmap_example.png")


# ======================================================================
# 5. 二维等高线
# ======================================================================

def example_contour():
    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    X, Y = np.meshgrid(x, y)
    Z = surface_function(X, Y)
    path_x, path_y = gradient_descent_path()

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6.8, 5.6), dpi=120)
    plotter.add_contour(
        X, Y, Z, subplot=0,
        title="二维等高线 + 下降轨迹",
        xlabel="x", ylabel="y",
        levels=30, line_levels=15, cmap="viridis",
        contour_kwargs={"colors": "black", "linewidths": 0.5, "alpha": 0.65},
        clabel=True,
        clabel_kwargs={"inline": True, "fontsize": 8, "fmt": "%.1f"},
        colorbar=True,
        colorbar_kwargs={"shrink": 0.85, "aspect": 20, "label": "f(x, y)"},
        view={"aspect": "equal", "grid": True},
    )
    plotter.add_plot(
        kind="line", x=path_x, y=path_y, subplot=0,
        color="crimson", linewidth=2.2, marker="o", markersize=4,
        label="gradient descent", legend=True, zorder=5,
    )
    plotter.add_plot(
        kind="scatter", x=path_x[0], y=path_y[0], subplot=0,
        color="limegreen", s=90, marker="o",
        label="start", legend=True, zorder=6,
    )
    plotter.add_plot(
        kind="scatter", x=path_x[-1], y=path_y[-1], subplot=0,
        color="black", s=110, marker="*",
        label="end", legend=True, zorder=6,
    )
    plotter.draw(show=False)
    save_current("10_contour_example.png")


# ======================================================================
# 6. 三维曲面
# ======================================================================

def example_surface():
    x = np.linspace(-3, 3, 200)
    y = np.linspace(-3, 3, 200)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(np.sqrt(X ** 2 + Y ** 2)) * 2.0 + 0.3 * (X ** 2 + Y ** 2)

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(8.0, 6.2), dpi=120)
    plotter.add_surface(
        X, Y, Z, subplot=0,
        title="三维曲面（光照增强 + 颜色条）",
        xlabel="X", ylabel="Y", zlabel="f(X, Y)",
        cmap="turbo", edgecolor="none", alpha=0.95,
        light_enhance={
            "azdeg": 315, "altdeg": 55, "gamma": 0.65,
            "vert_exag": 1.8, "blend_mode": "soft",
        },
        colorbar=True,
        colorbar_kwargs={"shrink": 0.7, "pad": 0.1, "label": "f(X, Y)"},
        view={"elev": 35, "azim": -55, "box_aspect": (1, 1, 0.65)},
    )
    plotter.draw(show=False)
    save_current("11_surface_example.png")


# ======================================================================
# 7. 三维曲线
# ======================================================================

def example_line3d():
    path_x, path_y = gradient_descent_path()
    path_z = surface_function(path_x, path_y)
    theta = np.linspace(0, 4 * np.pi, 300)

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.8, 5.4), dpi=120)
    plotter.add_line3d(
        path_x, path_y, path_z, subplot=0,
        title="三维下降轨迹",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        color="crimson", linewidth=2.5, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left"},
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8)},
    )
    plotter.add_line3d(
        np.cos(theta), np.sin(theta), theta, subplot=1,
        title="三维螺旋曲线", xlabel="x", ylabel="y", zlabel="z",
        color="#1976D2", linewidth=2.0, linestyle="--", alpha=0.9,
        label="helix", legend=True,
        view={"elev": 28, "azim": -65},
    )
    plotter.draw(show=False)
    save_current("12_line3d_example.png")


# ======================================================================
# 8. 三维散点
# ======================================================================

def example_scatter3d():
    rng = np.random.default_rng(5)
    x = rng.normal(0, 1, 200)
    y = rng.normal(0, 1, 200)
    z = 0.6 * x - 0.4 * y + rng.normal(0, 0.4, 200)
    path_x, path_y = gradient_descent_path()
    path_z = surface_function(path_x, path_y)

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.8, 5.4), dpi=120)
    plotter.add_scatter3d(
        x, y, z, subplot=0,
        title="三维散点", xlabel="x", ylabel="y", zlabel="z",
        c=z, cmap="viridis", s=26, alpha=0.85,
        depthshade=True, label="samples", legend=True,
        view={"elev": 28, "azim": -55},
    )
    plotter.add_scatter3d(
        path_x[0], path_y[0], path_z[0], subplot=1,
        title="起点 / 终点标记",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        color="limegreen", s=90, marker="o", depthshade=False,
        label="start", legend=True,
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8)},
    )
    plotter.add_scatter3d(
        path_x[-1], path_y[-1], path_z[-1], subplot=1,
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        color="black", s=110, marker="*", depthshade=False,
        label="end", legend=True,
        legend_kwargs={"loc": "upper left"},
    )
    plotter.draw(show=False)
    save_current("13_scatter3d_example.png")


# ======================================================================
# 9. 三维柱状图：选择性数值标注
# ======================================================================

def example_bar3d_values():
    x = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    z = np.zeros(8)
    height = np.array([12.0, 48.0, 21.0, 6.5, 33.0, 9.0, 54.0, 15.0])

    common = dict(
        x=x, y=y, z=z, dx=0.7, dy=0.7, dz=height,
        xlabel="x", ylabel="y", zlabel="value",
        color="steelblue", edgecolor="black",
        linewidth=0.5, alpha=0.88,
        view={"elev": 26, "azim": -58, "box_aspect": (1, 1, 0.85)},
        value_kwargs={"fontsize": 8},
    )

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.8, 5.4), dpi=120)
    plotter.add_bar3d(
        subplot=0, title="value_selection='all'：全部标注",
        show_values=True, value_selection="all",
        value_format=".0f", value_offset=0.02, **common,
    )
    plotter.add_bar3d(
        subplot=1, title="value_selection='auto'：只标重点",
        show_values=True, value_selection="auto", max_value_labels=3,
        value_format=".0f", value_offset=0.02, **common,
    )
    plotter.draw(show=False)
    save_current("16_bar3d_values_example.png")


# ======================================================================
# 10. 三维直方图：选择性数值标注
# ======================================================================

def example_hist3d_values():
    rng = np.random.default_rng(42)
    sample_x = rng.normal(0, 1, 4000)
    sample_y = rng.normal(0, 1.4, 4000)

    common = dict(
        x=sample_x, y=sample_y, bins=(20, 20),
        xlabel="sample x", ylabel="sample y", zlabel="count",
        cmap="viridis", edgecolor="black",
        linewidth=0.2, alpha=0.9,
        view={"elev": 30, "azim": -60, "box_aspect": (1, 1, 0.7)},
        value_kwargs={"fontsize": 6},
    )

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.8, 5.4), dpi=120)
    plotter.add_hist3d(
        subplot=0, title="value_selection='all'：文字严重重叠",
        show_values=True, value_selection="all", value_format=".0f",
        **common,
    )
    plotter.add_hist3d(
        subplot=1, title="value_selection='auto'：只标 12 个高柱",
        show_values=True, value_selection="auto",
        max_value_labels=12, value_format=".0f",
        value_offset=0.04, **common,
    )
    plotter.draw(show=False)
    save_current("17_hist3d_values_example.png")


def example_hist3d_single():
    rng = np.random.default_rng(9)
    sample_x = rng.normal(0, 1, 2500)
    sample_y = rng.normal(0, 1.2, 2500)

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(8.0, 6.2), dpi=120)
    plotter.add_hist3d(
        sample_x, sample_y, bins=(16, 16), subplot=0,
        title="三维直方图（统一颜色 + threshold 标注）",
        xlabel="sample x", ylabel="sample y", zlabel="count",
        color="steelblue", edgecolor="black",
        linewidth=0.25, alpha=0.92,
        show_values=True, value_selection="threshold",
        value_threshold=120, value_format=".0f", value_offset=0.05,
        value_kwargs={"fontsize": 8},
        view={"elev": 30, "azim": -60, "box_aspect": (1, 1, 0.7)},
    )
    plotter.draw(show=False)
    save_current("15_hist3d_example.png")


# ======================================================================
# 11. 三维图层总览
# ======================================================================

def example_3d_layers():
    x = np.linspace(-3, 3, 120)
    y = np.linspace(-3, 3, 120)
    X, Y = np.meshgrid(x, y)
    Z = surface_function(X, Y)
    path_x, path_y = gradient_descent_path()
    path_z = surface_function(path_x, path_y)

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6.9, 5.5), dpi=120)
    plotter.add_surface(
        X, Y, Z, subplot=0,
        title="surface + line3d + scatter3d",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        cmap="turbo", edgecolor="none", alpha=0.9,
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8)},
    )
    plotter.add_line3d(
        path_x, path_y, path_z, subplot=0,
        color="crimson", linewidth=2.5, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left"},
    )
    plotter.add_scatter3d(
        path_x[0], path_y[0], path_z[0], subplot=0,
        color="limegreen", s=90, marker="o", depthshade=False,
        label="start", legend=True,
    )
    plotter.add_scatter3d(
        path_x[-1], path_y[-1], path_z[-1], subplot=0,
        color="black", s=110, marker="*", depthshade=False,
        label="end", legend=True,
    )
    plotter.add_bar3d(
        np.array([0, 1, 2, 0, 1, 2]),
        np.array([0, 0, 0, 1, 1, 1]),
        np.zeros(6), dx=0.7, dy=0.7,
        dz=np.array([2, 5, 3, 7, 4, 6]), subplot=1,
        title="bar3d", xlabel="x", ylabel="y", zlabel="value",
        color="steelblue", edgecolor="black",
        linewidth=0.5, alpha=0.88,
        show_values=True, value_selection="all",
        value_format=".0f", value_offset=0.03,
        value_kwargs={"fontsize": 8},
        view={"elev": 26, "azim": -58, "box_aspect": (1, 1, 0.85)},
    )
    plotter.draw(show=False)
    save_current("31_multiplotter_3d_examples.png")


# ======================================================================
# 12. 同一个子图混排多种二维图层
# ======================================================================

def example_mixed_layers_2d():
    rng = np.random.default_rng(2024)
    x = np.linspace(0, 10, 40)
    y = 2.4 * x + 1.6 + rng.normal(0, 1.8, x.size)
    slope, intercept = np.polyfit(x, y, 1)
    y_fit = slope * x + intercept
    r2 = 1 - np.sum((y - y_fit) ** 2) / np.sum((y - y.mean()) ** 2)

    theta = np.linspace(0, 2 * np.pi, 400)
    radius = 2.0 * np.sin(3 * theta)

    plotter = MultiPlotter(ncols=3, figsize_per_plot=(6.2, 4.8), dpi=120)

    # 子图 0：scatter（样本点）+ line（回归直线）
    plotter.add_plot(
        kind="scatter", x=x, y=y, subplot=0,
        color="#E64A19", s=34, alpha=0.75,
        label="观测样本", legend=True,
    )
    plotter.add_plot(
        kind="line", x=x, y=y_fit, subplot=0,
        title=f"线性回归：scatter + line（R²={r2:.3f}）",
        xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.4,
        label="回归直线", legend=True,
        legend_kwargs={"loc": "upper left"},
    )

    # 子图 1：line（零残差基线）+ scatter（残差）
    plotter.add_plot(
        kind="line", x=[0, 10], y=[0, 0], subplot=1,
        title="R² 视角：line + scatter（残差图）",
        xlabel="x", ylabel="残差",
        color="#90A4AE", linewidth=1.4, linestyle="--",
        label="零残差基线", legend=True,
    )
    plotter.add_plot(
        kind="scatter", x=x, y=y - y_fit, subplot=1,
        color="#388E3C", s=30, alpha=0.8,
        label="残差", legend=True,
        legend_kwargs={"loc": "upper right"},
    )

    # 子图 2：line（玫瑰线）+ scatter（采样点）
    plotter.add_plot(
        kind="line",
        x=radius * np.cos(theta), y=radius * np.sin(theta), subplot=2,
        title="line + scatter（同一子图）",
        xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.0,
        label="玫瑰线", legend=True,
        view={"aspect": "equal", "grid": True},
    )
    plotter.add_plot(
        kind="scatter",
        x=radius[::20] * np.cos(theta[::20]),
        y=radius[::20] * np.sin(theta[::20]), subplot=2,
        color="#F57C00", s=42, zorder=5,
        label="采样点", legend=True,
        legend_kwargs={"loc": "upper right"},
    )
    plotter.draw(show=False)
    save_current("18_mixed_layers_2d_example.png")


# ======================================================================
# 13. 同一个子图混排 surface + line3d + scatter3d（梯度下降）
# ======================================================================

def example_mixed_layers_3d():
    path_x, path_y = gradient_descent_path()
    X, Y = np.meshgrid(np.linspace(-3, 3, 160), np.linspace(-3, 3, 160))
    Z = surface_function(X, Y)
    path_z = surface_function(path_x, path_y)

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(8.4, 6.6), dpi=120)
    plotter.add_surface(
        X, Y, Z, subplot=0,
        title="梯度下降：surface + line3d + scatter3d",
        xlabel="x", ylabel="y", zlabel="f(x, y)",
        cmap="turbo", edgecolor="none", alpha=0.9,
        colorbar=True,
        colorbar_kwargs={"shrink": 0.7, "pad": 0.1, "label": "f(x, y)"},
        view={"elev": 32, "azim": -60, "box_aspect": (1, 1, 0.8)},
    )
    plotter.add_line3d(
        path_x, path_y, path_z, subplot=0,
        color="crimson", linewidth=2.6, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left", "bbox_to_anchor": (1.02, 1.0)},
    )
    plotter.add_scatter3d(
        path_x[0], path_y[0], path_z[0], subplot=0,
        color="limegreen", s=95, marker="o", depthshade=False,
        label="start", legend=True,
    )
    plotter.add_scatter3d(
        path_x[-1], path_y[-1], path_z[-1], subplot=0,
        color="black", s=120, marker="*", depthshade=False,
        label="end", legend=True,
    )
    plotter.draw(show=False)
    save_current("14_gradient_descent_mixed_3d.png")


# ======================================================================
# 14. README 完整示例的输出
# ======================================================================

def example_full_output():
    x = np.linspace(-3, 3, 240)
    y = np.linspace(-3, 3, 240)
    X, Y = np.meshgrid(x, y)
    Z = surface_function(X, Y)
    path_x, path_y = gradient_descent_path(steps=25)
    path_z = surface_function(path_x, path_y)

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(7, 5), dpi=130)
    plotter.add_surface(
        X, Y, Z, subplot=0,
        title="三维曲面", xlabel="x", ylabel="y", zlabel="f(x, y)",
        cmap="turbo", edgecolor="none", light_enhance=True,
        colorbar=True,
        colorbar_kwargs={"shrink": 0.7, "pad": 0.1, "label": "f(x, y)"},
        view={"elev": 35, "azim": -55, "box_aspect": (1, 1, 0.8)},
    )
    plotter.add_line3d(
        path_x, path_y, path_z, subplot=0,
        color="crimson", linewidth=2.5, marker="o", markersize=4,
        label="gradient descent", legend=True,
        legend_kwargs={"loc": "upper left", "bbox_to_anchor": (1.03, 1.0)},
    )
    plotter.add_scatter3d(
        path_x[0], path_y[0], path_z[0], subplot=0,
        color="limegreen", s=90, marker="o", depthshade=False,
        label="start", legend=True,
    )
    plotter.add_scatter3d(
        path_x[-1], path_y[-1], path_z[-1], subplot=0,
        color="black", s=110, marker="*", depthshade=False,
        label="end", legend=True,
    )
    plotter.add_contour(
        X, Y, Z, subplot=1,
        title="二维等高线", xlabel="x", ylabel="y",
        levels=30, line_levels=15, cmap="viridis",
        contour_kwargs={"colors": "black", "linewidths": 0.5, "alpha": 0.65},
        clabel=True,
        colorbar=True,
        colorbar_kwargs={"shrink": 0.85, "aspect": 20, "label": "f(x, y)"},
        view={"aspect": "equal", "grid": True},
    )
    plotter.add_plot(
        kind="line", x=path_x, y=path_y, subplot=1,
        color="crimson", linewidth=2.2, marker="o", markersize=4,
        label="gradient descent", legend=True, zorder=5,
    )
    plotter.add_plot(
        kind="scatter", x=path_x[0], y=path_y[0], subplot=1,
        color="limegreen", s=90, marker="o",
        label="start", legend=True, zorder=6,
    )
    plotter.add_plot(
        kind="scatter", x=path_x[-1], y=path_y[-1], subplot=1,
        color="black", s=110, marker="*",
        label="end", legend=True, zorder=6,
    )
    plotter.draw(show=False)
    save_current("30_multiplotter_example_output.png")


# ======================================================================
# 15. 验证 draw(save_path=...)
# ======================================================================

def example_save_path():
    """验证 draw(save_path=...) 保存结果，并生成 README 引用的示例图片。"""
    save_dir = os.path.join(BASE_DIR, "example_output")
    os.makedirs(save_dir, exist_ok=True)
    target = os.path.join(save_dir, "demo_save_path.png")

    # 同名文件会被自动加序号，为了生成固定名字的 README 图片，
    # 这里先把上一次的结果和示例图删掉。
    for stale in (target, out("25_save_path_example.png")):
        if os.path.exists(stale):
            os.remove(stale)

    grid = np.linspace(0, 10, 200)
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=80)
    plotter.add_plot(
        kind="line", x=grid, y=np.sin(grid), subplot=0,
        title="draw(save_path=...) 保存到指定位置",
        xlabel="x", ylabel="y",
        color="#1976D2", linewidth=2.0, label="sin(x)", legend=True,
    )

    # 保存到指定文件
    plotter.draw(show=False, save_path=target)
    plt.close("all")

    # 同一份配置再存一次到 images/，作为 README 中的示例图片
    plotter.draw(show=False, save_path=out("25_save_path_example.png"))
    plt.close("all")

    return target


def main():
    tasks = [
        ("04_init_quickstart.png", example_init_demo),
        ("05_multiplotter_2d_examples.png", example_2d_layers),
        ("06_bar_values_example.png", example_bar_values),
        ("07_hist_values_example.png", example_hist_values),
        ("08_pie_example.png", example_pie),
        ("09_correlation_heatmap_example.png", example_correlation_heatmap),
        ("10_contour_example.png", example_contour),
        ("11_surface_example.png", example_surface),
        ("12_line3d_example.png", example_line3d),
        ("13_scatter3d_example.png", example_scatter3d),
        ("16_bar3d_values_example.png", example_bar3d_values),
        ("17_hist3d_values_example.png", example_hist3d_values),
        ("15_hist3d_example.png", example_hist3d_single),
        ("31_multiplotter_3d_examples.png", example_3d_layers),
        ("18_mixed_layers_2d_example.png", example_mixed_layers_2d),
        ("14_gradient_descent_mixed_3d.png", example_mixed_layers_3d),
        ("30_multiplotter_example_output.png", example_full_output),
    ]

    for name, task in tasks:
        reset_style()
        task()
        print(f"[ok] {name}")

    reset_style()
    print(f"[ok] save_path -> {example_save_path()}")
    print("所有示例图片已重新生成")


if __name__ == "__main__":
    main()
