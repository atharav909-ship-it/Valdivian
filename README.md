# Valdivian

A small Flask e-commerce store with a polished responsive storefront, registration/login, search and categories, product pages, cart, demo checkout, order history, and an admin dashboard for products and order status. Checkout places an order and reduces stock; it does **not** collect payments.

## Requirements

Python 3.10+ and Git. Windows PowerShell commands are shown first; macOS/Linux alternatives follow.

## Run locally (Windows PowerShell)

From this extracted `valdivian` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = "replace-this-with-a-long-random-string"
python -m flask --app app init-db
python -m flask --app app seed
python -m flask --app app create-admin
python -m flask --app app run --debug
```

Open http://127.0.0.1:5000 . The `create-admin` command prompts for an email, name and password (at least eight characters). Register a separate customer account through the website. If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process RemoteSigned` in that same terminal, then activate again.

## Run locally (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY='replace-this-with-a-long-random-string'
python -m flask --app app init-db
python -m flask --app app seed
python -m flask --app app create-admin
python -m flask --app app run --debug
```

The default database is SQLite in `instance/valdivian.db`. `seed` is safe to rerun; it only inserts sample products into an empty catalog. Sample images load from Unsplash over the network, while product cards still work without them.

## Run tests

```bash
python -m pytest -q
```

## GitHub and CI/CD

Create a **new empty repository** on GitHub, then from the `valdivian` directory:

```bash
git init
git add .
git commit -m "Build Valdivian storefront and automated tests"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/valdivian.git
git push -u origin main
```

Change `YOUR_USERNAME` to your own username. You can check actual commits with `git rev-list --count HEAD`. The Actions page is `https://github.com/YOUR_USERNAME/valdivian/actions`. Each push or pull request to `main` runs pytest. The deployment job runs after tests pass on pushes to `main`.

## Live deployment with Render

1. Push this folder to GitHub. In Render, select **New → Blueprint** and connect the repository; `render.yaml` defines a Flask web service plus PostgreSQL. Review the plan and pricing displayed in Render before creating resources. Render and GitHub screens may change over time.
2. The Blueprint sets `SECRET_KEY` and `DATABASE_URL`. Its web service runs `flask --app app init-db` before deployment and `gunicorn 'app:app'` to serve requests.
3. In the Render web service, create a deploy hook URL. In GitHub repository **Settings → Secrets and variables → Actions**, add the secret `RENDER_DEPLOY_HOOK_URL` with that value. Do not commit it. The Blueprint disables Render automatic deployments so the Actions test gate controls subsequent deploys.
4. Trigger a new push to `main` or run the workflow from its Actions page. When tests pass, the deploy job calls Render. Check the Render deployment result and `/health` URL; the webhook starts a deploy but GitHub Actions does not wait for Render to finish.
5. Populate the live catalog with a one-time shell command in the Render web service: `flask --app app seed`. Create the admin there using `flask --app app create-admin` and enter credentials at the prompts. If a shell is unavailable on the chosen plan, temporarily run these commands through a controlled one-off job or add products through an admin account created with a secure provisioning method. Never hard-code admin credentials in the repository.

If you prefer a manually created web service instead of a Blueprint, set its build command to `pip install -r requirements.txt`, start command to `gunicorn 'app:app'`, and provide `SECRET_KEY` and a persistent PostgreSQL `DATABASE_URL`. Run `flask --app app init-db` once before the first web request.

## Submission fields

- **Technology:** Python, Flask, Flask-SQLAlchemy, HTML/CSS, PostgreSQL (live), SQLite (local)
- **CI/CD:** GitHub Actions; optional Render deploy hook configured as above
- **Repository:** `https://github.com/YOUR_USERNAME/valdivian`
- **Live app:** Your actual Render web service URL
- **Pipeline:** `https://github.com/YOUR_USERNAME/valdivian/actions`
- **Commits:** `git rev-list --count HEAD` (use the real number)

These links and the commit count become real after you create the repository and deploy it. The ZIP itself is a starting snapshot, so it does not contain an invented Git history.
