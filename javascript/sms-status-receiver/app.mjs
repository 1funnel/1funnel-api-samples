import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { DatabaseSync } from "node:sqlite";
import { pathToFileURL } from "node:url";

const types = new Set([
  "sms.message.sent.v1",
  "sms.message.delivered.v1",
  "sms.message.failed.v1",
]);
const statuses = new Set(["queued", "sent", "delivered", "failed"]);

export function openStore(filename) {
  const db = new DatabaseSync(filename);
  db.exec(`
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=FULL;
    PRAGMA busy_timeout=5000;
    CREATE TABLE IF NOT EXISTS configuration (scope TEXT PRIMARY KEY);
    CREATE TABLE IF NOT EXISTS sends (
      operation TEXT PRIMARY KEY, idem_key TEXT NOT NULL, body TEXT NOT NULL,
      message_id TEXT UNIQUE, status TEXT, snapshot TEXT, checked_at TEXT
    );
    CREATE TABLE IF NOT EXISTS inbox (
      event_id TEXT PRIMARY KEY, message_id TEXT NOT NULL, body TEXT NOT NULL,
      received_at TEXT NOT NULL, processed_at TEXT
    );
  `);
  return db;
}

function transaction(db, fn) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const result = fn();
    db.exec("COMMIT");
    return result;
  } catch (error) {
    db.exec("ROLLBACK");
    throw error;
  }
}

export function createApp({
  db,
  baseUrl,
  businessId,
  token,
  keys,
  now = Date.now,
}) {
  const base = new URL(baseUrl);
  if (
    base.protocol !== "https:" &&
    !(base.protocol === "http:" && base.hostname === "127.0.0.1")
  ) {
    throw new Error("Use HTTPS, or 127.0.0.1 for offline tests");
  }
  const scope = JSON.stringify([base.origin, businessId]);
  transaction(db, () => {
    const saved = db.prepare("SELECT scope FROM configuration").get();
    if (saved && saved.scope !== scope)
      throw new Error("Use a separate database per API host and business");
    if (!saved)
      db.prepare("INSERT INTO configuration(scope) VALUES (?)").run(scope);
  });
  const resource = `/v1/businesses/${encodeURIComponent(businessId)}/sms/messages`;
  const stamp = () => new Date(now()).toISOString();
  async function request(path, method, body, key, expected) {
    const response = await fetch(new URL(path, base), {
      method,
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(key ? { "Idempotency-Key": key } : {}),
      },
      body,
    });
    const http_status = response.status;
    if (http_status !== expected) {
      // Do not log response bodies, tokens, message text or recipient numbers.
      throw new Error(
        `API HTTP ${http_status}; request ${response.headers.get("x-request-id") ?? "unknown"}`,
      );
    }
    return response.json();
  }
  function validateMessage(message, expectedId) {
    if (
      !message ||
      typeof message.id !== "string" ||
      !message.id ||
      message.business_id !== businessId ||
      !statuses.has(message.status) ||
      (expectedId && message.id !== expectedId)
    )
      throw new Error("Unexpected message resource");
  }
  async function send(operation, payload) {
    if (!operation) throw new Error("Supply a stable application operation ID");
    const body = JSON.stringify(payload);
    const row = transaction(db, () => {
      db.prepare(
        "INSERT OR IGNORE INTO sends(operation, idem_key, body) VALUES (?, ?, ?)",
      ).run(operation, randomUUID(), body);
      const saved = db
        .prepare("SELECT * FROM sends WHERE operation = ?")
        .get(operation);
      if (saved.body !== body)
        throw new Error("Operation already has a different payload");
      return saved;
    });
    if (row.message_id) return { id: row.message_id, status: row.status };
    // The key and exact bytes survive a timeout, process exit, or lost response.
    const message = await request(
      resource,
      "POST",
      row.body,
      row.idem_key,
      202,
    );
    validateMessage(message);
    // Never overwrite a newer worker snapshot when an acceptance response arrives late.
    db.prepare(
      `UPDATE sends SET message_id=?, status=?, snapshot=?, checked_at=?
      WHERE operation=? AND message_id IS NULL`,
    ).run(
      message.id,
      message.status,
      JSON.stringify(message),
      stamp(),
      operation,
    );
    return { id: message.id, status: message.status };
  }
  function verify(raw, headers) {
    const timestamp = headers["1funnel-webhook-timestamp"];
    const signature = headers["1funnel-webhook-signature"];
    const version = headers["1funnel-webhook-secret-version"] ?? "1";
    if (
      typeof version !== "string" ||
      typeof timestamp !== "string" ||
      !/^\d+$/.test(timestamp) ||
      typeof signature !== "string" ||
      !/^v1=[a-f0-9]{64}$/.test(signature)
    )
      return false;
    const key = Object.hasOwn(keys, version) ? keys[version] : null;
    const seconds = now() / 1000;
    if (
      !key ||
      typeof key.secret !== "string" ||
      !key.secret ||
      !Number.isFinite(key.validFrom) ||
      !Number.isFinite(key.validUntil) ||
      seconds < key.validFrom ||
      seconds >= key.validUntil ||
      Math.abs(seconds - Number(timestamp)) > 300
    )
      return false;
    const expected = createHmac("sha256", key.secret)
      .update(timestamp + ".")
      .update(raw)
      .digest();
    return timingSafeEqual(expected, Buffer.from(signature.slice(3), "hex"));
  }
  async function receive(req, res) {
    if (req.method !== "POST" || req.url !== "/hooks/1funnel") {
      res.writeHead(404).end();
      return;
    }
    try {
      let size = 0;
      const chunks = [];
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 65536) {
          res.writeHead(413).end();
          return;
        }
        chunks.push(chunk);
      }
      const raw = Buffer.concat(chunks);
      if (!verify(raw, req.headers)) {
        res.writeHead(401).end();
        return;
      }
      let event;
      try {
        event = JSON.parse(raw.toString("utf8"));
      } catch {
        res.writeHead(400).end();
        return;
      }
      if (
        !event ||
        typeof event.id !== "string" ||
        !event.id ||
        event.id !== req.headers["1funnel-webhook-id"] ||
        event.business_id !== businessId ||
        event.api_version !== "v1" ||
        !types.has(event.type) ||
        typeof event.data?.message_id !== "string" ||
        !event.data.message_id
      ) {
        res.writeHead(400).end();
        return;
      }
      // The insert is durable before 204. A worker handles business processing later.
      db.prepare(
        `INSERT OR IGNORE INTO inbox(event_id,message_id,body,received_at)
        VALUES (?,?,?,?)`,
      ).run(event.id, event.data.message_id, raw.toString("utf8"), stamp());
      res.writeHead(204).end();
    } catch {
      if (!res.headersSent) res.writeHead(503).end();
      else res.destroy();
    }
  }
  async function refresh(messageId) {
    const message = await request(
      `${resource}/${encodeURIComponent(messageId)}`,
      "GET",
      undefined,
      undefined,
      200,
    );
    validateMessage(message, messageId);
    return message;
  }
  async function work() {
    // Run ONE worker. Fetch current REST state instead of applying event arrival order.
    const events = db
      .prepare(
        `SELECT i.event_id,i.message_id FROM inbox i
      JOIN sends s ON s.message_id=i.message_id WHERE i.processed_at IS NULL
      ORDER BY i.received_at,i.event_id LIMIT 50`,
      )
      .all();
    for (const event of events) {
      const message = await refresh(event.message_id);
      transaction(db, () => {
        db.prepare(
          "UPDATE sends SET status=?,snapshot=?,checked_at=? WHERE message_id=?",
        ).run(message.status, JSON.stringify(message), stamp(), message.id);
        db.prepare("UPDATE inbox SET processed_at=? WHERE event_id=?").run(
          stamp(),
          event.event_id,
        );
      });
    }
    return events.length;
  }
  async function reconcile(operation) {
    const row = db
      .prepare("SELECT * FROM sends WHERE operation=?")
      .get(operation);
    if (!row?.message_id)
      throw new Error("No saved message ID; resolve the original send first");
    const message = await refresh(row.message_id);
    db.prepare(
      "UPDATE sends SET status=?,snapshot=?,checked_at=? WHERE operation=?",
    ).run(message.status, JSON.stringify(message), stamp(), operation);
    return { id: message.id, status: message.status };
  }
  return { send, receive, work, reconcile };
}

