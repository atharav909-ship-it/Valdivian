# Valdivian

Valdivian is a Flask-based e-commerce web application developed as a university CI/CD project. It includes a responsive storefront, user registration and login, product search and categories, individual product pages, a shopping cart, demo checkout, order history, and role-protected administrator functionality.

Checkout creates an order and reduces product stock. The application is intended for demonstration purposes and does **not** process real payments.

## Features

- User registration and login
- Secure password hashing
- Session-based authentication
- Product catalogue
- Product search and category filtering
- Individual product pages
- Shopping cart
- Stock validation
- Demo checkout
- Order history
- Admin dashboard
- Product management
- Order status management
- CSRF protection
- Automated testing

## Technology Stack

### Backend
- Python
- Flask
- Flask-SQLAlchemy
- SQLAlchemy

### Frontend
- HTML
- CSS
- Jinja2

### Database
- SQLite for local development
- PostgreSQL for production

### Testing and Deployment
- Pytest
- GitHub Actions
- Render
- Gunicorn

## Requirements

- Python 3.10+
- Git
- pip

## Run Locally — Windows PowerShell

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Set a development secret key:

```powershell
$env:SECRET_KEY = "replace-this-with-a-long-random-string"
```

Initialize the database:

```powershell
python -m flask --app app init-db
```

Populate the database with sample products:

```powershell
python -m flask --app app seed
```

Run the application:

```powershell
python -m flask --app app run --debug
```

Open:

`http://127.0.0.1:5000`

If PowerShell blocks virtual environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

and activate the environment again.

## Run Locally — macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY='replace-this-with-a-long-random-string'
python -m flask --app app init-db
python -m flask --app app seed
python -m flask --app app run --debug
```

The default local database uses SQLite.

Sample product images are loaded over the network. Product cards remain functional if an external image cannot be loaded.

## Administrator Access

Administrator functionality is protected using role-based authorization.

An existing local user can be promoted using the Flask CLI command:

```bash
flask --app app make-admin
```

The command requests the user's email and changes the account's administrator status.

Administrator privileges are not available through public registration.

## Automated Testing

The project includes automated tests using Pytest.

Run the tests locally with:

```bash
python -m pytest -q
```

The test suite covers important application functionality including authentication, products, cart operations, checkout, stock validation, CSRF protection, and administrator authorization.

## CI/CD Pipeline

GitHub Actions is used for continuous integration and automated deployment.

Whenever code is pushed to the `main` branch, GitHub Actions automatically:

1. Checks out the latest source code.
2. Configures the Python environment.
3. Installs the project dependencies.
4. Executes the automated Pytest test suite.
5. If the tests pass, triggers the Render deploy hook.
6. Render deploys the latest version of the application.

If the automated tests fail, the deployment job does not run. This prevents a failing version from being deployed through the CI/CD pipeline.

The workflow configuration is stored in:

```text
.github/workflows/ci-cd.yml

This ensures that changes pushed to the repository are automatically tested before deployment-related actions are performed.

## Deployment

Valdivian is deployed as a Render Web Service.

The production architecture is:

```text
Browser
   ↓
Render Web Service
   ↓
Gunicorn
   ↓
Flask
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

SQLite is used during local development, while the deployed application uses PostgreSQL for persistent production data.

The Render service uses:

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app
```

Environment variables are used for sensitive and environment-specific configuration, including:

- `SECRET_KEY`
- `DATABASE_URL`

These values are configured on the deployment platform and are not committed to the public GitHub repository.

## Project Structure

```text
Valdivian/
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml
│
├── static/
├── templates/
├── tests/
│
├── app.py
├── render.yaml
├── requirements.txt
├── .gitignore
└── README.md
```

## Development and Deployment Workflow

```text
Developer
    ↓
Git Commit
    ↓
Git Push
    ↓
GitHub Repository
    ↓
GitHub Actions
    ↓
Automated Tests
    ↓
Render Deployment
    ↓
Live Application
```

This workflow demonstrates the use of version control, automated testing, continuous integration, and cloud deployment in a complete web application.

## Security

Valdivian includes several basic security measures:

- Password hashing
- Session-based authentication
- CSRF protection
- Role-based administrator authorization
- Server-side stock validation
- Environment-based configuration for secrets

Sensitive credentials and production database connection information are not stored in the repository.

## Project Links

**GitHub Repository:**  
https://github.com/atharav909-ship-it/Valdivian

**Live Application:**  
https://valdivian.onrender.com/

**GitHub Actions Pipeline:**  
https://github.com/atharav909-ship-it/Valdivian/actions

## Project Purpose

Valdivian was developed as a university project demonstrating the implementation of a web application together with Git version control, automated testing, GitHub Actions CI/CD concepts, and cloud deployment using Render.
