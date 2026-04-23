from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Cuisine, Restaurant


User = get_user_model()


class RestaurantsApiSmokeTests(APITestCase):
	def test_public_restaurants_list_returns_data(self):
		owner = User.objects.create_user(
			email='vendor@example.com',
			username='vendor-user',
			password='VendorPass123!',
			user_type='vendor',
		)
		cuisine = Cuisine.objects.create(name='Fusion', description='Fusion cuisine')
		Restaurant.objects.create(
			owner=owner,
			name='Smoke Bistro',
			description='Test restaurant',
			cuisine=cuisine,
			address='123 Main Street',
			phone_number='+15550001111',
			email='restaurant@example.com',
			price_range='$$',
			opening_hours={'mon': '09:00-17:00'},
			features=['delivery'],
		)

		response = self.client.get('/api/restaurants/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertGreaterEqual(len(response.data.get('results', response.data)), 1)
