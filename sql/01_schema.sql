-- Rebuilds only these three project tables and their dependent views.
DROP VIEW IF EXISTS forecast_backtest;
DROP VIEW IF EXISTS weekly_sales;
DROP VIEW IF EXISTS department_performance;
DROP VIEW IF EXISTS store_performance;
DROP VIEW IF EXISTS holiday_comparison;
DROP VIEW IF EXISTS sales_features;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS external_features;
DROP TABLE IF EXISTS stores;
CREATE TABLE stores (
 store_id SMALLINT PRIMARY KEY,store_type CHAR(1) NOT NULL,
 size_sqft INTEGER NOT NULL CHECK(size_sqft>0)
);
CREATE TABLE external_features (
 store_id SMALLINT NOT NULL,week_date DATE NOT NULL,
 temperature DECIMAL(8,3),fuel_price DECIMAL(8,3),
 markdown1 DECIMAL(14,2),markdown2 DECIMAL(14,2),markdown3 DECIMAL(14,2),
 markdown4 DECIMAL(14,2),markdown5 DECIMAL(14,2),
 cpi DECIMAL(14,7),unemployment DECIMAL(8,3),is_holiday BOOLEAN NOT NULL,
 PRIMARY KEY(store_id,week_date),FOREIGN KEY(store_id) REFERENCES stores(store_id)
);
CREATE TABLE sales (
 store_id SMALLINT NOT NULL,department_id SMALLINT NOT NULL,week_date DATE NOT NULL,
 weekly_sales DECIMAL(14,2) NOT NULL,is_holiday BOOLEAN NOT NULL,
 PRIMARY KEY(store_id,department_id,week_date),
 FOREIGN KEY(store_id) REFERENCES stores(store_id),
 INDEX idx_sales_date(week_date)
);
