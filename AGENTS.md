# AGENTS.md

面向 agent 的 TexCanvas 使用指南。本文以「让 agent 用 TexCanvas 生成 .pptx」为第一目标；代码维护部分压缩在末尾，需要扩展时再读。

TexCanvas 是一个 YAML → 可编辑 PPTX 生成器：把结构化的 YAML deck 描述编译成普通 OOXML `.pptx`，保留 Beamer 风格的导航/标题/页脚，输出可在 WPS / PowerPoint 中继续微调。不渲染整页图片，每个形状和文字都可编辑。

---

## 1. 如何调用

### 推荐工作流：init 脚手架 → 编辑 YAML → build

```bash
texcanvas init my-talk        # 在当前目录创建 my-talk/ 脚手架
cd my-talk
bash build.sh                 # 生成 output/deck.pptx（build.sh 自动定位包内模板）
```

脚手架生成：`AGENTS.md`（精简版）、`deck.yml`（最小可跑：title + section_divider + content 三页）、`assets/`（放图片）、`build.sh`（wrapper）、`output/`、`.gitignore`。agent 只需编辑 `deck.yml` 然后跑 `build.sh`。

### CLI（子命令结构）

```bash
texcanvas build <input.yml> -o <output.pptx> [选项]   # 从 YAML 生成 pptx
texcanvas init <name> [-d <dir>]                      # 创建脚手架
python -m texcanvas build <input.yml> -o <output.pptx> # 等价模块入口
```

`build` 参数：

| 参数 | 必填 | 说明 |
|------|------|------|
| `input` | 是 | YAML deck 描述文件路径 |
| `-o, --output` | 是 | 输出 .pptx 路径；父目录不存在会自动创建 |
| `-t, --template` | 否 | 可编辑 PPTX 模板；不传时用随包 `beamer-academic.pptx`（母版已烘焙背景），传则保留母版/主题、清空示例页 |
| `--asset-root` | 否 | 相对图片路径基准目录；默认为 YAML 文件所在目录 |
| `--strict` | 否（默认） | 图片缺失/损坏/格式不支持时立即失败 |
| `--no-strict` | 否 | 记录 warning 并在页面放入可编辑占位框后继续 |
| `--verbose` | 否 | 打印每条 warning 详情 |

成功时 stdout 打印摘要：

```
Built /abs/path/output.pptx
Slides: 13
Sections: 4
Warnings: 0
```

退出码：`0` 成功；`2` 失败（YAML 不可读 / schema 不合法 / 资源无效 / 渲染保存失败），错误信息打到 stderr，格式为 `Error: <location>: <reason>`。

### Python API

```python
from texcanvas import build, init_project, bundled_template_path

# 生成 pptx（不传 template 即用随包模板）
report = build(
    input="deck.yml",
    output="output/deck.pptx",
    strict=True,        # 默认
    asset_root=".",     # 默认 = input 的父目录
)
# report: BuildReport(output, slide_count, section_count, warnings)

# 在代码里创建脚手架
init_project(parent_dir, "my-talk")
```

异常基类 `TexCanvasError`（子类 `InputError` / `ValidationError` / `AssetError` / `RenderError`），捕获 `TexCanvasError` 即可覆盖所有失败情况。保存采用同目录临时文件 + 原子替换，失败不会留下半成品目标文件。

---

## 2. YAML 顶层结构

```yaml
metadata:
  title: 必填                    # deck 标题
  subtitle: ""                   # 可选
  author: ""
  institute: ""
  date: ""                       # 字符串，如 "2026-03-22"
  short_title: ""                # 可选，导航用短标题

aspect: "16:9"                   # 目前仅支持 "16:9"

sections:                        # 至少一个 section
  - id: background               # 可省略，默认由 short_title 生成 slug
    title: 研究背景              # 必填
    short_title: Background      # 可选，默认 = title
    slides: [...]                # 至少一张
```

