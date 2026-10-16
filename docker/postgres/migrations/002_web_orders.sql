-- เพิ่มตารางเมนู + คอลัมน์ menu_id / quantity / status / paid_at ให้ orders (ปลอดภัยต่อการรันซ้ำ)
-- ต้องรัน 001_orders_identity.sql มาก่อน
-- รันด้วย: Get-Content docker/postgres/migrations/002_web_orders.sql | docker exec -i daily-postgres psql -U <user> -d <db>
BEGIN;

CREATE TABLE IF NOT EXISTS public.menu (
    menu_id   INT PRIMARY KEY,
    name      VARCHAR(255)  NOT NULL CHECK (length(btrim(name)) > 0),
    price     NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    category  VARCHAR(50)   NOT NULL,
    emoji     VARCHAR(16)   NOT NULL DEFAULT '',
    available BOOLEAN       NOT NULL DEFAULT TRUE
);

INSERT INTO public.menu (menu_id, name, price, category, emoji) VALUES
    (1, 'ข้าวมันไก่กุ๊กๆ',          50,  'จานเดียว',  '🍗'),
    (2, 'ข้าวผัดกระเพราหมูกรอบ',    65,  'จานเดียว',  '🍳'),
    (3, 'ก๋วยเตี๋ยวต้มยำกุ้ง',      80,  'ต้ม/แกง',   '🍜'),
    (4, 'ต้มยำกุ้งน้ำข้น',          150, 'ต้ม/แกง',   '🥘'),
    (5, 'ชาไทยเย็น',                35,  'เครื่องดื่ม', '🧋')
ON CONFLICT (menu_id) DO NOTHING;

ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS menu_id  INT REFERENCES public.menu (menu_id);
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS quantity INT NOT NULL DEFAULT 1;
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS status   VARCHAR(10) NOT NULL DEFAULT 'open';
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS paid_at  TIMESTAMPTZ;

DO $$ BEGIN
    ALTER TABLE public.orders ADD CONSTRAINT orders_quantity_check CHECK (quantity BETWEEN 1 AND 99);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TABLE public.orders ADD CONSTRAINT orders_status_check CHECK (status IN ('open', 'paid'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_orders_table_status ON public.orders (table_id, status);
COMMIT;
