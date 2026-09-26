# -*- coding: utf-8 -*-
"""示例 3：动画（三种更新模式 + frame_data + 保存格式）。

对应文档：
    ANIMATION.md（全部内容）

运行：
    python examples/03_animation.py
"""

import numpy as np
import matplotlib.pyplot as plt

from _common import output, prepare

prepare()

from multiplotter import AnimationPlotter  # noqa: E402

X = np.linspace(0, 2 * np.pi, 200)


def artists_mode():
    """artists 模式：原地更新已有对象，最快。

    要求 ``draw()`` 之后能拿到 artist 对象（这里用 ``ax.plot([], [])`` 先占位）。
    """

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=90)
    plotter.add_plot(
        kind="line", x=X, y=np.sin(X), subplot=0,
        title="artists 模式：原地更新", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)},
    )
    plotter.draw(show=False)

    # 取出坐标轴，自己创建一条空线，之后用 set_data 原地更新
    ax = plotter.get_axes(0)
    line, = ax.plot([], [], linewidth=2.2, color="#E64A19")

    def update(frame):
        line.set_data(X, np.sin(X - frame / 20 * np.pi))
        return (line,)

    plotter.animate(
        frames=60,
        interval=40,
        blit=True,
        update_mode="artists",
        update_func=update,
        save_path=output("20_anim_artists.gif"),
        fps=12,
        dpi=80,
    )

    print("[ok] 20_anim_artists.gif")


def reset_mode():
    """reset 模式：每帧先 ax.clear() 再重画，最通用。

    回调里必须把标题、范围、比例等重新设置一遍。
    """

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=90)
    plotter.add_plot(
        kind="line", x=X, y=np.sin(X), subplot=0,
        title="reset 模式：每帧重画", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)},
    )
    plotter.draw(show=False)

    def update(ax, frame):
        ax.clear()
        ax.plot(X, np.sin(X - frame / 20 * np.pi), linewidth=2.2,
                color="#1976D2")
        ax.plot(X, np.cos(X - frame / 20 * np.pi), linewidth=1.4,
                color="#388E3C", linestyle="--")
        ax.set_xlim(0, 2 * np.pi)
        ax.set_ylim(-1.6, 1.6)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"reset 模式  frame={frame}")

        return (ax,)

    plotter.animate(
        frames=48,
        interval=50,
        blit=False,
        update_mode="reset",
        update_func=update,
        save_path=output("21_anim_reset.gif"),
        fps=12,
        dpi=80,
    )

    print("[ok] 21_anim_reset.gif")


def append_mode():
    """append 模式：每帧把新对象累积上去，适合画轨迹。"""

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=90)
    plotter.add_plot(
        kind="line", x=X, y=np.sin(X), subplot=0,
        title="append 模式：累积轨迹", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)},
    )
    plotter.draw(show=False)

    ax = plotter.get_axes(0)
    rng = np.random.default_rng(0)

    def update(frame):
        # 每帧画一个随机点。append 模式不会清空坐标轴，
        # 所以点会越积越多。注意用 ax，不要用 plt.gca()：
        # MultiPlotter 管理自己的 Figure，plt.gca() 可能指向别的画布。
        point, = ax.plot(
            rng.uniform(0, 2 * np.pi), rng.uniform(-1.5, 1.5),
            marker="o", markersize=5, color="#7B1FA2", alpha=0.6,
        )
        return (point,)

    plotter.animate(
        frames=80,
        interval=30,
        blit=False,
        update_mode="append",
        update_func=update,
        save_path=output("22_anim_append.gif"),
        fps=15,
        dpi=80,
    )

    print("[ok] 22_anim_append.gif")


def frame_data_mode():
    """frame_data：播放预先算好的帧，回调里直接拿到那一帧的数据。"""

    # 预先算好 24 帧（真实场景里可能来自求解器）
    frames = {
        step: np.sin(X - step * 0.15) * np.exp(-0.02 * step)
        for step in range(24)
    }

    plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=90)
    plotter.add_plot(
        kind="line", x=X, y=frames[0], subplot=0,
        title="frame_data：播放预算好的帧", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.3, 1.3)},
    )
    plotter.draw(show=False)

    def update(ax, values):
        """第二个参数是 frame_data 里对应的那一帧数据，不是帧号。"""

        ax.clear()
        ax.plot(X, values, linewidth=2.2, color="#00796B")
        ax.set_xlim(0, 2 * np.pi)
        ax.set_ylim(-1.3, 1.3)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("frame_data 模式")

        return (ax,)

    plotter.animate(
        frame_data=frames,          # 帧号自动取字典的键
        update_func=update,
        update_mode="reset",
        interval=60,
        save_path=output("23_anim_frame_data.gif"),
        fps=10,
        dpi=80,
    )

    print("[ok] 23_anim_frame_data.gif")


def multi_subplot():
    """多个子图同时动画：回调按传入的 ax 判断画哪个子图。"""

    plotter = AnimationPlotter(ncols=2, figsize_per_plot=(5.5, 4), dpi=85)

    plotter.add_plot(
        kind="line", x=X, y=np.sin(X), subplot=0,
        title="左：正弦", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)},
    )
    plotter.add_plot(
        kind="line", x=X, y=np.cos(X), subplot=1,
        title="右：余弦", xlabel="x", ylabel="y",
        view={"xlim": (0, 2 * np.pi), "ylim": (-1.6, 1.6)},
    )
    plotter.draw(show=False)

    left = plotter.get_axes(0)
    right = plotter.get_axes(1)

    def update(ax, frame):
        ax.clear()
        ax.set_xlim(0, 2 * np.pi)
        ax.set_ylim(-1.6, 1.6)
        ax.set_xlabel("x")
        ax.set_ylabel("y")

        if ax is left:
            ax.plot(X, np.sin(X - frame / 15 * np.pi),
                    linewidth=2.2, color="#1976D2")
            ax.set_title(f"左：正弦  frame={frame}")
        else:
            ax.plot(X, np.cos(X - frame / 15 * np.pi),
                    linewidth=2.2, color="#E64A19")
            ax.set_title(f"右：余弦  frame={frame}")

        return (ax,)

    plotter.animate(
        subplots="all",
        frames=40,
        interval=50,
        blit=False,
        update_mode="reset",
        update_func=update,
        save_path=output("24_anim_multi.gif"),
        fps=12,
        dpi=80,
    )

    print("[ok] 24_anim_multi.gif")


def main():
    artists_mode()
    reset_mode()
    append_mode()
    frame_data_mode()
    multi_subplot()

    plt.close("all")
    print("\n完成，输出在 examples/output/")


if __name__ == "__main__":
    main()
