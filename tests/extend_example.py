# -*- coding: utf-8 -*-
"""自定义扩展的可运行示例：给 MultiPlotter 新增两种图层。

本文件是 EXTENDING.md 的配套示例，新增：

    step     二维阶梯图（演示轴参数、where 校验）
    trisurf  三维三角剖分曲面（演示静态方法绘图 + 光照增强）

同时演示如何把新 kind 接入：
    SUPPORTED_2D_KINDS / SUPPORTED_3D_KINDS   注册
    add_layer                                统一入口分发
    _draw_layer                              实际绘制
    KIND_DEFAULTS / INIT_KIND_ALIASES        init() 预设与别名
    PASSTHROUGH_BY_KIND                      允许透传给 matplotlib 的参数

用法：

    python extend_example.py

会生成系统临时目录 ``multiplotter-tests/extended-example/`` 下的几张图。
"""

import os
import sys

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource, Normalize  # noqa: E402

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402
from _test_paths import output_dir  # noqa: E402


class ExtendedPlotter(AnimationPlotter):
    """通过继承扩展新图层（继承 AnimationPlotter 就同时具备动画能力）。"""

    # ==================================================================
    # 1. 注册新 kind
    # ==================================================================
    # 必须用 | 取并集，而不是直接赋值，否则会丢掉内置的 kind。
    # 注意：如果子类只覆盖了 SUPPORTED_2D_KINDS，
    # 类体里不能直接引用 SUPPORTED_3D_KINDS（还没定义），要写完整的父类名字。
    SUPPORTED_2D_KINDS = MultiPlotter.SUPPORTED_2D_KINDS | {"step"}
    SUPPORTED_3D_KINDS = MultiPlotter.SUPPORTED_3D_KINDS | {"trisurf"}
    SUPPORTED_KINDS = SUPPORTED_2D_KINDS | SUPPORTED_3D_KINDS

    # ==================================================================
    # 2. 给 init() 加预设和别名
    # ==================================================================
    KIND_DEFAULTS = dict(MultiPlotter.KIND_DEFAULTS)
    KIND_DEFAULTS["step"] = ("add_step", {
        "linewidth": 2.2,
        "xlabel": "x",
        "ylabel": "y",
        "view": {"grid": True},
    })
    KIND_DEFAULTS["trisurf"] = ("add_trisurf", {
        "cmap": "turbo",
        "light_enhance": True,
        "colorbar": True,
        "view": {"elev": 30, "azim": -60},
    })

    INIT_KIND_ALIASES = dict(MultiPlotter.INIT_KIND_ALIASES)
    INIT_KIND_ALIASES["stairs"] = "step"

    # ==================================================================
    # 3. 允许透传给 matplotlib 的参数
    # ==================================================================
    # 这些键不在 add_step / add_trisurf 的签名里，
    # 但要继续传给 ax.step() / ax.plot_trisurf()
    PASSTHROUGH_BY_KIND = dict(MultiPlotter.PASSTHROUGH_BY_KIND)
    PASSTHROUGH_BY_KIND["step"] = {"where", "color", "linestyle"}
    PASSTHROUGH_BY_KIND["trisurf"] = {"rstride", "cstride", "shade"}

    # ==================================================================
    # 4. 用静态方法写纯绘图逻辑（推荐做法）
    # ==================================================================

    @staticmethod
    def _draw_trisurf(ax, config, kwargs):
        """
        三维三角剖分曲面的绘制逻辑。

        静态方法的好处：不依赖 self，逻辑独立、方便单测、也不会误改实例状态。
        需要读 config 就拿 config，需要画的轴就拿 ax，全部显式传入。

        关于光照：`LightSource.shade()` 内部用 `np.gradient` 算坡度，
        要求输入是**二维数组**；散点数据没有网格结构，所以这里会明确报错，
        而不是抛出一个难懂的 TypeError。
        """

        z = np.asarray(config["data"], dtype=float)
        light_enhance = config.get("light_enhance")

        if light_enhance and z.ndim != 2:
            raise ValueError(
                "light_enhance 需要二维的 z 数据（LightSource.shade 要算梯度）。\n"
                "散点构成的三角剖分请改用 light_enhance=False，"
                "或者把 z 组织成二维网格（z.shape = (ny, nx)）后传入。"
            )

        flat_z = z.ravel()

        if not light_enhance:
            handle = ax.plot_trisurf(
                config["x"], config["y"], flat_z, **kwargs
            )
            return handle, None, None

        options = light_enhance if isinstance(light_enhance, dict) else {}

        cmap_name = options.get("cmap", kwargs.get("cmap"))
        cmap_obj = (
            plt.get_cmap(cmap_name)
            if isinstance(cmap_name, str)
            else cmap_name
        )

        norm = Normalize(
            vmin=float(options.get("vmin", np.percentile(z, 2))),
            vmax=float(options.get("vmax", np.percentile(z, 98))),
        )

        source = LightSource(
            azdeg=options.get("azdeg", 315.0),
            altdeg=options.get("altdeg", 55.0),
        )

        # 山体阴影在网格结构上算，得到 (ny*nx, 4) 的面颜色
        face_colors = source.shade(
            z,
            cmap=cmap_obj,
            norm=norm,
            vert_exag=float(options.get("vert_exag", 1.0)),
            blend_mode=options.get("blend_mode", "soft"),
        ).reshape(-1, 4)

        # plot_trisurf 要的是“顶点顺序”的颜色：
        # 顶点已经按 np.lexsort((x, y)) 排成网格顺序，
        # 所以这里逆置换回去，保证颜色跟着点走
        order = config.get("vertex_order")

        if order is not None:
            face_colors = face_colors[np.argsort(order)]

        kwargs["facecolors"] = face_colors

        handle = ax.plot_trisurf(
            config["x"], config["y"], flat_z, **kwargs
        )

        return handle, norm, cmap_obj

    # ==================================================================
    # 5. add_xxx：只负责校验参数 + 组装 config
    # ==================================================================

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
        """
        添加二维阶梯图。

        参数写法与内置方法保持一致：
        数据 + subplot + 文案 + 本图层特有参数 + view + **kwargs。
        """

        # ---- 参数校验：尽早报错，并且要说清期望值 ----
        x = self._as_1d_array(x, "x")
        y = self._as_1d_array(y, "y")

        self._check_same_length(x, y)

        if where not in ("pre", "post", "mid"):
            raise ValueError(
                f"where 只能是 pre/post/mid，当前为 {where!r}"
            )

        # ---- 组装 config：字段名要与 _draw_layer 里读的一致 ----
        self.plot_configs.append({
            "kind": "step",
            "dimension": 2,
            "x": x,
            "y": y,
            "z": None,
            "data": None,
            "subplot": subplot,
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "zlabel": "",
            "label": label,
            "legend": legend,
            "legend_kwargs": legend_kwargs or {},
            "axis": "",
            "view": view or {},
            "where": where,
            "kwargs": kwargs,
        })

        return self

    def add_trisurf(
        self,
        x,
        y,
        z,
        subplot=0,
        title="",
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        label=None,
        legend=False,
        legend_kwargs=None,
        cmap="turbo",
        light_enhance=None,
        shade=True,
        colorbar=False,
        colorbar_kwargs=None,
        view=None,
        **kwargs,
    ):
        """添加三维三角剖分曲面。"""

        x = self._as_1d_array(x, "x")
        y = self._as_1d_array(y, "y")
        z = self._as_1d_array(z, "z")

        self._check_same_length(x, y, z)

        if len(x) < 3:
            raise ValueError(
                f"三角剖分至少需要 3 个点，当前为 {len(x)}"
            )

        # 如果 x、y 恰好构成规则网格，就把 z 还原成二维，
        # 这样 light_enhance 才能用；否则保持一维。
        z_data = z
        vertex_order = None

        unique_x = np.unique(x)
        unique_y = np.unique(y)

        if len(unique_x) * len(unique_y) == len(x):
            vertex_order = np.lexsort((x, y))
            z_data = z[vertex_order].reshape(len(unique_y), len(unique_x))

        self.plot_configs.append({
            "kind": "trisurf",
            "dimension": 3,
            "x": x,
            "y": y,
            "z": None,
            "data": z_data,
            "vertex_order": vertex_order,
            "subplot": subplot,
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "zlabel": zlabel,
            "label": label,
            "legend": legend,
            "legend_kwargs": legend_kwargs or {},
            "axis": "",
            "view": view or {},
            "cmap": cmap,
            "light_enhance": light_enhance,
            "shade": shade,
            "colorbar": colorbar,
            "colorbar_kwargs": colorbar_kwargs or {},
            "kwargs": kwargs,
        })

        return self

    # ==================================================================
    # 6. add_layer：把新 kind 接进统一入口
    # ==================================================================

    def add_layer(self, kind, subplot=0, **kwargs):
        """
        父类的 add_layer 只认内置 kind，这里补上自定义的，其余交回父类。
        """

        if kind == "step":
            return self.add_step(subplot=subplot, **kwargs)

        if kind == "trisurf":
            return self.add_trisurf(subplot=subplot, **kwargs)

        return super().add_layer(kind, subplot=subplot, **kwargs)

    # ==================================================================
    # 7. _draw_layer：按 kind + dimension 分派到实际绘制
    # ==================================================================

    def _draw_layer(self, ax, config):
        """
        分派规则：

            dimension == 2  -> 用二维坐标轴画
            dimension == 3  -> 用三维坐标轴画

        一定先判断 dimension 再判断 kind：
        同名 kind 在不同维度下含义可能不同，而且坐标轴类型不匹配会直接报错。
        """

        kind = config["kind"]
        dimension = config["dimension"]

        # ---------------- 二维：阶梯图 ----------------
        if dimension == 2 and kind == "step":
            kwargs = config["kwargs"].copy()

            if config["label"] is not None:
                kwargs["label"] = config["label"]

            ax.step(
                config["x"],
                config["y"],
                where=config["where"],
                **kwargs,
            )

            return

        # ---------------- 三维：三角剖分曲面 ----------------
        if dimension == 3 and kind == "trisurf":
            kwargs = config["kwargs"].copy()
            kwargs["cmap"] = config["cmap"]
            kwargs["shade"] = config["shade"]

            # 调用静态方法完成真正的绘制
            handle, norm, cmap_obj = self._draw_trisurf(ax, config, kwargs)

            if config["label"] is not None:
                handle.set_label(config["label"])

            # 颜色条要用独立的 ScalarMappable：
            # 因为 facecolors 已经算成固定颜色，handle 本身不再带标量数据
            if config["colorbar"] and norm is not None:
                from matplotlib import cm as mpl_cm

                mappable = mpl_cm.ScalarMappable(norm=norm, cmap=cmap_obj)
                mappable.set_array(np.asarray(config["data"], dtype=float))
                ax.figure.colorbar(
                    mappable, ax=ax, **config["colorbar_kwargs"]
                )

            return

        # ---------------- 其它情况交回父类 ----------------
        super()._draw_layer(ax, config)


