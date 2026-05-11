-- Create users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  stripe_customer TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create chargers table
CREATE TABLE chargers (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nickname TEXT,
  location TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create events table
CREATE TABLE events (
  id BIGSERIAL PRIMARY KEY,
  cp_id TEXT NOT NULL REFERENCES chargers(id) ON DELETE CASCADE,
  connector_id INT NOT NULL,
  status TEXT NOT NULL,
  ts TIMESTAMPTZ DEFAULT now()
);

-- Create alerts table
CREATE TABLE alerts (
  id BIGSERIAL PRIMARY KEY,
  cp_id TEXT NOT NULL REFERENCES chargers(id) ON DELETE CASCADE,
  triggered_at TIMESTAMPTZ NOT NULL,
  cleared_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX idx_chargers_user_id ON chargers(user_id);
CREATE INDEX idx_events_cp_id ON events(cp_id);
CREATE INDEX idx_events_ts ON events(ts DESC);
CREATE INDEX idx_alerts_cp_id ON alerts(cp_id);
CREATE INDEX idx_alerts_triggered_at ON alerts(triggered_at DESC);
CREATE INDEX idx_alerts_cleared_at ON alerts(cleared_at DESC) WHERE cleared_at IS NOT NULL;