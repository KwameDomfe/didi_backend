"""
Idempotent schema reconciliation migration.

Brings the PostgreSQL database in line with the current model state by
re-applying every schema change from 0002-0018 using IF NOT EXISTS / IF EXISTS
guards.  Safe to run on a fully up-to-date DB (all statements become no-ops)
and safe to run on a DB that is missing some of those changes.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("restaurants", "0018_add_lat_lng_to_restaurant"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
-- ── 0002: meal_period on MenuCategory ────────────────────────────────────────
ALTER TABLE restaurants_menucategory
    ADD COLUMN IF NOT EXISTS meal_period VARCHAR(20) NOT NULL DEFAULT 'all_day';

-- ── 0003: delivery fields on Restaurant ──────────────────────────────────────
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS delivery_fee NUMERIC(6,2) NOT NULL DEFAULT 2.99;
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS delivery_time VARCHAR(50) NOT NULL DEFAULT '30-45 min';
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS min_order NUMERIC(8,2) NOT NULL DEFAULT 15.0;

-- ── 0004: slug columns ────────────────────────────────────────────────────────
ALTER TABLE restaurants_menuitem
    ADD COLUMN IF NOT EXISTS slug VARCHAR(255);
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS slug VARCHAR(255);

-- Backfill slugs for any rows that are missing them
UPDATE restaurants_menuitem
    SET slug = LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g')) || '-' || id
    WHERE slug IS NULL OR slug = '';
UPDATE restaurants_restaurant
    SET slug = LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g')) || '-' || id
    WHERE slug IS NULL OR slug = '';

-- Add UNIQUE constraints for slug (skipped if one already exists on that column)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'restaurants_menuitem'
          AND tc.constraint_type = 'UNIQUE'
          AND ccu.column_name = 'slug'
    ) THEN
        ALTER TABLE restaurants_menuitem
            ADD CONSTRAINT restaurants_menuitem_slug_uniq UNIQUE (slug);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'restaurants_restaurant'
          AND tc.constraint_type = 'UNIQUE'
          AND ccu.column_name = 'slug'
    ) THEN
        ALTER TABLE restaurants_restaurant
            ADD CONSTRAINT restaurants_restaurant_slug_uniq UNIQUE (slug);
    END IF;
END $$;

-- ── 0005: image on MenuCategory ───────────────────────────────────────────────
ALTER TABLE restaurants_menucategory
    ADD COLUMN IF NOT EXISTS image VARCHAR(100) NOT NULL DEFAULT '';

-- ── 0006: make prep_time nullable with default 0 ─────────────────────────────
ALTER TABLE restaurants_menuitem ALTER COLUMN prep_time DROP NOT NULL;
ALTER TABLE restaurants_menuitem ALTER COLUMN prep_time SET DEFAULT 0;

-- ── 0008: owner FK on Restaurant ─────────────────────────────────────────────
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS owner_id BIGINT
    REFERENCES accounts_customuser(id) ON DELETE CASCADE;

-- ── 0009: OptionGroup and OptionChoice ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants_optiongroup (
    id           BIGSERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    required     BOOLEAN NOT NULL DEFAULT FALSE,
    min_selections SMALLINT NOT NULL DEFAULT 1,
    max_selections SMALLINT NOT NULL DEFAULT 1,
    menu_item_id BIGINT NOT NULL
        REFERENCES restaurants_menuitem(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurants_optionchoice (
    id             BIGSERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    price_modifier NUMERIC(8,2) NOT NULL DEFAULT 0,
    group_id       BIGINT NOT NULL
        REFERENCES restaurants_optiongroup(id) ON DELETE CASCADE
);

-- ── 0010 + 0012: remove ingredients from MenuItem ────────────────────────────
ALTER TABLE restaurants_menuitem DROP COLUMN IF EXISTS ingredients CASCADE;

-- ── 0013: MenuItemShare / MenuItemComment / MenuItemLike ─────────────────────
CREATE TABLE IF NOT EXISTS restaurants_menuitemshare (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    menu_item_id BIGINT NOT NULL
        REFERENCES restaurants_menuitem(id) ON DELETE CASCADE,
    user_id      BIGINT
        REFERENCES accounts_customuser(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurants_menuitemcomment (
    id           BIGSERIAL PRIMARY KEY,
    comment      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    menu_item_id BIGINT NOT NULL
        REFERENCES restaurants_menuitem(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL
        REFERENCES accounts_customuser(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurants_menuitemlike (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    menu_item_id BIGINT NOT NULL
        REFERENCES restaurants_menuitem(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL
        REFERENCES accounts_customuser(id) ON DELETE CASCADE,
    UNIQUE (menu_item_id, user_id)
);

-- ── 0014: Cuisine ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants_cuisine (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    image       VARCHAR(100) NOT NULL DEFAULT ''
);

-- ── 0015: remove cuisine_type, add cuisine FK ────────────────────────────────
ALTER TABLE restaurants_restaurant DROP COLUMN IF EXISTS cuisine_type CASCADE;
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS cuisine_id BIGINT
    REFERENCES restaurants_cuisine(id) ON DELETE SET NULL;

-- ── 0016: RestaurantComment / RestaurantLike ──────────────────────────────────
CREATE TABLE IF NOT EXISTS restaurants_restaurantcomment (
    id            BIGSERIAL PRIMARY KEY,
    text          TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    restaurant_id BIGINT NOT NULL
        REFERENCES restaurants_restaurant(id) ON DELETE CASCADE,
    user_id       BIGINT NOT NULL
        REFERENCES accounts_customuser(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurants_restaurantlike (
    id            BIGSERIAL PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    restaurant_id BIGINT NOT NULL
        REFERENCES restaurants_restaurant(id) ON DELETE CASCADE,
    user_id       BIGINT NOT NULL
        REFERENCES accounts_customuser(id) ON DELETE CASCADE,
    UNIQUE (restaurant_id, user_id)
);

-- ── 0017: parent FK on RestaurantComment ─────────────────────────────────────
ALTER TABLE restaurants_restaurantcomment
    ADD COLUMN IF NOT EXISTS parent_id BIGINT
    REFERENCES restaurants_restaurantcomment(id) ON DELETE CASCADE;

-- ── 0018: latitude / longitude on Restaurant ─────────────────────────────────
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(9,6);
ALTER TABLE restaurants_restaurant
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(9,6);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
