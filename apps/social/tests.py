from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class SocialApiSmokeTests(APITestCase):
	def test_authenticated_user_can_list_notifications(self):
		user = User.objects.create_user(
			email='social-user@example.com',
			username='social-user',
			password='SocialPass123!',
			user_type='customer',
		)
		self.client.force_authenticate(user=user)

		response = self.client.get('/api/social/notifications/')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsInstance(response.data, list)
