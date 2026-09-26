# -*- coding: utf-8 -*-
"""示例 4：扩展开发 —— 注册一个新的 step 图层。

对应文档：
    EXTENDING.md 第 5 章「完整实战：新增一个 step 图层」

演示「一次注册，全部打通」：

    MyPlotter.register_layer(...)   之后
        add_step(...)                直接调用
        add_layer(kind="step", ...)  统一入口
        MyPlotter.init().add("stairs", ...)   别名 + 预设
        plotter.animate(...)         自动可动画化

运行：
    python examples/04_custom_layer.py
"""

import numpy as np
import matplotlib.pyplot as plt

from _common import output, prepare

prepare()

from multiplotter import AnimationPlotter  # noqa: E402
from multiplotter.validation import (  # noqa: E402
    as_1d_array,
    check_same_length,
)

X = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
Y = np.array([0.0, 1.0, 4.0, 2.0, 3.0, 1.5])


# ======================================================================
# 1. 绘制处理器：签名固定为 (ax, config)
# ======================================================================

def draw_step(ax, config):
    """阶梯线：``Axes.step()``。

    三条规则：
      * 只操作传入的 ax，不要碰 plt.gca()；
      * label 不在 config["kwargs"] 里，需要图例时手动补回；
      * 不要缓存跨调用的状态。
    """

    kwargs = config["kwargs"].copy()

    if config["label"] is not None:
        kwargs["label"] = config["label"]

    ax.step(config["x"], config["y"], where=config["where"], **kwargs)


# ======================================================================
# 2. 子类：写 add_step，然后一次性注册
# ======================================================================

class StepPlotter(AnimationPlotter):
    """新增 ``step``（二维阶梯线）图层。

    基类选 ``AnimationPlotter`` 是为了让新图层也能动画化；
    只要静态出图就够的话，继承 ``MultiPlotter`` 即可。
    """

    def add_step(
        self,
        x,
        y,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        label=None,
        legend=False,
        legend_kwargs=None,
        where="pre",
        view=None,
        **kwargs,
    ):
        """登记一个 step 图层。

        ``add_*`` 只做校验 + 组装 config，**绝对不画图**。
        """

        x = as_1d_array(x, "x")
        y = as_1d_array(y, "y")
        check_same_length(x, y)

        if where not in ("pre", "post", "mid"):
            raise ValueError(f"where 只能是 pre/post/mid，当前为 {where!r}")

        return self._register_layer(
            "step",
            dimension=2,
            subplot=subplot,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            label=label,
            legend=legend,
            legend_kwargs=legend_kwargs,
            view=view,
            kwargs=kwargs,
            x=x,
            y=y,
            where=where,
        )


# 单一注册操作：注册之后 add_layer / init() / PlotBuilder / draw 全部打通
StepPlotter.register_layer(
    kind="step",
    dimension=2,
    add_method="add_step",
    draw_handler=draw_step,
    defaults={
        "linewidth": 2.2,
        "xlabel": "x",
        "ylabel": "y",
        "view": {"grid": True},
    },
    passthrough={"where", "color", "linestyle"},
    aliases=("stairs",),
    description="二维阶梯线",
)


# ======================================================================
# 3. 三种入口
# ======================================================================

def direct_call():
    """入口 ①：直接调用 add_step。"""

    plotter = StepPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=100)
    plotter.add_step(X, Y, subplot=0, where="mid",
                     title="入口 ①：add_step()",
                     color="#1976D2", label="阶梯", legend=True)

    plotter.draw(show=False, save_path=output("30_step_direct.png"))

    print("[ok] 30_step_direct.png")


def unified_entry():
    """入口 ②：add_layer(kind="step") 统一入口。"""

    plotter = StepPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=100)
    plotter.add_layer(kind="step", x=X, y=Y, subplot=0, where="post",
                      title="入口 ②：add_layer(kind='step')",
                      color="#E64A19")

    plotter.draw(show=False, save_path=output("31_step_add_layer.png"))

    print("[ok] 31_step_add_layer.png")


def init_entry():
    """入口 ③：init() + 别名 + 预设。"""

    session = StepPlotter.init(ncols=1, figsize_per_plot=(6, 4), dpi=100,
                               legend=True, grid=True)

    # 用别名 "stairs"，并只给数据
    session.add("stairs", {"x": X, "y": Y}, where="mid", title="入口 ③：init() + 别名")

    print("  预设：", session.kind_presets("step"))
    print("  被丢弃的参数：", session.get_dropped_keys())

    session.draw(show=False, save_path=output("32_step_init.png"))

    print("[ok] 32_step_init.png")


def animated():
    """新图层自动可动画化：只要 view 里固定了范围。"""

    plotter = StepPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=90)
    plotter.add_step(
        X, Y, subplot=0,
        title="自定义图层的动画",
        view={"xlim": (-0.2, 5.2), "ylim": (-1.0, 7.0)},   # 动画必须固定范围
    )
    plotter.draw(show=False)

    def update(ax, frame):
        # reset 模式：框架先 ax.clear()，这里必须重画
        ax.clear()
        ax.step(X, Y + 0.15 * frame, where="mid",
                linewidth=2.2, color="#388E3C")
        ax.set_xlim(-0.2, 5.2)
        ax.set_ylim(-1.0, 7.0)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"自定义图层的动画  frame={frame}")

        return (ax,)

    plotter.animate(
        frames=24, interval=60, blit=False, update_mode="reset",
        update_func=update, save_path=output("33_step_animation.gif"),
        fps=10, dpi=80,
    )

    print("[ok] 33_step_animation.gif")


def inspect():
    """查看注册结果：契约、维度、别名、透传键。"""

    spec = StepPlotter.get_layer_spec("step")

    print("  kind        :", spec.kind)
    print("  dimension   :", spec.dimension)
    print("  add_method  :", spec.add_method)
    print("  aliases     :", spec.aliases)
    print("  passthrough :", sorted(spec.passthrough))
    print("  animatable  :", spec.animatable)

    # 契约自检
    spec.validate()

    # 运行期校验一份 config
    StepPlotter.validate_layer_config(
        "step", {"kind": "step", "dimension": 2, "subplot": 0, "view": {}}
    )

    # 已注册的全部图层
    kinds = [item["kind"] for item in StepPlotter.registered_layers()]
    print("  已注册图层  :", len(kinds), "个，其中自定义：",
          [k for k in kinds if k in ("step",)])

    # 校验会拦住错误输入
    for label, call in (
        ("非法 where", lambda: StepPlotter().add_step(X, Y, where="nope")),
        ("长度不一致", lambda: StepPlotter().add_step(X, Y[:-1])),
        ("缺少 dimension", lambda: StepPlotter.validate_layer_config(
            "step", {"kind": "step", "subplot": 0})),
    ):
        try:
            call()
        except (ValueError, TypeError) as exc:
            print(f"  [校验生效] {label}: {type(exc).__name__}: {exc}")
        else:
            print(f"  [!! 未拦住] {label}")


def main():
    print("== 注册结果 ==")
    inspect()

    print("\n== 三种入口 ==")
    direct_call()
    unified_entry()
    init_entry()

    print("\n== 动画 ==")
    animated()

    plt.close("all")
    print("\n完成，输出在 examples/output/")


if __name__ == "__main__":
    main()
