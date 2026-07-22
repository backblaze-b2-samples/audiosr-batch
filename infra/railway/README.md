# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt -r requirements-ml.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

> The API image needs `requirements-ml.txt` (torch + AudioSR) to actually run
> enhancements. It is a large image and the first enhancement downloads the
> ~2 GB model checkpoint. For CPU-only hosts, expect enhancement runs to be
> slow; a GPU host (set `AUDIOSR_DEVICE` unset → CUDA auto-detect) is faster.

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your bucket's region slug (e.g. `us-west-004`) |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |
| `AUDIOSR_DEVICE` | *(optional)* force a device; unset auto-detects CUDA → CPU |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
