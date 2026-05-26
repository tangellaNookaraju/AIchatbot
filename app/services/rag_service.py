import os
import logging
from typing import Dict, Any, List
from app.vectorstore.vector_store import VectorStoreManager
from app.services.history_service import HistoryService
from app.prompts.prompt_builder import PromptBuilder

logger = logging.getLogger("app.services.rag_service")

class RAGService:
    @classmethod
    def query(cls, session_id: str, message: str) -> Dict[str, Any]:
        """
        Executes the query flow:
        - Retrieves top 3 chunks matching the message from the vector DB.
        - Verifies if they meet the similarity threshold.
        - If no chunks pass the threshold, returns grounded 'I could not find enough information'.
        - Otherwise, builds a prompt with the context and history.
        - Sends the prompt to the Gemini API with temperature 0.2.
        - Updates history and returns response with usage metadata.
        """
        logger.info(f"Processing query for session {session_id}: '{message}'")
        
        # 1. Retrieve matching chunks from vector database
        retrieved_chunks = VectorStoreManager.similarity_search(message, top_k=3)
        
        # 2. Check if similarity threshold is met (if list is empty, threshold rejected all)
        if not retrieved_chunks:
            logger.info("No documents matched the similarity threshold. Halting generation to prevent hallucinations.")
            reply = "I could not find enough information in the knowledge base."
            
            # Even for threshold rejections, keep track of dialogue turns
            HistoryService.add_message(session_id, "user", message)
            HistoryService.add_message(session_id, "assistant", reply)
            
            return {
                "reply": reply,
                "tokensUsed": 0,
                "retrievedChunks": 0,
                "sources": [],
                "mocked": False
            }

        # 3. Retrieve short-term chat history for prompt construction (before appending the current user message)
        history = HistoryService.get_history(session_id)
        
        # Add current user message to session history
        HistoryService.add_message(session_id, "user", message)

        # 4. Formulate context sources array
        sources = [
            {
                "title": chunk["metadata"].get("title", "Unknown"),
                "text": chunk["text"],
                "similarity": float(chunk["similarity"])
            }
            for chunk in retrieved_chunks
        ]

        # 5. Build final prompt
        prompt = PromptBuilder.build_prompt_content(
            context_chunks=retrieved_chunks,
            history=history,
            question=message
        )

        # 6. Execute LLM Call (Gemini API or Mock fallback)
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        
        if not api_key:
            logger.warning("GEMINI_API_KEY is not defined in the environment. Running in Demo Mock Mode.")
            
            # Demo Mode: use the best retrieved chunk to formulate a response
            best_chunk = retrieved_chunks[0]
            reply = (
                f"**[DEMO MODE - GEMINI_API_KEY NOT CONFIGURED]**\n\n"
                f"**Context Title:** {best_chunk['metadata'].get('title')}\n"
                f"**Retrieved Content:** {best_chunk['text']}\n\n"
                f"*Note: To enable full AI reasoning, please configure your `GEMINI_API_KEY` in the `.env` file.*"
            )
            estimated_tokens = len(prompt + reply) // 4
            
            # Save response to history
            HistoryService.add_message(session_id, "assistant", reply)
            
            return {
                "reply": reply,
                "tokensUsed": estimated_tokens,
                "retrievedChunks": len(retrieved_chunks),
                "sources": sources,
                "mocked": True
            }

        try:
            # Dynamically import google-generativeai package
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Use gemini-1.5-flash with custom system instructions
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=PromptBuilder.build_system_instruction()
            )
            
            logger.info("Calling Gemini API...")
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2
                )
            )
            
            reply = response.text
            
            # Extract total token count from API response
            tokens_used = 0
            if response.usage_metadata:
                tokens_used = response.usage_metadata.total_token_count
            else:
                tokens_used = len(prompt + reply) // 4
                
            # Save response to history
            HistoryService.add_message(session_id, "assistant", reply)
            
            return {
                "reply": reply,
                "tokensUsed": tokens_used,
                "retrievedChunks": len(retrieved_chunks),
                "sources": sources,
                "mocked": False
            }

        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            # Create a user-friendly error response
            err_reply = (
                f"I encountered an error querying the Gemini API: {str(e)}.\n"
                f"Please verify your `GEMINI_API_KEY` and connection settings."
            )
            
            # Save the error warning in history
            HistoryService.add_message(session_id, "assistant", err_reply)
            
            return {
                "reply": err_reply,
                "tokensUsed": 0,
                "retrievedChunks": len(retrieved_chunks),
                "sources": sources,
                "mocked": False,
                "error": str(e)
            }
