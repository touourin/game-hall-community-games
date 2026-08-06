const fs = require('fs/promises');
const path = require('path');
const sharp = require('sharp');

const outDir = __dirname;
const fontStack = "'Microsoft YaHei','Noto Sans CJK SC','Source Han Sans SC',Arial,sans-serif";

const priceLadder = [
  10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42,
  46, 52, 56, 62, 68, 76, 84, 92, 100, 110, 122, 134, 146, 162, 178, 196, 216,
  238, 262, 286, 312, 338, 366, 394, 424, 454, 486, 518, 552, 586, 622, 658, 696, 734,
];

if (priceLadder.length !== 51 || priceLadder[25] !== 100 || priceLadder.some((value) => value % 2 !== 0)) {
  throw new Error('Price ladder must contain 51 even values and place 100 at grid 26.');
}

function trackSvg(kind) {
  const isSpot = kind === 'spot';
  const width = 3600;
  const height = 620;
  const left = 240;
  const cellWidth = 64;
  const trackY = 224;
  const trackHeight = 174;
  const accent = isSpot ? '#087A88' : '#C96632';
  const accent2 = isSpot ? '#34B3B1' : '#E9A45F';
  const headerA = isSpot ? '#075E6C' : '#102A43';
  const headerB = isSpot ? '#0B8790' : '#244760';
  const title = isSpot ? '现货价格' : '期货价格';
  const subtitle = isSpot ? '真实价值 · 由信息与事件推动' : '市场成交价 · 由玩家竞价形成';
  const rule = isSpot ? '现货不设涨跌幅上限' : '单轮竞价范围：开盘价上下各 3 格';
  const badge = isSpot ? '结算回归基准' : '成交与持仓基准';

  const cells = priceLadder.map((value, index) => {
    const grid = index + 1;
    const x = left + index * cellWidth;
    const zoneFill = grid <= 17 ? '#E7F4F6' : grid <= 34 ? '#F1F3F4' : '#FFF0D5';
    const alt = index % 2 === 0 ? 0.84 : 1;
    const isCenter = grid === 26;
    const valueSize = value >= 100 ? 23 : 25;
    return `
      <g>
        <rect x="${x}" y="${trackY}" width="${cellWidth}" height="${trackHeight}" fill="${zoneFill}" fill-opacity="${alt}"/>
        ${isCenter ? `<rect x="${x + 3}" y="${trackY + 3}" width="${cellWidth - 6}" height="${trackHeight - 6}" rx="10" fill="${accent}" opacity="0.16"/><path d="M${x + cellWidth / 2 - 10} ${trackY - 16}h20l-10 12z" fill="${accent}"/>` : ''}
        <line x1="${x}" y1="${trackY}" x2="${x}" y2="${trackY + trackHeight}" stroke="#8BA6AD" stroke-width="1" opacity="0.64"/>
        <text x="${x + cellWidth / 2}" y="${trackY + 74}" text-anchor="middle" font-family="${fontStack}" font-size="${valueSize}" font-weight="800" fill="#173247">${value}</text>
        <text x="${x + cellWidth / 2}" y="${trackY + 129}" text-anchor="middle" font-family="${fontStack}" font-size="17" font-weight="600" fill="#637986">${String(grid).padStart(2, '0')}</text>
        <circle cx="${x + cellWidth / 2}" cy="${trackY + 151}" r="4.5" fill="${isCenter ? accent : '#89A0A8'}"/>
      </g>`;
  }).join('');

  const endX = left + priceLadder.length * cellWidth;
  const zones = [
    { label: '低价区', x: left, count: 17, fill: '#BFE5E8' },
    { label: '中价区', x: left + 17 * cellWidth, count: 17, fill: '#D8DEE2' },
    { label: '高价区', x: left + 34 * cellWidth, count: 17, fill: '#F2D096' },
  ].map((zone) => {
    const zoneWidth = zone.count * cellWidth;
    return `<g>
      <rect x="${zone.x}" y="420" width="${zoneWidth}" height="52" rx="13" fill="${zone.fill}"/>
      <text x="${zone.x + zoneWidth / 2}" y="453" text-anchor="middle" font-family="${fontStack}" font-size="22" font-weight="800" fill="#173247">${zone.label}</text>
    </g>`;
  }).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="header" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="${headerA}"/>
      <stop offset="1" stop-color="${headerB}"/>
    </linearGradient>
    <pattern id="microGrid" width="36" height="36" patternUnits="userSpaceOnUse">
      <path d="M36 0H0V36" fill="none" stroke="#FFFFFF" stroke-width="1" opacity="0.06"/>
    </pattern>
    <filter id="shadow" x="-10%" y="-20%" width="120%" height="150%">
      <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#0B2235" flood-opacity="0.20"/>
    </filter>
  </defs>
  <rect width="${width}" height="${height}" fill="#EEF2F3"/>
  <rect x="30" y="30" width="3540" height="560" rx="30" fill="#FBFAF5" stroke="#D4DFE2" stroke-width="3" filter="url(#shadow)"/>
  <path d="M30 60Q30 30 60 30H3540Q3570 30 3570 60V178H30Z" fill="url(#header)"/>
  <path d="M30 60Q30 30 60 30H3540Q3570 30 3570 60V178H30Z" fill="url(#microGrid)"/>
  <rect x="55" y="56" width="10" height="96" rx="5" fill="${accent2}"/>
  <text x="92" y="101" font-family="${fontStack}" font-size="48" font-weight="900" fill="#FFFFFF">${title}</text>
  <text x="94" y="143" font-family="${fontStack}" font-size="23" font-weight="500" fill="#DCEFF0">${subtitle}</text>
  <rect x="2980" y="72" width="520" height="64" rx="32" fill="#FFFFFF" opacity="0.13" stroke="#FFFFFF" stroke-width="2"/>
  <text x="3240" y="113" text-anchor="middle" font-family="${fontStack}" font-size="25" font-weight="800" fill="#FFFFFF">${badge}</text>

  <g>
    <rect x="70" y="224" width="142" height="174" rx="18" fill="#173247"/>
    <text x="141" y="274" text-anchor="middle" font-family="${fontStack}" font-size="20" font-weight="700" fill="#BFD9DE">格位</text>
    <text x="141" y="326" text-anchor="middle" font-family="${fontStack}" font-size="40" font-weight="900" fill="#FFFFFF">51</text>
    <text x="141" y="365" text-anchor="middle" font-family="${fontStack}" font-size="17" font-weight="600" fill="#BFD9DE">第26格=100</text>
  </g>
  <g filter="url(#shadow)">
    <rect x="${left}" y="${trackY}" width="${priceLadder.length * cellWidth}" height="${trackHeight}" rx="18" fill="#FFFFFF" stroke="#809AA3" stroke-width="3"/>
    <clipPath id="trackClip"><rect x="${left}" y="${trackY}" width="${priceLadder.length * cellWidth}" height="${trackHeight}" rx="18"/></clipPath>
    <g clip-path="url(#trackClip)">${cells}</g>
    <line x1="${endX}" y1="${trackY}" x2="${endX}" y2="${trackY + trackHeight}" stroke="#8BA6AD" stroke-width="1" opacity="0.64"/>
  </g>
  ${zones}
  <rect x="70" y="510" width="3460" height="52" rx="16" fill="#E8EEF0"/>
  <circle cx="104" cy="536" r="9" fill="${accent}"/>
  <text x="128" y="544" font-family="${fontStack}" font-size="22" font-weight="700" fill="#294355">移动 1 格 = 移动到相邻价格；所有价格均为 2 的倍数。</text>
  <text x="3470" y="544" text-anchor="end" font-family="${fontStack}" font-size="22" font-weight="800" fill="${accent}">${rule}</text>
</svg>`;
}

function rosette(cx, cy, rx, ry, color, opacity) {
  const ellipses = Array.from({ length: 18 }, (_, index) => {
    const angle = index * 10;
    return `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="none" stroke="${color}" stroke-width="2" opacity="${opacity}" transform="rotate(${angle} ${cx} ${cy})"/>`;
  }).join('');
  return `<g>${ellipses}</g>`;
}

function moneySvg(spec) {
  const { value, code, accent, accentLight, accentDark } = spec;
  const width = 1400;
  const height = 700;
  const valueText = String(value);
  const valueSize = value >= 100 ? 272 : value >= 10 ? 310 : 350;
  const serial = `CF-${String(value).padStart(3, '0')}-0805`;
  const wavePaths = Array.from({ length: 10 }, (_, index) => {
    const y = 108 + index * 54;
    const shift = index % 2 === 0 ? 0 : 30;
    return `<path d="M40 ${y} C210 ${y - 64 + shift}, 370 ${y + 64 - shift}, 540 ${y} S870 ${y - 64 + shift}, 1040 ${y} S1230 ${y + 64 - shift}, 1360 ${y}" fill="none" stroke="${accent}" stroke-width="2" opacity="0.10"/>`;
  }).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#FFFDF5"/>
      <stop offset="0.5" stop-color="${accentLight}" stop-opacity="0.32"/>
      <stop offset="1" stop-color="#F7F0DE"/>
    </linearGradient>
    <linearGradient id="band" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="${accentDark}"/>
      <stop offset="0.55" stop-color="${accent}"/>
      <stop offset="1" stop-color="${accentDark}"/>
    </linearGradient>
    <pattern id="fineGrid" width="22" height="22" patternUnits="userSpaceOnUse">
      <path d="M22 0H0V22" fill="none" stroke="${accentDark}" stroke-width="0.8" opacity="0.10"/>
      <path d="M0 22L22 0" stroke="${accent}" stroke-width="0.6" opacity="0.05"/>
    </pattern>
    <clipPath id="noteClip"><rect x="20" y="20" width="1360" height="660" rx="42"/></clipPath>
    <filter id="noteShadow" x="-10%" y="-20%" width="120%" height="150%">
      <feDropShadow dx="0" dy="10" stdDeviation="11" flood-color="#0B2235" flood-opacity="0.24"/>
    </filter>
  </defs>
  <rect width="1400" height="700" fill="#EDF1F1"/>
  <g filter="url(#noteShadow)">
    <rect x="20" y="20" width="1360" height="660" rx="42" fill="url(#paper)" stroke="${accentDark}" stroke-width="8"/>
    <g clip-path="url(#noteClip)">
      <rect x="20" y="20" width="1360" height="660" fill="url(#fineGrid)"/>
      ${wavePaths}
      <path d="M20 20H230L370 350 230 680H20Z" fill="url(#band)" opacity="0.98"/>
      <path d="M1380 20H1170L1030 350 1170 680H1380Z" fill="url(#band)" opacity="0.98"/>
      <path d="M315 20H1085L990 92H410Z" fill="${accent}" opacity="0.16"/>
      <path d="M315 680H1085L990 608H410Z" fill="${accent}" opacity="0.16"/>
      ${rosette(700, 354, 262, 112, accentDark, 0.16)}
      ${rosette(700, 354, 214, 88, accent, 0.20)}
      ${rosette(260, 350, 100, 44, '#FFFFFF', 0.16)}
      ${rosette(1140, 350, 100, 44, '#FFFFFF', 0.16)}
      <circle cx="700" cy="354" r="185" fill="#FFFDF7" fill-opacity="0.72" stroke="${accent}" stroke-width="6"/>
      <circle cx="700" cy="354" r="163" fill="none" stroke="${accentDark}" stroke-width="2" stroke-dasharray="8 10" opacity="0.55"/>
      <path d="M576 420 L623 370 L670 390 L716 306 L760 337 L810 264" fill="none" stroke="${accentDark}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round" opacity="0.24"/>
      <path d="M790 262H814V286" fill="none" stroke="${accentDark}" stroke-width="14" stroke-linecap="round" opacity="0.24"/>
    </g>
    <rect x="42" y="42" width="1316" height="616" rx="30" fill="none" stroke="#FFFDF4" stroke-width="3" opacity="0.90"/>
    <rect x="58" y="58" width="1284" height="584" rx="24" fill="none" stroke="${accentDark}" stroke-width="2" stroke-dasharray="14 9" opacity="0.72"/>
  </g>

  <text x="700" y="102" text-anchor="middle" font-family="${fontStack}" font-size="42" font-weight="900" letter-spacing="8" fill="#163145">疯狂期货</text>
  <text x="700" y="142" text-anchor="middle" font-family="${fontStack}" font-size="19" font-weight="700" letter-spacing="5" fill="${accentDark}">交易银行 · GAME BANK</text>
  <text x="700" y="438" text-anchor="middle" font-family="${fontStack}" font-size="${valueSize}" font-weight="900" fill="${accentDark}" opacity="0.96">${valueText}</text>
  <text x="700" y="522" text-anchor="middle" font-family="${fontStack}" font-size="43" font-weight="900" letter-spacing="10" fill="${accentDark}">万金币</text>
  <text x="700" y="572" text-anchor="middle" font-family="${fontStack}" font-size="20" font-weight="700" letter-spacing="3" fill="#526A76">桌游专用 · 无实际货币价值</text>

  <text x="120" y="144" text-anchor="middle" font-family="${fontStack}" font-size="78" font-weight="900" fill="#FFFFFF">${valueText}</text>
  <text x="1280" y="144" text-anchor="middle" font-family="${fontStack}" font-size="78" font-weight="900" fill="#FFFFFF">${valueText}</text>
  <text x="120" y="615" text-anchor="middle" font-family="${fontStack}" font-size="78" font-weight="900" fill="#FFFFFF">${valueText}</text>
  <text x="1280" y="615" text-anchor="middle" font-family="${fontStack}" font-size="78" font-weight="900" fill="#FFFFFF">${valueText}</text>
  <text x="87" y="350" text-anchor="middle" font-family="${fontStack}" font-size="17" font-weight="800" fill="#FFFFFF" transform="rotate(-90 87 350)">${code}</text>
  <text x="1313" y="350" text-anchor="middle" font-family="${fontStack}" font-size="17" font-weight="800" fill="#FFFFFF" transform="rotate(90 1313 350)">${serial}</text>
</svg>`;
}

