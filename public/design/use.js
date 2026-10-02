const DESIGN_COOKIE = "cftf-design";
const DESIGNS = [
  "ancient-egypt",
  "botanical-art",
  "brutalist-graphic",
  "editorial-luxury",
  "engraving",
  "french-doll",
  "gear-engine-robotics",
  "greek-sculpture",
  "rorschach",
];
const USE_LABEL = "これを使う";
const STOP_LABEL = "使用をやめる";

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
