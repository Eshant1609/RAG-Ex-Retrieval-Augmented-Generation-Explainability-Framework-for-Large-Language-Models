import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional

import requests

from utils.config import Config

logger = logging.getLogger(__name__)


class RAGService:
    """Retrieval-Augmented Generation service combining semantic search with LLM"""

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.ollama_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL

    def query(self, query: str, top_k: int = 5) -> Dict:
        """
        Answer a query using RAG.

        Args:
            query: User query
            top_k: Number of relevant chunks to retrieve

        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            search_results = self.vector_store.search(query, top_k=top_k)

            if not search_results:
                return {
                    "answer": "I couldn't find any relevant information in the uploaded documents. Please upload some research papers first.",
                    "sources": [],
                    "metadata": {},
                }

            ranked_results = self._rank_search_results(query, search_results)
            context_results = ranked_results[: max(top_k * 2, 4)]
            context = self._build_context(context_results)
            prompt = self._build_query_prompt(query, context)
            answer = self._call_ollama(prompt)
            sources = self._format_sources(context_results)
            explainability = self._build_explainability(answer, context_results)

            return {
                "answer": answer,
                "sources": sources,
                "metadata": {
                    "retrieved_chunks": len(context_results),
                    "model": self.model,
                    "confidence_score": explainability["confidence_score"],
                    "explainability": explainability,
                },
            }

        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "metadata": {},
            }

    def summarize(self, query: Optional[str] = None, summary_type: str = "general", top_k: int = 10) -> Dict:
        """
        Generate contextual summary.

        Args:
            query: Optional query to focus the summary
            summary_type: Type of summary (general, detailed, key_points)
            top_k: Number of chunks to retrieve

        Returns:
            Dictionary with summary, sources, and metadata
        """
        try:
            if query:
                search_results = self.vector_store.search(query, top_k=top_k)
                search_results = self._rank_search_results(query, search_results)
            else:
                documents = self.vector_store.list_documents()
                search_results = []
                for doc in documents[:5]:
                    chunks = self.vector_store.get_document_chunks(doc["document_id"])
                    for chunk in chunks[:2]:
                        search_results.append({
                            "text": chunk["text"],
                            "metadata": chunk["metadata"],
                            "relevance_score": 0.5,
                        })

            if not search_results:
                return {
                    "summary": "No documents available for summarization. Please upload some research papers first.",
                    "sources": [],
                    "metadata": {},
                }

            context = self._build_context(search_results)
            prompt = self._build_summary_prompt(context, summary_type, query)
            summary = self._call_ollama(prompt)
            sources = self._format_sources(search_results)
            explainability = self._build_explainability(summary, search_results)

            return {
                "summary": summary,
                "sources": sources,
                "metadata": {
                    "type": summary_type,
                    "retrieved_chunks": len(search_results),
                    "model": self.model,
                    "confidence_score": explainability["confidence_score"],
                    "explainability": explainability,
                },
            }

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                "summary": f"Error generating summary: {str(e)}",
                "sources": [],
                "metadata": {},
            }

    def summarize_by_ids(self, document_ids: List[str], summary_type: str = "general") -> Dict:
        """Generate summary for specific documents."""
        try:
            search_results = []
            for doc_id in document_ids:
                chunks = self.vector_store.get_document_chunks(doc_id)
                for chunk in chunks:
                    search_results.append({
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                        "relevance_score": 0.5,
                    })

            if not search_results:
                return {
                    "summary": "No content found in the specified documents.",
                    "sources": [],
                    "metadata": {},
                }

            context = self._build_context(search_results)
            prompt = self._build_summary_prompt(context, summary_type)
            summary = self._call_ollama(prompt)
            sources = self._format_sources(search_results)
            explainability = self._build_explainability(summary, search_results)

            return {
                "summary": summary,
                "sources": sources,
                "metadata": {
                    "type": summary_type,
                    "document_ids": document_ids,
                    "retrieved_chunks": len(search_results),
                    "model": self.model,
                    "confidence_score": explainability["confidence_score"],
                    "explainability": explainability,
                },
            }

        except Exception as e:
            logger.error(f"Error generating summary by IDs: {str(e)}")
            return {
                "summary": f"Error generating summary: {str(e)}",
                "sources": [],
                "metadata": {},
            }

    def query_with_documents(self, query: str, document_ids: List[str], top_k: int = 5) -> Dict:
        """Answer a query using specific documents."""
        try:
            search_results = []
            for doc_id in document_ids:
                chunks = self.vector_store.get_document_chunks(doc_id)
                for chunk in chunks:
                    search_results.append({
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                    })

            if not search_results:
                return {
                    "answer": "No documents found with the specified IDs.",
                    "sources": [],
                    "metadata": {},
                }

            ranked_results = self._rank_search_results(query, search_results)
            context_results = ranked_results[: max(top_k * 2, 4)]
            context = self._build_context(context_results)
            prompt = self._build_query_prompt(query, context)
            answer = self._call_ollama(prompt)
            sources = self._format_sources(context_results)
            explainability = self._build_explainability(answer, context_results)

            return {
                "answer": answer,
                "sources": sources,
                "metadata": {
                    "retrieved_chunks": len(context_results),
                    "candidate_chunks": len(search_results),
                    "document_ids": document_ids,
                    "model": self.model,
                    "confidence_score": explainability["confidence_score"],
                    "explainability": explainability,
                },
            }

        except Exception as e:
            logger.error(f"Error in RAG query with documents: {str(e)}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "metadata": {},
            }

    def summarize_with_documents(self, query: str, document_ids: List[str], summary_type: str = "general") -> Dict:
        """Generate summary for specific documents with query focus."""
        try:
            search_results = []
            for doc_id in document_ids:
                chunks = self.vector_store.get_document_chunks(doc_id)
                for chunk in chunks:
                    search_results.append({
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                    })

            if not search_results:
                return {
                    "summary": "No content found in the specified documents.",
                    "sources": [],
                    "metadata": {},
                }

            ranked_results = self._rank_search_results(query, search_results)
            context = self._build_context(ranked_results)
            prompt = self._build_summary_prompt(context, summary_type, query)
            summary = self._call_ollama(prompt)
            sources = self._format_sources(ranked_results)
            explainability = self._build_explainability(summary, ranked_results)

            return {
                "summary": summary,
                "sources": sources,
                "metadata": {
                    "type": summary_type,
                    "document_ids": document_ids,
                    "retrieved_chunks": len(ranked_results),
                    "model": self.model,
                    "confidence_score": explainability["confidence_score"],
                    "explainability": explainability,
                },
            }

        except Exception as e:
            logger.error(f"Error generating summary with documents: {str(e)}")
            return {
                "summary": f"Error generating summary: {str(e)}",
                "sources": [],
                "metadata": {},
            }

    def _build_context(self, search_results: List[Dict]) -> str:
        """Build context string from search results."""
        context_parts = []
        for result in search_results:
            text = result.get("text", "")
            metadata = result.get("metadata", {})
            title = metadata.get("title", "Unknown")
            filename = metadata.get("filename", "Unknown")
            chunk_index = metadata.get("chunk_index")
            chunk_label = chunk_index + 1 if isinstance(chunk_index, int) else "N/A"
            score = float(result.get("relevance_score", 0.0))

            context_parts.append(
                f"[Source: {filename} | Title: {title} | Chunk: {chunk_label} | Relevance: {score:.3f}]\n{text}\n"
            )

        return "\n---\n".join(context_parts)

    def _build_query_prompt(self, query: str, context: str) -> str:
        """Build prompt for query answering."""
        prompt = f"""You are a RAG explainability assistant.
