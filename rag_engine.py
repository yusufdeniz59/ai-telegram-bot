import os
from configparser import ConfigParser
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Load OpenAI API key from config or environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    config = ConfigParser()
    config.read('config/settings.ini')
    OPENAI_API_KEY = config.get('OpenAI', 'api_key', fallback=None)

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your environment or config/settings.ini.")

def retrieve_memory(query, index_path="memory/vector_store"):
    """
    Kullanıcı mesajı ile en çok ilişkili 3 metin parçasını FAISS içinden getirir.
    """
    db = FAISS.load_local(
        index_path,
        OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        allow_dangerous_deserialization=True
    )
    docs = db.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in docs])
