# -*- coding: utf-8 -*-
"""AnimationPlotter 的功能与错误处理测试。"""

import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# 本脚本位于 tests/，把包根目录加入 sys.path，才能导入 Multiplotter
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from Multiplotter import AnimationPlotter, MultiPlotter  # noqa: E402
from _test_paths import output_dir  # noqa: E402

OUT = output_dir("animation")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

x = np.linspace(0, 2 * np.pi, 200)
ok = 0
fail = 0


def check(name, condition, extra=""):
    global ok, fail
    if condition:
        ok += 1
        print(f"[PASS] {name} {extra}")
    else:
        fail += 1
        print(f"[FAIL] {name} {extra}")


# ======================================================================
# 1. 继承关系正常
# ======================================================================
check("是 MultiPlotter 的子类", issubclass(AnimationPlotter, MultiPlotter))

# ======================================================================
# 2. 没有固定范围时必须报错
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, title="no view")
p.draw(show=False)
try:
    p.animate(frames=5, update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 5)))
    check("缺少 xlim/ylim 时抛 ValueError", False)
except ValueError as exc:
    msg = str(exc)
    check(
        "缺少 xlim/ylim 时抛 ValueError",
        ("subplot=0" in msg and "xlim" in msg and "ylim" in msg),
    )
plt.close("all")

# 三维缺少 zlim 也要报错
X, Y = np.meshgrid(np.linspace(-3, 3, 40), np.linspace(-3, 3, 40))
Z = np.sin(X) * np.cos(Y)
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
p.add_surface(X, Y, Z, subplot=0, title="3d",
              view={"xlim": (-3, 3), "ylim": (-3, 3)})
p.draw(show=False)
try:
    p.animate(frames=3, update_func=lambda ax, f: None)
    check("三维缺少 zlim 时抛 ValueError", False)
except ValueError as exc:
    check("三维缺少 zlim 时抛 ValueError", "zlim" in str(exc))
plt.close("all")

# ======================================================================
# 3. 固定范围后可以正常动画（reset 模式）
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, title="reset",
           xlabel="x", ylabel="y",
           view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
p.draw(show=False)
anim = p.animate(
    frames=12,
    interval=40,
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 4), lw=2),
    update_mode="reset",
)
check("reset 模式返回 FuncAnimation", anim is not None)
check("动画参数可读回", p.get_animation_params()["frames_count"] == 12)
fig, animation = p.draw(show=False) if False else (None, None)
# 保存 GIF
p.animate(
    frames=12,
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 4), lw=2),
    save=True,
    save_path=os.path.join(OUT, "reset.gif"),
    fps=15,
)
check("保存 GIF", os.path.isfile(os.path.join(OUT, "reset.gif")))
check("返回的动画对象可获取", p.get_animation() is not None)
p.stop_animation()
check("stop_animation 之后动画为空", p.get_animation() is None)
plt.close("all")

# ======================================================================
# 4. 保存 MP4（ffmpeg）
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
p.draw(show=False)
p.animate(
    frames=10,
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 3), lw=2),
    save=True,
    save_path=os.path.join(OUT, "clip.mp4"),
    fps=10,
)
check("保存 MP4", os.path.isfile(os.path.join(OUT, "clip.mp4")))
plt.close("all")

# ======================================================================
# 5. 不带扩展名 -> 自动补 .gif；save=True -> 默认目录
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 6.3), "ylim": (-1.5, 1.5)})
p.draw(show=False)
p.animate(
    frames=6,
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 2)),
    save_path=os.path.join(OUT, "no_ext"),
)
check("无扩展名自动补 .gif", os.path.isfile(os.path.join(OUT, "no_ext.gif")))
plt.close("all")

p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 6.3), "ylim": (-1.5, 1.5)})
p.draw(show=False)
p.animate(
    frames=6,
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 2)),
    save=True,
    save_path_name=os.path.join(OUT, "save-true"),
)
check(
    "save=True 保存到指定目录",
    os.path.isfile(os.path.join(
        OUT, "save-true", "MultiPlotter_animation.gif"
    )),
)
plt.close("all")

# ======================================================================
# 6. artists 模式：原地更新 + blit
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
p.draw(show=False)
ax = p.get_axes(0)
line = ax.lines[0]


def update_artists(f, ln=line):
    ln.set_data(x, np.sin(x - f / 4))
    return ln,


p.animate(frames=8, update_func=update_artists, update_mode="artists", blit=True)
check("artists 模式可运行", p.get_animation() is not None)
p.animate(frames=8, update_func=update_artists, update_mode="artists",
          blit=True, save_path=os.path.join(OUT, "artists.gif"), fps=10)
check("artists 模式可保存", os.path.isfile(os.path.join(OUT, "artists.gif")))
plt.close("all")

# ======================================================================
# 7. frame_data 字典：帧号来自键
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 2 * np.pi), "ylim": (-1.5, 1.5)})
p.draw(show=False)
frames_dict = {k: np.sin(x - k / 5) for k in range(10)}
seen = []


def update_data(ax, y):
    seen.append(float(np.round(np.asarray(y, dtype=float)[0], 6)))
    ax.plot(x, y, lw=2)
    return ax,


