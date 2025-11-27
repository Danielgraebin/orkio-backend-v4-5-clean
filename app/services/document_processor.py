"""
Serviço de processamento de documentos para RAG
- Extração de texto (PDF, TXT, DOCX)
- Chunking com tiktoken (800 tokens, 200 overlap)
- Embeddings OpenAI (text-embedding-3-small)
- Armazenamento pgvector
"""
import os
import tiktoken
from typing import List, Tuple
from openai import OpenAI
import pypdf
from docx import Document as DocxDocument


class DocumentProcessor:
    """
    Processa documentos para o sistema RAG:
    1. Extrai texto do arquivo
    2. Divide em chunks com overlap
    3. Gera embeddings OpenAI
    """
    
    def __init__(self):
        # Cliente para chat (usa proxy Manus)
        self.chat_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        # Cliente para embeddings (usa API OpenAI direta)
        self.embedding_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1"
        )
        self.encoding = tiktoken.get_encoding("cl100k_base")  # Encoding do GPT-4
        self.chunk_size = 800  # tokens
        self.chunk_overlap = 200  # tokens
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimensions = 1536
    
    def extract_text(self, file_path: str, filename: str) -> str:
        """
        Extrai texto de PDF, TXT ou DOCX.
        """
        extension = filename.lower().split('.')[-1]
        
        if extension == 'pdf':
            return self._extract_from_pdf(file_path)
        elif extension == 'txt':
            return self._extract_from_txt(file_path)
        elif extension in ['docx', 'doc']:
            return self._extract_from_docx(file_path)
        else:
            raise ValueError(f"Formato não suportado: {extension}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extrai texto de PDF usando pypdf."""
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extrai texto de TXT."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read().strip()
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extrai texto de DOCX."""
        doc = DocxDocument(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Divide texto em chunks com overlap.
        
        Returns:
            List[(chunk_text, start_token, end_token)]
        """
        if not text or not text.strip():
            return []
        
        # Tokenizar texto completo
        tokens = self.encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Definir fim do chunk
            end = start + self.chunk_size
            
            # Extrair tokens do chunk
            chunk_tokens = tokens[start:end]
            
            # Decodificar para texto
            chunk_text = self.encoding.decode(chunk_tokens)
            
            chunks.append((chunk_text, start, end))
            
            # Próximo chunk começa com overlap
            start += (self.chunk_size - self.chunk_overlap)
        
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Gera embedding OpenAI para um chunk de texto.
        """
        if not text or not text.strip():
            # Retornar vetor zero se texto vazio
            return [0.0] * self.embedding_dimensions
        
        response = self.embedding_client.embeddings.create(
            model=self.embedding_model,
            input=text,
            encoding_format="float"
        )
        
        return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Gera embeddings em batch para múltiplos textos.
        TEMPORÁRIO: Usando embeddings fake (vetores aleatórios) até ter chave OpenAI válida.
        """
        import random
        import hashlib
        
        if not texts:
            return []
        
        embeddings = []
        
        for text in texts:
            # Gerar vetor determinístico baseado no hash do texto
            text_hash = hashlib.md5(text.encode()).hexdigest()
            random.seed(text_hash)
            embedding = [random.uniform(-1, 1) for _ in range(self.embedding_dimensions)]
            embeddings.append(embedding)
        
        return embeddings
        
        # TODO: Descomentar quando tiver chave OpenAI válida
        # for i in range(0, len(texts), batch_size):
        #     batch = texts[i:i + batch_size]
        #     valid_batch = [t if t.strip() else " " for t in batch]
        #     response = self.embedding_client.embeddings.create(
        #         model=self.embedding_model,
        #         input=valid_batch,
        #         encoding_format="float"
        #     )
        #     batch_embeddings = [item.embedding for item in response.data]
        #     embeddings.extend(batch_embeddings)
        # return embeddings
    
    def process_document(self, file_path: str, filename: str) -> Tuple[List[str], List[List[float]]]:
        """
        Pipeline completo de processamento:
        1. Extrai texto
        2. Cria chunks
        3. Gera embeddings
        
        Returns:
            (chunk_texts, chunk_embeddings)
        """
        # 1. Extrair texto
        text = self.extract_text(file_path, filename)
        
        if not text or not text.strip():
            raise ValueError("Documento vazio ou sem texto extraível")
        
        # 2. Criar chunks
        chunks_data = self.chunk_text(text)
        
        if not chunks_data:
            raise ValueError("Falha ao criar chunks do documento")
        
        chunk_texts = [chunk[0] for chunk in chunks_data]
        
        # 3. Gerar embeddings em batch
        embeddings = self.generate_embeddings_batch(chunk_texts)
        
        return chunk_texts, embeddings

