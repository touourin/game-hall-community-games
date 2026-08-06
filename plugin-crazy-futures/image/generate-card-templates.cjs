const fs = require('fs/promises');
const path = require('path');
const sharp = require('sharp');

const outDir = __dirname;
const fontStack = "'Microsoft YaHei','Noto Sans CJK SC','Source Han Sans SC',Arial,sans-serif";
const cardWidth = 750;
const cardHeight = 1050;

function sharedDefs(kind) {
  const personal = kind === 'personal';
  const dark = personal ? '#083F51' : '#4B2630';
  const mid = personal ? '#087A88' : '#B65735';
  const light = personal ? '#47C1BC' : '#F1A45E';
  const pale = personal ? '#D9F0EF' : '#F8E2CA';
  return {
    dark,
    mid,
    light,
    pale,
    defs: `<defs>
      <linearGradient id="cardBg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#FFFDF6"/>
        <stop offset="1" stop-color="${pale}"/>
      </linearGradient>
      <linearGradient id="hero" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="${dark}"/>
        <stop offset="0.58" stop-color="${mid}"/>
        <stop offset="1" stop-color="#102A43"/>
      </linearGradient>
      <linearGradient id="backBg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#071E2F"/>
        <stop offset="0.48" stop-color="${dark}"/>
        <stop offset="1" stop-color="${mid}"/>
      </linearGradient>
      <pattern id="microGrid" width="30" height="30" patternUnits="userSpaceOnUse">
        <path d="M30 0H0V30" fill="none" stroke="#FFFFFF" stroke-width="1" opacity="0.065"/>
        <path d="M0 30L30 0" stroke="#FFFFFF" stroke-width="0.7" opacity="0.035"/>
      </pattern>
      <pattern id="dotField" width="24" height="24" patternUnits="userSpaceOnUse">
        <circle cx="12" cy="12" r="1.6" fill="#FFFFFF" opacity="0.10"/>
      </pattern>
      <clipPath id="cardClip"><rect x="15" y="15" width="720" height="1020" rx="48"/></clipPath>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">
        <feDropShadow dx="0" dy="12" stdDeviation="13" flood-color="#071E2F" flood-opacity="0.28"/>
      </filter>
    </defs>`,
  };
}

function marketChart(accent, opacity = 0.28) {
  return `<g opacity="${opacity}">
    <path d="M54 385L114 348L164 367L220 288L274 315L332 245L384 274L448 191L510 229L565 174L696 106" fill="none" stroke="${accent}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M668 107H696V135" fill="none" stroke="${accent}" stroke-width="11" stroke-linecap="round"/>
    <g stroke="#FFFFFF" stroke-width="4">
      <line x1="130" y1="268" x2="130" y2="344"/><rect x="118" y="290" width="24" height="33" fill="#FFFFFF"/>
      <line x1="190" y1="234" x2="190" y2="322"/><rect x="178" y="255" width="24" height="41" fill="none"/>
      <line x1="250" y1="203" x2="250" y2="292"/><rect x="238" y="222" width="24" height="44" fill="#FFFFFF"/>
      <line x1="310" y1="176" x2="310" y2="265"/><rect x="298" y="198" width="24" height="39" fill="none"/>
      <line x1="370" y1="145" x2="370" y2="235"/><rect x="358" y="167" width="24" height="42" fill="#FFFFFF"/>
    </g>
  </g>`;
}

function eyeIcon(cx, cy, scale, color) {
  return `<g transform="translate(${cx} ${cy}) scale(${scale})" fill="none" stroke="${color}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M-118 0C-72-66 72-66 118 0C72 66-72 66-118 0Z" stroke-width="14"/>
    <circle cx="0" cy="0" r="42" stroke-width="14"/>
    <circle cx="0" cy="0" r="13" fill="${color}" stroke="none"/>
    <path d="M-145-86L-116-57M145-86L116-57M-145 86L-116 57M145 86L116 57" stroke-width="10" opacity="0.72"/>
  </g>`;
}

