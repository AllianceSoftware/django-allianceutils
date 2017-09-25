from django.conf.urls import include
from django.conf.urls import url
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView

import allianceutils.tests.profile_auth.urls

urlpatterns = [
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', LogoutView.as_view(), name='logout'),
    url(r'^profile_auth/', include(allianceutils.tests.profile_auth.urls)),
]
