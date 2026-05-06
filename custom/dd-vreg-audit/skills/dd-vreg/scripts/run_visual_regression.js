#!/usr/bin/env node

const fs = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');
const { PNG } = require('pngjs');
const pixelmatch = require('pixelmatch').default;
const skillRoot = path.resolve(__dirname, '..');
const bundledLogoPath = path.join(skillRoot, 'assets', 'agency-logo.svg');

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

function buildTimestamp(date = new Date()) {
  return `${pad2(date.getMonth() + 1)}${pad2(date.getDate())}${date.getFullYear()}-${pad2(date.getHours())}${pad2(date.getMinutes())}`;
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
    testUrl: urls[0].replace(/\/+$/, ''),
    prodUrl: urls[1].replace(/\/+$/, ''),
    pages,
  };
}

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

function percent(value) {
  return `${(value * 100).toFixed(2)}%`;
}

function inferNotes(result) {
  if (result.changed_ratio === 0) {
    return {
      summary: 'Pixel-identical in this run.',
      review: 'No layout, spacing, typography, or responsive regression was detected.',
    };
  }
  if (result.region_metrics.top_ratio > 0.2 && result.region_metrics.body_ratio < 0.01) {
    return {
      summary: 'Likely hero-only false positive.',
      review: 'The diff is concentrated in the top quarter of the page, which is typical of a rotating hero, carousel, or time-based banner rather than a body-content regression.',
    };
  }
  if (result.changed_ratio >= 0.15) {
    return {
      summary: 'Substantial body-level visual change detected.',
      review: 'The diff extends well beyond the hero area into page body content. Review typography scale, line wrapping, spacing, and image placement.',
    };
  }
  if (result.changed_ratio >= 0.05) {
    return {
      summary: 'Moderate visual change detected.',
      review: 'The page shows noticeable visual movement. Review image swaps, section spacing, and text wrapping to confirm whether the change is intentional.',
    };
  }
  return {
    summary: 'Minor visual change detected.',
    review: 'The diff is limited, but still worth a quick review for small spacing, rendering, or content differences.',
  };
}

