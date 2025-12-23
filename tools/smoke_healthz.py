import asyncio
import os
import sys

# Ensure project root is on sys.path for `import app`
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app

async def main():
    print('Starting smoke test for /healthz ...')
    app = create_app()
    async with app.test_app():
        async with app.test_client() as client:
            resp = await client.get('/healthz')
            print('STATUS:', resp.status_code)
            body = await resp.get_data()
            try:
                text = body.decode('utf-8')
            except Exception:
                text = str(body)
            print('BODY:', text[:200])

if __name__ == '__main__':
    asyncio.run(main())
