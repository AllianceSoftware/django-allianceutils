from django.conf.urls import include
from django.conf.urls import url
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.urls import path

import test_allianceutils.tests.middleware.urls
import test_allianceutils.tests.object_cache.urls
import test_allianceutils.tests.profile_auth.urls
import test_allianceutils.tests.viewset_permissions.urls

urlpatterns = [
    path(r'accounts/login/', LoginView.as_view(), name='login'),
    path(r'accounts/logout/', LogoutView.as_view(), name='logout'),
    path(r'middleware/', include(test_allianceutils.tests.middleware.urls)),
    path(r'object_cache/', include(test_allianceutils.tests.object_cache.urls)),
    path(r'profile_auth/', include(test_allianceutils.tests.profile_auth.urls)),
    path(r'viewset_permissions/', include(test_allianceutils.tests.viewset_permissions.urls)),
]
