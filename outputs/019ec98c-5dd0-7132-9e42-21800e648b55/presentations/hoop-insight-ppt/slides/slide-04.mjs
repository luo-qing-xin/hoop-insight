import { C, bg, footer, kicker, nodeBox, title } from "./common.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.paper);
  kicker(slide, ctx, "LOCAL DATA STORE", 72, 50, false);
  title(slide, ctx, "raw / processed / cache 分离，让数据可追溯、可展示、可复用。", 72, 82, 980, false);

  nodeBox(slide, ctx, {
    x: 92, y: 215, w: 315, h: 330, label: "data/raw",
    body: "保存 NBA 接口返回的原始数据\n\n用途：保留最初来源，方便检查字段、重新处理和对比接口变更\n\n示例：LeagueGameLog、ShotChartDetail、PlayByPlayV3 原始 CSV",
    fill: "#FFF8EA", stroke: "#D8C99F", accent: C.amber, dark: false,
  });
  nodeBox(slide, ctx, {
    x: 482, y: 215, w: 315, h: 330, label: "data/processed",
    body: "保存清洗后的演示数据和页面可读数据\n\n用途：供前端展示、后端分析、demo 模式稳定运行\n\n示例：games、players、teams、shots、game_flow、box_scores",
    fill: "#FFFFFF", stroke: "#CFD8DC", accent: C.teal, dark: false,
  });
  nodeBox(slide, ctx, {
    x: 872, y: 215, w: 315, h: 330, label: "data/cache",
    body: "缓存 API 响应和本地查询结果\n\n用途：减少重复请求、提升运行效率、避免频繁访问 NBA 官方接口\n\n缓存过期后可自动重新拉取最新数据",
    fill: "#F4F7FB", stroke: "#CBD5E1", accent: C.red, dark: false,
  });

  ctx.addText(slide, { text: "接口响应", x: 294, y: 575, w: 96, h: 22, fontSize: 16, bold: true, color: "#7A5A08", typeface: "PingFang SC", align: "center" });
  ctx.addText(slide, { text: "清洗聚合", x: 596, y: 575, w: 96, h: 22, fontSize: 16, bold: true, color: "#0E766B", typeface: "PingFang SC", align: "center" });
  ctx.addText(slide, { text: "请求加速", x: 988, y: 575, w: 96, h: 22, fontSize: 16, bold: true, color: "#B91C1C", typeface: "PingFang SC", align: "center" });
  ctx.addShape(slide, { x: 390, y: 584, w: 88, h: 2, fill: "#A89773", line: ctx.line() });
  ctx.addShape(slide, { x: 798, y: 584, w: 72, h: 2, fill: "#A89773", line: ctx.line() });

  footer(slide, ctx, 4, false);
  return slide;
}
