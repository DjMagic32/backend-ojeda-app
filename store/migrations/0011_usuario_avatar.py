from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0010_notificacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),
    ]
