export const C = {
  ink: "#0B1020",
  ink2: "#121A2D",
  ink3: "#1B2740",
  paper: "#F6F0E4",
  paper2: "#FFF8EA",
  amber: "#F59E0B",
  teal: "#22C7A9",
  red: "#EF4444",
  blue: "#60A5FA",
  green: "#84CC16",
  text: "#E5E7EB",
  muted: "#94A3B8",
  dim: "#5B677A",
  white: "#FFFFFF",
};

export function bg(slide, ctx, fill = C.ink) {
  ctx.addShape(slide, { x: 0, y: 0, w: 1280, h: 720, fill, line: ctx.line() });
}

export function footer(slide, ctx, n, dark = true) {
  const color = dark ? C.muted : "#6B5F4A";
  ctx.addShape(slide, { x: 72, y: 676, w: 1040, h: 1, fill: dark ? "#273449" : "#D9CDB5", line: ctx.line() });
  ctx.addText(slide, {
    text: "Hoop Insight · NBA 篮球数据分析与智能问数系统",
    x: 72, y: 685, w: 700, h: 20, fontSize: 12, color,
    typeface: "PingFang SC",
  });
  ctx.addText(slide, {
    text: String(n).padStart(2, "0"),
    x: 1160, y: 681, w: 48, h: 26, fontSize: 15, bold: true, color,
    align: "right", typeface: "Aptos",
  });
}

export function kicker(slide, ctx, text, x, y, dark = true) {
  ctx.addShape(slide, { x, y: y + 7, w: 30, h: 3, fill: C.amber, line: ctx.line() });
  ctx.addText(slide, {
    text,
    x: x + 42, y, w: 360, h: 22, fontSize: 13, bold: true,
    color: dark ? C.teal : "#167F72", typeface: "Aptos",
  });
}

export function title(slide, ctx, text, x = 72, y = 72, w = 900, dark = true) {
  ctx.addText(slide, {
    text,
    x, y, w, h: 92, fontSize: 38, bold: true,
    color: dark ? C.white : C.ink, typeface: "PingFang SC",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function small(slide, ctx, text, x, y, w, h, color = C.muted, size = 16, bold = false) {
  return ctx.addText(slide, {
    text, x, y, w, h, fontSize: size, color, bold,
    typeface: "PingFang SC", insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function pill(slide, ctx, text, x, y, w, fill, color = C.white) {
  ctx.addShape(slide, { x, y, w, h: 30, fill, line: ctx.line("#00000000", 0), geometry: "roundRect" });
  ctx.addText(slide, {
    text, x: x + 12, y: y + 5, w: w - 24, h: 20, fontSize: 13,
    bold: true, color, typeface: "PingFang SC", align: "center",
  });
}

export function nodeBox(slide, ctx, { x, y, w, h, label, body, fill = C.ink2, stroke = "#31415F", accent = C.teal, dark = true }) {
  ctx.addShape(slide, { x, y, w, h, fill, line: ctx.line(stroke, 1), geometry: "roundRect" });
  ctx.addShape(slide, { x, y, w: 5, h, fill: accent, line: ctx.line() });
  ctx.addText(slide, {
    text: label, x: x + 22, y: y + 16, w: w - 34, h: 28, fontSize: 22, bold: true,
    color: dark ? C.white : C.ink, typeface: "PingFang SC",
  });
  ctx.addText(slide, {
    text: body, x: x + 22, y: y + 54, w: w - 34, h: h - 66, fontSize: 16,
    color: dark ? C.muted : "#5C5348", typeface: "PingFang SC",
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function arrowText(slide, ctx, x, y, color = C.amber) {
  ctx.addText(slide, {
    text: "→", x, y, w: 48, h: 44, fontSize: 34, bold: true,
    color, typeface: "Aptos", align: "center", valign: "middle",
  });
}

export function miniCourt(slide, ctx, x, y, scale = 1, color = "#FFFFFF33") {
  const w = 270 * scale;
  const h = 230 * scale;
  ctx.addShape(slide, { x, y, w, h, fill: "#00000000", line: ctx.line(color, 2) });
  ctx.addShape(slide, { x: x + 85 * scale, y, w: 100 * scale, h: 78 * scale, fill: "#00000000", line: ctx.line(color, 2) });
  ctx.addShape(slide, { x: x + 110 * scale, y: y + 50 * scale, w: 50 * scale, h: 50 * scale, fill: "#00000000", line: ctx.line(color, 2), geometry: "ellipse" });
  ctx.addShape(slide, { x: x + 118 * scale, y: y + 32 * scale, w: 34 * scale, h: 4 * scale, fill: color, line: ctx.line() });
  ctx.addShape(slide, { x: x + 96 * scale, y: y + 88 * scale, w: 78 * scale, h: 78 * scale, fill: "#00000000", line: ctx.line(color, 2), geometry: "ellipse" });
  ctx.addShape(slide, { x: x + 36 * scale, y: y + 34 * scale, w: 198 * scale, h: 198 * scale, fill: "#00000000", line: ctx.line(color, 2), geometry: "ellipse" });
}

export function dot(slide, ctx, x, y, fill, s = 8) {
  ctx.addShape(slide, { x, y, w: s, h: s, fill, line: ctx.line("#00000000", 0), geometry: "ellipse" });
}
