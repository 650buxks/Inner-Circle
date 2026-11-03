// Clique AI buttons above the message box:
// - "Write it for me": one tap writes a reply from the latest messages
//   and photos. Tap again for a different one.
// - "Help me reply": type what you need. Requests ("say no politely") get
//   a draft; questions ("what time did we agree on?") get a private answer.
// Nothing is ever sent for you: you can edit the text, then press Send.

const tools = document.getElementById("ai-tools");

if (tools) {
  const writeButton = document.getElementById("write-button");
  const helpToggle = document.getElementById("help-toggle");
  const helpBox = document.getElementById("help-box");
  const helpRequest = document.getElementById("help-request");
  const helpButton = document.getElementById("help-button");
  const helpSteps = document.getElementById("help-steps");
  const helpAnswer = document.getElementById("help-answer");
  const usesLeft = document.getElementById("ai-uses-left");
  const textarea = document.querySelector("#send textarea");
  const csrfToken = document.querySelector("#send [name=csrfmiddlewaretoken]").value;
  const errorBox = document.getElementById("chat-error");
  let lastWritten = ""; // the last reply "Write it for me" put in the box

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

  // --- Write it for me --------------------------------------------------

  // Missing when it's turned off in settings.
  writeButton?.addEventListener("click", () =>
    whileThinking(writeButton, async () => {
      // If the box still holds the last reply, tapping again means "give
      // me a different one", so tell Clique AI what not to repeat.
      const previous = textarea.value === lastWritten ? lastWritten : "";
      const data = await askClique(tools.dataset.writeUrl, { previous });
      if (data) {
        lastWritten = data.draft;
        fillMessageBox(data.draft);
      }
    }),
  );

  // --- Help me reply ----------------------------------------------------

  helpToggle.addEventListener("click", () => {
    helpBox.classList.toggle("d-none");
    if (!helpBox.classList.contains("d-none")) {
      helpRequest.focus();
      textarea.form.scrollIntoView({ block: "end" });
    }
  });

  // Show what the agent looked up, e.g. "🔎 Searched the chat for “trip”".
  function showSteps(steps) {
    helpSteps.replaceChildren();
    for (const step of steps) {
      const item = document.createElement("li");
      item.textContent = step; // textContent, so it can't add HTML
      helpSteps.append(item);
    }
  }

  function showAnswer(text) {
    helpAnswer.textContent = text ? `✨ ${text}` : "";
    helpAnswer.classList.toggle("d-none", !text);
    if (text) {
      textarea.form.scrollIntoView({ block: "end" }); // keep it in view
    }
  }

  function askForHelp() {
    return whileThinking(helpButton, async () => {
      showSteps([]);
      showAnswer("");
      const data = await askClique(tools.dataset.helpUrl, {
        request: helpRequest.value,
      });
      if (!data) {
        return;
      }
      showSteps(data.steps);
      if (data.answer) {
        showAnswer(data.answer); // only this person sees it
      } else {
        fillMessageBox(data.draft);
      }
    });
  }

  helpButton.addEventListener("click", askForHelp);
  helpRequest.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault(); // don't send the chat message
      askForHelp();
    }
  });

  tools.classList.remove("d-none"); // JavaScript works, so show the buttons
}
