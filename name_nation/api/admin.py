from django.contrib import admin
from .models import Country, NameRequest, NameCountry

admin.site.register(Country)
admin.site.register(NameRequest)
admin.site.register(NameCountry)
