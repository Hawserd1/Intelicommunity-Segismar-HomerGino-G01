from django.db import migrations, models


def convert_legacy_roles(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(
        role__in=('FIELD_EXPERT', 'CREATIVE_PROFESSIONAL', 'COMMUNITY_MEMBER')
    ).update(role='STANDARD_USER')


def restore_legacy_roles(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(role='STANDARD_USER').update(role='COMMUNITY_MEMBER')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(convert_legacy_roles, restore_legacy_roles),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('STANDARD_USER', 'Standard User'),
                    ('MODERATOR', 'Moderator'),
                    ('ADMINISTRATOR', 'Administrator'),
                ],
                default='STANDARD_USER',
                max_length=24,
            ),
        ),
    ]
