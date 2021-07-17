from django.urls import path

from .views import LoginRequiredView

app_name = 'profile_auth'

urlpatterns = [
    path(r'protected/', LoginRequiredView.as_view(), name='login_required')
]
