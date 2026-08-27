import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('rag_server/.env')
from supabase import create_client

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

res = supabase.table('uploaded_files').select('id, file_name').execute()
files = res.data

for f in files:
    count_res = supabase.table('documents').select('id', count='exact').eq('file_id', f['id']).execute()
    print(f"{f['file_name']} (ID: {f['id']}) - Chunks: {count_res.count}")
