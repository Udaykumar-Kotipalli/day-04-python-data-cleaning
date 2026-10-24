from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"; OUT.mkdir(exist_ok=True)
df=pd.read_csv(ROOT/"data"/"retail_orders_raw.csv"); n=len(df)
text=["order_id","customer_name","email","city","sales_channel","product_category","product"]
for c in text: df[c]=df[c].astype("string").str.strip()
for c in ["city","sales_channel","product_category"]: df[c]=df[c].str.title()
df["order_date"]=pd.to_datetime(df["order_date"],errors="coerce")
for c in ["quantity","unit_price_inr","discount_rate"]: df[c]=pd.to_numeric(df[c],errors="coerce")
quality={"input_rows":int(n),"duplicate_order_ids":int(df["order_id"].duplicated().sum()),"invalid_dates":int(df["order_date"].isna().sum()),"invalid_emails":int((~df["email"].fillna("").str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")).sum()),"non_positive_quantity":int((df["quantity"].isna()|(df["quantity"]<=0)).sum()),"non_positive_price":int((df["unit_price_inr"].isna()|(df["unit_price_inr"]<=0)).sum()),"invalid_discount":int((df["discount_rate"].isna()|~df["discount_rate"].between(0,1)).sum())}
df=df.drop_duplicates("order_id")
df=df[df["order_id"].notna()&(df["order_id"]!="")&df["order_date"].notna()&df["quantity"].gt(0)&df["unit_price_inr"].gt(0)&df["discount_rate"].between(0,1)&df["product_category"].notna()&(df["product_category"]!="")&df["product"].notna()&(df["product"]!="")].copy()
df["gross_sales_inr"]=(df.quantity*df.unit_price_inr).round(2)
df["net_sales_inr"]=(df.gross_sales_inr*(1-df.discount_rate)).round(2)
for c,default in [("customer_name","Unknown"),("city","Unknown"),("email","Missing"),("sales_channel","Unknown")]:
 df[c]=df[c].fillna("").replace("",default)
df["order_month"]=df.order_date.dt.to_period("M").astype(str)
df=df.sort_values(["order_date","order_id"]).reset_index(drop=True)
df.to_csv(OUT/"retail_orders_cleaned.csv",index=False,date_format="%Y-%m-%d")
quality.update({"cleaned_rows":int(len(df)),"rows_removed":int(n-len(df)),"rows_retained_pct":round(len(df)*100/n,2)})
(OUT/"data_quality_report.json").write_text(json.dumps(quality,indent=2))
summary={"cleaned_orders":int(len(df)),"total_units":int(df.quantity.sum()),"gross_sales_inr":round(float(df.gross_sales_inr.sum()),2),"net_sales_inr":round(float(df.net_sales_inr.sum()),2),"average_order_value_inr":round(float(df.net_sales_inr.mean()),2),"top_category_by_net_sales":str(df.groupby("product_category").net_sales_inr.sum().idxmax()),"top_city_by_net_sales":str(df.groupby("city").net_sales_inr.sum().idxmax())}
(OUT/"cleaning_summary.json").write_text(json.dumps(summary,indent=2))
df.groupby("product_category").agg(orders=("order_id","nunique"),units=("quantity","sum"),net_sales_inr=("net_sales_inr","sum")).sort_values("net_sales_inr",ascending=False).round(2).to_csv(OUT/"sales_by_category.csv")
df.groupby("city").agg(orders=("order_id","nunique"),net_sales_inr=("net_sales_inr","sum")).sort_values("net_sales_inr",ascending=False).round(2).to_csv(OUT/"sales_by_city.csv")
df.groupby("order_month").agg(orders=("order_id","nunique"),net_sales_inr=("net_sales_inr","sum")).round(2).to_csv(OUT/"monthly_sales.csv")
print(f"Cleaning complete: {n} input rows -> {len(df)} cleaned rows.")
