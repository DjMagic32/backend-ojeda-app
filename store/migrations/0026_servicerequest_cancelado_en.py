# Generated manually (no local Django env) on 2026-08-11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0025_articulo_usado'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='cancelado_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
