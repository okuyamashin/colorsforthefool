const DECK = [
  "the-fool",
  "the-magician",
  "the-high-priestess",
  "the-empress",
  "the-emperor",
  "the-hierophant",
  "the-lovers",
  "the-chariot",
  "strength",
  "the-hermit",
  "wheel-of-fortune",
  "justice",
  "the-hanged-man",
  "death",
  "temperance",
  "the-devil",
  "the-tower",
  "the-star",
  "the-moon",
  "the-sun",
  "judgement",
  "the-world",
];

const cardButton = document.querySelector("#card");
const face = document.querySelector("#face");
const hintWrap = document.querySelector("#hint-wrap");
const reading = document.querySelector("#reading");
const title = document.querySelector("#title");
const en = document.querySelector("#en");
const meaning = document.querySelector("#meaning");
const notice = document.querySelector("#notice");

let open = false;
let busy = false;

function reduceMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function showError(message) {
  notice.hidden = !message;
  notice.textContent = message || "";
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(src);
    image.onerror = () => reject(new Error("image"));
    image.src = src;
  });
}

function parseReading(text) {
  const [head, body] = text.trim().split(/\n\n/, 2);
  const match = head.match(/^(.+?)（(.+?)）/);
  if (!match || !body) throw new Error("reading");
  return { nameJa: match[1], nameEn: match[2], body };
}

async function draw() {
  if (busy || open) return;
  busy = true;
  showError("");
  cardButton.classList.add("is-waiting");
  const id = pick(DECK);
  try {
    const response = await fetch(`${id}.txt`);
    if (!response.ok) throw new Error("reading");
    const readingText = parseReading(await response.text());
    const src = `img/${id}.jpg`;
    await loadImage(src);
    face.src = src;
    face.alt = `${readingText.nameJa}、正位置`;
    title.textContent = readingText.nameJa;
    en.textContent = readingText.nameEn;
    meaning.textContent = readingText.body;
    cardButton.classList.add("is-flipped");
    cardButton.classList.add("is-open");
    hintWrap.hidden = true;
    reading.hidden = false;
    open = true;
  } catch {
    showError("カードを開けませんでした。もう一度タップしてください。");
  } finally {
    cardButton.classList.remove("is-waiting");
    busy = false;
  }
}

function closeReading() {
  if (!open || busy) return;
  open = false;
  cardButton.classList.remove("is-flipped");
  cardButton.classList.remove("is-open");
  reading.hidden = true;
  hintWrap.hidden = false;
  const top = document.querySelector(".stage");
  if (reduceMotion()) window.scrollTo(0, top.offsetTop);
  else top.scrollIntoView({ behavior: "smooth", block: "center" });
}

if (reduceMotion()) cardButton.classList.add("no-motion");
cardButton.addEventListener("click", draw);
document.querySelector("#hint").addEventListener("click", draw);
document.querySelector("#close").addEventListener("click", closeReading);
