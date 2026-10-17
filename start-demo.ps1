# Demo mode: fictional in-memory data (nothing persists), no Firebase sign-in. Groq (GROQ_API_KEY in backend/.env) extracts MOUs.
# Groq free tier: ~7-8k tokens per minute per model, so pages are read one at a time and extraction parts are small.
$root = $PSScriptRoot
$backendEnv = "`$env:OBLIGOT_DEMO_MODE='true'; `$env:REQUIRE_FIREBASE_AUTH='false'; `$env:VISION_BATCH_PAGES='1'; " +
  "`$env:GROQ_MAX_CONCURRENCY='1'; `$env:GROQ_MAX_RETRIES='6'; `$env:GROQ_MAX_RETRY_WAIT_SECONDS='65'; " +
  "`$env:EXTRACTION_CHUNK_CHARS='5000'; `$env:GROQ_DOCUMENT_TIMEOUT_SECONDS='180'; `$env:GROQ_MODEL='openai/gpt-oss-120b'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; $backendEnv; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npx vite --mode demo --host localhost --port 5173 --strictPort"
Start-Sleep 6
Start-Process "http://localhost:5173"
