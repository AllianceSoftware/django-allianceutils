from django.urls import path

from .views import current_user
from .views import query_overhead
from .views import run_queries

app_name = 'middleware'

urlpatterns = [
    path('run_queries/', run_queries, name='run_queries'),
    path('query_overhead/', query_overhead, name='query_overhead'),
    path('current_user/', current_user, name='current_user'),
]
