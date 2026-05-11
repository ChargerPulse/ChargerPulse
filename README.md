# ChargerPulse 🔌⚡

A modern, scalable OCPP (Open Charge Point Protocol) server with real-time WebSocket communication, PostgreSQL backend, and a beautiful Next.js dashboard.

## Features

✅ **OCPP 1.6 Compliant** - Full support for Open Charge Point Protocol v1.6  
✅ **Real-Time WebSocket** - Live charger status updates  
✅ **PostgreSQL Database** - Persistent event storage and alerting  
✅ **Alert System** - Automatic email notifications for charger downtime  
✅ **Scalable Architecture** - Async/await with connection pooling  
✅ **Fly.io Ready** - One-command deployment  
✅ **Production-Grade** - Error handling, logging, monitoring  

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ChargerPulse                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Backend (main.py + alerts.py)     Frontend (Next.js)  │
│  ├─ OCPP Server (Fly.io)           ├─ Dashboard UI     │
│  ├─ Alert Manager                  ├─ Real-time Stats  │
│  ├─ SendGrid Integration           └─ Authentication   │
│  └─ Async Task Queue               (Vercel)            │
│                │                                        │
│                └─────────┬──────────────────┐           │
│                          │                  │           │
│                   PostgreSQL DB       Supabase Auth     │
│                   (Fly.io)                              │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Fly.io account
- SendGrid API key
- Git

### Local Development

```bash
# Clone repository
git clone https://github.com/ChargerPulse/ChargerPulse.git
cd ChargerPulse

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
echo "DATABASE_URL=postgresql://user:pass@localhost/chargerpulse" > .env
echo "SENDGRID_KEY=your-sendgrid-key" >> .env

# Run database migrations
psql $DATABASE_URL < schema.sql

# Start server
python main.py

# In another terminal, start alert worker
python alerts.py
```

### Docker Build

```bash
# Build image
docker build -t chargerpulse:latest .

# Run container
docker run -e DATABASE_URL="postgresql://..." \
           -e SENDGRID_KEY="SG.xxx" \
           -p 443:443 \
           chargerpulse:latest
```

---

## Deployment on Fly.io

### One-Command Deploy

```bash
fly launch --now --region iad
```

### Full Setup Guide

See [FLY_IO_SETUP.md](./FLY_IO_SETUP.md) for comprehensive instructions including:
- PostgreSQL database creation
- Environment secrets configuration
- Database schema initialization
- WebSocket endpoint verification

---

## API Endpoints

### WebSocket
```
wss://chargerpulse.fly.dev/ocpp
```

Receives OCPP messages from charge points.

**Example Connection:**
```python
import websockets
import asyncio

async def connect():
    async with websockets.connect("wss://chargerpulse.fly.dev/ocpp/CP001") as ws:
        # Send OCPP messages
        await ws.send(json.dumps([...]))
        # Receive responses
        response = await ws.recv()
```

---

## Database Schema

### Tables

**users**
```sql
id UUID PRIMARY KEY
email TEXT UNIQUE
stripe_customer TEXT
created_at TIMESTAMPTZ
```

**chargers**
```sql
id TEXT PRIMARY KEY
user_id UUID REFERENCES users(id)
nickname TEXT
location TEXT
```

**events**
```sql
id BIGSERIAL PRIMARY KEY
cp_id TEXT REFERENCES chargers(id)
connector_id INT
status TEXT
ts TIMESTAMPTZ
```

**alerts**
```sql
id BIGSERIAL PRIMARY KEY
cp_id TEXT REFERENCES chargers(id)
triggered_at TIMESTAMPTZ
cleared_at TIMESTAMPTZ
```

For full schema, see [schema.sql](./schema.sql).

---

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/chargerpulse

# Email Alerts
SENDGRID_KEY=SG.xxxxxxxxxxxx

# Optional: SSL Certificates
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Alert Configuration

Edit `alerts.py` to customize:

```python
self.offline_threshold = 600  # 10 minutes in seconds
await asyncio.sleep(60)  # Check every 60 seconds
```

---

## Project Board

See [PROJECT_BOARD.md](./PROJECT_BOARD.md) for the full development roadmap with:
- 4-column Kanban board (Back-End, Front-End, Ops, Marketplace)
- 38+ tasks across all areas
- Sprint planning for MVP and beyond

---

## Frontend (Next.js Dashboard)

The companion dashboard is in a separate repository:

```bash
npx create-next-app@latest chargerpulse-ui
cd chargerpulse-ui
npm install @supabase/supabase-js
```

See [chargerpulse-ui](https://github.com/ChargerPulse/chargerpulse-ui) repository.

---

## Monitoring & Logs

### Fly.io Logs

```bash
fly logs --app chargerpulse
fly logs --app chargerpulse --level warn
```

### Metrics

```bash
fly metrics --app chargerpulse
```

### SSH Access

```bash
fly ssh console --app chargerpulse
psql $DATABASE_URL
```

---

## Troubleshooting

### WebSocket Connection Fails
```bash
# Check if server is running
fly status --app chargerpulse

# View recent logs
fly logs --app chargerpulse --lines 50
```

### Database Connection Error
```bash
# Verify DATABASE_URL
fly secrets list --app chargerpulse

# Check database status
fly status --app chargerpulse-db
```

### Memory Issues
```bash
# Increase app memory
fly scale memory --app chargerpulse 512
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see LICENSE file for details

---

## Support

- 📖 [OCPP Documentation](https://www.ocpp-chargepoint.org/)
- 🚀 [Fly.io Docs](https://fly.io/docs)
- 💬 [OCPP Forum](https://www.openchargealliance.org/)
- 📧 Contact: support@chargerpulse.dev

---

**Made with ❤️ by ChargerPulse Team**