from app import rag_indice

if __name__ == "__main__":
    print("Generando embeddings (la primera vez descarga el modelo, puede tardar un par de minutos)...")
    print(rag_indice.reindexar())