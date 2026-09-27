import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
from urllib.parse import urlparse

import click
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=False, default='')


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id'),)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Placed')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User')
    items = db.relationship('OrderItem', cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)


def create_app(test_config=None):
    app = Flask(__name__)
    database_url = os.getenv('DATABASE_URL', 'sqlite:///Valdivian.db')
    if database_url.startswith('postgres://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgres://'):]
    elif database_url.startswith('postgresql://'):
        database_url = 'postgresql+psycopg://' + database_url[len('postgresql://'):]
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-me'),
                      SQLALCHEMY_DATABASE_URI=database_url,
                      SQLALCHEMY_TRACK_MODIFICATIONS=False,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    if test_config:
        app.config.update(test_config)
    db.init_app(app)

    @app.before_request
    def csrf_protect():
        if request.method == 'POST':
            token = session.get('csrf_token')
            if not token or not secrets.compare_digest(token, request.form.get('csrf_token', '')):
                abort(400, 'Invalid form token')

    @app.context_processor
    def template_context():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(24)
        user = db.session.get(User, session.get('user_id')) if session.get('user_id') else None
        cart_count = db.session.query(db.func.coalesce(db.func.sum(CartItem.quantity), 0)).filter_by(user_id=user.id).scalar() if user else 0
        return {'current_user': user, 'csrf_token': session['csrf_token'], 'cart_count': cart_count}

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('user_id') or not db.session.get(User, session['user_id']):
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapper

    def admin_required(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if not db.session.get(User, session['user_id']).is_admin:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper

    def positive_int(raw):
        try:
            value = int(raw)
            if value > 0:
                return value
        except (ValueError, TypeError):
            pass
        abort(400, 'Enter a positive quantity')

    @app.get('/')
    def index():
        featured = db.session.execute(select(Product).order_by(Product.id.desc()).limit(4)).scalars().all()
        return render_template('index.html', products=featured)

    @app.get('/products')
    def products():
        query = select(Product)
        search = request.args.get('q', '').strip()[:100]
        category = request.args.get('category', '').strip()[:60]
        if search:
            query = query.where(Product.name.ilike(f'%{search}%'))
        if category:
            query = query.where(Product.category == category)
        categories = db.session.execute(select(Product.category).distinct().order_by(Product.category)).scalars().all()
        return render_template('products.html', products=db.session.execute(query.order_by(Product.id.desc())).scalars().all(), categories=categories, search=search, category=category)

    @app.get('/products/<int:product_id>')
    def product_detail(product_id):
        return render_template('product.html', product=db.get_or_404(Product, product_id))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()[:100]
            email = request.form.get('email', '').strip().lower()[:255]
            password = request.form.get('password', '')
            if not name or '@' not in email or len(password) < 8:
                flash('Enter a name, valid email and password of at least 8 characters.', 'error')
            else:
                user = User(name=name, email=email, password_hash=generate_password_hash(password))
                db.session.add(user)
                try:
                    db.session.commit()
                    session.clear()
                    session['user_id'] = user.id
                    flash('Welcome to Valdivian!', 'success')
                    return redirect(url_for('index'))
                except IntegrityError:
                    db.session.rollback()
                    flash('That email is already registered.', 'error')
        return render_template('auth.html', mode='register')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            user = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user and check_password_hash(user.password_hash, request.form.get('password', '')):
                session.clear()
                session['user_id'] = user.id
                return redirect(url_for('index'))
            flash('Invalid email or password.', 'error')
        return render_template('auth.html', mode='login')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.get('/cart')
    @login_required
    def cart():
        items = db.session.execute(select(CartItem).where(CartItem.user_id == session['user_id'])).scalars().all()
        total = sum((item.product.price * item.quantity for item in items), Decimal('0.00'))
        return render_template('cart.html', items=items, total=total)

    @app.post('/cart/add/<int:product_id>')
    @login_required
    def add_cart(product_id):
        product = db.get_or_404(Product, product_id)
        quantity = positive_int(request.form.get('quantity', '1'))
        item = db.session.execute(select(CartItem).where(CartItem.user_id == session['user_id'], CartItem.product_id == product_id)).scalar_one_or_none()
        if product.stock < quantity + (item.quantity if item else 0):
            flash('Not enough stock available.', 'error')
        else:
            if item:
                item.quantity += quantity
            else:
                db.session.add(CartItem(user_id=session['user_id'], product_id=product_id, quantity=quantity))
            db.session.commit()
            flash('Added to cart.', 'success')
        return redirect(url_for('cart'))

    @app.post('/cart/update/<int:item_id>')
    @login_required
    def update_cart(item_id):
        item = db.get_or_404(CartItem, item_id)
        if item.user_id != session['user_id']:
            abort(403)
        quantity = request.form.get('quantity', '').strip()
        if request.form.get('action') == 'remove' or quantity == '0':
            db.session.delete(item)
        else:
            value = positive_int(quantity)
            if value > item.product.stock:
                flash('Not enough stock available.', 'error')
                return redirect(url_for('cart'))
            item.quantity = value
        db.session.commit()
        return redirect(url_for('cart'))

    @app.post('/checkout')
    @login_required
    def checkout():
        items = db.session.execute(select(CartItem).where(CartItem.user_id == session['user_id'])).scalars().all()
        if not items:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('cart'))
        # Lock product rows on PostgreSQL while checking and reducing stock.
        ids = sorted(item.product_id for item in items)
        products_by_id = {p.id: p for p in db.session.execute(select(Product).where(Product.id.in_(ids)).order_by(Product.id).with_for_update()).scalars()}
        for item in items:
            if item.product_id not in products_by_id or item.quantity > products_by_id[item.product_id].stock:
                db.session.rollback()
                flash('Stock changed. Please review your cart.', 'error')
                return redirect(url_for('cart'))
        total = sum((products_by_id[i.product_id].price * i.quantity for i in items), Decimal('0.00'))
        order = Order(user_id=session['user_id'], total=total)
        for item in items:
            product = products_by_id[item.product_id]
            product.stock -= item.quantity
            order.items.append(OrderItem(product_name=product.name, quantity=item.quantity, price=product.price))
            db.session.delete(item)
        db.session.add(order)
        db.session.commit()
        flash(f'Order #{order.id} placed! No payment was collected.', 'success')
        return redirect(url_for('orders'))

    @app.get('/orders')
    @login_required
    def orders():
        own = db.session.execute(select(Order).where(Order.user_id == session['user_id']).order_by(Order.id.desc())).scalars().all()
        return render_template('orders.html', orders=own, heading='Your orders')

    @app.get('/admin')
    @admin_required
    def admin():
        products = db.session.execute(select(Product).order_by(Product.id.desc())).scalars().all()
        orders = db.session.execute(select(Order).order_by(Order.id.desc())).scalars().all()
        return render_template('admin.html', products=products, orders=orders)

    @app.route('/admin/products/new', methods=['GET', 'POST'])
    @admin_required
    def new_product():
        return edit_product(None)

    @app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def edit_product(product_id):
        product = db.get_or_404(Product, product_id) if product_id else Product()
        if request.method == 'POST':
            try:
                name = request.form.get('name', '').strip()[:120]
                description = request.form.get('description', '').strip()
                category = request.form.get('category', '').strip()[:60]
                price = Decimal(request.form.get('price', '')).quantize(Decimal('0.01'))
                stock = int(request.form.get('stock', ''))
                image_url = request.form.get('image_url', '').strip()[:500]
                if not name or not description or not category or price <= 0 or stock < 0 or (image_url and (urlparse(image_url).scheme not in ('https', 'http') or not urlparse(image_url).netloc)):
                    raise ValueError()
            except (ValueError, ArithmeticError):
                flash('Check the product fields, price, stock and image URL.', 'error')
            else:
                product.name, product.description, product.category = name, description, category
                product.price, product.stock, product.image_url = price, stock, image_url
                db.session.add(product)
                db.session.commit()
                flash('Product saved.', 'success')
                return redirect(url_for('admin'))
        return render_template('product_form.html', product=product)

    @app.post('/admin/products/<int:product_id>/delete')
    @admin_required
    def delete_product(product_id):
        product = db.get_or_404(Product, product_id)
        db.session.query(CartItem).filter_by(product_id=product_id).delete()
        db.session.delete(product)
        db.session.commit()
        flash('Product removed.', 'success')
        return redirect(url_for('admin'))

    @app.post('/admin/orders/<int:order_id>/status')
    @admin_required
    def order_status(order_id):
        order = db.get_or_404(Order, order_id)
        status = request.form.get('status')
        if status not in ('Placed', 'Processing', 'Shipped', 'Delivered', 'Cancelled'):
            abort(400)
        order.status = status
        db.session.commit()
        return redirect(url_for('admin'))

    @app.get('/health')
    def health():
        db.session.execute(select(db.literal(1))).scalar()
        return {'status': 'ok'}

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        click.echo('Database ready.')

    @app.cli.command('create-admin')
    @click.option('--email', prompt=True)
    @click.option('--name', prompt=True)
    @click.password_option()
    def create_admin(email, name, password):
        if len(password) < 8:
            raise click.ClickException('Password must have at least 8 characters.')
        email = email.strip().lower()
        if db.session.execute(select(User).where(User.email == email)).scalar_one_or_none():
            raise click.ClickException('Email already exists.')
        db.session.add(User(email=email, name=name.strip(), password_hash=generate_password_hash(password), is_admin=True))
        db.session.commit()
        click.echo('Admin created.')

    @app.cli.command('seed')
    def seed():
        if db.session.execute(select(Product.id).limit(1)).first():
            click.echo('Products already exist.')
            return
        samples = [
            ('Studio headphones', 'Wireless listening with soft ear cushions and a clean sound.', 'Audio', '3499.00', 14, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=900&q=80'),
            ('Minimal desk lamp', 'Warm adjustable light for your desk and late evenings.', 'Home', '2299.00', 18, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=900&q=80'),
            ('Everyday backpack', 'A compact, durable carry for classes and commuting.', 'Lifestyle', '2899.00', 11, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=900&q=80'),
            ('Ceramic coffee cup', 'A comfortable matte finish for your daily ritual.', 'Home', '799.00', 24, 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=900&q=80'),
            ('Portable speaker', 'Small footprint, rich sound, easy Bluetooth pairing.', 'Audio', '4199.00', 9, 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=900&q=80'),
            ('Classic wristwatch', 'Simple details and an easy everyday fit.', 'Lifestyle', '5499.00', 7, 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=900&q=80'),
        ]
        db.session.add_all(Product(name=n, description=d, category=c, price=Decimal(p), stock=s, image_url=i) for n, d, c, p, s, i in samples)
        db.session.commit()
        click.echo('Sample products added.')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
