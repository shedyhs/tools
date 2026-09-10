#!/usr/bin/env node
// Hook Stop: avisa (ou barra) quando ha trabalho que some junto com o sandbox.
//
// Modo em KIT_DIRTY_GUARD: off | warn | block (default warn).
//   warn  -> mensagem visivel, nao interrompe
//   block -> exit 2: o Claude Code devolve a mensagem ao agente, que precisa agir
//
// Num sandbox --clone, `git fetch sandbox-<nome>` no host so traz COMMITS.
// Arquivo nao commitado morre com o sandbox.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const MODE = (process.env.KIT_DIRTY_GUARD || "warn").toLowerCase();
if (MODE === "off") process.exit(0);

function stdin() {
  try {
    return JSON.parse(readFileSync(0, "utf8"));
  } catch {
    return {};
  }
}

function git(dir, args) {
  try {
    return execFileSync("git", ["-C", dir, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return null;
  }
}

const input = stdin();
const dir = input.cwd || process.cwd();

if (git(dir, ["rev-parse", "--is-inside-work-tree"]) !== "true") process.exit(0);

const dirty = (git(dir, ["status", "--porcelain"]) || "")
  .split("\n")
  .filter(Boolean).length;

const upstream = git(dir, ["rev-parse", "--abbrev-ref", "@{upstream}"]);
const ahead = upstream
  ? (git(dir, ["log", "--oneline", `${upstream}..HEAD`]) || "")
      .split("\n")
      .filter(Boolean).length
  : 0;

if (dirty === 0 && ahead === 0) process.exit(0);

const branch = git(dir, ["rev-parse", "--abbrev-ref", "HEAD"]) || "?";
const partes = [];
if (dirty > 0) {
  partes.push(
    `${dirty} arquivo(s) nao commitados em ${dir} (branch ${branch}). ` +
      `Se este sandbox foi criado com --clone, isso NAO volta para o host: ` +
      `\`git fetch sandbox-<nome>\` traz apenas commits. Commite antes de encerrar.`
  );
}
if (ahead > 0) {
  partes.push(
    `${ahead} commit(s) locais ainda nao enviados para ${upstream}. ` +
      `Do host: \`git fetch sandbox-<nome> && git log sandbox-<nome>/${branch}\`.`
  );
}
const msg = `[dirty-guard] ${partes.join(" ")}`;

if (MODE === "block" && input.stop_hook_active !== true) {
  process.stderr.write(msg + "\n");
  process.exit(2);
}

process.stdout.write(JSON.stringify({ systemMessage: msg }) + "\n");
process.exit(0);