**校验规则**：
- `metadata.title` 必填；`aspect` 必须是 `"16:9"`。
- 至少一个 section；每个 section 至少一张 slide；section `id` 全局唯一。
- `id` 省略时由 `short_title` slug 化（小写字母数字 + 连字符）；无法 slug 化的标题回退为 `section-1`、`section-2`……

---

## 3. 11 种 slide 版式

每张 slide 必填 `kind`。下表是**字段速查**，详细规则见后续小节。

| kind | 必填字段 | 常用可选字段 |
|------|----------|--------------|
| `title` | （无，从 metadata 回退） | `title`, `subtitle` |
| `section_divider` | （无） | `title`, `subtitle` |
| `content` | `body` 或 `bullets` 至少一项 | `title`, `body`, `bullets` |
| `two_columns` | `left` + `right`（都非空） | `title` |
| `image` | `image.path` | `image.fit`, `caption`, `title` |
| `code` | `code.source` | `code.lang`, `code.caption`, `title` |
| `table` | `table.header` 或 `table.rows` 至少一项 | `table.caption`, `title` |
| `equation` | `equation` | `title` |
| `block` | `block.body` 或 `block.bullets` | `block.style`, `block.title`, `title` |
| `conclusion` | `takeaway` 或 `bullets` | `takeaway`, `bullets`, `title` |
| `references` | `items`（非空） | `title` |

所有 slide 都可写 `title`（frame title，显示在顶部）、`notes`（保留在 IR，**当前版本尚未写入 PPTX 讲者备注**）、`citation`（可选页底灰色引用条，见 3.3）。

> **公式新能力**：`equation` 版式在系统装有 `pandoc` 时会把 LaTeX 转成原生 OMML 公式对象（支持矩阵/对齐/根号等完整结构），缺失时回退 Unicode 方案。详见 3.8。

### 3.1 `title` — 封面页

```yaml
- kind: title
  title: 科研训练汇报
  subtitle: A Beamer-style editable presentation
```

- 绘制主色满宽带 + accent 高亮条 + 大标题 + 副标题 + 署名行（`author · institute · date`）。
- **不绘制导航 / frame title / 页脚**（chrome 被抑制），但封面页**仍计入总页数**——第一张内容页页码显示 `02 / N`。
- `title` / `subtitle` 可省略，自动回退到 `metadata.title` / `metadata.subtitle`；署名行始终来自 `metadata`。
- 建议作为 deck 第一页。

### 3.2 `section_divider` — 章节分隔

```yaml
- kind: section_divider
  title: 研究背景
  subtitle: Motivation and research question
```

展示 section 编号、标题、可选副标题。通常作为每个 section 的第一张。

### 3.3 `content` — 正文 + bullets

```yaml
- kind: content
  title: 科学问题
  body: 本研究希望回答以下问题。
  bullets:
    - 现象为什么发生？
    - 哪些变量影响结果？
  citation: "[1] Doe et al., NeurIPS 2024."   # 可选：页底灰色引用条
  inline_image:                                # 可选：内联小图，文字环绕
    path: assets/fig.png
    width: 3.0       # 英寸
    align: right     # left | right
```

`body` 和 `bullets` 至少有一项。`citation` 在页底绘制一条灰色小字（9pt，`DSH_CITATION`），适合标注图表出处/引用。`inline_image` 把图片贴在内容区一侧，正文/ bullets 自动缩到剩余宽度形成环绕；`align: right` 图在右、文字在左，`align: left` 反之；仅支持 PNG/JPEG，路径规则同 `image` 版式（相对 `--asset-root`）。

### 3.4 `two_columns` — 双栏

```yaml
- kind: two_columns
  title: 实验设计
  left:
    heading: 实验组
    body: 处理条件说明
    bullets: [三个条件, 每组五重复]
  right:
    heading: 对照组
    bullets: [相同培养条件]
```

