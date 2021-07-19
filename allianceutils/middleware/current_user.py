import threading

from django.utils.deprecation import MiddlewareMixin

GLOBAL_USER = threading.local()

class CurrentUserMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None):
        self.get_response = get_response

    """
    Middleware to enable accessing the currently logged-in user without
    a request object.
    """
    def process_request(self, request):
        """
        Loads the user record for the currently logged in user and adjusts the scope security based on
        that user
        :param request: The current request
        :return None
        """
        assert hasattr(request, 'user'), (
            "The CurrentUser middleware requires the authentication middleware "
            "to be installed. Edit your MIDDLEWARE setting to insert"
            "'django.contrib.auth.middleware.AuthenticationMiddleware' before "
            f"'{__name__}.CurrentUserMiddleware'."
        )

        if request.user is not None:
            CurrentUserMiddleware._set_user(request.user.id, request.META.get('REMOTE_ADDR'))
        else:
            CurrentUserMiddleware._set_user(None, request.META.get('REMOTE_ADDR'))

    def process_response(self, request, response):
        CurrentUserMiddleware._del_user()
        return response

    def process_exception(self, request, exception):
        CurrentUserMiddleware._del_user()

    @classmethod
    def _set_user(cls, user_id, remote_ip):
        GLOBAL_USER.user = {
            'user_id': user_id,
            'remote_ip': remote_ip,
        }

    @classmethod
    def get_user(cls):
        thread_id = threading.current_thread().ident
        try:
            return GLOBAL_USER.user
        except AttributeError:
            raise KeyError('Thread {} not already registered with CurrentUserMiddleware.'.format(thread_id))

    @classmethod
    def _del_user(cls):
        del GLOBAL_USER.user
