# beamer-pptx

`beamer-pptx` 是一个面向科研汇报的 YAML → PPTX 生成器。它保留 Beamer 的结构化工作流（section、固定 headline、frame title、footline 和页码），同时输出普通、可编辑的 OOXML `.pptx`，便于在 macOS WPS 演示中继续微调。

项目采用“内容模型与渲染分离”的设计：YAML 会先转换成不可变的 Presentation IR，IR 不包含任何 `python-pptx` 对象；共享 chrome renderer 统一绘制 section 导航、标题和页脚，各版式 renderer 只处理内容区。

## 安装

要求 Python 3.10 或更高版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 快速开始

仓库已提供示例 YAML、PNG 图片和一个零内容页的 16:9 模板：

```bash
beamer-pptx examples/demo.yml \
  -t templates/beamer-academic.pptx \
  -o output/demo.pptx \
  --asset-root examples
```

也可以运行：

```bash
python -m beamer_pptx examples/demo.yml \
  --template templates/beamer-academic.pptx \
  --output output/demo.pptx \
  --asset-root examples
```

Python API 只有一个主要入口：

```python
from beamer_pptx import build

report = build(
    input="examples/demo.yml",
    output="output/demo.pptx",
    template="templates/beamer-academic.pptx",
    strict=True,
    asset_root="examples",
)
print(report.slide_count, report.warnings)
```

`BuildReport` 包含输出绝对路径、页数、section 数和 warnings。保存使用同目录临时文件和原子替换；失败时不会留下半成品目标文件。

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

- `section_divider`：章节编号、标题和可选副标题。
- `content`：正文和 bullet list。
- `two_columns`：必须同时提供非空 `left` 和 `right`；列支持 `heading`、`body`、`bullets`。
- `image`：必须提供 `image.path`；`fit` 可为 `contain` 或 `cover`；可选 `caption`。
- `conclusion`：提供醒目的 `takeaway` 和补充 bullets，二者至少有一项。
- `references`：`items` 必填，生成可编辑的编号条目。

内容较多（例如超过 8 个 bullets 或 12 条参考文献）时会给出 warning，而不是尝试不可预测的自动缩排。section 超过 8 个也会提示导航可能拥挤；渲染器会使用 `short_title` 并自动缩小导航字号。

## 图片路径与 strict 模式

相对图片路径以 `--asset-root` 为基准；未指定时以 YAML 文件所在目录为基准。当前明确支持 PNG、JPEG，SVG 不保证兼容并会被拒绝。

- `--strict`（默认）：图片缺失、损坏或格式不支持时立即失败。
- `--no-strict`：记录 warning，在页面放入明显且可编辑的占位框后继续生成。

`contain` 完整显示图片并允许留白；`cover` 使用 `crop_left/right/top/bottom` 做中心裁剪。两种模式都通过 Pillow 读取原始尺寸并保持纵横比，不做非等比拉伸。

## 模板制作指南

传入模板时，生成器使用 `Presentation(template)`，保留页面尺寸、主题、母版和版式关系，选择名为 `Blank`/`空白` 的版式（否则选择占位符最少的版式）。模板中的现有示例页会从输出副本中删除，输入模板不会被修改。

`python-pptx` 对母版编辑能力有限。正式使用时，建议：

1. 在 WPS 中编辑母版、字体、Logo 和页面背景；
2. 保留一个空白版式；
3. 将文件另存为 `.pptx`；
4. 通过 `--template` 传入。

动态导航、frame title、footline 和内容仍由 Python 绘制为普通可编辑形状。当前版本不强依赖形状命名约定，但生成形状使用 `DSH_TITLE`、`DSH_BODY`、`DSH_NAV_*`、`DSH_FOOTER_*`、`DSH_IMAGE` 等名字，便于测试和后续工具定位。

如需重新生成仓库内基础模板和演示图片：

```bash
python scripts/create_template.py
python scripts/create_demo_assets.py
```

## WPS 兼容说明

输出只使用常规 OOXML 文本框、矩形、圆角矩形、chevron、线条和 PNG/JPEG 图片；不使用 VBA、ActiveX、COM、SmartArt、复杂动画或 PPT 原生 section。字体、字号、颜色、文本框边距和段落间距均显式设置。生成结果不是整页截图，各形状和文字可以继续编辑。

字体是否完全一致取决于本机安装情况。默认中文字体为 `Noto Sans CJK SC`，英文字体为 Arial；WPS 在字体缺失时可能替换字体。建议在最终导出 PDF 前检查字体替换和换行。

## 测试

```bash
pytest
```

测试覆盖模型不可变性、YAML/schema 校验、section ID、图片资源、contain/cover 几何、导航宽度、页码、CLI、模板不变性，以及集成生成。集成测试会用 `python-pptx` 重新打开输出，并检查可编辑形状、当前 section 颜色、图片、参考文献、ZIP 格式和关键 OOXML 文件。

## 已知限制

- 当前仅支持 16:9 内容模型，不包含 cover/outline 自动版式。
- 不深度修改幻灯片母版或主题 XML；高级模板视觉应在 WPS 中制作。
- 不自动同步 PowerPoint/WPS 原生“节”。当前 section 完全由 YAML 层级决定。
- 不保证 SVG 跨 WPS 版本表现，建议先转 PNG。
- 自动排版以稳定安全区为目标；极长文字只给 warning，仍需在 WPS 中人工微调。
- `notes` 字段会被解析并保留在 IR 中，当前版本尚未写入 PPTX 讲者备注。
- 自动测试可以验证 OOXML 与 `python-pptx` 兼容性，但 macOS WPS GUI 打开效果必须由用户进行最终人工验收。

## 项目结构

```text
src/beamer_pptx/        模型、加载、校验、资源、几何、build/CLI 与渲染器
src/beamer_pptx/renderers/
                        共享 chrome 和六种内容版式
templates/              可编辑的基础 PPTX 模板
examples/               YAML 和示例图片
scripts/                模板与演示图片生成脚本
tests/                  单元、集成、模板和 OOXML smoke tests
output/                 生成文件目录
```

