from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
# from langchain import OpenAI, SQLDatabase, SQLDatabaseChain

load_dotenv()

# Access environment variables
api_key = os.getenv('OPENAI_API_KEY')
pc_api_key = os.getenv('PINECONE_API_KEY')


print(f"API Key: {api_key}")
print(f"Pinecone Password: {pc_api_key}")



pc = Pinecone(api_key=pc_api_key)

index_name = "rag-fusion"



# if not pc.has_index(index_name):
#     pc.create_index_for_model(
#         name=index_name,
#         cloud="aws",
#         region="us-east-1",
#         embed={
#             "model": OpenAIEmbeddings().model,  # Uses the default OpenAI embedding model
#             "field_map": {"text": "chunk_text"}
#         }
#     )
    # "error":{"code":"INVALID_ARGUMENT","message":"Model text-embedding-ada-002 not found. 
    # Supported models: 'llama-text-embed-v2', 'multilingual-e5-large', 'pinecone-sparse-english-v0'"},"status":400}


if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model":"llama-text-embed-v2",
            "field_map":{"text": "chunk_text"}
        }
    )


