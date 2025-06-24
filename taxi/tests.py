from django.urls import reverse
from django.utils import timezone
from django.test import override_settings # Import override_settings
from rest_framework import status, serializers as drf_serializers # Added for ValidationError
from rest_framework.test import APITestCase, APIClient
from store.models import Usuario
from .models import DriverProfile, Vehicle, ServiceRequest, TaxiRide
from .serializers import DriverProfileSerializer, VehicleSerializer, TaxiRideRequestInputSerializer
from rest_framework.exceptions import ValidationError


# Helper to create users
def create_user(email, username, password, rol, **extra_fields):
    user = Usuario.objects.create_user(
        email=email,
        username=username,
        password=password,
        rol=rol,
        **extra_fields
    )
    return user

class UserModelModificationTests(APITestCase):
    def test_user_can_have_conductor_role(self):
        user = create_user("conductor@test.com", "testconductor", "password123", Usuario.ES_CONDUCTOR)
        self.assertEqual(user.rol, Usuario.ES_CONDUCTOR)

class DriverProfileModelTests(APITestCase):
    def setUp(self):
        self.driver_user = create_user("driver@example.com", "driver1", "password", Usuario.ES_CONDUCTOR)

    def test_driver_profile_creation(self):
        profile = DriverProfile.objects.create(user=self.driver_user)
        self.assertEqual(profile.user, self.driver_user)
        self.assertEqual(str(profile), f"Driver: {self.driver_user.username}")
        self.assertEqual(profile.availability_status, DriverProfile.AVAILABILITY_STATUS_CHOICES[1][0]) # OFFLINE

class VehicleModelTests(APITestCase):
    def setUp(self):
        self.driver_user = create_user("vehicledriver@example.com", "driverwithcar", "password", Usuario.ES_CONDUCTOR)
        self.driver_profile = DriverProfile.objects.create(user=self.driver_user)

    def test_vehicle_creation(self):
        vehicle = Vehicle.objects.create(
            driver=self.driver_profile,
            type='SEDAN',
            make='Toyota',
            model='Camry',
            license_plate='TEST1234'
        )
        self.assertEqual(vehicle.driver, self.driver_profile)
        self.assertEqual(vehicle.license_plate, 'TEST1234')
        self.assertEqual(str(vehicle), "Toyota Camry (TEST1234)")


class DriverProfileSerializerTests(APITestCase):
    def setUp(self):
        self.driver_user = create_user("serializerdriver@example.com", "serializerdriver", "password", Usuario.ES_CONDUCTOR)
        self.client_user = create_user("serializerclient@example.com", "serializerclient", "password", Usuario.ES_CLIENTE)
        self.profile_data = {
            "availability_status": "ONLINE",
            "current_latitude": 10.123456,
            "current_longitude": -60.654321
        }
        # Mock request context for serializer
        self.request_mock = type('Request', (), {'user': self.driver_user})


    def test_driver_profile_serializer_valid(self):
        serializer = DriverProfileSerializer(data=self.profile_data, context={'request': self.request_mock})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        profile = serializer.save(user=self.request_mock.user) # Pass user to save
        self.assertEqual(profile.user, self.driver_user)
        self.assertEqual(profile.availability_status, "ONLINE")

    def test_driver_profile_serializer_create_non_conductor(self):
        self.request_mock.user = self.client_user # Change context user
        serializer = DriverProfileSerializer(data=self.profile_data, context={'request': self.request_mock})
        # Serializer itself might be valid based on fields, but save() should fail
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaisesMessage(ValidationError, "User must have the 'CONDUCTOR' role to create a driver profile."): # Changed here
            serializer.save(user=self.request_mock.user) # Pass user to save


    def test_driver_profile_serializer_update(self):
        profile = DriverProfile.objects.create(user=self.driver_user)
        update_data = {"availability_status": "BUSY"}
        serializer = DriverProfileSerializer(instance=profile, data=update_data, partial=True, context={'request': self.request_mock})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_profile = serializer.save()
        self.assertEqual(updated_profile.availability_status, "BUSY")


