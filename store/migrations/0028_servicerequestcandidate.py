from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0027_tienda_banner_descripcion_producto_destacado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceRequestCandidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('applied', 'Postulado'), ('rejected', 'Rechazado'), ('selected', 'Seleccionado')], default='applied', max_length=20)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(limit_choices_to={'es_conductor': True}, on_delete=django.db.models.deletion.CASCADE, related_name='service_request_candidates', to='store.usuario')),
                ('service_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidates', to='store.servicerequest')),
            ],
            options={'ordering': ['creado']},
        ),
        migrations.AddConstraint(
            model_name='servicerequestcandidate',
            constraint=models.UniqueConstraint(fields=('service_request', 'driver'), name='unique_service_request_candidate'),
        ),
    ]
