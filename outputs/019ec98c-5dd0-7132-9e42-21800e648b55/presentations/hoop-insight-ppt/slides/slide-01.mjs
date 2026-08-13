import { C, bg, dot, miniCourt, pill, small } from "./common.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);

  ctx.addShape(slide, { x: 0, y: 0, w: 1280, h: 720, fill: "linear(135deg, #0B1020, #121A2D 55%, #20170B)", line: ctx.line() });
  miniCourt(slide, ctx, 845, 108, 1.15, "#F59E0B55");
  for (const p of [
    [910, 180, C.teal], [985, 218, C.amber], [1048, 156, C.red], [1120, 250, C.teal],
    [936, 314, C.amber], [1092, 352, C.teal], [1010, 402, C.red], [1150, 165, C.blue],
  ]) dot(slide, ctx, p[0], p[1], p[2], 9);

  pill(slide, ctx, "NBA DATA · FASTAPI · REACT · AI", 74, 78, 272, C.ink3, C.teal);
  ctx.addText(slide, {
    text: "Hoop Insight",
    x: 72, y: 150, w: 650, h: 82, fontSize: 62, bold: true,
    color: C.white, typeface: "Aptos Display",
  });
  ctx.addText(slide, {
    text: "NBA 篮球数据分析与智能问数系统",
    x: 72, y: 238, w: 760, h: 58, fontSize: 34, bold: true,
    color: C.paper, typeface: "PingFang SC",
  });
  small(slide, ctx, "从 NBA 官方数据接口到可视化复盘，再到中文自然语言问数的一体化课程项目。", 76, 320, 720, 58, C.muted, 20);

  const metrics = [
    ["8", "核心页面"],
    ["6", "NBA 接口族"],
    ["3", "数据文件层"],
    ["AI", "中文问数助手"],
  ];
  metrics.forEach((m, i) => {
    const x = 76 + i * 160;
    ctx.addShape(slide, { x, y: 440, w: 126, h: 94, fill: "#FFFFFF0E", line: ctx.line("#FFFFFF22", 1), geometry: "roundRect" });
    ctx.addText(slide, { text: m[0], x: x + 16, y: 456, w: 94, h: 38, fontSize: 32, bold: true, color: i === 3 ? C.teal : C.amber, typeface: "Aptos", align: "center" });
    ctx.addText(slide, { text: m[1], x: x + 12, y: 500, w: 102, h: 22, fontSize: 15, color: C.paper, typeface: "PingFang SC", align: "center" });
  });

  ctx.addText(slide, { text: "汇报人：吕品正", x: 76, y: 610, w: 260, h: 28, fontSize: 20, color: C.text, typeface: "PingFang SC" });
  ctx.addText(slide, { text: "课程项目展示", x: 1042, y: 610, w: 150, h: 24, fontSize: 14, bold: true, color: C.muted, align: "right", typeface: "PingFang SC" });
  return slide;
}
