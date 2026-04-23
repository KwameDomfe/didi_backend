from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class OrdersApiSmokeTests(APITestCase):
	def test_authenticated_user_can_fetch_current_cart(self):
		user = User.objects.create_user(
			email='orders-user@example.com',
			username='orders-user',
			password='OrdersPass123!',
			user_type='customer',
		)
		self.client.force_authenticate(user=user)

		response = self.client.get('/api/orders/cart/current/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn('id', response.data)
