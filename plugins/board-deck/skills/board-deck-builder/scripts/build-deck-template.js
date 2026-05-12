#!/usr/bin/env node
/**
 * MoxyWolf Board Deck Builder — Data-Driven Template
 *
 * Usage:  node build-deck-template.js <data.json> [output.pptx]
 *
 * Reads a JSON data file and generates a 10-slide MoxyWolf board deck.
 * All monthly data lives in the JSON; layout logic lives here.
 *
 * PPTX Design Rules (hard-won):
 *   - Never reuse option objects — PptxGenJS mutates them
 *   - Use makeShadow() factory, never a shared shadow object
 *   - Use { bullet: true }, never unicode bullets
 *   - Never put accent lines under slide titles
 *   - Never use emoji anywhere in slides
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// ── Args ──
const dataPath = process.argv[2];
if (!dataPath) {
  console.error("Usage: node build-deck-template.js <data.json> [output.pptx]");
  process.exit(1);
}

const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const outPath = process.argv[3] || path.join(
  path.dirname(dataPath),
  `MoxyWolf-Board-${D.meta.month}-${D.meta.year}.pptx`
);

// ── Brand Palette ──
const C = {
  orange: "FF6B35", dark: "1A1A2E", darkLight: "2D2D44",
  white: "FFFFFF", offWhite: "F5F5F5",
  gray: "6B7280", grayLight: "D1D5DB", grayMid: "9CA3AF",
  green: "10B981", greenBg: "ECFDF5",
  yellow: "F59E0B", yellowBg: "FFFBEB",
  red: "EF4444", redBg: "FEF2F2",
  blue: "3B82F6", blueBg: "EFF6FF",
  purpleBg: "F5F3FF",
};

const makeShadow = () => ({
  type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.12
});

const rowStyle = (bg) => ({ fill: { color: bg }, fontSize: 10, fontFace: "Calibri", color: "374151" });

// Resolve a color key — accepts "red", "green", etc. and returns the hex value
const resolveColor = (key) => C[key] || key;

// ── Presentation setup ──
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "MoxyWolf LLC";
pres.title = `MoxyWolf Board Report - ${D.meta.month} ${D.meta.year}`;

// ────────────────────────────────────────────────────
// SLIDE 1: Title
// ────────────────────────────────────────────────────
let s1 = pres.addSlide();
s1.background = { color: C.dark };
s1.addText("MOXYWOLF", {
  x: 0.5, y: 1.2, w: 9, h: 0.8,
  fontSize: 48, fontFace: "Arial Black", color: C.orange,
  align: "center", bold: true, charSpacing: 8
});
s1.addText("Board Report", {
  x: 0.5, y: 2.0, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Calibri", color: C.white, align: "center"
});
s1.addText(`${D.meta.month} ${D.meta.year}`, {
  x: 0.5, y: 2.7, w: 9, h: 0.5,
  fontSize: 20, fontFace: "Calibri", color: C.grayMid, align: "center"
});
s1.addShape(pres.shapes.RECTANGLE, {
  x: 3.5, y: 3.5, w: 3, h: 0.06, fill: { color: C.orange }
});
s1.addText(D.meta.tagline, {
  x: 0.5, y: 3.8, w: 9, h: 0.4,
  fontSize: 14, fontFace: "Calibri", color: C.grayMid, align: "center", italic: true
});
s1.addText("MoxyWolf LLC  \u2013  Confidential Board Materials", {
  x: 0, y: 5.1, w: 10, h: 0.4,
  fontSize: 9, fontFace: "Calibri", color: C.grayMid, align: "center"
});

// ────────────────────────────────────────────────────
// SLIDE 2: Executive Summary
// ────────────────────────────────────────────────────
let s2 = pres.addSlide();
s2.background = { color: C.offWhite };
s2.addText("Executive Summary", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

const summaryCards = [
  { label: "Monthly Headline", color: C.orange, bg: "FFF7ED", text: D.executiveSummary.headline },
  { label: "Biggest Learning", color: C.blue, bg: C.blueBg, text: D.executiveSummary.learning },
  { label: "Biggest Obstacle", color: C.red, bg: C.redBg, text: D.executiveSummary.obstacle },
  { label: "Next Month Priority", color: C.green, bg: C.greenBg, text: D.executiveSummary.priority },
];
summaryCards.forEach((c, i) => {
  const y = 1.15 + i * 1.1;
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 9, h: 0.95, fill: { color: c.bg }, shadow: makeShadow()
  });
  s2.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 0.08, h: 0.95, fill: { color: c.color }
  });
  s2.addText(c.label, {
    x: 0.8, y, w: 8.5, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: c.color, bold: true, margin: 0, valign: "bottom"
  });
  s2.addText(c.text, {
    x: 0.8, y: y + 0.32, w: 8.5, h: 0.55,
    fontSize: 11, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
  });
});

// ────────────────────────────────────────────────────
// SLIDE 3: Portfolio Dashboard
// ────────────────────────────────────────────────────
let s3 = pres.addSlide();
s3.background = { color: C.offWhite };
s3.addText("Portfolio Dashboard", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

const tblHeader = [
  { text: "Product", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
  { text: "TOF (Sessions)", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
  { text: "Dev Status", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
  { text: "Health", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 10, fontFace: "Calibri" } },
];

const tblRows = D.portfolio.map((p, i) => {
  const bg = i % 2 === 0 ? C.white : C.offWhite;
  const tofOpts = p.tofMuted
    ? { ...rowStyle(bg), color: C.grayMid, italic: true }
    : rowStyle(bg);
  const devOpts = p.devStatusMuted
    ? { ...rowStyle(bg), color: C.grayMid, italic: true }
    : rowStyle(bg);
  return [
    { text: p.name, options: { ...rowStyle(bg), bold: true } },
    { text: p.tof, options: tofOpts },
    { text: p.devStatus, options: devOpts },
    { text: p.health, options: { ...rowStyle(bg), align: "center", color: resolveColor(p.healthColor), bold: true } },
  ];
});

const rowHeights = [0.4, ...D.portfolio.map(() => 0.4)];
s3.addTable([tblHeader, ...tblRows], {
  x: 0.5, y: 1.1, w: 9, h: 2.6,
  colW: [1.6, 2.0, 4.0, 1.0],
  border: { pt: 0.5, color: C.grayLight },
  rowH: rowHeights,
});

// Portfolio North Star section
const ns = D.northStar;
const nsY = 3.85;

// Full-width North Star container
s3.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: nsY, w: 9, h: 1.5, fill: { color: C.dark }, shadow: makeShadow(),
  rectRadius: 0.05
});

// "Portfolio North Star" label
s3.addText("Portfolio North Star", {
  x: 0.75, y: nsY + 0.08, w: 3.5, h: 0.3,
  fontSize: 11, fontFace: "Calibri", color: C.orange, bold: true, margin: 0
});

// Formula subtitle
s3.addText(ns.formula, {
  x: 0.75, y: nsY + 0.35, w: 3.5, h: 0.25,
  fontSize: 9, fontFace: "Calibri", color: C.grayMid, italic: true, margin: 0
});

// Current Score — big number
s3.addText(ns.currentScore, {
  x: 0.75, y: nsY + 0.6, w: 2.0, h: 0.7,
  fontSize: 36, fontFace: "Arial Black", color: resolveColor(ns.scoreColor), align: "left", valign: "middle", margin: 0
});
s3.addText("Current Score", {
  x: 0.75, y: nsY + 1.2, w: 2.0, h: 0.2,
  fontSize: 8, fontFace: "Calibri", color: C.grayMid, align: "left", margin: 0
});

// Target card
s3.addShape(pres.shapes.RECTANGLE, {
  x: 3.2, y: nsY + 0.6, w: 2.0, h: 0.8, fill: { color: C.darkLight }, rectRadius: 0.05
});
s3.addText(ns.target, {
  x: 3.2, y: nsY + 0.6, w: 2.0, h: 0.5,
  fontSize: 20, fontFace: "Arial Black", color: C.white, align: "center", valign: "middle", margin: 0
});
s3.addText("Target", {
  x: 3.2, y: nsY + 1.05, w: 2.0, h: 0.25,
  fontSize: 8, fontFace: "Calibri", color: C.grayMid, align: "center", margin: 0
});

// Products Scoring card
s3.addShape(pres.shapes.RECTANGLE, {
  x: 5.5, y: nsY + 0.6, w: 2.0, h: 0.8, fill: { color: C.darkLight }, rectRadius: 0.05
});
s3.addText(ns.productsScoring, {
  x: 5.5, y: nsY + 0.6, w: 2.0, h: 0.5,
  fontSize: 20, fontFace: "Arial Black", color: resolveColor(ns.productsScoringColor), align: "center", valign: "middle", margin: 0
});
s3.addText("Products Scoring <0.75", {
  x: 5.5, y: nsY + 1.05, w: 2.0, h: 0.25,
  fontSize: 8, fontFace: "Calibri", color: C.grayMid, align: "center", margin: 0
});

// Trend card
s3.addShape(pres.shapes.RECTANGLE, {
  x: 7.8, y: nsY + 0.6, w: 1.5, h: 0.8, fill: { color: C.darkLight }, rectRadius: 0.05
});
const trendColor = ns.trend === "Up" ? C.green : ns.trend === "Down" ? C.red : C.grayMid;
const trendArrow = ns.trend === "Up" ? "\u25B2" : ns.trend === "Down" ? "\u25BC" : "\u25C6";
s3.addText([
  { text: trendArrow + " ", options: { fontSize: 14, color: trendColor } },
  { text: ns.trend, options: { fontSize: 14, color: trendColor } }
], {
  x: 7.8, y: nsY + 0.6, w: 1.5, h: 0.5,
  fontFace: "Arial Black", align: "center", valign: "middle", margin: 0
});
s3.addText("Trend", {
  x: 7.8, y: nsY + 1.05, w: 1.5, h: 0.25,
  fontSize: 8, fontFace: "Calibri", color: C.grayMid, align: "center", margin: 0
});

// ────────────────────────────────────────────────────
// SLIDE 4: Capital & Burn
// ────────────────────────────────────────────────────
let s4 = pres.addSlide();
s4.background = { color: C.offWhite };
s4.addText("Capital & Burn", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

D.financials.leftCards.forEach((c, i) => {
  const y = 1.15 + i * 1.0;
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 4.3, h: 0.85, fill: { color: C.white }, shadow: makeShadow()
  });
  s4.addText(c.label, {
    x: 0.75, y, w: 3.8, h: 0.35,
    fontSize: 10, fontFace: "Calibri", color: C.gray, margin: 0, valign: "bottom"
  });
  s4.addText(c.value, {
    x: 0.75, y: y + 0.32, w: 3.8, h: 0.45,
    fontSize: 18, fontFace: "Arial Black", color: resolveColor(c.valueColor), margin: 0, valign: "top"
  });
});

D.financials.rightSections.forEach((sec, i) => {
  const y = 1.15 + i * 1.35;
  s4.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y, w: 4.3, h: 1.2, fill: { color: resolveColor(sec.bgColor) }, shadow: makeShadow()
  });
  s4.addText(sec.title, {
    x: 5.45, y, w: 3.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.dark, bold: true, margin: 0, valign: "bottom"
  });
  s4.addText(sec.items.map((item, idx) => ({
    text: item,
    options: { breakLine: idx < sec.items.length - 1, fontSize: 9, fontFace: "Calibri", color: "374151", bullet: true }
  })), {
    x: 5.45, y: y + 0.35, w: 3.8, h: 0.8, margin: 0, valign: "top"
  });
});

// ────────────────────────────────────────────────────
// SLIDE 5: STIGViewer OKRs
// ────────────────────────────────────────────────────
let s5 = pres.addSlide();
s5.background = { color: C.offWhite };
s5.addText("Product OKRs: STIGViewer", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

// Helper: turn data items into PptxGenJS text array
function makeItems(items) {
  return items.map((item, idx) => {
    const raw = typeof item === "string" ? { text: item } : item;
    const opts = { breakLine: idx < items.length - 1, fontSize: 10, bullet: true };
    if (raw.highlight) { opts.color = resolveColor(raw.highlightColor); opts.bold = true; }
    if (raw.muted) { opts.color = C.grayMid; opts.italic = true; }
    if (raw.bold) { opts.bold = true; }
    return { text: raw.text || raw, options: opts };
  });
}

// KR1 Marketing
s5.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 4.3, h: 2.0, fill: { color: C.white }, shadow: makeShadow() });
s5.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 0.08, h: 2.0, fill: { color: C.blue } });
s5.addText("KR1: Marketing & Sales", {
  x: 0.8, y: 1.15, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.blue, bold: true, margin: 0
});
s5.addText(makeItems(D.stigviewerOKRs.kr1Marketing.items), {
  x: 0.8, y: 1.5, w: 3.8, h: 1.5, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// KR2 Development
s5.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.25, w: 4.3, h: 1.9, fill: { color: C.white }, shadow: makeShadow() });
s5.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.25, w: 0.08, h: 1.9, fill: { color: resolveColor(D.stigviewerOKRs.kr2Dev.labelColor) } });
s5.addText(D.stigviewerOKRs.kr2Dev.label, {
  x: 0.8, y: 3.3, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: resolveColor(D.stigviewerOKRs.kr2Dev.labelColor), bold: true, margin: 0
});
s5.addText(makeItems(D.stigviewerOKRs.kr2Dev.items), {
  x: 0.8, y: 3.65, w: 3.8, h: 1.4, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// KR3 Operations
s5.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 1.8, fill: { color: C.white }, shadow: makeShadow() });
s5.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 0.08, h: 1.8, fill: { color: resolveColor(D.stigviewerOKRs.kr3Ops.labelColor) } });
s5.addText(D.stigviewerOKRs.kr3Ops.label, {
  x: 5.5, y: 1.15, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: resolveColor(D.stigviewerOKRs.kr3Ops.labelColor), bold: true, margin: 0
});
s5.addText(makeItems(D.stigviewerOKRs.kr3Ops.items), {
  x: 5.5, y: 1.5, w: 3.8, h: 1.3, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// Channel breakdown
s5.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 3.1, w: 4.3, h: 2.05, fill: { color: C.white }, shadow: makeShadow() });
s5.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 3.1, w: 0.08, h: 2.05, fill: { color: C.orange } });
s5.addText("Traffic Channels", {
  x: 5.5, y: 3.15, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.orange, bold: true, margin: 0
});
s5.addText(makeItems(D.stigviewerOKRs.channels), {
  x: 5.5, y: 3.5, w: 3.8, h: 1.55, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// ────────────────────────────────────────────────────
// SLIDE 6: PRFAQ OKRs
// ────────────────────────────────────────────────────
let s6 = pres.addSlide();
s6.background = { color: C.offWhite };
s6.addText("Product OKRs: PRFAQ", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

// KR1 Marketing (left)
s6.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 4.3, h: 2.2, fill: { color: C.white }, shadow: makeShadow() });
s6.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 0.08, h: 2.2, fill: { color: C.green } });
s6.addText("KR1: Marketing & Traffic", {
  x: 0.8, y: 1.15, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.green, bold: true, margin: 0
});
s6.addText(D.prfaqOKRs.kr1Marketing.bigStat, {
  x: 0.8, y: 1.55, w: 1.2, h: 0.6,
  fontSize: 36, fontFace: "Arial Black", color: C.green, margin: 0
});
s6.addText(D.prfaqOKRs.kr1Marketing.bigStatSub, {
  x: 2.0, y: 1.55, w: 2.8, h: 0.6,
  fontSize: 11, fontFace: "Calibri", color: C.gray, margin: 0, valign: "middle"
});
s6.addText(makeItems(D.prfaqOKRs.kr1Marketing.items), {
  x: 0.8, y: 2.25, w: 3.8, h: 1.0, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// KR2 Development (left bottom)
s6.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.5, w: 4.3, h: 1.6, fill: { color: C.white }, shadow: makeShadow() });
s6.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.5, w: 0.08, h: 1.6, fill: { color: C.yellow } });
s6.addText("KR2: Development", {
  x: 0.8, y: 3.55, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.yellow, bold: true, margin: 0
});
s6.addText(D.prfaqOKRs.kr2Dev.placeholder, {
  x: 0.8, y: 3.95, w: 3.8, h: 0.4,
  fontSize: 10, fontFace: "Calibri", color: C.grayMid, italic: true, margin: 0
});

// Right — Product context
s6.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 4.0, fill: { color: C.white }, shadow: makeShadow() });
s6.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 0.08, h: 4.0, fill: { color: C.orange } });
s6.addText("Product Context", {
  x: 5.5, y: 1.15, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.orange, bold: true, margin: 0
});
s6.addText(makeItems(D.prfaqOKRs.productContext), {
  x: 5.5, y: 1.55, w: 3.8, h: 1.6, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});
s6.addShape(pres.shapes.RECTANGLE, { x: 5.5, y: 3.3, w: 3.7, h: 0.04, fill: { color: C.grayLight } });
s6.addText("Key Actions", {
  x: 5.5, y: 3.45, w: 3.8, h: 0.35,
  fontSize: 12, fontFace: "Calibri", color: C.dark, bold: true, margin: 0
});
s6.addText(makeItems(D.prfaqOKRs.keyActions), {
  x: 5.5, y: 3.85, w: 3.8, h: 1.0, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// ────────────────────────────────────────────────────
// SLIDE 7: SAMS + RegGenome OKRs
// ────────────────────────────────────────────────────
let s7 = pres.addSlide();
s7.background = { color: C.offWhite };
s7.addText("Product OKRs: SAMS & RegGenome", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

// SAMS (left)
s7.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 4.3, h: 4.0, fill: { color: C.white }, shadow: makeShadow() });
s7.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 0.08, h: 4.0, fill: { color: C.yellow } });
s7.addText("SAMS", {
  x: 0.8, y: 1.15, w: 3.8, h: 0.4,
  fontSize: 16, fontFace: "Arial Black", color: C.dark, margin: 0
});
s7.addText(D.samsOKRs.devLabel, {
  x: 0.8, y: 1.6, w: 3.8, h: 0.3,
  fontSize: 12, fontFace: "Calibri", color: resolveColor(D.samsOKRs.devLabelColor), bold: true, margin: 0
});
s7.addText(makeItems(D.samsOKRs.devItems), {
  x: 0.8, y: 1.95, w: 3.8, h: 1.2, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});
s7.addText(D.samsOKRs.opsLabel, {
  x: 0.8, y: 3.2, w: 3.8, h: 0.3,
  fontSize: 12, fontFace: "Calibri", color: resolveColor(D.samsOKRs.opsLabelColor), bold: true, margin: 0
});
s7.addText(makeItems(D.samsOKRs.opsItems), {
  x: 0.8, y: 3.55, w: 3.8, h: 0.8, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});
s7.addText(D.samsOKRs.footer, {
  x: 0.8, y: 4.5, w: 3.8, h: 0.4,
  fontSize: 9, fontFace: "Calibri", color: C.grayMid, italic: true, margin: 0
});

// RegGenome (right)
s7.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 4.0, fill: { color: C.white }, shadow: makeShadow() });
s7.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.1, w: 0.08, h: 4.0, fill: { color: C.green } });
s7.addText("RegGenome", {
  x: 5.5, y: 1.15, w: 3.8, h: 0.4,
  fontSize: 16, fontFace: "Arial Black", color: C.dark, margin: 0
});
s7.addText("Development", {
  x: 5.5, y: 1.6, w: 3.8, h: 0.3,
  fontSize: 12, fontFace: "Calibri", color: C.dark, bold: true, margin: 0
});
s7.addText(makeItems(D.reggenomeOKRs.devItems), {
  x: 5.5, y: 1.95, w: 3.8, h: 0.8, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});
s7.addText(D.reggenomeOKRs.footer, {
  x: 5.5, y: 4.5, w: 3.8, h: 0.4,
  fontSize: 9, fontFace: "Calibri", color: C.grayMid, italic: true, margin: 0
});

// ────────────────────────────────────────────────────
// SLIDE 8: Sprint Detail
// ────────────────────────────────────────────────────
let s8 = pres.addSlide();
s8.background = { color: C.offWhite };
s8.addText(D.sprint.title, {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});
s8.addText(D.sprint.dates, {
  x: 0.5, y: 0.95, w: 9, h: 0.3,
  fontSize: 12, fontFace: "Calibri", color: C.gray, margin: 0
});

// Progress bar
s8.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.4, w: 9, h: 0.25, fill: { color: C.grayLight } });
s8.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.4, w: 9 * D.sprint.velocityPct, h: 0.25, fill: { color: C.orange } });
s8.addText(D.sprint.velocityLabel, {
  x: 0.5, y: 1.4, w: 9, h: 0.25,
  fontSize: 10, fontFace: "Calibri", color: C.white, bold: true, align: "center", valign: "middle", margin: 0
});

// Sprint KPIs
D.sprint.kpis.forEach((k, i) => {
  const x = 0.5 + i * 1.85;
  s8.addShape(pres.shapes.RECTANGLE, {
    x, y: 1.9, w: 1.65, h: 0.9, fill: { color: C.white }, shadow: makeShadow()
  });
  s8.addText(k.value, {
    x, y: 1.92, w: 1.65, h: 0.5,
    fontSize: 28, fontFace: "Arial Black", color: resolveColor(k.color), align: "center", valign: "middle", margin: 0
  });
  s8.addText(k.label, {
    x, y: 2.45, w: 1.65, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.gray, align: "center", margin: 0
  });
});

// Done tasks
s8.addText("Completed Tasks", {
  x: 0.5, y: 3.05, w: 9, h: 0.35,
  fontSize: 14, fontFace: "Calibri", color: C.dark, bold: true, margin: 0
});
s8.addText(D.sprint.doneTasks.map((t, idx) => ({
  text: t,
  options: { breakLine: idx < D.sprint.doneTasks.length - 1, fontSize: 10, fontFace: "Calibri", color: "374151", bullet: true }
})), {
  x: 0.7, y: 3.4, w: 4.3, h: 2.0, margin: 0, valign: "top"
});

// In-progress
s8.addText("In Progress", {
  x: 5.2, y: 3.05, w: 4.3, h: 0.35,
  fontSize: 14, fontFace: "Calibri", color: C.dark, bold: true, margin: 0
});
s8.addText(D.sprint.inProgress.map((t, idx) => ({
  text: t,
  options: { breakLine: idx < D.sprint.inProgress.length - 1, fontSize: 10, bullet: true }
})), {
  x: 5.4, y: 3.4, w: 4.1, h: 0.7, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// To Do
s8.addText("To Do", {
  x: 5.2, y: 4.2, w: 4.3, h: 0.35,
  fontSize: 14, fontFace: "Calibri", color: C.dark, bold: true, margin: 0
});
s8.addText(D.sprint.toDo.map((t, idx) => ({
  text: t,
  options: { breakLine: idx < D.sprint.toDo.length - 1, fontSize: 10, bullet: true }
})), {
  x: 5.4, y: 4.55, w: 4.1, h: 0.4, fontFace: "Calibri", color: "374151", margin: 0, valign: "top"
});

// ────────────────────────────────────────────────────
// SLIDE 9: Risk Register
// ────────────────────────────────────────────────────
let s9 = pres.addSlide();
s9.background = { color: C.offWhite };
s9.addText("Risk Register", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

const riskHdr = [
  { text: "Pri", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 9, fontFace: "Calibri", align: "center" } },
  { text: "Category", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 9, fontFace: "Calibri" } },
  { text: "Risk Description", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 9, fontFace: "Calibri" } },
  { text: "Mitigation", options: { fill: { color: C.dark }, color: C.white, bold: true, fontSize: 9, fontFace: "Calibri" } },
];

const riskRows = D.risks.map((r, i) => {
  const bg = i % 2 === 0 ? C.white : C.offWhite;
  return [
    { text: r.priority, options: { fill: { color: bg }, fontSize: 9, fontFace: "Calibri", color: resolveColor(r.color), bold: true, align: "center" } },
    { text: r.category, options: { fill: { color: bg }, fontSize: 9, fontFace: "Calibri", color: "374151" } },
    { text: r.description, options: { fill: { color: bg }, fontSize: 9, fontFace: "Calibri", color: "374151" } },
    { text: r.mitigation, options: { fill: { color: bg }, fontSize: 9, fontFace: "Calibri", color: "374151" } },
  ];
});

const riskRowH = [0.35, ...D.risks.map(() => 0.55)];
s9.addTable([riskHdr, ...riskRows], {
  x: 0.5, y: 1.1, w: 9,
  colW: [0.6, 1.0, 4.2, 3.2],
  border: { pt: 0.5, color: C.grayLight },
  rowH: riskRowH,
});

const priLegend = [
  { label: "P0 (Critical)", text: "Immediate threat", bg: C.redBg, color: C.red },
  { label: "P1 (High)", text: "Address within 30 days", bg: C.yellowBg, color: C.yellow },
  { label: "P2 (Medium)", text: "Monitor within quarter", bg: C.blueBg, color: C.blue },
];
priLegend.forEach((p, i) => {
  const x = 0.5 + i * 3.1;
  s9.addShape(pres.shapes.RECTANGLE, {
    x, y: 4.3, w: 2.9, h: 0.7, fill: { color: p.bg }, shadow: makeShadow()
  });
  s9.addText(p.label, {
    x, y: 4.32, w: 2.9, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: p.color, bold: true, align: "center", margin: 0
  });
  s9.addText(p.text, {
    x, y: 4.62, w: 2.9, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.gray, align: "center", margin: 0
  });
});

// ────────────────────────────────────────────────────
// SLIDE 10: Strategic Decisions
// ────────────────────────────────────────────────────
let s10 = pres.addSlide();
s10.background = { color: C.offWhite };
s10.addText("Strategic Decisions / Board Input", {
  x: 0.5, y: 0.3, w: 9, h: 0.6,
  fontSize: 28, fontFace: "Arial Black", color: C.dark, bold: true, margin: 0
});

D.decisions.forEach((d, i) => {
  const y = 1.1 + i * 1.45;
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 9, h: 1.3, fill: { color: C.white }, shadow: makeShadow()
  });
  s10.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y, w: 0.08, h: 1.3, fill: { color: resolveColor(d.color) }
  });
  s10.addText("Decision " + (i + 1) + ": " + d.title, {
    x: 0.8, y, w: 8.5, h: 0.35,
    fontSize: 13, fontFace: "Calibri", color: resolveColor(d.color), bold: true, margin: 0, valign: "bottom"
  });
  s10.addText([
    { text: "Context: ", options: { bold: true, fontSize: 10, color: C.gray } },
    { text: d.context, options: { fontSize: 10, color: "374151", breakLine: true } },
    { text: "Recommendation: ", options: { bold: true, fontSize: 10, color: C.gray } },
    { text: d.recommendation, options: { fontSize: 10, color: "374151" } },
  ], {
    x: 0.8, y: y + 0.35, w: 8.5, h: 0.85, fontFace: "Calibri", margin: 0, valign: "top"
  });
});

// Footer on all slides (2-10)
[s2, s3, s4, s5, s6, s7, s8, s9, s10].forEach(s => {
  s.addText("MoxyWolf LLC  \u2013  Confidential Board Materials", {
    x: 0, y: 5.25, w: 10, h: 0.3,
    fontSize: 8, fontFace: "Calibri", color: C.grayMid, align: "center"
  });
});

// ── Write file ──
pres.writeFile({ fileName: outPath }).then(() => {
  console.log("PPTX saved to:", outPath);
}).catch(err => {
  console.error("Error:", err);
});
