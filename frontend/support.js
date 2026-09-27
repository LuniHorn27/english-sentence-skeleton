// 「請我喝杯咖啡」：site-config.js 設定了 Buy Me a Coffee 網址才顯示。
// 只放連結，不載入 Buy Me a Coffee 的外部程式（不追蹤訪客、網頁也比較快）。
(() => {
  const url = (window.SITE_CONFIG || {}).coffeeUrl || "";
  if (!/^https:\/\/(www\.)?buymeacoffee\.com\/[\w.-]+\/?$/.test(url)) return;
  for (const card of document.querySelectorAll(".coffee-card")) {
    card.querySelector(".coffee-btn").href = url;
    card.hidden = false;
  }
})();
