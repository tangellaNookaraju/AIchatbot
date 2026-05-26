import os
import json
import logging
from typing import List, Dict, Any, Optional
import chromadb
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("app.vectorstore.vector_store")

class VectorStoreManager:
    _client = None
    _collection = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
            logger.info(f"Initializing ChromaDB client in: {persist_dir}")
            cls._client = chromadb.PersistentClient(path=persist_dir)
        return cls._client

    @classmethod
    def get_collection(cls):
        if cls._collection is None:
            client = cls.get_client()
            # Use cosine similarity for similarity metric
            cls._collection = client.get_or_create_collection(
                name="knowledge_base",
                metadata={"hnsw:space": "cosine"}
            )
        return cls._collection

    @classmethod
    def chunk_text(cls, text: str, max_words: int = 100, overlap: int = 20) -> List[str]:
        """
        Split text into overlapping chunks of words.
        """
        words = text.split()
        if len(words) <= max_words:
            return [text]
        
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i : i + max_words]
            chunks.append(" ".join(chunk_words))
            # Move index forward by max_words - overlap
            i += (max_words - overlap)
            # If the next start index leaves a tiny chunk, adjust or stop
            if i >= len(words) or (len(words) - i) < overlap:
                break
        return chunks

    @classmethod
    def initialize_database(cls, docs_path: str = "docs.json") -> bool:
        """
        Load documents from docs.json, chunk them, embed them, and save to Chroma.
        Only runs if the database collection is currently empty.
        """
        try:
            collection = cls.get_collection()
            count = collection.count()
            
            if count > 0:
                logger.info(f"Database already populated with {count} chunks. Skipping initialization.")
                return False

            if not os.path.exists(docs_path):
                logger.warning(f"Documents file not found at {docs_path}. No documents indexed.")
                return False

            logger.info(f"Reading documents from {docs_path}...")
            with open(docs_path, "r", encoding="utf-8") as f:
                documents = json.load(f)

            all_ids = []
            all_embeddings = []
            all_documents = []
            all_metadatas = []
            
            chunk_index = 0
            for doc_idx, doc in enumerate(documents):
                title = doc.get("title", f"Doc {doc_idx}")
                content = doc.get("content", "")
                
                if not content.strip():
                    continue

                # Chunk the document content
                chunks = cls.chunk_text(content)
                logger.info(f"Document '{title}' split into {len(chunks)} chunk(s).")

                for c_idx, chunk in enumerate(chunks):
                    chunk_id = f"doc_{doc_idx}_chunk_{c_idx}"
                    
                    # Generate embedding for this chunk
                    embedding = EmbeddingService.get_embedding(chunk)
                    
                    all_ids.append(chunk_id)
                    all_embeddings.append(embedding)
                    all_documents.append(chunk)
                    all_metadatas.append({
                        "chunk_id": chunk_index,
                        "title": title,
                        "source": docs_path,
                        "doc_index": doc_idx,
                        "chunk_index": c_idx
                    })
                    chunk_index += 1

            if all_ids:
                logger.info(f"Adding {len(all_ids)} chunks to ChromaDB...")
                collection.add(
                    ids=all_ids,
                    embeddings=all_embeddings,
                    documents=all_documents,
                    metadatas=all_metadatas
                )
                logger.info("ChromaDB initialization completed successfully.")
                return True
            else:
                logger.warning("No valid chunks were found to add to ChromaDB.")
                return False

        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise e

    @classmethod
    def similarity_search(cls, query: str, top_k: int = 3, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for top_k similar document chunks.
        Applies similarity threshold check (similarity_score = 1.0 - cosine_distance).
        """
        try:
            if threshold is None:
                try:
                    threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))
                except ValueError:
                    threshold = 0.35

            collection = cls.get_collection()
            
            # Embed the user query
            query_embedding = EmbeddingService.get_embedding(query)
            
            # Search ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            # Parse results
            retrieved_chunks = []
            if not results or not results.get("ids") or len(results["ids"][0]) == 0:
                return retrieved_chunks

            # results returns nested lists because it supports batch queries
            ids = results["ids"][0]
            distances = results["distances"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]

            for idx in range(len(ids)):
                distance = distances[idx]
                # Chroma's cosine space returns distance: 0.0 means identical, 1.0 means orthogonal.
                # similarity_score = 1.0 - distance
                similarity = 1.0 - distance
                
                # Check threshold
                if similarity >= threshold:
                    retrieved_chunks.append({
                        "id": ids[idx],
                        "text": documents[idx],
                        "metadata": metadatas[idx],
                        "similarity": similarity,
                        "distance": distance
                    })
                    logger.debug(f"Retrieved chunk {ids[idx]} with similarity {similarity:.4f} (passed threshold {threshold})")
                else:
                    logger.debug(f"Rejected chunk {ids[idx]} with similarity {similarity:.4f} (failed threshold {threshold})")

            return retrieved_chunks
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            raise e
