import { C, bg, dot, miniCourt, pill, small } from "./common.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  ctx.addShape(slide, { x: 0, y: 0, w: 1280, h: 720, fill: "linear(145deg, #0B1020, #101827 58%, #1F2937)", line: ctx.line() });
  miniCourt(slide, ctx, 815, 90, 1.25, "#22C7A933");
  for (let i = 0; i < 18; i += 1) {
    const x = 820 + (i % 6) * 62;
    const y = 430 + Math.floor(i / 6) * 42;
    dot(slide, ctx, x, y, i % 3 === 0 ? C.amber : i % 3 === 1 ? C.teal : C.red, 6);
  }

  pill(slide, ctx, "THANK YOU", 74, 94, 160, C.ink3, C.teal);
  ctx.addText(slide, {
    text: "谢谢观看！",
    x: 72, y: 174, w: 560, h: 86, fontSize: 62, bold: true,
    color: C.white, typeface: "PingFang SC",
  });
  ctx.addText(slide, {
    text: "欢迎老师和同学批评指正。",
    x: 76, y: 280, w: 520, h: 42, fontSize: 30, color: C.paper, typeface: "PingFang SC",
  });
  ctx.addShape(slide, { x: 76, y: 390, w: 620, h: 108, fill: "#FFFFFF0B", line: ctx.line("#FFFFFF1E", 1), geometry: "roundRect" });
  small(slide, ctx, "Hoop Insight 将 NBA 官方数据接口、本地数据处理、FastAPI 在线服务、React 可视化和 AI 问数串成一条完整的数据分析链路。", 108, 420, 556, 48, C.text, 20, true);

  [["数据接入", C.amber], ["分析计算", C.teal], ["可视化展示", C.blue], ["智能问数", C.red]].forEach(([t, color], i) => {
    const x = 82 + i * 145;
    ctx.addShape(slide, { x, y: 552, w: 120, h: 36, fill: "#FFFFFF0D", line: ctx.line(color, 1.2), geometry: "roundRect" });
    ctx.addText(slide, { text: t, x, y: 561, w: 120, h: 18, fontSize: 15, bold: true, color: C.white, typeface: "PingFang SC", align: "center" });
  });

  ctx.addText(slide, { text: "吕品正", x: 76, y: 638, w: 160, h: 28, fontSize: 20, color: C.muted, typeface: "PingFang SC" });
  return slide;
}
