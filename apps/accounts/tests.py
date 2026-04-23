from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .serializers import UserSerializer


User = get_user_model()


class AccountsApiSmokeTests(APITestCase):
	def test_register_endpoint_creates_user(self):
		payload = {
			'username': 'smoke-user',
			'email': 'smoke-user@example.com',
			'first_name': 'Smoke',
			'last_name': 'User',
			'phone_number': '+15551234567',
			'user_type': 'customer',
			'password': 'StrongPass123!',
			'password_confirm': 'StrongPass123!',
		}

		response = self.client.post('/api/accounts/register/', payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(User.objects.filter(email='smoke-user@example.com').exists())

	def test_user_serializer_requires_password_on_create(self):
		serializer = UserSerializer(
			data={
				'username': 'no-pass',
				'email': 'no-pass@example.com',
				'user_type': 'customer',
			}
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('password', serializer.errors)
