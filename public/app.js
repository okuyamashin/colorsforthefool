const DATA = "../data";
const COOKIE = "cftf";
const SESSION = "cftf-reading";
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
const ORIENTATION = { upright: "正位置", reversed: "逆位置" };

const cardButton = document.querySelector("#card");
const face = document.querySelector("#face");
const count = document.querySelector("#count");
const notice = document.querySelector("#notice");
const hint = document.querySelector("#hint");
const reading = document.querySelector("#reading");
const title = document.querySelector("#title");
const en = document.querySelector("#en");
const orientationEl = document.querySelector("#orientation");
const meaning = document.querySelector("#meaning");
const sheet = document.querySelector("#sheet");
const colorPanel = document.querySelector("#color");
const scene = document.querySelector("#scene");
const story = document.querySelector("#story");
const error = document.querySelector("#error");

let state = null;
let lockedUntil = 0;
let busy = false;

function readDrawn() {
  const found = document.cookie.split("; ").find((part) => part.startsWith(`${COOKIE}=`));
  if (!found) return [];
  try {
    const ids = JSON.parse(decodeURIComponent(found.slice(COOKIE.length + 1)));
    if (!Array.isArray(ids)) return [];
    return [...new Set(ids.filter((id) => DECK.includes(id)))];
  } catch {
    return [];
  }
}

