#!/usr/bin/env node

const fs = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');
const { PNG } = require('pngjs');
const pixelmatch = require('pixelmatch').default;
const JSZip = require('jszip');

const pluginRoot = path.resolve(__dirname, '..');
const templatesDir = path.join(pluginRoot, 'templates');
const templateHtmlPath = path.join(templatesDir, 'dashboard.html');
const brandJsonPath = path.join(templatesDir, 'brand.json');
const templateAssetsDir = path.join(templatesDir, 'assets');

const viewports = {
  desktop: {
    width: 1440,
    height: 1200,
    deviceScaleFactor: 1,
    isMobile: false,
    hasTouch: false,
  },
  mobile: {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  },
};

// --- Spec parsing -----------------------------------------------------------

function sanitizeProjectName(rawName) {
  return rawName
    .trim()
    .replace(/^#+\s*/, '')
    .replace(/\s+/g, '_')
    .replace(/[^A-Za-z0-9_-]/g, '')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '') || 'Visual_Regression';
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function buildDateStamp(date = new Date()) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function buildHumanDate(date = new Date()) {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

function parseSpec(text) {
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const projectLine = lines.find((line) => line.startsWith('#'));
  const urls = lines.filter((line) => /^https?:\/\//i.test(line.replace(/^-\s*/, ''))).map((line) => line.replace(/^-\s*/, ''));
  const pages = lines.filter((line) => /^\/.+/.test(line.replace(/^-\s*/, '')) || line.replace(/^-\s*/, '') === '/').map((line) => line.replace(/^-\s*/, ''));

  if (!projectLine) {
    throw new Error('Spec is missing a #Project_Name line.');
  }
  if (urls.length < 2) {
    throw new Error('Spec must include at least two URLs.');
  }
  if (pages.length < 1) {
    throw new Error('Spec must include at least one page path.');
  }

  return {
    projectName: sanitizeProjectName(projectLine),
    rawProjectName: projectLine.replace(/^#+\s*/, '').trim(),
    testUrl: urls[0].replace(/\/+$/, ''),
    prodUrl: urls[1].replace(/\/+$/, ''),
    pages,
  };
}

// --- FS / capture / diff ----------------------------------------------------

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

function pageSlug(pagePath) {
  return pagePath === '/' ? 'home' : pagePath.replace(/^\/|\/$/g, '').replace(/\//g, '-');
}

async function capturePage(browser, baseUrl, pagePath, destination, viewport) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: viewport.deviceScaleFactor,
    isMobile: viewport.isMobile,
    hasTouch: viewport.hasTouch,
  });

  const page = await context.newPage();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.addInitScript(() => {
    window.__visualRegressionStyle = `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
        caret-color: transparent !important;
      }
      video, iframe[title*="chat"], .grecaptcha-badge {
        visibility: hidden !important;
      }
    `;
  });
  await page.goto(`${baseUrl}${pagePath}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.addStyleTag({ content: `
    *, *::before, *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
      caret-color: transparent !important;
    }
    video, iframe[title*="chat"], .grecaptcha-badge {
      visibility: hidden !important;
    }
  `});
  await page.waitForTimeout(4000);
  await page.evaluate(async () => {
    window.scrollTo(0, 0);
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
  });
  await page.screenshot({ path: destination, fullPage: true });
  await context.close();
}

function padImage(image, width, height) {
  if (image.width === width && image.height === height) {
    return image;
  }
  const padded = new PNG({ width, height, fill: true });
  padded.data.fill(255);
  PNG.bitblt(image, padded, 0, 0, image.width, image.height, 0, 0);
  return padded;
}

function analyzeRegions(changedRows, width, height) {
  const heroCutoff = Math.max(1, Math.floor(height * 0.25));
  let topChanged = 0;
  let bodyChanged = 0;

  for (let y = 0; y < changedRows.length; y += 1) {
    const rowChanged = changedRows[y];
    if (y < heroCutoff) {
      topChanged += rowChanged;
    } else {
      bodyChanged += rowChanged;
    }
  }

  return {
    top_ratio: topChanged / Math.max(1, width * heroCutoff),
    body_ratio: bodyChanged / Math.max(1, width * Math.max(1, height - heroCutoff)),
  };
}

async function diffImages(testPath, prodPath, diffPath) {
  const testImage = PNG.sync.read(await fs.readFile(testPath));
  const prodImage = PNG.sync.read(await fs.readFile(prodPath));
  const width = Math.max(testImage.width, prodImage.width);
  const height = Math.max(testImage.height, prodImage.height);
  const paddedTest = padImage(testImage, width, height);
  const paddedProd = padImage(prodImage, width, height);
  const diffImage = new PNG({ width, height });

  const changedPixels = pixelmatch(
    paddedTest.data,
    paddedProd.data,
    diffImage.data,
    width,
    height,
    {
      threshold: 0.1,
      includeAA: true,
      alpha: 0.6,
      diffColor: [255, 0, 0],
    }
  );

  const changedRows = [];
  for (let y = 0; y < height; y += 1) {
    let rowChanged = 0;
    for (let x = 0; x < width; x += 1) {
      const offset = (y * width + x) * 4;
      const isChanged =
        diffImage.data[offset] === 255 &&
        diffImage.data[offset + 1] === 0 &&
        diffImage.data[offset + 2] === 0;
      if (isChanged) {
        rowChanged += 1;
      }
    }
    changedRows.push(rowChanged);
  }

  const regionMetrics = analyzeRegions(changedRows, width, height);

  await fs.writeFile(diffPath, PNG.sync.write(diffImage));
  return {
    width,
    height,
    changed_pixels: changedPixels,
    total_pixels: width * height,
    changed_ratio: changedPixels / (width * height),
    region_metrics: regionMetrics,
  };
}

// --- Severity ---------------------------------------------------------------

/**
 * Classify a single page-viewport diff using the body % and top-quarter % rules.
 * Thresholds intentionally hardcoded — see references/diff-thresholds.md.
 */
function classifySeverity(bodyPct, topQuarterPct) {
  if (bodyPct >= 5.0) return { label: 'Critical', glyph: '🔴', note: '' };
  if (bodyPct >= 1.0) return { label: 'Warning',  glyph: '⚠️', note: '' };
  if (topQuarterPct >= 10.0 && bodyPct < 1.0) {
    return { label: 'Warning', glyph: '⚠️', note: 'Likely rotating hero — verify' };
  }
  return { label: 'Pass', glyph: '✅', note: '' };
}

function severitySortKey(label) {
  return { Critical: 0, Warning: 1, Pass: 2 }[label] ?? 9;
}

// --- Helpers ---------------------------------------------------------------

function pct(value) {
  return `${(value * 100).toFixed(2)}%`;
}

function htmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function xmlEscape(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function csvEscape(value) {
  const s = String(value ?? '');
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

async function loadBrand() {
  try {
    const raw = await fs.readFile(brandJsonPath, 'utf8');
    return JSON.parse(raw);
  } catch (e) {
    return {};
  }
}

function severityCounts(results) {
  return results.reduce((acc, r) => {
    acc[r.severity.label] = (acc[r.severity.label] ?? 0) + 1;
    return acc;
  }, { Critical: 0, Warning: 0, Pass: 0 });
}

// --- Section renderers ------------------------------------------------------

function severityPill(label) {
  const cls = {
    Critical: 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400',
    Warning:  'bg-yellow-50 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    Pass:     'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400',
  }[label] || 'bg-gray-100 text-gray-700';
  return `<span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${cls}">${htmlEscape(label)}</span>`;
}

function renderSeverityRows(results) {
  if (!results.length) {
    return `<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No diffs captured.</td></tr>`;
  }
  const sorted = [...results].sort((a, b) =>
    severitySortKey(a.severity.label) - severitySortKey(b.severity.label)
    || a.page.localeCompare(b.page)
    || a.viewport.localeCompare(b.viewport)
  );
  return sorted.map((r) => {
    const body = (r.region_metrics.body_ratio * 100).toFixed(2) + '%';
    const top  = (r.region_metrics.top_ratio * 100).toFixed(2) + '%';
    return `<tr>
      <td class="px-6 py-4 text-gray-900 dark:text-white break-all">${htmlEscape(r.page)}</td>
      <td class="px-6 py-4 text-gray-700 dark:text-gray-300 capitalize">${htmlEscape(r.viewport)}</td>
      <td class="px-6 py-4">${severityPill(r.severity.label)}</td>
      <td class="px-6 py-4 text-gray-700 dark:text-gray-300">${body}</td>
      <td class="px-6 py-4 text-gray-700 dark:text-gray-300">${top}</td>
      <td class="px-6 py-4 text-gray-600 dark:text-gray-400">${htmlEscape(r.severity.note || '')}</td>
    </tr>`;
  }).join('\n');
}

function renderPagePreviewSections(results) {
  // Group by page, then per-viewport row of test|prod|diff
  const byPage = new Map();
  for (const r of results) {
    if (!byPage.has(r.page)) byPage.set(r.page, []);
    byPage.get(r.page).push(r);
  }

  const articles = [];
  for (const [page, items] of byPage.entries()) {
    items.sort((a, b) => a.viewport.localeCompare(b.viewport));
    const viewportRows = items.map((r) => {
      const testRel = path.relative(r.output_dir, r.test_screenshot).split(path.sep).join('/');
      const prodRel = path.relative(r.output_dir, r.prod_screenshot).split(path.sep).join('/');
      const diffRel = path.relative(r.output_dir, r.diff_image).split(path.sep).join('/');
      const bodyPctStr = (r.region_metrics.body_ratio * 100).toFixed(2);
      const topPctStr = (r.region_metrics.top_ratio * 100).toFixed(2);
      const vpDims = r.viewport === 'desktop' ? '1440×1200' : '390×844';

      const diffAlt = r.changed_pixels === 0
        ? `No visual diff for ${r.viewport} ${page}`
        : `Diff screenshot, ${bodyPctStr}% body changed, ${topPctStr}% top-quarter changed, ${r.viewport} ${page}`;

      const diffCell = r.changed_pixels === 0
        ? `<div class="rounded-lg border border-dashed border-gray-200 dark:border-dark-border p-6 text-center text-sm text-gray-500 dark:text-gray-400">No visual changes</div>`
        : `<a href="${htmlEscape(diffRel)}" class="block rounded-lg overflow-hidden border border-gray-100 dark:border-dark-border focus:outline-none focus-visible:ring-[3px] focus-visible:ring-brand-500" aria-label="Open full-size ${diffAlt}"><img src="${htmlEscape(diffRel)}" alt="${htmlEscape(diffAlt)}" loading="lazy" class="w-full h-auto block"></a>`;

      return `<figure class="rounded-xl border border-gray-100 dark:border-dark-border p-4 mt-4" aria-labelledby="vp-${pageSlug(page)}-${r.viewport}">
        <figcaption id="vp-${pageSlug(page)}-${r.viewport}" class="font-semibold text-gray-900 dark:text-white capitalize mb-3">${htmlEscape(r.viewport)} — ${vpDims} · ${severityPill(r.severity.label)} <span class="ml-2 text-xs font-normal text-gray-600 dark:text-gray-400">Body ${bodyPctStr}% · Top ${topPctStr}%${r.severity.note ? ' · ' + htmlEscape(r.severity.note) : ''}</span></figcaption>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a href="${htmlEscape(testRel)}" class="block rounded-lg overflow-hidden border border-gray-100 dark:border-dark-border focus:outline-none focus-visible:ring-[3px] focus-visible:ring-brand-500" aria-label="Open full-size ${r.viewport} test screenshot for ${page}"><img src="${htmlEscape(testRel)}" alt="${htmlEscape(r.viewport + ' test screenshot for ' + page)}" loading="lazy" class="w-full h-auto block"></a>
          <a href="${htmlEscape(prodRel)}" class="block rounded-lg overflow-hidden border border-gray-100 dark:border-dark-border focus:outline-none focus-visible:ring-[3px] focus-visible:ring-brand-500" aria-label="Open full-size ${r.viewport} prod screenshot for ${page}"><img src="${htmlEscape(prodRel)}" alt="${htmlEscape(r.viewport + ' prod screenshot for ' + page)}" loading="lazy" class="w-full h-auto block"></a>
          ${diffCell}
        </div>
      </figure>`;
    }).join('\n');

    articles.push(`<article aria-labelledby="page-${pageSlug(page)}">
      <h3 id="page-${pageSlug(page)}" class="text-base font-bold text-gray-900 dark:text-white break-all">${htmlEscape(page)}</h3>
      ${viewportRows}
    </article>`);
  }
  return articles.join('\n');
}

function renderDownloadLinks(artifacts) {
  return artifacts.map(({ kind, label, filename }) => `<a href="${htmlEscape(filename)}" download class="inline-flex items-center gap-3 px-5 py-3 bg-[#1C1C1C] text-white rounded-xl font-semibold hover:bg-black focus:outline-none focus-visible:ring-[3px] focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-brand-600 transition-colors shadow-md">
    <i class="fa-solid fa-file-arrow-down" aria-hidden="true"></i>
    <span class="flex flex-col items-start leading-tight">
      <span class="text-xs uppercase tracking-wider opacity-80">${htmlEscape(kind)}</span>
      <span class="text-sm">${htmlEscape(label)}</span>
    </span>
  </a>`).join('\n');
}

// --- Template render --------------------------------------------------------

async function renderDashboard(spec, results, brand, audit_date, artifacts) {
  const template = await fs.readFile(templateHtmlPath, 'utf8');
  const counts = severityCounts(results);
  const totalDiffs = counts.Critical + counts.Warning;
  const subs = {
    REPORT_TITLE: brand.report_title || 'Visual Regression Report',
    REPORT_SUBTITLE: brand.report_subtitle || '',
    AGENCY_NAME: brand.agency_name || '',
    AGENCY_KICKER: brand.agency_kicker || 'Visual Regression',
    AGENCY_LOGO: brand.agency_logo || 'assets/imgs/logo-mini.svg',
    FOOTER_TEXT: brand.footer_text || '',
    DOWNLOADS_NOTE: brand.downloads_note || '',
    TASKS_NOTE: brand.tasks_note || '',
    PROJECT_NAME: spec.rawProjectName || spec.projectName,
    TEST_URL: spec.testUrl,
    PROD_URL: spec.prodUrl,
    AUDIT_DATE: audit_date,
    PAGE_VIEWPORT_LABEL: `${spec.pages.length} pages × ${Object.keys(viewports).length} viewports`,
    TOTAL_DIFFS: String(totalDiffs),
    CRITICAL_COUNT: String(counts.Critical),
    WARNING_COUNT: String(counts.Warning),
    PASS_COUNT: String(counts.Pass),
    TASK_COUNT: String(results.length),
    SEVERITY_ROWS: renderSeverityRows(results),
    PAGE_PREVIEW_SECTIONS: renderPagePreviewSections(results),
    DOWNLOAD_LINKS: renderDownloadLinks(artifacts),
  };
  let html = template;
  for (const [key, val] of Object.entries(subs)) {
    html = html.split(`{{${key}}}`).join(String(val));
  }
  return html;
}

// --- CSV --------------------------------------------------------------------

async function writeCsv(outPath, spec, results) {
  const header = ['project','page','viewport','severity','body_pct','top_quarter_pct','changed_ratio_pct','note','test_screenshot','prod_screenshot','diff_image'];
  const lines = [header.map(csvEscape).join(',')];
  const sorted = [...results].sort((a, b) =>
    severitySortKey(a.severity.label) - severitySortKey(b.severity.label)
    || a.page.localeCompare(b.page)
    || a.viewport.localeCompare(b.viewport)
  );
  for (const r of sorted) {
    const row = [
      spec.rawProjectName || spec.projectName,
      r.page,
      r.viewport,
      r.severity.label,
      (r.region_metrics.body_ratio * 100).toFixed(2),
      (r.region_metrics.top_ratio * 100).toFixed(2),
      (r.changed_ratio * 100).toFixed(2),
      r.severity.note || '',
      path.relative(r.output_dir, r.test_screenshot).split(path.sep).join('/'),
      path.relative(r.output_dir, r.prod_screenshot).split(path.sep).join('/'),
      path.relative(r.output_dir, r.diff_image).split(path.sep).join('/'),
    ];
    lines.push(row.map(csvEscape).join(','));
  }
  await fs.writeFile(outPath, lines.join('\n') + '\n');
}

// --- Action Plan ------------------------------------------------------------

async function writeActionPlan(outPath, spec, results, audit_date) {
  const counts = severityCounts(results);
  const lines = [];
  lines.push(`# Visual Regression — Action Plan`);
  lines.push('');
  lines.push(`- **Project**: ${spec.rawProjectName || spec.projectName}`);
  lines.push(`- **Test URL**: ${spec.testUrl}`);
  lines.push(`- **Prod URL**: ${spec.prodUrl}`);
  lines.push(`- **Audit date**: ${audit_date}`);
  lines.push(`- **Coverage**: ${spec.pages.length} pages × ${Object.keys(viewports).length} viewports = ${spec.pages.length * Object.keys(viewports).length} diffs`);
  lines.push('');
  lines.push(`## Severity summary`);
  lines.push('');
  lines.push(`| Severity | Count |`);
  lines.push(`|---|---:|`);
  lines.push(`| 🔴 Critical | ${counts.Critical} |`);
  lines.push(`| ⚠️ Warning | ${counts.Warning} |`);
  lines.push(`| ✅ Pass | ${counts.Pass} |`);
  lines.push('');

  const sections = [
    ['Critical', '🔴', 'Investigate immediately. Body diff ≥ 5%.'],
    ['Warning',  '⚠️', 'Verify before opening a bug. Body diff 1–5% OR top-quarter ≥ 10% with body < 1%.'],
    ['Pass',     '✅', 'Body diff < 1% AND top-quarter < 10%. No action required.'],
  ];

  for (const [label, glyph, blurb] of sections) {
    const bucket = results.filter((r) => r.severity.label === label)
      .sort((a, b) => a.page.localeCompare(b.page) || a.viewport.localeCompare(b.viewport));
    if (!bucket.length) continue;
    lines.push(`## ${glyph} ${label}`);
    lines.push('');
    lines.push(`*${blurb}*`);
    lines.push('');
    for (const r of bucket) {
      const body = (r.region_metrics.body_ratio * 100).toFixed(2);
      const top = (r.region_metrics.top_ratio * 100).toFixed(2);
      const diffRel = path.relative(r.output_dir, r.diff_image).split(path.sep).join('/');
      lines.push(`- **\`${r.page}\` · ${r.viewport}** — body ${body}%, top-quarter ${top}%${r.severity.note ? ` · _${r.severity.note}_` : ''}`);
      lines.push(`  - Diff: [\`${diffRel}\`](${diffRel})`);
      if (label === 'Warning' && r.severity.note && r.severity.note.includes('rotating hero')) {
        lines.push(`  - See [false-positive-patterns.md](../../skills/dd-vreg/references/false-positive-patterns.md#rotating-hero--carousel) for verification steps.`);
      }
    }
    lines.push('');
  }

  lines.push(`## References`);
  lines.push('');
  lines.push(`- Severity rules: \`skills/dd-vreg/references/diff-thresholds.md\``);
  lines.push(`- False-positive patterns: \`skills/dd-vreg/references/false-positive-patterns.md\``);
  lines.push('');
  await fs.writeFile(outPath, lines.join('\n'));
}

// --- DOCX -------------------------------------------------------------------

function docPara(text, opts = {}) {
  const bold = opts.bold ? '<w:b/>' : '';
  const sz = opts.sz ? `<w:sz w:val="${opts.sz}"/>` : '';
  const align = opts.align ? `<w:pPr><w:jc w:val="${opts.align}"/></w:pPr>` : '';
  return `<w:p>${align}<w:r><w:rPr>${bold}${sz}</w:rPr><w:t xml:space="preserve">${xmlEscape(text)}</w:t></w:r></w:p>`;
}

function docHeading(text, level = 1) {
  const sz = level === 1 ? 36 : level === 2 ? 28 : 24;
  return docPara(text, { bold: true, sz });
}

function docTableRow(cells, opts = {}) {
  return `<w:tr>${cells.map((c) => `<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>${docPara(c, { bold: !!opts.header })}</w:tc>`).join('')}</w:tr>`;
}

function docTable(rows, opts = {}) {
  const header = opts.header ? docTableRow(rows[0], { header: true }) : '';
  const body = (opts.header ? rows.slice(1) : rows).map((r) => docTableRow(r)).join('');
  return `<w:tbl>
    <w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>
      <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
    </w:tblBorders></w:tblPr>
    ${header}${body}
  </w:tbl>`;
}

async function writeDocx(outPath, spec, results, audit_date) {
  const counts = severityCounts(results);
  const zip = new JSZip();

  zip.file('[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>`);

  zip.file('_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`);

  const summaryRows = [
    ['Severity', 'Count'],
    ['Critical', String(counts.Critical)],
    ['Warning',  String(counts.Warning)],
    ['Pass',     String(counts.Pass)],
  ];

  const findingRows = [['Page', 'Viewport', 'Severity', 'Body %', 'Top-quarter %', 'Note']];
  const sorted = [...results].sort((a, b) =>
    severitySortKey(a.severity.label) - severitySortKey(b.severity.label)
    || a.page.localeCompare(b.page)
    || a.viewport.localeCompare(b.viewport)
  );
  for (const r of sorted) {
    findingRows.push([
      r.page,
      r.viewport,
      r.severity.label,
      (r.region_metrics.body_ratio * 100).toFixed(2) + '%',
      (r.region_metrics.top_ratio * 100).toFixed(2) + '%',
      r.severity.note || '',
    ]);
  }

  const body = [
    docHeading('Visual Regression Report', 1),
    docPara(`Project: ${spec.rawProjectName || spec.projectName}`),
    docPara(`Test URL: ${spec.testUrl}`),
    docPara(`Production URL: ${spec.prodUrl}`),
    docPara(`Audit date: ${audit_date}`),
    docPara(`Coverage: ${spec.pages.length} pages × ${Object.keys(viewports).length} viewports`),
    docHeading('Severity summary', 2),
    docTable(summaryRows, { header: true }),
    docHeading('Findings', 2),
    docTable(findingRows, { header: true }),
    docHeading('Notes', 2),
    docPara('Thresholds — Critical: body diff ≥ 5%. Warning: body diff 1–5% OR top-quarter ≥ 10% with body < 1%. Pass: otherwise.'),
    docPara('See diff-thresholds.md and false-positive-patterns.md in the skill for rationale and operator guidance.'),
  ].join('');

  const doc = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>${body}<w:sectPr/></w:body>
</w:document>`;
  zip.file('word/document.xml', doc);

  const buf = await zip.generateAsync({ type: 'nodebuffer' });
  await fs.writeFile(outPath, buf);
}

// --- Markdown report (slim) -------------------------------------------------

function buildMarkdownReport(spec, results, audit_date) {
  const counts = severityCounts(results);
  const lines = [];
  lines.push('# Visual Regression Report');
  lines.push('');
  lines.push(`- **Project**: ${spec.rawProjectName || spec.projectName}`);
  lines.push(`- **Test URL**: ${spec.testUrl}`);
  lines.push(`- **Prod URL**: ${spec.prodUrl}`);
  lines.push(`- **Audit date**: ${audit_date}`);
  lines.push(`- **Bundle**: open \`index.html\` for the interactive dashboard.`);
  lines.push('');
  lines.push(`## Severity summary`);
  lines.push('');
  lines.push(`| Severity | Count |`);
  lines.push(`|---|---:|`);
  lines.push(`| 🔴 Critical | ${counts.Critical} |`);
  lines.push(`| ⚠️ Warning | ${counts.Warning} |`);
  lines.push(`| ✅ Pass | ${counts.Pass} |`);
  lines.push('');
  lines.push(`## All diffs`);
  lines.push('');
  lines.push(`| Page | Viewport | Severity | Body % | Top-quarter % | Note |`);
  lines.push(`|---|---|---|---:|---:|---|`);
  const sorted = [...results].sort((a, b) =>
    severitySortKey(a.severity.label) - severitySortKey(b.severity.label)
    || a.page.localeCompare(b.page)
    || a.viewport.localeCompare(b.viewport)
  );
  for (const r of sorted) {
    lines.push(`| \`${r.page}\` | ${r.viewport} | ${r.severity.glyph} ${r.severity.label} | ${(r.region_metrics.body_ratio * 100).toFixed(2)}% | ${(r.region_metrics.top_ratio * 100).toFixed(2)}% | ${r.severity.note || ''} |`);
  }
  lines.push('');
  lines.push(`See \`ACTION-PLAN.md\` for grouped remediation steps, \`DIFFS.csv\` for project-tracker import, \`DIFF-REPORT.docx\` for client delivery.`);
  return lines.join('\n') + '\n';
}

// --- Asset copy -------------------------------------------------------------

async function copyTemplateAssets(outputDir) {
  try {
    await fs.access(templateAssetsDir);
  } catch {
    return;
  }
  const dst = path.join(outputDir, 'assets');
  await fs.cp(templateAssetsDir, dst, { recursive: true });
}

// --- Output dir -------------------------------------------------------------

async function prepareOutputDir(spec) {
  const cwd = process.cwd();
  const webDir = path.join(cwd, 'web');
  await ensureDir(webDir);
  const outputDir = path.join(webDir, `${spec.projectName}-vreg-${buildDateStamp()}`);
  // Clean any previous run on the same day
  await fs.rm(outputDir, { recursive: true, force: true });
  await ensureDir(outputDir);
  return outputDir;
}

// --- Entry point ------------------------------------------------------------

async function readSpec() {
  const specPath = process.argv[2];
  if (specPath) {
    return fs.readFile(path.resolve(specPath), 'utf8');
  }
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => chunks.push(chunk));
    process.stdin.on('end', () => resolve(chunks.join('')));
    process.stdin.on('error', reject);
  });
}

