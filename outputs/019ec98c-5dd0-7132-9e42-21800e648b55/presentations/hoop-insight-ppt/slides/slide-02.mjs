import { C, arrowText, bg, footer, kicker, nodeBox, title } from "./common.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "ARCHITECTURE", 72, 50);
  title(slide, ctx, "三层链路把 NBA 官方数据转成可交互分析。", 72, 82, 880);

  nodeBox(slide, ctx, {
    x: 72, y: 205, w: 320, h: 310, label: "前端展示层",
    body: "React + TypeScript + Vite\n\n8 个核心页面：总览、比赛、单场复盘、球员、球队、投篮、数据中心、智能问数\n\nReact SVG / CSS 图表：雷达图、投篮图、热区图、比分走势",
    accent: C.teal,
  });
  arrowText(slide, ctx, 416, 330);
  nodeBox(slide, ctx, {
    x: 474, y: 205, w: 320, h: 310, label: "在线后端层",
    body: "FastAPI 在线服务\n\n接口模块：比赛、球员、球队、投篮、数据中心、AI 问数\n\nService 层封装查询与业务逻辑；Analytics 层计算走势、关键时刻、热区、高级指标",
    accent: C.amber,
  });
  arrowText(slide, ctx, 820, 330);
  nodeBox(slide, ctx, {
    x: 878, y: 205, w: 320, h: 310, label: "数据处理层",
    body: "Python + pandas + nba_api\n\n拉取比赛、球员、球队、投篮和回合数据\n\n生成 raw / processed / cache 三层数据文件，兼顾溯源、展示与性能",
    accent: C.red,
  });

  const lanes = [
    ["页面路由", "React Router"],
    ["业务接口", "FastAPI Router"],
    ["分析计算", "pandas Analytics"],
    ["官方数据", "NBA.com endpoints"],
  ];
  lanes.forEach((l, i) => {
    const x = 146 + i * 260;
    ctx.addShape(slide, { x, y: 568, w: 178, h: 44, fill: "#FFFFFF0B", line: ctx.line("#FFFFFF18", 1), geometry: "roundRect" });
    ctx.addText(slide, { text: l[0], x: x + 14, y: 578, w: 70, h: 18, fontSize: 14, bold: true, color: C.white, typeface: "PingFang SC" });
    ctx.addText(slide, { text: l[1], x: x + 84, y: 578, w: 82, h: 18, fontSize: 13, color: C.muted, typeface: "Aptos", align: "right" });
  });

  footer(slide, ctx, 2);
  return slide;
}
