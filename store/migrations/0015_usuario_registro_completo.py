from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0014_tienda_ubicacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='registro_completo',
            field=models.BooleanField(default=True),
        ),
    ]
