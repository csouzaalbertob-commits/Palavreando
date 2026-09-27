from django.conf import settings

def global_version(request):
    return {
        'APP_VERSION': getattr(settings, 'APP_VERSION', '1.0.0')
    }