class VehicleSerializerTests(APITestCase):
    def setUp(self):
        self.driver_user = create_user("vehserializerdriver@example.com", "vehserializerdriver", "password", Usuario.ES_CONDUCTOR)
        self.driver_profile = DriverProfile.objects.create(user=self.driver_user)
        self.vehicle_data = {
            "type": "SUV",
            "make": "Honda",
            "model": "CRV",
            "license_plate": "HONDA1",
            "is_active": True
        }
        # self.request_mock = type('Request', (), {'user': self.driver_user, 'driver_profile': self.driver_profile})


    def test_vehicle_serializer_valid_create(self):
        # Context for VehicleSerializer doesn't strictly need 'request' if driver is passed in save()
        serializer = VehicleSerializer(data=self.vehicle_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        vehicle = serializer.save(driver=self.driver_profile)
        self.assertEqual(vehicle.make, "Honda")

    def test_vehicle_serializer_duplicate_license_plate(self):
        Vehicle.objects.create(driver=self.driver_profile, license_plate="DUPLICATELP", make="Test", model="Test")
        data = self.vehicle_data.copy()
        data["license_plate"] = "DUPLICATELP"
        serializer = VehicleSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("license_plate", serializer.errors)
        self.assertIn("already exists", serializer.errors['license_plate'][0])


@override_settings(SECURE_SSL_REDIRECT=False)
class DriverProfileViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = create_user("driverview@example.com", "driverview", "testpass", Usuario.ES_CONDUCTOR)
        self.other_driver_user = create_user("otherdriver@example.com", "otherdriver", "testpass", Usuario.ES_CONDUCTOR)
        self.client_user = create_user("clientview@example.com", "clientview", "testpass", Usuario.ES_CLIENTE)
        self.admin_user = create_user("adminview@example.com", "adminview", "testpass", Usuario.ES_TIENDA, is_staff=True)

        self.driver_profile_data = {
            "availability_status": "ONLINE",
            "current_latitude": 10.0,
            "current_longitude": 20.0
        }
        self.profile_list_url = reverse('taxi:driverprofile-list')

    def test_create_driver_profile_authenticated_driver(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(self.profile_list_url, self.driver_profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(DriverProfile.objects.count(), 1)
        self.assertEqual(DriverProfile.objects.get().user, self.driver_user)

    def test_create_driver_profile_authenticated_client(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(self.profile_list_url, self.driver_profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_driver_profile_unauthenticated(self):
        response = self.client.post(self.profile_list_url, self.driver_profile_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_own_driver_profile(self):
        profile = DriverProfile.objects.create(user=self.driver_user, **self.driver_profile_data)
        self.client.force_authenticate(user=self.driver_user)
        detail_url = reverse('taxi:driverprofile-detail', kwargs={'pk': profile.pk})
        response = self.client.get(detail_url, format='json', follow=True) # Added follow=True
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], self.driver_user.pk)

    def test_retrieve_other_driver_profile_as_driver_permission_denied(self):
        DriverProfile.objects.create(user=self.driver_user)
        other_profile = DriverProfile.objects.create(user=self.other_driver_user)
        self.client.force_authenticate(user=self.driver_user)
        detail_url = reverse('taxi:driverprofile-detail', kwargs={'pk': other_profile.pk})
        response = self.client.get(detail_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Changed to 404


    def test_update_own_driver_profile(self):
        profile = DriverProfile.objects.create(user=self.driver_user, availability_status='OFFLINE')
        self.client.force_authenticate(user=self.driver_user)
        detail_url = reverse('taxi:driverprofile-detail', kwargs={'pk': profile.pk})
        update_data = {"availability_status": "ONLINE"}
        response = self.client.patch(detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        profile.refresh_from_db()
        self.assertEqual(profile.availability_status, "ONLINE")

    def test_set_availability_action(self):
        profile = DriverProfile.objects.create(user=self.driver_user, availability_status='OFFLINE')
        self.client.force_authenticate(user=self.driver_user)
        availability_url = reverse('taxi:driverprofile-set-availability', kwargs={'pk': profile.pk})
        update_data = {"availability_status": "BUSY"}
        response = self.client.patch(availability_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        profile.refresh_from_db()
        self.assertEqual(profile.availability_status, "BUSY")

@override_settings(SECURE_SSL_REDIRECT=False)
class VehicleViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = create_user("vehicledriverview@example.com", "vehdriverview", "testpass", Usuario.ES_CONDUCTOR)
        self.driver_profile = DriverProfile.objects.create(user=self.driver_user)
        self.client.force_authenticate(user=self.driver_user)

        self.vehicle_data = {
            "type": "SEDAN", "make": "Toyota", "model": "Corolla", "license_plate": "CAR1"
        }
        self.vehicles_list_url = reverse('taxi:vehicle-list')

    def test_create_vehicle(self):
        response = self.client.post(self.vehicles_list_url, self.vehicle_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(Vehicle.objects.get().driver, self.driver_profile)

    def test_list_own_vehicles(self):
        Vehicle.objects.create(driver=self.driver_profile, **self.vehicle_data)
        response = self.client.get(self.vehicles_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_own_vehicle(self):
        vehicle = Vehicle.objects.create(driver=self.driver_profile, **self.vehicle_data)
        detail_url = reverse('taxi:vehicle-detail', kwargs={'pk': vehicle.pk})
        response = self.client.get(detail_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['license_plate'], "CAR1")

    def test_update_own_vehicle(self):
        vehicle = Vehicle.objects.create(driver=self.driver_profile, **self.vehicle_data)
        detail_url = reverse('taxi:vehicle-detail', kwargs={'pk': vehicle.pk})
        update_data = {"make": "Honda"}
        response = self.client.patch(detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.make, "Honda")

    def test_delete_own_vehicle(self):
        vehicle = Vehicle.objects.create(driver=self.driver_profile, **self.vehicle_data)
        detail_url = reverse('taxi:vehicle-detail', kwargs={'pk': vehicle.pk})
        response = self.client.delete(detail_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Vehicle.objects.count(), 0)

@override_settings(SECURE_SSL_REDIRECT=False)
class TaxiRideRequestViewTests(APITestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.client_user = create_user("clientreq@example.com", "clientreq", "testpass", Usuario.ES_CLIENTE)
        self.driver_user = create_user("driverreq@example.com", "driverreq", "testpass", Usuario.ES_CONDUCTOR)

        self.request_url = reverse('taxi:taxi-ride-request')
        self.ride_data = {
            "pickup_latitude": 10.0, "pickup_longitude": 10.0, "pickup_address_text": "123 Pickup St",
            "dropoff_latitude": 11.0, "dropoff_longitude": 11.0, "dropoff_address_text": "456 Dropoff Ave",
            "number_of_passengers": 1
        }

    def test_create_taxi_ride_request_as_client(self):
        self.client_api.force_authenticate(user=self.client_user)
        response = self.client_api.post(self.request_url, self.ride_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(TaxiRide.objects.count(), 1)
        sr = ServiceRequest.objects.first()
        self.assertEqual(sr.customer, self.client_user)
        self.assertEqual(sr.service_type, "TAXI")
        self.assertEqual(sr.status, "PENDING_ASSIGNMENT")

    def test_create_taxi_ride_request_as_driver(self):
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.post(self.request_url, self.ride_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_taxi_ride_request_unauthenticated(self):
        response = self.client_api.post(self.request_url, self.ride_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_taxi_ride_invalid_data(self):
        self.client_api.force_authenticate(user=self.client_user)
        invalid_data = self.ride_data.copy()
        del invalid_data["pickup_latitude"]
        response = self.client_api.post(self.request_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(SECURE_SSL_REDIRECT=False)
class AvailableTaxiRequestsViewTests(APITestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.driver_user = create_user("driveravail@example.com", "driveravail", "testpass", Usuario.ES_CONDUCTOR)
        self.driver_profile = DriverProfile.objects.create(user=self.driver_user, availability_status="ONLINE")
        self.client_user = create_user("clientavail@example.com", "clientavail", "testpass", Usuario.ES_CLIENTE)

        ServiceRequest.objects.create(
            customer=self.client_user, service_type="TAXI", status="PENDING_ASSIGNMENT",
            pickup_latitude=1.0, pickup_longitude=1.0, pickup_address_text="P1",
            dropoff_latitude=2.0, dropoff_longitude=2.0, dropoff_address_text="D1"
        )
        self.available_url = reverse('taxi:available-taxi-rides')

    def test_list_available_requests_as_online_driver(self):
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.get(self.available_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)

    def test_list_available_requests_as_offline_driver(self):
        self.driver_profile.availability_status = "OFFLINE"
        self.driver_profile.save()
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.get(self.available_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_available_requests_as_client(self):
        self.client_api.force_authenticate(user=self.client_user)
        response = self.client_api.get(self.available_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(SECURE_SSL_REDIRECT=False)
class AcceptTaxiRequestViewTests(APITestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.driver_user = create_user("driveraccept@example.com", "driveraccept", "testpass", Usuario.ES_CONDUCTOR)
        self.driver_profile = DriverProfile.objects.create(user=self.driver_user, availability_status="ONLINE")
        self.client_user = create_user("clientaccept@example.com", "clientaccept", "testpass", Usuario.ES_CLIENTE)

        self.service_request = ServiceRequest.objects.create(
            customer=self.client_user, service_type="TAXI", status="PENDING_ASSIGNMENT",
            pickup_latitude=1.0, pickup_longitude=1.0, pickup_address_text="P1",
            dropoff_latitude=2.0, dropoff_longitude=2.0, dropoff_address_text="D1"
        )
        self.accept_url = reverse('taxi:accept-taxi-ride', kwargs={'pk': self.service_request.pk})

    def test_accept_request_as_online_driver(self):
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.patch(self.accept_url, format='json') # Changed to PATCH
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.service_request.refresh_from_db()
        self.driver_profile.refresh_from_db()
        self.assertEqual(self.service_request.status, ServiceRequest.STATUS_CHOICES[1][0]) # DRIVER_ASSIGNED
        self.assertEqual(self.service_request.assigned_driver, self.driver_profile)
        self.assertEqual(self.driver_profile.availability_status, DriverProfile.AVAILABILITY_STATUS_CHOICES[2][0]) # BUSY
        self.assertIsNotNone(self.service_request.assigned_at)

    def test_accept_request_as_offline_driver(self):
        self.driver_profile.availability_status = "OFFLINE"
        self.driver_profile.save()
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.patch(self.accept_url, format='json') # Changed to PATCH
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_accept_already_assigned_request_returns_404(self):
        other_driver_user = create_user("otherd@example.com", "otherd", "pw", Usuario.ES_CONDUCTOR)
        other_profile = DriverProfile.objects.create(user=other_driver_user, availability_status="ONLINE")
        self.service_request.assigned_driver = other_profile
        self.service_request.status = ServiceRequest.STATUS_CHOICES[1][0] # DRIVER_ASSIGNED
        self.service_request.save()

        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.patch(self.accept_url, format='json') # Changed to PATCH
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_non_existent_request(self):
        non_existent_url = reverse('taxi:accept-taxi-ride', kwargs={'pk': 9999})
        self.client_api.force_authenticate(user=self.driver_user)
        response = self.client_api.patch(non_existent_url, format='json') # Changed to PATCH
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
