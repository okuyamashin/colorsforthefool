const langMenu = document.querySelector(".lang-menu");
const langToggle = langMenu?.querySelector(".lang");
const langList = langMenu?.querySelector(".lang-list");
if (langMenu && langToggle && langList) {
  const closeLanguages = () => {
    langToggle.setAttribute("aria-expanded", "false");
    langList.hidden = true;
  };
  langToggle.addEventListener("click", () => {
    const open = langToggle.getAttribute("aria-expanded") === "true";
    langToggle.setAttribute("aria-expanded", String(!open));
    langList.hidden = open;
  });
  document.addEventListener("click", (event) => {
    if (langToggle.getAttribute("aria-expanded") !== "true") return;
    if (langMenu.contains(event.target)) return;
    event.stopPropagation();
    closeLanguages();
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || langToggle.getAttribute("aria-expanded") !== "true") return;
    closeLanguages();
    langToggle.focus();
  });
}
