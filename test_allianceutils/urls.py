from django.conf.urls import include
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.urls import path

import test_allianceutils.tests.middleware.urls
import test_allianceutils.tests.profile_auth.urls
import test_allianceutils.tests.viewset_permissions.urls

urlpatterns = [
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('middleware/', include(test_allianceutils.tests.middleware.urls)),
    path('profile_auth/', include(test_allianceutils.tests.profile_auth.urls)),
    path('viewset_permissions/', include(test_allianceutils.tests.viewset_permissions.urls)),
]
