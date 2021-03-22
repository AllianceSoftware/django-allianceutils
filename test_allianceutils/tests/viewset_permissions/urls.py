from rest_framework.routers import DefaultRouter

from .views import NinjaTurtleViewSet
from .views import NinjaTurtleGetModelViewSet
from .views import SimpleTestViewSet

app_name = 'permissions'

router = DefaultRouter(trailing_slash=True)
router.include_format_suffixes = False
router.register(r'turtle/simple', SimpleTestViewSet, basename='simple')
router.register(r'turtle/model', NinjaTurtleViewSet, basename='model')
router.register(r'turtle/getmodel', NinjaTurtleGetModelViewSet, basename='getmodel')

urlpatterns = router.urls
