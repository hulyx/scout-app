"""POD Database - Separate file to avoid escaping issues."""

from scout.db import get_connection, logger

def _migrate_pod_schema(conn):
    """Apply POD schema SQL."""
    from scout.db import POD_SCHEMA_SQL
    statements = [s.strip() for s in POD_SCHEMA_SQL.split(';') if s.strip()]
    for stmt in statements:
        try:
            conn.execute(stmt)
        except Exception as e:
            logger.warning(f'POD migration statement failed: {e}')
    conn.commit()
    logger.info("Migration: applied POD schema")


class PodKeywordRepository:
    """Data access for pod_keywords table."""

    def __init__(self, conn=None):
        self._conn = conn or get_connection()
        self._owns_conn = conn is None

    def close(self):
        if self._owns_conn:
            self._conn.close()

    def upsert(self, keyword, data):
        existing = self._conn.execute(
            'SELECT id FROM pod_keywords WHERE keyword = ?', (keyword,)
        ).fetchone()
        if existing:
            sets = ', '.join(f'{k} = ?' for k in data.keys())
            vals = list(data.values()) + [keyword]
            self._conn.execute(f'UPDATE pod_keywords SET {sets} WHERE keyword = ?', vals)
        else:
            cols = ', '.join(['keyword'] + list(data.keys()))
            qs = ', '.join(['?'] * (len(data) + 1))
            vals = [keyword] + list(data.values())
            self._conn.execute(f'INSERT INTO pod_keywords ({cols}) VALUES ({qs})', vals)
        self._conn.commit()

    def get_all(self):
        return self._conn.execute('SELECT * FROM pod_keywords ORDER BY score DESC').fetchall()

    def get_by_category(self, category):
        return self._conn.execute(
            'SELECT * FROM pod_keywords WHERE niche_category = ? ORDER BY score DESC', (category,)
        ).fetchall()

    def delete_all(self):
        self._conn.execute('DELETE FROM pod_keywords')
        self._conn.commit()


class PodListingRepository:
    """Data access for pod_listings table."""

    def __init__(self, conn=None):
        self._conn = conn or get_connection()
        self._owns_conn = conn is None

    def close(self):
        if self._owns_conn:
            self._conn.close()

    def insert(self, keyword_id, listing):
        self._conn.execute(
            """INSERT INTO pod_listings
               (keyword_id, platform, title, seller, price, reviews_count, is_bestseller, url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                keyword_id, listing.get('platform'), listing.get('title'),
                listing.get('seller'), listing.get('price'),
                listing.get('reviews_count'), listing.get('is_bestseller'),
                listing.get('url'),
            ),
        )
        self._conn.commit()

    def get_by_keyword(self, keyword_id):
        return self._conn.execute(
            'SELECT * FROM pod_listings WHERE keyword_id = ?', (keyword_id,)
        ).fetchall()


class PodNicheRepository:
    """Data access for pod_niche_analyses table."""

    def __init__(self, conn=None):
        self._conn = conn or get_connection()
        self._owns_conn = conn is None

    def close(self):
        if self._owns_conn:
            self._conn.close()

    def insert(self, data):
        self._conn.execute(
            """INSERT INTO pod_niche_analyses
               (niche, demand_score, competition_score, profitability_score, trend_score, global_score, recommended_platform)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get('niche'), data.get('demand_score'), data.get('competition_score'),
                data.get('profitability_score'), data.get('trend_score'),
                data.get('global_score'), data.get('recommended_platform'),
            ),
        )
        self._conn.commit()

    def get_all(self):
        return self._conn.execute(
            'SELECT * FROM pod_niche_analyses ORDER BY global_score DESC'
        ).fetchall()
