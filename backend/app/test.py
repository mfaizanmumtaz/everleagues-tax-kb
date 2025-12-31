from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(api_key="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",model="text-embedding-3-small")

print(embeddings.embed_query("hi"))