`left` 和 `right` 都必填且都**必须有内容**（`heading` / `body` / `bullets` 至少一项非空），否则校验失败。每栏支持 `heading`、`body`、`bullets`。

### 3.5 `image` — 图片

```yaml
- kind: image
  title: 实验流程
  image:
    path: assets/example-figure.png   # 相对路径基于 --asset-root
    fit: contain                       # contain(默认) | cover
  caption: 图 1：实验流程示意图
```

- `path` 必填；`fit` 默认 `contain`。
- 相对路径基准：`--asset-root`，未指定时为 YAML 文件所在目录。
- 支持格式：**PNG、JPEG**。SVG 不保证兼容，会被拒绝。
- `contain` 完整显示并允许留白；`cover` 中心裁剪（保持纵横比，不拉伸）。

### 3.6 `code` — 代码块

```yaml
- kind: code
  title: 训练入口
  code:
    lang: python
    source: |
      def train(model, data):
          loss = model.loss(data)
          loss.backward()
    caption: Listing 1
```

- `code.source` 必填（不能为空）。
- `code.lang` 可选，支持：**python / c / cpp / java / javascript / rust / go**；未识别时回退为通用 C 系高亮。
- 行内语法高亮：关键字 / 字符串 / 注释 / 数字不同颜色，全部为可编辑文本 run。
- 等宽字体 Menlo，直角面板。

### 3.7 `table` — 表格

```yaml
- kind: table
  title: 方法对比
  table:
    header: [方法, 准确率, 推理时间]
    rows:
      - [Baseline, "0.82", "12.4 ms"]
      - [Ours, "0.91", "8.1 ms"]
    caption: 表 1：指标对比
```

- `header` 或 `rows` 至少一项；`header` 为字符串列表，`rows` 为字符串列表的列表。
- 行可参差，缺列留空。
- 生成原生 PPTX 表格：表头主题色填充，奇数行斑马底色，单元格带细网格线。

### 3.8 `equation` — 公式（最小化 LaTeX）

```yaml
- kind: equation
  title: 损失函数
  equation: "L = -\\frac{1}{N}\\sum_{i=1}^{N} y_i \\log p_i"
```

> ⚠️ YAML 里反斜杠需转义：写 `\\frac`，或用 `equation: |` 块标量（推荐，反斜杠不用双写）。

**渲染方式**：当系统装有 `pandoc` 时，equation 文本被转成**原生 OMML 公式对象**（`<m:oMath>`），再放入 PowerPoint 要求的 `a14:m` 扩展容器，并用 `mc:AlternateContent` 包住公式形状；WPS/PowerPoint 中可双击编辑，支持完整的 LaTeX 数学结构。`pandoc` 不存在时回退到 Unicode 符号方案（覆盖面有限）。公式 run 的字体（Latin Helvetica / 东亚 苹方-简）会被显式写入 DrawingML `a:rPr`，不依赖主题数学字体。由于 PowerPoint 的公式形状使用 `AlternateContent`，`python-pptx` 重新读取时可能不会把该公式暴露在 `slide.shapes` 集合中，应直接检查最终 slide XML。

**pandoc 在场时支持**（原生 OMML）：
- 分数 `\frac{a}{b}`、上下标 `^{...}`/`_{...}`、根号 `\sqrt{...}`、`n` 次根 `\sqrt[n]{...}`
- 大型算子 `\sum` `\prod` `\int` `\lim` 及其上下限
- 矩阵 `\begin{pmatrix}...\end{pmatrix}` / `bmatrix` / `vmatrix`
- 对齐环境 `\begin{aligned}...\end{aligned}`
- 希腊字母、`\det` `\log` `\sin` 等函数名、`\mathbf` `\mathcal` 等字体命令

**pandoc 缺失时回退**（Unicode 方案，仅覆盖）：分数（`a⁄b` 拼接）、上下标、`\sum`/`\alpha` 等符号命令、函数名。**不能**做矩阵/对齐/根号下嵌套。

