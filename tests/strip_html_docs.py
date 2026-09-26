# -*- coding: utf-8 -*-
"""生成一份「不依赖任何 HTML」的文档副本。

适用场景：某些 Markdown 预览器会过滤 / 不渲染 HTML，
此时 `<details>` 折叠用不了、`<h2 id="...">` 也不生效。
这份副本把折叠块展开成普通小标题、把手写 id 的 HTML 标题换成标准
Markdown 标题，图片路径保持不变。

拆分文档后，只有 **API.md** 还用到 HTML（开篇对比与几个示例的三处折叠块），
其余文档已经是纯 Markdown。脚本会扫描全部文档，只处理真正含 HTML 的那些。

用法：

    python tests/strip_html_docs.py

生成：``tests/nohtml/<原文件名>``，例如 ``tests/nohtml/API.md``。
"""

import io
import os
import re

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)                                  # 包根目录（tests 的上一层）
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(TESTS_DIR, "nohtml")

#: 需要处理的文档（相对包根目录）。
DOCS = [
    "README.md",
    "API.md",
    "ANIMATION.md",
    "EXTENDING.md",
    "FAQ.md",
    os.path.join("examples", "README.md"),
]

HTML_PATTERN = re.compile(r"<details|</details|<summary|<style|<h[2-4]\s+id=")


def has_html(text):
    """判断文档里有没有需要处理的 HTML。"""

    return bool(HTML_PATTERN.search(text))


def strip_html(text):
    """把折叠块展开、把 HTML 标题转成 Markdown，返回处理后的文本。"""

    # 1) 去掉 <style> 块（现在没有，只是兜底）
    text = re.sub(r"<style>.*?</style>\n*", "", text, flags=re.S)

    # 2) 折叠块 -> 小标题 + 内容（保持内容不丢）
    def expand(match):
        label = match.group(1).strip()
        body = match.group(2).strip("\n")
        label = re.sub(r"^\[点击展开\]\s*", "", label)

        return f"**▼ {label}**\n\n{body}\n"

    text = re.sub(
        r"<details>\s*<summary>(.*?)</summary>(.*?)</details>",
        expand,
        text,
        flags=re.S,
    )

    # 3) 手写 id 的 HTML 标题 -> 标准 Markdown 标题
    def to_md_heading(match):
        level = match.group(1)
        inner = match.group(2).strip()

        return f"{'#' * int(level)} {inner}"

    text = re.sub(
        r"<h([2-4])\s+id=\"[^\"]*\">(.*?)</h\1>",
        to_md_heading,
        text,
        flags=re.S,
    )

    # 4) 说明文字里的转义实体还原成可读写法（只影响正文描述，不是真标签）
    text = text.replace("&lt;details&gt;", "details")

    # 5) 去掉只对折叠版有意义的说明段
    text = re.sub(
        r"> 下面这些代码块都可以\*\*点击标题展开 / 收起\*\*。\n"
        r"> 折叠用的是 HTML 原生的 details 标签[^\n]*\n"
        r"> 都支持[^\n]*\n\n",
        "> 下面这些代码块在本版本里已经全部展开。\n\n",
        text,
    )

    return text


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)

    processed = 0
    skipped = []

    for name in DOCS:
        source = os.path.join(BASE_DIR, name)

        if not os.path.isfile(source):
            skipped.append((name, "文件不存在"))
            continue

        text = io.open(source, encoding="utf-8").read()

        if not has_html(text):
            skipped.append((name, "没有 HTML，跳过"))
            continue

        stripped = strip_html(text)

        header = (
            "<!-- 由 tests/strip_html_docs.py 从 "
            f"{name.replace(os.sep, '/')} 生成，"
            "内容相同但没有 HTML，折叠块已展开。 -->\n\n"
            "> 这是 **不含 HTML 的版本**：所有折叠代码块都已展开成小标题，\n"
            "> 便于在过滤 HTML 的 Markdown 预览器里阅读。\n"
            f"> 带折叠效果的版本请看 [{name.replace(os.sep, '/')}]"
            f"(../../{name.replace(os.sep, '/')})。\n\n"
        )

        # 副本放在 tests/nohtml/ 下，图片相对路径要多退两级
        stripped = re.sub(
            r"\]\(tests/images/", "](../../tests/images/", stripped
        )

        target = os.path.join(TARGET_DIR, os.path.basename(name))

        io.open(target, "w", encoding="utf-8").write(header + stripped)

        leftover = len(HTML_PATTERN.findall(stripped))

        print(
            f"[ok] {name} -> {os.path.relpath(target, BASE_DIR)}"
            f"（残留 HTML 标签 {leftover}）"
        )

        processed += 1

    for name, reason in skipped:
        print(f"[skip] {name}：{reason}")

    print(f"\n处理 {processed} 份文档，跳过 {len(skipped)} 份。")


if __name__ == "__main__":
    main()