p.animate(frames=None, frame_data=frames_dict, update_func=update_data)
params = p.get_animation_params()
check("frame_data 存入参数", params["frame_data"] is frames_dict)
p.animate(frames=None, frame_data=frames_dict, update_func=update_data,
          save_path=os.path.join(OUT, "frame_data.gif"), fps=8)
check("frame_data 可保存", os.path.isfile(os.path.join(OUT, "frame_data.gif")))
check("frame_data 每帧都回调了", len(seen) == 10, f"回调 {len(seen)} 次")

# frames 与 frame_data 键不一致时要给出明确提示
try:
    p.animate(frames=30, frame_data=frames_dict, update_func=update_data)
    check("frames 与 frame_data 不一致时报错", False)
except ValueError as exc:
    check("frames 与 frame_data 不一致时报错", "frame_data" in str(exc))
except Exception as exc:
    check("frames 与 frame_data 不一致时报错", False,
          f"-> 抛出 {type(exc).__name__}: {str(exc)[:60]}")

# frames 写具体的键列表时应该可用
p.animate(frames=list(frames_dict.keys())[:4], frame_data=frames_dict,
          update_func=update_data)
check("frames 与 frame_data 键一致时可用", True)
plt.close("all")

# ======================================================================
# 8. 多子图 + xlim/ylim 分轴指定
# ======================================================================
p = AnimationPlotter(ncols=2, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, title="a")
p.add_plot(kind="line", x=x, y=np.cos(x), subplot=1, title="b")
p.draw(show=False)
try:
    p.animate(frames=4, update_func=lambda ax, f: None)
    check("多子图未固定范围时报错", False)
except ValueError as exc:
    check("多子图未固定范围时报错", "subplot=0" in str(exc) and "subplot=1" in str(exc))
plt.close("all")

p = AnimationPlotter(ncols=2, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0, title="a")
p.add_plot(kind="line", x=x, y=np.cos(x), subplot=1, title="b")
p.draw(show=False)
p.animate(
    frames=6,
    subplots=[0, 1],
    xlim=(0, 2 * np.pi),
    ylim=(-1.5, 1.5),
    update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 3)),
    save_path=os.path.join(OUT, "multi.mp4"),
    fps=8,
)
check("多子图统一范围可保存", os.path.isfile(os.path.join(OUT, "multi.mp4")))
plt.close("all")

# ======================================================================
# 9. allow_auto_limits=True 兜底
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0)
p.draw(show=False)
before = p.get_axes(0).get_xlim()
p.animate(frames=5, allow_auto_limits=True,
          update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 2)))
after = p.get_axes(0).get_xlim()
check("allow_auto_limits 不报错且范围不变", np.allclose(before, after),
      f"{before} -> {after}")
plt.close("all")

# ======================================================================
# 10. 3D 动画：自动关闭 blit
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 4), dpi=60)
p.add_surface(X, Y, Z, subplot=0,
              view={"xlim": (-3, 3), "ylim": (-3, 3), "zlim": (-1, 1),
                    "elev": 30, "azim": -60})
p.draw(show=False)


def update_3d(ax, f):
    ax.clear()
    ax.plot_surface(X, Y, Z * np.sin(f / 5), cmap="turbo", edgecolor="none")
    ax.set_zlim(-1, 1)
    return ax,


p.animate(frames=6, blit=True, update_func=update_3d,
          save_path=os.path.join(OUT, "surface.gif"), fps=8)
check("3D 动画自动 blit=False", p.get_animation_params()["blit"] is False)
check("3D 动画可保存", os.path.isfile(os.path.join(OUT, "surface.gif")))
plt.close("all")

# ======================================================================
# 11. 参数错误处理
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 6.3), "ylim": (-1.5, 1.5)})
try:
    p.animate(frames=3)
    check("draw() 之前 animate 应报错", False)
except RuntimeError as exc:
    check("draw() 之前 animate 应报错", "draw()" in str(exc))

p.draw(show=False)
for name, kwargs, exc_type in (
    ("非法 update_mode", {"update_mode": "xxx"}, ValueError),
    ("frames 为负", {"frames": -1}, ValueError),
    ("不存在的 subplot", {"subplots": 9}, KeyError),
    ("无限动画无法保存", {"frames": None, "save": True}, ValueError),
    ("非法 writer 字符串", {"writer": "nope",
                            "save_path": os.path.join(OUT, "bad.gif")}, ValueError),
):
    try:
        p.animate(update_func=lambda ax, f: None, **kwargs)
        check(name, False)
    except exc_type as exc:
        check(name, True, f"-> {type(exc).__name__}")
    except Exception as exc:
        check(name, False, f"-> 抛出 {type(exc).__name__}: {str(exc)[:60]}")
plt.close("all")

# ======================================================================
# 12. 保存 HTML
# ======================================================================
p = AnimationPlotter(ncols=1, figsize_per_plot=(5, 3), dpi=60)
p.add_plot(kind="line", x=x, y=np.sin(x), subplot=0,
           view={"xlim": (0, 6.3), "ylim": (-1.5, 1.5)})
p.draw(show=False)
p.animate(frames=5, update_func=lambda ax, f: ax.plot(x, np.sin(x - f / 2)),
          save_path=os.path.join(OUT, "page.html"), fps=8)
check("保存 HTML", os.path.isfile(os.path.join(OUT, "page.html")))
plt.close("all")

print()
print(f"通过 {ok} 项，失败 {fail} 项")
if fail:
    sys.exit(1)
