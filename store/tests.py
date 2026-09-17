from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Usuario


class ArticuloUsadoApiTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email='cliente@example.com',
            username='cliente@example.com',
            password='UnaClaveSegura123!',
            rol=Usuario.ES_CLIENTE,
        )
        self.url = reverse('articulos-usados-list')

    def test_cliente_puede_publicar_y_aparece_en_catalogo_publico(self):
        self.client.force_authenticate(user=self.usuario)
        response = self.client.post(
            self.url,
            {
                'titulo': 'Bicicleta usada',
                'descripcion': 'Bicicleta en buen estado.',
                'precio': '120.00',
                'moneda': 'USD',
                'estado_articulo': 'buen_estado',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['activo'])

        self.client.force_authenticate(user=None)
        public_response = self.client.get(self.url)

        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(len(public_response.data), 1)
        self.assertEqual(public_response.data[0]['titulo'], 'Bicicleta usada')

    def test_mis_articulos_incluye_solo_las_publicaciones_del_usuario(self):
        self.client.force_authenticate(user=self.usuario)
        self.client.post(
            self.url,
            {
                'titulo': 'Artículo propio',
                'descripcion': 'Publicación personal.',
                'precio': '10.00',
                'moneda': 'USD',
                'estado_articulo': 'como_nuevo',
            },
            format='json',
        )

        response = self.client.get(self.url, {'mine': 'true'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vendedor'], self.usuario.id)
