import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from name_nation.api.models import NameRequest, Country, NameCountry


@pytest.mark.django_db
class TestNamesAPI:
    """
    Tests for the /names/ API endpoint.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize the API client before each test."""
        self.client = APIClient()

    def test_missing_name_param(self):
        """
        Ensure the API returns 400 Bad Request
        when 'name' query parameter is missing.
        """
        url = reverse("names-api")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_name_not_found_external_api(self):
        """
        Simulate external API returning no country data
        and ensure API returns 404 Not Found.
        """
        url = reverse("names-api")
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"country": []}

            response = self.client.get(url, {"name": "unknownname"})
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "error" in response.data

    def test_name_cached_recent(self):
        """
        Test that a recent cached NameRequest (accessed within 1 day)
        is returned without calling external API.
        """
        url = reverse("names-api")
        response = self.client.get(url, {"name": "John"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "John"

    @patch("requests.get")
    def test_name_fetch_and_save(self, mock_get):
        """
        Test fetching data from external APIs and saving
        Country and NameCountry data in the database.
        """
        url = reverse("names-api")

        # Mock responses: first from nationalize.io, second from restcountries.com
        mock_get.side_effect = [
            type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "json": lambda self=None: {
                        "country": [{"country_id": "US", "probability": 0.75}]
                    },
                },
            )(),
            type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "json": lambda self=None: [
                        {
                            "name": {
                                "common": "United States",
                                "official": "United States of America",
                            },
                            "region": "Americas",
                            "subregion": "Northern America",
                            "independent": True,
                            "capital": ["Washington D.C."],
                            "capitalInfo": {"latlng": [38.8951, -77.0364]},
                            "maps": {
                                "googleMaps": "https://maps.google.com/...",
                                "openStreetMaps": "https://osm.org/...",
                            },
                            "flags": {
                                "png": "https://flag.png",
                                "svg": "https://flag.svg",
                                "alt": "US flag",
                            },
                            "coatOfArms": {
                                "png": "https://coa.png",
                                "svg": "https://coa.svg",
                            },
                            "borders": ["CA", "MX"],
                        }
                    ],
                },
            )(),
        ]

        response = self.client.get(url, {"name": "John"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "John"
        assert len(response.data["country_associations"]) == 1
        assert (
            response.data["country_associations"][0]["country"]["code"] == "US"
        )


@pytest.mark.django_db
class TestPopularNamesAPI:
    """
    Tests for the /popular-names/ API endpoint.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize the API client before each test."""
        self.client = APIClient()

    def test_missing_country_param(self):
        """
        Ensure the API returns 400 Bad Request
        when 'country' query parameter is missing.
        """
        url = reverse("popular-names-api")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_no_data_for_country(self):
        """
        Ensure the API returns 404 Not Found
        when no popular names data exists for the given country code.
        """
        url = reverse("popular-names-api")
        response = self.client.get(url, {"country": "ZZ"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    def test_return_top_5_names(self):
        """
        Test that the API returns top 5 popular names for a valid country code.
        """
        country = Country.objects.create(
            code="US", name="United States", region="Americas"
        )
        for i in range(7):
            name_request = NameRequest.objects.create(
                name=f"Name{i}", request_count=i + 1
            )
            NameCountry.objects.create(
                name_request=name_request, country=country, probability=0.5
            )

        url = reverse("popular-names-api")
        response = self.client.get(url, {"country": "US"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5
