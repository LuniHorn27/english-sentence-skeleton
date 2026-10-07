// 關於偵探貓頁：標題區的偵探貓。探頭（CSS 播一次）之後偷看一次，之後每 10 秒左右再偷看一次。
// 系統設定「減少動態」時不偷看（CSS 也會讓探頭直接停在定位）。
(() => {
  const cat = document.querySelector(".peek-cat");
  if (!cat || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const glance = () => {
    if (document.hidden) return;
    cat.classList.remove("glance");
    void cat.getBoundingClientRect(); // 重新開始動畫
    cat.classList.add("glance");
  };
  setTimeout(glance, 1400);
  setInterval(glance, 10000);
})();
