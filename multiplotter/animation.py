# -*- coding: utf-8 -*-
"""``AnimationPlotter``：在 ``MultiPlotter`` 之上增加动画能力。

工作方式：

1. 和 ``MultiPlotter`` 一样用 ``add_plot`` / ``add_surface`` … 添加图层；
2. 先调用 ``draw()``，得到固定的 Figure 和 Axes；
3. 再调用 ``animate()`` 生成并播放/保存动画。

与 ``MultiPlotter`` 的区别：

* ``animate()`` 会把参数整理进 ``self._anim_state``，交给 ``_animation_frame``；
* 每帧重绘前会重新应用坐标轴范围，因此动画里的坐标轴不会抖动；
* 会检查每个动画子图是否固定了 ``xlim`` / ``ylim`` / ``zlim``，
  没有固定时默认直接抛 ``ValueError``（可用 ``allow_auto_limits=True`` 放宽）；
* 可以直接把 ``FuncAnimation`` 的参数（``frames``、``interval``、``blit``、
  ``repeat``、``cache_frame_data`` 等）透传进去；
* 可以和 ``save`` / ``save_path`` 联动保存 GIF / MP4 / HTML。

生命周期
--------
* ``draw()`` 记住 Figure / Axes；
* ``stop_animation()`` 只停动画，不清图层；
* ``clear()`` 会先 ``stop_animation()``，再清配置；
  ``clear(close_figures=True)`` 还会关闭画布；
* ``close()`` 关闭画布，保留配置。
"""

from __future__ import annotations

import inspect
import os

import numpy as np
import matplotlib.pyplot as plt

from .compat import call_with_supported
from .core import MultiPlotter
from .layout import (
    apply_3d_view,
    as_limit_dict,
    normalize_axis_limit,
    resolve_subplots,
)
from .saving import (
    ANIMATION_WRITERS,
    DEFAULT_DIRECTORY,
    default_animation_name,
    resolve_animation_writer,
    resolve_save_path,
)
from .styles import apply_theme_to_axes, facecolor_for, resolve_theme


def bind_fargs(func, fargs):
    """把额外的位置参数拼到 ``update_func`` 后面。

    ``update_func`` 和 ``fargs`` 都是普通 Python 对象，
    这里用闭包而不是 ``functools.partial``，
    避免参数顺序被 ``partial`` 改写。
    """

    if not fargs:
        return func

    def bound(*args):
        return func(*args, *fargs)

    return bound


