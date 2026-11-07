from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from core.analyzer import analyze
from core.explanations import explain
from core.request_limits import RequestSizeLimit

ROOT = Path(__file__).resolve().parent
app = FastAPI(title='PluQ', version='1.0.0')
app.add_middleware(RequestSizeLimit)

@app.middleware('http')
async def security(request: Request, call_next):
    if request.method == 'POST':
        origin = request.headers.get('origin')
        if origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Cross-origin requests disabled'}, status_code=403)
        try:
            oversized = int(request.headers.get('content-length','0')) > 16384
        except ValueError:
            oversized = True
        if oversized:
            return JSONResponse({'detail':'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers.update({'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'", 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'Permissions-Policy':'camera=(self), microphone=(), geolocation=()', 'Cache-Control':'no-store' if request.url.path.startswith('/api/') else 'no-cache'})
    return response

class Scan(BaseModel):
    text: str = Field(min_length=1, max_length=4096)

@app.get('/health')
def health():
    return {'status':'ok','destination_fetching':False}

@app.post('/api/analyze')
def scan(body: Scan):
    return analyze(body.text)

@app.post('/api/explain')
def explanation(body: Scan):
    return explain(analyze(body.text))

@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')

app.mount('/', StaticFiles(directory=ROOT / 'static'), name='static')
