
## Activate your environment
In your terminal, activate your environment with one of the following commands, depending on your operating system.
```
# Windows command prompt
.venv\Scripts\activate.bat

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS and Linux
source .venv/bin/activate
```
Once activated, you will see your environment name in parentheses before your prompt. "(.venv)"


## Deactivate venv
When you're done using this environment, return to your normal shell by typing:
```
deactivate
```


# Pinecone
Pinecone click here [get-started](https://app.pinecone.io/organizations/-OTS4wLTKMvfhBhyA7SD/projects/c4ecfed8-ce2b-4c3f-aea2-e9cdfb2060e7/get-started/database)
```
pcsk_256kWr_K67xqiAPgtwj9esABQ4HJ6pvnbBjmnH3dTdtuyQLDm5wsaPV8Tq5iYfqpRY22XP
```
## Install Pinecone
Ready to get started with Pinecone? First, install the Python SDK:
```
pip install pinecone
```

## Initialize
Next, use your API key to initialize your client:
```
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="********-****-****-****-************")
```

## Create index
Then [create an index](https://docs.pinecone.io/guides/index-data/create-an-index) that is integrated with an embedding model hosted by Pinecone. With integrated models, you upsert and search with text and have Pinecone generate vectors automatically.

```
index_name = "developer-quickstart-py"

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
```

Now you’re ready to upsert records and start searching. Head to our documentation for detailed information and examples: