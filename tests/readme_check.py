# -*- coding: utf-8 -*-
"""文档交付前最后校验：图片/动图路径、锚点、章节编号、代码块、表格、跨文件链接。

重构后文档拆成了多份（README / API / ANIMATION / EXTENDING / FAQ /
examples/README），本脚本把这几份**一起**校验：

* 图片引用能否解析（统一相对**包根目录**，即 ``tests/images/xxx.png``）；
* 站内锚点 ``](#xxx)`` 在**同一个文件内**是否存在；
* 跨文件锚点 ``](API.md#xxx)`` 在目标文件里是否存在；
* 相对文件链接 ``](examples/)`` 是否存在；
* 代码围栏 ``~~~`` 是否成对；
* Markdown 表格列数是否一致；
* 章节编号是否连续（只对保留 ``## N.`` 编号的 API.md 强制）。

用法::

    python tests/readme_check.py
"""

import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

#: 要校验的文档（相对包根目录）。
DOCS = [
    "README.md",
    "API.md",
    "ANIMATION.md",
    "EXTENDING.md",
    "FAQ.md",
    os.path.join("examples", "README.md"),
]

#: 只有这份文档保留了 ``## N.`` 章节编号，需要检查连续性。
NUMBERED_DOC = "API.md"

#: 编号有意空出来的章节（内容已经移到别的文档）。
#:
#: 第 25 章「动画：AnimationPlotter」整体移到了 ANIMATION.md，
#: 编号沿用拆分前的 README，方便老读者按原编号跳转。
SKIPPED_CHAPTERS = frozenset({25})

problems = []


def slug(title):
    """把标题转成 GitHub 风格的锚点。"""

    text = title.strip().lower()
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)

    return text.replace(" ", "-")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def collect_anchors(text):
    """收集一份文档里所有可被链接的锚点。"""

    anchors = {slug(title) for title in re.findall(r"^#{1,6} (.+)$", text, re.M)}

    # 手写 id 的 HTML 标题，例如 <h2 id="0-开篇与普通-matplotlib-的完整对比">
    anchors |= set(re.findall(r"<h[1-6]\s+id=\"([^\"]+)\"", text))

    return anchors


# ----------------------------------------------------------------------
# 1. 先读一遍所有文档，建立锚点索引
# ----------------------------------------------------------------------

texts = {}

for doc in DOCS:
    path = os.path.join(BASE_DIR, doc)

    if not os.path.isfile(path):
        problems.append(f"文档不存在: {doc}")
        continue

    texts[doc] = read(path)

anchors_by_doc = {doc: collect_anchors(text) for doc, text in texts.items()}

print(f"校验 {len(texts)} 份文档\n")

# ----------------------------------------------------------------------
# 2. 逐份检查
# ----------------------------------------------------------------------

all_images = set()
total_images = 0
total_links = 0

