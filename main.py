import asyncio
import websockets
import logging
import asyncpg
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DSN = os.getenv("DATABASE_URL")
pool = None

async def init_db():
    """Initialize database connection pool"""
    global pool
    try:
        pool = await asyncpg.create_pool(DSN, min_size=2, max_size=10)
        logger.info("✅ Database pool initialized")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        pool = None

async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO events (cp_id, connector_id, status) VALUES ($1, $2, $3)",
                cp_id, connector_id, status
            )
        logger.info(f"✅ Logged: {cp_id} (connector {connector_id}) = {status}")
    except Exception as e:
        logger.error(f"❌ Failed to log event: {e}")

async def main(websocket, path):
    """Handle incoming OCPP WebSocket connections"""
    client_id = path.split('/')[-1]
    logger.info(f"📡 Client connected: {client_id}")
    
    try:
        async for message in websocket:
            logger.info(f"[{client_id}] Received: {message}")
            
            # Try to parse as JSON (OCPP messages)
            try:
                data = json.loads(message)
                # Example: log StatusNotification messages
                if isinstance(data, list) and len(data) >= 4:
                    msg_type = data[0]  # Message type
                    if msg_type == 2:  # StatusNotification
                        connector_id = data[3].get('connectorId')
                        status = data[3].get('status')
                        await log_event(client_id, connector_id, status)
            except json.JSONDecodeError:
                pass
            
            # Echo back acknowledgment
            await websocket.send(f"ACK: {message[:50]}")
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"📡 Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"❌ Error handling client {client_id}: {e}")

async def run_server():
    """Start the OCPP WebSocket server"""
    server = await websockets.serve(main, "0.0.0.0", 8765, subprotocols=['ocpp1.6'])
    logger.info("🚀 OCPP server started on ws://0.0.0.0:8765")
    return server

async def shutdown_db():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()
        logger.info("🛑 Database pool closed")

if __name__ == "__main__":
    async def main_async():
        await init_db()
        await run_server()
        try:
            await asyncio.sleep(float('inf'))
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await shutdown_db()
    
    asyncio.run(main_async())