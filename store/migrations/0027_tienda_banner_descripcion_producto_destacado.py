# Generated manually (no local Django env) on 2026-08-18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0026_servicerequest_cancelado_en'),
    ]

    operations = [
        migrations.AddField(
            model_name='tienda',
            name='descripcion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tienda',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to='banners/'),
        ),
        migrations.AddField(
            model_name='productotienda',
            name='destacado',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name='productotienda',
            options={'ordering': ['-destacado', '-id']},
        ),
    ]
