import { C, bg, footer, kicker, small, title } from "./common.mjs";

function apiNode(slide, ctx, x, y, w, h, name, desc, color) {
  ctx.addShape(slide, { x, y, w, h, fill: "#101827", line: ctx.line(color, 1.4), geometry: "roundRect" });
  ctx.addText(slide, { text: name, x: x + 16, y: y + 13, w: w - 32, h: 24, fontSize: 18, bold: true, color: C.white, typeface: "Aptos" });
  ctx.addText(slide, { text: desc, x: x + 16, y: y + 45, w: w - 32, h: h - 56, fontSize: 14, color: C.muted, typeface: "PingFang SC" });
}

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "NBA OFFICIAL DATA", 72, 50);
  title(slide, ctx, "nba_api 是比赛、球员、球队、投篮和回合数据的统一入口。", 72, 82, 980);

  ctx.addShape(slide, { x: 470, y: 244, w: 340, h: 166, fill: "linear(135deg, #17213A, #0F766E)", line: ctx.line("#22C7A9", 2), geometry: "roundRect" });
  ctx.addText(slide, { text: "nba_api", x: 505, y: 278, w: 270, h: 46, fontSize: 40, bold: true, color: C.white, typeface: "Aptos Display", align: "center" });
  ctx.addText(slide, { text: "Python API Client\n访问 NBA.com 官方数据接口", x: 510, y: 335, w: 260, h: 48, fontSize: 18, color: C.paper, typeface: "PingFang SC", align: "center" });

  apiNode(slide, ctx, 70, 205, 300, 96, "LeagueGameLog", "获取赛季比赛日志；支持常规赛 / 季后赛记录", C.amber);
  apiNode(slide, ctx, 70, 340, 300, 112, "LeagueDashPlayerStats", "获取球员基础数据与高级数据，用于榜单和对比", C.teal);
  apiNode(slide, ctx, 70, 492, 300, 96, "LeagueDashTeamStats", "获取球队基础、高级、四要素、防守和对手数据", C.blue);

  apiNode(slide, ctx, 910, 205, 300, 112, "ShotChartDetail", "获取球员 / 球队投篮坐标和投篮区域数据", C.red);
  apiNode(slide, ctx, 910, 358, 300, 96, "PlayByPlayV3", "获取单场比赛逐回合事件流，用于走势和关键时刻", C.green);
  apiNode(slide, ctx, 910, 492, 300, 96, "BoxScoreTraditionalV2", "获取单场球员技术统计，支撑复盘与影响力分析", C.amber);

  [["370", "252", "470", "306"], ["370", "396", "470", "330"], ["370", "540", "470", "356"], ["810", "306", "910", "252"], ["810", "330", "910", "404"], ["810", "356", "910", "540"]].forEach(([x1, y1, x2, y2]) => {
    const y = Number(y1);
    ctx.addShape(slide, { x: Number(x1), y, w: Math.abs(Number(x2) - Number(x1)), h: 2, fill: "#FFFFFF24", line: ctx.line() });
  });

  small(slide, ctx, "接口层覆盖“赛季级统计 + 单场级事件 + 空间投篮坐标”，因此既能做榜单，也能做单场复盘和投篮区域分析。", 445, 470, 390, 56, C.muted, 16);
  footer(slide, ctx, 3);
  return slide;
}
