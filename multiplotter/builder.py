# -*- coding: utf-8 -*-
"""``PlotBuilder``：``MultiPlotter.init()`` 返回的绘图会话。

作用：把「初始化设置」和「数据」分开。

* 初始化设置（标题、标签、范围、图例、网格、字体、各种图层参数）
  在 ``init()`` 里写一次；
* 之后每次 ``add()`` 只需要给 ``kind`` 和数据。

每个 kind 都有一套预设参数（见 ``MultiPlotter.KIND_DEFAULTS``），
例如 surface 默认开启光照增强、柱状图默认标注数值。

优先级（从低到高）::

    KIND_DEFAULTS  <  init() 的全局样式  <  add() 的参数  <  add() 的 **kwargs

也就是说，越靠近调用处的设置优先级越高，随时可以就地覆盖。

典型用法::

    plotter = MultiPlotter.init(ncols=2, dpi=120, legend=True)

    plotter.add(kind="line", x=x, y=y, title="曲线")
    plotter.add(kind="surface", x=X, y=Y, z=Z, title="曲面")

    fig, axes = plotter.draw(show=False, save_path="out/result.png")
"""

from __future__ import annotations

import copy
import inspect
import warnings

import numpy as np

from . import registries

#: 全局样式里属于「坐标轴级别」的键：要合并进 ``view``，不能放顶层。
AXIS_LEVEL_STYLE_KEYS = {
    "grid", "grid_linestyle", "grid_alpha", "grid_color",
    "grid_linewidth", "aspect", "xscale", "yscale", "scale",
    "ticks_rotation",
}

#: ``map_data()`` 认得的数据参数名。
DATA_PARAMETER_NAMES = {
    "x", "y", "z", "u", "v", "w",
    "data", "image", "cell_text",
    "labels", "values",
    "dx", "dy", "dz",
}

#: ``clean_call()`` 里不参与「去 None」的特殊键。
ALWAYS_KEPT_KEYS = {
    "subplot", "title", "xlabel", "ylabel", "zlabel",
    "view", "cell_text",
}


