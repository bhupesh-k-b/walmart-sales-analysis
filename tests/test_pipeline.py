from pathlib import Path
from datetime import date,timedelta
import os
import shutil
import json
import pandas as pd
import pytest
from src import analyze

def fixture_data():
    rows=[]
    for i in range(70):
        day=(date(2010,2,5)+timedelta(weeks=i)).isoformat()
        for dept in [1,2]:rows.append([1,dept,day,-10 if i==0 and dept==1 else 100+i,bool(i%10==0)])
    sales=pd.DataFrame(rows,columns=['Store','Dept','Date','Weekly_Sales','IsHoliday'])
    stores=pd.DataFrame([[1,'A',1000]],columns=['Store','Type','Size'])
    f=sales[['Store','Date','IsHoliday']].drop_duplicates().copy()
    for c in ['Temperature','Fuel_Price','MarkDown1','MarkDown2','MarkDown3','MarkDown4','MarkDown5','CPI','Unemployment']:f[c]=float('nan')
    return sales,stores,f

def test_reject_duplicate_grain():
    sales,stores,f=fixture_data()
    with pytest.raises(ValueError,match='Duplicate key'):
        analyze.validate_input(pd.concat([sales,sales.iloc[:1]]),stores,f)

def test_reject_unknown_store_and_missing_features():
    sales,stores,f=fixture_data()
    invalid=sales.copy();invalid.loc[0,'Store']=99
    with pytest.raises(ValueError,match='unknown stores'):analyze.validate_input(invalid,stores,f)
    with pytest.raises(ValueError,match='Missing store-week'):analyze.validate_input(sales,stores,f.iloc[1:])

@pytest.mark.skipif(not os.getenv('MYSQL_PASSWORD'),reason='Set MYSQL_PASSWORD and start MySQL to run integration test')
def test_mysql_end_to_end(tmp_path,monkeypatch):
    assert os.getenv('MYSQL_DATABASE','').endswith('_test'), 'Integration tests require a dedicated MYSQL_DATABASE ending in _test'
    shutil.copytree(analyze.ROOT/'sql',tmp_path/'sql')
    raw=tmp_path/'raw';raw.mkdir()
    for name,frame in zip(['train','stores','features'],fixture_data()):frame.to_csv(raw/f'{name}.csv',index=False)
    monkeypatch.setattr(analyze,'ROOT',tmp_path)
    analyze.run(raw)
    metrics=json.loads((tmp_path/'reports/metrics.json').read_text())
    assert metrics['rows_loaded']==140
    assert metrics['negative_sales_rows']==1
    assert len(pd.read_csv(tmp_path/'data/processed/forecast_backtest.csv'))==12
    assert metrics['forecast_evaluation']['naive_wmae']==2.0
