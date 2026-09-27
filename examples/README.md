# 示例与图片

本目录存放**可直接运行**的示例脚本，以及文档中所有图片 / 动图的说明。

## 1. 运行示例

在**包根目录**执行（脚本内部已经把包根目录加入 `sys.path`）：

~~~bash
python examples/01_quickstart.py                    # 二维 / 三维 / 混排 / save_path
python examples/02_convective_heat_transfer.py      # 对流传热算例（见 README 第 5 章）
python examples/03_animation.py                     # 正弦波、傅里叶方波动画
python examples/04_custom_layer.py                  # 扩展开发：注册新的 step 图层
python examples/05_science_composition.py           # ScienceResult + SciencePlotter
~~~

所有脚本都默认不弹窗，直接保存到 `examples/output/`。

| 脚本 | 对应文档 |
| --- | --- |
| `01_quickstart.py` | [README 第 2、3 章](../README.md)、[API 第 5、12 章](../API.md) |
| `02_convective_heat_transfer.py` | [README 第 5 章](../README.md#5-科研算例对流传热) |
| `03_animation.py` | [ANIMATION.md](../ANIMATION.md) |
| `04_custom_layer.py` | [EXTENDING.md 第 5 章](../EXTENDING.md#5-完整实战新增一个-step-图层) |
| `05_science_composition.py` | [API 附录 A](../API.md#附录-a-科研组合接口实验性-api) |

## 2. 图片与动图路径说明

文档引用的示例图片统一保存在 `tests/images/` 子目录中。
**文件名按文档中的出现顺序编号**（`01_` 是正文里第一张图，依次递增到 `31_`），
后面的英文名保留原来的含义，方便对照。

本包目录结构：

~~~text
MultiPlotter/
├── README.md                       # 快速开始
├── API.md                          # 所有方法与参数
├── ANIMATION.md                    # 动画
├── EXTENDING.md                    # 扩展开发与包结构
├── FAQ.md                          # 常见问题
├── pyproject.toml                  # 依赖与打包配置
├── requirements.txt                # 运行依赖
├── Multiplotter.py                 # 兼容入口（转发到 multiplotter 包）
├── multiplotter/                   # 包实现（见 EXTENDING.md 第 1 章）
├── examples/
│   ├── README.md                   # 本文件
│   ├── 01_quickstart.py
│   ├── 02_convective_heat_transfer.py
│   ├── 03_animation.py
│   ├── 04_custom_layer.py
│   ├── 05_science_composition.py
│   └── output/                     # 示例输出（运行后生成）
└── tests/
    ├── images/                     # 文档引用的全部图片与动图
    ├── nohtml/                     # strip_html_docs.py 生成的无 HTML 副本
    ├── %TEMP%/multiplotter-tests/  # 测试与生成脚本的附加输出
    ├── generate_examples.py              # 生成静态示例图片
    ├── generate_animation_examples.py    # 生成动画示例动图
    ├── generate_compare_examples.py      # 生成开篇对比章节的图与动图
    ├── generate_field_examples.py        # 生成矢量场 / 张量场 / 表格的图与动图
    ├── extend_example.py                 # 扩展开发示例（新增 step / trisurf）
    ├── renumber_images.py                # 给图片分配/同步顺序编号（稳定编号）
    ├── strip_html_docs.py                # 生成不含 HTML 的文档副本
    ├── readme_check.py                   # 校验全部文档的路径 / 锚点 / 表格
    ├── defaults_snapshot.json            # 默认值快照（defaults_test.py 用）
    ├── contract_baseline.json            # 绘图契约基线（contract_test.py 用）
    ├── library_smoke_test.py             # 全部 add_* 示例的冒烟测试
    ├── field_table_test.py               # 矢量场与表格的测试
    ├── init_test.py                      # init() / PlotBuilder 的测试
    ├── extension_test.py                 # 扩展开发测试
    ├── anim_api_test.py                  # AnimationPlotter 测试
    ├── compat_test.py                    # Matplotlib 版本兼容层测试
    ├── font_test.py                      # 字体挑选（中文/西文、各平台）
    ├── defaults_test.py                  # 图层契约、预设可达性、默认值快照
    └── contract_test.py                  # 绘图契约回归（18 个场景）
~~~

`tests/images/` 下的图片：

~~~text
01_compare_matplotlib.png               # README/API：普通 matplotlib 四联图
02_compare_multiplotter.png             # README/API：MultiPlotter 四联图
03_compare_animated.gif                 # README/API：AnimationPlotter 动画
04_init_quickstart.png                  # API 第 3 章：init() 快速绘图
05_multiplotter_2d_examples.png         # README 第 2 章 / API 第 5 章：二维基础图层总览
06_bar_values_example.png               # API 第 6 章：柱状图柱顶数值
07_hist_values_example.png              # API 第 7 章：直方图柱顶数值
08_pie_example.png                      # API 第 8 章：二维饼图
09_correlation_heatmap_example.png      # API 第 9 章：相关性矩阵热力图
10_contour_example.png                  # API 第 11 章：二维等高线
11_surface_example.png                  # README 第 3 章 / API 第 12 章：三维曲面
12_line3d_example.png                   # API 第 13 章：三维曲线
13_scatter3d_example.png                # API 第 14 章：三维散点
14_gradient_descent_mixed_3d.png        # API 第 13 章：三维混排 surface + line3d
15_hist3d_example.png                   # API 第 16 章：三维直方图
16_bar3d_values_example.png             # API 第 17 章：三维柱状图选择性标注
17_hist3d_values_example.png            # API 第 17 章：三维直方图选择性标注
18_mixed_layers_2d_example.png          # API 第 18 章：二维混排 scatter + line
19_vector_2d_example.png                # API 第 19 章：二维矢量场（箭头 + 流线）
20_tensor_field_example.png             # API 第 19 章：二维有限元张量场
21_vector_3d_example.png                # API 第 19 章：三维矢量场（箭头 + RK4 流线）
22_vector_2d_animated.gif               # API 第 19 章：二维矢量场动画
23_vector_3d_animated.gif               # API 第 19 章：三维矢量场动画
24_table_example.png                    # API 第 20 章：二维表格
25_save_path_example.png                # API 第 24 章：draw(save_path=...)
26_animation_sine.gif                   # README 第 4 章 / ANIMATION.md：简单示例动图
27_animation_sine_preview.png           # ANIMATION.md：简单示例末帧预览
28_animation_fourier.gif                # ANIMATION.md：傅里叶方波动图
29_animation_fourier_preview.png        # ANIMATION.md：傅里叶方波末帧预览
30_multiplotter_example_output.png      # API 第 26 章：完整示例输出
31_multiplotter_3d_examples.png         # API 第 27 章：三维图层总览
~~~

根目录文档（README / API / ANIMATION / FAQ）中的图片和动图都使用相对路径
`tests/images/01_xxx.png`、`tests/images/22_xxx.gif`，**相对包根目录解析**。
请保持文档与 `tests/images/` 的相对位置不变，Markdown 中的图片就会正常显示。

想重新编号时执行：

~~~bash
python tests/renumber_images.py            # 预演
python tests/renumber_images.py --apply    # 执行
~~~

它会按当时的出现顺序重排文件名，并同步更新文档与各生成脚本里的引用。

## 3. 关于动图

GitHub、VS Code、Typora 都能直接播放 GIF；`.mp4` 在 Markdown 里通常只能下载后播放，
所以文档中的动图统一使用 GIF。GIF 体积敏感，生成时用了
`dpi=75`、`fps=20`、`frames=48`（正弦波）和 `dpi=75`、`fps=5`、`frames=20`（方波）这一档，
两张动图都在 250 KB 以内。
