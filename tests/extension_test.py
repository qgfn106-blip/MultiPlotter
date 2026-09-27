# -*- coding: utf-8 -*-
"""扩展开发测试：验证 EXTENDING.md 里描述的扩展流程确实可行。

覆盖三条主线：

    1. 继承 MultiPlotter / AnimationPlotter 新增 step（二维）与 trisurf（三维）
    2. EXTENDING.md 末尾的最小模板（纯绘图版 + 动画版）
    3. add_plot / add_layer / init() 三类入口的接入

用法：

    python extension_test.py

全部通过时退出码为 0。
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LightSource, Normalize  # noqa: E402

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from Multiplotter import (  # noqa: E402
    AnimationPlotter,
    MultiPlotter,
    matplotlib_option,
    matplotlib_surface_option,
)
from _test_paths import output_dir  # noqa: E402

OUT = output_dir("extension")

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
# 被测试的扩展实现（与 extend_example.py 保持一致）
# ======================================================================

class ExtendedPlotter(AnimationPlotter):
    """新增 step（二维）与 trisurf（三维）。"""

    SUPPORTED_2D_KINDS = MultiPlotter.SUPPORTED_2D_KINDS | {"step"}
    SUPPORTED_3D_KINDS = MultiPlotter.SUPPORTED_3D_KINDS | {"trisurf"}
    SUPPORTED_KINDS = SUPPORTED_2D_KINDS | SUPPORTED_3D_KINDS

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

    PASSTHROUGH_BY_KIND = dict(MultiPlotter.PASSTHROUGH_BY_KIND)
    PASSTHROUGH_BY_KIND["step"] = {"where", "color", "linestyle"}
    PASSTHROUGH_BY_KIND["trisurf"] = {"rstride", "cstride", "shade"}

    @staticmethod
    def _draw_trisurf(ax, config, kwargs):
        """静态方法：纯绘制逻辑，不依赖 self。"""

        z = np.asarray(config["data"], dtype=float)
        light_enhance = config.get("light_enhance")

        if light_enhance and z.ndim != 2:
            raise ValueError(
                "light_enhance 需要二维的 z 数据（LightSource.shade 要算梯度）。"
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
            plt.get_cmap(cmap_name) if isinstance(cmap_name, str)
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

        face_colors = source.shade(
            z,
            cmap=cmap_obj,
            norm=norm,
            vert_exag=float(options.get("vert_exag", 1.0)),
            blend_mode=options.get("blend_mode", "soft"),
        ).reshape(-1, 4)

        order = config.get("vertex_order")

        if order is not None:
            face_colors = face_colors[np.argsort(order)]

        kwargs["facecolors"] = face_colors

        handle = ax.plot_trisurf(
            config["x"], config["y"], flat_z, **kwargs
        )

        return handle, norm, cmap_obj

    def add_step(
        self, x, y, subplot=0, title="", xlabel="X", ylabel="Y",
        label=None, legend=False, legend_kwargs=None, where="pre",
        view=None, **kwargs,
    ):
        x = self._as_1d_array(x, "x")
        y = self._as_1d_array(y, "y")
        self._check_same_length(x, y)

        if where not in ("pre", "post", "mid"):
            raise ValueError(f"where 只能是 pre/post/mid，当前为 {where!r}")

        self.plot_configs.append({
            "kind": "step", "dimension": 2,
            "x": x, "y": y, "z": None, "data": None,
            "subplot": subplot,
            "title": title, "xlabel": xlabel, "ylabel": ylabel, "zlabel": "",
            "label": label, "legend": legend,
            "legend_kwargs": legend_kwargs or {},
            "axis": "", "view": view or {},
            "where": where, "kwargs": kwargs,
        })
        return self

    def add_trisurf(
        self, x, y, z, subplot=0, title="", xlabel="X", ylabel="Y",
        zlabel="Z", label=None, legend=False, legend_kwargs=None,
        cmap="turbo", light_enhance=None, shade=True, colorbar=False,
        colorbar_kwargs=None, view=None, **kwargs,
    ):
        x = self._as_1d_array(x, "x")
        y = self._as_1d_array(y, "y")
        z = self._as_1d_array(z, "z")
        self._check_same_length(x, y, z)

        if len(x) < 3:
            raise ValueError(f"三角剖分至少需要 3 个点，当前为 {len(x)}")

        z_data = z
        vertex_order = None
        unique_x = np.unique(x)
        unique_y = np.unique(y)

        if len(unique_x) * len(unique_y) == len(x):
            vertex_order = np.lexsort((x, y))
            z_data = z[vertex_order].reshape(len(unique_y), len(unique_x))

        self.plot_configs.append({
            "kind": "trisurf", "dimension": 3,
            "x": x, "y": y, "z": None, "data": z_data,
            "vertex_order": vertex_order,
            "subplot": subplot,
            "title": title, "xlabel": xlabel, "ylabel": ylabel,
            "zlabel": zlabel,
            "label": label, "legend": legend,
            "legend_kwargs": legend_kwargs or {},
            "axis": "", "view": view or {},
            "cmap": cmap, "light_enhance": light_enhance, "shade": shade,
            "colorbar": colorbar,
            "colorbar_kwargs": colorbar_kwargs or {},
            "kwargs": kwargs,
        })
        return self

    def add_layer(self, kind, subplot=0, **kwargs):
        if kind == "step":
            return self.add_step(subplot=subplot, **kwargs)

        if kind == "trisurf":
            return self.add_trisurf(subplot=subplot, **kwargs)

        return super().add_layer(kind, subplot=subplot, **kwargs)

    def _draw_layer(self, ax, config):
        kind = config["kind"]
        dimension = config["dimension"]

        if dimension == 2 and kind == "step":
            kwargs = config["kwargs"].copy()

            if config["label"] is not None:
                kwargs["label"] = config["label"]

            ax.step(config["x"], config["y"],
                    where=config["where"], **kwargs)
            return

        if dimension == 3 and kind == "trisurf":
            kwargs = config["kwargs"].copy()
            kwargs["cmap"] = config["cmap"]
            kwargs["shade"] = config["shade"]

            handle, norm, cmap_obj = self._draw_trisurf(ax, config, kwargs)

            if config["label"] is not None:
                handle.set_label(config["label"])

            if config["colorbar"] and norm is not None:
                from matplotlib import cm as mpl_cm

                mappable = mpl_cm.ScalarMappable(norm=norm, cmap=cmap_obj)
                mappable.set_array(np.asarray(config["data"], dtype=float))
                ax.figure.colorbar(
                    mappable, ax=ax, **config["colorbar_kwargs"]
                )
            return

        super()._draw_layer(ax, config)


# ======================================================================
# 数据
# ======================================================================

X1 = np.linspace(0, 10, 24)
Y1 = np.sin(X1)

GRID_1D = np.linspace(-2, 2, 9)
GRID_X, GRID_Y = np.meshgrid(GRID_1D, GRID_1D)
GRID_Z = np.sin(GRID_X) * np.cos(GRID_Y)
TRI_X, TRI_Y, TRI_Z = GRID_X.ravel(), GRID_Y.ravel(), GRID_Z.ravel()


# ======================================================================
# 1. 注册与维度
# ======================================================================

def test_registration():
    check("step 注册为二维", "step" in ExtendedPlotter.SUPPORTED_2D_KINDS)
    check("trisurf 注册为三维", "trisurf" in ExtendedPlotter.SUPPORTED_3D_KINDS)
    check("父类不受影响",
          "step" not in MultiPlotter.SUPPORTED_KINDS)
    check("_get_dimension 用 cls 解析（step）",
          ExtendedPlotter._get_dimension("step") == 2)
    check("_get_dimension 用 cls 解析（trisurf）",
          ExtendedPlotter._get_dimension("trisurf") == 3)

    expect_error("父类拒绝未知 kind", ValueError,
                 MultiPlotter._get_dimension, "step")


# ======================================================================
# 2. 两个自定义图层
# ======================================================================

def test_step_layer():
    plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_step(X1, Y1, subplot=0, title="阶梯图", where="mid",
                     color="#1976D2")
    fig, axes = plotter.draw(show=False)
    ax = np.asarray(axes, dtype=object).ravel()[0]

    check("add_step 出图", len(ax.lines) == 1)
    check("add_step 的 title 生效", ax.get_title() == "阶梯图")
    plt.close("all")


def test_trisurf_layer():
    plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(5, 5), dpi=60)
    plotter.add_trisurf(
        TRI_X, TRI_Y, TRI_Z, subplot=0, title="三角剖分",
        light_enhance=True, colorbar=True,
        view={"xlim": (-2, 2), "ylim": (-2, 2), "elev": 30, "azim": -60},
    )
    fig, axes = plotter.draw(show=False)
    check("add_trisurf 出图（含颜色条）", len(fig.axes) == 2,
          f"-> fig.axes={len(fig.axes)}")
    plt.close("all")


def test_validation():
    expect_error("step: 长度不一致", ValueError,
                 ExtendedPlotter().add_step, X1, Y1[:-1])
    expect_error("step: 非法 where", ValueError,
                 ExtendedPlotter().add_step, X1, Y1, where="middle")
    expect_error("trisurf: 点数不足", ValueError,
                 ExtendedPlotter().add_trisurf,
                 [0.0, 1.0], [0.0, 1.0], [0.0, 1.0])
    expect_error("trisurf: 长度不一致", ValueError,
                 ExtendedPlotter().add_trisurf, TRI_X, TRI_Y[:-1], TRI_Z)
    expect_error("trisurf: 光照需要二维 z（静态方法内的校验）", ValueError,
                 ExtendedPlotter._draw_trisurf,
                 None, {"data": np.array([1.0, 2.0, 3.0]),
                        "light_enhance": True, "x": [0, 1, 2],
                        "y": [0, 1, 2]}, {})


# ======================================================================
# 3. 三类入口
# ======================================================================

def test_add_layer_entry():
    plotter = ExtendedPlotter(ncols=2, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_layer(kind="step", x=X1, y=Y1, subplot=0)
    plotter.add_layer(kind="trisurf", x=TRI_X, y=TRI_Y, z=TRI_Z, subplot=1,
                      view={"elev": 30, "azim": -60})
    plotter.draw(show=False)
    check("add_layer 分发自定义 kind", len(plotter.plot_configs) == 2)
    plt.close("all")

    # 内置 kind 依然能通过父类路径分发
    plotter = ExtendedPlotter(ncols=2, figsize_per_plot=(4, 3), dpi=50)
    plotter.add_layer(kind="line", x=X1, y=Y1, subplot=0)
    plotter.add_layer(kind="surface", x=GRID_X, y=GRID_Y, z=GRID_Z, subplot=1)
    plotter.draw(show=False)
    check("add_layer 仍支持内置 kind", len(plotter.plot_configs) == 2)
    plt.close("all")


def test_init_entry():
    session = ExtendedPlotter.init(ncols=2, figsize_per_plot=(5, 4), dpi=60,
                                   legend=True, title="扩展会话")
    check("init() 内部实例化子类",
          isinstance(session.plotter, ExtendedPlotter))

    session.add("step", {"x": X1, "y": Y1}, subplot=0, label="阶梯")
    session.add("stairs", {"x": X1, "y": Y1}, subplot=1, label="别名")
    fig, axes = session.draw(show=False)
    check("init() 支持新 kind 与别名", len(session) == 2)
    check("init() 的预设生效",
          np.asarray(axes, dtype=object).ravel()[0].get_xlabel() == "x")
    plt.close("all")

    expect_error("init() 拒绝未注册 kind", ValueError,
                 session.resolve_kind, "unknownkind")


def test_kind_presets_inheritance():
    method, defaults = ExtendedPlotter.kind_presets("step")
    check("子类 kind_presets 返回新 kind", method == "add_step")
    check("子类别名可解析",
          ExtendedPlotter.kind_presets("stairs")[0] == "add_step")
    check("父类仍然拒绝新 kind",
          not hasattr(MultiPlotter, "step"))


# ======================================================================
# 4. 动画
# ======================================================================

def test_custom_animation():
    plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_step(X1, Y1, subplot=0, title="阶梯动画",
                     view={"xlim": (0, 10), "ylim": (-1.5, 1.5)})
    plotter.draw(show=False)

    def update(ax, frame):
        ax.clear()
        ax.step(X1, Y1 + 0.1 * frame, where="pre", color="#E64A19")
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.5, 1.5)
        ax.set_title(f"frame={frame}")
        return ax,

    target = os.path.join(OUT, "step_anim.gif")
    plotter.animate(frames=5, update_mode="reset", blit=False,
                    update_func=update, save_path=target, fps=5, dpi=50)
    check("自定义 kind 可动画", os.path.isfile(target))
    plt.close("all")


# ======================================================================
# 5. 初始化设置的扩展
# ======================================================================

def test_style_hooks():
    """全局样式钩子仍然可替换（重构后入口变成 multiplotter.styles）。

    重构前是 ``import Multiplotter as module; module.matplotlib_option = ...``；
    重构后代码拆包，全局样式路径改成按维度调用
    ``multiplotter.styles.matplotlib_option`` /
    ``matplotlib_surface_option``，所以补丁要打到那个模块上。
    ``module.matplotlib_option`` 依然可读（兼容别名），但只影响调用方，
    不影响 MultiPlotter 内部的全局样式路径。
    """
    import multiplotter.styles as styles_module

    original = styles_module.matplotlib_option
    calls = {"n": 0}

    def patched():
        calls["n"] += 1
        original()
        plt.rcParams["axes.titlesize"] = 20
        plt.rcParams["axes.grid"] = False

    styles_module.matplotlib_option = patched

    try:
        plotter = ExtendedPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
        plotter.add_step(X1, Y1, subplot=0, title="样式")
        # style_scope="global" 才会走全局 rcParams 路径（旧行为）
        plotter.draw(show=False, style_scope="global")
        check("包装 matplotlib_option 生效", calls["n"] >= 1,
              f"-> 调用 {calls['n']} 次")
    finally:
        styles_module.matplotlib_option = original
        plt.close("all")


def test_option_defaults():
    plt.rcParams["axes.facecolor"] = "red"
    matplotlib_option()
    check("二维 option 设置白色坐标轴",
          plt.rcParams["axes.facecolor"] == "#FFFFFF",
          f"-> {plt.rcParams['axes.facecolor']}")

    plt.rcParams["axes.facecolor"] = "red"
    matplotlib_surface_option()
    check("三维 option 设置深色坐标轴",
          plt.rcParams["axes.facecolor"] == "#000000",
          f"-> {plt.rcParams['axes.facecolor']}")
    plt.close("all")


def test_passthrough_registration():
    """注册的透传键不会被 PlotBuilder 丢掉。"""

    session = ExtendedPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    session.add("step", {"x": X1, "y": Y1}, where="post", color="crimson")
    dropped = session.get_dropped_keys()

    check("PASSTHROUGH_BY_KIND 里的键不会被丢弃",
          "where" not in dropped.get("step", []),
          f"-> {dropped}")
    plt.close("all")


def test_mpl_kwargs_escape_hatch():
    """``mpl_kwargs``：白名单没覆盖的键可以显式原样透传。

    这是需求 (7) 里“对确实需要完全透传的图层使用专门的 mpl_kwargs 字典”。
    ``picker`` / ``gid`` 都是真实的 Matplotlib 参数，但不在本包的白名单里。
    """

    # ---- 直接入口：add_plot(mpl_kwargs=...) ----
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    plotter.add_plot(
        kind="line", x=X1, y=Y1, subplot=0,
        mpl_kwargs={"picker": 5, "gid": "my-line"},
    )
    _, axes = plotter.draw(show=False)
    line = axes[0].lines[0]

    check("add_plot 的 mpl_kwargs 能透传 picker",
          line.get_picker() == 5, f"-> {line.get_picker()}")
    check("add_plot 的 mpl_kwargs 能透传 gid",
          line.get_gid() == "my-line", f"-> {line.get_gid()}")
    plt.close("all")

    # ---- init() 会话入口：add(mpl_kwargs=...) ----
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    session.add("line", {"x": X1, "y": Y1}, mpl_kwargs={"picker": 7})
    record = session.get_records()[-1]
    _, axes = session.draw(show=False)

    check("init() 会话的 mpl_kwargs 能透传 picker",
          axes[0].lines[0].get_picker() == 7,
          f"-> {axes[0].lines[0].get_picker()}")
    check("mpl_kwargs 不会被记成被丢弃的键",
          record["dropped"] == [], f"-> {record['dropped']}")
    plt.close("all")

    # ---- 同样的键走普通 kwargs 时仍会被白名单拦下 ----
    session = MultiPlotter.init(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    session.add("line", {"x": X1, "y": Y1}, picker=5)
    dropped = session.get_dropped_keys()

    check("普通 kwargs 里的白名单外键仍被丢弃",
          "picker" in dropped.get("line", []), f"-> {dropped}")
    plt.close("all")

    # ---- 类型校验：不是字典就报 TypeError ----
    plotter = MultiPlotter(ncols=1, figsize_per_plot=(4, 3), dpi=50)
    expect_error(
        "mpl_kwargs 必须是字典",
        TypeError,
        plotter.add_plot,
        kind="line", x=X1, y=Y1, subplot=0, mpl_kwargs=[("a", 1)],
    )
    plt.close("all")


# ======================================================================
# 6. EXTENDING.md 里的最小模板
# ======================================================================

class MyPlotter(MultiPlotter):
    """文档「纯绘图版」模板（逐字复制）。"""

    SUPPORTED_2D_KINDS = MultiPlotter.SUPPORTED_2D_KINDS | {"mykind"}
    SUPPORTED_KINDS = SUPPORTED_2D_KINDS | MultiPlotter.SUPPORTED_3D_KINDS

    KIND_DEFAULTS = dict(MultiPlotter.KIND_DEFAULTS)
    KIND_DEFAULTS["mykind"] = ("add_mykind", {"xlabel": "x", "ylabel": "y"})

    INIT_KIND_ALIASES = dict(MultiPlotter.INIT_KIND_ALIASES)
    INIT_KIND_ALIASES["alias"] = "mykind"

    PASSTHROUGH_BY_KIND = dict(MultiPlotter.PASSTHROUGH_BY_KIND)
    PASSTHROUGH_BY_KIND["mykind"] = {"alpha", "color"}

    def add_mykind(
        self, x, y, subplot=0, title="", xlabel="X", ylabel="Y",
        label=None, legend=False, legend_kwargs=None, view=None, **kwargs,
    ):
        x = self._as_1d_array(x, "x")
        y = self._as_1d_array(y, "y")
        self._check_same_length(x, y)

        if len(x) < 2:
            raise ValueError(f"mykind 至少需要 2 个点，当前为 {len(x)}")

        self.plot_configs.append({
            "kind": "mykind", "dimension": 2,
            "x": x, "y": y, "z": None, "data": None,
            "subplot": subplot,
            "title": title, "xlabel": xlabel, "ylabel": ylabel, "zlabel": "",
            "label": label, "legend": legend,
            "legend_kwargs": legend_kwargs or {},
            "axis": "", "view": view or {},
            "kwargs": kwargs,
        })
        return self

    def add_layer(self, kind, subplot=0, **kwargs):
        if kind == "mykind":
            return self.add_mykind(subplot=subplot, **kwargs)
        return super().add_layer(kind, subplot=subplot, **kwargs)

    def _draw_layer(self, ax, config):
        kind = config["kind"]
        dimension = config["dimension"]

        if dimension == 2 and kind == "mykind":
            kwargs = config["kwargs"].copy()

            if config["label"] is not None:
                kwargs["label"] = config["label"]

            ax.plot(config["x"], config["y"], "o-", **kwargs)
            return

        super()._draw_layer(ax, config)


class PlotEntryPlotter(MyPlotter):
    """文档 11.1 的 add_plot 覆盖写法。"""

    def add_plot(self, kind, *args, **kwargs):
        if kind == "mykind":
            x = args[0] if args else kwargs.pop("x")
            y = args[1] if len(args) > 1 else kwargs.pop("y")
            return self.add_mykind(x, y, **kwargs)

        return super().add_plot(kind, *args, **kwargs)


def test_template_draw():
    plotter = MyPlotter(ncols=1, figsize_per_plot=(6, 4), dpi=60)
    plotter.add_mykind([0, 1, 2, 3], [0, 1, 4, 9], title="我的图层",
                       view={"xlim": (0, 3), "ylim": (0, 9)})
    target = os.path.join(OUT, "mykind.png")
    plotter.draw(show=False, save_path=target)
    check("模板可直接运行", os.path.isfile(target))
    plt.close("all")


def test_template_entries():
    # add_layer + 内置 kind 转发
    plotter = MyPlotter(ncols=2, figsize_per_plot=(5, 4), dpi=60)
    plotter.add_layer(kind="mykind", x=[0, 1, 2], y=[0, 1, 4], subplot=0)
    plotter.add_layer(kind="line", x=[0, 1, 2], y=[0, 1, 4], subplot=1)
    plotter.draw(show=False)
    check("模板 add_layer 转发（含内置 kind）", len(plotter.plot_configs) == 2)
    plt.close("all")

    # init + 别名
    session = MyPlotter.init(ncols=1, figsize_per_plot=(5, 4), dpi=60)
    session.add("mykind", {"x": [0, 1, 2], "y": [0, 1, 4]})
    session.add("alias", {"x": [0, 1, 2], "y": [0, 1, 4]}, subplot=0)
    session.draw(show=False)
    check("模板支持 init() + 别名", len(session) == 2)
    plt.close("all")

    # add_plot 覆盖
    plotter = PlotEntryPlotter(ncols=3, figsize_per_plot=(4, 3), dpi=50)
    plotter.add_plot("mykind", [0, 1, 2], [0, 1, 4], subplot=0)
    plotter.add_plot("mykind", x=[0, 1, 2], y=[0, 1, 4], subplot=1)
    plotter.add_plot(kind="scatter", x=[0, 1, 2], y=[0, 1, 4], subplot=2)
    plotter.draw(show=False)
    check("add_plot 覆盖后三种写法可用", len(plotter.plot_configs) == 3)
    plt.close("all")


def test_template_animation():
    """文档「需要动画时」：把基类换成 AnimationPlotter。"""

    class AnimatedMyPlotter(AnimationPlotter):
        SUPPORTED_2D_KINDS = AnimationPlotter.SUPPORTED_2D_KINDS | {"mykind"}
        SUPPORTED_KINDS = (SUPPORTED_2D_KINDS
                           | AnimationPlotter.SUPPORTED_3D_KINDS)

        def add_mykind(self, x, y, subplot=0, title="", xlabel="X",
                       ylabel="Y", label=None, legend=False,
                       legend_kwargs=None, view=None, **kwargs):
            x = self._as_1d_array(x, "x")
            y = self._as_1d_array(y, "y")
            self._check_same_length(x, y)

            self.plot_configs.append({
                "kind": "mykind", "dimension": 2,
                "x": x, "y": y, "z": None, "data": None,
                "subplot": subplot,
                "title": title, "xlabel": xlabel, "ylabel": ylabel,
                "zlabel": "",
                "label": label, "legend": legend,
                "legend_kwargs": legend_kwargs or {},
                "axis": "", "view": view or {},
                "kwargs": kwargs,
            })
            return self

        def add_layer(self, kind, subplot=0, **kwargs):
            if kind == "mykind":
                return self.add_mykind(subplot=subplot, **kwargs)
            return super().add_layer(kind, subplot=subplot, **kwargs)

        def _draw_layer(self, ax, config):
            if config["dimension"] == 2 and config["kind"] == "mykind":
                kwargs = config["kwargs"].copy()

                if config["label"] is not None:
                    kwargs["label"] = config["label"]

                ax.plot(config["x"], config["y"], "o-", **kwargs)
                return

            super()._draw_layer(ax, config)

    plotter = AnimatedMyPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
    plotter.add_mykind([0, 1, 2, 3], [0, 1, 4, 9], title="动画",
                       view={"xlim": (0, 3), "ylim": (0, 9)})
    plotter.draw(show=False)

    def update(ax, frame):
        ax.clear()
        ax.plot([0, 1, 2, 3], [0, 1, 4, 9], "o-")
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 9)
        return ax,

    target = os.path.join(OUT, "template_anim.gif")
    plotter.animate(frames=4, update_mode="reset", blit=False,
                    update_func=update, save_path=target, fps=4, dpi=50)
    check("换成 AnimationPlotter 基类后可动画", os.path.isfile(target))
    plt.close("all")


# ======================================================================
# 运行
# ======================================================================

def main():
    tests = [
        ("注册与维度", test_registration),
        ("step 图层", test_step_layer),
        ("trisurf 图层", test_trisurf_layer),
        ("参数校验", test_validation),
        ("add_layer 入口", test_add_layer_entry),
        ("init 入口", test_init_entry),
        ("kind_presets 继承", test_kind_presets_inheritance),
        ("自定义动画", test_custom_animation),
        ("样式钩子", test_style_hooks),
        ("option 默认值", test_option_defaults),
        ("透传白名单", test_passthrough_registration),
        ("mpl_kwargs 完全透传", test_mpl_kwargs_escape_hatch),
        ("模板出图", test_template_draw),
        ("模板三类入口", test_template_entries),
        ("模板动画版", test_template_animation),
    ]

    for name, func in tests:
        try:
            func()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            check(name, False, f"-> {type(exc).__name__}: {exc}")

    print()
    print(f"通过 {passed} 项，失败 {failed} 项")

    shutil.rmtree(OUT, ignore_errors=True)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