class PlotBuilder:
    """MultiPlotter.init() 返回的绘图会话。

    它**不重复实现任何绘图逻辑**，只是「参数装配器」：
    装配完仍然调用 ``MultiPlotter`` 的 ``add_*``。
    """

    def __init__(
        self,
        ncols=2,
        figsize_per_plot=(6, 4),
        dpi=120,
        style=None,
        subplot=0,
        title="",
        xlabel=None,
        ylabel=None,
        zlabel=None,
        limits=None,
        plotter_class=None,
        theme=None,
        strict=False,
    ):
        from .core import MultiPlotter

        self.ncols = ncols
        self.figsize_per_plot = figsize_per_plot
        self.dpi = dpi

        # 全局样式：只保留用户真正设置过的键
        self.style = {
            key: value
            for key, value in dict(style or {}).items()
            if value is not None
        }

        self.subplot = subplot
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel
        self.limits = dict(limits or {})

        # 每个子图单独的覆盖设置：{subplot序号: {键: 值}}
        self.subplot_styles = {}

        # 真正承载绘图的实例。
        # 传入 AnimationPlotter 时会自动用 AnimationPlotter，
        # 这样 animate() 等方法也能直接用。
        plotter_class = plotter_class or MultiPlotter

        self.plotter_class = plotter_class
        self.theme = theme
        self.strict = bool(strict)

        plotter_kwargs = {
            "ncols": ncols,
            "figsize_per_plot": figsize_per_plot,
            "dpi": dpi,
        }

        if theme is not None:
            plotter_kwargs["theme"] = theme

        self.plotter = plotter_class(**plotter_kwargs)

        # 记录每次 add() 的结果，便于复查
        self.records = []

        # 已经提醒过的「被丢弃的键」，避免同一会话重复提示
        self._warned_keys = {}

    # ================================================================
    # 会话级设置
    # ================================================================

    def configure(self, **style):
        """追加/修改全局样式，返回自身以便链式调用。

        ::

            session.configure(legend=True, cell_fontsize=12)
        """

        for key, value in style.items():
            if key in ("subplot", "title", "xlabel", "ylabel", "zlabel"):
                setattr(self, key, value)
            elif key in ("xlim", "ylim", "zlim"):
                self.limits[key] = value
            elif key == "theme":
                self.theme = value
                self.plotter.theme = value
            elif value is not None:
                self.style[key] = value

        return self

    def for_subplot(self, subplot, **style):
        """给某个子图单独设置样式，优先级高于全局样式。

        ::

            session.for_subplot(1, aspect="equal", legend=True)
        """

        bucket = self.subplot_styles.setdefault(int(subplot), {})
        bucket.update({
            key: value for key, value in style.items() if value is not None
        })

        return self

    def resolve_kind(self, kind):
        """解析 kind 别名，返回真实支持的 kind。

        用 ``self.plotter_class`` 而不是 ``MultiPlotter``：
        子类覆盖 ``KIND_DEFAULTS`` / ``INIT_KIND_ALIASES`` 后，
        ``init()`` 依然能解析新 kind。
        """

        plotter_class = self.plotter_class

        resolved = plotter_class.INIT_KIND_ALIASES.get(kind, kind)

        if resolved not in plotter_class.KIND_DEFAULTS:
            raise ValueError(
                f"init() 不支持kind={kind}；"
                f"支持的kind：{sorted(plotter_class.KIND_DEFAULTS)}；"
                f"别名：{sorted(plotter_class.INIT_KIND_ALIASES)}"
            )

        return resolved

    # ================================================================
    # 核心：组装一次 add 调用
    # ================================================================

    def build_call(self, kind, data=None, subplot=None, **kwargs):
        """把预设、全局样式、调用参数合并成一次真正的 ``add_*`` 调用。

        返回 ``(方法名, 参数字典)``，不真正执行绘图。
        """

        resolved = self.resolve_kind(kind)
        method_name, defaults = self.plotter_class.kind_presets(resolved)

        call = copy.deepcopy(defaults)

        # add_plot() 需要用 kind 参数区分折线/散点/柱状等，
        # 其它方法（add_surface / add_table ...）的 kind 由方法名决定。
        if method_name == "add_plot":
            call["kind"] = resolved

        # ---------------- 1. 全局样式 ----------------
        style = dict(self.style)
        style.update(
            self.subplot_styles.get(
                int(subplot if subplot is not None else self.subplot), {}
            )
        )

        # 图层默认参数里已经有的键，不能被全局的 None 覆盖，
        # 所以全局样式只覆盖「显式设置过」的键。
        call.update({
            key: value
            for key, value in style.items()
            if key not in AXIS_LEVEL_STYLE_KEYS
        })

        # ---------------- 2. 数据 ----------------
        call.update(self.map_data(resolved, data, kwargs))

        # ---------------- 3. 定位与文案 ----------------
        call["subplot"] = int(
            subplot if subplot is not None else self.subplot
        )

        if "title" in kwargs:
            call["title"] = kwargs["title"]
        elif self.title:
            call["title"] = self.title

        # 坐标轴文案的优先级：
        #   add() 显式传入 > init() 的全局默认 > kind 预设
        for axis_name in ("xlabel", "ylabel", "zlabel"):
            if axis_name in kwargs:
                call[axis_name] = kwargs[axis_name]
            elif getattr(self, axis_name) is not None:
                call[axis_name] = getattr(self, axis_name)

        # ---------------- 4. 坐标轴范围 -> view ----------------
        call["view"] = self.merge_view(call.get("view"), kwargs)

        # ---------------- 5. 调用参数覆盖 ----------------
        call.update({
            key: value
            for key, value in kwargs.items()
            if key not in {"view", "lims"}
        })

        # xlim/ylim/zlim 作为 add() 参数时也写进 view
        for axis_name in ("xlim", "ylim", "zlim"):
            if axis_name in kwargs and kwargs[axis_name] is not None:
                call["view"][axis_name] = kwargs[axis_name]
                call.pop(axis_name, None)

        # ---------------- 6. 清理 ----------------
        return method_name, self.clean_call(call)

    @staticmethod
    def map_data(kind, data, kwargs):
        """把用户给的数据映射到对应方法的参数名。

        支持两种写法::

            session.add("line", {"x": x, "y": y})
            session.add("quiver", x=X, y=Y, u=U, v=V)
        """

        mapping = dict(data) if isinstance(data, dict) else {}

        # 允许 data 直接是数组：按 kind 推断参数名
        if data is not None and not isinstance(data, dict):
            array = np.asarray(data)

            if kind in ("line", "scatter", "bar", "hist", "pie"):
                if kind == "hist":
                    mapping = {"x": data}
                elif array.ndim == 2 and array.shape[0] == 2:
                    mapping = {"x": array[0], "y": array[1]}
                else:
                    mapping = {"x": array, "y": kwargs.get("y")}
            elif kind in ("heatmap", "image", "correlation"):
                mapping = {"data" if kind == "heatmap" else "image": data}

                if kind == "correlation":
                    mapping = {"data": data}
            elif kind == "table":
                mapping = {"cell_text": data}
            elif kind in ("surface", "contour"):
                mapping = {"z": data}
            else:
                mapping = {"x": data}

        # 与显式 kwargs 合并，kwargs 优先
        merged = dict(mapping)

        for key, value in kwargs.items():
            if key in DATA_PARAMETER_NAMES:
                merged[key] = value

        return {
            key: value for key, value in merged.items() if value is not None
        }

    def merge_view(self, base_view, kwargs):
        """合并 view：图层预设 -> init() 的范围 -> kwargs 的 lims。"""

        view = dict(base_view or {})

        # init() 里给的 xlim/ylim/zlim
        for axis_name in ("xlim", "ylim", "zlim"):
            value = self.limits.get(axis_name)

            if value is not None:
                view[axis_name] = value

        # add(..., lims=(xlim, ylim)) 或 lims=(xlim, ylim, zlim)
        lims = kwargs.get("lims")

        if lims is not None:
            lims = list(lims)
            names = ["xlim", "ylim", "zlim"]

            if len(lims) > len(names):
                raise ValueError(
                    "lims 最多给 3 组范围 (xlim, ylim, zlim)，"
                    f"当前给了 {len(lims)} 组"
                )

            for name, value in zip(names, lims):
                if value is not None:
                    view[name] = value

        # add(..., view={...}) 直接并进来
        if isinstance(kwargs.get("view"), dict):
            view.update(kwargs["view"])

        # 全局样式里的网格设置
        if "grid" in self.style:
            view.setdefault("grid", self.style["grid"])

        for key in ("grid_linestyle", "grid_alpha", "grid_color"):
            if key in self.style:
                view.setdefault(key, self.style[key])

        # scale / aspect / xscale / yscale
        for key in ("aspect", "xscale", "yscale", "ticks_rotation"):
            if self.style.get(key) is not None:
                view.setdefault(key, self.style[key])

        if self.style.get("scale") is not None:
            view.setdefault("yscale", self.style["scale"])

        return self.clean_view(view)

    @staticmethod
    def clean_view(view):
        """去掉 view 里值为 None 的键，避免把 None 传进 matplotlib。"""

        return {
            key: value
            for key, value in dict(view or {}).items()
            if value is not None
        }

    @staticmethod
    def clean_call(call):
        """去掉值为 None 的样式键（少数特殊键除外）。"""

        call = dict(call)

        return {
            key: value
            for key, value in call.items()
            if value is not None or key in ALWAYS_KEPT_KEYS
        }

    # ================================================================
    # 对外接口
    # ================================================================

    def add(self, kind, data=None, **kwargs):
        """添加一个图层。

        参数
        ----
        kind
            图层类型；只写 kind 和数据即可
        data
            数据字典，也可以直接用关键字传 ``x``、``y``、``z``、``u``、``v``…
        **kwargs
            覆盖预设的任意参数（``title``、``legend``、``xlim``、``cmap``…）

        返回自身，支持链式调用。
        """

        method_name, call = self.build_call(kind, data=data, **kwargs)

        method = getattr(self.plotter, method_name)

        resolved = self.resolve_kind(kind)
        filtered, dropped = self.filter_call(
            method, call, resolved, plotter_class=self.plotter_class
        )

        # 被丢掉的键通常意味着写错了名字，或者把某个图层的专用参数
        # 当成了全局样式。默认保持兼容，只发一次标准警告；严格模式
        # 直接失败，避免生成“看起来成功但参数没有生效”的图。
        if dropped:
            if self.strict:
                raise TypeError(
                    f"kind={kind} 不支持参数：{dropped}。"
                    "如果确实需要透传，请使用 mpl_kwargs 或注册透传键。"
                )
            warned = self._warned_keys.setdefault(resolved, set())
            fresh = [key for key in dropped if key not in warned]
            if fresh:
                warned.update(fresh)
                message = (
                    f"kind={kind} 忽略了不适用的参数：{fresh}。"
                    "如果确实需要透传，请使用 mpl_kwargs 或注册透传键。"
                )
                warnings.warn(message, UserWarning, stacklevel=2)

        self.records.append({
            "kind": kind,
            "method": method_name,
            "subplot": call.get("subplot"),
            "params": filtered,
            "dropped": dropped,
        })

        method(**filtered)

        return self

    @staticmethod
    def filter_call(method, call, kind=None, plotter_class=None):
        """按目标方法的真实签名过滤参数。

        返回 ``(可用参数, 被丢弃的参数名)``。

        允许三类键通过：

        1. 方法签名里存在的参数；
        2. 通用 artist 样式键（``color``、``linewidth``、``alpha``…）；
        3. 该 kind 专属的透传白名单（见 ``PASSTHROUGH_BY_KIND``）。

        被丢弃的键会被记录下来，可以用 ``get_dropped_keys()`` 查出来。
        这样「全局样式里写了某个图层用不到的键」不会让绘图直接报
        ``TypeError``，但又能在调试时看到。
        """

        signature = inspect.signature(method)

        allowed = {
            name
            for name, parameter in signature.parameters.items()
            if name != "self"
            and parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )

        if not accepts_kwargs:
            # 没有 **kwargs 的方法：只认签名
            filtered = {
                key: value for key, value in call.items() if key in allowed
            }
            return filtered, sorted(set(call) - set(filtered))

        passthrough_keys = getattr(
            plotter_class, "PASSTHROUGH_KEYS", registries.PASSTHROUGH_KEYS
        )
        passthrough_by_kind = getattr(
            plotter_class, "PASSTHROUGH_BY_KIND",
            registries.PASSTHROUGH_BY_KIND,
        )

        passthrough = set(passthrough_keys)
        passthrough.update(passthrough_by_kind.get(kind, ()))
        # ``mpl_kwargs`` 是框架参数（它自己装着要透传的键），
        # 不能按「未知键」丢掉；真正的合并发生在 _register_layer()。
        passthrough.add("mpl_kwargs")

        filtered = {}
        dropped = []

        for key, value in call.items():
            if key in allowed or key in passthrough:
                filtered[key] = value
            else:
                dropped.append(key)

        return filtered, sorted(dropped)

    def add_many(self, *layers):
        """一次添加多个图层。

        ::

            session.add_many(
                ("line", {"x": x, "y": y}),
                ("surface", {"x": X, "y": Y, "z": Z}),
            )
        """

        for item in layers:
            if isinstance(item, dict):
                item = dict(item)
                kind = item.pop("kind")
                self.add(kind, **item)
            else:
                kind, data = item
                self.add(kind, data)

        return self

    def get_records(self):
        """返回每次 ``add()`` 的记录（kind、方法名、子图、最终参数、被丢弃的键）。"""

        return copy.deepcopy(self.records)

    def get_dropped_keys(self):
        """返回「因为目标方法不接受而被丢弃」的样式键。

        通常说明全局样式里写了该图层用不到的键，
        例如给 ``table`` 传了 ``cmap``。
        """

        dropped = {}

        for record in self.records:
            if record["dropped"]:
                dropped.setdefault(record["kind"], set()).update(
                    record["dropped"]
                )

        return {key: sorted(value) for key, value in dropped.items()}

    def kind_presets(self, kind):
        """查看某个 kind 的预设参数。"""

        return self.plotter_class.kind_presets(kind)

    # ---- 转发给内部 MultiPlotter 的常用方法 ----

    def draw(self, *args, **kwargs):
        """绘制全部图层，参数与 ``MultiPlotter.draw()`` 完全一致。"""

        return self.plotter.draw(*args, **kwargs)

    def clear(self, *args, **kwargs):
        """清空已添加的图层与记录，保留初始化设置。

        额外参数会原样转给 ``MultiPlotter.clear()``
        （例如 ``close_figures=True``）。
        """

        self.plotter.clear(*args, **kwargs)
        self.records = []

        return self

    def close(self):
        """关闭内部绘图对象产生的 Figure。"""

        self.plotter.close()

        return self

    def __getattr__(self, name):
        """未定义的属性转发给内部的 ``MultiPlotter``。

        这样 ``plotter.get_axes(0)`` / ``add_layer(...)`` 等老写法依然可用。
        """

        if name.startswith("__"):
            raise AttributeError(name)

        # __init__ 还没跑完时 __dict__ 里可能没有 plotter，
        # 这里必须直接抛 AttributeError，不能用会递归的 self.plotter
        plotter = self.__dict__.get("plotter")

        if plotter is not None:
            try:
                return getattr(plotter, name)
            except AttributeError:
                pass

        raise AttributeError(f"PlotBuilder 没有属性 {name!r}")

    def __len__(self):
        return len(self.records)

    def __repr__(self):
        return (
            f"PlotBuilder({self.plotter_class.__name__}, "
            f"ncols={self.ncols}, dpi={self.dpi}, "
            f"layers={len(self.records)})"
        )


__all__ = ["PlotBuilder", "AXIS_LEVEL_STYLE_KEYS", "DATA_PARAMETER_NAMES"]
