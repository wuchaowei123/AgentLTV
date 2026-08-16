import pandas as pd
import numpy as np
from datetime import timedelta
from collections import defaultdict

# ---------- 配置 ----------
CHUNK_SIZE = 200000  # 根据内存可调（你机器 32GB 可尝试 200k 或更多）
CSV_PATH = '/home/jupyter/Luigi工作空间/LLM+决策树工作/ZILN公开数据集处理/transactions.csv'
OUTPUT_DIR = '/home/jupyter/Luigi工作空间/LLM+决策树工作/ZILN公开数据集处理/'

# 只读取我们用到的列（显著减少内存）
usecols = [
    'id', 'date', 'company', 'chain', 'dept', 'category',
    'brand', 'productsize', 'productmeasure', 'purchasequantity', 'purchaseamount'
]

# 为常见列指定较小的 dtype（根据你的 CSV 实际数值/范围调整）
dtypes = {
    'id': np.int64,
    'company': np.int64,
    'chain': 'category',
    'dept': 'category',
    'category': 'category',
    'brand': 'category',
    'productsize': 'category',
    'productmeasure': 'category',
    'purchasequantity': np.float32,
    'purchaseamount': np.float32
}

# 目标公司集合（与你原来一致）
target_companies = set([
    10000, 101200010, 101410010, 101600010, 102100020,
    102700020, 102840020, 103000030, 103338333, 103400030,
    103600030, 103700030, 103800030, 104300040, 104400040,
    104470040, 104900040, 105100050, 105150050, 107800070
])

print("=" * 60)
print("第一遍扫描：按 chunk 计算每个用户的首次购买日期（增量合并）")
print("=" * 60)

# 用 pandas Series 存储 user -> first_date（比 dict 更高效做向量化 map）
user_first_series = pd.Series(dtype='datetime64[ns]')

reader = pd.read_csv(
    CSV_PATH,
    usecols=usecols,
    dtype={k: v for k, v in dtypes.items() if k in usecols},
    parse_dates=['date'],
    chunksize=CHUNK_SIZE
)

chunk_count = 0
for chunk in reader:
    chunk_count += 1
    print(f"处理第 {chunk_count} 批, 大小 {len(chunk)}")
    # 每个 chunk 得到该 chunk 内每个 id 的最小日期
    chunk_first = chunk.groupby('id', observed=True)['date'].min()
    # 合并：已有 user_first_series 与 chunk_first 取全局最小
    if user_first_series.empty:
        user_first_series = chunk_first
    else:
        # concat 后按 index 取最小
        combined = pd.concat([user_first_series, chunk_first], axis=0)
        user_first_series = combined.groupby(level=0).min()

print(f"\n总共找到 {len(user_first_series)} 个唯一用户")

# 过滤首次购买日期在区间内的用户（向量化）
start_date = pd.to_datetime('2012-03-01')
end_date = pd.to_datetime('2012-07-01')
mask = (user_first_series >= start_date) & (user_first_series <= end_date)
filtered_user_ids = set(user_first_series[mask].index.tolist())
print(f"首次购买日期在 2012-03-01 到 2012-07-01 的用户数: {len(filtered_user_ids)}")

# ---------- 第二遍：增量聚合（不保留所有交易，只保留需要的汇总） ----------
print("\n" + "=" * 60)
print("第二遍扫描：为筛选用户统计首次购买明细与一年内累计 LTV（内存友好）")
print("=" * 60)

# 存放首次购买的汇总信息（只保存首次购买那天的记录的聚合）
first_purchase_agg = {}  # id -> dict( first_amount_sum, quantity, lists of attributes )
ltv_sums = defaultdict(float)  # id -> sum of purchaseamount in 1 year after first_date

# 重新创建 reader（CSV 游标已到末尾）
reader = pd.read_csv(
    CSV_PATH,
    usecols=usecols,
    dtype={k: v for k, v in dtypes.items() if k in usecols},
    parse_dates=['date'],
    chunksize=CHUNK_SIZE
)

