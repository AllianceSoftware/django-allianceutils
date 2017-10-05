from django.conf.urls import url

from .views import LoginRequiredView

urlpatterns = [
    url(r'^protected/$', LoginRequiredView.as_view(), name='login_required')
]