async function main() {
  process.umask(0o077);
  const [command, operation, file] = process.argv.slice(2);
  const db = openStore(process.env.DB_PATH ?? "./sms-status.sqlite");
  if (command === "inspect") {
    console.log(
      JSON.stringify(
        {
          sends: db
            .prepare("SELECT operation,message_id,status,checked_at FROM sends")
            .all(),
          inbox: db
            .prepare(
              "SELECT event_id,message_id,received_at,processed_at FROM inbox",
            )
            .all(),
        },
        null,
        2,
      ),
    );
    db.close();
    return;
  }
  const required = (name) => {
    if (!process.env[name]) throw new Error(`Set ${name}`);
    return process.env[name];
  };
  const app = createApp({
    db,
    baseUrl: process.env.API_BASE_URL ?? "https://api.sandbox.1-funnel.org",
    businessId: required("BUSINESS_ID"),
    token: required("ACCESS_TOKEN"),
    keys:
      command === "serve"
        ? JSON.parse(readFileSync(required("WEBHOOK_KEYS_FILE"), "utf8"))
        : {},
  });
  if (command === "serve") {
    const server = createServer(app.receive);
    server.requestTimeout = 10000;
    server.headersTimeout = 10000;
    server.listen(Number(process.env.PORT ?? 8080), "127.0.0.1", () =>
      console.log("Receiver listening on loopback"),
    );
    return;
  }
  try {
    if (command === "send")
      console.log(
        await app.send(operation, JSON.parse(readFileSync(file, "utf8"))),
      );
    else if (command === "work") console.log({ processed: await app.work() });
    else if (command === "reconcile")
      console.log(await app.reconcile(operation));
    else
      throw new Error(
        "Use send <operation> <request.json>, serve, work, reconcile <operation>, or inspect",
      );
  } finally {
    db.close();
  }
}
if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
