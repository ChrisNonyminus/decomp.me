import logging
from typing import Optional, TYPE_CHECKING, Union

from django.contrib import auth
from django.contrib.auth.models import User
from django.http.request import HttpRequest
from django.utils.timezone import now
from rest_framework.request import Request as DRFRequest

from .models.profile import Profile

if TYPE_CHECKING:
    from .models.github import GitHubUser


class AnonymousUser(auth.models.AnonymousUser):
    profile: Profile


if TYPE_CHECKING:

    class Request(DRFRequest):
        user: Union[User, AnonymousUser]
        profile: Profile

else:
    Request = DRFRequest


def disable_csrf(get_response):
    def middleware(request: HttpRequest):
        setattr(request, "_dont_enforce_csrf_checks", True)
        return get_response(request)

    return middleware


def set_user_profile(get_response):
    """
    Makes sure that `request.profile` is always available, even for anonymous users.
    """

    def middleware(request: Request):
        # Skip if the request is from SSR
        if (
            "User-Agent" in request.headers
            and "node-fetch" in request.headers["User-Agent"]
        ):
            request.profile = Profile()
            return get_response(request)

        profile: Optional[Profile] = None

        # Use the user's profile if they're logged in
        if not request.user.is_anonymous:
            profile = Profile.objects.filter(user=request.user).first()

        # Otherwise, use their session profile
        if not profile:
            id = request.session.get("profile_id")

            if isinstance(id, int):
                profile = Profile.objects.filter(id=id).first()
                profile_user = User.objects.filter(profile=profile).first()

                # If the request is logged out but the profile stored in their session
                # references a user, don't use that profile
                if profile_user and request.user.is_anonymous:
                    profile = None

        # If we still don't have a profile, create a new one
        if not profile:
            profile = Profile()

            # And attach it to the logged-in user, if there is one
            if not request.user.is_anonymous:
                assert Profile.objects.filter(user=request.user).first() is None
                profile.user = request.user

            profile.save()
            request.session["profile_id"] = profile.id
            logging.debug(f"Made new profile: {profile}")

        if profile.user is None and not request.user.is_anonymous:
            profile.user = request.user

        profile.last_request_date = now()
        profile.save()

        request.profile = profile

        return get_response(request)

    return middleware
