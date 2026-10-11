// 關於偵探貓頁：標題區的偵探貓。
// 1. 滑鼠靠近貓（離貓的範圍 56px 內）時，放大鏡裡的眼睛變成「？」；只有滑鼠的裝置才有。
// 2. 探頭（CSS 播一次，約 2.9 秒）之後偷看一次，之後每 10 秒左右再偷看一次。
//    系統設定「減少動態」時不偷看（CSS 也會讓探頭直接停在定位）。
(() => {
  const cat = document.querySelector(".peek-cat");
  if (!cat) return;

  if (window.matchMedia("(hover: hover)").matches) {
    const NEAR = 56;
    let x = -1e4, y = -1e4, frame = 0;
    const check = () => {
      frame = 0;
      const r = cat.getBoundingClientRect();
      const dx = Math.max(r.left - x, 0, x - r.right);
      const dy = Math.max(r.top - y, 0, y - r.bottom);
      cat.classList.toggle("curious", Math.hypot(dx, dy) < NEAR);
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(check); };
    window.addEventListener("pointermove", (e) => { x = e.clientX; y = e.clientY; schedule(); }, { passive: true });
    window.addEventListener("scroll", schedule, { passive: true }); // 滑鼠不動、頁面捲動時貓也會靠近或離開
    document.documentElement.addEventListener("mouseleave", () => { x = y = -1e4; schedule(); });
  }

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const glance = () => {
    if (document.hidden) return;
    cat.classList.remove("glance");
    void cat.getBoundingClientRect(); // 重新開始動畫
    cat.classList.add("glance");
  };
  setTimeout(glance, 3200);
  setInterval(glance, 10000);
})();
