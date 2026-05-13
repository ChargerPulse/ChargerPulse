import asyncio
import websockets
import logging
import asyncpg
import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DSN = os.getenv("DATABASE_URL")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
ALERT_EMAIL = "senzoradebe999@gmail.com"
FROM_EMAIL = "senzoradebe999@gmail.com"

pool = None

async def send_email(subject, body):
    """Send email via SendGrid"""
    if not SENDGRID_API_KEY or SENDGRID_API_KEY == "SG.dummy_key_for_now":
        logger.warning("No SendGrid key configured, skipping email")
        return
    try:
        data = json.dumps({
            "personalizations": [{"to": [{"email": ALERT_EMAIL}]}],
            "from": {"email": FROM_EMAIL, "name": "ChargerPulse Alerts"},
            "subject": subject,
            "content": [{"type": "text/html", "value": body}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            logger.info(f"✅ Email sent: {subject} (status {response.status})")
    except urllib.error.HTTPError as e:
        logger.error(f"❌ Email failed: {e.code} {e.read().decode()}")
    except Exception as e:
        logger.error(f"❌ Email error: {e}")

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
            charger = await conn.fetchrow(
                "SELECT nickname FROM chargers WHERE id = $1", cp_id
            )
            nickname = charger['nickname'] if charger else cp_id

            if status in ('Faulted', 'Unavailable', 'Offline'):
                existing = await conn.fetchrow(
                    "SELECT id FROM alerts WHERE cp_id = $1 AND resolved = false", cp_id
                )
                if not existing:
                    await conn.execute(
                        "INSERT INTO alerts (cp_id, nickname) VALUES ($1, $2)",
                        cp_id, nickname
                    )
                    logger.info(f"🚨 Alert created for {cp_id} — status: {status}")

                    # Send email alert
                    subject = f"🚨 ChargerPulse Alert — {cp_id} is DOWN"
                    body = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: #1e3a5f; padding: 20px; text-align: center;">
                            <h1 style="color: white; margin: 0;">⚡ ChargerPulse</h1>
                        </div>
                        <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 20px; margin: 20px 0;">
                            <h2 style="color: #dc2626; margin: 0 0 10px 0;">🚨 Charger Down Alert</h2>
                            <p style="margin: 0; font-size: 16px;">Your charger is offline and needs attention!</p>
                        </div>
                        <div style="padding: 0 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Charger ID</td>
                                    <td style="padding: 10px; font-family: monospace;">{cp_id}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Name</td>
                                    <td style="padding: 10px;">{nickname}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Status</td>
                                    <td style="padding: 10px; color: #dc2626; font-weight: bold;">{status}</td>
                                </tr>
                            </table>
                        </div>
                        <div style="padding: 20px; text-align: center;">
                            <a href="https://chargerpulse-dashboard.onrender.com/alerts"
                               style="background: #2563eb; color: white; padding: 12px 30px;
                                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                                View Dashboard
                            </a>
                        </div>
                        <div style="background: #f8fafc; padding: 15px; text-align: center; color: #64748b; font-size: 12px;">
                            ChargerPulse — EV Charger Uptime Monitoring
                        </div>
                    </div>
                    """
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: asyncio.run(send_email(subject, body))
                    )
                    asyncio.create_task(send_email(subject, body))

            elif status == 'Available':
                result = await conn.execute(
                    """UPDATE alerts SET resolved = true, resolved_at = now()
                    WHERE cp_id = $1 AND resolved = false""", cp_id
                )
                if result != "UPDATE 0":
                    logger.info(f"✅ Alert resolved for {cp_id} — back online")

                    # Send recovery email
                    subject = f"✅ ChargerPulse — {cp_id} is back ONLINE"
                    body = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: #1e3a5f; padding: 20px; text-align: center;">
                            <h1 style="color: white; margin: 0;">⚡ ChargerPulse</h1>
                        </div>
                        <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 20px; margin: 20px 0;">
                            <h2 style="color: #16a34a; margin: 0 0 10px 0;">✅ Charger Back Online</h2>
                            <p style="margin: 0; font-size: 16px;">Good news — your charger has recovered!</p>
                        </div>
                        <div style="padding: 0 20px;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Charger ID</td>
                                    <td style="padding: 10px; font-family: monospace;">{cp_id}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Name</td>
                                    <td style="padding: 10px;">{nickname}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px; font-weight: bold; color: #64748b;">Status</td>
                                    <td style="padding: 10px; color: #16a34a; font-weight: bold;">Available</td>
                                </tr>
                            </table>
                        </div>
                        <div style="padding: 20px; text-align: center;">
                            <a href="https://chargerpulse-dashboard.onrender.com"
                               style="background: #16a34a; color: white; padding: 12px 30px;
                                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                                View Dashboard
                            </a>
                        </div>
                        <div style="background: #f8fafc; padding: 15px; text-align: center; color: #64748b; font-size: 12px;">
                            ChargerPulse — EV Charger Uptime Monitoring
                        </div>
                    </div>
                    """
                    asyncio.create_task(send_email(subject, body))

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