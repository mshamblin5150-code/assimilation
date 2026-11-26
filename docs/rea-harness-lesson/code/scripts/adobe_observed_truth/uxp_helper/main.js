// Runs the harness's commands inside Photoshop. It only ever does what the harness queues on
// 127.0.0.1 (see ../uxp_bridge.py): answer a ping, run one menu command by the number
// menuBarInfo reports, or hand over the actions Photoshop reported since last asked. It presses
// no buttons and plays no actions; the harness handles any dialog a command opens.
const { core, action } = require("photoshop");
const { entrypoints } = require("uxp");

// The actions Photoshop performs, as it reports them to listeners: the event name and its
// descriptor (every setting with the value used). Only listened to, never replayed.
// Photoshop refuses a listener for "all", so the harness sends the names from its dictionary.
const recorded = [];
const registered = new Set();

function remember(event, descriptor) {
  recorded.push({ event, descriptor });
  if (recorded.length > 200) recorded.shift();
}

async function listen(names) {
  const fresh = names.filter((name) => !registered.has(name));
  const refused = [];
  for (let start = 0; start < fresh.length; start += 200) {
    const chunk = fresh.slice(start, start + 200);
    try {
      await action.addNotificationListener(chunk, remember);
      chunk.forEach((name) => registered.add(name));
    } catch (error) {
      for (const name of chunk) {  // find the few Photoshop will not allow
        try {
          await action.addNotificationListener([name], remember);
          registered.add(name);
        } catch (single) {
          refused.push(name);
        }
      }
    }
  }
  return { listening: registered.size, refused };
}

// Both spellings of this machine, on the bridge's one port; whichever UXP allows is kept.
const BASES = ["http://127.0.0.1:47615", "http://localhost:47615"];
let BASE = BASES[0];
let lastError = "";
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function showStatus(text) {
  const element = document.getElementById("status");
  if (element) element.textContent = text;
}

async function handle(command) {
  if (command.kind === "ping") {
    // Installed for every Photoshop here: say which one is answering.
    return {
      ok: true,
      value: { reply: "pong", version: require("uxp").host.version, listening: registered.size },
    };
  }
  if (command.kind === "listen") {
    return { ok: true, value: await listen(command.names || []) };
  }
  if (command.kind === "recorded_actions") {
    return { ok: true, value: recorded.splice(0, recorded.length) };
  }
  if (command.kind === "menu_command") {
    // Refused whoever asks: signing out would end every later probe (and the operator's session).
    const title = core.getMenuCommandTitle
      ? await core.getMenuCommandTitle({ commandID: command.command })
      : "";
    if (/sign\s*out|log\s*out/i.test(title)) {
      return { ok: false, error: `refused: "${title}" is never run` };
    }
    let ran = false;
    await core.executeAsModal(
      async () => {
        ran = await core.performMenuCommand({ commandID: command.command });
      },
      { commandName: "Observed-truth menu command" }
    );
    return { ok: true, value: ran };
  }
  return { ok: false, error: `unknown command kind ${command.kind}` };
}

async function serve() {
  for (;;) {
    try {
      const response = await fetch(`${BASE}/next`);
      if (response.status !== 200) continue; // nothing queued; the harness waits up to 1 s
      const command = await response.json();
      showStatus(`Running ${command.kind} ${command.command ?? ""}`);
      let result;
      try {
        result = await handle(command);
      } catch (error) {
        result = { ok: false, error: String(error) };
      }
      await fetch(`${BASE}/result`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: command.id, ...result }),
      });
      showStatus("Connected to the harness");
    } catch (error) {
      lastError = String(error);
      BASE = BASES[(BASES.indexOf(BASE) + 1) % BASES.length];
      showStatus(`Waiting for the harness (${BASE}): ${lastError}`);
      await pause(2000); // harness not running, or this address refused: try the other
    }
  }
}

entrypoints.setup({
  plugin: {
    create() {
      serve();
    },
  },
  panels: { helperPanel: { show() {} } },
});
