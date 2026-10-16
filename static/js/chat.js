// Live chat: new messages, edits and deletes show up without refreshing.
// Without JavaScript (or if the connection drops) the form still works the
// old way, by posting and reloading the page.

const form = document.getElementById("send");
const socketUrl = form.dataset.socketUrl;

if (socketUrl) {
  const messages = document.getElementById("messages");
  const textarea = form.querySelector("textarea");
  const errorBox = document.getElementById("chat-error");
  const receipt = document.getElementById("read-receipt");
  const typing = document.getElementById("typing");
  const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;
  let socket = null;
  let typingTimer = null; // hides "… is typing" when they stop
  let lastTypingSent = 0; // when we last told others we're typing

  // Turn an HTML string from the server into a page element.
  function toElement(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    const element = template.content.firstElementChild;
    // Messages drawn by the WebSocket have no CSRF token, so add ours.
    element.querySelectorAll("[name=csrfmiddlewaretoken]").forEach((input) => {
      input.value = csrfToken;
    });
    return element;
  }

  function scrollToBottom() {
    form.scrollIntoView({ block: "end" });
  }

  function showError(text) {
    errorBox.textContent = text;
    errorBox.classList.toggle("d-none", !text);
  }

  // Show "Jordan is typing…", and hide it if no update comes for 3 seconds.
  function showTyping(text) {
    typing.textContent = text;
    clearTimeout(typingTimer);
    if (text) {
      typingTimer = setTimeout(() => showTyping(""), 3000);
    }
  }

  function connect() {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${location.host}${socketUrl}`);

    socket.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "message.new") {
        document.getElementById("no-messages")?.remove();
        messages.append(toElement(data.html));
        receipt.textContent = ""; // nobody has seen the new message yet
        showTyping("");
        scrollToBottom();
      } else if (data.type === "typing") {
        showTyping(`${data.name} is typing…`);
      } else if (data.type === "receipt") {
        receipt.textContent = data.text;
      } else if (data.type === "message.changed") {
        document.getElementById(`message-${data.id}`)
          ?.replaceWith(toElement(data.html));
      } else if (data.type === "error") {
        showError(data.message);
      }
    });

    // Try again a few seconds after the connection drops.
    socket.addEventListener("close", () => {
      socket = null;
      setTimeout(connect, 3000);
    });
  }

  form.addEventListener("submit", (event) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return; // not connected: let the form post normally
    }
    event.preventDefault();
    socket.send(JSON.stringify({ type: "message", body: textarea.value }));
    textarea.value = "";
    lastTypingSent = 0;
    showError("");
  });

  // Tell others we're typing, but at most once every 2 seconds.
  textarea.addEventListener("input", () => {
    const now = Date.now();
    if (socket?.readyState === WebSocket.OPEN && now - lastTypingSent > 2000) {
      socket.send(JSON.stringify({ type: "typing" }));
      lastTypingSent = now;
    }
  });

  // Enter sends, Shift+Enter makes a new line.
  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  connect();
  scrollToBottom();
}