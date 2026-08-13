import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  createSlideContext,
  ensureArtifactToolWorkspace,
  importArtifactTool,
  importModuleFresh,
  padSlideNumber,
  resolveSlideFunction,
  saveBlobToFile,
  slideNumberFromModuleName,
} from "/Users/yunye/.codex/plugins/cache/openai-primary-runtime/presentations/26.614.11602/skills/presentations/scripts/artifact_tool_utils.mjs";

const workspace = "/Users/yunye/Desktop/hoop-insight/outputs/019ec98c-5dd0-7132-9e42-21800e648b55/presentations/hoop-insight-ppt";
const slidesDir = path.join(workspace, "slides");
const previewDir = path.join(workspace, "preview");
const layoutDir = path.join(workspace, "layout", "final");
const outputDir = path.join(workspace, "output");
const finalPptx = path.join(outputDir, "hoop-insight-nba-analytics-ai.pptx");
const slideSize = { width: 1280, height: 720 };

async function discoverSlideModules() {
  const entries = await fs.readdir(slidesDir);
  return entries
    .filter((entry) => /^slide[-_]?\d+\.mjs$/i.test(entry))
    .map((entry) => ({
      path: path.join(slidesDir, entry),
      slideNumber: slideNumberFromModuleName(entry),
    }))
    .sort((a, b) => a.slideNumber - b.slideNumber);
}

async function main() {
  await ensureArtifactToolWorkspace(workspace);
  const artifact = await importArtifactTool(workspace);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize });
  const modules = await discoverSlideModules();

  if (modules.length !== 6) {
    throw new Error(`Expected 6 slide modules, found ${modules.length}.`);
  }

  const records = [];
  for (const mod of modules) {
    const module = await importModuleFresh(mod.path);
    const { name, fn } = resolveSlideFunction(module, undefined, mod.slideNumber);
    const ctx = createSlideContext(artifact, {
      slideSize,
      slideNumber: mod.slideNumber,
      outputDir,
      assetDir: path.join(workspace, "assets"),
      workspaceDir: workspace,
      titleFont: "PingFang SC",
      bodyFont: "PingFang SC",
    });
    const beforeCount = presentation.slides.count;
    const slide = await fn(presentation, ctx);
    if (presentation.slides.count !== beforeCount + 1) {
      throw new Error(`${path.basename(mod.path)} must add exactly one slide.`);
    }
    records.push({ ...mod, exportName: name, slide });
  }

  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });
  await fs.mkdir(outputDir, { recursive: true });

  for (let i = 0; i < records.length; i += 1) {
    const stem = `slide-${padSlideNumber(i + 1)}`;
    const png = await presentation.export({ slide: records[i].slide, format: "png", scale: 1 });
    await saveBlobToFile(png, path.join(previewDir, `${stem}.png`));
    const layout = await records[i].slide.export({ format: "layout" });
    await fs.writeFile(path.join(layoutDir, `${stem}.layout.json`), await layout.text(), "utf8");
  }

  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await saveBlobToFile(montage, path.join(previewDir, "deck-montage.webp"));

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(finalPptx);
  const stat = await fs.stat(finalPptx);
  const manifest = {
    output: finalPptx,
    outputBytes: stat.size,
    slideCount: presentation.slides.count,
    slideSize,
    previews: records.map((_, i) => path.join(previewDir, `slide-${padSlideNumber(i + 1)}.png`)),
    montage: path.join(previewDir, "deck-montage.webp"),
    slides: records.map((record) => ({
      modulePath: record.path,
      exportName: record.exportName,
    })),
  };
  await fs.writeFile(path.join(outputDir, "artifact-build-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
