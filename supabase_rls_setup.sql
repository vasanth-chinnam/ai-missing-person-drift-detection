-- run this in the Supabase SQL Editor to secure your tables

-- Enable RLS for locations table
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;

-- Allow public read access (the app needs to read the history)
CREATE POLICY "Allow public read access" ON locations 
FOR SELECT USING (true);

-- Allow public insert access (the app needs to insert new locations)
CREATE POLICY "Allow public insert access" ON locations 
FOR INSERT WITH CHECK (true);

-- Create the system_metadata table since it appears to be entirely missing!
CREATE TABLE IF NOT EXISTS system_metadata (
  key text PRIMARY KEY,
  value text NOT NULL
);

-- Enable RLS for system_metadata table (used for SMS/Voice cooldown tracking)
ALTER TABLE system_metadata ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access" ON system_metadata 
FOR SELECT USING (true);

-- Allow public upsert/insert access
CREATE POLICY "Allow public upsert access" ON system_metadata 
FOR INSERT WITH CHECK (true);

-- Allow public update access
CREATE POLICY "Allow public update access" ON system_metadata 
FOR UPDATE USING (true);
