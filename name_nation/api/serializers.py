from rest_framework import serializers
from .models import Country, NameRequest, NameCountry


class CountrySerializer(serializers.ModelSerializer):
    """
    Serializes all relevant fields of the Country model for API responses.
    """

    class Meta:
        model = Country
        fields = [
            "code",
            "name",
            "official_name",
            "region",
            "subregion",
            "independent",
            "capital",
            "capital_lat",
            "capital_lon",
            "google_maps",
            "open_street_map",
            "flag_png",
            "flag_svg",
            "flag_alt",
            "coat_of_arms_png",
            "coat_of_arms_svg",
            "borders",
        ]


class NameCountrySerializer(serializers.ModelSerializer):
    """
    Serializes a NameCountry entry, including nested Country details and
    the associated probability score.
    """

    country = CountrySerializer(read_only=True)

    class Meta:
        model = NameCountry
        fields = ["country", "probability"]


class NameRequestSerializer(serializers.ModelSerializer):
    """
    Serializes a NameRequest entry, including its associated country probabilities.
    """

    country_associations = NameCountrySerializer(many=True, read_only=True)

    class Meta:
        model = NameRequest
        fields = [
            "name",
            "request_count",
            "last_accessed",
            "country_associations",
        ]
