// Live inbox: new messages move their chat to the top and update its
// preview and unread count, without refreshing the page.

const list = document.getElementById("chat-list");
let socket = null;

// Turn an HTML string from the server into a page element.
function toElement(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

function connect() {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${scheme}://${location.host}${list.dataset.socketUrl}`);

  socket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);
    const row = document.getElementById(`chat-${data.id}`);

    if (data.type === "inbox.row") {
      const newRow = toElement(data.html);
      if (data.to_top || !row) {
        // A new message: move the chat (or add a brand-new one) to the top.
        row?.remove();
        list.prepend(newRow);
        document.getElementById("no-chats")?.remove();
      } else {
        row.replaceWith(newRow); // same place, fresh unread count
      }
    } else if (data.type === "inbox.remove") {
      row?.remove();
    }
  });

  // Try again a few seconds after the connection drops.
  socket.addEventListener("close", () => {
    socket = null;
    setTimeout(connect, 3000);
  });
}

// Check in every 30 seconds so we keep showing as online.
setInterval(() => {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "ping" }));
  }
}, 30000);

connect();