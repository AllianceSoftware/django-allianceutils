from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LoginRequiredView(LoginRequiredMixin, TemplateView):
    template_name = 'profile_auth/login_required.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = {
            'username': self.request.user.username,
            'class': self.request.user.__class__.__name__,
        }
        return context