function globeIcon(cx, cy, scale, color) {
  return `<g transform="translate(${cx} ${cy}) scale(${scale})" fill="none" stroke="${color}" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="0" cy="0" r="108" stroke-width="13"/>
    <ellipse cx="0" cy="0" rx="48" ry="108" stroke-width="10"/>
    <path d="M-100-41C-35-14 35-14 100-41M-100 41C-35 14 35 14 100 41M-108 0H108" stroke-width="9"/>
    <path d="M88-116L135-82L113-39L160-9" stroke-width="12"/>
    <circle cx="88" cy="-116" r="9" fill="${color}" stroke="none"/>
    <circle cx="160" cy="-9" r="9" fill="${color}" stroke="none"/>
  </g>`;
}

function cardFrame(defs, accent) {
  return `<rect width="${cardWidth}" height="${cardHeight}" fill="#EAF0F1"/>
    <g filter="url(#shadow)">
      <rect x="15" y="15" width="720" height="1020" rx="48" fill="url(#cardBg)" stroke="${defs.dark}" stroke-width="10"/>
      <rect x="34" y="34" width="682" height="982" rx="35" fill="none" stroke="${accent}" stroke-width="3" opacity="0.78"/>
    </g>`;
}

function frontSvg(kind) {
  const personal = kind === 'personal';
  const s = sharedDefs(kind);
  const accent = personal ? '#42C4BF' : '#F0A052';
  const category = personal ? '个人信息牌' : '公共事件牌';
  const categoryEn = personal ? 'PRIVATE INTELLIGENCE' : 'PUBLIC EVENT';
  const visibility = personal ? '仅持有者查看' : '翻开后所有玩家可见';
  const cornerCode = personal ? 'P' : 'E';
  const artIcon = personal ? eyeIcon(375, 315, 0.55, '#FFFFFF') : globeIcon(375, 312, 0.50, '#FFFFFF');
  const timing = personal ? '出牌阶段' : '翻牌阶段立即生效';

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${cardWidth}" height="${cardHeight}" viewBox="0 0 ${cardWidth} ${cardHeight}">
  ${s.defs}
  ${cardFrame(s, accent)}
  <g clip-path="url(#cardClip)">
    <rect x="15" y="15" width="720" height="462" fill="url(#hero)"/>
    <rect x="15" y="15" width="720" height="462" fill="url(#microGrid)"/>
    ${marketChart(accent, 0.24)}
    <path d="M15 446L735 390V494H15Z" fill="#FFFDF6"/>
  </g>

  <g id="category-header">
    <rect x="52" y="53" width="380" height="78" rx="24" fill="#071E2F" opacity="0.88"/>
    <rect x="67" y="69" width="9" height="46" rx="4.5" fill="${accent}"/>
    <text x="96" y="96" font-family="${fontStack}" font-size="30" font-weight="900" fill="#FFFFFF">${category}</text>
    <text x="97" y="119" font-family="${fontStack}" font-size="12" font-weight="700" letter-spacing="2" fill="#C8DCE1">${categoryEn}</text>
    <rect x="624" y="54" width="70" height="70" rx="22" fill="${accent}"/>
    <text x="659" y="103" text-anchor="middle" font-family="${fontStack}" font-size="44" font-weight="900" fill="${s.dark}">${cornerCode}</text>
  </g>

  <g id="artwork-placeholder">
    <rect x="54" y="154" width="642" height="304" rx="30" fill="#061D2B" fill-opacity="0.26" stroke="#FFFFFF" stroke-width="3" stroke-dasharray="12 9" opacity="0.92"/>
    ${artIcon}
  </g>

  <g id="card-title-panel">
    <rect x="54" y="486" width="642" height="430" rx="30" fill="#FFFFFF" stroke="${s.pale}" stroke-width="4"/>
    <rect x="82" y="518" width="586" height="7" rx="3.5" fill="${accent}" opacity="0.75"/>
    <circle cx="375" cy="705" r="152" fill="none" stroke="${s.mid}" stroke-width="3" opacity="0.08"/>
    <circle cx="375" cy="705" r="112" fill="none" stroke="${accent}" stroke-width="3" stroke-dasharray="12 14" opacity="0.13"/>
    <path d="M112 842H638" stroke="${s.pale}" stroke-width="5" stroke-linecap="round"/>
    <path d="M214 866H536" stroke="${accent}" stroke-width="4" stroke-linecap="round" opacity="0.34"/>
  </g>

  <g id="card-footer">
    <rect x="54" y="934" width="642" height="65" rx="20" fill="${s.dark}"/>
    <text x="82" y="975" font-family="${fontStack}" font-size="18" font-weight="800" fill="#FFFFFF">${timing}</text>
    <text x="669" y="975" text-anchor="end" font-family="${fontStack}" font-size="17" font-weight="700" fill="${accent}">${visibility}</text>
  </g>
</svg>`;
}

function backPattern(kind, s, accent) {
  if (kind === 'personal') {
    const diamonds = Array.from({ length: 7 }, (_, i) => {
      const size = 590 - i * 74;
      const x = 375 - size / 2;
      const y = 525 - size / 2;
      return `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="44" fill="none" stroke="${accent}" stroke-width="${i === 0 ? 4 : 2}" opacity="${0.12 + i * 0.025}" transform="rotate(45 375 525)"/>`;
    }).join('');
    return `${diamonds}
      <path d="M94 525H210M540 525H656M375 98V214M375 836V952" stroke="${accent}" stroke-width="5" stroke-linecap="round" opacity="0.42"/>
      <circle cx="94" cy="525" r="8" fill="${accent}"/><circle cx="656" cy="525" r="8" fill="${accent}"/>
      <circle cx="375" cy="98" r="8" fill="${accent}"/><circle cx="375" cy="952" r="8" fill="${accent}"/>`;
  }

  const rings = Array.from({ length: 8 }, (_, i) => {
    const radius = 300 - i * 34;
    return `<circle cx="375" cy="525" r="${radius}" fill="none" stroke="${accent}" stroke-width="${i === 0 ? 5 : 2}" opacity="${0.10 + i * 0.025}" stroke-dasharray="${i % 2 === 0 ? '12 11' : '4 14'}"/>`;
  }).join('');
  const rays = Array.from({ length: 16 }, (_, i) => {
    const angle = i * 22.5;
    return `<path d="M375 184V108" stroke="${accent}" stroke-width="5" stroke-linecap="round" opacity="0.30" transform="rotate(${angle} 375 525)"/>`;
  }).join('');
  return `${rings}${rays}`;
}

function backSvg(kind) {
  const personal = kind === 'personal';
  const s = sharedDefs(kind);
  const accent = personal ? '#59D3CA' : '#FFB568';
  const category = personal ? '个人信息' : '公共事件';
  const categoryEn = personal ? 'PRIVATE INTELLIGENCE' : 'PUBLIC EVENT';
  const visibility = personal ? '仅持有者查看' : '所有玩家可见';
  const icon = personal ? eyeIcon(375, 520, 1.0, '#FFFFFF') : globeIcon(375, 520, 0.90, '#FFFFFF');
  const symbol = personal ? 'P' : 'E';

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${cardWidth}" height="${cardHeight}" viewBox="0 0 ${cardWidth} ${cardHeight}">
  ${s.defs}
  <rect width="${cardWidth}" height="${cardHeight}" fill="#EAF0F1"/>
  <g filter="url(#shadow)">
    <rect x="15" y="15" width="720" height="1020" rx="48" fill="url(#backBg)" stroke="${s.dark}" stroke-width="10"/>
  </g>
  <g clip-path="url(#cardClip)">
    <rect x="15" y="15" width="720" height="1020" fill="url(#microGrid)"/>
    <rect x="15" y="15" width="720" height="1020" fill="url(#dotField)"/>
    ${backPattern(kind, s, accent)}
    <path d="M15 15H245L375 162L505 15H735V190L612 315L735 440V610L612 735L735 860V1035H505L375 888L245 1035H15V860L138 735L15 610V440L138 315L15 190Z" fill="${accent}" opacity="0.075"/>
  </g>

  <rect x="39" y="39" width="672" height="972" rx="34" fill="none" stroke="#FFFFFF" stroke-width="3" opacity="0.72"/>
  <rect x="54" y="54" width="642" height="942" rx="26" fill="none" stroke="${accent}" stroke-width="3" stroke-dasharray="14 10" opacity="0.72"/>

  <g id="brand-top">
    <text x="375" y="104" text-anchor="middle" font-family="${fontStack}" font-size="20" font-weight="800" letter-spacing="5" fill="#D8E7EA">CRAZY FUTURES</text>
    <rect x="319" y="126" width="112" height="45" rx="22.5" fill="${accent}"/>
    <text x="375" y="158" text-anchor="middle" font-family="${fontStack}" font-size="28" font-weight="900" fill="${s.dark}">${symbol}</text>
  </g>

  <g id="category-emblem">
    <circle cx="375" cy="520" r="220" fill="#061C2B" fill-opacity="0.66" stroke="${accent}" stroke-width="8"/>
    <circle cx="375" cy="520" r="195" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-dasharray="8 11" opacity="0.46"/>
    ${icon}
  </g>

  <g id="category-label">
    <rect x="107" y="740" width="536" height="122" rx="34" fill="#061C2B" fill-opacity="0.88" stroke="${accent}" stroke-width="3"/>
    <text x="375" y="795" text-anchor="middle" font-family="${fontStack}" font-size="42" font-weight="900" letter-spacing="8" fill="#FFFFFF">${category}</text>
    <text x="375" y="830" text-anchor="middle" font-family="${fontStack}" font-size="14" font-weight="800" letter-spacing="3" fill="${accent}">${categoryEn}</text>
  </g>
  <text x="375" y="924" text-anchor="middle" font-family="${fontStack}" font-size="20" font-weight="800" letter-spacing="4" fill="#FFFFFF">${visibility}</text>
  <text x="375" y="967" text-anchor="middle" font-family="${fontStack}" font-size="15" font-weight="700" letter-spacing="3" fill="${accent}">疯狂期货 · 交易桌游</text>
</svg>`;
}

