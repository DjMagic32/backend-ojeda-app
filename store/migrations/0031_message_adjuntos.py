from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0030_lugar_ciudad_traki'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='adjunto',
            field=models.FileField(blank=True, null=True, upload_to='chat_adjuntos/'),
        ),
        migrations.AddField(
            model_name='message',
            name='adjunto_nombre',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='message',
            name='adjunto_tipo',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