建议本机 `brew install pandoc`（macOS）/ `apt install pandoc`（Linux）以获得完整公式能力。pandoc 是独立二进制，不是 Python 包，运行时由 texcanvas 子进程调用。居中呈现于直角面板。

### 3.9 `block` — Beamer 风格块

```yaml
- kind: block
  title: 注意事项
  block:
    style: alert            # default | alert | example
    title: 警示
    body: 样本量仍然有限，外推需谨慎。
    bullets: [...]          # 可选
```

- `block.body` 或 `block.bullets` 至少一项。
- `style`：`default`（蓝）/ `alert`（红）/ `example`（绿），对应 beamer 的 block / alertblock / exampleblock。
- `block.title` 可选。面板为直角边。

### 3.10 `conclusion` — 结论页

```yaml
- kind: conclusion
  title: 总结
  takeaway: 提出的方法在准确率与效率上均有提升。
  bullets:
    - 方法具有可重复性
    - 后续需要扩大样本量
```

`takeaway` 或 `bullets` 至少一项。`takeaway` 为醒目大字。

### 3.11 `references` — 参考文献

```yaml
- kind: references
  title: 参考文献
  items:
    - "Doe et al. Example paper. Journal, 2024."
    - "Smith et al. Another paper. Journal, 2023."
```

`items` 必填且非空，生成可编辑编号条目。

---

## 4. 内容容量与 warning

TexCanvas **不自动缩排**超长内容，而是给出 warning（仍会生成 pptx）。阈值：

| 场景 | 阈值 |
|------|------|
| 每个 slide 的 bullets | > 8 |
| code 行数 | > 18 |
| table 行数 | > 10 |
| table 单行单元格数 | > 6 |
| references 条目数 | > 12 |
| section 数 | > 8（导航可能拥挤，会用 `short_title` 并自动缩小字号） |

超长内容只在安全区内绘制，溢出部分不会自动换页——拿到 warning 后应在 YAML 里拆分 slide 或精简内容。

---

## 5. 字体（固定不变）

| 用途 | 字体 |
|------|------|
| 中文（CJK） | 苹方-简（PingFang SC） |
| 英文 / 数字 / 符号 | Helvetica |
| 代码 | Menlo |

每个 run 同时写入 `a:latin` + `a:ea` + `a:cs` 三个字体元素，保证无论模板主题字体如何继承，中英文始终落在指定字体。**这三个字体名不可改**（除非改 `src/texcanvas/theme.py` 的 `DEFAULT_THEME`）。苹方-简 与 Helvetica 是 macOS 内置字体，Linux/Windows 或容器环境会字体替换——最终导出 PDF 前应在目标机器检查字体替换与换行。

---

## 6. 视觉与形状约定（便于 agent 定位/微调输出）

- 画布 13.333 × 7.5 英寸（16:9）。
- 所有内容面板（block / code / equation / two_columns / conclusion）统一为**直角矩形**（非圆角），更接近 Beamer。
- 生成形状使用 `DSH_` 前缀命名：`DSH_TITLE_BAND`、`DSH_TITLE_COVER`、`DSH_BODY`、`DSH_NAV_*`、`DSH_FOOTER_*`、`DSH_IMAGE`、`DSH_TABLE`、`DSH_CODE_BODY`、`DSH_EQUATION`、`DSH_BLOCK_PANEL` 等，便于后续脚本/测试定位。
- 输出只使用常规 OOXML（文本框、矩形、chevron、线条、原生表格、PNG/JPEG），无 VBA / ActiveX / SmartArt / 复杂动画。

---

## 7. 生成 deck 的工作流建议

