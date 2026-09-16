const W = 800;
const H = 1000;

/** Draws the mascot SVG on an 800×1000 brand gradient with the chest label and saves it as PNG. */
export function exportMascotPng(
  svg: SVGSVGElement,
  brand: { primary: string; secondary: string; label: string },
  filename: string,
) {
  const xml = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const gradient = ctx.createLinearGradient(0, 0, 0, H);
    gradient.addColorStop(0, brand.primary);
    gradient.addColorStop(1, brand.secondary);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, W, H);

    const ih = H * 0.78;
    const iw = ih * (160 / 248);
    ctx.drawImage(img, (W - iw) / 2, H * 0.1, iw, ih);

    ctx.textAlign = "center";
    ctx.fillStyle = brand.secondary;
    ctx.font = `600 ${Math.round(ih * 0.072)}px Instrument Sans, Helvetica, sans-serif`;
    ctx.fillText(brand.label, W / 2, H * 0.1 + ih * 0.62);
    ctx.fillStyle = "rgba(0,0,0,.45)";
    ctx.font = "500 20px JetBrains Mono, monospace";
    ctx.fillText("DEMO DATA · неофициальный мерч", W / 2, H - 34);

    const link = document.createElement("a");
    link.download = filename;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };
  img.src = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(xml)))}`;
}
