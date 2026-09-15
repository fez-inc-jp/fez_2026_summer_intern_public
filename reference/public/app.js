// 固定値・DOM 要素
const API = "/api/chat";
const sidebar = document.querySelector("aside nav ul");
const result = document.getElementById("result");
const form = document.getElementById("data-fetch-form");
const invalidHelper = document.getElementById("invalid-helper");
const promptInput = document.getElementById("prompt");
const promptSubmit = document.getElementById("prompt-submit");
const titleDialog = document.getElementById("title-dialog");
const titleInput = document.getElementById("title-input");
const titleSave = document.getElementById("title-save");
const deleteDialog = document.getElementById("delete-dialog");
const deleteSubmit = document.getElementById("delete-submit");

// アプリケーションの状態
let isSubmitting = false;
// POST 結果を現在の画面へ反映するか。履歴移動後は false
let shouldApplyResult = false;

// 一覧を取得し、サイドバーにタイトルのリンクを並べる
async function loadList() {
  const chats = await fetch(API).then((r) => r.json());
  sidebar.replaceChildren(
    ...chats.map((chat) => {
      const a = document.createElement("a");
      a.href = `/chat/${chat.id}`;
      a.className = "secondary";
      a.textContent = chat.title;
      const li = document.createElement("li");
      li.append(a);
      return li;
    }),
  );
}

