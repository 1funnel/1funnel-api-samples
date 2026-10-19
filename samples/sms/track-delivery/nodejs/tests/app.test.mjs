// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createHmac, randomBytes } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { createApp, openStore } from "../src/app.mjs";

const businessId = "018f3c4e-7b2a-7c3d-8e9f-0123456789ab";
const messageId = "018f3c4e-7b2a-7c3d-8e9f-aaaaaaaaaaaa";
const listen = (server) =>
  new Promise((resolve) =>
    server.listen(0, "127.0.0.1", () =>
      resolve(`http://127.0.0.1:${server.address().port}`),
    ),
  );
const close = (server) =>
  new Promise((resolve) => {
    server.close(resolve);
    server.closeAllConnections();
  });

test("persist send, verify HTTP deliveries, restart, recover and reconcile", async () => {
  const dir = mkdtempSync(join(tmpdir(), "sms-tutorial-"));
  const path = join(dir, "test.sqlite");
  let db = openStore(path);
  const secret = randomBytes(32).toString("hex");
  const clock = Date.now();
  const seconds = Math.floor(clock / 1000);
  const keys = {
    1: { secret, validFrom: seconds - 600, validUntil: seconds + 600 },
  };
  const calls = [];
  let loseResponse = true;
  let postStatus = 202;
  let getStatus = 200;
  let status = "delivered";
  const payload = {
    from: "ONEFUNNEL",
    to: "+2348012345678",
    classification: "transactional",
    message: "Order ORD-1001 confirmed.",
  };
  const resource = (current) => ({
    id: messageId,
    business_id: businessId,
    ...payload,
    status: current,
    accepted_at: "2026-10-13T09:00:00.000Z",
  });
  const api = createServer(async (req, res) => {
    assert.equal(req.headers.authorization, "Bearer offline-test-token");
    if (req.method === "POST") {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      calls.push({
        key: req.headers["idempotency-key"],
        body: Buffer.concat(chunks).toString(),
      });
      assert.equal(req.url, `/v1/businesses/${businessId}/sms/messages`);
      if (loseResponse) {
        loseResponse = false;
        req.socket.destroy();
        return;
      }
      res
        .writeHead(postStatus, { "Content-Type": "application/json" })
        .end(JSON.stringify(resource("queued")));
    } else {
      assert.equal(
        req.url,
        `/v1/businesses/${businessId}/sms/messages/${messageId}`,
      );
      res
        .writeHead(getStatus, { "Content-Type": "application/json" })
        .end(JSON.stringify(resource(status)));
    }
  });
  const baseUrl = await listen(api);
  const makeApp = () =>
    createApp({
      db,
      baseUrl,
      businessId,
      token: "offline-test-token",
      keys,
      now: () => clock,
    });
  let app = makeApp();
  let receiver;
  try {
    await assert.rejects(app.send("order-1001", payload));
    const key = db.prepare("SELECT idem_key FROM sends").get().idem_key;
    db.close();
    db = openStore(path);
    app = makeApp();
    assert.deepEqual(await app.send("order-1001", payload), {
      id: messageId,
      status: "queued",
    });
    assert.equal(calls.length, 2);
    assert.equal(calls[0].key, key);
    assert.deepEqual(calls[0], calls[1]);
    await app.send("order-1001", payload);
    assert.equal(
      calls.length,
      2,
      "a saved message must not be submitted again",
    );
    await assert.rejects(
      app.send("order-1001", { ...payload, message: "Changed" }),
      /different payload/,
    );

    receiver = createServer((req, res) => app.receive(req, res));
    const receiverUrl = await listen(receiver);
    const event = (id, type = "sms.message.delivered.v1") => ({
      id,
      type,
      created_at: "2026-10-13T09:00:05.000Z",
      business_id: businessId,
      api_version: "v1",
      data: {
        message_id: messageId,
        status: type.split(".")[2],
        occurred_at: "2026-10-13T09:00:05.000Z",
      },
    });
    async function deliver(value, options = {}) {
      const raw = options.raw ?? JSON.stringify(value);
      const timestamp = String(options.timestamp ?? seconds);
      const digest = createHmac("sha256", options.secret ?? secret)
        .update(timestamp + "." + raw)
        .digest("hex");
      const response = await fetch(receiverUrl + "/hooks/1funnel", {
        method: "POST",
        headers: {
          "1Funnel-Webhook-Id": value?.id ?? "invalid",
          "1Funnel-Webhook-Timestamp": timestamp,
          "1Funnel-Webhook-Signature": `v1=${digest}`,
          ...options.headers,
        },
        body: raw,
      });
      await response.arrayBuffer();
      return response.status;
    }
    const first = event("018f3c4e-7b2a-7c3d-8e9f-ffffffffffff");
    assert.equal(await deliver(first, { timestamp: seconds - 301 }), 401);
    assert.equal(await deliver(first, { secret: "wrong" }), 401);
    assert.equal(
      await deliver(first, {
        headers: { "1Funnel-Webhook-Secret-Version": "unknown" },
      }),
      401,
    );
    keys["2"] = { secret, validFrom: seconds - 60, validUntil: seconds + 60 };
    keys["3"] = { secret, validFrom: seconds - 60, validUntil: seconds };
    assert.equal(
      await deliver(first, {
        headers: { "1Funnel-Webhook-Secret-Version": "3" },
      }),
      401,
    );
    assert.equal(await deliver(first, { raw: "{" }), 400);
    assert.equal(
      await deliver({ ...first, business_id: "other-business" }),
      400,
    );
    assert.equal(
      await deliver(first, { headers: { "1Funnel-Webhook-Id": "different" } }),
      400,
    );
    assert.equal(await deliver(first, { raw: "x".repeat(65537) }), 413);
    assert.equal(db.prepare("SELECT count(*) AS n FROM inbox").get().n, 0);
    assert.equal(
      await deliver(first, {
        headers: { "1Funnel-Webhook-Secret-Version": "2" },
      }),
      204,
    );
    assert.equal(await deliver(first), 204);
    assert.equal(db.prepare("SELECT count(*) AS n FROM inbox").get().n, 1);
    assert.equal(
      db.prepare("SELECT processed_at FROM inbox").get().processed_at,
      null,
    );
    db.close();
    db = openStore(path);
    app = makeApp();
    db.prepare(
      "UPDATE sends SET message_id=NULL WHERE operation='order-1001'",
    ).run();
    assert.equal(
      await app.work(),
      0,
      "event stays pending until acceptance ID is saved",
    );
    db.prepare(
      "UPDATE sends SET message_id=? WHERE operation='order-1001'",
    ).run(messageId);
    getStatus = 503;
    await assert.rejects(app.work(), /HTTP 503/);
    assert.equal(
      db.prepare("SELECT processed_at FROM inbox").get().processed_at,
      null,
    );
    getStatus = 200;
    assert.equal(await app.work(), 1);
    assert.equal(
      db.prepare("SELECT status FROM sends").get().status,
      "delivered",
    );
    assert.equal(await app.work(), 0);
    assert.equal(
      await deliver(
        event("018f3c4e-7b2a-7c3d-8e9f-eeeeeeeeeeee", "sms.message.sent.v1"),
      ),
      204,
    );
    await app.work();
    assert.equal(
      db.prepare("SELECT status FROM sends").get().status,
      "delivered",
      "late sent event must not regress current REST status",
    );
    status = "failed";
    assert.deepEqual(await app.reconcile("order-1001"), {
      id: messageId,
      status: "failed",
    });
    assert.equal(calls.length, 2, "recovery uses GET, never another send");
    postStatus = 200;
    await assert.rejects(app.send("unexpected-response", payload), /HTTP 200/);
    assert.equal(
      db
        .prepare(
          "SELECT message_id FROM sends WHERE operation='unexpected-response'",
        )
        .get().message_id,
      null,
    );
    assert.throws(
      () =>
        createApp({ db, baseUrl, businessId: "other", token: "test", keys }),
      /separate database/,
    );
    db.close();
    assert.equal(
      await deliver(event("018f3c4e-7b2a-7c3d-8e9f-dddddddddddd")),
      503,
      "storage failure must not acknowledge receipt",
    );
    db = openStore(path);
  } finally {
    if (receiver) await close(receiver);
    await close(api);
    db.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