async function saveSvgAndPng(baseName, svg) {
  await fs.writeFile(path.join(outDir, `${baseName}.svg`), svg, 'utf8');
  await sharp(Buffer.from(svg))
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .withMetadata({ density: 300 })
    .toFile(path.join(outDir, `${baseName}.png`));
}

async function makeOverview() {
  const width = 2200;
  const height = 930;
  const names = [
    ['card-personal-front.png', '个人牌 · 正面'],
    ['card-personal-back.png', '个人牌 · 背面'],
    ['card-event-front.png', '事件牌 · 正面'],
    ['card-event-back.png', '事件牌 · 背面'],
  ];
  const composite = [];

  for (let index = 0; index < names.length; index += 1) {
    const input = await sharp(path.join(outDir, names[index][0])).resize(450, 630, { fit: 'fill' }).png().toBuffer();
    composite.push({ input, left: 85 + index * 520, top: 190 });
  }

  const labels = names.map(([, label], index) => {
    const x = 85 + index * 520;
    const fill = index < 2 ? '#087A88' : '#B65735';
    return `<rect x="${x}" y="838" width="450" height="54" rx="18" fill="${fill}"/>
      <text x="${x + 225}" y="875" text-anchor="middle" font-family="${fontStack}" font-size="25" font-weight="900" fill="#FFFFFF">${label}</text>`;
  }).join('');
  const overlay = `<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
      <text x="80" y="82" font-family="${fontStack}" font-size="52" font-weight="900" fill="#122F45">疯狂期货 · 卡牌模板</text>
      <text x="80" y="132" font-family="${fontStack}" font-size="24" font-weight="700" fill="#5A7480">个人牌使用青绿色与“眼睛”标识；事件牌使用铜橙色与“地球”标识。</text>
      ${labels}
    </svg>`;
  composite.push({ input: Buffer.from(overlay), left: 0, top: 0 });

  await sharp({
    create: { width, height, channels: 4, background: { r: 234, g: 240, b: 241, alpha: 1 } },
  }).composite(composite).png({ compressionLevel: 9, adaptiveFiltering: true }).toFile(path.join(outDir, 'card-template-overview.png'));
}

async function main() {
  await saveSvgAndPng('card-personal-front', frontSvg('personal'));
  await saveSvgAndPng('card-personal-back', backSvg('personal'));
  await saveSvgAndPng('card-event-front', frontSvg('event'));
  await saveSvgAndPng('card-event-back', backSvg('event'));
  await makeOverview();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
