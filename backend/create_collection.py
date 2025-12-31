import requests
import time

class SolrCollectionManager:
    def __init__(self, base_url="http://localhost:8983/solr"):
        self.base_url = base_url
        self.admin_url = f"{base_url}/admin/cores"
    
    def collection_exists(self, collection_name):
        """Check if collection exists"""
        params = {'action': 'STATUS', 'core': collection_name}
        response = requests.get(self.admin_url, params=params)
        result = response.json()
        return collection_name in result.get('status', {})
    
    def create_collection(self, collection_name):
        """Create a new collection"""
        params = {
            'action': 'CREATE',
            'name': collection_name,
            'instanceDir': collection_name,
        }
        
        response = requests.get(self.admin_url, params=params)
        return response.status_code == 200
    
    def delete_collection(self, collection_name):
        """Delete collection"""
        params = {
            'action': 'UNLOAD',
            'core': collection_name,
            'deleteIndex': 'true',
            'deleteDataDir': 'true',
            'deleteInstanceDir': 'true'
        }
        
        response = requests.get(self.admin_url, params=params)
        return response.status_code == 200
    
    def setup_vector_schema(self, collection_name, vector_dimension=1536):
        """Configure schema for vector search"""
        schema_url = f"{self.base_url}/{collection_name}/schema"
        
        # Add vector field type
        field_type = {
            "add-field-type": {
                "name": "knn_vector",
                "class": "solr.DenseVectorField",
                "vectorDimension": vector_dimension,
                "similarityFunction": "cosine"
            }
        }
        requests.post(schema_url, json=field_type)
        
        # Add fields
        fields = [
            {"name": "vector", "type": "knn_vector"},
            {"name": "title", "type": "text_general"},
            {"name": "content", "type": "text_general"},
            {"name": "category", "type": "string"},
            {"name": "authority_level", "type": "pint"},
            {"name": "source", "type": "string"}
        ]
        
        for field_def in fields:
            field = {
                "add-field": {
                    **field_def,
                    "indexed": True,
                    "stored": True
                }
            }
            requests.post(schema_url, json=field)
    
    def setup_complete_collection(self, collection_name, vector_dimension=1536, recreate=False):
        """Complete setup: create collection and configure schema"""
        
        # Delete if recreate flag is set
        if recreate and self.collection_exists(collection_name):
            print(f"Deleting existing collection: {collection_name}")
            self.delete_collection(collection_name)
            time.sleep(2)
        
        # Check if already exists
        if self.collection_exists(collection_name):
            print(f"✅ Collection '{collection_name}' already exists")
            return True
        
        # Create collection
        print(f"Creating collection: {collection_name}...")
        if not self.create_collection(collection_name):
            print(f"❌ Failed to create collection")
            return False
        
        print(f"✅ Collection created!")
        time.sleep(2)
        
        # Setup schema
        print("Configuring schema for vector search...")
        self.setup_vector_schema(collection_name, vector_dimension)
        
        print(f"🎉 Collection '{collection_name}' is ready!")
        return True

# Usage
if __name__ == "__main__":
    manager = SolrCollectionManager()
    
    # Create new collection
    # manager.setup_complete_collection("tax_docs", vector_dimension=1536)
    
    # Or recreate if exists
    manager.setup_complete_collection("tax_docs", vector_dimension=1536, recreate=True)