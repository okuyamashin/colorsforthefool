const share = document.querySelector(".share");
const shareCopy = document.querySelector("#share-copy");
const copied = document.querySelector("#copied");

if (share && shareCopy && copied) {
  const pageUrl = share.dataset.url;
  let copiedTimer = 0;

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
    try {
      await copyUrl(pageUrl);
    } catch {
      return;
    }
    copied.hidden = false;
    clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => {
      copied.hidden = true;
    }, 2200);
  });
}
