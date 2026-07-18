/* AI BOT FUNCTIONS */

let chatSending = false;

// One conversation ID per browser tab, persisted via sessionStorage so a
// page refresh doesn't lose context (a new tab gets a fresh one). This is
// what lets the backend remember prior messages -- without it, every
// message would be treated as a totally isolated question with no idea
// what "it" or "that race" refers to.
function getConversationId() {
    let id = sessionStorage.getItem("otter_chat_conversation_id");
    if (!id) {
        id = (crypto.randomUUID ? crypto.randomUUID() : `chat-${Date.now()}-${Math.random()}`);
        sessionStorage.setItem("otter_chat_conversation_id", id);
    }
    return id;
}

async function sendMessage() {

    if (chatSending) return;  // guard against double-send while a request is in flight

    const input = document.getElementById("message");
    const text = input.value.trim();

    if (!text) return;

    chatSending = true;
    input.disabled = true;

    appendMessage(text, "user");
    input.value = "";

    const thinkingEl = appendMessage("...", "ai");

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                conversation_id: getConversationId()
            })
        });

        if (!response.ok) {
            throw new Error(`Server responded ${response.status}`);
        }

        const data = await response.json();

        thinkingEl.textContent = data.response;

    } catch (err) {
        thinkingEl.textContent = "Something went wrong -- try again.";
        thinkingEl.classList.add("chat-msg-error");
        console.error("Chat error:", err);
    } finally {
        chatSending = false;
        input.disabled = false;
        input.focus();
    }
}

function appendMessage(text, role) {

    const messages = document.getElementById("messages");

    const el = document.createElement("div");
    el.className = `chat-msg chat-msg-${role}`;
    el.textContent = text;  // textContent, not innerHTML -- never parsed as HTML, so nothing typed can break layout or inject markup

    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;  // auto-scroll to the newest message

    return el;
}

// Send on Enter, same as most chat UIs
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("message").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
});
