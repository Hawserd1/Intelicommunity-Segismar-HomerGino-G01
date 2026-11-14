from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView

from .models import CustomUser
from .forms import ProfileForm, RegistrationForm


class RegisterView(CreateView):
    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        messages.success(self.request, 'Your account was created. You can now log in.')
        return super().form_valid(form)


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_url = self.get_redirect_url()
        if redirect_url:
            return redirect_url
        dashboard_names = {
            CustomUser.Role.STANDARD_USER: 'dashboard:member',
            CustomUser.Role.MODERATOR: 'dashboard:moderator',
            CustomUser.Role.ADMINISTRATOR: 'dashboard:administrator',
        }
        return reverse(dashboard_names.get(self.request.user.role, 'dashboard:home'))


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your profile was updated.')
        return super().form_valid(form)
