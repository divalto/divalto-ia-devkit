'use strict';
const fs = require('fs');
const path = require('path');

const permanentContext = fs.readFileSync(path.join(__dirname, '..', 'context', 'CLAUDE.md'), 'utf-8');

function findContext(start) {
  for (let dir = start; ; dir = path.dirname(dir)) {
    const file = path.join(dir, '.divalto', 'mcp-context.json');
    if (fs.existsSync(file)) {
      return file;
    }
    if (path.dirname(dir) === dir) {
      return undefined;
    }
  }
}

let line = 'Divalto Studio project not opened: MCP tools unavailable.';
const file = findContext(process.env.CLAUDE_PROJECT_DIR || process.cwd());
if (file) {
  try {
    const capabilities = JSON.parse(fs.readFileSync(file, 'utf-8')).capabilities;
    const list = Array.isArray(capabilities) && capabilities.length > 0 ? capabilities.join(', ') : 'none';
    line = `Active capabilities: ${list} — do not use skills that declare a missing capability.`;
  } catch {
    // Unreadable context: keep the "not opened" line.
  }
}
const additionalContext = `${permanentContext}\n${line}\n`;
// Copilot only injects the top-level additionalContext; Claude Code reads hookSpecificOutput.
process.stdout.write(
  JSON.stringify({ additionalContext, hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext } })
);