Use ONLY the provided context to answer the question.

Context:
{context}

User Question: {query}

Instructions:
- Answer only from the provided context.
- If context is insufficient, explicitly say what is missing.
- Cite sources using filenames from the context (for example: [resumeRaashish.pdf]).
- Do NOT invent source labels such as \"Document 1\", \"Document 2\", etc.
- Keep the answer concise, factual, and grounded.

Grounded Answer:"""
        return prompt

    def _build_summary_prompt(self, context: str, summary_type: str, query: Optional[str] = None) -> str:
        """Build prompt for summarization."""
        if summary_type == "key_points":
            instruction = "Extract and list the key points, findings, and conclusions from the following research documents. Format as a bulleted list."
        elif summary_type == "detailed":
            instruction = "Provide a detailed summary of the following research documents, including methodology, key findings, and conclusions."
        else:
            instruction = "Provide a concise but comprehensive summary of the following research documents, highlighting the main contributions and findings."

        if query:
            instruction += f"\n\nFocus the summary on: {query}"

        prompt = f"""You are a research assistant. {instruction}

Research Documents:
{context}

Summary:"""
        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for LLM inference."""
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            }

            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response generated")

        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Make sure Ollama is running.")
            return "Error: Cannot connect to Ollama. Please ensure Ollama is running and the model is installed."
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return "Error: Request timed out after 5 minutes. The model may be too slow or the prompt too long. Try reducing the number of documents or simplifying your query."
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """Format sources for display."""
        source_map = {}

        for result in search_results:
            metadata = result.get("metadata", {})
            doc_id = metadata.get("document_id")
            if not doc_id:
                continue

            title = metadata.get("title", "Unknown")
            filename = metadata.get("filename", "Unknown")
            score = float(result.get("relevance_score", 0.0))
            chunk_index = metadata.get("chunk_index")
            chunk_preview = result.get("text", "").replace("\n", " ").strip()[:220]

            if doc_id not in source_map:
                source_map[doc_id] = {
                    "document_id": doc_id,
                    "title": title,
                    "filename": filename,
                    "max_relevance_score": score,
                    "relevance_score": score,
                    "chunk_count": 0,
                    "top_chunks": [],
                }

            source_map[doc_id]["chunk_count"] += 1
            source_map[doc_id]["max_relevance_score"] = max(source_map[doc_id]["max_relevance_score"], score)
            source_map[doc_id]["relevance_score"] = source_map[doc_id]["max_relevance_score"]

            source_map[doc_id]["top_chunks"].append({
                "chunk_index": chunk_index,
                "relevance_score": round(score, 4),
                "preview": chunk_preview,
            })
            source_map[doc_id]["top_chunks"] = sorted(
                source_map[doc_id]["top_chunks"],
                key=lambda chunk: chunk["relevance_score"],
                reverse=True,
            )[:3]

        return sorted(source_map.values(), key=lambda source: source["max_relevance_score"], reverse=True)

    def _rank_search_results(self, query: str, search_results: List[Dict]) -> List[Dict]:
        """Rank chunks by relevance score for deterministic explainability output."""
        if not search_results:
            return []

        all_have_scores = all(result.get("relevance_score") is not None for result in search_results)
        ranked_results = []

        if all_have_scores:
            for result in search_results:
                score = self._normalize_score(result.get("relevance_score", 0.0))
                enriched_result = dict(result)
                enriched_result["relevance_score"] = score
                ranked_results.append(enriched_result)
        else:
            query_embedding = self.vector_store.embedding_model.encode([query], show_progress_bar=False)[0]
            chunk_texts = [result.get("text", "") for result in search_results]
            chunk_embeddings = self.vector_store.embedding_model.encode(chunk_texts, show_progress_bar=False)

            for result, chunk_embedding in zip(search_results, chunk_embeddings):
                score = self._compute_cosine_similarity(query_embedding, chunk_embedding)
                enriched_result = dict(result)
                enriched_result["relevance_score"] = self._normalize_score(score)
                ranked_results.append(enriched_result)

        ranked_results.sort(key=lambda result: result.get("relevance_score", 0.0), reverse=True)
        return ranked_results

    def _compute_cosine_similarity(self, vector_a, vector_b) -> float:
        """Compute cosine similarity without extra dependencies."""
        dot_product = 0.0
        norm_a = 0.0
        norm_b = 0.0

        for a, b in zip(vector_a, vector_b):
            dot_product += float(a) * float(b)
            norm_a += float(a) * float(a)
            norm_b += float(b) * float(b)

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / ((norm_a ** 0.5) * (norm_b ** 0.5))

    def _normalize_score(self, score) -> float:
        """Normalize relevance score to [0, 1]."""
        try:
            normalized = float(score)
        except (TypeError, ValueError):
            return 0.0

        if normalized < 0.0:
            return 0.0
        if normalized > 1.0:
            return 1.0
        return normalized

    def _build_explainability(self, answer: str, ranked_results: List[Dict]) -> Dict:
        """Create explainability payload: confidence, retrieved evidence, attribution."""
        top_results = ranked_results[:8]
        evidence_chunks = []
        document_scores = defaultdict(list)

        for result in top_results:
            metadata = result.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            title = metadata.get("title", "Unknown")
            doc_id = metadata.get("document_id")
            chunk_index = metadata.get("chunk_index")
            score = self._normalize_score(result.get("relevance_score", 0.0))
            preview = result.get("text", "").replace("\n", " ").strip()[:260]

            evidence_chunks.append({
                "document_id": doc_id,
                "filename": filename,
                "title": title,
                "chunk_index": chunk_index,
                "relevance_score": round(score, 4),
                "chunk_preview": preview,
            })

            key = doc_id or filename
            document_scores[key].append({
                "document_id": doc_id,
                "filename": filename,
                "title": title,
                "score": score,
            })

        document_contributions = []
        for _, scores in document_scores.items():
            first = scores[0]
            max_score = max(item["score"] for item in scores)
            avg_score = sum(item["score"] for item in scores) / len(scores)
            document_contributions.append({
                "document_id": first["document_id"],
                "filename": first["filename"],
                "title": first["title"],
                "max_relevance_score": round(max_score, 4),
                "avg_relevance_score": round(avg_score, 4),
                "supporting_chunks": len(scores),
            })

        document_contributions.sort(key=lambda item: item["max_relevance_score"], reverse=True)
        confidence_score = self._calculate_confidence(top_results)
        answer_attribution = self._build_answer_attribution(answer, top_results)

        explanation_summary = (
            f"RAG-Ex retrieved {len(top_results)} relevant chunk(s) from "
            f"{len(document_contributions)} source document(s). "
            f"Confidence is estimated from chunk relevance and evidence concentration."
        )

        return {
            "confidence_score": confidence_score,
            "retrieved_chunk_count": len(top_results),
            "document_count": len(document_contributions),
            "explanation_summary": explanation_summary,
            "evidence_chunks": evidence_chunks,
            "document_contributions": document_contributions,
            "answer_attribution": answer_attribution,
        }

    def _calculate_confidence(self, ranked_results: List[Dict]) -> float:
        """Estimate answer confidence from top chunk relevance."""
        if not ranked_results:
            return 0.0

        scores = [self._normalize_score(result.get("relevance_score", 0.0)) for result in ranked_results[:3]]
        top_score = max(scores)
        avg_score = sum(scores) / len(scores)
        confidence = (0.6 * avg_score) + (0.4 * top_score)
        return round(confidence, 4)

    def _build_answer_attribution(self, answer: str, ranked_results: List[Dict]) -> List[Dict]:
        """Map each answer sentence to the strongest supporting chunk."""
        if not answer.strip() or not ranked_results:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", answer)
            if len(sentence.strip()) >= 20
        ][:6]

        attributions = []
        for sentence in sentences:
            sentence_tokens = self._tokenize(sentence)
            best_result = None
            best_score = -1.0

            for result in ranked_results[:8]:
                chunk_text = result.get("text", "")
                chunk_tokens = self._tokenize(chunk_text)
                if sentence_tokens and chunk_tokens:
                    lexical_overlap = len(sentence_tokens.intersection(chunk_tokens)) / max(len(sentence_tokens), 1)
                else:
                    lexical_overlap = 0.0

                relevance = self._normalize_score(result.get("relevance_score", 0.0))
                combined_score = (0.6 * lexical_overlap) + (0.4 * relevance)

                if combined_score > best_score:
                    best_score = combined_score
                    best_result = result

            if best_result:
                metadata = best_result.get("metadata", {})
                attributions.append({
                    "answer_segment": sentence,
                    "filename": metadata.get("filename", "Unknown"),
                    "title": metadata.get("title", "Unknown"),
                    "chunk_index": metadata.get("chunk_index"),
                    "relevance_score": round(self._normalize_score(best_result.get("relevance_score", 0.0)), 4),
                    "attribution_score": round(best_score, 4),
                })

        return attributions

    def _tokenize(self, text: str) -> set:
        """Tokenize text for lightweight lexical overlap attribution."""
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
            "have", "has", "had", "you", "your", "they", "their", "into", "about", "than",
            "then", "but", "not", "can", "could", "would", "should", "will", "just", "only",
            "also", "very", "more", "most", "such", "what", "when", "where", "which", "while",
            "been", "being", "because", "there", "here", "some", "any", "all", "our", "its",
        }
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return {token for token in tokens if len(token) > 2 and token not in stop_words}
