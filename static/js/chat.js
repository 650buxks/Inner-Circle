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
  const presence = document.getElementById("presence");
  const photoInput = document.getElementById("photo-input");
  const photoChosen = document.getElementById("photo-chosen");
  const MAX_PHOTO_SIZE = 10 * 1024 * 1024; // 10 MB, the same as the server
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

  // "Online" and "2 online" are green; "Last seen …" is grey.
  function showPresence(text) {
    presence.textContent = text;
    const online = text.toLowerCase().includes("online");
    presence.classList.toggle("text-success", online);
    presence.classList.toggle("text-body-secondary", !online);
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
      } else if (data.type === "presence") {
        showPresence(data.text);
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

  // Show which photo is about to be sent, and stop files that are too big
  // before they're uploaded.
  photoInput.addEventListener("change", () => {
    const photo = photoInput.files[0];
    if (photo && photo.size > MAX_PHOTO_SIZE) {
      photoInput.value = "";
      showError("Photos can be at most 10 MB.");
      photoChosen.textContent = "";
      return;
    }
    showError("");
    photoChosen.textContent = photo ? `📷 ${photo.name} will be sent` : "";
  });

  form.addEventListener("submit", (event) => {
    if (photoInput.files.length) {
      return; // photos are uploaded by posting the form normally
    }
    if (!textarea.value.trim()) {
      event.preventDefault(); // nothing to send
      return;
    }
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

  // Check in every 30 seconds so we keep showing as online.
  setInterval(() => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "ping" }));
    }
  }, 30000);

  connect();
  scrollToBottom();
}