/* AI BOT FUNCTIONS */

let chatSending = false;
let currentConversationId = null;

// One permanent ID per browser/device -- identifies "you" to the backend
// for grouping conversations, without any real login. Different from
// conversation_id, which identifies one specific chat thread.
function getBrowserId() {
    let id = localStorage.getItem("otter_browser_id");
    if (!id) {
        id = (crypto.randomUUID ? crypto.randomUUID() : `browser-${Date.now()}-${Math.random()}`);
        localStorage.setItem("otter_browser_id", id);
    }
    return id;
}

// --------------------
// Sending messages
// --------------------

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
                browser_id: getBrowserId(),
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            throw new Error(`Server responded ${response.status}`);
        }

        const data = await response.json();

        thinkingEl.textContent = data.response;
        scrollToBottom();

        const isNewConversation = currentConversationId === null;
        currentConversationId = data.conversation_id;

        if (isNewConversation) {
            // First message of a brand-new conversation -- it now exists
            // server-side with a real ID and title, so refresh the
            // sidebar to show it.
            await loadConversationList();
            highlightActiveConversation();
        } else {
            // Existing conversation just got a new message -- bump it to
            // the top of the list without a full reload.
            bumpConversationToTop(currentConversationId, data.title);
        }

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

// --------------------
// New chat
// --------------------

function startNewChat() {
    currentConversationId = null;
    document.getElementById("messages").innerHTML = "";
    document.getElementById("message").focus();
    highlightActiveConversation();
}

// --------------------
// Sidebar: conversation list
// --------------------

async function loadConversationList() {

    const response = await fetch(`/chat/conversations?browser_id=${encodeURIComponent(getBrowserId())}`);

    if (!response.ok) return;

    const data = await response.json();
    renderConversationList(data.conversations);
}

function renderConversationList(conversations) {

    const container = document.getElementById("conversation-list");

    if (conversations.length === 0) {
        container.innerHTML = `<div class="conversation-list-empty">No conversations yet</div>`;
        return;
    }

    container.innerHTML = conversations.map(c => `
        <div class="conversation-item" data-conversation-id="${c.conversation_id}" onclick="switchConversation('${c.conversation_id}')">
            <span class="conversation-item-title">${escapeHtml(c.title)}</span>
            <button class="conversation-item-delete" onclick="event.stopPropagation(); deleteConversation('${c.conversation_id}')" title="Delete">&times;</button>
        </div>
    `).join("");

    highlightActiveConversation();
}

function bumpConversationToTop(conversationId, title) {

    const container = document.getElementById("conversation-list");
    const existing = container.querySelector(`[data-conversation-id="${conversationId}"]`);

    if (existing) {
        existing.querySelector(".conversation-item-title").textContent = title;
        container.insertBefore(existing, container.firstChild);
    } else {
        loadConversationList();
    }
}

function highlightActiveConversation() {
    document.querySelectorAll(".conversation-item").forEach(el => {
        el.classList.toggle("active", el.dataset.conversationId === currentConversationId);
    });
}

async function switchConversation(conversationId) {

    if (chatSending) return;

    currentConversationId = conversationId;
    highlightActiveConversation();

    const response = await fetch(
        `/chat/conversations/${encodeURIComponent(conversationId)}?browser_id=${encodeURIComponent(getBrowserId())}`
    );

    const messagesContainer = document.getElementById("messages");
    messagesContainer.innerHTML = "";

    if (!response.ok) {
        // Conversation vanished (deleted elsewhere, expired, etc.) --
        // fall back to a fresh chat instead of showing a broken state.
        currentConversationId = null;
        return;
    }

    const data = await response.json();

    data.messages.forEach(m => appendMessage(m.text, m.role));
}

async function deleteConversation(conversationId) {

    await fetch(
        `/chat/conversations/${encodeURIComponent(conversationId)}?browser_id=${encodeURIComponent(getBrowserId())}`,
        { method: "DELETE" }
    );

    if (currentConversationId === conversationId) {
        startNewChat();
    }

    await loadConversationList();
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// --------------------
// Init
// --------------------

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("message").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            sendMessage();
        }
    });

    loadConversationList();
});
