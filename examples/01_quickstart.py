# -*- coding: utf-8 -*-
"""示例 1：快速开始（二维 / 三维 / 混排 / 保存）。

对应文档：
    最小二维示例        README.md 第 2 章
    最小三维示例        README.md 第 3 章
    init() 会话式绘图   README.md 第 6 章、API.md 第 3 章
    样式与主题          README.md 第 7 章、API.md 第 2 章
    保存与生命周期      API.md 第 24 章

运行：
    python examples/01_quickstart.py
"""

import numpy as np
import matplotlib.pyplot as plt

from _common import output, prepare

prepare()

from multiplotter import MultiPlotter  # noqa: E402


def minimal_2d():
    """最小二维示例：一条正弦曲线。"""

    x = np.linspace(0, 2 * np.pi, 200)

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=110)
    plotter.add_plot(
        kind="line",
        x=x,
        y=np.sin(x),
        subplot=0,
        title="最小二维示例",
        xlabel="x",
        ylabel="y",
        color="#1976D2",
        linewidth=2.0,
        label="sin(x)",
        legend=True,
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)},
    )

    plotter.draw(show=False, save_path=output("01_2d_line.png"))

    print("[ok] 01_2d_line.png")


def minimal_3d():
    """最小三维示例：曲面 + 光照增强 + 颜色条。"""

    x = np.linspace(-3, 3, 80)
    X, Y = np.meshgrid(x, x)
    Z = np.sin(np.sqrt(X ** 2 + Y ** 2))

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(7, 5), dpi=110)
    plotter.add_surface(
        X, Y, Z,
        subplot=0,
        title="最小三维示例",
        cmap="turbo",
        light_enhance=True,
        colorbar=True,
        view={"elev": 30, "azim": -60},
    )

    plotter.draw(show=False, save_path=output("02_3d_surface.png"))

    print("[ok] 02_3d_surface.png")


def mixed_layers():
    """同一个画布上的二维与三维混排。

    注意：**二维和三维不能放在同一个 subplot**，必须分到不同 subplot。
    """

    x = np.linspace(-3, 3, 70)
    X, Y = np.meshgrid(x, x)
    Z = np.sin(X) * np.cos(Y)

    plotter = MultiPlotter(ncols=2, figsize_per_plot=(6, 4.5), dpi=100)

    # subplot=0：三维（曲面 + 轨迹 + 起止点）
    plotter.add_surface(X, Y, Z, subplot=0, cmap="viridis",
                        colorbar=True, view={"elev": 28, "azim": -58})

    t = np.linspace(-2.0, 2.0, 40)
    path_z = np.sin(t) * np.cos(t) + 0.6
    plotter.add_line3d(t, t, path_z, subplot=0,
                       color="crimson", linewidth=3.0, label="轨迹",
                       legend=True)
    plotter.add_scatter3d([t[0], t[-1]], [t[0], t[-1]],
                          [path_z[0], path_z[-1]], subplot=0,
                          s=70, color="black")

    # subplot=1：二维（等高线 + 轨迹）
    plotter.add_contour(X, Y, Z, subplot=1, cmap="viridis",
                        levels=20, line_levels=10, colorbar=True,
                        view={"aspect": "equal", "grid": False})
    plotter.add_plot(kind="line", x=t, y=t, subplot=1,
                     color="crimson", linewidth=2.0, label="轨迹",
                     legend=True)

    plotter.draw(show=False, save_path=output("03_mixed_layers.png"))

    print("[ok] 03_mixed_layers.png")


def init_session():
    """init() 会话式绘图：初始化设置只写一次。"""

    x = np.linspace(0, 10, 120)
    rng = np.random.default_rng(0)

    session = MultiPlotter.init(
        ncols=2, dpi=100,
        title="init() 会话",
        xlabel="x", ylabel="y",
        legend=True,
        grid=True,
        xlim=(0, 10),
    )

    # 只给 kind + 数据；标题、标签、图例都来自 init()
    session.add("line", {"x": x, "y": np.sin(x)})
    session.add("scatter", {"x": x, "y": np.sin(x) + 0.1 * rng.normal(size=x.size)})
    session.add("bar", {"x": ["A", "B", "C", "D"], "y": [3, 7, 2, 5]})
    session.add("heatmap", {"data": np.add.outer(np.sin(x), np.cos(x))})

    print("被丢弃的参数：", session.get_dropped_keys())

    session.draw(show=False, save_path=output("04_init_session.png"))

    print("[ok] 04_init_session.png")


def dropped_keys():
    """演示「全局样式里写了某个图层用不到的键」会发生什么。

    注意：``cmap`` 属于通用透传白名单（散点、热力图都用得到），
    所以它**不会**被丢弃，而是会原样传给 ``ax.plot()`` —— 而
    ``Line2D`` 并不接受 ``cmap``，于是报 ``AttributeError``。

    这类「白名单里、但目标 artist 不认」的键要在 ``add()`` 里就地避开，
    或者只写在需要它的图层上。
    """

    x = np.linspace(0, 10, 120)

    session = MultiPlotter.init(ncols=2, dpi=90, legend=True)

    # 折线不要用 cmap；颜色用 color
    session.add("line", {"x": x, "y": np.sin(x)}, color="#1976D2")

    # cmap 只写给真正需要它的图层
    session.add("heatmap", {"data": np.add.outer(np.sin(x), np.cos(x))},
                cmap="magma")

    session.draw(show=False, save_path=output("08_cmap_per_layer.png"))

    print("[ok] 08_cmap_per_layer.png")


def themes_and_lifecycle():
    """主题作用域与对象生命周期。"""

    x = np.linspace(0, 2 * np.pi, 100)

    # ---- 1. 默认不污染全局 rcParams ----
    plt.rcParams["axes.titlesize"] = 30
    plt.rcParams["axes.grid"] = False

    plotter = MultiPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=90)
    plotter.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
                     title="样式作用域")
    plotter.draw(show=False, save_path=output("05_theme_context.png"))

    assert plt.rcParams["axes.titlesize"] == 30
    assert plt.rcParams["axes.grid"] is False
    print("[ok] 05_theme_context.png（全局 rcParams 未被修改）")

    # ---- 2. 实例级主题：两个对象互不影响 ----
    light = MultiPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=90)
    light.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
                   title="浅色主题")
    light.draw(show=False, save_path=output("06_theme_light.png"))

    dark = MultiPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=90,
                        theme="surface")
    dark.add_plot(kind="line", x=x, y=np.cos(x), subplot=0,
                  title="深色面板主题")
    dark.draw(show=False, save_path=output("07_theme_dark.png"))

    print("[ok] 06_theme_light.png / 07_theme_dark.png")

    # ---- 3. 生命周期：with 退出时自动关闭画布 ----
    with MultiPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=80) as scoped:
        scoped.add_plot(kind="line", x=x, y=np.sin(2 * x), subplot=0,
                        title="with 语句")
        scoped.draw(show=False)

    print("[ok] with 语句退出后画布已自动关闭")


def main():
    minimal_2d()
    minimal_3d()
    mixed_layers()
    init_session()
    dropped_keys()
    themes_and_lifecycle()

    plt.close("all")
    print("\n全部示例完成，输出在 examples/output/")


if __name__ == "__main__":
    main()
