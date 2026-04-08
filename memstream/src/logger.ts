import fs from "fs";
import path from "path";
import chalk from "chalk";
import cliProgress from "cli-progress";

const LOG_DIR = "./logs";
const CSV_PATH = path.join(LOG_DIR, "layer_times.csv");

if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

if (!fs.existsSync(CSV_PATH)) {
  fs.writeFileSync(
    CSV_PATH,
    "timestamp,event,layer,load_ms,ram_free_gb,vram_total_gb,vram_used_gb,tokens_per_sec\n"
  );
}

const logStream = fs.createWriteStream(CSV_PATH, { flags: "a" });
process.on("beforeExit", () => logStream.end());

let writeWindowStartMs = Date.now();
let writeWindowBytes = 0;
let loggingDisabled = false;

export function setWriteBudgetGBPerHour(maxGBPerHour: number | null) {
  if (!maxGBPerHour || !Number.isFinite(maxGBPerHour) || maxGBPerHour <= 0) return;
  const maxBytesPerHour = maxGBPerHour * 1024 ** 3;
  setInterval(() => {
    const now = Date.now();
    if (now - writeWindowStartMs >= 60 * 60 * 1000) {
      writeWindowStartMs = now;
      writeWindowBytes = 0;
      if (loggingDisabled) {
        loggingDisabled = false;
        log.warn("CSV logging re-enabled (new hourly write window).");
      }
    }
    if (writeWindowBytes > maxBytesPerHour && !loggingDisabled) {
      loggingDisabled = true;
      log.warn("CSV logging disabled (hourly write budget exceeded).");
    }
  }, 10_000).unref();
}

export function logEvent(row: {
  event: string;
  layer?: number;
  load_ms?: number;
  ram_free_gb?: number;
  vram_total_gb?: number;
  vram_used_gb?: number;
  tokens_per_sec?: number;
}) {
  if (loggingDisabled) return;
  const ts = new Date().toISOString();
  const line = [
    ts,
    row.event,
    row.layer ?? "",
    row.load_ms ?? "",
    row.ram_free_gb ?? "",
    row.vram_total_gb ?? "",
    row.vram_used_gb ?? "",
    row.tokens_per_sec ?? ""
  ].join(",");
  writeWindowBytes += Buffer.byteLength(line, "utf8") + 1;
  logStream.write(line + "\n");
}

export const log = {
  info: (msg: string) => console.log(chalk.cyan("  ℹ  ") + msg),
  success: (msg: string) => console.log(chalk.green("  ✅ ") + msg),
  warn: (msg: string) => console.log(chalk.yellow("  ⚠️  ") + msg),
  error: (msg: string) => console.log(chalk.red("  ❌ ") + msg),
  title: (msg: string) => console.log(chalk.bold.magenta("\n" + msg))
};

export function makeProgressBar(label: string, total: number, enabled: boolean) {
  if (!enabled) {
    return {
      update: (_: number) => {},
      stop: () => {}
    };
  }
  const bar = new cliProgress.SingleBar({
    format:
      chalk.cyan(label) +
      " |" +
      chalk.cyan("{bar}") +
      "| {percentage}% | {value}/{total}",
    barCompleteChar: "█",
    barIncompleteChar: "░",
    hideCursor: true
  });
  bar.start(total, 0);
  return bar;
}