for doc, text in texts.items():
    doc_dir = os.path.dirname(os.path.join(BASE_DIR, doc))

    # ---- 图片 / 动图引用 ----
    refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    total_images += len(refs)

    for ref in refs:
        if ref.startswith(("http://", "https://")):
            continue

        # 图片统一相对包根目录解析（见 examples/README.md 的说明）
        if not os.path.isfile(os.path.join(BASE_DIR, ref)):
            problems.append(f"{doc}: 图片缺失 {ref}")

        if ref.startswith("tests/images/"):
            all_images.add(os.path.basename(ref))

    # ---- 站内锚点 ----
    links = re.findall(r"\]\(#([^)]+)\)", text)
    total_links += len(links)

    for anchor in sorted(set(links)):
        if anchor not in anchors_by_doc[doc]:
            problems.append(f"{doc}: 断链锚点 #{anchor}")

    # ---- 跨文件链接（含锚点） ----
    for target, anchor in re.findall(r"\]\(([^)#\s]+\.md)#([^)]+)\)", text):
        target = target.replace("\\", "/")

        # 相对当前文档解析
        resolved = os.path.normpath(
            os.path.join(doc_dir, target)
        ).replace("\\", "/")
        relative = os.path.relpath(resolved, BASE_DIR).replace("\\", "/")

        if relative not in anchors_by_doc:
            problems.append(f"{doc}: 链接到不存在的文档 {target}")
            continue

        if anchor not in anchors_by_doc[relative]:
            problems.append(
                f"{doc}: {target} 里没有锚点 #{anchor}"
            )

    # ---- 相对文件/目录链接 ----
    for target in re.findall(r"\]\((?!#|https?:)([^)#\s]+)\)", text):
        if target.endswith(".md") or target.endswith((".png", ".gif")):
            continue

        candidate = os.path.normpath(os.path.join(doc_dir, target))

        if not os.path.exists(candidate):
            problems.append(f"{doc}: 链接指向不存在的路径 {target}")

    # ---- 代码围栏 ----
    if text.count("~~~") % 2 != 0:
        problems.append(f"{doc}: ~~~ 代码块没有成对闭合")

    if text.count("```") % 2 != 0:
        problems.append(f"{doc}: ``` 代码块没有成对闭合")

    # ---- 折叠块 ----
    details_open = len(re.findall(r"<details", text))
    details_close = len(re.findall(r"</details>", text))
    summary = len(re.findall(r"<summary>", text))

    if details_open != details_close:
        problems.append(f"{doc}: <details> 与 </details> 数量不一致")

    if summary != details_open:
        problems.append(f"{doc}: <summary> 数量与 <details> 不一致")

    if "<style>" in text:
        problems.append(f"{doc}: 不要用 <style>，原生 <details> 更稳")

    for index, label in enumerate(
        re.findall(r"<summary>(.*?)</summary>", text), 1
    ):
        if "点击展开" not in label:
            problems.append(
                f"{doc}: 第 {index} 个 <summary> 缺少「[点击展开]」提示"
            )

    for index, block in enumerate(
        re.findall(r"<details.*?</details>", text, flags=re.S), 1
    ):
        if block.count("~~~") % 2 != 0:
            problems.append(f"{doc}: 第 {index} 个 <details> 里的 ~~~ 没有成对")

    # ---- 表格列数 ----
    lines = text.splitlines()

    for line_number, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue

        if line_number + 1 >= len(lines):
            continue

        separator = lines[line_number + 1]

        if not set(separator.replace("|", "").replace(" ", "")) <= set("-:"):
            continue

        columns = line.count("|")
        cursor = line_number + 1

        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            if lines[cursor].count("|") != columns:
                problems.append(
                    f"{doc}: 第 {cursor + 1} 行表格列数不一致"
                )
            cursor += 1

    # ---- 章节编号（只对保留编号的文档） ----
    if doc == NUMBERED_DOC:
        numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", text, re.M)]

        # 第 25 章（动画）已经移到 ANIMATION.md，
        # 编号沿用拆分前的 README，所以允许有意的空档。
        expected = [
            n for n in range(1, max(numbers) + 1) if n not in SKIPPED_CHAPTERS
        ]

        if numbers != expected:
            problems.append(
                f"{doc}: 章节编号不连续 {numbers}（期望 {expected}）"
            )

        missing = sorted(set(SKIPPED_CHAPTERS) - {25})
        if missing:
            problems.append(f"{doc}: SKIPPED_CHAPTERS 里有未使用的编号 {missing}")

        print(f"  {doc}: {len(numbers)} 章（第 {sorted(SKIPPED_CHAPTERS)} 章在其它文档）")

    # ---- 文件规模提醒（README 应保持精简） ----
    size = len(text)

    print(f"  {doc}: {size} 字符，{total_images and len(refs)} 图片引用")

    if doc == "README.md" and size > 40000:
        problems.append(
            f"README.md 过长（{size} 字符），详细内容请放到 API.md"
        )

# ----------------------------------------------------------------------
# 3. 图片资产核对
# ----------------------------------------------------------------------

print(f"\n图片引用共 {total_images} 处，站内锚点 {total_links} 处")

if os.path.isdir(IMAGES_DIR):
    on_disk = {
        name for name in os.listdir(IMAGES_DIR)
        if name.endswith((".png", ".gif"))
    }
    unused = sorted(on_disk - all_images)

    if unused:
        print(f"磁盘上有但文档没引用（{len(unused)} 个）: {unused}")

    gifs = sorted(name for name in all_images if name.endswith(".gif"))

    for name in gifs:
        path = os.path.join(IMAGES_DIR, name)

        if not os.path.isfile(path):
            continue

        size = os.path.getsize(path)
        print(f"  - {name}: {size / 1024:.0f} KB")

        if size > 3 * 1024 * 1024:
            problems.append(f"{name} 体积过大（{size / 1024 / 1024:.1f} MB）")

print()

if problems:
    print("发现问题：")

    for item in problems:
        print(" -", item)

    sys.exit(1)

print("文档校验通过")
