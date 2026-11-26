// A stand-in for the Windows helper: reads one JSON request on stdin, echoes it back as a
// failure (so the test sees exactly what arrived), or sleeps when told to, to exercise timeouts.
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const request = JSON.parse(input);
  const reply = () =>
    process.stdout.write(JSON.stringify({ ok: false, code: "echo", message: `${request.action?.text?.length ?? 0}` }));
  if (request.sleep_ms) setTimeout(reply, request.sleep_ms);
  else reply();
});
