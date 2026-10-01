const EN = document.documentElement.lang === "en";
const DATA = EN ? "/data" : "../data";
const COOKIE = EN ? "cftf-en" : "cftf";
const SESSION = EN ? "cftf-reading-en" : "cftf-reading";
const COPY = EN
  ? {
      upright: "Upright",
      reversed: "Reversed",
      meaningFallback: "The picture on this card is today's sign.",
      renewed: "All twenty-two cards have been drawn, so the deck is whole again.",
      hintReveal: "Tap again, and today's color opens",
      hintDraw: "Tap to draw a card",
      drawLabel: "Draw a card",
      openLabel: "Tap again to open the color",
      mirror: "A mirror holding the color",
      scene: "A picture with a mirror holding the color",
      cardError: "The card did not open. Tap once more.",
      colorError: "Today's color did not open. Tap once more.",
      testError: "test looks like 4-10. Cards run from 1 to 22. Colors 1 to 10 are upright, 11 to 20 reversed.",
    }
  : {
      upright: "正位置",
      reversed: "逆位置",
      meaningFallback: "このカードの絵が、今日の象徴です。",
      renewed: "二十二枚を引き終えたので、山を戻しました。",
      hintReveal: "もう一度タップすると、今日の色が開きます",
      hintDraw: "タップして、一枚引く",
      drawLabel: "カードを引く",
      openLabel: "もう一度タップして色を開く",
      mirror: "中央に色を映す鏡",
      scene: "中央に色を映す鏡の絵",
      cardError: "カードを開けませんでした。もう一度タップしてください。",
      colorError: "今日の色を開けませんでした。もう一度タップしてください。",
      testError: "test は 4-10 の形です。カードは1から22、色は正位置が1から10、逆位置が11から20です。",
    };
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
const ORIENTATION = { upright: COPY.upright, reversed: COPY.reversed };

function colorFile(color) {
  return EN ? color.textEn : color.text;
}

function colorShare() {
  const slug = String(colorFile(state.color) || "").replace(/\.en\.txt$/i, "").replace(/\.txt$/i, "");
  const pageUrl = `${SITE}${EN ? "/en" : ""}/cards/${state.card.id}/${slug}/index.html`;
  const shareText = EN
    ? `Today's lucky color is ${state.color.name}.`
    : `今日のラッキーカラーは、${state.color.nameJa}です。`;
  return { slug, pageUrl, shareText };
}

