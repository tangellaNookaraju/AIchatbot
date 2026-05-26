from typing import List, Dict, Any

class PromptBuilder:
    @staticmethod
    def build_system_instruction() -> str:
        """
        Returns the system instruction that instructs the LLM to behave like
        a professional grounded assistant and only answer based on the context.
        """
        return (
            "You are a helpful and professional customer support AI assistant.\n"
            "Your task is to answer the user's question using ONLY the provided context below.\n"
            "If the provided context does not contain enough information to answer the question, "
            "you must state exactly: 'I could not find enough information in the knowledge base.'\n"
            "Do NOT make up facts, rely on external information, or hallucinate.\n"
            "Keep your responses concise, clear, and grounded in the source context."
        )

    @staticmethod
    def build_prompt_content(context_chunks: List[Dict[str, Any]], history: List[Dict[str, str]], question: str) -> str:
        """
        Formats the context, chat history, and current question into a single prompt string.
        """
        # Format the retrieved context
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            title = chunk["metadata"].get("title", "Document Chunk")
            text = chunk["text"]
            context_parts.append(f"[{i+1}] Document: {title}\nContent: {text}")
        
        context_str = "\n\n".join(context_parts) if context_parts else "No context available."

        # Format conversation history
        history_parts = []
        # Exclude the very last user message from history if it is already added,
        # but history_service typically gets queried BEFORE adding the new message,
        # or we just build history from what history_service returned.
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_parts.append(f"{role}: {msg['content']}")
        
        history_str = "\n".join(history_parts) if history_parts else "(No prior history)"

        # Combine into the prompt template
        prompt = (
            f"SYSTEM INSTRUCTIONS:\n"
            f"{PromptBuilder.build_system_instruction()}\n\n"
            f"=== CONTEXT ===\n"
            f"{context_str}\n\n"
            f"=== CONVERSATION HISTORY ===\n"
            f"{history_str}\n\n"
            f"=== NEW USER QUESTION ===\n"
            f"User: {question}\n\n"
            f"Based on the CONTEXT, generate a grounded answer to the NEW USER QUESTION. Remember, if the answer is not in the context, reply: 'I could not find enough information in the knowledge base.'"
        )
        return prompt
