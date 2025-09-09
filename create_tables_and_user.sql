-- Create tables
CREATE TABLE IF NOT EXISTS "User" (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    company_name TEXT,
    role TEXT NOT NULL,
    plan TEXT NOT NULL,
    credits_remaining INTEGER DEFAULT 0,
    credits_total INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "APIKey" (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "User"(id)
);

CREATE TABLE IF NOT EXISTS "CreditTransaction" (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES "User"(id)
);

-- Insert client user
INSERT INTO "User" (
    id, 
    email, 
    username, 
    password_hash, 
    full_name, 
    role, 
    plan, 
    credits_remaining, 
    credits_total, 
    is_active
) VALUES (
    'client_user_id', 
    'client@client.com', 
    'client', 
    '$2b$12$SzzpgO.Ey1d8ectg9BqT1u4TFg0yXdPJ8F/MV1G/smRKnYuwgDxvi', -- 'client' hashed
    'Client User', 
    'USER', 
    'FREE', 
    100, 
    100, 
    true
) ON CONFLICT (email) DO NOTHING;