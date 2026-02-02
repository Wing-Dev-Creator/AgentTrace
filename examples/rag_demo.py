import agenttrace
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FakeEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document

agenttrace.instrument()

def main():
    # 1. Setup minimal RAG
    embeddings = FakeEmbeddings(size=10)
    db = FAISS.from_documents([
        Document(page_content="Paris is the capital of France", metadata={"source": "geo"}),
        Document(page_content="Tokyo is the capital of Japan", metadata={"source": "geo"}),
    ], embeddings)
    
    retriever = db.as_retriever(search_kwargs={"k": 1})

    print("Starting RAG trace...")
    with agenttrace.trace("rag_demo") as t:
        # 2. Run Retrieval (Auto-captured)
        print("Running Retriever...")
        docs = retriever.invoke("France")
        print(f"Retrieved: {len(docs)} docs")
        
        # 3. Manual Retrieval (Testing manual API)
        t.retrieval(
            query="Manual Search", 
            documents=[{"content": "Manual Doc", "metadata": {"id": 1}}]
        )

if __name__ == "__main__":
    main()
