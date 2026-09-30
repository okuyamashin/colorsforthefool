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
const faceTurn = document.querySelector("#face-turn");
const face = document.querySelector("#face");
const notice = document.querySelector("#notice");
const hint = document.querySelector("#hint");
const reading = document.querySelector("#reading");
const title = document.querySelector("#title");
const en = document.querySelector("#en");
const orientationEl = document.querySelector("#orientation");
const meaning = document.querySelector("#meaning");
const sheet = document.querySelector("#sheet");
const guide = document.querySelector("#guide");
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

function clearFaceVideo() {
  faceTurn.querySelector("video")?.remove();
  faceTurn.classList.remove("reversed");
}

function showFace(playVideo) {
  const drawnLabel = ORIENTATION[state.orientation];
  const jpg = `${DATA}/${state.card.id}/face.jpg`;
  face.hidden = false;
  face.src = jpg;
  face.alt = `${state.card.nameJa}、${drawnLabel}`;
  faceTurn.classList.toggle("reversed", state.orientation === "reversed");
  const existing = faceTurn.querySelector("video");
  const videoFile = state.card.video;
  const canPlay = playVideo && typeof videoFile === "string" && videoFile.toLowerCase().endsWith(".mp4") && !reduceMotion();
  if (!canPlay || existing) return;
  const video = document.createElement("video");
  video.muted = true;
  video.defaultMuted = true;
  video.playsInline = true;
  video.setAttribute("playsinline", "");
  video.preload = "auto";
  video.src = `${DATA}/${state.card.id}/${videoFile}`;
  const drop = () => video.remove();
  video.addEventListener("ended", drop);
  video.addEventListener("error", drop);
  faceTurn.append(video);
  video.play().catch(drop);
}

function paint(animated) {
  const drawnLabel = ORIENTATION[state.orientation];
  cardButton.classList.toggle("no-motion", !animated);
  cardButton.classList.add("is-flipped");
  cardButton.classList.toggle("is-open", state.phase === "revealed");
  showFace(animated);
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
  requestAnimationFrame(() => cardButton.classList.remove("no-motion"));
}

let guideMotion = 0;

function reduceMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function hideGuide() {
  guide.classList.remove("is-folding");
  guide.classList.add("is-folded");
  guide.style.height = "";
  guide.setAttribute("aria-hidden", "true");
}

function foldGuide() {
  if (guide.classList.contains("is-folded") || guide.classList.contains("is-folding")) return;
  const motion = ++guideMotion;
  if (reduceMotion()) {
    hideGuide();
    return;
  }
  guide.style.height = `${guide.scrollHeight}px`;
  guide.offsetHeight;
  guide.classList.add("is-folding");
  let finished = false;
  const done = () => {
    if (finished || motion !== guideMotion) return;
    finished = true;
    hideGuide();
  };
  guide.addEventListener("transitionend", (event) => {
    if (event.target === guide && event.propertyName === "height") done();
  }, { once: true });
  window.setTimeout(done, 900);
}

function showGuide() {
  document.documentElement.classList.remove("has-reading");
  if (!guide.classList.contains("is-folded") && !guide.classList.contains("is-folding")) return;
  const motion = ++guideMotion;
  guide.classList.remove("is-folding", "is-folded");
  guide.removeAttribute("aria-hidden");
  if (reduceMotion()) {
    guide.style.height = "";
    return;
  }
  guide.style.height = "0px";
  const target = guide.scrollHeight;
  guide.offsetHeight;
  guide.style.height = `${target}px`;
  const done = () => {
    if (motion !== guideMotion) return;
    guide.style.height = "";
  };
  guide.addEventListener("transitionend", (event) => {
    if (event.target === guide && event.propertyName === "height") done();
  }, { once: true });
  window.setTimeout(done, 900);
}

function returnToDeck() {
  state = null;
  saveSession();
  clearFaceVideo();
  cardButton.classList.remove("is-flipped", "is-open");
  cardButton.setAttribute("aria-label", "カードを引く");
  reading.hidden = true;
  colorPanel.hidden = true;
  notice.hidden = true;
  hint.hidden = false;
  hint.textContent = "タップして、一枚引く";
  showError("");
  showGuide();
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
  if (reduce || reduceMotion()) {
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
    foldGuide();
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
    hideGuide();
  } catch {
    sessionStorage.removeItem(SESSION);
    returnToDeck();
  }
}

restore();
