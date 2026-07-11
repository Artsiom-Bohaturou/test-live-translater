const BACKEND_WS_URL = "ws://127.0.0.1:8765/ws";
const DEFAULT_CONTEXT_PROMPT = "Answer concisely and focus on practical explanations.";

let socket = null;
let activeRequestId = null;
let latestState = {
  captureStatus: "idle",
  status: "Not connected",
  transcript: "",
  answer: "",
  activeRequestId: null
};

async function ensureOffscreenDocument() {
  if (await chrome.offscreen.hasDocument()) return;
  await chrome.offscreen.createDocument({
    url: "offscreen.html",
    reasons: ["USER_MEDIA"],
    justification: "Capture and buffer tab audio while the extension service worker sleeps."
  });
}

function updateState(patch) {
  latestState = { ...latestState, ...patch };
  chrome.runtime.sendMessage({ type: "state", state: latestState }).catch(() => {});
}

function connectSocket() {
  if (socket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(socket.readyState)) return socket;
  socket = new WebSocket(BACKEND_WS_URL);
  socket.onopen = () => updateState({ status: "Connected to backend" });
  socket.onclose = () => updateState({ status: "Backend disconnected" });
  socket.onerror = () => updateState({ status: "Backend connection error" });
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.requestId && message.requestId !== activeRequestId) return;
    if (message.type === "status") updateState({ status: message.message });
    if (message.type === "transcript") updateState({ transcript: message.text, status: "Transcript received" });
    if (message.type === "token") updateState({ answer: latestState.answer + message.text, status: "Streaming answer" });
    if (message.type === "done") updateState({ status: "Done" });
    if (message.type === "cancelled") updateState({ status: "Previous request cancelled" });
    if (message.type === "error") updateState({ status: `Error: ${message.message}` });
  };
  return socket;
}

async function sendOffscreenMessage(message) {
  await ensureOffscreenDocument();
  return chrome.runtime.sendMessage(message);
}

async function startCapture() {
  await ensureOffscreenDocument();
  const streamId = await chrome.tabCapture.getMediaStreamId({ targetTabId: undefined });
  const response = await sendOffscreenMessage({ type: "offscreen_start_capture", streamId });
  updateState({ captureStatus: response.status || "capturing", status: "Capturing tab audio" });
  return response;
}

async function stopCapture() {
  const response = await sendOffscreenMessage({ type: "offscreen_stop_capture" });
  updateState({ captureStatus: "idle", status: "Capture stopped" });
  return response;
}

async function askLastAudio() {
  const audio = await sendOffscreenMessage({ type: "offscreen_get_recent_audio" });
  if (!audio?.audioBase64) {
    updateState({ status: "No buffered audio yet. Start capture and wait a moment." });
    return;
  }
  const { contextPrompt = DEFAULT_CONTEXT_PROMPT } = await chrome.storage.local.get({ contextPrompt: DEFAULT_CONTEXT_PROMPT });
  const requestId = crypto.randomUUID();
  activeRequestId = requestId;
  updateState({ activeRequestId: requestId, transcript: "", answer: "", status: "Sending audio to backend" });
  const ws = connectSocket();
  const payload = {
    type: "ask_audio",
    requestId,
    cancelPrevious: true,
    audioFormat: audio.audioFormat,
    contextPrompt,
    audioBase64: audio.audioBase64
  };
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  else ws.addEventListener("open", () => ws.send(JSON.stringify(payload)), { once: true });
}

chrome.commands.onCommand.addListener((command) => {
  if (command === "ask-last-audio") askLastAudio();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "get_state") sendResponse(latestState);
  if (message.type === "start_capture") startCapture().then(sendResponse).catch((error) => sendResponse({ error: error.message }));
  if (message.type === "stop_capture") stopCapture().then(sendResponse).catch((error) => sendResponse({ error: error.message }));
  if (message.type === "ask_last_audio") askLastAudio().then(() => sendResponse({ ok: true })).catch((error) => sendResponse({ error: error.message }));
  return true;
});
