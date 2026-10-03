import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { Linter } from "eslint";
import { afterAll, describe, expect, it } from "vitest";

const require = createRequire(import.meta.url);
const nextPlugin = require("@next/eslint-plugin-next");
const { getRootDirs } = require(
  join(
    dirname(require.resolve("@next/eslint-plugin-next")),
    "utils/get-root-dirs.js",
  ),
);
const root = mkdtempSync(join(tmpdir(), "projectpulse-eslint-"));
const web = join(root, "apps", "web");
const admin = join(root, "apps", "admin");
for (const directory of [web, admin]) {
  mkdirSync(join(directory, "app"), { recursive: true });
  writeFileSync(
    join(directory, "app", "page.tsx"),
    "export default function Page() {}",
  );
}
writeFileSync(join(root, "apps", "README.md"), "Fixture, not an app root.");
afterAll(() => rmSync(root, { recursive: true, force: true }));

const roots = (rootDir?: string | string[]) =>
  getRootDirs({ cwd: web, settings: { next: { rootDir } } }).sort();
const webPattern = web.replace(/\\/g, "/");
const appPatterns = [admin, web].map((path) => path.replace(/\\/g, "/")).sort();

describe("Next.js ESLint directory lookup compatibility", () => {
  it("keeps the default root and literal absolute roots without expanding children", () => {
    expect(roots()).toEqual([web]);
    expect(roots(web)).toEqual([webPattern]);
    expect(roots(join(root, "missing"))).toEqual([]);
    expect(roots(join(root, "apps", "README.md"))).toEqual([]);
  });

  it("finds only app directories for globs, braces, arrays and Windows separators", () => {
    expect(roots(join(root, "apps", "*"))).toEqual(appPatterns);
    expect(roots(join(root, "apps", "{admin,web}"))).toEqual(appPatterns);
    expect(roots([admin, web])).toEqual(appPatterns);
    expect(roots(join(root, "apps", "*").replace(/\//g, "\\"))).toEqual(
      appPatterns,
    );
  });

  it("handles deeply nested braces without exhausting the call stack", () => {
    const pattern = "{".repeat(10_000) + "a,b" + "}".repeat(10_000);
    expect(roots(pattern)).toEqual([]);
  });

  it.each([web, join(root, "apps", "*"), [admin, web]])(
    "still rejects plain anchors to internal app routes with rootDir %j",
    (rootDir) => {
      const messages = new Linter().verify(
        'const link = <a href="/">Home</a>;',
        {
          files: ["**/*.jsx"],
          languageOptions: { parserOptions: { ecmaFeatures: { jsx: true } } },
          plugins: { "@next/next": nextPlugin },
          settings: { next: { rootDir } },
          rules: { "@next/next/no-html-link-for-pages": "error" },
        },
        "link.jsx",
      );
      expect(messages).toHaveLength(1);
      expect(messages[0].ruleId).toBe("@next/next/no-html-link-for-pages");
    },
  );
});
