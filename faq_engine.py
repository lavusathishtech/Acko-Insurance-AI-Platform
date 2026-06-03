"""
FAQ RAG engine — indexes ACKO FAQ PDFs into ChromaDB and answers via Gemini.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import chromadb
from google import genai
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "chroma_db"
FAQ_COLLECTION = "acko_faqs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_VERSION = "2"  # bump when chunking / paths change (forces re-index)

# FAQ documents (Q&A format) — primary source for customer questions
FAQ_PDF_PATHS = [
    BASE_DIR / "docs" / "Acko_Insurance_FAQs.pdf",
    BASE_DIR / "docs" / "Acko_Motor_Insurance_FAQs.pdf",
    BASE_DIR / "docs" / "Acko_Health_Insurance_FAQs.pdf",
]

# Optional policy T&C (dense legal text; lower priority at answer time)
POLICY_TC_PDF_PATHS = [
    BASE_DIR / "docs" / "Acko_Motor_Insurance_Policy_TC.pdf",
    BASE_DIR / "docs" / "Acko_Health_Insurance_Policy_TC.pdf",
]

ALL_PDF_PATHS = FAQ_PDF_PATHS + POLICY_TC_PDF_PATHS

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# Split FAQ PDFs into individual Q/A pairs (e.g. "Q A6. ... A ...")
FAQ_QA_PATTERN = re.compile(
    r"Q\s+(?:[A-Z]?\d+\.\s*)?(.+?)\s+A\s+(.+?)(?=Q\s+[A-Z]?\d+\.|$)",
    re.IGNORECASE | re.DOTALL,
)

PROMPT_TEMPLATE = """
You are an intelligent and friendly insurance assistant for ACKO Insurance.

Answer the customer question using ONLY the provided FAQ context below.

---------------------
FAQ CONTEXT:
{context}
---------------------

CUSTOMER QUESTION:
{question}

---------------------

INSTRUCTIONS:
1. Find the FAQ entry whose question best matches the customer question.
2. Answer ONLY from that entry's answer text. Ignore unrelated FAQ entries in the context.
3. If the customer asks for steps or a "how to" guide, list the steps clearly (Step 1, Step 2, ...) exactly as in the FAQ answer.
4. Do NOT answer about premium calculation, IDV formulas, or coverage unless that is what the customer asked.
5. If the exact answer is not in the context, say: "I'm not fully sure based on the available policy documents. Please contact ACKO support for confirmation."
6. Be concise, friendly, and do not invent information.

