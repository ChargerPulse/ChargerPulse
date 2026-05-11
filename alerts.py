import asyncio
import logging
from datetime import datetime, timezone, timedelta
import asyncpg
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DSN = os.getenv("DATABASE_URL")
SENDGRID_KEY = os.getenv("SENDGRID_KEY")

sg = SendGridAPIClient(SENDGRID_KEY)

class AlertManager:
    def __init__(self, pool):
        self.pool = pool
        self.offline_threshold = 600  # 10 minutes in seconds
    
    async def check_alerts(self):
        """Check for chargers that have been offline for >10 minutes"""
        try:
            async with self.pool.acquire() as conn:
                # Find chargers offline for >10 min
                query = """
                    SELECT DISTINCT cp_id FROM events 
                    WHERE status = 'Unavailable' 
                    AND ts > now() - interval '10 minutes'
                    AND ts = (SELECT max(ts) FROM events e2 WHERE e2.cp_id = events.cp_id)
                    AND NOT EXISTS (
                        SELECT 1 FROM alerts 
                        WHERE cp_id = events.cp_id 
                        AND cleared_at IS NULL
                    )
                """
                
                offline_chargers = await conn.fetch(query)
                
                for row in offline_chargers:
                    cp_id = row['cp_id']
                    await self.create_alert(conn, cp_id)
                    await self.send_alert_email(conn, cp_id, "opened")
                
                logger.info(f"Checked alerts: {len(offline_chargers)} chargers offline")
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def create_alert(self, conn, cp_id):
        """Create a new alert in the database"""
        try:
            await conn.execute(
                "INSERT INTO alerts(cp_id, triggered_at) VALUES($1, $2)",
                cp_id, datetime.now(timezone.utc)
            )
            logger.info(f"Alert created for charger {cp_id}")
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def clear_alerts(self, cp_id):
        """Clear alerts when charger comes back online"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE alerts SET cleared_at = $1 WHERE cp_id = $2 AND cleared_at IS NULL",
                    datetime.now(timezone.utc), cp_id
                )
                await self.send_alert_email(conn, cp_id, "cleared")
                logger.info(f"Alert cleared for charger {cp_id}")
        except Exception as e:
            logger.error(f"Error clearing alert: {e}")
    
    async def send_alert_email(self, conn, cp_id, alert_type):
        """Send email notification via SendGrid"""
        try:
            # Get charger and user info
            query = """
                SELECT u.email, c.nickname FROM chargers c
                JOIN users u ON c.user_id = u.id
                WHERE c.id = $1
            """
            charger = await conn.fetchrow(query, cp_id)
            
            if not charger or not charger['email']:
                logger.warning(f"No email found for charger {cp_id}")
                return
            
            user_email = charger['email']
            charger_name = charger['nickname'] or cp_id
            
            if alert_type == "opened":
                subject = "⚠️ Charger Offline Alert"
                content = f"Charger '{charger_name}' (ID: {cp_id}) has been offline for more than 10 minutes."
            else:
                subject = "✅ Charger Back Online"
                content = f"Charger '{charger_name}' (ID: {cp_id}) is back online."
            
            message = Mail(
                from_email='alerts@chargerpulse.vercel.app',
                to_emails=user_email,
                subject=subject,
                plain_text_content=content
            )
            
            response = sg.send(message)
            logger.info(f"Email sent to {user_email} for charger {cp_id}")
        except Exception as e:
            logger.error(f"Error sending alert email: {e}")

async def alert_worker():
    """Background worker that checks for alerts every minute"""
    pool = await asyncpg.create_pool(DSN, min_size=2, max_size=10)
    alert_manager = AlertManager(pool)
    
    logger.info("Alert worker started")
    
    try:
        while True:
            await alert_manager.check_alerts()
            await asyncio.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Alert worker stopping...")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(alert_worker())