class AnimationPlotter(MultiPlotter):
    """在 ``MultiPlotter`` 基础上增加动画能力的绘图类。

    最简用法::

        plotter = AnimationPlotter(ncols=1, figsize_per_plot=(7, 4), dpi=100)

        plotter.add_plot(
            kind="line", x=x, y=np.sin(x), subplot=0,
            xlabel="x", ylabel="y",
            view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)},  # 必须固定范围
        )

        plotter.draw(show=False)

        plotter.animate(
            frames=60,
            update_func=lambda frame: {"y": np.sin(x - frame / 20 * np.pi)},
            save=True, save_path="output/sine.gif",
        )
    """

    #: 动画专用图层类型，不会和 ``MultiPlotter`` 的 ``SUPPORTED_KINDS`` 冲突。
    ANIMATION_KIND = "animation"

    #: 支持的动画帧更新模式。
    UPDATE_MODES = ("reset", "artists", "append")

    #: ``save_path`` 的扩展名 -> matplotlib 的动画 writer。
    ANIMATION_WRITERS = ANIMATION_WRITERS

    def __init__(self, ncols=2, figsize_per_plot=(6, 4), dpi=120, theme=None):
        super().__init__(ncols, figsize_per_plot, dpi, theme=theme)

        # 最近一次 draw() 得到的 Figure 和 Axes
        self._fig = None
        self._axes = None

        # 当前正在运行的动画
        self._animation = None
        # 当前动画调用的 update_func（停止动画后保留，便于查看）
        self._update_func = None
        # 当前动画的状态字典
        self._anim_state = {}

        # 最近一次 animate() 使用的参数，便于复查
        self._animation_params = {}

    # ================================================================
    # 生命周期
    # ================================================================

    def clear(self, close_figures=None):
        """先停止动画，再清空图层配置。

        ``close_figures``
            ``True`` 时同时关闭 ``draw()`` 产生的 Figure。
        """

        self.stop_animation()

        self._fig = None
        self._axes = None

        return super().clear(close_figures=close_figures)

    def close(self):
        """关闭画布（同时停止动画），保留图层配置。"""

        self.stop_animation()

        return super().close()

    def stop_animation(self):
        """停止当前动画并清空动画状态。

        只影响动画，不会清空图层配置和画布。
        """

        if self._animation is not None:
            try:
                self._animation.event_source.stop()
            except Exception:                           # noqa: BLE001
                pass

        self._animation = None
        self._anim_state = {}
        self._update_func = None

        return self

    # ================================================================
    # 内部工具
    # ================================================================

    # 兼容旧代码：静态方法版本
    _as_limit_dict = staticmethod(as_limit_dict)
    _normalize_axis_limit = staticmethod(normalize_axis_limit)
    _resolve_subplots = staticmethod(resolve_subplots)

    def _check_limits_fixed(self, subplots, allow_auto_limits):
        """检查这些子图是否已经固定了坐标轴范围。

        判断依据是 ``draw()`` 时记录的 view 配置：
        只有 view 里明确写了 ``xlim`` / ``ylim`` / ``zlim``，才算固定。

        返回没有固定范围的 subplot 序号列表；
        ``allow_auto_limits=False`` 时直接抛 ``ValueError``。
        """

        missing = []

        for subplot in subplots:
            limits = self._explicit_limits.get(subplot, {})
            dimension = self._dimension_by_subplot.get(subplot, 2)

            required = ["xlim", "ylim"]

            if dimension == 3:
                required.append("zlim")

            if any(name not in limits for name in required):
                missing.append(subplot)

        if missing and not allow_auto_limits:
            details = []

            for subplot in missing:
                limits = self._explicit_limits.get(subplot, {})
                dimension = self._dimension_by_subplot.get(subplot, 2)
                required = ["xlim", "ylim"] + (
                    ["zlim"] if dimension == 3 else []
                )
                not_set = [name for name in required if name not in limits]

                details.append(
                    f"subplot={subplot}（{dimension}维）缺少 "
                    + "、".join(not_set)
                )

            raise ValueError(
                "做动画前必须固定坐标轴范围，否则每帧会自动缩放，画面会抖动。\n"
                "问题子图：\n  - "
                + "\n  - ".join(details)
                + "\n\n解决办法（任选其一）：\n"
                "  1) 在添加图层时用 view 固定范围：\n"
                "     plotter.add_plot(..., view={\"xlim\": (0, 10), \"ylim\": (-2, 2)})\n"
                "  2) 调用 animate(..., xlim=(0, 10), ylim=(-2, 2)) 显式给出范围；\n"
                "  3) 调用 animate(..., allow_auto_limits=True)，"
                "用绘制完成时的当前范围兜底。"
            )

        return missing

    def _apply_stored_limits(self, subplot, ax, limits=None):
        """把记录下来的坐标轴范围重新应用到坐标轴上。

        每帧重绘后调用，保证动画过程中坐标轴范围始终不变。
        """

        stored = dict(self._explicit_limits.get(subplot, {}))

        if limits:
            stored.update(limits)

        if "xlim" in stored:
            ax.set_xlim(stored["xlim"])

        if "ylim" in stored:
            ax.set_ylim(stored["ylim"])

        if "zlim" in stored and hasattr(ax, "set_zlim"):
            ax.set_zlim(stored["zlim"])

        return stored

    @staticmethod
    def _describe_artist(artist):
        """给未参与 blit 的对象拼一个可读的名字，用于错误提示。"""

        label = None

        try:
            if (artist.get_label()
                    and not str(artist.get_label()).startswith("_")):
                label = artist.get_label()
        except Exception:                               # noqa: BLE001
            label = None

        name = type(artist).__name__

        return f"{name}(label={label})" if label else name

    def _check_blit_artists(self, ax, returned):
        """检查 ``blit=True`` 时返回的 artist 是否漏掉了新画的对象。

        blit 只会重绘 ``update_func`` 返回的 artist，
        如果 ``update_func`` 新建了对象却没有返回，画面上就看不到它。
        这里只做提醒，不抛异常。
        """

        missing = []

        try:
            drawn = list(ax.lines) + list(ax.collections) + list(ax.patches)
        except Exception:                               # noqa: BLE001
            return missing

        for artist in drawn:
            try:
                animated = artist.get_animated()
            except Exception:                           # noqa: BLE001
                continue

            if artist not in returned and not animated:
                try:
                    if not artist.get_visible():
                        continue
                except Exception:                       # noqa: BLE001
                    pass

                missing.append(artist)

        if missing and not self._anim_state.get("_blit_warned"):
            self._anim_state["_blit_warned"] = True
            names = "、".join(
                self._describe_artist(artist) for artist in missing[:5]
            )

            print(
                "[AnimationPlotter] blit=True 时，update_func 新建的对象"
                f"必须一起返回，否则不会显示。当前没有返回的可见对象：{names}。"
                "建议 update_func 末尾 return ax, 或改用 blit=False。"
            )

        return missing

    def _apply_user_options(self, ax, options, dimension):
        """``update_mode="reset"`` 时，在 ``ax.clear()`` 之后重新应用这些设置。"""

        if not options:
            return

        # 用实例主题重设面板颜色（不再无条件改全局 rcParams）
        apply_theme_to_axes(
            ax, dimension, resolve_theme(self.theme)
        )

        # 坐标轴范围单独处理，避免被下面的通用分支覆盖
        limits = {
            key: options[key]
            for key in ("xlim", "ylim", "zlim")
            if key in options
        }

        for key, value in options.items():
            if key in limits:
                continue

            if key == "title":
                ax.set_title(value)
            elif key == "xlabel":
                ax.set_xlabel(value)
            elif key == "ylabel":
                ax.set_ylabel(value)
            elif key == "zlabel" and dimension == 3:
                ax.set_zlabel(value)
            elif key == "grid":
                ax.grid(value)
            elif key == "aspect":
                ax.set_aspect(value)
            elif key == "xscale":
                ax.set_xscale(value)
            elif key == "yscale":
                ax.set_yscale(value)
            elif key == "axis":
                ax.axis(value)
            elif key == "axis_off" and value:
                ax.set_axis_off()
            elif key == "legend" and value:
                ax.legend(**(options.get("legend_kwargs") or {}))
            elif key == "view" and dimension == 3:
                apply_3d_view(ax, value)

        for name, value in limits.items():
            if name == "zlim" and hasattr(ax, "set_zlim"):
                ax.set_zlim(value)
            elif name == "xlim":
                ax.set_xlim(value)
            elif name == "ylim":
                ax.set_ylim(value)

    def _apply_dimension_style(self, subplot):
        """按子图维度重新套用一次面板颜色，返回该子图的维度。"""

        dimension = self._dimension_by_subplot.get(subplot, 2)

        ax = self._subplot_axes.get(subplot)

        if ax is not None:
            apply_theme_to_axes(ax, dimension, resolve_theme(self.theme))

        return dimension

    # ================================================================
    # 帧更新逻辑
    # ================================================================

    @staticmethod
    def _accepts_frame_arg(func):
        """判断 ``update_func`` 的签名是 ``update(ax, frame)`` 还是 ``update(frame)``。

        判断方法：看它能否只用「一个位置参数」完成绑定。

        * ``def update(ax, frame)`` -> ``bind(0)`` 失败 -> 返回 ``True``
        * ``def update(frame)`` -> ``bind(0)`` 成功 -> 返回 ``False``

        如果签名里有名为 ``ax`` / ``axis`` / ``axes`` / ``obj`` / ``target``
        的参数，也按 ``update(ax, frame)`` 处理。

        无法解析签名（例如内置函数）时，默认按 ``update(ax, frame)`` 调用。
        """

        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return True

        parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]

        if not parameters:
            return True

        # 必须至少能接收两个位置参数才能按 (ax, frame) 调用
        can_take_two = any(
            parameter.kind == inspect.Parameter.VAR_POSITIONAL
            for parameter in signature.parameters.values()
        ) or len(parameters) >= 2

        if not can_take_two:
            return False

        # 只有一个必填参数时，bind(0) 能成功说明它只想要帧号
        first_name = parameters[0].name.lower()

        if first_name in {"ax", "axis", "axes", "obj", "target"}:
            return True

        try:
            signature.bind(0)
        except TypeError:
            # 一个位置参数不够，说明需要 (ax, frame)
            return True

        return False

    @classmethod
    def _build_frame_function(cls, update_func):
        """把用户的 ``update_func`` 包装成 ``FuncAnimation`` 需要的 ``func(frame)``。"""

        if update_func is None:
            return None

        if update_func is cls._default_update_func:
            return update_func

        accepts_frame = cls._accepts_frame_arg(update_func)

        def frame_function(frame):
            if accepts_frame:
                return update_func(frame)

            return update_func()

        return frame_function

    @staticmethod
    def _default_update_func(ax, frame):
        """默认的更新函数：在坐标轴原点画流走的点，表示动画已经在运行。"""

        ax.plot(
            [0.0],
            [0.0],
            marker="o",
            markersize=8 + (frame % 6),
            color="#E64A19",
            alpha=max(0.15, 1.0 - (frame % 30) / 40.0),
            zorder=5,
        )
        ax.set_title(f"AnimationPlotter 默认动画  frame={frame}")

        return ax

    def _animation_frame(self, frame):
        """``FuncAnimation`` 每一帧实际执行的函数。

        流程：

        1. 取出这一帧的数据；
        2. 对 ``subplots`` 里的**每个**子图，按 ``update_mode`` 决定重绘还是原地更新；
        3. 重新套用坐标轴范围，保证坐标轴不抖动；
        4. 汇总所有子图返回的 artist，供 blit 使用。

        注意：``subplots`` 里可能不止一个子图（例如左图箭头 + 右图流线），
        每一帧都必须逐个处理，否则没被处理的那个子图会一直停在
        ``draw()`` 时的第一帧，看起来就像「不动」。
        """

        state = self._anim_state
        subplot_list = state.get("subplots") or [state["subplot"]]
        mode = state["mode"]
        callback = state["callback"]
        frame_value = self._frame_value(frame)
        all_limits = state.get("all_limits") or {}

        artists = []

        # ---------- 逐个处理每个参与动画的子图 ----------
        for subplot in subplot_list:
            ax = self._subplot_axes[subplot]
            dimension = self._dimension_by_subplot.get(subplot, 2)

            # 每个子图自己的范围：优先用它自己的记录，
            # 没有再退回主 subplot 的范围
            limits = all_limits.get(subplot, state["limits"])

            # ---------- 1. 重绘模式：先清空坐标轴 ----------
            if mode == "reset":
                ax.clear()

                if state["reset_options"] is not None:
                    self._apply_user_options(
                        ax, state["reset_options"], dimension
                    )

                # update_mode="artists"/"append" 时清空会丢对象，
                # 所以只有 reset 模式需要在这里恢复范围
                self._apply_stored_limits(subplot, ax, limits)

            # ---------- 2. 交给用户的回调画这一帧 ----------
            # with_ax=True  -> update_func(ax, frame_value)
            # with_ax=False -> update_func(frame_value)
            # 其中 frame_value 在给了 frame_data 时是那一帧的数据，
            # 否则就是帧号本身。
            try:
                if state["with_ax"]:
                    result = callback(ax, frame_value)
                else:
                    result = callback(frame_value)
            except Exception as error:                  # noqa: BLE001
                # 记下来。matplotlib 的 writer 在回调抛错时会先把
                # 自己的 finish() 走完，那个二次异常会盖掉这里的原始异常，
                # 最后只看到 "IndexError: list index out of range"，
                # 完全看不出是回调写错了。保存失败时用它还原真正的错误。
                state["callback_error"] = error
                raise

            # 回调返回 None 时按模式兜底，保证 blit 有东西可重绘
            if result is None:
                result = ax if mode == "reset" else []

            if result is ax:
                artists.append(ax)
            elif isinstance(result, (list, tuple, set)):
                artists.extend(result)
            else:
                artists.append(result)

            # ---------- 3. 再次固定坐标轴范围 ----------
            if mode != "reset":
                self._apply_stored_limits(subplot, ax, limits)

            # ---------- 4. blit 自检 ----------
            if state["blit"] and mode == "reset":
                self._check_blit_artists(ax, artists)

        state["last_artists"] = artists

        return artists

    def _frame_value(self, frame):
        """取出这一帧对应的数据。

        * 没有给 ``frame_data`` 时直接返回帧号；
        * ``frame_data`` 是字典时按帧做键；
        * ``frame_data`` 是序列时按帧号取下标的元素，
          下标越界（例如 ``frames`` 比数据长）时取最后一个元素，
          这样 ``frames=60`` + 少量帧数据也不会因为越界报错。
        """

        frame_data = self._anim_state.get("frame_data")

        if frame_data is None:
            return frame

        if isinstance(frame_data, dict):
            if frame in frame_data:
                return frame_data[frame]

            # 帧号是整数时再试一次整数键
            try:
                index = int(frame)
            except (TypeError, ValueError):
                index = None

            if index is not None and index in frame_data:
                return frame_data[index]

            raise KeyError(
                f"frame_data 中没有第 {frame!r} 帧。"
                f"frame_data 一共有 {len(frame_data)} 帧，"
                "常见原因：frames 的取值和 frame_data 的键不一致。\n"
                "建议二选一：\n"
                "  1) 让帧号来自 frame_data：animate(frame_data=data, frames=None)\n"
                f"  2) 直接把 frames 写成 frame_data 的键："
                f"animate(frames={list(frame_data.keys())[:8]!r}...)"
            )

        if isinstance(frame_data, (list, tuple, np.ndarray)):
            if len(frame_data) == 0:
                return frame

            index = int(frame)

            if index < 0:
                index = 0
            elif index >= len(frame_data):
                index = len(frame_data) - 1

            return frame_data[index]

        return frame_data

    @staticmethod
    def _resolve_frames(frames, frame_data=None):
        """处理帧参数，返回交给 ``FuncAnimation`` 的 ``frames``。

        规则（``frame_data`` 优先）：

        ``frame_data`` 是字典
            * ``frames=None`` -> 用它的键作为帧序列
            * ``frames`` 是整数或 ``range`` -> 必须和它的键完全一致，否则报错
            * ``frames`` 是其它序列 -> 用它的键（并检查 frames 里的帧都存在）
        ``frame_data`` 是列表 / 元组 / 数组
            * ``frames=None`` -> 用 ``range(len(frame_data))``
            * 其它 -> 按 ``frames`` 处理，取数据时越界会取最后一帧
        ``frame_data=None``
            * ``frames=None`` -> 返回 ``"indefinite"``，表示无限动画
            * ``frames`` 是整数 -> ``range(整数)``
            * 其它 -> 原样交给 ``FuncAnimation``
        """

        if frame_data is not None and isinstance(frame_data, dict):
            keys = list(frame_data.keys())

            # 没有指定 frames：直接用字典的键
            if frames is None:
                return keys

            count = (
                int(frames) if isinstance(frames, (int, np.integer)) else None
            )

            if count is not None:
                expected = list(range(count))

                if expected != keys:
                    raise ValueError(
                        f"frames={count} 与 frame_data 的 "
                        f"{len(frame_data)} 帧不匹配。\n"
                        f"frame_data 的键是：{keys[:8]}"
                        f"{' ...' if len(keys) > 8 else ''}\n"
                        "两种写法任选其一：\n"
                        "  1) animate(frame_data=data)               "
                        "# 帧号自动取 data 的键\n"
                        "  2) animate(frames=list(data.keys()), frame_data=data)"
                    )

                return expected

            # frames 已经是序列：检查里面的帧都能取到数据
            provided = list(frames)
            missing = [
                frame for frame in provided if frame not in frame_data
            ]

            if missing:
                raise KeyError(
                    f"frame_data 里缺少这些帧：{missing[:6]}"
                    f"{' ...' if len(missing) > 6 else ''}。"
                    f"frame_data 一共有 {len(frame_data)} 帧，"
                    f"前几个键是 {list(frame_data.keys())[:6]}。"
                )

            return provided

        # frame_data 是列表 / 元组 / 数组：没给 frames 时按元素个数决定帧数
        if (
            frames is None
            and isinstance(frame_data, (list, tuple, np.ndarray))
            and len(frame_data) > 0
        ):
            return range(len(frame_data))

        if frames is None:
            return "indefinite"

        if isinstance(frames, (int, np.integer)):
            if frames < 0:
                raise ValueError(f"frames不能为负数，当前为{frames}")

            return range(int(frames))

        return frames

    # ================================================================
    # 动画 writer
    # ================================================================

    @classmethod
    def _resolve_animation_writer(cls, path, writer=None, fps=25):
        """根据保存路径选择动画 writer（实现见 :mod:`multiplotter.saving`）。"""

        return resolve_animation_writer(path, writer=writer, fps=fps)

    @staticmethod
    def _default_save_path(frames_count):
        """``save_path=True`` 时的默认文件名。"""

        return default_animation_name(frames_count)

    # ================================================================
    # 对外接口
    # ================================================================

    def get_axes(self, subplot=0):
        """返回指定 subplot 的坐标轴对象，方便在 ``update_func`` 里直接操作。"""

        return self._get_subplot_axes(subplot)

    def get_animation(self):
        """返回当前正在使用的 ``FuncAnimation`` 对象（可能为 ``None``）。"""

        return self._animation

    def get_animation_params(self):
        """返回最近一次 ``animate()`` 的参数副本，便于复查和调试。"""

        return dict(self._animation_params)

    def draw(self, show=True, save=False, save_path=None,
             save_path_name=DEFAULT_DIRECTORY, **kwargs):
        """绘制静态图层，并记住 Figure / Axes 供 ``animate()`` 使用。

        参数与 ``MultiPlotter.draw()`` 完全一致，
        只是多保存了一份坐标轴索引。
        """

        fig, axes = super().draw(
            show=show,
            save=save,
            save_path=save_path,
            save_path_name=save_path_name,
            **kwargs,
        )

        self._fig = fig
        self._axes = axes
        self._subplot_axes = {
            int(index): ax
            for index, ax in enumerate(np.asarray(axes, dtype=object).ravel())
        }

        return fig, axes

    def animate(
        self,
        # ---------------- 目标子图与更新方式 ----------------
        subplots=None,
        update_func=None,
        update_mode="reset",
        fargs=(),
        # ---------------- FuncAnimation 参数 ----------------
        frames=None,
        frame_data=None,
        init_func=None,
        interval=50,
        blit=False,
        repeat=True,
        repeat_delay=0,
        cache_frame_data=False,
        # ---------------- 坐标轴范围检查 ----------------
        xlim=None,
        ylim=None,
        zlim=None,
        allow_auto_limits=False,
        # ---------------- 每帧样式 ----------------
        reset_options=None,
        # ---------------- 保存 ----------------
        save=False,
        save_path=None,
        save_path_name=DEFAULT_DIRECTORY,
        writer=None,
        fps=25,
        dpi=None,
        save_kwargs=None,
    ):
        """为已经 ``draw()`` 过的图层创建动画。

        **目标子图与更新方式**

        ``subplots``
            要动画化的 subplot 序号，默认给所有已经绘制的子图。
            支持 ``None`` / ``"all"`` / 整数 / 整数序列。

        ``update_func``
            帧更新函数。签名支持两种，会自动识别：

            * ``def update(ax, frame): ...`` —— 需要坐标轴时用这种
            * ``def update(frame): ...`` —— 不需要坐标轴时用这种

            第二个参数传的是「当前帧的值」：给了 ``frame_data`` 时它是
            ``frame_data`` 里对应的那一帧数据；没给时就是帧号本身。

            返回值决定 blit 重绘范围，可以返回 artist 或 artist 序列、
            ``ax``（推荐，等价于「整个坐标轴都重绘」）或 ``None``。

        ``update_mode``
            ``"reset"`` / ``"artists"`` / ``"append"``：

            * ``"reset"`` 每帧先 ``ax.clear()`` 再让 ``update_func`` 重画。
              通用、直观，能画任意类型的图，速度中等。
            * ``"artists"`` 不清空坐标轴，只在 ``update_func`` 里对已有对象
              调用 ``set_data`` / ``set_offsets`` 等原地更新。
              最快，但要求图层对象在 ``draw()`` 之后能被拿到。
            * ``"append"`` 不 clear，每帧把新画的对象累积到画布上，
              适合画轨迹、粒子、覆盖层。

        ``fargs``
            追加传给 ``update_func`` 的位置参数，
            实际调用为 ``update_func(ax, frame, *fargs)`` 或
            ``update_func(frame, *fargs)``。

        **FuncAnimation 参数**

        ``frames``
            帧数或帧序列。整数 ``n`` 表示 ``range(n)``；可迭代对象原样使用；
            ``None`` 时：没有 ``frame_data`` 表示无限动画（不能保存），
            有 ``frame_data`` 则自动取它的长度或键。

        ``frame_data``
            每一帧的数据。给出后帧号会从它的键（字典）或下标（序列）生成，
            回调里可以拿到对应的那一帧数据。

        ``init_func`` / ``interval`` / ``blit`` / ``repeat`` /
        ``repeat_delay`` / ``cache_frame_data``
            与 ``matplotlib.animation.FuncAnimation`` 同名同义。
            三维不支持 ``blit``（会强制为 ``False``）。

        **坐标轴范围检查**

        ``xlim`` / ``ylim`` / ``zlim``
            显式指定的坐标轴范围，优先级高于 ``view`` 里的设置。支持::

                xlim=(0, 10)                     # 所有子图统一
                xlim={0: (0, 10), 1: (-1, 1)}    # 每个子图分别指定
                xlim=(0, 10) 与 ylim=(-1, 1)     # 分别指定两条轴
                xlim=((0, 10), (-1, 1))          # 一次给出 x、y

        ``allow_auto_limits``
            默认 ``False``：子图没有用 ``view`` 固定范围时直接抛
            ``ValueError``。设为 ``True``：用绘制完成时的当前范围兜底。

        **每帧样式**

        ``reset_options``
            ``update_mode="reset"`` 时，``ax.clear()`` 之后重新应用的样式。
            可用键：``title``、``xlabel``、``ylabel``、``zlabel``、``grid``、
            ``aspect``、``xscale``、``yscale``、``axis``、``axis_off``、
            ``legend``、``legend_kwargs``、``view``、``xlim``、``ylim``、
            ``zlim``。

        **保存**

        ``save`` / ``save_path`` / ``save_path_name`` / ``writer`` /
        ``fps`` / ``dpi`` / ``save_kwargs``
            * ``save=True`` 且 ``save_path=None``：保存到 ``save_path_name``
              目录，文件名 ``MultiPlotter_animation.gif`` / ``.mp4``；
            * ``save_path="out.gif"`` / ``"out.mp4"`` / ``"out.html"``：
              按扩展名选 writer；
            * ``save_path=True``：等价于 ``save=True``。

        返回 ``(fig, anim)``，即画布和 ``FuncAnimation`` 对象。
        """

        if self._fig is None or not self._subplot_axes:
            raise RuntimeError(
                "还没有可动画的坐标轴，请先调用 draw()。"
                "例如：plotter.draw(show=False)"
            )

        # ---------------- 0. 校验更新模式 ----------------
        if update_mode not in self.UPDATE_MODES:
            raise ValueError(
                f"update_mode 必须是 {self.UPDATE_MODES} 之一，"
                f"当前为{update_mode!r}"
            )

        # ---------------- 1. 解析目标子图 ----------------
        available = sorted(self._subplot_axes)
        subplot_list = resolve_subplots(subplots, available)

        if not subplot_list:
            raise ValueError(
                "没有可以动画化的子图，请先添加图层并调用 draw()"
            )

        for subplot in subplot_list:
            if subplot not in self._subplot_axes:
                raise KeyError(
                    f"subplot={subplot}不存在，"
                    f"当前可用的子图有：{available}"
                )

        if len(subplot_list) > 1 and update_func is None:
            raise ValueError(
                "多个子图同时动画时必须提供 update_func，"
                "因为默认的槽位动画只支持单子图"
            )

        # ---------------- 2. 整理并检查坐标轴范围 ----------------
        limit_overrides = self._collect_limit_overrides(
            subplot_list, xlim, ylim, zlim
        )

        # 记录用户显式给出的范围，后面的检查就不会再报缺少范围
        for subplot, limits in limit_overrides.items():
            self._explicit_limits.setdefault(subplot, {}).update(limits)

        missing = self._check_limits_fixed(subplot_list, allow_auto_limits)

        # ---------------- 3. 确定每个子图每帧使用的范围 ----------------
        per_subplot_limits = {}

        for subplot in subplot_list:
            stored = dict(self._explicit_limits.get(subplot, {}))
            stored.update(limit_overrides.get(subplot, {}))
            per_subplot_limits[subplot] = stored

        self._apply_auto_limits(missing, per_subplot_limits)

        # ---------------- 4. 处理帧数与 3D blit ----------------
        resolved_frames = self._resolve_frames(frames, frame_data)
        frames_count = None

        if resolved_frames != "indefinite":
            try:
                frames_count = len(resolved_frames)
            except TypeError:
                frames_count = None

        # frame_data 是字典时，提前检查帧号是否都能取到数据。
        # 否则要等到真正渲染（save/show）时才会在回调里报错，
        # 报错位置离调用处很远，很难排查。
        self._check_frame_data(frame_data, resolved_frames)

        blit = bool(blit)
        dimensions = {
            self._dimension_by_subplot.get(subplot, 2)
            for subplot in subplot_list
        }

        if blit and 3 in dimensions:
            print(
                "[AnimationPlotter] Axes3D 不支持 blit，已自动改为 blit=False"
            )
            blit = False

        # ---------------- 5. 组织 update_func ----------------
        if update_func is None:
            call_func = self._default_update_func
            with_ax = True
        else:
            call_func = bind_fargs(update_func, fargs)
            with_ax = self._accepts_frame_arg(call_func)

        self._update_func = call_func

        # ---------------- 6. 生成默认 init_func ----------------
        if init_func is None:
            init_func = self._make_init_func(subplot_list, blit)

        # ---------------- 7. 创建 FuncAnimation ----------------
        from matplotlib.animation import FuncAnimation

        self.stop_animation()

        self._anim_state = {
            "subplot": subplot_list[0],
            "subplots": subplot_list,
            "mode": update_mode,
            "frame_data": frame_data,
            "callback": call_func,
            "limits": per_subplot_limits.get(subplot_list[0], {}),
            "all_limits": per_subplot_limits,
            "reset_options": reset_options,
            "blit": blit,
            "with_ax": with_ax,
            "last_artists": [],
            "callback_error": None,
        }

        # FuncAnimation 在构造时就会做一次初始绘制（blit 需要），
        # 这一步同样发生在 draw() 的 rc_context 之外，
        # 所以也要在主题上下文里做，否则中文字体在动画里会变方框。
        with resolve_theme(self.theme).rc_context():
            self._animation = FuncAnimation(
                self._fig,
                self._animation_frame,
                frames=resolved_frames,
                init_func=init_func,
                interval=interval,
                blit=blit,
                repeat=repeat,
                repeat_delay=repeat_delay,
                cache_frame_data=cache_frame_data,
            )

        self._animation_params = {
            "subplots": subplot_list,
            "update_mode": update_mode,
            "frames": frames,
            "frame_data": frame_data,
            "frames_count": frames_count,
            "interval": interval,
            "blit": blit,
            "repeat": repeat,
            "repeat_delay": repeat_delay,
            "cache_frame_data": cache_frame_data,
            "allow_auto_limits": allow_auto_limits,
            "limits": per_subplot_limits,
            "writer": writer,
            "fps": fps,
        }
        self._anim_state.update(self._animation_params)

        # ---------------- 8. 保存 ----------------
        self._save_animation(
            resolved_frames=resolved_frames,
            frames_count=frames_count,
            save=save,
            save_path=save_path,
            save_path_name=save_path_name,
            writer=writer,
            fps=fps,
            dpi=dpi,
            save_kwargs=save_kwargs,
        )

        return self._fig, self._animation

    # ---- animate() 的几个步骤（拆出来便于阅读与测试）----

    def _collect_limit_overrides(self, subplot_list, xlim, ylim, zlim):
        """把 ``xlim`` / ``ylim`` / ``zlim`` 参数整理成 ``{subplot: 范围}``。"""

        limit_overrides = {}

        for name, value in (("xlim", xlim), ("ylim", ylim), ("zlim", zlim)):
            if value is None:
                continue

            normalized = as_limit_dict(value, name)

            if "__all__" in normalized:
                # 统一范围：按每个子图的维度拆成 xlim / ylim / zlim
                items = [
                    (subplot, normalized["__all__"])
                    for subplot in subplot_list
                ]
            else:
                items = list(normalized.items())

            for subplot, item in items:
                dimension = self._dimension_by_subplot.get(subplot, 2)

                for axis_name, axis_value in normalize_axis_limit(
                    item, dimension, name
                ):
                    limit_overrides.setdefault(subplot, {})[
                        axis_name
                    ] = axis_value

        return limit_overrides

    def _apply_auto_limits(self, missing, per_subplot_limits):
        """``allow_auto_limits=True`` 且确实缺范围时，用当前显示范围兜底。"""

        for subplot in missing:
            ax = self._subplot_axes[subplot]
            dimension = self._dimension_by_subplot.get(subplot, 2)
            fallback = per_subplot_limits.setdefault(subplot, {})

            fallback.setdefault("xlim", tuple(ax.get_xlim()))
            fallback.setdefault("ylim", tuple(ax.get_ylim()))

            if dimension == 3:
                fallback.setdefault("zlim", tuple(ax.get_zlim()))

                # 三维还要固定视角，否则每帧重绘会让视角复位
                fallback["__view__"] = {
                    "elev": ax.elev,
                    "azim": ax.azim,
                }

    @staticmethod
    def _check_frame_data(frame_data, resolved_frames):
        """提前检查 ``frames`` 里的帧号是否都能在 ``frame_data`` 里取到。"""

        if not isinstance(frame_data, dict):
            return

        if resolved_frames == "indefinite":
            return

        missing_keys = [
            frame for frame in resolved_frames if frame not in frame_data
        ]

        if missing_keys:
            preview = list(frame_data.keys())[:6]

            raise KeyError(
                f"frame_data 里缺少这些帧：{missing_keys[:6]}"
                f"{' ...' if len(missing_keys) > 6 else ''}。"
                f"frame_data 一共有 {len(frame_data)} 帧，"
                f"前几个键是 {preview}。\n"
                "常见原因：frames 与 frame_data 的键不匹配。\n"
                "两种写法任选其一：\n"
                "  1) animate(frame_data=data)              # 帧号自动取 data 的键\n"
                "  2) animate(frames=list(data.keys()), frame_data=data)"
            )

    def _make_init_func(self, subplot_list, blit):
        """生成默认 ``init_func``：把所有可见 artist 标记为初始状态。"""

        def init_func():
            artists = []

            for subplot in subplot_list:
                ax = self._subplot_axes[subplot]

                for artist in (
                    list(ax.lines)
                    + list(ax.collections)
                    + list(ax.patches)
                    + list(ax.texts)
                ):
                    try:
                        artist.set_animated(blit)
                    except Exception:                   # noqa: BLE001
                        pass

                    artists.append(artist)

            return artists

        return init_func

    def _save_animation(self, resolved_frames, frames_count, save, save_path,
                        save_path_name, writer, fps, dpi, save_kwargs):
        """保存动画（按扩展名选 writer），返回最终路径或 ``None``。"""

        should_save = bool(save) or save_path is True
        target_path = None if save_path is True else save_path

        if not should_save and target_path is None:
            return None

        if resolved_frames == "indefinite":
            raise ValueError(
                "无限动画（frames=None）没有长度，无法保存。"
                "请给出具体帧数，例如 frames=60。"
            )

        if target_path is None:
            # save=True：放到 save_path_name 目录下的默认文件名
            os.makedirs(save_path_name, exist_ok=True)
            target_path = os.path.join(
                save_path_name, default_animation_name(frames_count)
            )

        # 动画路径必须带动画扩展名，
        # 否则 resolve_save_path() 会按静态图片补成 .png
        target_path = str(target_path)
        suffix = os.path.splitext(target_path)[1].lower()

        if suffix not in self.ANIMATION_WRITERS:
            target_path = f"{target_path}.gif"

        target_path = resolve_save_path(
            target_path, default_name="MultiPlotter_animation"
        )

        writer_obj, final_path = resolve_animation_writer(
            target_path, writer=writer, fps=fps
        )

        save_arguments = dict(save_kwargs or {})
        save_arguments.setdefault("dpi", dpi or self.dpi)

        # draw() 的 rc_context 早已退出，而这里的渲染发生在很久之后。
        # 不重新进入主题上下文的话，动画会丢掉主题（中文字体变成方框、
        # 背景色回到默认），静态图却是对的 —— 很难排查。
        save_theme = resolve_theme(self.theme)
        theme_context = save_theme.rc_context()

        try:
            with theme_context:
                self._animation.save(
                    final_path, writer=writer_obj, **save_arguments
                )
        except Exception as error:
            # 逐帧回调里出错时，matplotlib 的 writer 会处于半开状态，
            # 直接抛出会把真正的错误（例如 KeyError / TypeError）
            # 盖成 "IndexError: list index out of range"。
            # 这里先关掉 writer，再把回调里的原始异常重新抛出。
            for method in ("finish", "cleanup"):
                try:
                    getattr(writer_obj, method)()
                except Exception:                       # noqa: BLE001
                    pass

            callback_error = self._anim_state.get("callback_error")

            if callback_error is not None:
                self._anim_state["callback_error"] = None

                raise callback_error from error

            raise

        self._animation_params["saved_to"] = final_path

        print(f"[AnimationPlotter] 动画已保存：{final_path}")

        return final_path


__all__ = ["AnimationPlotter", "bind_fargs"]
