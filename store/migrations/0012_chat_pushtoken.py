from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_usuario_avatar'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacion',
            name='data',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='notificacion',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('favorite', 'Favorito'),
                    ('order', 'Orden'),
                    ('service', 'Servicio'),
                    ('message', 'Mensaje'),
                    ('general', 'General'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('participantes', models.ManyToManyField(related_name='conversaciones', to=settings.AUTH_USER_MODEL)),
                ('producto', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name='conversaciones', to='store.productotienda')),
            ],
            options={'ordering': ['-actualizado']},
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contenido', models.TextField()),
                ('leido', models.BooleanField(default=False)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='mensajes_enviados', to=settings.AUTH_USER_MODEL)),
                ('conversation', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='mensajes', to='store.conversation')),
            ],
            options={
                'ordering': ['creado'],
                'indexes': [models.Index(fields=['conversation', 'creado'], name='store_messa_convers_idx')],
            },
        ),
        migrations.CreateModel(
            name='ExpoPushToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=255, unique=True)),
                ('plataforma', models.CharField(blank=True, max_length=20, null=True)),
                ('creado', models.DateTimeField(auto_now_add=True)),
                ('actualizado', models.DateTimeField(auto_now=True)),
                ('usuario', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='push_tokens', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
