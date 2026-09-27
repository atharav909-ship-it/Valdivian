import re
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app import CartItem, Order, Product, User, create_app, db


@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'SECRET_KEY': 'test-secret'})
    with app.app_context():
        db.create_all()
        db.session.add(Product(name='Desk lamp', description='A warm lamp', category='Home', price=Decimal('99.50'), stock=3))
        db.session.add(User(name='Admin', email='admin@example.com', password_hash=generate_password_hash('password123'), is_admin=True))
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def post(client, path, data=None):
    client.get('/')
    with client.session_transaction() as sess:
        token = sess['csrf_token']
    return client.post(path, data={**(data or {}), 'csrf_token': token}, follow_redirects=True)


def test_catalog_and_search(client):
    assert b'Desk lamp' in client.get('/products?q=Desk').data
    assert b'No products found' in client.get('/products?q=keyboard').data
    assert client.get('/health').json == {'status': 'okS'}


def test_registration_auth_and_admin_permissions(client):
    response = post(client, '/register', {'name': 'Alex', 'email': 'alex@example.com', 'password': 'password123'})
    assert b'Welcome to Valdivian' in response.data
    assert client.get('/admin').status_code == 403
    post(client, '/logout')
    assert client.get('/cart').status_code == 302
    response = post(client, '/login', {'email': 'alex@example.com', 'password': 'wrong'})
    assert b'Invalid email or password' in response.data
    response = post(client, '/login', {'email': 'alex@example.com', 'password': 'password123'})
    assert b'Fresh finds' in response.data


def test_cart_checkout_and_stock(client):
    post(client, '/register', {'name': 'Alex', 'email': 'alex@example.com', 'password': 'password123'})
    assert b'Not enough stock' in post(client, '/cart/add/1', {'quantity': '4'}).data
    assert b'99.50' in post(client, '/cart/add/1', {'quantity': '1'}).data
    assert b'199.00' in post(client, '/cart/add/1', {'quantity': '1'}).data
    assert b'Not enough stock' in post(client, '/cart/add/1', {'quantity': '2'}).data
    with client.application.app_context():
        item_id = db.session.query(CartItem).one().id
    assert b'99.50' in post(client, f'/cart/update/{item_id}', {'quantity': '1'}).data
    result = post(client, '/checkout')
    assert b'Order #1 placed' in result.data
    assert b'Desk lamp' in client.get('/orders').data
    with client.application.app_context():
        assert db.session.get(Product, 1).stock == 2
        assert db.session.query(Order).one().total == Decimal('99.50')
        assert db.session.query(CartItem).count() == 0


def test_remove_cart_and_csrf(client):
    post(client, '/register', {'name': 'Alex', 'email': 'alex@example.com', 'password': 'password123'})
    assert client.post('/cart/add/1', data={'quantity': 1}).status_code == 400
    post(client, '/cart/add/1', {'quantity': '1'})
    with client.application.app_context():
        item_id = db.session.query(CartItem).one().id
    assert b'Nothing in your cart' in post(client, f'/cart/update/{item_id}', {'quantity': '1', 'action': 'remove'}).data


def test_admin_product_and_order(client):
    post(client, '/login', {'email': 'admin@example.com', 'password': 'password123'})
    result = post(client, '/admin/products/new', {'name': 'Cup', 'category': 'Home', 'description': 'Ceramic cup', 'price': '12.99', 'stock': '5', 'image_url': ''})
    assert b'Cup' in result.data
    with client.application.app_context():
        product = db.session.query(Product).filter_by(name='Cup').one()
        product_id = product.id
    result = post(client, f'/admin/products/{product_id}/edit', {'name': 'Blue cup', 'category': 'Home', 'description': 'Ceramic cup', 'price': '14.99', 'stock': '4', 'image_url': ''})
    assert b'Blue cup' in result.data
    result = post(client, f'/admin/products/{product_id}/delete')
    assert b'Blue cup' not in result.data