async function main() {
  const specText = await readSpec();
  const spec = parseSpec(specText);
  const outputDir = await prepareOutputDir(spec);
  const screenshotDir = path.join(outputDir, 'screenshots');
  const diffDir = path.join(outputDir, 'diffs');
  await ensureDir(screenshotDir);
  await ensureDir(diffDir);
  await copyTemplateAssets(outputDir);

  const audit_date = buildHumanDate();
  const brand = await loadBrand();

  const browser = await chromium.launch({ headless: true });
  const results = [];

  try {
    for (const [viewportName, viewport] of Object.entries(viewports)) {
      for (const page of spec.pages) {
        const slug = pageSlug(page);
        const testPath = path.join(screenshotDir, viewportName, 'test', `${slug}.png`);
        const prodPath = path.join(screenshotDir, viewportName, 'prod', `${slug}.png`);
        const diffPath = path.join(diffDir, viewportName, `${slug}.png`);
        await ensureDir(path.dirname(testPath));
        await ensureDir(path.dirname(prodPath));
        await ensureDir(path.dirname(diffPath));

        console.log(`Capturing ${viewportName} test ${page}`);
        await capturePage(browser, spec.testUrl, page, testPath, viewport);
        console.log(`Capturing ${viewportName} prod ${page}`);
        await capturePage(browser, spec.prodUrl, page, prodPath, viewport);
        const metrics = await diffImages(testPath, prodPath, diffPath);

        const bodyPct = metrics.region_metrics.body_ratio * 100;
        const topPct = metrics.region_metrics.top_ratio * 100;
        const severity = classifySeverity(bodyPct, topPct);

        results.push({
          page,
          viewport: viewportName,
          dimensions: viewport,
          test_screenshot: testPath,
          prod_screenshot: prodPath,
          diff_image: diffPath,
          output_dir: outputDir,
          severity,
          ...metrics,
        });
      }
    }
  } finally {
    await browser.close();
  }

  // Artifacts
  const artifacts = [
    { kind: 'DOCX', label: 'Visual Diff Report', filename: 'DIFF-REPORT.docx' },
    { kind: 'MD',   label: 'Action Plan',        filename: 'ACTION-PLAN.md' },
    { kind: 'CSV',  label: 'Diffs',              filename: 'DIFFS.csv' },
    { kind: 'MD',   label: 'Markdown Summary',   filename: 'report.md' },
    { kind: 'JSON', label: 'Raw Metrics',        filename: 'metrics.json' },
  ];

  await fs.writeFile(path.join(outputDir, 'metrics.json'), JSON.stringify(results, null, 2));
  await fs.writeFile(path.join(outputDir, 'report.md'),     buildMarkdownReport(spec, results, audit_date));
  await writeCsv(       path.join(outputDir, 'DIFFS.csv'),         spec, results);
  await writeActionPlan(path.join(outputDir, 'ACTION-PLAN.md'),    spec, results, audit_date);
  await writeDocx(      path.join(outputDir, 'DIFF-REPORT.docx'),  spec, results, audit_date);
  const html = await renderDashboard(spec, results, brand, audit_date, artifacts);
  await fs.writeFile(path.join(outputDir, 'index.html'), html);

  console.log(outputDir);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
