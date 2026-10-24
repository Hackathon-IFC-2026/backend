from django.test import SimpleTestCase, Client


class CorsTests(SimpleTestCase):
    def test_preflight_accepts_new_frontend_origin_and_jwt_header(self):
        response = Client().options(
            '/api/projetos/',
            HTTP_ORIGIN='https://novo-frontend.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='PATCH',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        self.assertIn('PATCH', response.headers['Access-Control-Allow-Methods'])
        self.assertIn('authorization', response.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', response.headers)

    def test_any_origin_still_requires_authentication(self):
        response = Client().get(
            '/api/projetos/', HTTP_ORIGIN='https://novo-frontend.example',
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
