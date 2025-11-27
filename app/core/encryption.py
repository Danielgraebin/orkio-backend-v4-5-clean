"""
ORKIO v4.5 - Encryption Module
AES-256-GCM para criptografia de API keys
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


def get_encryption_key() -> bytes:
    """
    Obtém a chave de criptografia da variável de ambiente.
    Se não existir, gera uma nova (apenas para desenvolvimento).
    """
    key_b64 = os.getenv("ORKIO_ENCRYPTION_KEY")
    
    if not key_b64:
        # Gerar chave temporária para desenvolvimento
        # EM PRODUÇÃO, DEVE SER CONFIGURADA VIA VARIÁVEL DE AMBIENTE
        key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.b64encode(key).decode('utf-8')
        os.environ["ORKIO_ENCRYPTION_KEY"] = key_b64
        print(f"⚠️  WARNING: Using temporary encryption key. Set ORKIO_ENCRYPTION_KEY in production!")
        print(f"   ORKIO_ENCRYPTION_KEY={key_b64}")
    
    return base64.b64decode(key_b64)


def encrypt_api_key(plain_key: str) -> str:
    """
    Criptografa uma API key usando AES-256-GCM.
    
    Args:
        plain_key: API key em texto plano
        
    Returns:
        String base64 contendo: nonce (12 bytes) + ciphertext + tag (16 bytes)
    """
    if not plain_key:
        raise ValueError("API key cannot be empty")
    
    # Obter chave de criptografia
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    
    # Gerar nonce aleatório (12 bytes para GCM)
    nonce = os.urandom(12)
    
    # Criptografar
    ciphertext = aesgcm.encrypt(nonce, plain_key.encode('utf-8'), None)
    
    # Retornar: nonce + ciphertext (já inclui tag) em base64
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Descriptografa uma API key usando AES-256-GCM.
    
    Args:
        encrypted_key: String base64 contendo nonce + ciphertext + tag
        
    Returns:
        API key em texto plano
    """
    if not encrypted_key:
        raise ValueError("Encrypted key cannot be empty")
    
    # Obter chave de criptografia
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    
    # Decodificar base64
    encrypted = base64.b64decode(encrypted_key)
    
    # Separar nonce (12 bytes) e ciphertext
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    
    # Descriptografar
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


# Teste básico
if __name__ == "__main__":
    # Testar criptografia/descriptografia
    test_key = "sk-test-1234567890abcdefghijklmnopqrstuvwxyz"
    
    print("Original:", test_key)
    
    encrypted = encrypt_api_key(test_key)
    print("Encrypted:", encrypted)
    
    decrypted = decrypt_api_key(encrypted)
    print("Decrypted:", decrypted)
    
    assert test_key == decrypted, "Decryption failed!"
    print("✅ Encryption/Decryption test passed!")

