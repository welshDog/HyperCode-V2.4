import http from "http";
import { getHealthSnapshot, updateHealth } from "./health.js";
import { log } from "./logger.js";

type GenerateRequest = {
  prompt: string;
  stream?: boolean;
  max_tokens?: number;
};

type GenerateResponse = {
  id: string;
  model: string;
  output: string;
  finish_reason: "stop" | "length" | "error";
  elapsed_ms: number;
  tokens: number;
  health: ReturnType<typeof getHealthSnapshot>;
};

function unauthorized(res: http.ServerResponse) {
  res.writeHead(401);
  res.end("Unauthorized");
}

function json(res: http.ServerResponse, status: number, body: unknown) {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(JSON.stringify(body));
}

function sseHeaders(res: http.ServerResponse) {
  res.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-store",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no"
  });
  res.flushHeaders?.();
}

function sseEvent(res: http.ServerResponse, event: string, data: unknown) {
  res.write(`event: ${event}\n`);
  res.write(`data: ${JSON.stringify(data)}\n\n`);
}

async function readJsonBody(req: http.IncomingMessage, maxBytes: number): Promise<unknown> {
  let size = 0;
  const chunks: Buffer[] = [];

  return await new Promise((resolve, reject) => {
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > maxBytes) {
        reject(Object.assign(new Error("payload_too_large"), { code: "PAYLOAD_TOO_LARGE" }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => {
      try {
        const text = Buffer.concat(chunks).toString("utf8");
        resolve(text ? JSON.parse(text) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

export async function startApiServer(args: {
  session: any;
  model: any;
  modelName: string;
  port?: number;
}): Promise<{ server: http.Server; port: number }> {
  const token = process.env.MEMSTREAM_API_TOKEN ?? "";
  if (!token) {
    throw new Error("MEMSTREAM_API_TOKEN is required to start the /generate API");
  }

  const port = args.port ?? 8011;

  let inFlight = false;

  const server = http.createServer(async (req, res) => {
    res.setHeader("Cache-Control", "no-store");

    const auth = String(req.headers["authorization"] ?? "");
    if (auth !== `Bearer ${token}`) {
      unauthorized(res);
      return;
    }

    if (req.method !== "POST" || req.url !== "/generate") {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    if (inFlight) {
      res.writeHead(429, { "Retry-After": "1" });
      res.end("Busy");
      return;
    }

    inFlight = true;
    const start = Date.now();
    try {
      const raw = (await readJsonBody(req, 1024 * 1024)) as GenerateRequest;
      const prompt = typeof raw?.prompt === "string" ? raw.prompt : "";
      const stream = Boolean(raw?.stream ?? false);
      const maxTokens = typeof raw?.max_tokens === "number" ? Math.floor(raw.max_tokens) : 512;

      if (prompt.length < 1 || prompt.length > 8000) {
        json(res, 400, { error: "invalid_prompt_length" });
        return;
      }

      if (!Number.isFinite(maxTokens) || maxTokens < 1 || maxTokens > 4096) {
        json(res, 400, { error: "invalid_max_tokens" });
        return;
      }

      let lastHealthUpdateMs = 0;
      let chunkCount = 0;

      updateHealth({ current_mode: "api_generate" });

      if (stream) {
        sseHeaders(res);
        sseEvent(res, "open", { id: `gen_${Date.now()}`, model: args.modelName });

        const abortController = new AbortController();
        req.on("close", () => abortController.abort());

        let output = "";
        try {
          await args.session.prompt(prompt, {
            maxTokens,
            stopOnAbortSignal: true,
            signal: abortController.signal,
            onTextChunk: (chunk: string) => {
              output += chunk;
              sseEvent(res, "token", { text: chunk });

              chunkCount++;
              const now = Date.now();
              if (now - lastHealthUpdateMs >= 250) {
                lastHealthUpdateMs = now;
                const elapsed = (now - start) / 1000;
                const tokPerSec = elapsed > 0 ? chunkCount / elapsed : 0;
                updateHealth({ tokens_per_sec: tokPerSec, current_mode: "api_generate" });
              }
            }
          });
        } catch (err: any) {
          updateHealth({ current_mode: "idle", tokens_per_sec: 0 });
          sseEvent(res, "error", { error: "internal_error", message: err?.message ?? String(err) });
          res.end();
          return;
        }

        const elapsedMs = Date.now() - start;
        let tokens = 0;
        if (args.model && typeof args.model.tokenize === "function") {
          try {
            tokens = (args.model.tokenize(output) as any[])?.length ?? 0;
          } catch {
            tokens = 0;
          }
        }
        const finish_reason: GenerateResponse["finish_reason"] = tokens >= maxTokens ? "length" : "stop";
        updateHealth({ current_mode: "idle", tokens_per_sec: 0 });

        sseEvent(res, "done", {
          finish_reason,
          elapsed_ms: elapsedMs,
          tokens,
          health: getHealthSnapshot()
        });
        res.end();
        return;
      }

      const output = await args.session.prompt(prompt, {
        maxTokens,
        onTextChunk: (chunk: string) => {
          chunkCount++;
          const now = Date.now();
          if (now - lastHealthUpdateMs >= 250) {
            lastHealthUpdateMs = now;
            const elapsed = (now - start) / 1000;
            const tokPerSec = elapsed > 0 ? chunkCount / elapsed : 0;
            updateHealth({ tokens_per_sec: tokPerSec, current_mode: "api_generate" });
          }
        }
      });

      const elapsedMs = Date.now() - start;

      let tokens = 0;
      if (args.model && typeof args.model.tokenize === "function") {
        try {
          tokens = (args.model.tokenize(output) as any[])?.length ?? 0;
        } catch {
          tokens = 0;
        }
      }

      const finish_reason: GenerateResponse["finish_reason"] = tokens >= maxTokens ? "length" : "stop";

      const response: GenerateResponse = {
        id: `gen_${Date.now()}`,
        model: args.modelName,
        output,
        finish_reason,
        elapsed_ms: elapsedMs,
        tokens,
        health: getHealthSnapshot()
      };

      updateHealth({ current_mode: "idle", tokens_per_sec: 0 });
      json(res, 200, response);
    } catch (e: any) {
      if (e?.code === "PAYLOAD_TOO_LARGE") {
        json(res, 413, { error: "payload_too_large" });
      } else {
        log.error(e?.message ?? String(e));
        updateHealth({ current_mode: "idle", tokens_per_sec: 0 });
        json(res, 500, { error: "internal_error" });
      }
    } finally {
      inFlight = false;
    }
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve());
  });

  log.success(`MemStream API → http://127.0.0.1:${port}/generate`);
  return { server, port };
}

