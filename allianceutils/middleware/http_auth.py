import base64

from django.conf import settings
from django.http import HttpResponse


class HttpAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __unauthorized(self):
        response = HttpResponse('You are not authorized to view this resource.', status=401)
        response['WWW-Authenticate']='Basic realm="restricted"'
        return response

    def __call__(self, request):
        auth_username = getattr(settings,'HTTP_AUTH_USERNAME',None)
        if not auth_username:
            return self.get_response(request)
        auth_password = getattr(settings,'HTTP_AUTH_PASSWORD',None)

        environ = request.environ
        authorization = environ.get('HTTP_AUTHORIZATION', None)
        if not authorization:
            return self.__unauthorized()

        (method, authentication) = authorization.split(' ', 1)
        if 'basic' == method.lower():
            request_username, request_password = str(base64.b64decode(authentication.strip()), 'utf-8').split(':', 1)
            if auth_username == request_username and auth_password == request_password:
                return self.get_response(request)

        return self.__unauthorized()
