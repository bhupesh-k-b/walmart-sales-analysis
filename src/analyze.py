"""Build a MySQL warehouse and export SQL reports from public Walmart data."""
from pathlib import Path
from decimal import Decimal
import os
import json
import pandas as pd
import pymysql
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]

def connect():
    return pymysql.connect(host=os.getenv('MYSQL_HOST','127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT','3307')),user=os.getenv('MYSQL_USER','analyst'),
        password=os.environ['MYSQL_PASSWORD'],database=os.getenv('MYSQL_DATABASE','walmart'),
        charset='utf8mb4',autocommit=False)

def execute_file(conn,path):
    content='\n'.join(line for line in path.read_text().splitlines() if not line.lstrip().startswith('--'))
    with conn.cursor() as cursor:
        for statement in content.split(';'):
            if statement.strip():cursor.execute(statement)
    conn.commit()

def validate_input(sales,stores,features):
    for frame,keys in [(sales,['Store','Dept','Date']),(stores,['Store']),(features,['Store','Date'])]:
        if frame.duplicated(keys).any():raise ValueError(f'Duplicate key: {keys}')
        if frame[keys].isna().any().any():raise ValueError(f'Missing key: {keys}')
    if not set(sales.Store).issubset(set(stores.Store)):
        raise ValueError('Sales reference unknown stores')
    for frame in [sales,features]:
        if not pd.to_datetime(frame.Date,format='%Y-%m-%d',errors='raise').notna().all():
            raise ValueError('Invalid dates')
        if not frame.IsHoliday.isin([True,False]).all():raise ValueError('Invalid holiday flags')
    if sales.Weekly_Sales.isna().any():raise ValueError('Missing weekly sales')
    joined=sales.merge(features[['Store','Date','IsHoliday']],on=['Store','Date'],how='left',suffixes=('_sales','_features'),validate='many_to_one')
    if joined.IsHoliday_features.isna().any():raise ValueError('Missing store-week features')
    if not joined.IsHoliday_sales.eq(joined.IsHoliday_features).all():raise ValueError('Holiday mismatch')

def load(conn,table,frame):
    # Explicit column order is defined in run(); placeholders prevent SQL injection.
    statement=f"INSERT INTO {table} VALUES ({','.join(['%s']*len(frame.columns))})"
    with conn.cursor() as cursor:
        for start in range(0,len(frame),10_000):
            batch=frame.iloc[start:start+10_000].astype(object).where(frame.iloc[start:start+10_000].notna(),None)
            cursor.executemany(statement,list(batch.itertuples(index=False,name=None)))
    conn.commit()

