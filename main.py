import asyncio
import websockets
import logging
import asyncpg
import json
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DSN = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DSN, min_size=2, max_size=10)
        logger.info("✅ Database pool initialized")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        pool = None

async def log_event(cp_id, connector_id, status):
    logger.info(f"🔍 log_event called: cp_id={cp_id}, connector_id={connector_id}, status={status}")
    if not pool:
        logger.warning("❌ Database pool not available, skipping log")
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO events (cp_id, connector_id, status) VALUES ($1, $2, $3)",
                cp_id, connector_id, status
            )
        logger.info(f"✅ Logged: {cp_id} (connector {connector_id}) = {status}")
    except Exception as e:
        logger.error(f"❌ Failed to log event: {e}")

async def handle_connection(websocket, path):
    client_id = path.split('/')[-1]
    logger.info(f"📡 Client connected: {client_id}")
    try:
        async for message in websocket:
            logger.info(f"[{client_id}] Received: {message}")
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) >= 4:
                    if data[0] == 2:
                        connector_id = data[3].get('connectorId')
                        status = data[3].get('status')
                        await log_event(client_id, connector_id, status)
            except json.JSONDecodeError:
                pass
            await websocket.send(f"ACK: {message[:50]}")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"📡 Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")

async def run_server():
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765, subprotocols=['ocpp1.6'])
    logger.info("🚀 OCPP server started on ws://0.0.0.0:8765")
    return server

async def shutdown_db():
    global pool
    if pool:
        await pool.close()
        logger.info("🛑 Database pool closed")

async def main_async():
    await init_db()
    await run_server()
    try:
        await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await shutdown_db()

if __name__ == "__main__":
    asyncio.run(main_async())