function htmlEscape(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildMarkdownReport(spec, results, relativeOutputDir) {
  const lines = [];
  lines.push('# Visual Regression Report');
  lines.push('');
  lines.push(`Project: ${spec.projectName}`);
  lines.push(`Test URL: ${spec.testUrl}`);
  lines.push(`Prod URL: ${spec.prodUrl}`);
  lines.push(`Output folder: ${relativeOutputDir}`);
  lines.push('');
  lines.push('| Page | Viewport | Diff | Notes |');
  lines.push('| --- | --- | ---: | --- |');
  for (const result of results) {
    const notes = inferNotes(result);
    lines.push(`| \`${result.page}\` | ${result.viewport} | ${percent(result.changed_ratio)} | ${notes.summary} |`);
  }
  lines.push('');
  lines.push('## Findings');
  lines.push('');
  for (const result of results) {
    const notes = inferNotes(result);
    lines.push(`### ${result.page} (${result.viewport})`);
    lines.push('');
    lines.push(`- Pixel diff: ${percent(result.changed_ratio)} (${result.changed_pixels.toLocaleString()} changed pixels)`);
    lines.push(`- Assessment: ${notes.summary}`);
    lines.push(`- Review note: ${notes.review}`);
    lines.push(`- Top-quarter diff: ${percent(result.region_metrics.top_ratio)}`);
    lines.push(`- Body diff: ${percent(result.region_metrics.body_ratio)}`);
    lines.push(`- Test screenshot: \`${path.relative(relativeOutputDir, result.test_screenshot)}\``);
    lines.push(`- Prod screenshot: \`${path.relative(relativeOutputDir, result.prod_screenshot)}\``);
    lines.push(`- Diff image: \`${path.relative(relativeOutputDir, result.diff_image)}\``);
    lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

function buildHtmlReport(spec, results) {
  const rows = results.map((result) => `
    <tr>
      <td><code>${htmlEscape(result.page)}</code></td>
      <td>${htmlEscape(result.viewport)}</td>
      <td>${percent(result.changed_ratio)}</td>
      <td>${htmlEscape(inferNotes(result).summary)}</td>
    </tr>
  `).join('');

  const sections = results.map((result) => {
    const notes = inferNotes(result);
    const testPath = htmlEscape(path.relative(result.output_dir, result.test_screenshot));
    const prodPath = htmlEscape(path.relative(result.output_dir, result.prod_screenshot));
    const diffPath = htmlEscape(path.relative(result.output_dir, result.diff_image));
    return `
      <section class="result">
        <h2><code>${htmlEscape(result.page)}</code> <span>${htmlEscape(result.viewport)}</span></h2>
        <p><strong>Pixel diff:</strong> ${percent(result.changed_ratio)} (${result.changed_pixels.toLocaleString()} changed pixels)</p>
        <p><strong>Assessment:</strong> ${htmlEscape(notes.summary)}</p>
        <p><strong>Review note:</strong> ${htmlEscape(notes.review)}</p>
        <p><strong>Top-quarter diff:</strong> ${percent(result.region_metrics.top_ratio)} | <strong>Body diff:</strong> ${percent(result.region_metrics.body_ratio)}</p>
        <div class="grid">
          <figure>
            <figcaption>Test</figcaption>
            <img src="${testPath}" loading="lazy" alt="Test screenshot for ${htmlEscape(result.page)} ${htmlEscape(result.viewport)}">
          </figure>
          <figure>
            <figcaption>Production</figcaption>
            <img src="${prodPath}" loading="lazy" alt="Production screenshot for ${htmlEscape(result.page)} ${htmlEscape(result.viewport)}">
          </figure>
          <figure>
            <figcaption>Diff</figcaption>
            <img src="${diffPath}" loading="lazy" alt="Diff screenshot for ${htmlEscape(result.page)} ${htmlEscape(result.viewport)}">
          </figure>
        </div>
      </section>
    `;
  }).join('');

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${htmlEscape(spec.projectName)} Visual Regression Report</title>
  <style>
    :root {
      --bg: #f3f6f8;
      --panel: #ffffff;
      --ink: #12212f;
      --muted: #5b6b79;
      --accent: #005ea8;
      --border: #d6e0e8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #e8eef3 0%, var(--bg) 220px);
    }
    main {
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }
    .hero, .panel, .result {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(18, 33, 47, 0.06);
    }
    .hero {
      padding: 28px;
      margin-bottom: 24px;
    }
    h1, h2 { margin: 0 0 12px; }
    h1 { font-size: 32px; }
    h2 {
      font-size: 22px;
      display: flex;
      gap: 12px;
      align-items: baseline;
      flex-wrap: wrap;
    }
    h2 span {
      font-size: 14px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    p, li { line-height: 1.5; }
    .meta {
      color: var(--muted);
      margin: 0;
    }
    .panel {
      padding: 20px;
      margin-bottom: 24px;
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 12px 10px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .result {
      padding: 20px;
      margin-bottom: 24px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(240px, 1fr));
      gap: 16px;
    }
    figure {
      margin: 0;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #fafcfd;
      overflow: hidden;
    }
    figcaption {
      padding: 10px 12px;
      font-size: 13px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      background: #f6f9fb;
    }
    img {
      display: block;
      width: 100%;
      height: auto;
    }
    code {
      background: #eef4f8;
      padding: 2px 6px;
      border-radius: 6px;
    }
    @media (max-width: 900px) {
      .grid {
        grid-template-columns: 1fr;
      }
      h1 {
        font-size: 26px;
      }
    }
  </style>
</head>
<body>
  <header>
    <img src="agency-logo.svg" title="Agency Logo" style="max-width: 75px;width: 100%;margin: 0 auto;margin-bottom: 40px;">
  </header>
  <main>
    <section class="hero">
      <h1>${htmlEscape(spec.projectName)} Visual Regression Report</h1>
      <p class="meta">Test URL: ${htmlEscape(spec.testUrl)}</p>
      <p class="meta">Production URL: ${htmlEscape(spec.prodUrl)}</p>
      <p class="meta">Desktop viewport: 1440x1200 | Mobile viewport: 390x844</p>
    </section>
    <section class="panel">
      <table>
        <thead>
          <tr>
            <th>Page</th>
            <th>Viewport</th>
            <th>Diff</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </section>
    ${sections}
  </main>
</body>
</html>`;
}

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
  const cwd = process.cwd();
  const webDir = path.join(cwd, 'web');
  await ensureDir(webDir);
  const outputDir = path.join(webDir, `${spec.projectName}-${buildTimestamp()}`);
  const screenshotDir = path.join(outputDir, 'screenshots');
  const diffDir = path.join(outputDir, 'diffs');
  await ensureDir(screenshotDir);
  await ensureDir(diffDir);
  await fs.copyFile(bundledLogoPath, path.join(outputDir, 'agency-logo.svg'));

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

        results.push({
          page,
          viewport: viewportName,
          dimensions: viewport,
          test_screenshot: testPath,
          prod_screenshot: prodPath,
          diff_image: diffPath,
          output_dir: outputDir,
          ...metrics,
        });
      }
    }
  } finally {
    await browser.close();
  }

  await fs.writeFile(path.join(outputDir, 'metrics.json'), JSON.stringify(results, null, 2));
  await fs.writeFile(path.join(outputDir, 'report.md'), buildMarkdownReport(spec, results, outputDir));
  await fs.writeFile(path.join(outputDir, 'report.html'), buildHtmlReport(spec, results));
  console.log(outputDir);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