def run(raw_dir=None):
    raw=Path(raw_dir) if raw_dir else ROOT/'data/raw'
    out=ROOT/'data/processed';out.mkdir(parents=True,exist_ok=True)
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    # Decimal preserves the source's cent precision during insert and reconciliation.
    sales=pd.read_csv(raw/'train.csv',converters={'Weekly_Sales':Decimal})
    stores=pd.read_csv(raw/'stores.csv')
    features=pd.read_csv(raw/'features.csv')
    validate_input(sales,stores,features)
    with connect() as conn:
        execute_file(conn,ROOT/'sql/01_schema.sql')
        load(conn,'stores',stores[['Store','Type','Size']])
        load(conn,'external_features',features[['Store','Date','Temperature','Fuel_Price','MarkDown1','MarkDown2','MarkDown3','MarkDown4','MarkDown5','CPI','Unemployment','IsHoliday']])
        load(conn,'sales',sales[['Store','Dept','Date','Weekly_Sales','IsHoliday']])
        execute_file(conn,ROOT/'sql/02_reporting.sql')
        def query(sql):
            with conn.cursor() as c:
                c.execute(sql)
                return pd.DataFrame(c.fetchall(),columns=[x[0] for x in c.description])
        tables={}
        for name,order in [('store_performance','sales_rank'),('department_performance','sales_rank'),('weekly_sales','week_date'),('holiday_comparison','is_holiday'),('forecast_backtest','week_date')]:
            tables[name]=query(f'SELECT * FROM {name} ORDER BY {order}')
            tables[name].to_csv(out/f'{name}.csv',index=False)
        audit=query('SELECT COUNT(*) AS rows_loaded,COUNT(DISTINCT store_id) AS stores,COUNT(DISTINCT department_id) AS departments,MIN(week_date) AS start_date,MAX(week_date) AS end_date,SUM(weekly_sales) AS total_sales,SUM(weekly_sales<0) AS negative_sales_rows FROM sales').iloc[0].to_dict()
        assert Decimal(str(audit['total_sales']))==sum(sales.Weekly_Sales), 'Revenue reconciliation failed'
        assert int(audit['rows_loaded'])==len(sales)
    bt=tables['forecast_backtest']
    assert len(bt)==12 and bt.seasonal_prediction.notna().all()
    weight=bt.evaluation_weight.astype(float)
    audit['forecast_evaluation']={
        'horizon':'rolling one-week-ahead; final 12 weeks',
        'naive_wmae':float((bt.naive_absolute_error.astype(float)*weight).sum()/weight.sum()),
        'seasonal_wmae':float((bt.seasonal_absolute_error.astype(float)*weight).sum()/weight.sum()),
        'unit':'national weekly sales dollars; holiday weight 5, otherwise 1'}
    audit['negative_sales_rows']=int(audit['negative_sales_rows'])
    audit={k: str(v) if isinstance(v,Decimal) or hasattr(v,'isoformat') else int(v) if hasattr(v,'item') else v for k,v in audit.items()}
    (reports/'metrics.json').write_text(json.dumps(audit,indent=2)+'\n')
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    w=tables['weekly_sales']
    axes[0].plot(pd.to_datetime(w.week_date),w.total_sales.astype(float)/1e6,color='#2563eb')
    axes[0].set_title('Walmart national weekly sales',loc='left',fontweight='bold')
    axes[0].set_ylabel('Sales (USD millions)')
    top=tables['store_performance'].head(10).iloc[::-1]
    axes[1].barh(top.store_id.astype(str),top.total_sales.astype(float)/1e6,color='#0f766e')
    axes[1].set_title('Top stores by observed sales',loc='left',fontweight='bold')
    axes[1].set_xlabel('Total sales (USD millions)');axes[1].set_ylabel('Anonymous store ID')
    fig.savefig(reports/'overview.png',dpi=160);plt.close(fig)
    leader=tables['store_performance'].iloc[0]
    department=tables['department_performance'].iloc[0]
    summary=f"""# Findings

Analyzed {audit['rows_loaded']:,} store-department-week observations from {audit['stores']} stores, {audit['start_date']} through {audit['end_date']}.

- Highest observed sales: store {int(leader.store_id)}, ${float(leader.total_sales):,.2f} across {int(leader.observed_weeks)} weeks.
- Highest department sales: anonymous department {int(department.department_id)}, ${float(department.total_sales):,.2f}.
- Retained {audit['negative_sales_rows']:,} negative sales observations; their cause is not specified, so they are not silently dropped.
- Rolling one-week-ahead final-12-week backtest: naive WMAE ${audit['forecast_evaluation']['naive_wmae']:,.2f}; seasonal WMAE ${audit['forecast_evaluation']['seasonal_wmae']:,.2f}. These are national totals, not department-level competition scores.

Use sales per square foot alongside total sales to compare differently sized stores. Review holiday peaks before staffing and replenishment planning. Department revenue ranks do not measure profitability or individual SKU demand. Holiday comparisons are descriptive and are not causal uplift estimates.

This source has no customer identities, transaction timestamps, cities, item names, unit quantities, costs, channel flags, or inventory. It cannot support peak operating hours, customer segmentation, profit margins, or claims of supply-chain improvement. Rows are weekly aggregates, not transactions.
"""
    (reports/'findings.md').write_text(summary)
    print(json.dumps(audit,indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=Path)
    run(p.parse_args().raw_dir)
