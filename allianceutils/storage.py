from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


# Define custom storage classes so we can have media and static files with
# separate prefixes on S3. If an user is not using one then the setting can be omitted.
class StaticStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = settings.STATICFILES_LOCATION


class MediaStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location = settings.MEDIAFILES_LOCATION
