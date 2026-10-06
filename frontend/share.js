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
    showToast("已複製連結，可以貼給朋友了");
  } catch {
    window.prompt("請複製這個連結：", url);
  }
}

document.getElementById("share-site")?.addEventListener("click", () => share(location.origin + "/", "英文句子骨架分析"));
