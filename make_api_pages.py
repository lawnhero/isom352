"""Dirt script for the s16 mock broker API.
Reads the clean master (eastville_teaching.csv), removes the 3 duplicate rows,
sorts by house number, and writes 7 JSON pages of 16 listings (page 7 holds 12).
Each page carries the envelope: page, page_size, total_pages, total, listings."""
import json, math
import pandas as pd

PAGE_SIZE = 16
df = pd.read_csv('eastville_teaching.csv')
df['price'] = df['price'].str.replace('$', '', regex=False).str.replace(',', '', regex=False).astype(int)
df = df.drop_duplicates().sort_values('house')
pages = math.ceil(len(df) / PAGE_SIZE)
for p in range(1, pages + 1):
    chunk = df.iloc[(p - 1) * PAGE_SIZE : p * PAGE_SIZE]
    body = {"page": p, "page_size": PAGE_SIZE, "total_pages": pages, "total": len(df),
            "listings": json.loads(chunk.to_json(orient='records'))}
    with open(f'api/eastville/page{p}.json', 'w') as f:
        json.dump(body, f, indent=1)
print(pages, "pages,", len(df), "listings")
