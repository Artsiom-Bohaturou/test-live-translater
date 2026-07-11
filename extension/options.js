const DEFAULT_CONTEXT_PROMPT = "Answer concisely and focus on practical explanations.";
const textarea = document.querySelector("#contextPrompt");
const statusEl = document.querySelector("#status");

chrome.storage.local.get({ contextPrompt: DEFAULT_CONTEXT_PROMPT }).then(({ contextPrompt }) => {
  textarea.value = contextPrompt;
});

document.querySelector("#save").addEventListener("click", async () => {
  await chrome.storage.local.set({ contextPrompt: textarea.value });
  statusEl.textContent = "Saved.";
});
