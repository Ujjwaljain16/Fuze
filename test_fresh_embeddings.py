import os
import numpy as np
from supabase import create_client, Client
from tqdm import tqdm
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity

# Optional: if using separate file/module for embedding
from embedding_utils import get_embedding  # your own local embedding method

class EmbeddingTester:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )

    def fetch_bookmarks_with_embeddings(self, limit=100):
        """
        Fetch bookmarks with valid embeddings from Supabase
        """
        response = (
            self.supabase.table('saved_content')
            .select('id, title, url, embedding')
            .is_not_null('embedding')
            .limit(limit)
            .execute()
        )
        return response.data

    def generate_query_embedding(self, query: str):
        """
        Generate a fresh embedding for the query using local method
        """
        return generate_fresh_embedding(query)

    def semantic_search(self, query, top_k=5):
        """
        Perform semantic search on bookmarks using cosine similarity
        """
        query_embedding = self.generate_query_embedding(query)
        bookmarks = self.fetch_bookmarks_with_embeddings()

        similarities = []
        for bookmark in bookmarks:
            similarity = cosine_similarity(
                [query_embedding], [bookmark['embedding']]
            )[0][0]
            similarities.append({
                'id': bookmark['id'],
                'title': bookmark['title'],
                'url': bookmark['url'],
                'similarity': similarity
            })

        return sorted(similarities, key=lambda x: x['similarity'], reverse=True)[:top_k]

    def visualize_embeddings(self):
        """
        Visualize embeddings using t-SNE
        """
        bookmarks = self.fetch_bookmarks_with_embeddings(limit=50)
        embeddings = [bm['embedding'] for bm in bookmarks]
        titles = [bm['title'] for bm in bookmarks]

        tsne = TSNE(n_components=2, random_state=42)
        embeddings_2d = tsne.fit_transform(embeddings)

        plt.figure(figsize=(12, 8))
        plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.7)

        for i, title in enumerate(titles):
            plt.annotate(title[:20], (embeddings_2d[i, 0], embeddings_2d[i, 1]), alpha=0.5, fontsize=8)

        plt.title('Bookmark Embeddings Visualization')
        plt.xlabel('t-SNE Dimension 1')
        plt.ylabel('t-SNE Dimension 2')
        plt.tight_layout()
        plt.show()

    def embedding_quality_report(self):
        """
        Generate quality stats on embeddings
        """
        bookmarks = self.fetch_bookmarks_with_embeddings()
        embeddings = np.array([bm['embedding'] for bm in bookmarks])

        report = {
            'Total Bookmarks': len(bookmarks),
            'Embedding Dimension': embeddings.shape[1],
            'Mean Embedding Vector': np.mean(embeddings, axis=0),
            'Std Embedding Vector': np.std(embeddings, axis=0),
            'Embedding Variance': np.var(embeddings, axis=0)
        }
        return report

def main():
    tester = EmbeddingTester()

    print("🔍 Semantic Search Results:")
    search_results = tester.semantic_search("Python programming")
    for result in search_results:
        print(f"Title     : {result['title']}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"URL       : {result['url']}\n")

    tester.visualize_embeddings()

    report = tester.embedding_quality_report()
    print("📊 Embedding Quality Report:")
    for key, value in report.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    main()
