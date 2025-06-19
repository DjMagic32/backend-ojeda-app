import json
from django.test import TestCase
from django.urls import reverse
from graphene_django.utils.testing import GraphQLTestCase
from backend_ojeda.schema import schema # Main schema
from .models import Usuario, Categoria # Import models needed for testing
from rest_framework_simplejwt.tokens import RefreshToken

class GraphQLAPITestCase(GraphQLTestCase):
    GRAPHQL_SCHEMA = schema
    # Attempt to reverse the 'graphql' URL name.
    # If this fails, it might indicate the URL is not yet defined or named 'graphql'.
    # For now, we'll proceed assuming it's correct as per instructions.
    # A more robust approach might involve try-except or ensuring URL setup first.
    GRAPHQL_URL = reverse('graphql')

    def setUp(self):
        # Create any initial data needed for tests
        self.test_user = Usuario.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.category1 = Categoria.objects.create(nombre="Electronics", descripcion="Gadgets and devices")
        # Add more setup data as needed for other tests

    def test_query_all_categorias(self):
        response = self.query(
            '''
            query {
              allCategorias {
                id
                nombre
              }
            }
            '''
        )
        self.assertResponseNoErrors(response)
        content = json.loads(response.content)
        # Add assertions to check the content, e.g., number of categories, names, etc.
        self.assertEqual(len(content['data']['allCategorias']), 1)
        self.assertEqual(content['data']['allCategorias'][0]['nombre'], "Electronics")

    def test_query_categoria_by_id(self):
        response = self.query(
            f'''
            query {{
              categoriaById(id: {self.category1.id}) {{
                id
                nombre
              }}
            }}
            '''
        )
        self.assertResponseNoErrors(response)
        content = json.loads(response.content)
        self.assertEqual(content['data']['categoriaById']['nombre'], self.category1.nombre)

    def test_query_me_authenticated(self):
        # Obtain JWT token for the test user
        refresh = RefreshToken.for_user(self.test_user)
        auth_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}',
        }

        response = self.query(
            '''
            query {
              me {
                id
                username
                email
              }
            }
            ''',
            headers=auth_headers
        )
        self.assertResponseNoErrors(response)
        content = json.loads(response.content)
        self.assertEqual(content['data']['me']['username'], self.test_user.username)

    def test_query_me_unauthenticated(self):
        response = self.query(
            '''
            query {
              me {
                id
                username
                email
              }
            }
            '''
        )
        # Expect an error because the user is not authenticated
        self.assertResponseHasErrors(response)
        content = json.loads(response.content)
        self.assertIsNotNone(content['errors'])
        # Depending on how Graphene handles exceptions (directly or wraps them),
        # the exact error message structure might vary.
        # We expect the message we defined: "Authentication required!"
        self.assertTrue(any(err.get('message') == "Authentication required!" for err in content['errors']))


    def test_mutation_create_usuario(self):
        response = self.query(
            '''
            mutation CreateUser($input: UsuarioInput!) {
              createUsuario(input: $input) {
                usuario {
                  id
                  username
                  email
                  rol
                }
              }
            }
            ''',
            op_name='CreateUser',
            variables={'input': {'email': 'newuser@example.com', 'username': 'newuser', 'password': 'password123', 'rol': 'CLIENTE'}}
        )
        self.assertResponseNoErrors(response)
        content = json.loads(response.content)
        self.assertEqual(content['data']['createUsuario']['usuario']['email'], 'newuser@example.com')
        self.assertTrue(Usuario.objects.filter(email='newuser@example.com').exists())
