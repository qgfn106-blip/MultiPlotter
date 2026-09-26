# -*- coding: utf-8 -*-
"""保存路径解析与动画 writer 选择。

本模块只管「文件往哪里写、用什么写」，不碰图层配置。
所有保存动作都作用在传入的 ``Figure`` 上（``fig.savefig``），
不使用 ``plt.savefig``，避免多个 Figure 同时存在时保存错图。

公开 API
--------
``get_unique_filename(path)``      同名文件自动加序号
``resolve_save_path(...)``         把用户给的 save_path 解析成真实文件路径
``save_figure(fig, ...)``          保存静态图
``resolve_animation_writer(...)``  按扩展名选择动画 writer
``default_animation_name(...)``    ``save=True`` 时的默认动画文件名
"""

from __future__ import annotations

import os

#: 动画保存路径的扩展名 -> writer 名称。
ANIMATION_WRITERS = {
    ".gif": "pillow",
    ".mp4": "ffmpeg",
    ".m4v": "ffmpeg",
    ".mov": "ffmpeg",
    ".avi": "ffmpeg",
    ".mkv": "ffmpeg",
    ".webm": "ffmpeg",
    ".html": "html",
    ".htm": "html",
}

#: writer 字符串别名 -> matplotlib 里的 writer 类名。
_WRITER_ALIASES = {
    "pillow": "PillowWriter",
    "gif": "PillowWriter",
    "ffmpeg": "FFMpegWriter",
    "mp4": "FFMpegWriter",
    "html": "HTMLWriter",
}

#: 默认保存目录名（与旧版保持一致）。
DEFAULT_DIRECTORY = "分析结果"


def get_unique_filename(filepath):
    """如果文件已存在，自动在文件名后加序号，避免覆盖旧结果。"""

    if not os.path.exists(filepath):
        return filepath

    base, ext = os.path.splitext(filepath)
    counter = 1
    new_filepath = f"{base}_{counter}{ext}"

    while os.path.exists(new_filepath):
        counter += 1
        new_filepath = f"{base}_{counter}{ext}"

    return new_filepath


def resolve_save_path(save_path, default_name="MultiPlotter"):
    """把 ``draw(save_path=...)`` 解析成最终要写入的文件路径。

    支持四种写法：

    ============================  ==================================
    ``save_path="results/a.png"`` 完整文件路径
    ``save_path="results/a"``     自动补上 ``.png``
    ``save_path="results/"``      目录，使用 ``default_name``
    ``save_path="results"``       已存在的目录，同上
    ============================  ==================================

    父目录不存在时自动创建；同名文件已存在时自动加序号。
    """

    path = os.path.abspath(os.path.expanduser(str(save_path)))

    # 以路径分隔符结尾，或者本身就是一个已存在的目录
    if str(save_path).endswith(("/", "\\")) or os.path.isdir(path):
        directory, filename = path, default_name
    else:
        directory, filename = os.path.split(path)

    if not os.path.splitext(filename)[1]:
        filename = f"{filename}.png"

    os.makedirs(directory, exist_ok=True)

    return get_unique_filename(os.path.join(directory, filename))


def save_figure(fig, save_path=None, save=False,
                save_path_name=DEFAULT_DIRECTORY, default_name="MultiPlotter"):
    """保存 ``fig``，返回真正写入的路径（没有保存时返回 ``None``）。

    优先级：``save_path`` > ``save=True``。
    只写 ``save=True`` 时保存到 ``save_path_name`` 目录下的
    ``default_name.png``。
    """

    if save_path is not None:
        target = resolve_save_path(save_path, default_name=default_name)

    elif save:
        os.makedirs(save_path_name, exist_ok=True)
        target = get_unique_filename(
            os.path.join(save_path_name, f"{default_name}.png")
        )

    else:
        return None

    fig.savefig(target)

    return target


def _writer_is_available(name):
    """matplotlib 是否真的能实例化这个 writer（Pillow / ffmpeg 是否就绪）。"""

    from matplotlib import animation as mpl_animation

    try:
        return (
            name in mpl_animation.writers.list()
            and mpl_animation.writers.is_available(name)
        )
    except Exception:                                   # noqa: BLE001
        return False


def resolve_animation_writer(path, writer=None, fps=25):
    """根据保存路径选择动画 writer。

    =============  =================
    ``.gif``       ``PillowWriter``
    ``.mp4`` 等    ``FFMpegWriter``
    ``.html``      ``HTMLWriter``
    =============  =================

    没有扩展名（或扩展名不认识）时默认用 GIF，并自动补上 ``.gif``。
    也可以直接传 writer 实例、writer 类或 writer 名称字符串。

    返回 ``(writer 实例, 最终路径)``。
    """

    from matplotlib import animation as mpl_animation

    if isinstance(writer, str):
        key = writer.strip().lower()
        class_name = _WRITER_ALIASES.get(key)

        if class_name is None:
            raise ValueError(
                "writer 字符串只支持：pillow、gif、ffmpeg、mp4、html，"
                f"当前为{writer!r}；也可以直接传 writer 实例"
            )

        writer = getattr(mpl_animation, class_name)

    if writer is not None:
        # 直接传实例时不再补 fps
        if isinstance(writer, mpl_animation.MovieWriter):
            return writer, path

        return writer(fps=fps), path

    suffix = os.path.splitext(path)[1].lower()
    name = ANIMATION_WRITERS.get(suffix)

    if name is None:
        # 没有扩展名或扩展名不认识，默认 GIF
        path = f"{path}.gif"
        name = "pillow"

    if name == "pillow":
        if not _writer_is_available("pillow"):
            raise RuntimeError(
                "保存 GIF 需要 Pillow writer，请先执行 pip install pillow；"
                "或者把保存路径改成 .mp4（需要 ffmpeg）。"
            )

        return mpl_animation.PillowWriter(fps=fps), path

    if name == "ffmpeg":
        if not _writer_is_available("ffmpeg"):
            raise RuntimeError(
                "保存 MP4 需要 ffmpeg，请先安装 ffmpeg 并加入 PATH，"
                "或者设置 plt.rcParams['animation.ffmpeg_path']；"
                "也可以把保存路径改成 .gif（只用 Pillow）。"
            )

        return (
            mpl_animation.FFMpegWriter(
                fps=fps,
                bitrate=2400,
                codec="h264",
                extra_args=["-pix_fmt", "yuv420p"],
            ),
            path,
        )

    return mpl_animation.HTMLWriter(fps=fps, embed_frames=True), path


def default_animation_name(frames_count):
    """``save=True`` 时的默认动画文件名：按帧数决定 GIF 还是 MP4。

    帧数多、尺寸大的动画用 MP4 体积小很多；
    帧数少或没有 ffmpeg 时退回 GIF。
    """

    suffix = ".gif"

    if (_writer_is_available("ffmpeg")
            and frames_count is not None
            and frames_count > 120):
        suffix = ".mp4"

    return f"MultiPlotter_animation{suffix}"


__all__ = [
    "ANIMATION_WRITERS",
    "DEFAULT_DIRECTORY",
    "get_unique_filename",
    "resolve_save_path",
    "save_figure",
    "resolve_animation_writer",
    "default_animation_name",
]
