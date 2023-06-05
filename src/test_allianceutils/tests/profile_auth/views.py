from typing import cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from test_allianceutils.tests.profile_auth.models import User


class LoginRequiredView(LoginRequiredMixin, TemplateView):
    template_name = 'profile_auth/login_required.html'

    def get_context_data(self, **kwargs):
        # if we get to here then user must be authenticated
        user = self.request.user
        assert isinstance(user, User)

        context = super().get_context_data(**kwargs)
        context['user'] = {
            'id': user.id,
            'username': user.email,
            'class': user.__class__.__name__,
        }
        return context
