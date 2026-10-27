import os, tempfile
from pathlib import Path
TEST_DIR=tempfile.mkdtemp(prefix='careerorbit-tests-')
test_url=os.environ.get('TEST_DATABASE_URL','sqlite:///'+TEST_DIR+'/test.db')
if not test_url.startswith('sqlite:') and not test_url.endswith('_test'): raise RuntimeError('Test database name must end in _test')
os.environ['DATABASE_URL']=test_url
os.environ['STORAGE_DIR']=TEST_DIR+'/files'
os.environ['PRODUCTION']='false'
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base,engine,SessionLocal

@pytest.fixture(autouse=True)
def clean():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    yield
@pytest.fixture
def client():
    with TestClient(app,headers={'Origin':'http://localhost:3000','X-CareerOrbit-Request':'1'}) as c: yield c
@pytest.fixture
def signed(client):
    r=client.post('/api/auth/register',json={'email':'applicant@example.com','password':'A-secure-test-password-001'})
    assert r.status_code==200
    return client
@pytest.fixture
def db():
    with SessionLocal() as session: yield session
