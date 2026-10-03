# Gemini setup and indexing recovery

Use this guide with completed Phase 2 on `main`. The phase branch
`phase/2-project-memory` is retained for history.

## Running on your laptop

A key in the repository-root `.env` is sufficient. Codex cloud secrets and its
outbound domain allowlist apply to the hosted Codex executor, not to a backend
running on your laptop. Your browser calls local Next.js, which forwards to local
FastAPI; FastAPI makes the HTTPS request to Google through your normal network.
Do not copy your local key into Codex just to use the local application.

1. Open a terminal at your ProjectPulse checkout (the directory containing `apps`,
   `README.md` and `.env`). Pull the completed Phase 2 implementation:

   ```sh
   git switch main
   git pull --ff-only origin main
   ```

   Preserve your existing `.env` and local database. If upgrading from Phase 1,
   apply the additive migrations using the local setup guide. The Gemini wire-format
   fix adds no migration or database reset. Git does not transfer the ignored `.env`.

2. In that root `.env`, use the exact variable name:

   ```dotenv
   GEMINI_API_KEY=your_actual_api_key
   ```

   Keep the existing database settings. Do not put this in `apps/web/.env.local`
   with a `NEXT_PUBLIC_` prefix: the key is for the Python server only. On Windows,
   check the file is named `.env`, not `.env.txt`. Never share its contents or commit it.

3. Stop the currently running backend with Ctrl+C in its terminal. Settings are
   cached inside the backend process; saving `.env` does not reload them by itself.

4. From a separate terminal, install the locked backend dependencies and run the
   optional synthetic connectivity check:

   ```sh
   cd apps/api
   uv sync --frozen
   uv run python -m app.check_gemini
   ```

   This makes two small embedding requests (document and query). It reads no uploaded
   files and does not change the database. It prints configuration presence/source
   and dimensions; it never prints the key, vectors or document text. Success includes:

   ```text
   Key configured: yes; settings source: root .env
   RETRIEVAL_DOCUMENT: OK; received 768 normalized dimensions
   RETRIEVAL_QUERY: OK; received 768 normalized dimensions
   Gemini connectivity and vector format passed. Verify document indexing and citations next.
   ```

   `process environment` is also a valid source when you intentionally configured
   the key there. Process variables take precedence over `.env`; an old/empty exported
   `GEMINI_API_KEY` can shadow the file. If that happens, correct that variable or clear
   it in this terminal before rerunning. To use the `.env` value in PowerShell:

   ```powershell
   Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
   uv run python -m app.check_gemini
   ```

   In Command Prompt, use `set GEMINI_API_KEY=`; in Bash/Zsh, use
   `unset GEMINI_API_KEY`. This only clears the variable in the current terminal;
   it does not remove the key from `.env`.

5. Start the backend from `apps/api`:

   ```sh
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   Keep this terminal running. If port 8000 is occupied, stop the previous backend
   so the frontend does not keep calling an older copy of the code.

6. Keep the frontend running, or start it from another terminal:

   ```sh
   cd apps/web
   npm ci
   npm run dev
   ```

   Open `http://127.0.0.1:3000` and refresh the page.

7. Open **Documents**. Click **Index** again on your existing TXT and PDF uploads.
   Failed indexing preserves their original bytes/text/chunks; no re-upload or
   deletion is needed. Expect `Index: indexed` with a positive chunk count.

8. Open **Context search**. Search for a paraphrase of a distinctive sentence in
   an indexed document. Expect **Text and semantic search**, relevant document
   evidence, and a **Read source** link to the correct page/section. Compare that
   citation with the original. Confirm the baseline records did not change.

If the probe or indexing still fails, share the probe output or the displayed error,
not your key or `.env`. The checks above verify your local live document retrieval.

## Why “Embedding provider returned invalid vectors” occurred

The earlier adapter nested `taskType` and `outputDimensionality` inside
`embedContentConfig`. Google's Python SDK 2.28.0 serializes those fields directly
on each request in `requests[]` for `batchEmbedContents`. An unapplied dimension
setting can return the model's default 3072 values instead of the 768 our database
requires. Validation correctly refused to store that incompatible vector; it did
not mean the document parser rejected your TXT/PDF.

The fixed adapter uses the SDK's batch wire format, keeps strict 768/finite/nonzero
validation, and reports actual/expected sizes when they differ. Regression tests
emulate the default 3072 response if the dimension setting is misplaced, then
verify that the corrected request and retries save valid vectors for TXT and PDF.
Provider responses in these automated tests are synthetic; live laptop checks
remain necessary. There is no arbitrary slicing, padding or fake-vector fallback.

References: [Gemini REST API](https://ai.google.dev/api/embeddings) and
[official Python SDK](https://github.com/googleapis/python-genai).

## If you later run the backend in Codex cloud

The cloud executor is a separate machine and does not receive your laptop's `.env`.
In its environment configuration workflow, the required settings are a server-side
secret binding named `GEMINI_API_KEY`, and a restricted outbound HTTP destination
`generativelanguage.googleapis.com`. Keep package-manager access for dependency
installation. Apply/review the configuration and restart/reconnect the environment;
verify the secret is ready and the network policy is enforced before running the
probe there. The runtime-status tool is read-only; editing
`/etc/codex/network-policy.json` cannot grant access.

The exact configuration-editor labels depend on the Codex client. These cloud
settings are not required for your current laptop setup, and the cloud environment
used to develop this project still has neither configured.