FINAL ANSWER:
"""

_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might must shall can to of in for on "
    "with at by from as and or but if how what when where why who which "
    "my your our their this that it its i we you they he she".split()
)


def _embed_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


def get_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=FAQ_COLLECTION,
        embedding_function=_embed_fn(),
        metadata={"index_version": INDEX_VERSION},
    )


def _is_valid_pdf(pdf_path: Path) -> bool:
    try:
        with open(pdf_path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def _read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    return full_text


def load_faq_qa_chunks(pdf_path: Path) -> list[tuple[str, dict]]:
    """One chunk per FAQ Q/A pair for accurate retrieval."""
    if not _is_valid_pdf(pdf_path):
        print(f"Skipping invalid PDF: {pdf_path.name}")
        return []

    text = _read_pdf_text(pdf_path)
    chunks: list[tuple[str, dict]] = []

    for match in FAQ_QA_PATTERN.finditer(text):
        question = " ".join(match.group(1).split())
        answer = " ".join(match.group(2).split())
        if len(question) < 8 or len(answer) < 10:
            continue
        doc = f"Q: {question}\nA: {answer}"
        chunks.append(
            (
                doc,
                {
                    "source": pdf_path.name,
                    "section": pdf_path.stem,
                    "question": question[:300],
                    "doc_type": "faq",
                },
            )
        )

    if chunks:
        return chunks

    # Fallback: word windows if PDF has no Q/A markers
    return [
        (f"[{pdf_path.stem}] {c}", {"source": pdf_path.name, "section": pdf_path.stem, "doc_type": "faq"})
        for c in _word_chunks(text, pdf_path.stem)
    ]


def _word_chunks(text: str, stem: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(f"[{stem}] {chunk}")
    return chunks


def load_policy_tc_chunks(pdf_path: Path, chunk_size: int = 500, overlap: int = 50) -> list[tuple[str, dict]]:
    if not _is_valid_pdf(pdf_path):
        return []
    text = _read_pdf_text(pdf_path)
    return [
        (
            c,
            {"source": pdf_path.name, "section": pdf_path.stem, "doc_type": "policy_tc"},
        )
        for c in _word_chunks(text, pdf_path.stem, chunk_size, overlap)
    ]


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOPWORDS}


def _rerank_docs(question: str, docs: list[str], metadatas: list[dict] | None = None) -> list[str]:
    """Boost chunks whose FAQ question overlaps the user query."""
    q_tokens = _tokenize(question)
    if not q_tokens:
        return docs

    scored: list[tuple[float, str]] = []
    for i, doc in enumerate(docs):
        meta = (metadatas[i] if metadatas and i < len(metadatas) else {}) or {}
        faq_q = meta.get("question", "")
        if not faq_q and doc.startswith("Q:"):
            faq_q = doc.split("\n", 1)[0][2:]

        doc_tokens = _tokenize(faq_q + " " + doc)
        overlap = len(q_tokens & doc_tokens) / max(len(q_tokens), 1)

        bonus = 0.0
        ql = question.lower()
        dl = doc.lower()
        if "step" in ql and "step 1" in dl:
            bonus += 0.35
        if "buy" in ql and "buy" in dl:
            bonus += 0.25
        if "how do i" in ql and faq_q:
            bonus += 0.15
        if meta.get("doc_type") == "faq":
            bonus += 0.1

        scored.append((overlap + bonus, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored]


def _focus_context(question: str, docs: list[str]) -> str:
    """Prefer the single best-matching Q/A block; include a second only if highly relevant."""
    if not docs:
        return ""

    ranked = _rerank_docs(question, docs)
    primary = ranked[0]
    parts = [primary]

    if len(ranked) > 1:
        q_tokens = _tokenize(question)
        doc_tokens = _tokenize(ranked[1])
        if len(q_tokens & doc_tokens) >= max(2, len(q_tokens) // 3):
            parts.append(ranked[1])

    return "\n\n---\n\n".join(parts)


def index_policy_pdfs(force: bool = False) -> int:
    """Index FAQ + policy PDFs into ChromaDB. Returns chunk count."""
    existing_pdfs = [p for p in ALL_PDF_PATHS if p.exists()]
    if not existing_pdfs:
        return 0

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = get_chroma_collection()
    stored_version = (collection.metadata or {}).get("index_version")

    if not force and collection.count() > 0 and stored_version == INDEX_VERSION:
        return collection.count()

    try:
        client.delete_collection(name=FAQ_COLLECTION)
    except Exception:
        pass

    collection = get_chroma_collection()
    all_docs: list[str] = []
    all_metas: list[dict] = []
    all_ids: list[str] = []

    idx = 0
    for pdf in FAQ_PDF_PATHS:
        if not pdf.exists():
            continue
        for doc, meta in load_faq_qa_chunks(pdf):
            all_docs.append(doc)
            all_metas.append(meta)
            all_ids.append(f"faq_{idx}")
            idx += 1

    for pdf in POLICY_TC_PDF_PATHS:
        if not pdf.exists():
            continue
        for doc, meta in load_policy_tc_chunks(pdf):
            all_docs.append(doc)
            all_metas.append(meta)
            all_ids.append(f"faq_{idx}")
            idx += 1

    if not all_docs:
        return 0

    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        collection.add(
            documents=all_docs[i : i + batch_size],
            metadatas=all_metas[i : i + batch_size],
            ids=all_ids[i : i + batch_size],
        )

    return collection.count()


def retrieve_faq_context(question: str, top_k: int = 8) -> str:
    """Public wrapper for RAG context retrieval (notebook / API)."""
    return _retrieve_context(question, top_k=top_k)


def _retrieve_context(question: str, top_k: int = 8) -> str:
    try:
        collection = get_chroma_collection()
        if collection.count() == 0:
            return ""

        fetch_k = min(max(top_k * 3, 12), collection.count())
        results = collection.query(
            query_texts=[question],
            n_results=fetch_k,
            include=["documents", "metadatas"],
        )
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else []

        if not docs:
            return ""

        ranked = _rerank_docs(question, docs, metas)
        return _focus_context(question, ranked[:top_k])
    except Exception:
        return ""


def _gemini_models() -> list[str]:
    configured = os.getenv("GEMINI_MODEL", "").strip()
    models = [m for m in [configured, "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.0-flash-lite"] if m]
    seen: set[str] = set()
    ordered: list[str] = []
    for m in models:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def answer_faq(question: str, api_key: str | None = None, top_k: int = 8) -> tuple[str, str]:
    """
    RAG answer from policy PDFs. Returns (reply, source).
    source: rag_gemini | rag_fallback | rule_fallback
    """
    key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
    context = _retrieve_context(question, top_k=top_k)

    if key and context:
        try:
            client = genai.Client(api_key=key)
            prompt = PROMPT_TEMPLATE.format(context=context, question=question)
            for model_name in _gemini_models():
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    text = (response.text or "").strip()
                    if text:
                        return text, f"rag_gemini ({model_name})"
                except Exception:
                    continue
        except Exception:
            pass

    if context:
        # Return the best FAQ answer text directly when Gemini is unavailable
        for block in context.split("\n\n---\n\n"):
            if block.startswith("Q:") and "\nA:" in block:
                return block.split("\nA:", 1)[1].strip(), "rag_faq_text"

        snippet = context[:900].replace("\n", " ")
        return (
            f"Based on your ACKO policy documents: {snippet}... "
            "For full details, refer to your policy schedule or contact ACKO support.",
            "rag_snippet",
        )

    return _rule_fallback(question), "rule_fallback"


def _rule_fallback(question: str) -> str:
    msg = question.lower()
    if "buy" in msg and ("car" in msg or "insurance" in msg or "online" in msg):
        return (
            "To buy ACKO car insurance online: visit acko.com or the Acko app, enter your "
            "registration number, confirm car details, choose coverage and add-ons, review IDV, "
            "enter personal details, pay online, and download your digital policy instantly."
        )
    if "claim" in msg:
        return "To file a claim, upload damage photos in the AI Claims Engine or call ACKO 24×7 support with your policy number."
    if "idv" in msg:
        return "IDV is the maximum sum insured for total loss or theft, based on your vehicle's current market value."
    if "ncb" in msg:
        return "NCB is a no-claim discount of 20–50% on own-damage premium for claim-free years."
    if "health" in msg or "hospital" in msg:
        return "ACKO health policies cover hospitalization subject to terms in your health policy document. Check waiting periods and network hospitals."
    if "motor" in msg or "car" in msg or "bike" in msg:
        return "Motor policies cover own damage and third-party liability per your policy type. See the Motor Insurance Policy T&C for exclusions."
    return (
        "I could not find a specific answer in the indexed policy PDFs yet. "
        "Try asking about claims, IDV, NCB, health coverage, or motor policy terms."
    )
