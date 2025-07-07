# Claude ve GPT geçmişinden vektör veri oluşturur
import os
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import Docx2txtLoader
from langchain.text_splitter import CharacterTextSplitter

# Load OpenAI API key from config or environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    from configparser import ConfigParser
    config = ConfigParser()
    config.read('config/settings.ini')
    OPENAI_API_KEY = config.get('OpenAI', 'api_key', fallback=None)

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set OPENAI_API_KEY in your environment or config/settings.ini.")

def build_memory(directory="memory/source_docs", index_path="memory/vector_store"):
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    all_text = ""

    for filename in os.listdir(directory):
        if filename.endswith(".docx"):
            doc = Docx2txtLoader(os.path.join(directory, filename)).load()
            for page in doc:
                all_text += page.page_content + "\n"

    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = splitter.split_text(all_text)
    faiss_index = FAISS.from_texts(texts, embeddings)
    faiss_index.save_local(index_path)

if __name__ == "__main__":
    build_memory()
    print("📚 Hafıza başarıyla oluşturuldu ve FAISS'e kaydedildi.")
