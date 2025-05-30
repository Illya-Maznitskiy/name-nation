from django.db import models


class Country(models.Model):
    """
    Stores detailed information about a country, including geolocation, maps,
    flags, and border relationships. Enriched from the REST Countries API.
    """

    code = models.CharField(max_length=3, unique=True)  # e.g., "US"
    name = models.CharField(max_length=100)
    official_name = models.CharField(max_length=150, blank=True)
    region = models.CharField(max_length=100)
    subregion = models.CharField(max_length=100, blank=True)
    independent = models.BooleanField(null=True)
    capital = models.CharField(max_length=100, blank=True)
    capital_lat = models.FloatField(null=True, blank=True)
    capital_lon = models.FloatField(null=True, blank=True)
    google_maps = models.URLField(blank=True)
    open_street_map = models.URLField(blank=True)
    flag_png = models.URLField(blank=True)
    flag_svg = models.URLField(blank=True)
    flag_alt = models.CharField(max_length=255, blank=True)
    coat_of_arms_png = models.URLField(blank=True)
    coat_of_arms_svg = models.URLField(blank=True)
    borders = models.CharField(max_length=255, blank=True)  # e.g., "CA,MX"

    def __str__(self):
        return self.name


class NameRequest(models.Model):
    """
    Represents a name that has been queried by users. Stores metadata about
    how often and when it was last accessed.
    """

    name = models.CharField(max_length=100)
    request_count = models.IntegerField(default=1)
    last_accessed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class NameCountry(models.Model):
    """
    Associates a queried name with a country and a probability indicating
    the likelihood that the name is common in that country.
    """

    name_request = models.ForeignKey(
        NameRequest,
        on_delete=models.CASCADE,
        related_name="country_associations",
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="name_associations"
    )
    probability = models.FloatField()

    def __str__(self):
        return f"{self.name_request.name} - {self.country.code} ({self.probability})"
