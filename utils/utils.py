from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import streamlit as st
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import ssl


# knowledge base path
kb_db_path = 'data/emb_db'


@st.cache_resource
# load the vectorized database
def load_db(db_path=kb_db_path, embedding_model='text-embedding-ada-002'):
    embeddings = OpenAIEmbeddings(model=embedding_model, chunk_size=1)
    db_loaded = FAISS.load_local(db_path, embeddings, 
                                 allow_dangerous_deserialization=True
                                 )
    print("Database loaded")
    return db_loaded

MONGODB_PASSWORD="9vYq3TWWsQn7bp2v"

uri = f"mongodb+srv://streamlit_app:{MONGODB_PASSWORD}@virtual-ta.q344d.mongodb.net/test?retryWrites=true&w=majority"

# MongoDB Atlas connection
@st.cache_resource
def query_db_connection():
    """Return a MongoDB connection to the user_queries_db database."""
    client = MongoClient(uri, server_api=ServerApi('1'),
                        ssl=True,
                        ssl_cert_reqs=ssl.CERT_NONE,
                        tlsAllowInvalidCertificates=True )
    print("Connected to MongoDB")
    return client['user_queries_db']


# function to store the query in the database
def process_and_store_query(collection, **kwargs):
    """Insert a query into the MongoDB collection."""
    # Create a document to insert
    document = {
        "timestamp": datetime.now()
    }
    # add any additional fields to the document
    document.update(kwargs)
    
    # Insert the document into the collection
    result = collection.insert_one(document)
    
    return result.inserted_id