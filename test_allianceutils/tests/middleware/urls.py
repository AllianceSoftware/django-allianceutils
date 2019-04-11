from django.conf.urls import url

from .views import current_user
from .views import query_overhead
from .views import run_queries

app_name = 'middleware'

urlpatterns = [
    url(r'^run_queries/$', run_queries, name='run_queries'),
    url(r'^query_overhead/$', query_overhead, name='query_overhead'),

    url(r'^current_user/$', current_user, name='current_user'),

]
