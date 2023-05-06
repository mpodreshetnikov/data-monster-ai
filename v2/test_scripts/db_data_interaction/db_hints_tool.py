from langchain.agents.agent_toolkits.base import BaseToolkit

def get_db_hints_toolkit(doc_path: str, doc_store_name: str = "db_hints_store") -> BaseToolkit:
    from langchain.embeddings.openai import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import CharacterTextSplitter
    from langchain.document_loaders import TextLoader
    
    loader = TextLoader(doc_path)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(separator='\n', chunk_size=400, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()
    db_doc_store = Chroma.from_documents(
        texts, embeddings, collection_name=doc_store_name, persist_directory=doc_store_name)

    from langchain.agents.agent_toolkits import (
        VectorStoreToolkit,
        VectorStoreInfo,
    )
    vectorstore_info = VectorStoreInfo(
        name="database hints",
        description="hints how to query the question from the database. Always use it BEFORE asking a human. Use this tool in english only.",
        vectorstore=db_doc_store
    )
    toolkit = VectorStoreToolkit(vectorstore_info=vectorstore_info)
    
    return toolkit