# Intelicommunity-Segismar-HomerGino-G01

## Local setup

1. Install the project dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and replace `DJANGO_SECRET_KEY` with a generated key:

   ```powershell
   .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Keep `.env` private; it is excluded from Git. Put any database credentials or Supabase keys there too, not in source files. Only commit `.env.example`, and keep its values as placeholders. Use `DJANGO_DEBUG=True` only for local development.

3. Start the development server:

   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```