# ======================================================================
# 演示
# ======================================================================

def main():
    out_dir = output_dir("extended-example")

    x = np.linspace(0, 10, 24)
    y = np.sin(x)

    grid = np.linspace(-2, 2, 12)
    mesh_x, mesh_y = np.meshgrid(grid, grid)
    mesh_z = np.sin(mesh_x) * np.cos(mesh_y)
    tri_x, tri_y, tri_z = mesh_x.ravel(), mesh_y.ravel(), mesh_z.ravel()

    # ---------------- 1. 直接调用 add_xxx ----------------
    plotter = ExtendedPlotter(ncols=2, figsize_per_plot=(6, 4.5), dpi=90)
    plotter.add_step(
        x, y, subplot=0, title="阶梯图（pre）",
        xlabel="x", ylabel="y", where="pre",
        color="#1976D2", label="step", legend=True,
        view={"xlim": (0, 10), "ylim": (-1.5, 1.5)},
    )
    plotter.add_trisurf(
        tri_x, tri_y, tri_z, subplot=1, title="三角剖分（光照增强）",
        xlabel="x", ylabel="y", zlabel="z",
        light_enhance=True, colorbar=True,
        colorbar_kwargs={"shrink": 0.7, "label": "z"},
        view={"xlim": (-2, 2), "ylim": (-2, 2), "zlim": (-1.2, 1.2),
              "elev": 30, "azim": -60},
    )
    target = os.path.join(out_dir, "extend_direct.png")
    plotter.draw(show=False, save_path=target)
    print("[ok]", target)
    plt.close("all")

    # ---------------- 2. 用 init() + add() ----------------
    session = ExtendedPlotter.init(
        ncols=2, figsize_per_plot=(6, 4.5), dpi=90,
        legend=True, grid_alpha=0.5, title="扩展会话",
    )
    session.add("step", {"x": x, "y": y}, subplot=0, label="阶梯")
    session.add("stairs", {"x": x, "y": y + 0.5}, subplot=0, label="别名")
    session.add("trisurf", {"x": tri_x, "y": tri_y, "z": tri_z}, subplot=1)
    target = os.path.join(out_dir, "extend_init.png")
    session.draw(show=False, save_path=target)
    print("[ok]", target)
    plt.close("all")

    # ---------------- 3. 用 add_layer() ----------------
    plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(6, 4.5), dpi=90)
    plotter.add_layer(kind="step", x=x, y=y, where="mid",
                      title="通过 add_layer 添加",
                      view={"xlim": (0, 10), "ylim": (-1.5, 1.5)})
    target = os.path.join(out_dir, "extend_add_layer.png")
    plotter.draw(show=False, save_path=target)
    print("[ok]", target)
    plt.close("all")

    # ---------------- 4. 自定义 kind 的动画 ----------------
    plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=80)
    plotter.add_step(
        x, y, subplot=0, title="阶梯动画",
        view={"xlim": (0, 10), "ylim": (-1.5, 1.5)},
    )
    plotter.draw(show=False)

    def update(ax, frame):
        # reset 模式：框架已经 clear 过，这里重画整帧内容
        ax.step(x, y + 0.1 * frame, where="pre", color="#E64A19")
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.5, 1.5)
        ax.set_title(f"阶梯动画 frame={frame}")
        return ax,

    target = os.path.join(out_dir, "extend_animation.gif")
    plotter.animate(
        frames=8, interval=140, blit=False, update_mode="reset",
        update_func=update, save_path=target, fps=6, dpi=70,
    )
    print("[ok]", target)
    plt.close("all")


if __name__ == "__main__":
    main()
