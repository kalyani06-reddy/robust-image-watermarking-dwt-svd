from app import app


def test_home_endpoint_returns_html():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Robust Image Watermarking' in response.data


def test_embed_endpoint_requires_files():
    client = app.test_client()
    response = client.post('/api/embed')
    assert response.status_code == 400
