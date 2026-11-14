from django.db import migrations
from django.utils.text import slugify


STARTER_SECTIONS = (
    ('Programming', 'Questions, ideas, and learning about software and programming.'),
    ('Engineering', 'Share practical questions and knowledge across engineering fields.'),
    ('Cooking', 'Recipes, techniques, and helpful kitchen know-how.'),
    ('Music', 'Talk about making, learning, performing, and enjoying music.'),
    ('Language', 'Practice languages and share tips about communication.'),
)


def create_starter_sections(apps, schema_editor):
    CommunitySection = apps.get_model('community', 'CommunitySection')
    for name, description in STARTER_SECTIONS:
        CommunitySection.objects.get_or_create(
            name=name,
            defaults={
                'slug': slugify(name),
                'description': description,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_starter_sections, migrations.RunPython.noop),
    ]
