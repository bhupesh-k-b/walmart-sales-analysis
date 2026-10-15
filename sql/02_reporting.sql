CREATE OR REPLACE VIEW sales_features AS
SELECT s.*,st.store_type,st.size_sqft,YEAR(s.week_date) AS sales_year,
 MONTH(s.week_date) AS sales_month,WEEK(s.week_date,3) AS iso_week,
 s.weekly_sales/st.size_sqft AS department_sales_per_store_sqft,
 f.temperature,f.fuel_price,f.cpi,f.unemployment,
 f.markdown1,f.markdown2,f.markdown3,f.markdown4,f.markdown5,
 -- Missing markdown amounts stay unknown; do not conflate with no promotion.
 (f.markdown1 IS NULL OR f.markdown2 IS NULL OR f.markdown3 IS NULL
  OR f.markdown4 IS NULL OR f.markdown5 IS NULL) AS missing_markdown,
 LAG(s.weekly_sales) OVER(PARTITION BY s.store_id,s.department_id ORDER BY s.week_date) AS prior_observed_week_sales,
 DATEDIFF(s.week_date,LAG(s.week_date) OVER(PARTITION BY s.store_id,s.department_id ORDER BY s.week_date)) AS days_since_prior_observation
FROM sales s JOIN stores st USING(store_id)
LEFT JOIN external_features f ON f.store_id=s.store_id AND f.week_date=s.week_date;

CREATE OR REPLACE VIEW store_performance AS
WITH store_weeks AS (
 SELECT store_id,week_date,SUM(weekly_sales) AS sales FROM sales GROUP BY store_id,week_date
), summary AS (
 SELECT store_id,COUNT(*) AS observed_weeks,SUM(sales) AS total_sales,
 AVG(sales) AS avg_weekly_sales,STDDEV_POP(sales) AS weekly_volatility
 FROM store_weeks GROUP BY store_id
)
SELECT s.*,st.store_type,st.size_sqft,
 s.avg_weekly_sales/st.size_sqft AS avg_weekly_sales_per_sqft,
 DENSE_RANK() OVER(ORDER BY s.total_sales DESC) AS sales_rank
FROM summary s JOIN stores st USING(store_id);

CREATE OR REPLACE VIEW department_performance AS
SELECT department_id,COUNT(DISTINCT store_id) AS stores,COUNT(*) AS store_weeks,
 SUM(weekly_sales) AS total_sales,AVG(weekly_sales) AS avg_store_week_sales,
 SUM(weekly_sales<0) AS negative_sales_weeks,
 DENSE_RANK() OVER(ORDER BY SUM(weekly_sales) DESC) AS sales_rank
FROM sales GROUP BY department_id;

CREATE OR REPLACE VIEW weekly_sales AS
WITH aggregate_sales AS (
 SELECT week_date,is_holiday,SUM(weekly_sales) AS total_sales,
 COUNT(*) AS reporting_store_departments FROM sales GROUP BY week_date,is_holiday
)
SELECT *,LAG(total_sales) OVER(ORDER BY week_date) AS prior_week_sales,
 total_sales/NULLIF(LAG(total_sales) OVER(ORDER BY week_date),0)-1 AS wow_growth
FROM aggregate_sales;

CREATE OR REPLACE VIEW holiday_comparison AS
SELECT is_holiday,COUNT(*) AS weeks,AVG(total_sales) AS avg_national_week_sales,
 MIN(total_sales) AS min_national_week_sales,MAX(total_sales) AS max_national_week_sales
FROM weekly_sales GROUP BY is_holiday;

-- Fixed holdout: final 12 observed weeks. Seasonal lag is exact 364 days.
-- Rolling one-week-ahead backtest: earlier holdout actuals are available at
-- each prediction origin. This is NOT a single-origin 12-week forecast.
CREATE OR REPLACE VIEW forecast_backtest AS
SELECT w.week_date,w.is_holiday,w.total_sales AS actual_sales,
 w.prior_week_sales AS naive_prediction,prior_year.total_sales AS seasonal_prediction,
 ABS(w.total_sales-w.prior_week_sales) AS naive_absolute_error,
 ABS(w.total_sales-prior_year.total_sales) AS seasonal_absolute_error,
 CASE WHEN w.is_holiday THEN 5 ELSE 1 END AS evaluation_weight
FROM weekly_sales w LEFT JOIN weekly_sales prior_year
 ON prior_year.week_date=DATE_SUB(w.week_date,INTERVAL 364 DAY)
WHERE w.week_date>DATE_SUB((SELECT MAX(week_date) FROM sales),INTERVAL 84 DAY);
