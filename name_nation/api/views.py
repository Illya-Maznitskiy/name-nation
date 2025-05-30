from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

from .models import NameRequest, Country, NameCountry
from .serializers import NameRequestSerializer


class NamesAPIView(APIView):
    """
    API view to handle requests for nationality prediction based on a given name.

    - GET /names/?name=<name>:
      Returns probability of countries associated with the given name.
      Caches results for 1 day to reduce external API calls.
    """

    def get(self, request):
        """
        Handles GET requests to retrieve nationality data for the specified name.
        """
        name = request.query_params.get("name")
        if not name:
            return Response(
                {"error": "Missing 'name' query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        one_day_ago = timezone.now() - timezone.timedelta(days=1)
        try:
            name_request = NameRequest.objects.get(name__iexact=name)
            if (
                name_request.last_accessed
                and name_request.last_accessed > one_day_ago
            ):
                serializer = NameRequestSerializer(name_request)
                return Response(serializer.data)
        except NameRequest.DoesNotExist:
            name_request = None

        response = requests.get(f"https://api.nationalize.io/?name={name}")
        if response.status_code != 200:
            return Response(
                {"error": "Failed to fetch data from external API."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = response.json()
        countries_data = data.get("country", [])

        if not countries_data:
            return Response(
                {"error": f"No country data found for name '{name}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not name_request:
            name_request = NameRequest.objects.create(
                name=name, request_count=1, last_accessed=timezone.now()
            )
        else:
            name_request.request_count += 1
            name_request.last_accessed = timezone.now()
            name_request.save()

        # Remove old country associations
        NameCountry.objects.filter(name_request=name_request).delete()

        for country_info in countries_data:
            country_code = country_info.get("country_id")
            probability = country_info.get("probability", 0)

            country_obj, created = Country.objects.get_or_create(
                code=country_code
            )
            if created or not country_obj.name:
                rest_response = requests.get(
                    f"https://restcountries.com/v3.1/alpha/{country_code}"
                )
                if rest_response.status_code == 200:
                    country_json = rest_response.json()
                    if country_json:
                        country_data = country_json[0]
                        country_obj.name = country_data.get("name", {}).get(
                            "common", ""
                        )
                        country_obj.official_name = country_data.get(
                            "name", {}
                        ).get("official", "")
                        country_obj.region = country_data.get("region", "")
                        country_obj.subregion = country_data.get(
                            "subregion", ""
                        )
                        country_obj.independent = country_data.get(
                            "independent", None
                        )
                        capital = country_data.get("capital", [])
                        country_obj.capital = capital[0] if capital else ""
                        latlng = country_data.get("capitalInfo", {}).get(
                            "latlng", []
                        )
                        if latlng and len(latlng) == 2:
                            country_obj.capital_lat = latlng[0]
                            country_obj.capital_lon = latlng[1]
                        country_obj.google_maps = country_data.get(
                            "maps", {}
                        ).get("googleMaps", "")
                        country_obj.open_street_map = country_data.get(
                            "maps", {}
                        ).get("openStreetMaps", "")
                        country_obj.flag_png = country_data.get(
                            "flags", {}
                        ).get("png", "")
                        country_obj.flag_svg = country_data.get(
                            "flags", {}
                        ).get("svg", "")
                        country_obj.flag_alt = country_data.get(
                            "flags", {}
                        ).get("alt", "")
                        coat_of_arms = country_data.get("coatOfArms", {})
                        country_obj.coat_of_arms_png = coat_of_arms.get(
                            "png", ""
                        )
                        country_obj.coat_of_arms_svg = coat_of_arms.get(
                            "svg", ""
                        )
                        borders = country_data.get("borders", [])
                        country_obj.borders = (
                            ",".join(borders) if borders else ""
                        )
                        country_obj.save()

            NameCountry.objects.create(
                name_request=name_request,
                country=country_obj,
                probability=probability,
            )

        serializer = NameRequestSerializer(name_request)
        return Response(serializer.data)


class PopularNamesAPIView(APIView):
    """
    API view to retrieve the most popular names for a given country.

    - GET /popular_names/?country=<country_code_or_name>:
      Returns top 5 names most frequently associated with the specified country.
    """

    def get(self, request):
        """
        Handles GET requests to retrieve the most popular names for a country.
        """
        country_code = request.query_params.get("country")

        if not country_code:
            return Response(
                {"error": "Missing 'country' query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        popular_names = (
            NameCountry.objects.filter(
                Q(country__code__iexact=country_code)
                | Q(country__name__iexact=country_code)
            )
            .values("name_request__name")
            .annotate(name_count=Count("name_request__name"))
            .order_by("-name_count")[:5]
        )

        if not popular_names:
            return Response(
                {"error": f"No data found for country '{country_code}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = [
            {"name": item["name_request__name"], "count": item["name_count"]}
            for item in popular_names
        ]

        return Response(result)