function cardTitle(card) {
  return EN ? card.name : card.nameJa;
}
const FRESH = "v=3";
const FACE_VIDEO = {
  "the-fool": "face.mp4",
  "the-chariot": "face.mp4",
  strength: "face.mp4",
  justice: "face.mp4",
  temperance: "face.mp4",
  judgement: "face.mp4",
};

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
const library = document.querySelector("#library");
const libraryLink = document.querySelector("#library-link");
const shareCopy = document.querySelector("#share-copy");
const shareX = document.querySelector("#share-x");
const shareLine = document.querySelector("#share-line");
const copied = document.querySelector("#copied");
const error = document.querySelector("#error");
const SITE = "https://colorsofthefool.engawa5656.com";
let copiedTimer = 0;

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
  const response = await fetch(`${DATA}/${id}/card.json?${FRESH}`, { cache: "no-cache" });
  if (!response.ok) throw new Error("card");
  return response.json();
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function fillProse(parent, text, dropTitle) {
  parent.replaceChildren();
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  if (dropTitle && /[―—-]\s*(正位置|逆位置|Upright|Reversed)\s*$/.test(lines[0] || "")) lines.shift();
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
    const reveal = block.some((line) => line.startsWith("今日のラッキーカラー") || line.startsWith("Today's lucky color") || line.startsWith("Lucky Color:"));
    if (reveal) {
      paragraph.className = "reveal";
      seenReveal = true;
    } else if (seenReveal) {
      paragraph.className = "afterword";
    }
    let chipJustAdded = false;
    block.forEach((line, index) => {
      if (index && !chipJustAdded) paragraph.append(document.createElement("br"));
      chipJustAdded = false;
      paragraph.append(document.createTextNode(line));
      const matched = line.match(/^Lucky Color:\s*.*(#[0-9A-Fa-f]{6})\s*$/);
      if (!matched) return;
      const chip = document.createElement("span");
      chip.className = "color-chip";
      chip.style.backgroundColor = matched[1];
      chip.setAttribute("aria-hidden", "true");
      paragraph.append(chip);
      chipJustAdded = true;
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
  mirror.setAttribute("aria-label", COPY.mirror);
  scene.append(mirror);
}

function showScene() {
  scene.replaceChildren();
  if (!state.color.image) {
    showMirror(state.color.hex);
    return;
  }
  const image = document.createElement("img");
  image.alt = COPY.scene;
  image.src = `${DATA}/${state.card.id}/${state.color.image}?${FRESH}`;
  image.addEventListener("error", () => showMirror(state.color.hex));
  scene.append(image);
}

let pendingVideo = null;

function clearFaceVideo() {
  faceMotion += 1;
  pendingVideo?.remove();
  pendingVideo = null;
  faceTurn.querySelector("video")?.remove();
  faceTurn.classList.remove("reversed");
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve(image);
    };
    image.onload = finish;
    image.onerror = () => {
      if (settled) return;
      settled = true;
      reject(new Error("image"));
    };
    image.src = url;
    if (image.complete && image.naturalWidth > 0) finish();
  });
}

function openFaceVideo(id, file) {
  faceMotion += 1;
  const video = document.createElement("video");
  video.muted = true;
  video.defaultMuted = true;
  video.setAttribute("muted", "");
  video.playsInline = true;
  video.setAttribute("playsinline", "");
  video.preload = "auto";
  video.style.cssText = "position:fixed;left:-9999px;width:320px;height:480px;opacity:0;pointer-events:none";
  const motion = faceMotion;
  const drop = () => {
    if (motion !== faceMotion) return;
    if (pendingVideo === video) pendingVideo = null;
    video.remove();
  };
  video.addEventListener("ended", drop);
  video.addEventListener("error", drop);
  video.dataset.face = `${id}/${file}`;
  video.src = `${DATA}/${id}/${file}?${FRESH}`;
  pendingVideo = video;
  document.body.append(video);
  video.play().catch(() => {});
}

function showFace(playVideo) {
  const drawnLabel = ORIENTATION[state.orientation];
  const jpg = `${DATA}/${state.card.id}/face.jpg`;
  face.hidden = false;
  if (!face.src.endsWith(`${state.card.id}/face.jpg`)) face.src = jpg;
  face.alt = `${cardTitle(state.card)}, ${drawnLabel}`;
  faceTurn.classList.toggle("reversed", state.orientation === "reversed");
  const videoFile = state.card.video;
  const canPlay = playVideo && typeof videoFile === "string" && videoFile.toLowerCase().endsWith(".mp4") && !reduceMotion();
  const primed = pendingVideo
    && pendingVideo.isConnected
    && pendingVideo.dataset.face === `${state.card.id}/${videoFile}`;
  if (!canPlay) {
    if (!faceTurn.querySelector("video")) {
      pendingVideo?.remove();
      pendingVideo = null;
    }
    return;
  }
  if (faceTurn.querySelector("video") || primed) return;
  openFaceVideo(state.card.id, videoFile);
}

function mountFaceVideo() {
  const video = pendingVideo;
  if (!video || !video.isConnected) return;
  pendingVideo = null;
  video.style.cssText = "";
  faceTurn.append(video);
  const start = () => video.play().catch(() => {});
  if (video.readyState >= 2) start();
  else video.addEventListener("loadeddata", start, { once: true });
}

function armVideoAfterFlip(motion) {
  const inner = cardButton.querySelector(".card-inner");
  let finished = false;
  const done = () => {
    if (finished || motion !== faceMotion) return;
    if (!cardButton.classList.contains("is-flipped")) return;
    finished = true;
    inner.removeEventListener("transitionend", onEnd);
    mountFaceVideo();
  };
  const onEnd = (event) => {
    if (event.target !== inner || event.propertyName !== "transform") return;
    done();
  };
  inner.addEventListener("transitionend", onEnd);
  window.setTimeout(done, 800);
}

function paint(animated) {
  const drawnLabel = ORIENTATION[state.orientation];
  cardButton.classList.toggle("no-motion", !animated);
  cardButton.classList.toggle("is-open", state.phase === "revealed");
  showFace(animated);
  title.textContent = cardTitle(state.card);
  en.textContent = EN ? state.card.nameJa : state.card.name;
  orientationEl.textContent = drawnLabel;
  const text = window.MEANINGS?.[state.card.id]?.[state.orientation];
  fillProse(meaning, text || COPY.meaningFallback, false);
  reading.hidden = false;
  notice.hidden = !state.renewed;
  notice.textContent = state.renewed ? COPY.renewed : "";
  const revealed = state.phase === "revealed";
  hint.hidden = revealed;
  hint.textContent = COPY.hintReveal;
  colorPanel.hidden = !revealed;
  cardButton.setAttribute("aria-label", revealed ? `${cardTitle(state.card)}, ${drawnLabel}` : COPY.openLabel);
  if (revealed) {
    showScene();
    fillProse(story, state.story || "", true);
    const shared = colorShare();
    libraryLink.href = `cards/${state.card.id}/${shared.slug}/index.html`;
    shareX.href = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shared.shareText)}&url=${encodeURIComponent(shared.pageUrl)}`;
    shareLine.href = `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(shared.pageUrl)}`;
    copied.hidden = true;
    library.hidden = false;
  } else {
    library.hidden = true;
  }
  const flip = () => {
    cardButton.classList.add("is-flipped");
    if (animated) {
      requestAnimationFrame(() => cardButton.classList.remove("no-motion"));
      if (pendingVideo) armVideoAfterFlip(faceMotion);
    } else {
      cardButton.classList.remove("no-motion");
    }
  };
  if (animated) requestAnimationFrame(() => requestAnimationFrame(flip));
  else flip();
}

let guideMotion = 0;
let faceMotion = 0;

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
  cardButton.setAttribute("aria-label", COPY.drawLabel);
  reading.hidden = true;
  colorPanel.hidden = true;
  notice.hidden = true;
  hint.hidden = false;
  hint.textContent = COPY.hintDraw;
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

function parseTestQueue() {
  const raw = new URLSearchParams(location.search).get("test");
  if (!raw) return [];
  const specs = [];
  for (const part of raw.split(",")) {
    const match = part.trim().match(/^(\d+)-(\d+)$/);
    if (!match) return null;
    const card = Number(match[1]);
    const color = Number(match[2]);
    if (card < 1 || card > DECK.length || color < 1 || color > 20) return null;
    specs.push({ card, color });
  }
  return specs;
}

const TEST_ERROR = COPY.testError;
let testQueue = parseTestQueue();

async function draw() {
  if (isLocked()) return;
  busy = true;
  showError("");
  if (testQueue === null) {
    showError(TEST_ERROR);
    busy = false;
    return;
  }
  const spec = testQueue[0] || null;
  let drawn = readDrawn();
  let pool = DECK.filter((id) => !drawn.includes(id));
  let renewed = false;
  if (!spec && pool.length === 0) {
    drawn = [];
    pool = DECK.slice();
    renewed = true;
  }
  const id = spec ? DECK[spec.card - 1] : pick(pool);
  if (FACE_VIDEO[id] && !reduceMotion()) openFaceVideo(id, FACE_VIDEO[id]);
  cardButton.classList.add("is-waiting");
  try {
    const card = await fetchCard(id);
    let orientation;
    let color;
    if (spec) {
      orientation = spec.color <= 10 ? "upright" : "reversed";
      color = card[orientation]?.[spec.color <= 10 ? spec.color - 1 : spec.color - 11];
      if (!color) throw new Error("colors");
    } else {
      orientation = Math.random() < 0.5 ? "upright" : "reversed";
      const colors = card[orientation];
      if (!Array.isArray(colors) || colors.length === 0) throw new Error("colors");
      color = pick(colors);
    }
    const jpg = `${DATA}/${id}/face.jpg`;
    await loadImage(jpg);
    state = { card, orientation, color, phase: "reading", renewed, story: "" };
    face.src = jpg;
    face.alt = `${cardTitle(card)}, ${ORIENTATION[orientation]}`;
    faceTurn.classList.toggle("reversed", orientation === "reversed");
    if (face.decode) await face.decode().catch(() => {});
    cardButton.classList.remove("is-waiting");
    if (spec) testQueue.shift();
    else writeDrawn([...drawn, id]);
    saveSession();
    foldGuide();
    paint(true);
    lock(750);
  } catch {
    faceMotion += 1;
    pendingVideo?.remove();
    pendingVideo = null;
    cardButton.classList.remove("is-waiting");
    showError(COPY.cardError);
  } finally {
    busy = false;
  }
}

async function reveal() {
  if (isLocked() || !state || state.phase !== "reading") return;
  busy = true;
  showError("");
  try {
    const file = colorFile(state.color);
    if (!file) throw new Error("text");
    const response = await fetch(`${DATA}/${state.card.id}/${file}`);
    if (!response.ok) throw new Error("text");
    state.story = await response.text();
    state.phase = "revealed";
    saveSession();
    paint(false);
    story.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch {
    showError(COPY.colorError);
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
async function copyUrl(url) {
  try {
    await navigator.clipboard.writeText(url);
    return;
  } catch {}
  const area = document.createElement("textarea");
  area.value = url;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  area.remove();
  if (!ok) throw new Error("copy failed");
}

shareCopy.addEventListener("click", async () => {
  if (!state || state.phase !== "revealed") return;
  try {
    await copyUrl(colorShare().pageUrl);
  } catch {
    return;
  }
  copied.hidden = false;
  clearTimeout(copiedTimer);
  copiedTimer = setTimeout(() => {
    copied.hidden = true;
  }, 2200);
});

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
      const file = colorFile(color);
      if (!file) throw new Error("text");
      const response = await fetch(`${DATA}/${card.id}/${file}`);
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

if (testQueue === null) {
  showError(TEST_ERROR);
  showGuide();
} else if (testQueue.length) {
  showGuide();
} else {
  restore();
}
