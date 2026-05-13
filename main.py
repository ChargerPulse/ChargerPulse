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

async def register_charger(cp_id):
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO chargers (id, nickname) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING",
                cp_id, cp_id
            )
        logger.info(f"✅ Charger registered: {cp_id}")
    except Exception as e:
        logger.error(f"❌ Failed to register charger: {e}")

async def check_and_create_alert(cp_id, status):
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            # Get charger nickname
            charger = await conn.fetchrow(
                "SELECT nickname FROM chargers WHERE id = $1", cp_id
            )
            nickname = charger['nickname'] if charger else cp_id

            if status in ('Faulted', 'Unavailable', 'Offline'):
                # Check if alert already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM alerts WHERE cp_id = $1 AND resolved = false",
                    cp_id
                )
                if not existing:
                    await conn.execute(
                        "INSERT INTO alerts (cp_id, nickname) VALUES ($1, $2)",
                        cp_id, nickname
                    )
                    logger.info(f"🚨 Alert created for {cp_id} — status: {status}")
            elif status == 'Available':
                # Auto-resolve alert when charger comes back
                result = await conn.execute(
                    """UPDATE alerts 
                    SET resolved = true, resolved_at = now() 
                    WHERE cp_id = $1 AND resolved = false""",
                    cp_id
                )
                if result != "UPDATE 0":
                    logger.info(f"✅ Alert resolved for {cp_id} — back online")
    except Exception as e:
        logger.error(f"❌ Alert check failed: {e}")

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
        await check_and_create_alert(cp_id, status)
    except Exception as e:
        logger.error(f"❌ Failed to log event: {e}")

async def handle_connection(websocket, path):
    client_id = path.split('/')[-1]
    logger.info(f"📡 Client connected: {client_id}")
    await register_charger(client_id)
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
        await check_and_create_alert(client_id, 'Offline')
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