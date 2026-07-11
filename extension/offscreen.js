const BUFFER_SECONDS = 25;
const MEDIA_RECORDER_TIMESLICE_MS = 1000;
const MIME_TYPE = "audio/webm;codecs=opus";

let mediaRecorder = null;
let audioContext = null;
let chunks = [];

function trimChunks() {
  const cutoff = Date.now() - BUFFER_SECONDS * 1000;
  chunks = chunks.filter((chunk) => chunk.timestamp >= cutoff);
}

async function blobToBase64(blob) {
  const arrayBuffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

async function startCapture(streamId) {
  if (mediaRecorder?.state === "recording") return { status: "capturing" };
  chunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: streamId } },
    video: false
  });
  audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  source.connect(audioContext.destination);
  mediaRecorder = new MediaRecorder(stream, { mimeType: MIME_TYPE });
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size === 0) return;
    chunks.push({ blob: event.data, timestamp: Date.now() });
    trimChunks();
  };
  mediaRecorder.start(MEDIA_RECORDER_TIMESLICE_MS);
  return { status: "capturing" };
}

async function stopCapture() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  await audioContext?.close();
  mediaRecorder = null;
  audioContext = null;
  chunks = [];
  return { status: "idle" };
}

async function getRecentAudio() {
  trimChunks();
  if (!chunks.length) return { audioBase64: "", audioFormat: "webm-opus" };
  const blob = new Blob(chunks.map((chunk) => chunk.blob), { type: MIME_TYPE });
  return { audioBase64: await blobToBase64(blob), audioFormat: "webm-opus" };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "offscreen_start_capture") startCapture(message.streamId).then(sendResponse).catch((error) => sendResponse({ error: error.message }));
  if (message.type === "offscreen_stop_capture") stopCapture().then(sendResponse).catch((error) => sendResponse({ error: error.message }));
  if (message.type === "offscreen_get_recent_audio") getRecentAudio().then(sendResponse).catch((error) => sendResponse({ error: error.message }));
  return true;
});
