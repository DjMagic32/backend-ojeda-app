from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_storeorderreview'),
    ]

    operations = [
        migrations.CreateModel(
            name='StoreOrderSellerReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(blank=True, null=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('comprador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_order_seller_reviews', to='store.usuario')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='seller_review', to='store.storeorder')),
                ('tienda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_reviews', to='store.tienda')),
            ],
            options={
                'ordering': ['-creado'],
            },
        ),
    ]