1. **先写 metadata + 一个 section 的几张 slide**，跑 `texcanvas ... -o out.pptx` 验证 schema 通过、能在 WPS 打开。
2. 用 `--verbose` 看 warning，按阈值拆分超长 slide。
3. 图片用 `--asset-root` 指定基准目录，避免绝对路径。
4. 需要自定义母版/Logo/背景时，在 WPS 里做好 `.pptx` 模板，用 `-t` 传入；模板里示例页会被清空。
5. 公式只用支持的标记；复杂公式留空或写注释，导出后在 WPS 用公式编辑器补。
6. 检查最终 PDF 的字体替换与换行（尤其跨机器时）。

### 人工微调同步（sync pull）

如果在 WPS/PowerPoint 中移动 block、修改文字、插入图片或调整 slide 顺序，可把编辑后的 PPTX 提取为覆盖层：

```bash
texcanvas sync pull output/edited.pptx -o overrides.yml
texcanvas build deck.yml -o output/rebuilt.pptx --overrides overrides.yml
```

`sync pull` 不反写 `deck.yml`，而是生成 `overrides.yml` 和新增图片资源目录。YAML 继续作为语义源文件，覆盖层记录人工布局/文字/图片/顺序调整。公式、母版、动画、SmartArt 等复杂对象暂不反向转换。生成 slide 的 `p:cSld/@name` 会保存稳定语义 ID，用于 slide 重排后的匹配；`python-pptx` 不暴露的扩展对象则由 XML 适配器处理。

### 常见错误

| 错误信息 | 原因 | 处理 |
|----------|------|------|
| `root: expected a mapping` | YAML 顶层不是 dict | 检查缩进/顶层结构 |
| `sections[0].slides[1].kind: unsupported value 'foo'` | kind 拼错 | 用上文 11 种之一 |
| `...two_columns requires left and right columns` | 缺 `left`/`right` | 两栏都必填 |
| `...image.path is required` | image 缺 path | 补 `path` |
| `...code.source: is required` | code.source 为空 | 补非空 source |
| `...table: header or rows are required` | table 全空 | 补 header 或 rows |
| `...equation: is required` | equation 为空 | 补 equation 文本 |
| `aspect: only '16:9' is currently supported` | aspect 写错 | 改回 `"16:9"` |
| `Error: <path>: cannot read input` | 文件不存在/无权限 | 检查路径 |
| `...image.path: image not found: <abs>` | 图片路径不存在 | 修路径或用 `--no-strict` |
| `...image.path: unsupported image format .svg; use PNG or JPEG` | 用了 SVG 等不支持格式 | 转 PNG/JPEG |

---

## 8. 代码维护（扩展时再看）

- **架构**：`loader.py`（YAML → frozen IR `Deck/Section/Slide/...`）→ `validate.py`（schema 校验 + warning）→ `render.py`（调度）→ `renderers/`（共享 `chrome.py` + 各版式 renderer）；`sync.py` 在生成后的 PPTX XML 与 `overrides.yml` 之间提供反向适配。IR 不含任何 `python-pptx` 对象。
- **加新 slide kind**：① `model.py` 的 `SlideKind` 加成员 + 必要的 spec dataclass；② `loader.py._slide` 解析字段；③ `validate.py.validate_deck` 加校验分支、`content_warnings` 加阈值；④ `renderers/<kind>.py` 写 `render_<kind>(ctx, slide)`；⑤ `renderers/__init__.py` 导出；⑥ `render.py` 的 `RENDERERS` dict 注册；⑦ 补测试。
- **字体不变量**：所有 run 必须经 `set_run_font(run, *, latin, ea)`（`renderers/common.py`），它同时写 `a:latin`+`a:ea`+`a:cs`。不要用裸 `run.font.name = ...`（只写 `a:latin`，CJK 会掉字体）。
- **面板形状不变量**：内容面板用 `MSO_AUTO_SHAPE_TYPE.RECTANGLE`（`radius=False`），不要改回圆角。
- **测试**：`pytest` 全绿是合并前提；`tests/test_typography.py` 守护字体三写与直角面板不变量。
- 改完跑 `python -m build` 重新生成 wheel/sdist（产物在 `dist/`，已 gitignore）。