// タイトル編集・削除ボタンを Pico の group で横並びにする
function createActions(chat, heading) {
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "outline";
  edit.textContent = "タイトルを編集";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "outline secondary";
  remove.textContent = "このチャットを削除";

  const actions = document.createElement("div");
  actions.setAttribute("role", "group");
  actions.append(edit, remove);

  // タイトル更新モーダルを開き、更新処理を行う
  edit.onclick = () => {
    invalidHelper.textContent = "";
    titleInput.value = chat.title;
    titleInput.removeAttribute("aria-invalid");

    titleSave.onclick = async () => {
      // 空タイトルの場合はエラー表示させる
      const title = titleInput.value.trim();
      if (!title) {
        titleInput.setAttribute("aria-invalid", "true");
        return;
      }

      try {
        titleSave.setAttribute("aria-busy", "true");
        const response = await fetch(`${API}/${chat.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
        });
        if (!response.ok) {
          throw new Error(`タイトルの更新に失敗しました: ${response.status}`);
        }

        chat.title = title;
        heading.textContent = title;
        await loadList();
        highlightActive();
      } catch (error) {
        console.error(error);
        invalidHelper.textContent =
          "予期せぬエラーが発生しました。開発者にお問い合わせください";
      } finally {
        titleSave.removeAttribute("aria-busy");
        titleDialog.close();
      }
    };

    titleDialog.showModal();
  };

  // 確認モーダルを開き、削除時の処理を行う。削除後は新規 (空) 状態へ戻す
  remove.onclick = () => {
    invalidHelper.textContent = "";

    deleteSubmit.onclick = async () => {
      try {
        deleteSubmit.setAttribute("aria-busy", "true");

        // 204 No Content が返るためレスポンス本文は読まない
        const response = await fetch(`${API}/${chat.id}`, { method: "DELETE" });
        if (!response.ok) {
          throw new Error(`チャットの削除に失敗しました: ${response.status}`);
        }

        history.replaceState({}, "", "/");
        await loadList();
        await route();
      } catch (error) {
        console.error(error);
        invalidHelper.textContent =
          "予期せぬエラーが発生しました。開発者にお問い合わせください";
      } finally {
        deleteSubmit.removeAttribute("aria-busy");
        deleteDialog.close();
      }
    };

    deleteDialog.showModal();
  };

  return actions;
}

// chat の内容を result に描画する
function render(chat) {
  const { columns, rows, summary, sql } = chat.result;
  result.replaceChildren();

  const h = document.createElement("h3");
  h.textContent = chat.title;

  const table = document.createElement("table");

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    headRow.append(th);
  });
  thead.append(headRow);
  table.append(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const bodyRow = document.createElement("tr");
    row.forEach((c) => {
      const td = document.createElement("td");
      td.textContent = c;
      bodyRow.append(td);
    });
    tbody.append(bodyRow);
  });
  table.append(tbody);

  const p = document.createElement("p");
  p.textContent = summary;

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.textContent = sql;
  pre.append(code);

  result.append(h, table, p, pre, createActions(chat, h));
}

// フォームの有効/無効を切り替える
function setFormEnabled(enabled) {
  promptInput.disabled = !enabled;
  promptSubmit.disabled = !enabled;
}

// ナビゲーションリンクの aria-disabled を切り替える
function setNavigationDisabled(disabled) {
  document.querySelectorAll("aside a[href^='/']").forEach((a) => {
    if (disabled) {
      a.setAttribute("aria-disabled", "true");
    } else {
      a.removeAttribute("aria-disabled");
    }
  });
}

// 現在 URL と一致する履歴項目をハイライトする
function highlightActive() {
  sidebar.querySelectorAll("a").forEach((a) => {
    if (a.getAttribute("href") === location.pathname) {
      a.removeAttribute("class");
    } else {
      a.setAttribute("class", "secondary");
    }
  });
}

// URL を見てビューを決めて描画する (初期ロード・遷移・戻る/進むで呼ぶ)
async function route() {
  invalidHelper.textContent = "";
  promptInput.removeAttribute("aria-invalid");

  const m = location.pathname.match(/^\/chat\/(.+)$/);
  if (m) {
    // 既存チャット表示（読み取り専用）
    const chat = await fetch(`${API}/${m[1]}`).then((r) => r.json());
    promptInput.value = chat.prompt;
    setFormEnabled(false);
    render(chat);
  } else {
    // 新規（空）状態
    result.replaceChildren();
    promptInput.value = "";
    setFormEnabled(true);
  }
  highlightActive();
}

// アプリ内リンクは通常遷移を止め、pushState でルーティングする (リロード無し)
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[href^='/']");
  if (!a) return;
  e.preventDefault();

  // メッセージ送信中は遷移を止める
  if (isSubmitting) {
    return;
  }

  const href = a.getAttribute("href");
  if (href !== location.pathname) {
    history.pushState({}, "", href);
    route();
  }
});

// data-close を持つボタンは、自身が属するモーダルを閉じる
document.querySelectorAll("dialog [data-close]").forEach((button) => {
  button.onclick = () => button.closest("dialog").close();
});

// ブラウザの戻る/進むに追従する
window.addEventListener("popstate", () => {
  // 処理中に戻る/進むが押された場合はメイン画面の描画を止める
  if (isSubmitting) {
    shouldApplyResult = false;
    promptSubmit.removeAttribute("aria-busy");
  }

  route();
});

// プロンプトを送信し、作成されたチャットの URL へ遷移して描画する
form.onsubmit = async (e) => {
  e.preventDefault();

  // 念のため、すでに送信中なら何もしない
  if (isSubmitting) return;

  invalidHelper.textContent = "";
  promptInput.removeAttribute("aria-invalid");

  isSubmitting = true;
  shouldApplyResult = true;

  setNavigationDisabled(true);

  let created = false;

  try {
    promptSubmit.setAttribute("aria-busy", "true");
    setFormEnabled(false);

    const response = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptInput.value }),
    });
    const data = await response.json();

    if (response.ok) {
      created = true;

      if (shouldApplyResult) {
        history.pushState({}, "", `/chat/${data.id}`);
        promptInput.value = data.prompt;
        render(data);
        setFormEnabled(false);
      }
    } else if (
      response.status === 422 &&
      data.detail?.code === "SQL_GENERATION_DECLINED"
    ) {
      if (shouldApplyResult) {
        invalidHelper.textContent = data.detail.message;
        promptInput.setAttribute("aria-invalid", "true");
        setFormEnabled(true);
      }
    } else {
      // SQL 生成拒否以外は予期しない失敗として catch で共通処理する
      throw new Error(`chat の作成に失敗しました: ${response.status}`);
    }
  } catch (error) {
    console.error(error);

    if (shouldApplyResult) {
      invalidHelper.textContent =
        "予期せぬエラーが発生しました。開発者にお問い合わせください";
      setFormEnabled(true);
    }
  } finally {
    promptSubmit.removeAttribute("aria-busy");
    isSubmitting = false;
    shouldApplyResult = false;
    setNavigationDisabled(false);
  }

  // 現在画面への反映有無にかかわらず、POST 成功時はサイドバーを更新
  if (created) {
    try {
      await loadList();
      highlightActive();
    } catch (error) {
      console.error(error);
    }
  }
};

// 初期表示: 一覧を並べてから現在 URL を描画する
loadList().then(route);
