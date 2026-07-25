export default {
  async scheduled(event, env) {
    await run(env);
  },

  async fetch(request, env) {
    if (request.method === "POST" && new URL(request.url).pathname === "/run") {
      await run(env);
      return new Response("OK");
    }
    return new Response("od-tgbot worker");
  },
};

async function run(env) {
  const state = await getState(env);
  const cookies = await login(env);
  const races = await getRaces(cookies, env);

  const newRaces = [];
  for (const race of races) {
    if (state.seen_ids.includes(race.id)) continue;
    if (race.race_date && new Date(race.race_date) < new Date()) {
      state.seen_ids.push(race.id);
      continue;
    }
    state.seen_ids.push(race.id);
    newRaces.push(race);
  }

  for (const race of newRaces) {
    await sendRaceMessage(race, env);
  }

  await putState(state, env);
}

async function getState(env) {
  const raw = await env.STATE.get("state");
  if (!raw) return { seen_ids: [] };
  try {
    return JSON.parse(raw);
  } catch {
    return { seen_ids: [] };
  }
}

async function putState(state, env) {
  await env.STATE.put("state", JSON.stringify(state));
}

async function login(env) {
  const resp = await fetch("https://onlydrafts.racing/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: env.ONLYDRAFTS_EMAIL,
      password: env.ONLYDRAFTS_PASSWORD,
    }),
  });
  if (!resp.ok) throw new Error(`Login failed: ${resp.status}`);
  const cookies = resp.headers.getSetCookie().join("; ");
  return cookies;
}

async function getRaces(cookies, env) {
  const resp = await fetch("https://onlydrafts.racing/api/races", {
    headers: { Cookie: cookies },
  });
  if (!resp.ok) throw new Error(`Get races failed: ${resp.status}`);
  return resp.json();
}

async function sendRaceMessage(race, env) {
  const name = race.name || "Без названия";
  const track = race.track || "—";
  const raceDate = race.race_date || "";
  const cars = Array.isArray(race.cars) ? race.cars : [];
  const stages = (race.stages || []).sort((a, b) => a.n - b.n);
  const totalLaps = stages.reduce((sum, s) => sum + (s.laps || 0), 0);

  let dateStr = "—";
  if (raceDate) {
    try {
      const d = new Date(raceDate);
      dateStr =
        String(d.getUTCDate()).padStart(2, "0") +
        "." +
        String(d.getUTCMonth() + 1).padStart(2, "0") +
        "." +
        d.getUTCFullYear() +
        " " +
        String(d.getUTCHours()).padStart(2, "0") +
        ":" +
        String(d.getUTCMinutes()).padStart(2, "0");
    } catch {}
  }

  let lines = [
    `🏁 <b>${esc(name)}</b>`,
    `📍 Трасса: ${esc(track)}`,
    `📅 Дата: ${dateStr}`,
  ];

  if (stages.length) {
    for (const s of stages) {
      lines.push(`  ● Стейдж ${s.n}: ${s.laps} кр.`);
    }
    lines.push(`🔄 Кругов: ${totalLaps}`);
  } else {
    lines.push(`🔄 Кругов: ${race.laps || "—"}`);
  }

  if (cars.length) {
    lines.push(`🚗 Машины: ${cars.map(esc).join(", ")}`);
  }

  lines.push("");
  lines.push(`🔗 <a href="https://onlydrafts.racing">OnlyDrafts.racing</a>`);

  if (race.irt_limit && (race.irt_min || race.irt_max)) {
    let irt = "Рейтинг: ";
    if (race.irt_min && race.irt_max) irt += `${race.irt_min}–${race.irt_max}`;
    else if (race.irt_min) irt += `от ${race.irt_min}`;
    else irt += `до ${race.irt_max}`;
    lines.push(irt);
  }

  await sendText(lines.join("\n"), env);
}

async function sendText(text, env) {
  const resp = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: env.TELEGRAM_CHAT_ID,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    }
  );
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    console.error("Telegram send failed:", err);
  }
}

function esc(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
