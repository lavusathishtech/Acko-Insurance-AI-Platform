"""
Adds 4 FAQ RAG cells to trainFAQ.ipynb:
  1. PROMPT_TEMPLATE (from faq_engine)
  2. PDF -> ChromaDB indexing (Q/A chunks via faq_engine)
  3. faq_answer() RAG query function
  4. Test cell
"""
import json
from pathlib import Path

NB_PATH = Path("C:/final project/.venv/Scripts/trainFAQ.ipynb")

new_cells = [
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "faq_prompt_template",
        "metadata": {},
        "outputs": [],
        "source": [
            "# ============================================================\n",
            "# FAQ RAG - STEP 1: Prompt template (shared with faq_engine.py)\n",
            "# ============================================================\n",
            "import sys\n",
            "sys.path.insert(0, str(PROJECT_ROOT))\n",
            "from faq_engine import PROMPT_TEMPLATE\n",
            "\n",
            "print('Prompt template loaded from faq_engine.py')\n",
            "print(f'Template length: {len(PROMPT_TEMPLATE)} characters.')\n",
        ],
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "faq_chroma_index",
        "metadata": {},
        "outputs": [],
        "source": [
            "# ============================================================\n",
            "# FAQ RAG - STEP 2: Index FAQ PDFs (one chunk per Q/A pair)\n",
            "# ============================================================\n",
            "import sys\n",
            "sys.path.insert(0, str(PROJECT_ROOT))\n",
            "from faq_engine import INDEX_VERSION, index_policy_pdfs, get_chroma_collection\n",
            "\n",
            "# Re-index when INDEX_VERSION changes in faq_engine.py\n",
            "chunk_count = index_policy_pdfs(force=False)\n",
            "collection = get_chroma_collection()\n",
            "print(f'FAQ collection: {FAQ_COLLECTION} | chunks: {chunk_count} | index v{INDEX_VERSION}')\n",
            "print('To force full re-index: index_policy_pdfs(force=True)')\n",
        ],
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "faq_query_fn",
        "metadata": {},
        "outputs": [],
        "source": [
            "# ============================================================\n",
            "# FAQ RAG - STEP 3: FAQ Query Function\n",
            "# ============================================================\n",
            "import sys\n",
            "sys.path.insert(0, str(PROJECT_ROOT))\n",
            "from faq_engine import PROMPT_TEMPLATE, retrieve_faq_context\n",
            "\n",
            "def faq_answer(question, top_k=8):\n",
            "    print(f'Customer Question: {question}')\n",
            "    print('-' * 55)\n",
            "\n",
            "    if gemini is None:\n",
            "        print('ERROR: Gemini not configured. Set GEMINI_API_KEY in .env')\n",
            "        return None\n",
            "\n",
            "    context = retrieve_faq_context(question, top_k=top_k)\n",
            "    if not context:\n",
            "        print('No relevant FAQ context found. Re-run Step 2 indexing.')\n",
            "        return None\n",
            "\n",
            "    print('Top FAQ context (preview):')\n",
            "    print(context[:500], '...' if len(context) > 500 else '')\n",
            "    print()\n",
            "\n",
            "    filled_prompt = PROMPT_TEMPLATE.format(context=context, question=question)\n",
            "    try:\n",
            "        response = gemini.generate_content(filled_prompt)\n",
            "        answer = response.text.strip()\n",
            "    except Exception as e:\n",
            "        print(f'Gemini error: {e}')\n",
            "        return None\n",
            "\n",
            "    print('Answer:')\n",
            "    print(answer)\n",
            "    print()\n",
            "    return answer\n",
            "\n",
            "print('faq_answer() is ready!')\n",
        ],
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "faq_test",
        "metadata": {},
        "outputs": [],
        "source": [
            "# ============================================================\n",
            "# FAQ RAG - STEP 4: Test the Chatbot\n",
            "# ============================================================\n",
            "\n",
            "faq_answer('How do I buy Acko car insurance online? Step-by-step guide.')\n",
        ],
    },
]


def _is_faq_rag_cell(cell: dict, faq_ids: set[str]) -> bool:
    if cell.get("id") in faq_ids:
        return True
    src = "".join(cell.get("source", []))
    return "FAQ RAG - STEP" in src


def main():
    nb = json.loads(NB_PATH.read_text(encoding="utf-8"))
    faq_ids = {c["id"] for c in new_cells}
    nb["cells"] = [c for c in nb["cells"] if not _is_faq_rag_cell(c, faq_ids)]
    nb["cells"].extend(new_cells)
    NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Added {len(new_cells)} FAQ RAG cells to {NB_PATH}")


if __name__ == "__main__":
    main()
