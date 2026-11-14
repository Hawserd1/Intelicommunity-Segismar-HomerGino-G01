# Intelicommunity-Segismar-HomerGino-G01

## Local setup

1. Install the project dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set your Supabase PostgreSQL connection details and replace `DJANGO_SECRET_KEY` with a generated key:

   ```powershell
   .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Keep `.env` private; it is excluded from Git. Put database credentials and Supabase keys there, not in source files. Only commit `.env.example`, and keep its values as placeholders. Use `DJANGO_DEBUG=True` only for local development.

3. Create and apply database migrations:

   ```powershell
   .\.venv\Scripts\python.exe manage.py makemigrations accounts
   .\.venv\Scripts\python.exe manage.py migrate
   .\.venv\Scripts\python.exe manage.py createsuperuser
   ```

4. Start the development server:

   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```

The account feature includes registration, login/logout, a protected profile, and separate Standard User, Moderator, and Administrator dashboards. Users can open only the dashboard matching their application role. Field Expert and Creative Professional describe a Standard User's interests or expertise; they are not privileged roles. An Administrator application role alone does not grant Django admin access, which is independently controlled by Django's `is_staff`, `is_superuser`, and model permissions.

Dashboard cards link to planned features. Until implemented, those links show a friendly explanation with HTTP 501; unknown feature links return HTTP 404. The dashboards are a UI foundation, not implementations of the linked community features.