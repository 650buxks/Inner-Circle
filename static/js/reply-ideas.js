// Clique AI helpers above the message box:
// - "Help me reply" shows a few replies as buttons. Tapping one puts it in
//   the message box.
// - "Write it for me" writes a message the way you ask ("say no politely").
// Nothing is ever sent for you: you can edit the text, then press Send.

const ideas = document.getElementById("reply-ideas");

if (ideas) {
  const button = document.getElementById("reply-ideas-button");
  const list = document.getElementById("reply-ideas-list");
  const writeToggle = document.getElementById("write-toggle");
  const writeBox = document.getElementById("write-box");
  const writeRequest = document.getElementById("write-request");
  const writeButton = document.getElementById("write-button");
  const textarea = document.querySelector("#send textarea");
  const csrfToken = document.querySelector("#send [name=csrfmiddlewaretoken]").value;
  const errorBox = document.getElementById("chat-error");
  const usesLeft = document.getElementById("ai-uses-left");
  let lastDraft = null; // the last message Clique AI wrote into the box

  function showError(text) {
    errorBox.textContent = text;
    errorBox.classList.toggle("d-none", !text);
  }

  // Put text in the message box, ready to edit or send.
  function fillMessageBox(text) {
    textarea.value = text;
    textarea.focus();
    // Tells chat.js we're typing, so friends see "… is typing".
    textarea.dispatchEvent(new Event("input"));
    textarea.form.scrollIntoView({ block: "end" });
  }

  // Grow the message box to fit longer messages (up to a limit set in
  // clique.css), and shrink it back after sending.
  function fitMessageBox() {
    textarea.style.height = "auto";
    if (textarea.value) {
      textarea.style.height = `${textarea.scrollHeight + 2}px`;
    }
  }
  textarea.addEventListener("input", fitMessageBox);
  // After chat.js has sent the message and emptied the box.
  textarea.form.addEventListener("submit", () => setTimeout(fitMessageBox));

  // POST to one of the Clique AI URLs. Returns the JSON answer, or null
  // after showing the error.
  async function askClique(url, fields = {}) {
    showError("");
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: new URLSearchParams(fields),
      });
      const data = await response.json();
      if (response.ok) {
        usesLeft.textContent = data.uses_left;
        return data;
      }
      showError(data.error || "Something went wrong.");
    } catch {
      showError("Couldn't reach Clique AI. Check your connection.");
    }
    return null;
  }

  // Disable a button and show "Thinking…" on it while `work` runs.
  async function whileThinking(target, work) {
    const label = target.textContent;
    target.disabled = true;
    target.textContent = "✨ Thinking…";
    try {
      await work();
    } finally {
      target.disabled = false;
      target.textContent = label;
    }
  }

  // --- Help me reply ----------------------------------------------------

  function showReplies(replies) {
    list.replaceChildren();
    for (const reply of replies) {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "btn btn-light btn-sm reply-idea";
      choice.textContent = reply; // textContent, so it can't add HTML
      choice.addEventListener("click", () => {
        fillMessageBox(reply);
        list.replaceChildren();
      });
      list.append(choice);
    }
    textarea.form.scrollIntoView({ block: "end" }); // keep the ideas in view
  }

  // Missing when smart replies are turned off in settings.
  button?.addEventListener("click", () =>
    whileThinking(button, async () => {
      const data = await askClique(ideas.dataset.url);
      if (data) {
        showReplies(data.replies);
      }
    }),
  );

  // --- Write it for me --------------------------------------------------

  writeToggle.addEventListener("click", () => {
    writeBox.classList.toggle("d-none");
    if (!writeBox.classList.contains("d-none")) {
      writeRequest.focus();
      textarea.form.scrollIntoView({ block: "end" });
    }
  });

  function write() {
    return whileThinking(writeButton, async () => {
      // If you typed something yourself, Clique AI rewrites it. If the box
      // holds its own last draft, pressing Write again means "try again".
      const typed = textarea.value.trim();
      const draft = typed && typed !== lastDraft ? typed : "";
      const data = await askClique(ideas.dataset.draftUrl, {
        request: writeRequest.value,
        draft,
      });
      if (data) {
        lastDraft = data.draft;
        fillMessageBox(data.draft);
      }
    }).then(() => {
      if (lastDraft) {
        writeButton.textContent = "Try again"; // after the label comes back
      }
    });
  }

  writeButton.addEventListener("click", write);
  writeRequest.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault(); // don't send the chat message
      write();
    }
  });
  // A new request starts over.
  writeRequest.addEventListener("input", () => {
    writeButton.textContent = "Write";
  });

  ideas.classList.remove("d-none"); // JavaScript works, so show the buttons
}
