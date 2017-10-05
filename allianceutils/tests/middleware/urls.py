from django.conf.urls import url

from .views import run_queries

urlpatterns = [
    url(r'^$', run_queries, name='run_queries')
]
