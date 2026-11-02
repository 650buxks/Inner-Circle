// "Help me reply": asks Clique AI for a few replies and shows them as
// buttons. Tapping one puts it in the message box, ready to edit or send.

const ideas = document.getElementById("reply-ideas");

if (ideas) {
  const button = document.getElementById("reply-ideas-button");
  const list = document.getElementById("reply-ideas-list");
  const textarea = document.querySelector("#send textarea");
  const csrfToken = document.querySelector("#send [name=csrfmiddlewaretoken]").value;
  const errorBox = document.getElementById("chat-error");

  function showError(text) {
    errorBox.textContent = text;
    errorBox.classList.toggle("d-none", !text);
  }

  function showReplies(replies) {
    list.replaceChildren();
    for (const reply of replies) {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "btn btn-light btn-sm reply-idea";
      choice.textContent = reply; // textContent, so it can't add HTML
      choice.addEventListener("click", () => {
        textarea.value = reply;
        textarea.focus();
        // Tells chat.js we're typing, so friends see "… is typing".
        textarea.dispatchEvent(new Event("input"));
        list.replaceChildren();
      });
      list.append(choice);
    }
    textarea.form.scrollIntoView({ block: "end" }); // keep the ideas in view
  }

  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "✨ Thinking…";
    showError("");
    try {
      const response = await fetch(ideas.dataset.url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
      });
      const data = await response.json();
      if (response.ok) {
        showReplies(data.replies);
      } else {
        showError(data.error || "Something went wrong.");
      }
    } catch {
      showError("Couldn't reach Clique AI. Check your connection.");
    } finally {
      button.disabled = false;
      button.textContent = "✨ Help me reply";
    }
  });

  ideas.classList.remove("d-none"); // JavaScript works, so show the button
}
