from django.contrib.admin.views.decorators import \
    staff_member_required as original_staff_member_required
from django.contrib.auth import REDIRECT_FIELD_NAME


# dont redirect to admin:login which breaks if admin's not present - redirect to generic login instead (which None will do).
def staff_member_required(view_func=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    return original_staff_member_required(view_func, redirect_field_name, login_url)
