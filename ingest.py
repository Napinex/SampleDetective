from rag_core import build_index, load_documents_as_chunks

if __name__ == "__main__":
    chunks = load_documents_as_chunks()
    index = build_index(chunks)
    print(f"Index neu gebaut: {len(index['chunks'])} Chunks")
    print("Gespeichert in: storage/rag_index.pkl")
