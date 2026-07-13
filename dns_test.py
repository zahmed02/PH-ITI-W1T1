# dns_test.py
import socket
try:
    ip = socket.gethostbyname('api-inference.huggingface.co')
    print(f"✅ DNS resolved! IP: {ip}")
except Exception as e:
    print(f"❌ DNS failed: {e}")