"""Create local configuration once; never overwrite existing user values or print secrets."""
from pathlib import Path
import secrets
from cryptography.fernet import Fernet
root=Path(__file__).resolve().parents[1]
p=root/'.env'
if p.exists():
    print('Existing .env preserved.')
else:
    keyfile=root/'storage'/'.encryption-key'
    key=keyfile.read_text().strip() if keyfile.exists() else Fernet.generate_key().decode()
    template=(root/'.env.example').read_text()
    template=template.replace('ENCRYPTION_KEY=\n','ENCRYPTION_KEY='+key+'\n').replace('POSTGRES_PASSWORD=\n','POSTGRES_PASSWORD='+secrets.token_urlsafe(32)+'\n')
    with p.open('x') as f:f.write(template)
    p.chmod(0o600)
    print('Local .env created with generated secrets. No provider credentials were configured.')
