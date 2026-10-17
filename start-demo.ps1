# Demo mode: fictional in-memory data (nothing persists), no Firebase sign-in.
# Extraction: PyMuPDF text layer -> local OCR (RapidOCR) for scanned pages -> Gemini lite structured extraction
# (GEMINI_API_KEY in backend/.env), Groq as the fallback.
$root = $PSScriptRoot
$backendEnv = "`$env:OBLIGOT_DEMO_MODE='true'; `$env:REQUIRE_FIREBASE_AUTH='false'; `$env:GROQ_MODEL='openai/gpt-oss-120b'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; $backendEnv; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npx vite --mode demo --host localhost --port 5173 --strictPort"
Start-Sleep 6
Start-Process "http://localhost:5173"
