// 分享：上方選單的「分享」每一頁都有；首頁結果下方的「分享這個分析」也用這裡的 share()
// 頁面上沒有提示框（#toast）時自動補一個，複製連結後才有地方顯示「已複製」

// action：{ label, onClick } 時在提示後面加一個按鈕（例如「復原」），提示多停留一下讓人來得及按
function showToast(message, action) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("p");
    toast.id = "toast";
    toast.className = "toast";
    toast.setAttribute("role", "status");
    document.querySelector("main").prepend(toast);
  }
  toast.textContent = message;
  if (action) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "toast-action";
    btn.textContent = action.label;
    btn.addEventListener("click", () => {
      toast.hidden = true;
      action.onClick();
    });
    toast.append(btn);
  }
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, action ? 6000 : 2500);
}

async function share(url, title) {
  if (navigator.share) {
    try {
      await navigator.share({ title, url });
      return;
    } catch (err) {
      if (err.name === "AbortError") return; // 使用者自己取消
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    showToast("連結複製好了，去分享給朋友吧（順便幫偵探貓打廣告）。");
  } catch {
    window.prompt("請複製這個連結：", url);
  }
}

document.getElementById("share-site")?.addEventListener("click", () => share(location.origin + "/", "英文句子骨架分析"));

// 手機上的漢堡選單：點按鈕開關；點選單外面、按 Esc、選了項目都會收起來
(() => {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".site-nav");
  if (!toggle || !nav) return;
  function setOpen(open) {
    nav.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "關閉選單" : "選單");
  }
  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("open")));
  document.addEventListener("click", (e) => {
    if (nav.classList.contains("open") && !nav.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && nav.classList.contains("open")) {
      setOpen(false);
      toggle.focus();
    }
  });
  nav.querySelector(".nav-links").addEventListener("click", (e) => {
    if (e.target.closest("a, button")) setOpen(false);
  });
})();

// 右下角的貓爪按鈕：往下捲一段之後出現，點了回到最上面
(() => {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "to-top";
  btn.setAttribute("aria-label", "回到最上面");
  btn.title = "回到最上面";
  btn.innerHTML = '<svg viewBox="0 0 48 48" aria-hidden="true">'
    + '<ellipse cx="9.5" cy="21" rx="4.6" ry="6" transform="rotate(-22 9.5 21)"/>'
    + '<ellipse cx="18.5" cy="11.5" rx="4.8" ry="6.3" transform="rotate(-8 18.5 11.5)"/>'
    + '<ellipse cx="29.5" cy="11.5" rx="4.8" ry="6.3" transform="rotate(8 29.5 11.5)"/>'
    + '<ellipse cx="38.5" cy="21" rx="4.6" ry="6" transform="rotate(22 38.5 21)"/>'
    + '<path d="M24 22.5c-6.8 0-13.5 7.5-13.5 13.2 0 4.2 3.1 6.8 6.9 6.8 2.7 0 4.3-1.4 6.6-1.4s3.9 1.4 6.6 1.4c3.8 0 6.9-2.6 6.9-6.8 0-5.7-6.7-13.2-13.5-13.2z"/>'
    + '<path class="to-top-arrow" d="M24 39.5v-9.5M19.8 34l4.2-4.2 4.2 4.2"/>'
    + "</svg>";
  document.body.append(btn);
  const update = () => btn.classList.toggle("show", window.scrollY > window.innerHeight * 0.6);
  window.addEventListener("scroll", update, { passive: true });
  update();
  btn.addEventListener("click", () => {
    const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: smooth ? "smooth" : "auto" });
    document.querySelector(".brand")?.focus({ preventScroll: true }); // 鍵盤使用者回到頁首，從選單開始
  });
})();