chunk_count = 0
for chunk in reader:
    chunk_count += 1
    if chunk_count % 50 == 0:
        print(f"处理第 {chunk_count} 批...")
    # 只保留关注的用户（向量化）
    chunk = chunk[chunk['id'].isin(filtered_user_ids)]
    if chunk.empty:
        continue

    # 将该行对应的用户首次购买日期映射过来（向量化）
    chunk['first_date'] = chunk['id'].map(user_first_series)

    # 计算 mask：是否为首次购买当天；是否为一年内的后续购买
    mask_first = chunk['date'] == chunk['first_date']
    # 计算一年后的截止日期：先把 first_date 转为 datetime，然后 +365
    chunk['one_year_later'] = chunk['first_date'] + pd.Timedelta(days=365)
    mask_future = (chunk['date'] > chunk['first_date']) & (chunk['date'] <= chunk['one_year_later'])

    # 处理首次购买当天的行 —— 需要聚合多个字段并检查是否包含目标公司
    first_rows = chunk[mask_first]
    if not first_rows.empty:
        # 按用户分组逐组更新（通常每个用户当天的记录并不多）
        for uid, grp in first_rows.groupby('id', observed=True):
            # lazy init
            agg = first_purchase_agg.get(uid)
            if agg is None:
                agg = {
                    'first_amount_sum': 0.0,
                    'quantity': 0,
                    'chains': [],
                    'depts': [],
                    'categorys': [],
                    'companies': [],
                    'brands': [],
                    'productsizes': [],
                    'productmeasures': [],
                    'purchasequantitys': [],
                    'purchaseamounts': []
                }
            # 更新数值型聚合
            agg['first_amount_sum'] += grp['purchaseamount'].sum()
            agg['quantity'] += len(grp)
            # 扩展属性列表（保持原始顺序）
            agg['chains'].extend(grp['chain'].astype(str).tolist())
            agg['depts'].extend(grp['dept'].astype(str).tolist())
            agg['categorys'].extend(grp['category'].astype(str).tolist())
            agg['companies'].extend(grp['company'].astype(str).tolist())
            agg['brands'].extend(grp['brand'].astype(str).tolist())
            agg['productsizes'].extend(grp['productsize'].astype(str).tolist())
            agg['productmeasures'].extend(grp['productmeasure'].astype(str).tolist())
            agg['purchasequantitys'].extend(grp['purchasequantity'].astype(float).tolist())
            agg['purchaseamounts'].extend(grp['purchaseamount'].astype(float).tolist())

            first_purchase_agg[uid] = agg

    # 处理一年内的后续消费，累加 LTV
    future_rows = chunk[mask_future]
    if not future_rows.empty:
        # 按用户分组求和（向量化后逐用户累加）
        sums = future_rows.groupby('id', observed=True)['purchaseamount'].sum()
        for uid, s in sums.items():
            ltv_sums[uid] += float(s)

print(f"\n收集到 {len(first_purchase_agg)} 个有首次购买记录的用户（在筛选集合中）")

# ---------- 第三步：基于聚合结果筛选包含 target_companies 的用户并构造最终结果 ----------
print("\n" + "=" * 60)
print("第三步：筛选包含目标公司的用户并构造最终结果")
print("=" * 60)

result_data = []
processed = 0
for uid in filtered_user_ids:
    processed += 1
    if processed % 1000 == 0:
        print(f"处理进度: {processed}/{len(filtered_user_ids)}")

    if uid not in first_purchase_agg:
        continue
    agg = first_purchase_agg[uid]
    # 检查首次购买是否包含目标公司（companies 列）
    # 注意：在 first_purchase_agg 中 company 已作为字符串，需转换回 int 比较（或字符串比较）
    try:
        companies_int = set(int(x) for x in agg['companies'] if x not in ('nan', 'None', ''))
    except:
        companies_int = set()
    if not companies_int.intersection(target_companies):
        continue

    first_date = user_first_series.loc[uid]

    result_data.append({
        'id': uid,
        'First purchase date': first_date.strftime('%Y-%m-%d'),
        'First purchase amount': agg['first_amount_sum'],
        'Quantity of goods purchased': agg['quantity'],
        'chains': agg['chains'],
        'depts': agg['depts'],
        'categorys': agg['categorys'],
        'companies': agg['companies'],
        'brands': agg['brands'],
        'productsizes': agg['productsizes'],
        'productmeasures': agg['productmeasures'],
        'purchasequantitys': agg['purchasequantitys'],
        'purchaseamounts': agg['purchaseamounts'],
        'LTV label': ltv_sums.get(uid, 0.0)
    })

print(f"\n筛选后的用户数（包含指定公司）: {len(result_data)}")

# 释放大对象
del first_purchase_agg
del ltv_sums
del user_first_series

# ---------- 第四步：划分并保存 ----------
print("\n" + "=" * 60)
print("第四步：划分训练集/测试集并保存")
print("=" * 60)

result_df = pd.DataFrame(result_data)
# 打乱并划分
result_df = result_df.sample(frac=1, random_state=42).reset_index(drop=True)
train_size = int(len(result_df) * 0.8)
train_df = result_df.iloc[:train_size]
test_df = result_df.iloc[train_size:]

train_path = OUTPUT_DIR + 'ZILNtrain.csv'
test_path = OUTPUT_DIR + 'ZILNtest.csv'

print(f"保存训练集到: {train_path}")
train_df.to_csv(train_path, index=False)
print(f"保存测试集到: {test_path}")
test_df.to_csv(test_path, index=False)

print("处理完成！")
print("\n训练集前几行:")
print(train_df.head())
print("\n测试集前几行:")
print(test_df.head())
