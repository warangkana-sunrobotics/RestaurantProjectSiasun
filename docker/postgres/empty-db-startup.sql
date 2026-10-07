CREATE TABLE public.orders (
    order_id BIGINT PRIMARY KEY,
    table_id BIGINT,
    menu VARCHAR(255),
    cost REAL
);
