from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_storeorder'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreOrderReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(blank=True, null=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review', to='store.storeorder')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='store.productotienda')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_order_reviews', to='store.usuario')),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
    ]
