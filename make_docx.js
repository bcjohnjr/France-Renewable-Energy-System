// Render a JSON document spec to .docx with docx-js.  Usage: node make_docx.js spec.json out.docx
const fs = require('fs');
const path = require('path');
const d = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
        BorderStyle, ShadingType, ImageRun, Footer, PageNumber, LineNumberRestartFormat, PageBreak, LevelFormat } = d;

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = process.argv[3];
const FONT = spec.font || 'Times New Roman';
const SIZE = spec.size || 24;                 // half-points
const LINE = spec.double ? 480 : (spec.line || 300);
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1418;  // A4, 2.5 cm
const CONTENT_W = PAGE_W - 2 * MARGIN;

const para = (text, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { line: o.line || LINE, before: o.before ?? 0, after: o.after ?? 120 },
  keepNext: !!o.keepNext, indent: o.indent,
  numbering: o.bullet ? { reference: 'bullets', level: 0 } : undefined,
  children: (Array.isArray(text) ? text : [text]).map(t => typeof t === 'string'
    ? new TextRun({ text: t, font: FONT, size: o.size || SIZE, bold: o.bold, italics: o.italics, color: o.color })
    : t),
});

function table(t) {
  const ncol = t.header.length;
  const widths = t.widths || (ncol === 3 ? [0.5, 0.18, 0.32] : ncol === 4 ? [0.38, 0.14, 0.18, 0.30] : ncol === 5 ? [0.12, 0.22, 0.22, 0.22, 0.22] : Array(ncol).fill(1 / ncol));
  const cw = widths.map(w => Math.round(w * CONTENT_W));
  cw[cw.length - 1] = CONTENT_W - cw.slice(0, -1).reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: '9A9893' };
  const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
  const cell = (txt, i, head, last) => new TableCell({
    width: { size: cw[i], type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    shading: head ? { type: ShadingType.CLEAR, color: 'auto', fill: 'EEECE6' } : undefined,
    borders: { top: head ? border : none, bottom: (head || last) ? border : none, left: none, right: none },
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.LEFT, spacing: { line: 260, before: 0, after: 0 },
      children: [new TextRun({ text: String(txt), font: FONT, size: (spec.tableSize || 20), bold: head })] })],
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: cw,
    rows: [new TableRow({ tableHeader: true, children: t.header.map((h, i) => cell(h, i, true, false)) }),
           ...t.rows.map((r, j) => new TableRow({ children: r.map((v, i) => cell(v, i, false, j === t.rows.length - 1)) }))],
  });
}

function image(f) {
  const data = fs.readFileSync(f.path);
  const maxW = (spec.figWidthCm || 16) / 2.54 * 96;
  const w = Math.min(maxW, f.w), h = f.h * w / f.w;
  const maxH = 21 / 2.54 * 96;
  const s = h > maxH ? maxH / h : 1;
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 80 }, keepNext: true,
    children: [new ImageRun({ type: 'png', data, transformation: { width: Math.round(w * s), height: Math.round(h * s) } })] });
}

const children = [];
for (const b of spec.blocks) {
  switch (b.kind) {
    case 'articletype': children.push(para(b.text, { align: AlignmentType.CENTER, italics: true, color: '52514E', after: 120 })); break;
    case 'title': children.push(para(b.text, { align: AlignmentType.CENTER, bold: true, size: SIZE + 8, after: 240, line: Math.min(LINE, 360) })); break;
    case 'subtitle': children.push(para(b.text, { align: AlignmentType.CENTER, italics: true, size: SIZE, after: 200 })); break;
    case 'authors': children.push(para(b.text, { align: AlignmentType.CENTER, after: 120 })); break;
    case 'affil': children.push(para(b.text, { align: AlignmentType.CENTER, size: SIZE - 2, after: 40 })); break;
    case 'date': children.push(para(b.text, { align: AlignmentType.RIGHT, after: 240 })); break;
    case 'addr': b.text.split('\n').forEach((l, i, a) => children.push(para(l, { align: AlignmentType.LEFT, after: i === a.length - 1 ? 240 : 0 }))); break;
    case 'h1': children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, spacing: { before: 300, after: 120, line: Math.min(LINE, 360) },
      children: [new TextRun({ text: b.text, font: FONT, size: SIZE + 2, bold: true })] })); break;
    case 'h2': children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, spacing: { before: 200, after: 100, line: Math.min(LINE, 360) },
      children: [new TextRun({ text: b.text, font: FONT, size: SIZE, bold: true, italics: true })] })); break;
    case 'h': children.push(para(b.text, { bold: true, align: AlignmentType.LEFT, keepNext: true, before: 160, after: 60 })); break;
    case 'p': children.push(para(b.text)); break;
    case 'keywords': children.push(para(b.text, { align: AlignmentType.JUSTIFIED, italics: true, after: 200 })); break;
    case 'eq': children.push(para(b.text, { align: AlignmentType.CENTER, italics: true })); break;
    case 'bullet': children.push(para(b.text, { bullet: true, after: 60 })); break;
    case 'ref': children.push(para(b.text, { align: AlignmentType.JUSTIFIED, size: SIZE - 2, after: 60, indent: { left: 400, hanging: 400 } })); break;
    case 'pagebreak': children.push(new Paragraph({ children: [new PageBreak()] })); break;
    case 'table':
      if (b.newPage) children.push(new Paragraph({ children: [new PageBreak()] }));
      children.push(para(b.caption, { align: AlignmentType.JUSTIFIED, bold: false, italics: false, size: SIZE - 2, keepNext: true, after: 80, line: Math.min(LINE, 300) }));
      children.push(table(b));
      children.push(para('', { after: 120 }));
      break;
    case 'figure':
      if (b.newPage) children.push(new Paragraph({ children: [new PageBreak()] }));
      if (b.path) children.push(image(b));
      children.push(para(b.caption, { align: AlignmentType.JUSTIFIED, size: SIZE - 2, after: 200, line: Math.min(LINE, 300) }));
      break;
    default: throw new Error('unknown block ' + b.kind);
  }
}

const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, suppressLineNumbers: true,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })] });

const doc = new Document({
  creator: spec.creator || 'J.K. Bily, C. Pahl, P. Valdés Bacallao',
  title: spec.title || '', description: spec.description || '',
  styles: { default: { document: { run: { font: FONT, size: SIZE } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: SIZE + 2, bold: true }, paragraph: { spacing: { before: 300, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: SIZE, bold: true, italics: true }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 500, hanging: 260 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
      lineNumbers: spec.lineNumbers ? { countBy: 1, restart: LineNumberRestartFormat.CONTINUOUS, distance: 300 } : undefined },
    footers: { default: footer }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(out, buf); console.log('wrote', out); });
