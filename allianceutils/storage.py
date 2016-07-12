from django.conf import settings
from storages.backends.s3boto import S3BotoStorage

# Define custom storage classes so we can have media and static files with
# separate prefixes on S3
class StaticStorage(S3BotoStorage):
    location = settings.STATICFILES_LOCATION

class MediaStorage(S3BotoStorage):
    location = settings.MEDIAFILES_LOCATION
