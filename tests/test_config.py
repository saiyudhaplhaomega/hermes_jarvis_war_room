import pytest
from backend.core.config import PostQuantumCrypto

def test_post_quantum_crypto():
    pqc = PostQuantumCrypto()
    data = b"Sensitive data"
    ciphertext = pqc.encrypt(data)
    assert pqc.decrypt(ciphertext) == data
