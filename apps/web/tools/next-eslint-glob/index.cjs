/* eslint-disable @typescript-eslint/no-require-imports -- Next.js loads this adapter synchronously through CommonJS. */
const { statSync } = require("node:fs");
const { isAbsolute } = require("node:path");
const { globSync, isDynamicPattern } = require("tinyglobby");

// Only the directory lookup API used by @next/eslint-plugin-next 16.3.8.
exports.globSync = (pattern, options) => {
  if (typeof pattern !== "string" || options?.onlyDirectories !== true) {
    throw new TypeError(
      "Next.js ESLint glob adapter requires a directory pattern",
    );
  }

  // Avoid expanding literal directories or losing an absolute app root.
  if (!isDynamicPattern(pattern)) {
    return statSync(pattern, { throwIfNoEntry: false })?.isDirectory()
      ? [pattern]
      : [];
  }

  return globSync(pattern, {
    onlyDirectories: true,
    expandDirectories: false,
    absolute: isAbsolute(pattern),
  }).map((directory) => directory.replace(/\/$/, ""));
};
