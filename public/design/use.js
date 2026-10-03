const DESIGN_COOKIE = "cftf-design";
const DESIGNS = [
  "ancient-egypt",
  "art-nouveau",
  "botanical-art",
  "brutalist-graphic",
  "chess-pieces",
  "classic-tarot",
  "colored-pencil",
  "cubism",
  "cyber-mysticism",
  "editorial-luxury",
  "engraving",
  "french-doll",
  "gear-engine-robotics",
  "glass-and-chrome",
  "greek-sculpture",
  "japanese-contemporary-poster",
  "luxury-ui",
  "mezzotint",
  "minimal-geometric",
  "neo-deco",
  "neo-symbolism",
  "plastic-model-diorama",
  "rorschach",
  "ruler-compass-pen",
  "stained-glass",
  "suit-and-dress",
  "sumi-e",
  "surreal-photography",
  "tile-mosaic",
  "unkei-kaikei",
  "watercolor",
  "wayang-kulit",
];
const USE_LABEL = designButtonLabel("use", "これを使う");
const STOP_LABEL = designButtonLabel("stop", "使用をやめる");

function designButtonLabel(key, fallback) {
  const button = document.querySelector("#design-use");
  const value = button?.dataset[key];
  return value || fallback;
}

function readDesign() {
  const found = document.cookie.split("; ").find((part) => part.startsWith(`${DESIGN_COOKIE}=`));
  if (!found) return "";
  try {
    const value = decodeURIComponent(found.slice(DESIGN_COOKIE.length + 1));
    return DESIGNS.includes(value) ? value : "";
  } catch {
    return "";
  }
}

function writeDesign(value) {
  const body = value
    ? `${DESIGN_COOKIE}=${encodeURIComponent(value)}; Path=/; Max-Age=31536000; SameSite=Lax`
    : `${DESIGN_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  document.cookie = body;
}

const designButton = document.querySelector("#design-use");
if (designButton && DESIGNS.includes(designButton.dataset.design)) {
  const id = designButton.dataset.design;
  const paintDesign = () => {
    designButton.textContent = readDesign() === id ? STOP_LABEL : USE_LABEL;
  };
  designButton.addEventListener("click", () => {
    writeDesign(readDesign() === id ? "" : id);
    paintDesign();
  });
  paintDesign();
}
