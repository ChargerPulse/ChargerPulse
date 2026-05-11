import ssl
import logging
from datetime import datetime, timezone
from ocpp.v16 import ChargePoint as CP, call_result
from ocpp.routing import on
import asyncio, websockets, asyncpg, os, json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DSN = os.getenv("DATABASE_URL")
pool = None

class ChargePoint(CP):
    @on("StatusNotification")
    async def on_status(self, connectorId, status, **kwargs):
        try:
            valid_statuses = ["Available", "Preparing", "Charging", "SuspendedEVSE", "SuspendedEV", "Finishing", "Reserved", "Unavailable", "Faulted"]
            if not isinstance(connectorId, int) or status not in valid_statuses:
                logger.warning(f"Invalid status data: connectorId={connectorId}, status={status}")
                return call_result.StatusNotificationPayload()
            
            await pool.execute(
                "insert into events(cp_id, connector_id, status, ts) values($1, $2, $3, $4)",
                self.id, connectorId, status, datetime.now(timezone.utc))
            logger.info(f"CP {self.id}: Connector {connectorId} -> {status}")
        except Exception as e:
            logger.error(f"Error storing status: {e}")
        
        return call_result.StatusNotificationPayload()

async def main(websocket, path):
    cp = ChargePoint(websocket.path.split('/')[-1], websocket)
    await cp.start()

async def init():
    global pool
    pool = await asyncpg.create_pool(DSN, min_size=5, max_size=20)
    logger.info("Database pool initialized")

async def shutdown():
    global pool
    if pool:
        await pool.close()
    logger.info("Database pool closed")

async def run_server():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        os.getenv("SSL_CERT_PATH", "/etc/ssl/certs/cert.pem"),
        os.getenv("SSL_KEY_PATH", "/etc/ssl/private/key.pem")
    )
    
    server = await websockets.serve(main, "0.0.0.0", 443, ssl=ssl_context, subprotocols=['ocpp1.6'])
    logger.info("OCPP server started on wss://0.0.0.0:443")
    return server

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init())
    loop.run_until_complete(run_server())
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        loop.run_until_complete(shutdown())