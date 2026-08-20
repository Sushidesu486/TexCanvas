# texcanvas

`texcanvas` 是一个面向科研汇报的 YAML → PPTX 生成器。它保留 Beamer 的结构化工作流（section、固定 headline、frame title、footline 和页码），同时输出普通、可编辑的 OOXML `.pptx`，便于在 macOS WPS 演示中继续微调。

项目采用"内容模型与渲染分离"的设计：YAML 会先转换成不可变的 Presentation IR，IR 不包含任何 `python-pptx` 对象；共享 chrome renderer 统一绘制 section 导航、标题和页脚，各版式 renderer 只处理内容区。

## 安装

要求 Python 3.10 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### 可选：安装 pandoc（获得完整数学公式能力）

`equation` 版式在系统装有 [pandoc](https://pandoc.org/) 时，会把 LaTeX 公式转成**原生可编辑的 OMML 公式对象**（支持矩阵 `\begin{pmatrix}`、对齐 `\begin{aligned}`、嵌套根号 `\sqrt{\frac{a}{b}}`、求和上下限等完整结构，WPS/PowerPoint 中可双击编辑）。pandoc 缺失时回退到 Unicode 符号方案，仅覆盖分数、上下标、希腊字母等基础标记。

```bash
brew install pandoc          # macOS (Homebrew)
# 或 sudo apt install pandoc # Debian/Ubuntu
# 或参见 https://pandoc.org/installing.html
```

验证：

```bash
pandoc --version              # 任意较新版本均可
texcanvas build deck.yml -o out.pptx
```

> pandoc 是一个独立二进制工具，不作为 Python 依赖安装；texcanvas 在运行时通过子进程调用它。`pip install` 不会自动装 pandoc。

## 快速开始

最简单的方式是用脚手架一键创建一个 deck 项目：

```bash
texcanvas init my-talk        # 在当前目录创建 my-talk/ 脚手架
cd my-talk
bash build.sh                 # 生成 output/deck.pptx
```

脚手架会生成 `AGENTS.md`、`deck.yml`（最小可跑）、`assets/`、`build.sh`（自动定位包内模板）和 `output/`。`deck.yml` 是一个含封面页 + section_divider + 正文的三页示例，改它即可。

也可以直接对任意 YAML 调用 `build`：

```bash
texcanvas build examples/demo.yml \
  -o output/demo.pptx \
  --asset-root examples
```

不传 `-t` 时自动使用随包分发的 `beamer-academic.pptx` 模板（母版已烘焙 16:9 背景色）。也可显式指定模板：

```bash
texcanvas build deck.yml -t your-template.pptx -o out.pptx --asset-root .
```

通过模块方式运行：

```bash
python -m texcanvas build examples/demo.yml -o output/demo.pptx --asset-root examples
```

Python API 只有一个主要入口：

```python
from texcanvas import build

report = build(
    input="examples/demo.yml",
    output="output/demo.pptx",
    strict=True,
    asset_root="examples",
)
print(report.slide_count, report.warnings)
```

`BuildReport` 包含输出绝对路径、页数、section 数和 warnings。保存使用同目录临时文件和原子替换；失败时不会留下半成品目标文件。

### 命令行参数

`texcanvas` 采用子命令结构：

```text
texcanvas [-h] <command> ...

commands:
  build     从 YAML 生成 PPTX
  init      在当前目录创建一个 deck 脚手架目录
```

`texcanvas build --help`：

```text
usage: texcanvas build [-h] -o OUTPUT [-t TEMPLATE] [--asset-root ASSET_ROOT]
                       [--strict | --no-strict] [--verbose]
                       input

positional arguments:
  input                 YAML deck 描述文件路径

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   输出 .pptx 文件路径（父目录不存在时会自动创建）
  -t, --template TEMPLATE
                        可选的可编辑 PPTX 模板路径；不传时使用随包模板
  --asset-root ASSET_ROOT
                        相对图片路径的基准目录；默认为 YAML 文件所在目录
  --strict              严格模式（默认）：图片缺失、损坏或格式不支持时立即失败
  --no-strict           宽松模式：记录 warning 并在页面放入可编辑占位框后继续生成
  --verbose             打印每条 warning 的详细信息
```

`texcanvas init [--help] name [-d DIR]`：在 `-d`（默认当前目录）下创建名为 `name` 的脚手架目录。

- `input`：YAML deck 描述文件，必填。
- `-o / --output`：输出 `.pptx` 路径，必填；父目录不存在时会自动创建。
- `-t / --template`：可选模板；不传时使用随包分发的 `beamer-academic.pptx`。自定义模板会保留母版、主题和页面尺寸，模板中的示例页会被清空（输入模板本身不会被修改）。
- `--asset-root`：相对图片路径的基准目录；未指定时以 YAML 文件所在目录为基准。
- `--strict` / `--no-strict`：二者互斥。`--strict`（默认）下图片缺失、损坏或格式不支持时立即失败；`--no-strict` 下记录 warning 并在页面放入明显且可编辑的占位框后继续生成。
- `--verbose`：打印每条 warning 的详细信息。

## YAML 格式

根节点必须是 mapping，`metadata.title` 和至少一个 section 必填。目前 `aspect` 仅支持 `"16:9"`。完整示例见 `examples/demo.yml`。

```yaml
metadata:
  title: 科研训练汇报
  author: 张三
  institute: Zhejiang University
  short_title: Research Training
aspect: "16:9"
sections:
  - id: background
    title: 研究背景
    short_title: Background
    slides:
      - kind: content
        title: 科学问题
        body: 本研究希望回答以下问题。
        bullets:
          - 现象为什么发生？
```

section 的 `id` 可省略：英文标题会生成 slug，无法安全 slug 化的标题会使用 `section-1`、`section-2` 等稳定 ID。所有 ID 必须唯一。

## 支持的版式

- `title`：封面页。从 deck `metadata` 读取标题/副标题/作者/单位/日期，绘制一条主色满宽带 + accent 高亮条 + 大标题 + 副标题 + 署名行；封面页不绘制导航、frame title 和页脚。建议作为 deck 的第一页。可省略 slide 级 `title`/`subtitle`，此时回退到 `metadata.title`/`metadata.subtitle`。
- `section_divider`：章节编号、标题和可选副标题。
- `content`：正文和 bullet list。可选 `citation`（页底灰色引用条）、`inline_image`（内联小图，文字环绕：`path`/`width`/`align: left|right`）。
- `two_columns`：必须同时提供非空 `left` 和 `right`；列支持 `heading`、`body`、`bullets`。
- `image`：必须提供 `image.path`；`fit` 可为 `contain` 或 `cover`；可选 `caption`。
- `code`：必须提供 `code.source`；可选 `code.lang`（python/c/cpp/java/javascript/rust/go 等，未识别时回退为通用 C 系高亮）、`code.caption`。代码以等宽字体、带行内语法高亮（关键字/字符串/注释/数字不同颜色）绘制在直角面板内，全部为可编辑文本。
- `table`：`table.header` 或 `table.rows` 至少有一项；`header` 为字符串列表，`rows` 为字符串列表的列表（行可参差，缺列留空）；可选 `table.caption`。生成原生 PPTX 表格，表头使用主题色填充，奇数行斑马底色，单元格带细网格线。
- `equation`：必须提供 `equation` 文本（LaTeX）。系统装有 `pandoc` 时转成原生 OMML 公式对象（支持 `\frac`/`\sum`/`\sqrt`/`\begin{pmatrix}` 矩阵/`\begin{aligned}` 对齐等完整结构，WPS 可双击编辑），缺失时回退 Unicode 符号方案。以居中直角面板呈现。
- `block`：必须提供 `block.body` 或 `block.bullets`；`block.style` 可为 `default`/`alert`/`example`（分别使用蓝/红/绿三套标题+底色，对应 beamer 的 block/alertblock/exampleblock）；可选 `block.title`。面板为直角边。
- `conclusion`：提供醒目的 `takeaway` 和补充 bullets，二者至少有一项。
- `references`：`items` 必填，生成可编辑的编号条目。

内容较多（例如超过 8 个 bullets、超过 18 行代码、超过 10 行表格或 12 条参考文献）时会给出 warning，而不是尝试不可预测的自动缩排。section 超过 8 个也会提示导航可能拥挤；渲染器会使用 `short_title` 并自动缩小导航字号。

### `code` / `table` / `equation` / `block` 示例

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

- kind: table
  title: 方法对比
  table:
    header: [方法, 准确率, 推理时间]
    rows:
      - [Baseline, "0.82", "12.4 ms"]
      - [Ours, "0.91", "8.1 ms"]
    caption: 表 1：指标对比

- kind: equation
  title: 损失函数
  equation: |
    L = -\frac{1}{N}\sum_{i=1}^{N} y_i \log p_i

- kind: block
  title: 注意事项
  block:
    style: alert
    title: 警示
    body: 样本量仍然有限，外推需谨慎。
```

## 图片路径与 strict 模式

相对图片路径（`image` 版式和 `content.inline_image`）以 `--asset-root` 为基准；未指定时以 YAML 文件所在目录为基准。当前明确支持 PNG、JPEG，SVG 不保证兼容并会被拒绝。

- `--strict`（默认）：图片缺失、损坏或格式不支持时立即失败。
- `--no-strict`：记录 warning，在页面放入明显且可编辑的占位框后继续生成（内联图缺失则跳过，正文保持满宽）。

`image` 版式的 `contain` 完整显示图片并允许留白；`cover` 使用 `crop_left/right/top/bottom` 做中心裁剪。两种模式都通过 Pillow 读取原始尺寸并保持纵横比，不做非等比拉伸。`content.inline_image` 按指定 `width`（英寸）等比缩放，`align` 控制贴左/右，正文自动缩到剩余宽度。

## 模板

`texcanvas build` 不传 `-t` 时自动使用随包分发的 `beamer-academic.pptx`（位于包内 `texcanvas/templates/`，母版已烘焙 16:9 背景色 F7F9FC）。你也可以传入自定义模板：`texcanvas build deck.yml -t your.pptx -o out.pptx`。

传入模板时，生成器使用 `Presentation(template)`，保留页面尺寸、主题、母版和版式关系，选择名为 `Blank`/`空白` 的版式（否则选择占位符最少的版式）。模板中的现有示例页会从输出副本中删除，输入模板不会被修改。

`python-pptx` 对母版编辑能力有限。正式使用时，建议：

1. 在 WPS 中编辑母版、字体、Logo 和页面背景；
2. 保留一个空白版式；
3. 将文件另存为 `.pptx`；
4. 通过 `-t` 传入。

动态导航、frame title、footline 和内容仍由 Python 绘制为普通可编辑形状。当前版本不强依赖形状命名约定，但生成形状使用 `DSH_TITLE`、`DSH_BODY`、`DSH_NAV_*`、`DSH_FOOTER_*`、`DSH_IMAGE` 等名字，便于测试和后续工具定位。

如需重新生成随包基础模板和演示图片：

```bash
python scripts/create_template.py     # → src/texcanvas/templates/beamer-academic.pptx
python scripts/create_demo_assets.py
```

## WPS 兼容说明

输出只使用常规 OOXML 文本框、矩形、chevron、线条、原生表格和 PNG/JPEG 图片；不使用 VBA、ActiveX、COM、SmartArt、复杂动画或 PPT 原生 section。字体、字号、颜色、文本框边距和段落间距均显式设置。生成结果不是整页截图，各形状和文字可以继续编辑。代码块的语法高亮由多个带颜色的 run 组成，公式中的上下标通过 run 的 baseline 属性实现，均在 WPS 中可编辑。所有内容面板（block、code、equation、two_columns、conclusion）统一使用直角边矩形，视觉更接近 Beamer。

## 字体

字体固定为：中文（CJK）使用 **苹方-简（PingFang SC）**，英文/数字/符号使用 **Helvetica**，代码使用 **Menlo**。

`python-pptx` 的 `Font.name` 只写入 `a:latin`，而 WPS/PowerPoint 渲染 CJK 字形时从 `a:ea`（东亚）取字体、复杂文字从 `a:cs` 取字体——这两个元素 `python-pptx` 并不暴露。因此本项目在每个 run 上同时写入 `a:latin` + `a:ea` + `a:cs`，保证无论模板主题字体如何继承，中文始终落在苹方-简、英文/数字始终落在 Helvetica、代码落在 Menlo，三者均为无衬线/等宽无衬线字体。

字体是否完全一致取决于本机安装情况（苹方-简 与 Helvetica 为 macOS 内置字体）。WPS 在字体缺失时可能替换字体，建议在最终导出 PDF 前检查字体替换和换行。

## 测试

```bash
pytest
```

测试覆盖模型不可变性、YAML/schema 校验、section ID、图片资源、contain/cover 几何、导航宽度、页码、CLI、模板不变性、新增的 code/table/equation/block 版式校验与渲染、脚手架生成与端到端 `build.sh`，以及集成生成。集成测试会用 `python-pptx` 重新打开输出，并检查可编辑形状、当前 section 颜色、图片、表格单元格、公式上下标、代码关键字高亮、参考文献、ZIP 格式和关键 OOXML 文件。

## 已知限制

- 当前仅支持 16:9 内容模型。`title` 为内置封面版式，不依赖外部模板的标题母版。
- 不深度修改幻灯片母版或主题 XML；高级模板视觉应在 WPS 中制作。
- 不自动同步 PowerPoint/WPS 原生“节”。当前 section 完全由 YAML 层级决定。
- 不保证 SVG 跨 WPS 版本表现，建议先转 PNG。
- 自动排版以稳定安全区为目标；极长文字只给 warning，仍需在 WPS 中人工微调。
- `notes` 字段会被解析并保留在 IR 中，当前版本尚未写入 PPTX 讲者备注。
- `equation` 在系统装有 `pandoc` 时把 LaTeX 转成原生 OMML 公式对象（支持矩阵/对齐/根号等完整结构，WPS 可双击编辑），缺失时回退到 Unicode 符号方案；TikZ 转 SVG 管线为后续规划。
- 自动测试可以验证 OOXML 与 `python-pptx` 兼容性，但 macOS WPS GUI 打开效果必须由用户进行最终人工验收。

## 项目结构

```text
src/texcanvas/          模型、加载、校验、资源、几何、build/CLI/scaffold 与渲染器
src/texcanvas/renderers/
                        共享 chrome、封面页和六种内容版式
src/texcanvas/templates/
                        随包分发的 beamer-academic.pptx 模板
examples/               YAML 和示例图片
scripts/                模板与演示图片生成脚本
tests/                  单元、集成、模板、脚手架和 OOXML smoke tests
output/                 生成文件目录
```

