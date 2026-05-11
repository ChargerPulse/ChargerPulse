# Fly.io Deployment & PostgreSQL Setup Guide

## Prerequisites
- Fly.io account (https://fly.io)
- Fly CLI installed: `curl -L https://fly.io/install.sh | sh`
- GitHub account (ChargerPulse repo)
- SendGrid API key
- Supabase project (for auth/dashboard)

---

## Step 1: Authenticate with Fly.io

```bash
fly auth login
```

Follow the browser prompt to authenticate.

---

## Step 2: Create PostgreSQL Database on Fly.io

### Option A: Create Managed PostgreSQL (Recommended)

```bash
# Create a new PostgreSQL app
fly postgres create --name chargerpulse-db --region iad

# This will output your DATABASE_URL:
# postgres://postgres:XXXX@chargerpulse-db.internal:5432/chargerpulse
```

**Save the output!** You'll need the `DATABASE_URL`.

### Option B: Use External PostgreSQL (if you have one)
```
DATABASE_URL=postgresql://user:password@host:port/dbname
```

---

## Step 3: Create Backend App on Fly.io

```bash
# Create the OCPP server app
fly app create --name chargerpulse --region iad
```

---

## Step 4: Add PostgreSQL Network Connection

If using Fly.io PostgreSQL, add the network attachment:

```bash
# Attach the database to your app
fly postgres attach chargerpulse-db --app chargerpulse
```

This automatically sets `DATABASE_URL` in your app.

---

## Step 5: Set Environment Secrets

```bash
# SendGrid API Key
fly secrets set SENDGRID_KEY="your-sendgrid-api-key" --app chargerpulse

# Database URL (if not using managed PostgreSQL)
fly secrets set DATABASE_URL="your-postgresql-url" --app chargerpulse

# Optional: SSL Certificates (if using self-signed)
fly secrets set SSL_CERT_PATH="/app/cert.pem" --app chargerpulse
fly secrets set SSL_KEY_PATH="/app/key.pem" --app chargerpulse
```

---

## Step 6: Deploy Backend

```bash
# Clone and navigate to your repo
git clone https://github.com/ChargerPulse/ChargerPulse.git
cd ChargerPulse

# Deploy to Fly.io
fly deploy --app chargerpulse --region iad

# Alternatively, use the one-liner:
fly launch --now --region iad
```

---

## Step 7: Initialize Database Schema

```bash
# SSH into the app
fly ssh console --app chargerpulse

# Inside the console, run psql
psql $DATABASE_URL -f schema.sql
```

Or directly:

```bash
# From your local machine
psql $DATABASE_URL < schema.sql
```

To get your DATABASE_URL from Fly.io:

```bash
fly secrets list --app chargerpulse
```

---

## Step 8: Verify Deployment

```bash
# Check app status
fly status --app chargerpulse

# View logs
fly logs --app chargerpulse

# Test WebSocket endpoint
echo "App should be running at: wss://chargerpulse.fly.dev/ocpp"
```

---

## Step 9: Deploy Frontend (Vercel)

```bash
# Create Next.js app
npx create-next-app@latest chargerpulse-ui

# Add Supabase client
npm install @supabase/supabase-js

# Set environment variables in .env.local
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_KEY=your-supabase-key
NEXT_PUBLIC_API_URL=wss://chargerpulse.fly.dev

# Deploy to Vercel
npm run build
vercel deploy --prod
```

---

## Complete Environment Variables Reference

### Backend (.env)
```
DATABASE_URL=postgresql://postgres:PASSWORD@chargerpulse-db.internal:5432/chargerpulse
SENDGRID_KEY=SG.xxxx...
SSL_CERT_PATH=/app/cert.pem
SSL_KEY_PATH=/app/key.pem
```

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_KEY=eyJhbGc...
NEXT_PUBLIC_API_URL=wss://chargerpulse.fly.dev
```

---

## Useful Fly.io Commands

```bash
# View all apps
fly apps list

# Monitor metrics
fly metrics --app chargerpulse

# Scale app
fly scale count --app chargerpulse --max 3

# Update secrets
fly secrets set KEY=VALUE --app chargerpulse

# Remove secret
fly secrets unset KEY --app chargerpulse

# SSH into app
fly ssh console --app chargerpulse

# View recent deployments
fly history --app chargerpulse

# Rollback to previous version
fly releases rollback --app chargerpulse
```

---

## Troubleshooting

### Database Connection Fails
```bash
# Verify DATABASE_URL is set
fly secrets list --app chargerpulse

# Check if database is running
fly status --app chargerpulse-db
```

### WebSocket Connection Fails
```bash
# Check logs for errors
fly logs --app chargerpulse --level warn

# Verify SSL certificates are valid
openssl s_client -connect chargerpulse.fly.dev:443
```

### Out of Memory
```bash
# Increase app memory
fly scale memory --app chargerpulse 512
```

---

## Next Steps

1. ✅ Create Fly.io account
2. ✅ Create PostgreSQL database
3. ✅ Deploy backend to Fly.io
4. ✅ Initialize database schema
5. ✅ Create Next.js frontend
6. ✅ Deploy frontend to Vercel
7. ✅ Test WebSocket connection

**Final Endpoint:** `wss://chargerpulse.fly.dev/ocpp`