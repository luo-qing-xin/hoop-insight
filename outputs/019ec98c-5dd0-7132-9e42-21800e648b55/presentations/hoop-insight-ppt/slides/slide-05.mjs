import { C, bg, dot, footer, kicker, miniCourt, small, title } from "./common.mjs";

function featureShell(slide, ctx, x, label, titleText, color) {
  ctx.addShape(slide, { x, y: 190, w: 342, h: 390, fill: "#FFFFFF0B", line: ctx.line("#FFFFFF20", 1), geometry: "roundRect" });
  ctx.addText(slide, { text: label, x: x + 24, y: 212, w: 80, h: 20, fontSize: 12, bold: true, color, typeface: "Aptos" });
  ctx.addText(slide, { text: titleText, x: x + 24, y: 240, w: 286, h: 40, fontSize: 25, bold: true, color: C.white, typeface: "PingFang SC" });
}

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "PROJECT HIGHLIGHTS", 72, 50);
  title(slide, ctx, "三个能力把篮球数据从“表格”推进到“洞察”。", 72, 82, 900);

  featureShell(slide, ctx, 72, "01 · SHOT SPACE", "投篮空间可视化", C.amber);
  miniCourt(slide, ctx, 108, 308, 0.82, "#FFFFFF38");
  [[150, 348, C.teal], [202, 375, C.amber], [260, 337, C.red], [292, 442, C.teal], [180, 480, C.amber], [276, 500, C.blue], [220, 422, C.red]].forEach(p => dot(slide, ctx, p[0], p[1], p[2], 9));
  small(slide, ctx, "散点图展示出手位置；热区图和区域效率统计解释球员或球队的出手选择与得分效率。", 98, 525, 286, 44, C.muted, 15);

  featureShell(slide, ctx, 469, "02 · ASK AI", "智能问数助手", C.teal);
  ctx.addShape(slide, { x: 505, y: 322, w: 260, h: 76, fill: "#0F766E55", line: ctx.line("#22C7A9", 1.5), geometry: "roundRect" });
  ctx.addText(slide, { text: "“哪支球队近期净效率最高？”", x: 526, y: 346, w: 218, h: 24, fontSize: 17, bold: true, color: C.white, typeface: "PingFang SC", align: "center" });
  ctx.addShape(slide, { x: 535, y: 426, w: 200, h: 70, fill: "#FFFFFF10", line: ctx.line("#FFFFFF25", 1), geometry: "roundRect" });
  ctx.addText(slide, { text: "结构化数据上下文\n+\n中文分析回答", x: 558, y: 438, w: 154, h: 44, fontSize: 15, color: C.paper, typeface: "PingFang SC", align: "center" });
  small(slide, ctx, "自然语言提问，后端基于真实结构化数据组织上下文，支持比赛解读、球员比较、球队分析和报告生成。", 495, 525, 286, 44, C.muted, 15);

  featureShell(slide, ctx, 866, "03 · DATA OPS", "NBA API 自动化接入", C.red);
  const cx = 1037, cy = 402;
  [["请求", cx - 112, cy - 76, C.amber], ["缓存", cx + 42, cy - 76, C.teal], ["处理", cx + 42, cy + 44, C.blue], ["展示", cx - 112, cy + 44, C.red]].forEach(([t, x, y, color]) => {
    ctx.addShape(slide, { x, y, w: 78, h: 46, fill: "#FFFFFF12", line: ctx.line(color, 1.4), geometry: "roundRect" });
    ctx.addText(slide, { text: t, x, y: y + 12, w: 78, h: 18, fontSize: 15, bold: true, color: C.white, typeface: "PingFang SC", align: "center" });
  });
  ctx.addText(slide, { text: "↻", x: cx - 23, y: cy - 28, w: 46, h: 46, fontSize: 36, bold: true, color: C.amber, typeface: "Aptos", align: "center" });
  small(slide, ctx, "按赛季、球队、球员或比赛 ID 自动请求；缓存过期后重新拉取，支持实时 / 准实时更新。", 892, 525, 286, 44, C.muted, 15);

  footer(slide, ctx, 5);
  return slide;
}
