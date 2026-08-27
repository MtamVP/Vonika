import os, sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('rag_server/.env')
from supabase import create_client

import sys
sys.path.append(os.path.join(os.getcwd(), 'rag_server'))
from parser import extract_text, chunk_text

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

res = supabase.table('uploaded_files').select('*').eq('id', 278).execute()
if res.data:
    file_url = res.data[0]['file_url']
    file_name = res.data[0]['file_name']
    
    print(f'Downloading {file_url}...')
    temp_path = os.path.join('rag_server', file_name)
    urllib.request.urlretrieve(file_url, temp_path)
    
    print(f'Processing {file_name} into chunks...')
    try:
        with open(temp_path, 'rb') as f:
            file_bytes = f.read()
        text = extract_text(file_bytes, file_name)
        chunks = chunk_text(text)
        print(f'Extracted {len(chunks)} chunks.')
        
        if len(chunks) > 0:
            print('Inserting chunks to Supabase...')
            for i, chunk in enumerate(chunks):
                supabase.table('documents').insert({
                    'file_id': 278,
                    'chunk_index': i,
                    'content': chunk
                }).execute()
            print('DONE! Chunks inserted successfully.')
        else:
            print('Failed to extract chunks.')
            
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
else:
    print('File ID 278 not found in DB.')
