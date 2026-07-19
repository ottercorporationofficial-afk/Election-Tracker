/* AI BOT FUNCTIONS */

let chatSending = false;

// One conversation ID per browser/device, persisted via localStorage so
// it survives closing the tab or browser entirely (sessionStorage would
// wipe it on tab close). Still scoped to this one browser/device --
// a different browser or clearing site data starts fresh.
function getConversationId() {
    let id = localStorage.getItem("otter_chat_conversation_id");
    if (!id) {
        id = (crypto.randomUUID ? crypto.randomUUID() : `chat-${Date.now()}-${Math.random()}`);
        localStorage.setItem("otter_chat_conversation_id", id);
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
        scrollToBottom();

    } catch (err) {
        thinkingEl.textContent = "Something went wrong -- try again.";
        thinkingEl.classList.add("chat-msg-error");
        scrollToBottom();
        console.error("Chat error:", err);
    } finally {
        chatSending = false;
        input.disabled = false;
        input.focus();
    }
}

function scrollToBottom() {
    const messages = document.getElementById("messages");
    messages.scrollTop = messages.scrollHeight;
}

function appendMessage(text, role) {

    const messages = document.getElementById("messages");

    const el = document.createElement("div");
    el.className = `chat-msg chat-msg-${role}`;
    el.textContent = text;  // textContent, not innerHTML -- never parsed as HTML, so nothing typed can break layout or inject markup

    messages.appendChild(el);
    scrollToBottom();

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
