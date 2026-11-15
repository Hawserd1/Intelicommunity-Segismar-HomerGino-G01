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
   .\.venv\Scripts\python.exe manage.py makemigrations
   .\.venv\Scripts\python.exe manage.py migrate
   .\.venv\Scripts\python.exe manage.py createsuperuser
   ```

4. Start the development server:

   ```powershell
   .\.venv\Scripts\python.exe manage.py runserver
   ```

The account feature includes registration, login/logout, a protected profile, and separate Standard User, Moderator, and Administrator dashboards. Users can open only the dashboard matching their application role. Field Expert and Creative Professional describe a Standard User's interests or expertise; they are not privileged roles. An Administrator application role alone does not grant Django admin access, which is independently controlled by Django's `is_staff`, `is_superuser`, and model permissions.

Community sections, section following, discussions, replies, discussion tags, voting, and content reports are available from the dashboard. Search sections by name or description and sort by name, recency, or popularity (followers, then discussion count). Search discussions by title, body, section, author, or tag; filter by section or tag; and sort by newest, oldest, or most discussed (reply count). Signed-in users can upvote or downvote discussions and individual replies, change their vote, or remove it by selecting the same vote again; each user can have at most one vote per item. Vote totals are visible to everyone. Members can report discussions or replies for moderator review; moderators can mark reports reviewed or dismissed and view summaries of report counts, most-reported users, and discussions per section. Reply authors can edit their own replies. The initial migration seeds Programming, Engineering, Cooking, Music, and Language sections; administrators can add more sections through Django admin. Users can browse sections and discussions, while signing in is required to follow a section, post, reply, vote, or report content. Authors can edit or delete their discussions; moderators and application administrators can also manage discussions. Discussion authors can enter up to five comma-separated tags; tags are normalized and reused, and each tag links to discussions using it. Other dashboard cards link to planned features and show a friendly HTTP 501 page until implemented; unknown feature links return HTTP 404.