# 常见问题（FAQ）

按「报错信息 / 现象」组织，每条都给出原因和可直接复制的改法。

相关文档：

- 方法与参数：[API.md](API.md)
- 动画：[ANIMATION.md](ANIMATION.md)
- 扩展开发：[EXTENDING.md](EXTENDING.md)
- 安装、依赖与中文字体：[README.md](README.md)
- 示例脚本：[`examples/`](examples/)

### z 的形状不匹配

当：

~~~text
x.shape == (100,)
y.shape == (80,)
~~~

必须满足：

~~~text
z.shape == (80, 100)
~~~

也就是：

~~~text
z.shape == (len(y), len(x))
~~~

### 二维、三维图层放在同一个子图

会直接抛出 `ValueError`，并列出冲突的图层。请把二维和三维图层分到不同的 subplot：

~~~text
subplot=0：surface + line3d + scatter3d
subplot=1：contour + line + scatter
~~~

### 三维柱顶文字糊成一团

把 `value_selection` 从 `"all"` 改成 `"auto"`（默认值），并调小 `max_value_labels`；
或者用 `"threshold"` 只标注重要柱子。详见[第 17 节](API.md#17-选择性数值标注)。

### 等高线覆盖轨迹

先调用 `add_contour()`，再调用 `add_plot(kind="line")` 和 `add_plot(kind="scatter")`。
必要时给轨迹设置更大的 `zorder`。

### 图例遮挡图像

使用 `bbox_to_anchor` 将图例移到坐标轴外，并适当增大 `figsize_per_plot`。

### 曲面起伏不明显

启用光照增强，并提高 `vert_exag`：

~~~python
light_enhance={
    "gamma": 0.55,
    "vert_exag": 2.5,
    "azdeg": 315,
    "altdeg": 55,
}
~~~

### 找不到图片或图片显示不出来

- 确认当前工作目录就是包含 `README.md` 的目录；
- 确认 `images/` 目录存在且文件名与 README 中一致（可用 `python tests/generate_examples.py`
  重新生成静态图，用 `python tests/generate_animation_examples.py` 重新生成动图）；
- Markdown 预览器需要支持相对路径图片，GitHub、VS Code、Typora 等都可以正常显示。

### 动图不动 / 显示成静态图

- 确认引用的是 `.gif` 而不是 `_preview.png`（预览图本来就只有一帧）；
- 部分 Markdown 预览器不播放 GIF，用浏览器打开 README 或推到 GitHub 上查看；
- 用 `python tests/generate_animation_examples.py` 重新生成一次动图。

### 折叠块点不开 / 显示成原始标签

折叠用的是 HTML 原生的 `&lt;details&gt;`，**故意没有用任何自定义 CSS**
（`&lt;style&gt;` + `class` + `::-webkit-details-marker` 这类写法在 VS Code、Typora、
Obsidian 的不同内核下表现不一致，容易让标题看起来点不动）。

按顺序排查：

1. **确认标题前面有三角符号**：`▶ [点击展开] 初始化设置对比`。
   有三角就能点；如果只剩一行粗体文字，说明预览器把 `&lt;summary&gt;` 过滤掉了。
2. **确认打开的是 Markdown 预览，不是源码**：
   VS Code 按 `Ctrl+Shift+V`，或右上角「打开预览」；直接看 `.md` 源码当然不能折叠。
3. **换浏览器内核试**：VS Code 预览基于 Electron，一般没问题；
   如果是某个插件提供的预览，试着用 VS Code 自带预览打开。
4. **都不行就用无 HTML 版本**：

   ~~~bash
   python tests/strip_html_docs.py       # 生成 tests/nohtml/API.md
   ~~~

   拆分文档后，只有 **API.md** 还用到了 HTML（开篇对比那几处折叠块），
   其余文档已经是纯 Markdown。这份副本把折叠块展开成普通小标题、
   把 HTML 标题换成标准 Markdown 标题，内容和图片完全一样，
   在任何预览器里都能正常显示。

### 动画报“必须固定坐标轴范围”

见[第 25.2 节](ANIMATION.md#252-坐标轴范围必须固定)。

### 保存动图时报缺少 ffmpeg / Pillow

~~~bash
pip install pillow        # 保存 .gif 需要
# 保存 .mp4 / .html 需要 ffmpeg，装好后确认在 PATH 里
ffmpeg -version
~~~

matplotlib 找不到 ffmpeg 时可以手动指定：

~~~python
import matplotlib.pyplot as plt

plt.rcParams["animation.ffmpeg_path"] = r"D:\Program Files\ffmpeg\bin\ffmpeg.EXE"
~~~

### 中文显示成方框

见 [README.md 的「字体」一节](README.md#字体)。主题会自动跳过系统中不存在的字体；
Linux 上装 `fonts-noto-cjk` 即可（README 里有各发行版的命令）。

### `**kwargs` 里写的参数没生效

先看是否出现这样的标准警告：

~~~text
kind=line 忽略了不适用的参数：['cell_fontsize']。
~~~

这说明该键既不在目标方法的签名里，也不在透传白名单里，已经被丢弃。

排查顺序：

1. **确认它属于哪一层**。`view`、`legend`、`show_values`、`colorbar`、
   `light_enhance` 是框架参数，不会透传给 Matplotlib；
   而 `color`、`linewidth`、`alpha`、`cmap`、`zorder` 会。
2. **确认目标方法真的支持它**。例如 `heatmap_text_size` 是框架参数，
   而 `interpolation` 是 `Axes.imshow()` 的参数。
3. **确实需要透传就登记白名单，或者使用 `mpl_kwargs`**：

   ~~~python
   session.add("line", {"x": x, "y": y}, mpl_kwargs={"picker": 5})
   ~~~

   需要让这类错误直接失败时：

   ~~~python
   session = MultiPlotter.init(ncols=1, strict=True)
   ~~~

   登记白名单的写法仍然是：

   ~~~python
   from multiplotter import MultiPlotter

   MultiPlotter.PASSTHROUGH_BY_KIND = dict(MultiPlotter.PASSTHROUGH_BY_KIND)
   MultiPlotter.PASSTHROUGH_BY_KIND["line"] = {"drawstyle", "my_custom_key"}
   ~~~

4. **查一下被丢弃的键**：

   ~~~python
   session = MultiPlotter.init(ncols=1, cmap="magma")
   session.add("table", data)
   print(session.get_dropped_keys())
   # {'table': ['cmap']}  -> 表格用不到 cmap
   ~~~

### 全局 `plt.rcParams` 被改掉了

重构后 `draw()` **默认不再修改全局 rcParams**，主题通过
`matplotlib.rc_context()` 临时生效，画完自动恢复：

~~~python
import matplotlib.pyplot as plt

plt.rcParams["axes.titlesize"] = 30     # 用户自己的设置
plotter.draw(show=False)
print(plt.rcParams["axes.titlesize"])   # 仍然是 30
~~~

如果确实想沿用旧行为（直接写全局 rcParams），显式选择：

~~~python
plotter.draw(show=False, style_scope="global")
~~~

细节见 [EXTENDING.md 的样式作用域一节](EXTENDING.md#132-样式作用域context-与-global)。

### 重复 `draw()` 之后 Figure 越积越多

`draw()` 不会自动关闭上一次的 Figure（与旧行为一致）。需要回收时：

~~~python
plotter.draw(show=False, close_previous=True)   # 出图前先关掉上一次的
plotter.close()                                 # 手动关闭当前画布
plotter.clear(close_figures=True)               # 清空配置并关闭画布
with MultiPlotter(ncols=2) as plotter:          # 离开 with 时自动 close()
    ...
~~~
