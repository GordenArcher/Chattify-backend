from django.contrib.gis.geoip2 import GeoIP2

def get_client_ip(request):
    """Extract the real IP address even behind a proxy."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0] 
    return request.META.get('REMOTE_ADDR')



def get_location(ip):
    """Get city and country from IP address using GeoIP2."""
    try:
        geo = GeoIP2()
        location = geo.city(ip)
        city = location.get("city", "Unknown")
        country = geo.country_name(ip)
        return city, country
    except Exception:
        return "Unknown", "Unknown"
