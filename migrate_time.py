import re
from datetime import datetime, timedelta
from sqlalchemy import text
from db.db import engine

def migrate():
    with engine.connect() as conn:
        # 1. Fetch current reports
        rows = conn.execute(text('SELECT id, "timeAgo" FROM reports')).fetchall()
        now = datetime.utcnow()
        for row in rows:
            row_id = row[0]
            time_str = row[1]
            ts = now
            if time_str and str(time_str).strip() != 'just now':
                m = re.match(r'([\d.]+)\s*(min|hr|hour|day)s?\s*ago', str(time_str).strip())
                if m:
                    val = float(m.group(1))
                    unit = m.group(2)
                    if unit == 'min':
                        ts = now - timedelta(minutes=val)
                    elif 'hr' in unit or 'hour' in unit:
                        ts = now - timedelta(hours=val)
                    elif 'day' in unit:
                        ts = now - timedelta(days=val)
            conn.execute(
                text('UPDATE reports SET "timeAgo" = :ts WHERE id = :id'),
                {'ts': ts.strftime('%Y-%m-%d %H:%M:%S'), 'id': row_id}
            )

        # 2. Alter column type to TIMESTAMP
        conn.execute(text('ALTER TABLE reports ALTER COLUMN "timeAgo" TYPE TIMESTAMP WITHOUT TIME ZONE USING "timeAgo"::timestamp'))

        # 3. Add timestamp to alerts if not exists
        conn.execute(text('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS "timestamp" TIMESTAMP WITHOUT TIME ZONE'))
        conn.execute(text('UPDATE alerts SET "timestamp" = NOW() - ("reportedMinutesAgo" || \' minutes\')::interval WHERE "timestamp" IS NULL'))

        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
