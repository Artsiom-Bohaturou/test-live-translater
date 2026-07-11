const statusEl = document.querySelector("#status");
const transcriptEl = document.querySelector("#transcript");
const answerEl = document.querySelector("#answer");

function render(state) {
  statusEl.textContent = `${state.captureStatus || "idle"}: ${state.status || ""}`;
  transcriptEl.textContent = state.transcript || "";
  answerEl.textContent = state.answer || "";
}

async function send(type) {
  const response = await chrome.runtime.sendMessage({ type });
  if (response?.error) statusEl.textContent = response.error;
}

document.querySelector("#start").addEventListener("click", () => send("start_capture"));
document.querySelector("#stop").addEventListener("click", () => send("stop_capture"));
document.querySelector("#ask").addEventListener("click", () => send("ask_last_audio"));

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "state") render(message.state);
});

chrome.runtime.sendMessage({ type: "get_state" }).then(render);
