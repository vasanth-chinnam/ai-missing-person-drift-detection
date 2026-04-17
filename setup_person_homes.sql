-- Create the person_homes table for per-person home locations
CREATE TABLE IF NOT EXISTS person_homes (
  person_id TEXT PRIMARY KEY,
  home_lat DOUBLE PRECISION NOT NULL,
  home_lon DOUBLE PRECISION NOT NULL,
  radius_m INTEGER DEFAULT 500,
  updated_at TIMESTAMP DEFAULT now()
);

-- Enable Row-Level Security (table is secured just like locations)
ALTER TABLE person_homes ENABLE ROW LEVEL SECURITY;

-- Seed your existing home location for P001
INSERT INTO person_homes (person_id, home_lat, home_lon, radius_m)
VALUES ('P001', 17.3972319, 78.6100460, 500)
ON CONFLICT (person_id) DO NOTHING;