async function saveSvgAndPng(baseName, svg) {
  const svgPath = path.join(outDir, `${baseName}.svg`);
  const pngPath = path.join(outDir, `${baseName}.png`);
  await fs.writeFile(svgPath, svg, 'utf8');
  await sharp(Buffer.from(svg)).png({ compressionLevel: 9, adaptiveFiltering: true }).toFile(pngPath);
}

async function makeOverview() {
  const canvasWidth = 2400;
  const canvasHeight = 1960;
  const commodityFiles = [
    ['commodity-crude-oil.png', '原油'],
    ['commodity-gold.png', '黄金'],
    ['commodity-cotton.png', '棉花'],
    ['commodity-copper.png', '铜'],
  ];
  const noteValues = [1, 5, 10, 50, 100];
  const composite = [];

  for (let index = 0; index < commodityFiles.length; index += 1) {
    const [fileName] = commodityFiles[index];
    const input = await sharp(path.join(outDir, fileName)).resize(500, 500, { fit: 'cover' }).png().toBuffer();
    composite.push({ input, left: 70 + index * 580, top: 170 });
  }

  for (const [index, name] of ['price-track-spot.png', 'price-track-futures.png'].entries()) {
    const input = await sharp(path.join(outDir, name)).resize({ width: 2260 }).png().toBuffer();
    composite.push({ input, left: 70, top: 770 + index * 400 });
  }

  for (let index = 0; index < noteValues.length; index += 1) {
    const name = `money-${String(noteValues[index]).padStart(3, '0')}.png`;
    const input = await sharp(path.join(outDir, name)).resize(420, 210, { fit: 'fill' }).png().toBuffer();
    composite.push({ input, left: 70 + index * 455, top: 1655 });
  }

  const overlay = `<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${canvasHeight}" viewBox="0 0 ${canvasWidth} ${canvasHeight}">
      <rect width="${canvasWidth}" height="${canvasHeight}" fill="none"/>
      <text x="70" y="82" font-family="${fontStack}" font-size="54" font-weight="900" fill="#122F45">疯狂期货 · 视觉资产总览</text>
      <text x="70" y="126" font-family="${fontStack}" font-size="23" font-weight="600" fill="#57717E">四种商品插画、现货/期货价格条与 1—100 万金币资金牌</text>
      ${commodityFiles.map(([, label], index) => {
        const x = 70 + index * 580;
        return `<rect x="${x + 22}" y="596" width="456" height="58" rx="18" fill="#0F2F46" opacity="0.92"/>
          <text x="${x + 250}" y="636" text-anchor="middle" font-family="${fontStack}" font-size="30" font-weight="900" fill="#FFFFFF">${label}</text>`;
      }).join('')}
      <text x="70" y="738" font-family="${fontStack}" font-size="26" font-weight="900" fill="#31566A">价格条（51 格偶数阶梯）</text>
      <text x="70" y="1625" font-family="${fontStack}" font-size="26" font-weight="900" fill="#31566A">交易银行资金牌</text>
      <text x="2330" y="1918" text-anchor="end" font-family="${fontStack}" font-size="20" font-weight="700" fill="#6D818A">CRAZY FUTURES · GAME ASSET KIT</text>
    </svg>`;
  composite.push({ input: Buffer.from(overlay), left: 0, top: 0 });

  await sharp({
    create: {
      width: canvasWidth,
      height: canvasHeight,
      channels: 4,
      background: { r: 235, g: 241, b: 242, alpha: 1 },
    },
  }).composite(composite).png({ compressionLevel: 9, adaptiveFiltering: true }).toFile(path.join(outDir, 'asset-overview.png'));
}

async function main() {
  await saveSvgAndPng('price-track-spot', trackSvg('spot'));
  await saveSvgAndPng('price-track-futures', trackSvg('futures'));

  const notes = [
    { value: 1, code: '基础流动性', accent: '#617F96', accentLight: '#BCD0DC', accentDark: '#35586F' },
    { value: 5, code: '交易准备金', accent: '#13838A', accentLight: '#A9D9D4', accentDark: '#075D66' },
    { value: 10, code: '市场资金', accent: '#4D8B62', accentLight: '#C8DEC0', accentDark: '#2E6443' },
    { value: 50, code: '大额结算金', accent: '#C68524', accentLight: '#F1D59A', accentDark: '#8B5716' },
    { value: 100, code: '银行储备金', accent: '#A84643', accentLight: '#E7BC9C', accentDark: '#6E2E36' },
  ];

  for (const note of notes) {
    await saveSvgAndPng(`money-${String(note.value).padStart(3, '0')}`, moneySvg(note));
  }

  await makeOverview();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