function writeDrawn(ids) {
  const value = encodeURIComponent(JSON.stringify(ids));
  document.cookie = `${COOKIE}=${value}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

function saveSession() {
  if (!state) {
    sessionStorage.removeItem(SESSION);
    return;
  }
  sessionStorage.setItem(SESSION, JSON.stringify({
    id: state.card.id,
    orientation: state.orientation,
    color: state.color.name,
    phase: state.phase,
    renewed: state.renewed,
  }));
}

function lock(ms) {
  lockedUntil = Date.now() + ms;
}

function isLocked() {
  return busy || Date.now() < lockedUntil;
}

function showError(message) {
  error.hidden = !message;
  error.textContent = message || "";
}

async function fetchCard(id) {
  const response = await fetch(`${DATA}/${id}/card.json`);
  if (!response.ok) throw new Error("card");
  return response.json();
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function renderCount() {
  count.textContent = `残り ${DECK.length - readDrawn().length} 枚`;
}

function fillProse(parent, text, dropTitle) {
  parent.replaceChildren();
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  if (dropTitle && /[―—-]\s*(正位置|逆位置)\s*$/.test(lines[0] || "")) lines.shift();
  const blocks = [];
  let buffer = [];
  const flush = () => {
    if (buffer.length) blocks.push(buffer);
    buffer = [];
  };
  for (const line of lines) {
    if (line.trim() === "") flush();
    else buffer.push(line);
  }
  flush();
  let seenReveal = false;
  for (const block of blocks) {
    const paragraph = document.createElement("p");
    const reveal = block.some((line) => line.startsWith("今日のラッキーカラー") || line.startsWith("Lucky Color:"));
    if (reveal) {
      paragraph.className = "reveal";
      seenReveal = true;
    } else if (seenReveal) {
      paragraph.className = "afterword";
    }
    block.forEach((line, index) => {
      if (index) paragraph.append(document.createElement("br"));
      paragraph.append(document.createTextNode(line));
    });
    parent.append(paragraph);
  }
}

function showMirror(hex) {
  scene.replaceChildren();
  const mirror = document.createElement("div");
  mirror.className = "mirror";
  mirror.style.setProperty("--mirror", hex);
  mirror.setAttribute("role", "img");
  mirror.setAttribute("aria-label", "中央に色を映す鏡");
  scene.append(mirror);
}

function showScene() {
  scene.replaceChildren();
  if (!state.color.image) {
    showMirror(state.color.hex);
    return;
  }
  const image = document.createElement("img");
  image.alt = "中央に色を映す鏡の絵";
  image.src = `${DATA}/${state.card.id}/${state.color.image}`;
  image.addEventListener("error", () => showMirror(state.color.hex));
  scene.append(image);
}

function paint(animated) {
  const drawnLabel = ORIENTATION[state.orientation];
  cardButton.classList.toggle("no-motion", !animated);
  cardButton.classList.add("is-flipped");
  cardButton.classList.toggle("is-open", state.phase === "revealed");
  face.src = `${DATA}/${state.card.id}/face.jpg`;
  face.alt = `${state.card.nameJa}、${drawnLabel}`;
  face.classList.toggle("reversed", state.orientation === "reversed");
  title.textContent = state.card.nameJa;
  en.textContent = state.card.name;
  orientationEl.textContent = drawnLabel;
  const text = window.MEANINGS?.[state.card.id]?.[state.orientation];
  fillProse(meaning, text || "このカードの絵が、今日の象徴です。", false);
  reading.hidden = false;
  notice.hidden = !state.renewed;
  notice.textContent = state.renewed ? "二十二枚を引き終えたので、山を戻しました。" : "";
  const revealed = state.phase === "revealed";
  hint.hidden = revealed;
  hint.textContent = "もう一度タップすると、今日の色が開きます";
  colorPanel.hidden = !revealed;
  cardButton.setAttribute("aria-label", revealed ? `${state.card.nameJa}、${drawnLabel}` : "もう一度タップして色を開く");
  if (revealed) {
    showScene();
    fillProse(story, state.story || "", true);
  }
  renderCount();
  requestAnimationFrame(() => cardButton.classList.remove("no-motion"));
}

function returnToDeck() {
  state = null;
  saveSession();
  cardButton.classList.remove("is-flipped", "is-open");
  cardButton.setAttribute("aria-label", "カードを引く");
  reading.hidden = true;
  colorPanel.hidden = true;
  notice.hidden = true;
  hint.hidden = false;
  hint.textContent = "タップして、一枚引く";
  showError("");
  renderCount();
}

function foldAway() {
  if (isLocked() || !state || state.phase !== "revealed") return;
  busy = true;
  cardButton.classList.remove("is-flipped", "is-open");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let finished = false;
  const done = () => {
    if (finished) return;
    finished = true;
    returnToDeck();
    sheet.classList.remove("is-folding");
    sheet.style.height = "";
    busy = false;
  };
  if (reduce) {
    window.scrollTo({ top: 0 });
    done();
    return;
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
  sheet.style.height = `${sheet.scrollHeight}px`;
  sheet.offsetHeight;
  sheet.classList.add("is-folding");
  sheet.addEventListener("transitionend", (event) => {
    if (event.target === sheet && event.propertyName === "height") done();
  });
  window.setTimeout(done, 900);
}

async function draw() {
  if (isLocked()) return;
  busy = true;
  showError("");
  let drawn = readDrawn();
  let pool = DECK.filter((id) => !drawn.includes(id));
  let renewed = false;
  if (pool.length === 0) {
    drawn = [];
    pool = DECK.slice();
    renewed = true;
  }
  const id = pick(pool);
  try {
    const card = await fetchCard(id);
    const orientation = Math.random() < 0.5 ? "upright" : "reversed";
    const colors = card[orientation];
    if (!Array.isArray(colors) || colors.length === 0) throw new Error("colors");
    state = { card, orientation, color: pick(colors), phase: "reading", renewed, story: "" };
    writeDrawn([...drawn, id]);
    saveSession();
    paint(true);
    lock(750);
  } catch {
    showError("カードを開けませんでした。もう一度タップしてください。");
  } finally {
    busy = false;
  }
}

async function reveal() {
  if (isLocked() || !state || state.phase !== "reading") return;
  busy = true;
  showError("");
  try {
    const response = await fetch(`${DATA}/${state.card.id}/${state.color.text}`);
    if (!response.ok) throw new Error("text");
    state.story = await response.text();
    state.phase = "revealed";
    saveSession();
    paint(false);
    story.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch {
    showError("今日の色を開けませんでした。もう一度タップしてください。");
  } finally {
    busy = false;
  }
}

function onTap() {
  if (!state) draw();
  else if (state.phase === "reading") reveal();
}

cardButton.addEventListener("click", onTap);
hint.addEventListener("click", onTap);
scene.addEventListener("click", foldAway);

async function restore() {
  renderCount();
  const saved = sessionStorage.getItem(SESSION);
  if (!saved) return;
  try {
    const data = JSON.parse(saved);
    if (!DECK.includes(data.id) || !ORIENTATION[data.orientation]) throw new Error("session");
    const card = await fetchCard(data.id);
    const color = card[data.orientation]?.find((item) => item.name === data.color);
    if (!color) throw new Error("color");
    state = {
      card,
      orientation: data.orientation,
      color,
      phase: data.phase === "revealed" ? "revealed" : "reading",
      renewed: Boolean(data.renewed),
      story: "",
    };
    if (state.phase === "revealed") {
      const response = await fetch(`${DATA}/${card.id}/${color.text}`);
      if (!response.ok) throw new Error("text");
      state.story = await response.text();
    }
    paint(false);
  } catch {
    sessionStorage.removeItem(SESSION);
    returnToDeck();
  }
}

restore();
